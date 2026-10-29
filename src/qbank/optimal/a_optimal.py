"""Known optima / bounds for category A.

Kinds (never mixed in reports):
  cnot_model_optimum   MQT QECC exact synthesis (z3) for CSS states: |0>/|+> initialisation + CNOT-only network,
                       objective = number of CNOTs; `proven` is the tool's proven_optimal flag (all smaller bounds UNSAT).
                       This is an UPPER bound on the true two-qubit optimum over all Clifford circuits.
  clifford_completion_upper_bound  MQT QMAP SAT synthesis (two_qubit_gates) of ONE Clifford unitary completing the target
                       state's tableau (n <= 3 only): optimal for that unitary, only an UPPER bound for the state (e.g.
                       rand_stab n3 s40308: QMAP 3, stim/rustiq/pytket 1).
  lower_bound_attained analytic lower bound that a known circuit attains (Iceberg / GHZ: n-1).
Each optimum circuit is re-verified with the qbank checkers before it is recorded.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import time
from pathlib import Path

from ..core.canon import dump_json
from ..core.instance import data_root, load_index, load_private, load_public
from ..baselines import runner

SCRIPT_CSS = r"""
import json, signal, sys, time
import numpy as np
from mqt.qecc.codes.core.pauli import CheckMatrix
from mqt.qecc.circuit_synthesis.exact.search import synthesize_isometry_exact
from mqt.qecc.circuit_synthesis.exact.types import TargetKind, Objective, SynthesisStatus
d = json.loads(sys.stdin.read())
signal.alarm(int(3 * d["timeout"] + 60))   # self-destruct even if the parent pool is killed (no orphans)
n = d["n"]
hx = np.zeros((len(d["hx"]), n), dtype=np.int8)
for i, r in enumerate(d["hx"]):
    hx[i, r] = 1
upper = d["upper"]
if upper is None:
    # independent upper bound: MQT QECC heuristic CNOT count for this code (|0>/|+> init + CNOTs)
    from mqt.qecc import CSSCode
    from mqt.qecc.circuit_synthesis import heuristic_prep_circuit
    upper = int(heuristic_prep_circuit(CSSCode(Hx=hx, Hz=np.zeros((0, n), dtype=np.int8)), optimize_depth=False).circ.num_cnots())
t = time.time()
res = synthesize_isometry_exact(target=CheckMatrix(hx, pauli_type="X"), target_kind=TargetKind.CSS_STATE,
                                objective=Objective.GATE_COUNT, lower_bound=0, upper_bound=upper,
                                use_exponential_backoff=True, min_timeout=1, timeout=d["timeout"])
out = {"upper_bound_used": upper, "status": res.status.value, "gate_count": res.gate_count, "proven_optimal": bool(getattr(res, "proven_optimal", False)),
       "message": res.message, "time_s": time.time() - t}
if res.circuit is not None:
    from qiskit import qasm2
    out["qasm"] = qasm2.dumps(res.circuit.to_qiskit_circuit())
print("QBANK_RESULT " + json.dumps(out))
"""


def _run_css(args):
    import subprocess
    import sys
    iid, h, pub, upper, timeout = args
    env = {**os.environ, **runner.THREAD_ENV}
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-c", SCRIPT_CSS], input=json.dumps({"n": pub["n"], "hx": pub["hx"], "upper": upper,
                                                                                  "timeout": timeout}),
                           capture_output=True, text=True, timeout=timeout * 3 + 120, env=env)
    except subprocess.TimeoutExpired:
        return {"instance_id": iid, "hash": h, "track": "a2a_2q", "kind": "cnot_model_optimum", "status": "timeout",
                "value": None, "proven": False, "time_s": time.time() - t0}
    line = [l for l in p.stdout.splitlines() if l.startswith("QBANK_RESULT ")]
    if not line:
        return {"instance_id": iid, "hash": h, "track": "a2a_2q", "kind": "cnot_model_optimum",
                "status": ("timeout" if p.returncode == -14 else "crash") if p.returncode < 0 else "tool_error",
                "value": None, "proven": False,                                  # -14 = SIGALRM: our self-destruct timer
                "returncode": p.returncode, "reason": p.stderr[-400:], "time_s": time.time() - t0}
    r = json.loads(line[0][len("QBANK_RESULT "):])
    rec = {"instance_id": iid, "hash": h, "track": "a2a_2q", "kind": "cnot_model_optimum",
           "solver": "mqt.qecc 2.0.0 exact.synthesize_isometry_exact(CSS_STATE, GATE_COUNT, exponential backoff, z3)",
           "upper_bound_given": upper, "timeout_s_per_bound": timeout, **{k: v for k, v in r.items() if k != "qasm"}}
    if r.get("qasm"):
        from qiskit import qasm2
        from ..categories.A.instances import verify
        from ..core.circuit import Circuit
        from ..core.costs import costs
        c = Circuit.from_qiskit(qasm2.loads(r["qasm"]), clifford_only=True)
        v = verify(pub, "a2a_2q", c)
        rec["verified"] = v.status == "pass"
        rec["value"] = costs(v.circuit)["two_qubit_gates"] if v.status == "pass" else None
        rec["circuit"] = v.circuit.to_json() if v.status == "pass" else None
        rec["proven"] = bool(r["proven_optimal"] and rec["verified"])
    return rec


def best_baseline(h: str, track: str = "a2a_2q") -> int | None:
    vals = [r["costs"]["two_qubit_gates"] for r in runner.load_all_records("A", h).values()
            if r["track"] == track and r["status"] == "pass"]
    return min(vals) if vals else None


def run(max_n: int = 12, timeout: int = 1800, workers: int = 8, log=print) -> list[dict]:
    out_path = data_root() / "optimal" / "A.jsonl"
    done = {}
    if out_path.exists():
        for l in out_path.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                done[(r["instance_id"], r["kind"])] = r
    jobs = []
    results = list(done.values())
    for row in load_index("A"):
        pub = load_public("A", row["hash"])
        priv = load_private("A", row["id"])
        ko = priv["private"].get("known_optimal")
        if ko and (row["id"], "lower_bound_attained") not in done:
            results.append({"instance_id": row["id"], "hash": row["hash"], "track": "a2a_2q", "kind": "lower_bound_attained",
                            "value": ko["value"], "proven": True, "reason": ko["reason"], "verified": None})
        if pub["task"] == "css_logical_zero" and pub["n"] <= max_n and (row["id"], "cnot_model_optimum") not in done:
            jobs.append((row["id"], row["hash"], pub, best_baseline(row["hash"]), timeout))
        if pub["task"] == "stabilizer_state" and pub["n"] <= 3 and (row["id"], "clifford_completion_upper_bound") not in done:
            recs = [r for r in runner.load_all_records("A", row["hash"]).values()
                    if r["tool"].startswith("mqt.qmap.synthesize_clifford(SAT") and r["status"] == "pass"]
            if recs:
                r = recs[0]
                best = min(recs, key=lambda x: x["costs"]["two_qubit_gates"])
                results.append({"instance_id": row["id"], "hash": row["hash"], "track": "a2a_2q", "kind": "clifford_completion_upper_bound",
                                "value": best["costs"]["two_qubit_gates"], "proven": False, "verified": True,
                                "solver": best["tool"] + " " + best["version"],
                                "note": "QMAP's SAT optimum for ONE Clifford unitary completing the state's tableau; the state itself "
                                        "can need fewer two-qubit gates (other Clifford completions), so this is an upper bound only"})
    log(f"[optimal] {len(jobs)} CNOT-model SAT jobs (n <= {max_n}), timeout {timeout}s per bound, {workers} workers")
    with mp.get_context("spawn").Pool(workers) as pool:
        for rec in pool.imap_unordered(_run_css, jobs):
            results.append(rec)
            log(f"  {rec['instance_id']}: {rec.get('status')} value={rec.get('value')} proven={rec.get('proven')} ({rec.get('time_s', 0):.0f}s)")
            _write(out_path, results)
    _write(out_path, results)
    return results


def _write(path: Path, results: list[dict]) -> None:
    """Atomic rewrite (temporary file + rename): an error can never leave a truncated file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in sorted(results, key=lambda r: (r["instance_id"], r.get("kind", ""))))
    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
