"""Baseline reproducibility: re-run 20 randomly drawn baseline records per category.

Deterministic tools must reproduce the stored circuit exactly (gate by gate, plus layout / output map / outputs);
seeded anytime tools are re-run for the recorded trial seed only. Tools whose result depends on wall-clock time
(OLSQ2, QMAP's exact Clifford synthesis) cannot be reproduced bit-for-bit under a different machine load and are
excluded from the draw (listed in the output). Since v1.2 the B tools SAT pebbling and XAG + MC use SAT conflict
budgets instead of wall-clock slices and are deterministic; the draw always contains one record of each of them and
of the mockturtle XAG tool (MUST_INCLUDE), the rest is drawn at random.
Tools built on floating-point linear algebra (qclib's SVD-based state preparation, FLOAT_DEPENDENT) give gate angles
that depend on the platform's LAPACK/Accelerate build: after the macOS 27 upgrade (10-28) re-runs differ from the
stored circuits in gates and in cost (10-29 sample: 0 to about 10% more two-qubit gates, 3 -> 5 CX on one small state). For them a re-run counts as reproduced when
it passes the same checker; the cost difference is reported in the note, not counted as a failure (user decision
10-28). Reference values stay those of the stored, verified circuits. Every other tool must reproduce gate by gate.
Outputs: data/v1/baselines/<C>/repro.jsonl and results/<date>/<C>_repro.csv.
"""
from __future__ import annotations

import gzip
import json
import random
import time

from ..core.circuit import Circuit
from ..core.instance import data_root, load_public

TIME_DEPENDENT = ("OLSQ2", "mqt.qmap.synthesize_clifford")
FLOAT_DEPENDENT = {"D": ("qclib ",)}
MUST_INCLUDE = {"B": ("XAG + MC", "XAG MC cut rewriting", "pebbling SAT")}
N_SAMPLE = 20


def _records(cat):
    p = data_root() / "baselines" / cat / "records.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _stored(rec) -> dict:
    path, key = rec["circuit_path"].split("#")
    with gzip.open(data_root() / path, "rt") as f:
        for line in f:
            d = json.loads(line)
            if d["cache_key"] == key:
                return d
    raise KeyError(key)


def eligible(rec) -> bool:
    return (rec["status"] == "pass" and rec.get("circuit_path") and not rec["tool"].startswith(("published:", "qecirc:"))
            and "reused" not in rec["tool"] and not any(rec["tool"].startswith(t) for t in TIME_DEPENDENT))


def _rerun(cat, rec, pub):
    tool, track, seed = rec["tool"], rec["track"], rec["seed"]
    meta = rec.get("meta") or {}
    past = time.monotonic() - 1                            # anytime tools: exactly one trial
    if cat == "A":
        from . import tools_a as T
        if T.is_anytime(tool):
            base = T.A2A_TOOLS["rustiq.stabilizer_state_synthesis"]
            cands = base(pub, "a2a_2q", meta["trial_seed"], past)
            if "+sabre" in tool:
                rc, om = T.sabre_route(cands[0]["circuit"], pub["tracks"][track]["connectivity"]["edges"], seed)
                cands = [{"circuit": rc, "output_map": om}]
            return cands
        return T.tools_for(pub, track)[tool](pub, track, seed, time.monotonic() + rec["budget_s"])
    if cat == "B":
        from . import tools_b as T
        return T.tool_fn(tool)(pub, track, seed, time.monotonic() + rec["budget_s"])
    if cat == "C":
        from . import tools_c as T
        if tool == "qiskit LightSABRE (anytime)":
            return T.t_sabre(pub, track, meta["trial_seed"], past)
        if tool.startswith("qiskit LightSABRE + block"):
            return T.t_sabre_shuffle_trial(pub, track, seed, meta["block_shuffle_trial"])
        return T.C_TOOLS[tool](pub, track, seed, time.monotonic() + rec["budget_s"])
    if cat == "D":
        from . import tools_d as T
        cands = T.D_TOOLS[tool](pub, track, seed, time.monotonic() + rec["budget_s"])
        edges = pub["tracks"][track].get("coupling_edges")
        if edges is not None:
            cands = [r for cd in cands for r in T.route_line(cd, pub["n"], edges, seed)]
        return cands
    raise ValueError(f"unknown category {cat}")


def float_dependent(cat, tool) -> bool:
    return tool.startswith(FLOAT_DEPENDENT.get(cat, ()))


def _verified(cat, cand, pub, track) -> bool:
    from ..categories.D.instances import verify
    return verify(pub, track, cand["circuit"], cand.get("output_map")).status == "pass"


def _cost_drift(cand, rec) -> str:
    """Cost difference of the re-run candidate that passed (10-29: not simply the first candidate)."""
    from ..core.costs import costs
    c = costs(cand["circuit"])
    d = {k: [rec["costs"].get(k), v] for k, v in c.items() if v != rec["costs"].get(k)}
    return f"cost differs from stored (stored, rerun): {d}" if d else "same costs"


def _matches(cat, cand, stored, pub, track, rec=None) -> bool:
    if rec is not None and float_dependent(cat, rec["tool"]):
        return _verified(cat, cand, pub, track)
    want = Circuit.from_json(stored["circuit"])
    c = cand["circuit"]
    if cat == "A":
        from ..categories.A.instances import verify
        v = verify(pub, track, c, cand.get("output_map"))
        return v.status == "pass" and v.circuit.gates == want.gates and \
            (cand.get("output_map") or None) == (stored.get("output_map") or None)
    if c.gates != want.gates:
        return False
    for k in ("initial_layout", "output_map", "outputs", "estimator"):
        a, b = cand.get(k), stored.get(k)
        if (a is not None or b is not None) and json.loads(json.dumps(a)) != json.loads(json.dumps(b)):
            return False
    return True


def _checker_hash(cat: str) -> str:
    """SHA-256 over the source files of the category's checker (contracts/ and categories/<C>/instances.py)."""
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    h = hashlib.sha256()
    for p in sorted((root / "contracts").glob("*.py")) + [root / "categories" / cat / "instances.py", root / "core" / "circuit.py"]:
        h.update(p.name.encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def run(cat: str, out_dir=None, log=print) -> list[dict]:
    recs = _records(cat)
    pool = [r for r in recs if eligible(r)]
    excluded = sorted({r["tool"] for r in recs if r["status"] == "pass" and any(r["tool"].startswith(t) for t in TIME_DEPENDENT)})
    rng = random.Random(f"repro-{cat}-20260926")
    sample = []
    for prefix in MUST_INCLUDE.get(cat, ()):
        cands = [r for r in pool if r["tool"].startswith(prefix)]
        if cands:
            sample.append(rng.choice(cands))
    rest = [r for r in pool if r not in sample]
    sample += rng.sample(rest, min(N_SAMPLE - len(sample), len(rest)))
    rows = []
    for rec in sample:
        pub = load_public(cat, rec["hash"])
        stored = _stored(rec)
        t0 = time.time()
        try:
            cands = _rerun(cat, rec, pub)
            hit = next((cd for cd in cands if _matches(cat, cd, stored, pub, rec["track"], rec)), None)
            ok = hit is not None
            # 10-29 (Codex review): say which rule was applied -- gate-identical reproduction, or (FLOAT_DEPENDENT
            # tools) a re-run that passes the checker, with the cost of the candidate that passed
            match = None if not ok else ("reverified" if float_dependent(cat, rec["tool"]) else "gate_identical")
            note = "no rerun candidate equals the stored circuit" if not ok else \
                (_cost_drift(hit, rec) if match == "reverified" else "")
        except Exception as e:
            ok, match, note = False, None, f"{type(e).__name__}: {str(e)[:120]}"
        rows.append({"instance_id": rec["instance_id"], "track": rec["track"], "tool": rec["tool"], "seed": rec["seed"],
                     "trial_seed": (rec.get("meta") or {}).get("trial_seed"), "recorded_cost": rec["costs"],
                     "reproduced": ok, "match": match, "note": note, "seconds": round(time.time() - t0, 1)})
        log(f"[repro {cat}] {rec['instance_id']} {rec['tool']} {rec['track']}: {'OK' if ok else 'MISMATCH ' + note}")
    import datetime
    res = {"category": cat, "n": len(rows), "reproduced": sum(r["reproduced"] for r in rows), "excluded_tools": excluded,
           "gate_identical": sum(r.get("match") == "gate_identical" for r in rows),
           "reverified": sum(r.get("match") == "reverified" for r in rows),
           "run_date": datetime.date.today().isoformat(), "checker_sha256": _checker_hash(cat), "rows": rows}
    (data_root() / "baselines" / cat / "repro.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    if out_dir is not None:
        import csv
        with open(out_dir / f"{cat}_repro.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["instance", "track", "tool", "seed", "trial_seed", "reproduced", "note"])
            for r in rows:
                w.writerow([r["instance_id"], r["track"], r["tool"], r["seed"], r["trial_seed"], r["reproduced"], r["note"]])
    return rows
