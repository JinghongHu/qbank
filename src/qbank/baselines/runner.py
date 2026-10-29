"""Baseline runner: persistent single-threaded workers, hard wall-clock budgets, crash isolation, caching.

Status codes: pass | fail | tool_error | unsupported | timeout | crash | unavailable | unverified (checking exceeded
VERIFY_LIMIT; never counted as correct).
Budget semantics: each (instance, tool, track) gets `budget` seconds of wall clock in one process
with every thread pool pinned to 1 thread; deterministic tools run once, anytime tools loop over seeds until the
deadline; the worker is killed at budget + GRACE seconds.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import platform
import sys
import time
import traceback
from collections import deque
from multiprocessing.connection import wait
from pathlib import Path

from ..core.canon import canonical_json, hash_hex
from ..core.instance import data_root

GRACE = 20.0
THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
              "VECLIB_MAXIMUM_THREADS": "1", "RAYON_NUM_THREADS": "1", "QISKIT_PARALLEL": "FALSE",
              "QISKIT_NUM_PROCS": "1"}


def _sysctl(name: str) -> str:
    try:
        import subprocess
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def core_counts() -> tuple[int, int]:
    """(performance cores, efficiency cores); on machines without core types: (all cores, 0)."""
    p, e = _sysctl("hw.perflevel0.physicalcpu"), _sysctl("hw.perflevel1.physicalcpu")
    if p.isdigit():
        return int(p), int(e) if e.isdigit() else 0
    return os.cpu_count() or 1, 0


def hardware() -> str:
    brand = _sysctl("machdep.cpu.brand_string") or platform.processor()
    p, e = core_counts()
    return (f"{brand} ({p} performance + {e} efficiency cores) | {platform.system()} {platform.release()} "
            f"{platform.machine()} | python {platform.python_version()} | 1 thread/job")


def cache_key(h: str, tool: str, version: str, config: dict, track: str) -> str:
    return hashlib.sha256(canonical_json({"hash": h, "tool": tool, "version": version, "config": config, "track": track},
                                         allow_float=True)).hexdigest()[:32]


def cache_file(category: str, h: str) -> Path:
    return data_root() / "cache" / category / f"{hash_hex(h)}.jsonl"


def load_cache(category: str, h: str) -> dict:
    p = cache_file(category, h)
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["cache_key"]] = r
    return out


def load_all_records(category: str, h: str) -> dict:
    """Runner cache + external-import cache; drops external records written by the superseded import-v1."""
    out = {}
    for ns in (category, f"{category}-external"):
        for k, r in load_cache(ns, h).items():
            if r["tool"].startswith(("published:", "qecirc:")) and "import-v2" not in r.get("version", ""):
                continue
            out[k] = r
    return out


# ------------------------------------------------------------------ worker side
VERIFY_LIMIT = 660.0   # seconds allowed for checking a tool's output (not part of the tool budget); v1.2: 600 s of SAT
#                        miter (B, contracts/oracle.py) + 60 s for building the miter, so the checker's own limit
#                        fires first and its "unverified" verdict is recorded (before v1.2: 600 s)
_CONN = None


def _signal_verify():
    if _CONN is not None:
        _CONN.send({"_phase": "verify"})


def _run_job_A(job: dict, public: dict) -> dict:
    from ..categories.A.instances import verify
    from ..core.circuit import Circuit
    from ..core.costs import costs
    from . import tools_a as T
    tool, track = job["tool"], job["track"]
    t0 = time.monotonic()
    c0 = time.process_time()
    deadline = t0 + job["budget"]
    res = {"tool": tool, "track": track}
    try:
        if tool.startswith("mqt.qmap.synthesize_clifford"):
            cands = _qmap_isolated(public, track, heuristic="heuristic" in tool, timeout=job["budget"])
        else:
            fn = T.tools_for(public, track).get(tool)
            if fn is None:
                return {**res, "status": "unsupported", "reason": "tool not applicable to this track"}
            cands = fn(public, track, job["seed"], deadline)
    except NotImplementedError as e:
        return {**res, "status": "unsupported", "reason": str(e), "wall_tool_s": time.monotonic() - t0}
    except _Crash as e:
        return {**res, "status": "crash", "reason": str(e), "wall_tool_s": time.monotonic() - t0}
    except _Timeout as e:
        return {**res, "status": "timeout", "reason": str(e), "wall_tool_s": time.monotonic() - t0}
    except Exception as e:
        return {**res, "status": "tool_error", "reason": f"{type(e).__name__}: {str(e)[:300]}",
                "trace": traceback.format_exc()[-1500:], "wall_tool_s": time.monotonic() - t0}
    wall_tool = time.monotonic() - t0
    cpu_tool = time.process_time() - c0
    _signal_verify()
    if wall_tool > job["budget"]:
        # a result delivered after the budget is not counted (same budget for every tool)
        return {**res, "status": "timeout", "reason": f"result delivered after the budget ({wall_tool:.1f} s > {job['budget']} s)",
                "wall_tool_s": wall_tool, "cpu_tool_s": cpu_tool}
    metric = public["tracks"][track]["metric"]
    scored = []
    for i, cd in enumerate(cands):
        cs = costs(cd["circuit"])
        scored.append((cs[metric], cs["two_qubit_depth"], cs["depth"], i, cd, cs))
    scored.sort(key=lambda s: s[:4])
    tv = time.monotonic()
    fails = []
    best = None
    for _, _, _, i, cd, _ in scored:
        v = verify(public, track, cd["circuit"], cd.get("output_map"))
        if v.status == "pass":
            best = (i, cd, v)
            break
        fails.append(v.reason)
    wall_verify = time.monotonic() - tv
    out = {**res, "n_candidates": len(cands), "wall_tool_s": wall_tool, "cpu_tool_s": cpu_tool, "wall_verify_s": wall_verify,
           "verify_failures": fails[:5]}
    if best is None:
        return {**out, "status": "fail", "reason": fails[0] if fails else "no candidate"}
    i, cd, v = best
    cs = costs(v.circuit)
    return {**out, "status": "pass", "costs": cs, "output_map": cd.get("output_map"), "meta": cd.get("meta", {}),
            "pauli_correction": v.pauli_correction, "circuit": v.circuit.to_json(), "best_candidate_index": i}


class _Crash(Exception):
    pass


class _Timeout(Exception):
    pass


def _qmap_isolated(public, track, heuristic: bool, timeout: float):
    """MQT QMAP in a separate minimal process: its heuristic mode segfaults on the Phase-0 machine."""
    import subprocess
    from qiskit import qasm2
    from ..core.circuit import Circuit
    from . import tools_a as T
    spec = public["tracks"][track]
    if spec["connectivity"] != "all" or spec["contract"] == "codespace_state":
        raise NotImplementedError("QMAP Clifford synthesis only used for all-to-all full-rank targets")
    if not heuristic and public["n"] > 3:
        raise NotImplementedError("QMAP SAT (optimal) only for n <= 3 (Phase-0 measurement: n=4 > 600 s)")
    rows, _ = T.synth_targets(public, track)
    env = {**os.environ, **THREAD_ENV}
    try:
        p = subprocess.run([sys.executable, "-c", T.QMAP_SCRIPT], input=json.dumps([rows.to_strings(), heuristic]),
                           capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        raise _Timeout(f"QMAP exceeded {timeout} s")
    if p.returncode != 0:
        if p.returncode < 0:
            raise _Crash(f"QMAP process killed by signal {-p.returncode} (heuristic={heuristic})")
        raise RuntimeError(p.stderr[-300:])
    qc = qasm2.loads(json.loads(p.stdout.strip().splitlines()[-1])["qasm"])
    return [{"circuit": Circuit.from_qiskit(qc, clifford_only=True)}]


def _worker_main(conn):
    global _CONN
    _CONN = conn
    os.environ.update(THREAD_ENV)
    from ..core.instance import load_public
    pubs: dict[str, dict] = {}
    while True:
        job = conn.recv()
        if job is None:
            return
        try:
            pub = pubs.get(job["hash"])
            if pub is None:
                pub = load_public(job["category"], job["hash"])
                pubs.clear()
                pubs[job["hash"]] = pub
            if job["category"] == "A":
                r = _run_job_A(job, pub)
            elif job["category"] == "B":
                from .job_b import run_job_B
                r = run_job_B(job, pub, _signal_verify)
            elif job["category"] == "C":
                from .job_c import run_job_C
                r = run_job_C(job, pub, _signal_verify)
            elif job["category"] == "D":
                from .job_d import run_job_D
                r = run_job_D(job, pub, _signal_verify)
            else:
                r = {"status": "unsupported", "reason": f"category {job['category']} not implemented yet"}
        except Exception as e:  # never let a job take the worker down silently
            r = {"status": "tool_error", "reason": f"runner: {type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]}
        conn.send(r)


# ------------------------------------------------------------------ core policy (server reruns, phase 7)
class CorePolicy:
    """Reruns of the classical baselines on the Linux server (NEXT_ROUND_EXTRA 2): every worker takes ONE slot of the
    unified core configuration (evoA fw2/coreconf.py: profile "pcore" = the campaign's P-core lock set, shared with every
    timed evaluation; "ecore" = the E-cores 12-19 under their own lock set, a timing condition the report must state),
    holds its lock and a lease for its lifetime (the lease token is in the worker's environment, so the whole-machine
    watch counts it as an evaluation and a dead runner's workers can be found), runs pinned to that core, waits for the
    watch's hold before each job and runs a job again when the watch saw foreign load during it. QBANK_CORES selects the
    profile; on Linux it is required (a run without it is refused), on macOS nothing changes."""

    def __init__(self, profile):
        import sys as _s
        evoa = Path(__file__).resolve().parents[3]
        if str(evoa / "fw2") not in _s.path:
            _s.path.insert(0, str(evoa / "fw2"))
        import coreconf as CC
        import hostwatch as HW
        import resguard as RG
        self.CC, self.HW, self.RG = CC, HW, RG
        self.p = CC.resolve(dict(os.environ, FW_CORE_PROFILE=profile))
        if self.p["name"] not in ("pcore", "ecore", "test"):   # test: the sandbox test of this class only
            raise SystemExit(f"QBANK_CORES={profile}: baseline reruns use the pcore or ecore profile")
        CC.LOCKDIR.mkdir(parents=True, exist_ok=True)
        self.slots = RG.Slots(CC.LOCKDIR, self.p["locktag"])

    def record(self):
        return self.CC.record(self.p)

    def acquire(self):
        """Block until a free, provably clean slot: -> (k, cpus, lock file, lease)."""
        import fcntl
        while True:
            self.HW.gate(self.p, log=lambda m: print("[runner] " + m, flush=True))
            for k, cpus in enumerate(self.p["slots"]):
                if self.slots.quarantined(k):
                    continue
                lk = open(self.CC.LOCKDIR / f"{self.p['locktag']}{k}", "w")
                try:
                    fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    lk.close()
                    continue
                if self.slots.recover(k) != "free":
                    lk.close()
                    continue
                return k, cpus, lk, self.slots.new_lease(k, "qbank-baseline-rerun")
            time.sleep(2.0)

    def bind(self, k, lease, pid):
        info = dict(lease, supervisor=pid, supervisor_start=self.RG.start_time(pid))
        self.slots.write(k, info)

    def release(self, k, lk, lease, proc):
        try:
            if proc.is_alive():
                proc.kill()
            proc.join(5)
        except Exception:
            pass
        self.RG.kill_token(lease["token"])
        self.slots.clear(k, lease["token"])
        lk.close()

    def contended(self, t0, t1):
        return self.HW.contended(self.p, t0, t1)


def core_policy():
    """-> CorePolicy or None (macOS / no rerun policy needed)."""
    prof = os.environ.get("QBANK_CORES")
    if prof:
        return CorePolicy(prof)
    if platform.system() == "Linux":
        raise SystemExit("baseline reruns on the server must state their cores: QBANK_CORES=pcore (the campaign's P-core "
                         "lock set, comparable timing) or QBANK_CORES=ecore (E-cores 12-19, timing stated as such)")
    return None


# ------------------------------------------------------------------ parent side
class _Slot:
    def __init__(self, ctx, policy=None):
        self.policy, self.core = policy, None
        if policy is not None:   # the worker inherits the lease token and runs on the slot's core only
            from multiprocessing import resource_tracker
            resource_tracker.ensure_running()   # started before the token is set: it is not part of the evaluation
            self.core = policy.acquire()
            os.environ[policy.RG.LEASE_ENV] = self.core[3]["token"]
        self.parent, child = ctx.Pipe()
        self.proc = ctx.Process(target=_worker_main, args=(child,), daemon=True)
        self.proc.start()
        if policy is not None:
            os.environ.pop(policy.RG.LEASE_ENV, None)
            k, cpus, lk, lease = self.core
            os.sched_setaffinity(self.proc.pid, set(int(c) for c in str(cpus).split(",")))
            policy.bind(k, lease, self.proc.pid)
        self.job = None
        self.t0 = 0.0

    def kill(self):
        try:
            self.proc.kill()
            self.proc.join(5)
        except Exception:
            pass
        if self.policy is not None and self.core is not None:
            k, cpus, lk, lease = self.core
            self.policy.release(k, lk, lease, self.proc)
            self.core = None


def run_jobs(jobs: list[dict], workers: int = 10, log=print) -> int:
    """Run jobs (dicts with category, iid, hash, track, tool, version, config, budget, seed); results go to the cache."""
    ctx = mp.get_context("spawn")
    policy = core_policy()
    todo = deque()
    for j in jobs:
        key = cache_key(j["hash"], j["tool"], j["version"], j["config"], j["track"])
        if key not in load_cache_keys(j.get("ns", j["category"]), j["hash"]):
            todo.append({**j, "cache_key": key})
    total = len(todo)
    log(f"[runner] {total} jobs to run ({len(jobs) - total} cached), {workers} workers")
    nw = min(workers, max(1, total))
    if policy is not None:
        nw = min(nw, len(policy.p["slots"]))
        log(f"[runner] cores: {policy.record()}")
    slots = [_Slot(ctx, policy) for _ in range(nw)]
    done = 0
    hw = hardware()
    t_start = time.time()
    while todo or any(s.job for s in slots):
        for s in slots:
            if s.job is None and todo:
                s.job = todo.popleft()
                if policy is not None:
                    policy.HW.gate(policy.p)
                s.wall0 = time.time()
                s.t0 = time.monotonic()
                s.verifying_since = None
                # v1.2: concurrency at dispatch; time-limited tools get less compute when more
                # jobs share the machine, and on Apple silicon jobs beyond the performance-core count run on
                # efficiency cores
                s.conc = {"workers": len(slots), "busy_slots_at_start": sum(1 for x in slots if x.job),
                          "loadavg_1m_at_start": round(os.getloadavg()[0], 2)}
                s.parent.send(s.job)
        ready = wait([s.parent for s in slots if s.job], timeout=0.5)
        now = time.monotonic()
        for s in slots:
            if not s.job:
                continue
            r = None
            if s.parent in ready:
                try:
                    r = s.parent.recv()
                except (EOFError, OSError):
                    r = {"status": "crash", "reason": f"worker died (exitcode {s.proc.exitcode})"}
                if r is not None and r.get("_phase") == "verify":
                    s.verifying_since = now      # tool finished within budget; verification has its own limit
                    continue
            elif not s.proc.is_alive():
                r = {"status": "crash", "reason": f"worker died (exitcode {s.proc.exitcode})"}
            elif getattr(s, "verifying_since", None) is None and now - s.t0 > s.job["budget"] + GRACE:
                r = {"status": "timeout", "reason": f"killed after {now - s.t0:.1f} s (budget {s.job['budget']} s + grace {GRACE} s)"}
            elif getattr(s, "verifying_since", None) is not None and now - s.verifying_since > VERIFY_LIMIT:
                r = {"status": "unverified", "reason": f"verification exceeded {VERIFY_LIMIT:.0f} s"}
            if r is None:
                continue
            if r["status"] in ("crash", "timeout", "unverified") and ("worker died" in r.get("reason", "") or "killed after" in r.get("reason", "")
                                                                       or "verification exceeded" in r.get("reason", "")):
                s.kill()
                new = _Slot(ctx, policy)
                s.parent, s.proc, s.core = new.parent, new.proc, new.core
            if policy is not None:
                hit = policy.contended(s.wall0, time.time())
                if hit != [] and s.job.get("_core_reruns", 0) < 3:   # disturbed timing: never stored, run again
                    log(f"[runner] {s.job['iid']} {s.job['tool']}: foreign load on the watched cores during the run: again")
                    todo.append(dict(s.job, _core_reruns=s.job.get("_core_reruns", 0) + 1))
                    s.job = None
                    s.verifying_since = None
                    continue
                r = dict(r, core_timing=dict(policy.record(), core=(s.core or [None, None])[1],
                                             contended=hit if hit else ([] if hit == [] else "unwatched"),
                                             reruns=s.job.get("_core_reruns", 0)))
            _store(s.job, r, now - s.t0, hw, getattr(s, "conc", None))
            s.job = None
            s.verifying_since = None
            done += 1
            if done % 50 == 0 or done == total:
                el = time.time() - t_start
                log(f"[runner] {done}/{total} done, {el/60:.1f} min elapsed")
    for s in slots:
        try:
            s.parent.send(None)
        except Exception:
            pass
        s.proc.join(5)
        if s.proc.is_alive() or policy is not None:
            s.kill()
    return done


_KEYS_CACHE: dict[str, set] = {}


def load_cache_keys(category: str, h: str) -> set:
    k = f"{category}:{h}"
    if k not in _KEYS_CACHE:
        _KEYS_CACHE[k] = set(load_cache(category, h))
    return _KEYS_CACHE[k]


def _store(job: dict, r: dict, wall_total: float, hw: str, conc: dict | None = None) -> None:
    rec = {"cache_key": job["cache_key"], "category": job["category"], "instance_id": job["iid"], "hash": job["hash"],
           "track": job["track"], "tool": job["tool"], "version": job["version"], "config": job["config"],
           "budget_s": job["budget"], "seed": job["seed"], "hardware": hw, "wall_total_s": round(wall_total, 3),
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **({"concurrency": conc} if conc else {}), **r}
    p = cache_file(job.get("ns", job["category"]), job["hash"])
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    load_cache_keys(job.get("ns", job["category"]), job["hash"]).add(job["cache_key"])


_CONC_EST: dict | None = None


def concurrency_estimates() -> dict:
    """For records written before v1.2 (no "concurrency" field): the number of qbank runner jobs (all categories and
    namespaces) of at least 2 s whose run interval [finished_at - wall_total_s, finished_at] contains the record's
    start, plus the job itself. finished_at has 1 s resolution; load from anything other than qbank runner jobs is not
    included. cache_key -> int."""
    global _CONC_EST
    if _CONC_EST is not None:
        return _CONC_EST
    import re
    from datetime import datetime
    # the run intervals are extracted once and kept in a small index (records written before v1.2 never change);
    # the cache lines hold whole circuits, so only three fields are pulled out with regular expressions
    idx_p = data_root() / "baselines" / "run_intervals.v1_1.json"
    if idx_p.exists():
        iv = [tuple(x) for x in json.loads(idx_p.read_text())]
    else:
        iv = []
        pk = re.compile(r'"cache_key": "([0-9a-f]+)"')
        pf = re.compile(r'"finished_at": "([^"]+)"')
        pw = re.compile(r'"wall_total_s": ([0-9.eE+-]+)')
        for p in sorted((data_root() / "cache").glob("*/*.jsonl")):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    k, fin, w = pk.search(line), pf.search(line), pw.search(line)
                    if not (k and fin and w):
                        continue
                    end = datetime.strptime(fin.group(1), "%Y-%m-%dT%H:%M:%S%z").timestamp()
                    iv.append((end - float(w.group(1)), end, k.group(1)))
        idx_p.parent.mkdir(parents=True, exist_ok=True)
        idx_p.write_text(json.dumps(sorted(iv)))
    # only jobs that ran for >= 2 s are counted as competitors: with 1 s timestamps, bursts of sub-second jobs
    # (unsupported tools, cache-fast answers) would otherwise appear to overlap
    longer = [(a, b) for a, b, _ in iv if b - a >= 2.0]
    starts = sorted(a for a, _ in longer)
    ends = sorted(b for _, b in longer)
    import bisect
    out = {}
    for a, b, k in iv:
        # competitors with start <= a < end, plus the job itself if it is not among them
        n = bisect.bisect_right(starts, a) - bisect.bisect_right(ends, a)
        out[k] = n + (0 if b - a >= 2.0 else 1)
    _CONC_EST = out
    return out
