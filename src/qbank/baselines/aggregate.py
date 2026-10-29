"""Aggregate cached baseline runs into the baseline table and best_known.

Outputs (data/v1/baselines/<C>/):
  records.jsonl            one record per (instance, track, tool config) incl. failures/timeouts/crashes
  circuits/<hash>.jsonl.gz every verified circuit (qbank JSON), addressed as "<file>#<cache_key>"
  best_circuits/<hash>/<track>.{qasm,qpy,stim,json}   the best verified circuit per (instance, track)
  best_known.jsonl         min over verified baselines and reported-only published values (source recorded)
"""
from __future__ import annotations

import gzip
import json
import multiprocessing as mp
from collections import defaultdict

from ..core.canon import dump_json, hash_hex
from ..core.circuit import _QB_TO_STIM, Circuit
from ..core.costs import costs
from ..core.instance import data_root, load_index, load_public
from . import runner

REUSE_SUFFIX = " [a2a |0_L> circuit reused]"
STIM_OK = set(_QB_TO_STIM) | {"id"}


def _reuse_codespace(args):
    """Verify the instance's verified a2a circuits under the codespace contract (any codespace state is valid)."""
    from ..categories.A.instances import verify
    h, pub, recs = args
    out = []
    for r in recs:
        c = Circuit.from_json(r["circuit"])
        v = verify(pub, "codespace_a2a_2q", c, r.get("output_map"))
        base = {k: r[k] for k in ("category", "instance_id", "hash", "tool", "version", "config", "budget_s", "seed", "hardware")}
        rec = {**base, "track": "codespace_a2a_2q", "tool": r["tool"] + REUSE_SUFFIX, "reused_from": r["cache_key"],
               "cache_key": r["cache_key"] + "-cs", "wall_total_s": 0.0}
        if v.status == "pass":
            rec.update(status="pass", costs=costs(v.circuit), circuit=v.circuit.to_json(), pauli_correction=v.pauli_correction)
        else:
            rec.update(status="fail", reason=v.reason)
        out.append(rec)
    return out


TOF_CLIFFORD = "tof_clifford@inf"
TC_SUFFIX = " [circuit reused, re-verified on tof_clifford@inf]"   # "reused": not drawn by repro


def _reuse_tof_clifford(args):
    """B, contract version 2 (10-29): the Toffoli side track tof_clifford@inf has no runs of its own. The instance's
    verified circuits of the other tracks are re-verified under its contract, cheapest Toffoli count first, until the
    first one passes (at most 60 tried) -- the same rule as the 10-28 re-verification of the task-pack references
    (evoA/docs/baseline_plan_1028/ab_tools/reverify_b.py)."""
    from ..categories.B.instances import verify
    h, pub, recs = args
    out = []
    for r in sorted(recs, key=lambda r: (r["costs"]["toffoli_count"], r["tool"], r["track"], r["cache_key"]))[:60]:
        c = Circuit.from_json(r["circuit"])
        v = verify(pub, TOF_CLIFFORD, c)
        base = {k: r.get(k) for k in ("category", "instance_id", "hash", "version", "config", "budget_s", "seed", "hardware")}
        rec = {**base, "track": TOF_CLIFFORD, "tool": r["tool"] + TC_SUFFIX, "reused_from": r["cache_key"],
               "reused_track": r["track"], "cache_key": r["cache_key"] + "-tc", "wall_total_s": 0.0}
        if v.status == "pass":
            rec.update(status="pass", costs=costs(v.circuit), circuit=v.circuit.to_json())
            out.append(rec)
            break
        rec.update(status="fail", reason=(v.reason or "")[:300])
        out.append(rec)
    return out


def aggregate(category: str = "A", workers: int = 10, published: list[dict] | None = None, log=print) -> dict:
    base = data_root() / "baselines" / category
    (base / "circuits").mkdir(parents=True, exist_ok=True)
    idx = load_index(category)
    all_recs = []
    reuse_jobs = []
    tc_jobs = []
    for row in idx:
        cache = runner.load_all_records(category, row["hash"])
        # a tool whose version changed was re-run; only the newest version of each (tool, track) counts (v1.2: the
        # superseded wall-clock-sliced B tools stay in the cache but no longer enter records or best_known)
        newest = {}
        for r in cache.values():
            k = (r["tool"], r["track"])
            if r.get("finished_at", "") >= newest.get(k, ("", None))[0]:
                newest[k] = (r.get("finished_at", ""), r.get("version"))
        cache = {ck: r for ck, r in cache.items() if r.get("version") == newest[(r["tool"], r["track"])][1]}
        recs = []
        for r in cache.values():
            # same budget for every tool: a result delivered after the budget does not count
            if r["status"] == "pass" and r.get("budget_s") and r.get("wall_tool_s", 0) > r["budget_s"]:
                r = {k: v for k, v in r.items() if k not in ("circuit", "costs")}
                r.update(status="timeout", reason=f"result delivered after the budget ({r['wall_tool_s']:.1f} s)")
            recs.append(r)
        pub = load_public(category, row["hash"])
        if "codespace_a2a_2q" in pub["tracks"]:
            a2a = [r for r in recs if r["track"] == "a2a_2q" and r["status"] == "pass"]
            if a2a:
                reuse_jobs.append((row["hash"], pub, a2a))
        if TOF_CLIFFORD in pub["tracks"] and not any(r["track"] == TOF_CLIFFORD for r in recs):
            other = [r for r in recs if r["status"] == "pass" and r.get("circuit") and "toffoli_count" in r.get("costs", {})]
            if other:
                tc_jobs.append((row["hash"], pub, other))
        all_recs.extend(recs)
    log(f"[aggregate] {len(all_recs)} cached records; re-verifying a2a circuits on codespace tracks for {len(reuse_jobs)} instances"
        + (f"; re-verifying circuits on {TOF_CLIFFORD} for {len(tc_jobs)} instances" if tc_jobs else ""))
    with mp.get_context("spawn").Pool(workers) as pool:
        for out in pool.imap_unordered(_reuse_codespace, reuse_jobs, chunksize=4):
            all_recs.extend(out)
        for out in pool.imap_unordered(_reuse_tof_clifford, tc_jobs, chunksize=2):
            all_recs.extend(out)
    by_inst = defaultdict(list)
    for r in all_recs:
        by_inst[r["hash"]].append(r)
    if category == "A":
        _add_qmap_unavailable(category, idx, by_inst)
    records = []
    best = []
    pub_by_key = defaultdict(list)
    for p in published or []:
        if p.get("instance_hash") and p.get("eligible_for_best_known"):
            pub_by_key[(p["instance_hash"], p["track"])].append(p)
    for row in idx:
        h = row["hash"]
        recs = sorted(by_inst.get(h, []), key=lambda r: (r["track"], r["tool"]))
        circ_file = base / "circuits" / f"{hash_hex(h)}.jsonl.gz"
        with gzip.open(circ_file, "wt", encoding="utf-8") as gz:
            for r in recs:
                if r.get("circuit"):
                    gz.write(json.dumps({"cache_key": r["cache_key"], "circuit": r["circuit"], "output_map": r.get("output_map"),
                                         **{k: r[k] for k in ("initial_layout", "outputs", "estimator") if r.get(k) is not None}},
                                        sort_keys=True) + "\n")
        pub = load_public(category, h)
        for track in pub["tracks"]:
            tr = [r for r in recs if r["track"] == track]
            ok = [r for r in tr if r["status"] == "pass"]
            metric = pub["tracks"][track]["metric"]
            tie = "two_qubit_depth" if category == "A" else \
                ({"swaps": "two_qubit_depth", "two_qubit_depth": "swaps"}.get(metric, "width") if category == "C" else "width")
            cands = [(r["costs"][metric], r["costs"].get(tie, 0), r["tool"], "baseline", r) for r in ok]
            for p in pub_by_key.get((h, track), []):
                cands.append((p["value"], 10 ** 9, p["label"], "published", p))
            if not cands:
                best.append({"instance_id": row["id"], "hash": h, "track": track, "value": None, "source": None,
                             "note": "no verified baseline"})
                continue
            cands.sort(key=lambda c: (c[0], c[1], c[2]))
            v, _, label, kind, obj = cands[0]
            ties = sorted({c[2] for c in cands if c[0] == v})
            entry = {"instance_id": row["id"], "hash": h, "track": track, "metric": metric, "value": v, "source_kind": kind, "source": label,
                     "ties": ties, "best_baseline_value": min((c[0] for c in cands if c[3] == "baseline"), default=None)}
            if kind == "baseline":
                entry["verified"] = True
                entry["circuit_path"] = f"baselines/{category}/best_circuits/{hash_hex(h)}/{track}"
                _materialize(base / "best_circuits" / hash_hex(h), track, obj)
            else:
                entry["verified"] = False
                entry["reference"] = obj["reference"]
            cur_ver = {r["tool"]: r.get("version") for r in recs}
            ext = [r for r in runner.load_cache(f"{category}-curve", h).values()
                   if r["track"] == track and r["status"] == "pass" and r.get("budget_s", 0) > 60
                   and cur_ver.get(r["tool"], r.get("version")) == r.get("version")
                   and not (r.get("budget_s") and r.get("wall_tool_s", 0) > r["budget_s"])]
            if ext:
                e = min(ext, key=lambda r: r["costs"][metric])
                if e["costs"][metric] < (entry["value"] if entry["value"] is not None else float("inf")):
                    entry["extended_10x"] = {"value": e["costs"][metric], "tool": e["tool"], "budget_s": e["budget_s"],
                                             "note": "10x-budget reference; not part of best_known"}
            best.append(entry)
        est = runner.concurrency_estimates()
        for r in recs:
            slim = {k: v for k, v in r.items() if k not in ("circuit", "trace")}
            slim["instance_id"] = row["id"]           # the index is authoritative (ids renamed in a data version)
            if "concurrency" not in slim and r.get("cache_key") in est:
                slim["concurrency_estimate"] = {"concurrent_runner_jobs_at_start": est[r["cache_key"]],
                                                "method": "reconstructed from finished_at - wall_total_s of all cached "
                                                          "runner jobs (1 s resolution); not recorded at run time"}
            if r.get("circuit"):
                slim["circuit_path"] = f"baselines/{category}/circuits/{hash_hex(h)}.jsonl.gz#{r['cache_key']}"
            records.append(slim)
    with open(base / "records.jsonl", "w", encoding="utf-8") as f:
        for r in sorted(records, key=lambda r: (r["instance_id"], r["track"], r["tool"])):
            f.write(json.dumps(r, sort_keys=True) + "\n")
    with open(base / "best_known.jsonl", "w", encoding="utf-8") as f:
        for b in sorted(best, key=lambda b: (b["instance_id"], b["track"])):
            f.write(json.dumps(b, sort_keys=True) + "\n")
    summary = {"records": len(records), "best_known": len(best)}
    dump_json(summary, base / "aggregate_summary.json")
    return summary


def _materialize(d, track: str, rec: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    c = Circuit.from_json(rec["circuit"])
    extra = {k: rec[k] for k in ("initial_layout", "outputs", "estimator") if rec.get(k) is not None}
    (d / f"{track}.json").write_text(json.dumps({"tool": rec["tool"], "cache_key": rec["cache_key"], "output_map": rec.get("output_map"),
                                                 "costs": rec["costs"], "circuit": rec["circuit"], **extra}, sort_keys=True) + "\n")
    if any(g == "measure" or g.startswith("c:") or g in ("cu", "prep_psi", "prep_phi", "mbu") for g, _, _ in c.gates):
        return                  # dynamic / oracle circuits: qbank JSON is the canonical format (QASM3/QPY not written)
    (d / f"{track}.qasm").write_text(c.to_qasm3())
    (d / f"{track}.qpy").write_bytes(c.to_qpy_bytes())
    if all(g in STIM_OK for g, _, _ in c.gates):        # stim format only for Clifford circuits (category A)
        (d / f"{track}.stim").write_text(str(c.to_stim()) + "\n")


QMAP_HEUR = "mqt.qmap.synthesize_clifford(heuristic)"


def _add_qmap_unavailable(category, idx, by_inst):
    """Where QMAP's heuristic was not run, record it as unavailable (deterministic SIGSEGV; evidence referenced)."""
    evidence = sorted({r["instance_id"] for rs in by_inst.values() for r in rs if r["tool"] == QMAP_HEUR and r["status"] == "crash"})
    for row in idx:
        pub = load_public(category, row["hash"])
        recs = by_inst[row["hash"]]
        if any(r["tool"] == QMAP_HEUR for r in recs):
            continue
        spec = pub["tracks"]["a2a_2q"]
        recs.append({"category": category, "instance_id": row["id"], "hash": row["hash"], "track": "a2a_2q", "tool": QMAP_HEUR,
                     "version": "mqt.qmap==3.10.0", "config": {"heuristic": True}, "budget_s": None, "seed": None,
                     "cache_key": f"qmap-unavailable-{row['hash'][7:23]}", "status": "unavailable",
                     "reason": ("not re-run: MQT QMAP 3.10.0 heuristic Clifford synthesis segfaults deterministically on the "
                                "Phase-0 machine (SIGSEGV in clifford_synthesis.abi3.so; wheels 3.3.1-3.10.0 and a source build, "
                                f"phase0/logs/qmap_isolation_loop.txt); crashed on every one of the {len(evidence)} instances "
                                f"where it was run in this baseline run: {', '.join(evidence)}")})
