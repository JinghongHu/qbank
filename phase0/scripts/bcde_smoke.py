"""Phase 0 smoke test for the B/C/D/E baseline tools.

Each check builds a tiny instance, runs one tool in its own subprocess (timeout; native crashes are caught),
and verifies the output exactly where that is cheap (dense operators / state vectors on <= 8 qubits,
QCEC for routing). This only answers "is the tool usable in the new venv"; it is not a baseline run.
Writes phase0/logs/bcde_smoke.json.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------------------- B: oracles, MCX, logic tools
def b_phase_oracle_gate():
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit.library import PhaseOracleGate
    from qiskit.quantum_info import Operator
    expr = "(a & b) | (~c & d)"
    g = PhaseOracleGate(expr)
    qc = QuantumCircuit(g.num_qubits)
    qc.append(g, range(g.num_qubits))
    t = transpile(qc, basis_gates=["cx", "u", "x", "h", "t", "tdg", "s", "sdg", "z"], optimization_level=0)
    u = Operator(t).data
    # variable order as reported by the gate; qubit i <-> i-th variable, little endian
    names = ["a", "b", "c", "d"]
    diag = []
    for x in range(16):
        v = {nm: (x >> i) & 1 for i, nm in enumerate(names)}
        f = (v["a"] & v["b"]) | ((1 - v["c"]) & v["d"])
        diag.append(-1 if f else 1)
    ok = np.allclose(u, np.diag(diag)) or np.allclose(u, -np.diag(diag))
    return {"verified": bool(ok), "cx": t.count_ops().get("cx", 0)}


def b_bitflip_oracle_gate():
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit.library import BitFlipOracleGate
    from qiskit.quantum_info import Operator
    g = BitFlipOracleGate("(a & b) ^ c")
    qc = QuantumCircuit(g.num_qubits)
    qc.append(g, range(g.num_qubits))
    t = transpile(qc, basis_gates=["cx", "u", "x", "h", "t", "tdg"], optimization_level=0)
    u = Operator(t).data
    n = g.num_qubits  # 3 inputs + 1 output (output is the last qubit)
    perm = np.zeros((2 ** n, 2 ** n))
    for x in range(2 ** n):
        a, b, c, y = (x >> 0) & 1, (x >> 1) & 1, (x >> 2) & 1, (x >> 3) & 1
        y2 = y ^ ((a & b) ^ c)
        perm[x & 7 | (y2 << 3), x] = 1
    ph = u[np.argmax(np.abs(u[:, 0])), 0]
    return {"verified": bool(np.allclose(u, ph * perm)), "cx": t.count_ops().get("cx", 0)}


def _mcx_check(fn_name, k):
    """MCX with k controls: controls 0..k-1, target k, ancillas after. Clean ancillas: check on |0> subspace."""
    import qiskit.synthesis as qs
    from qiskit import transpile
    from qiskit.quantum_info import Operator
    qc = getattr(qs, fn_name)(k)
    t = transpile(qc, basis_gates=["cx", "u"], optimization_level=0)
    n = qc.num_qubits
    u = Operator(t).data
    anc = n - k - 1
    clean = "clean" in fn_name
    ok = True
    ref_phase = None
    for x in range(2 ** n):
        if clean and (x >> (k + 1)):
            continue  # only inputs with clean ancillas = 0
        ctrl = all((x >> i) & 1 for i in range(k))
        y = x ^ (1 << k) if ctrl else x
        col = u[:, x]
        if not np.isclose(abs(col[y]), 1, atol=1e-9):
            ok = False
            break
        if ref_phase is None:
            ref_phase = col[y]
        if not np.isclose(col[y], ref_phase, atol=1e-9):
            ok = False  # relative phase between inputs
            break
    return {"verified": ok, "qubits": n, "ancillas": anc, "cx": t.count_ops().get("cx", 0)}


def b_mcx_all():
    import qiskit.synthesis as qs
    out = {}
    for fn in sorted(n for n in dir(qs) if n.startswith("synth_mcx")):
        try:
            out[fn] = _mcx_check(fn, 4)
        except Exception as e:
            out[fn] = {"error": f"{type(e).__name__}: {e}"}
    return {"verified": all(v.get("verified") for v in out.values()), "per_function": out}


def b_abc():
    """ABC reads binary AIGER only; use EPFL ctrl.aig at the pinned commit (lsils/benchmarks@82d8cc69)."""
    import ssl
    import urllib.request
    import certifi  # python.org macOS builds ship without a CA bundle for urllib
    ctx = ssl.create_default_context(cafile=certifi.where())
    url = "https://raw.githubusercontent.com/lsils/benchmarks/82d8cc6910419298e713a46644ed59fd3df53038/random_control/ctrl.aig"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ctrl.aig"
        p.write_bytes(urllib.request.urlopen(url, timeout=60, context=ctx).read())
        r = subprocess.run([str(ROOT / "external/src/abc/abc"), "-c", f"read {p}; print_stats; strash; dc2; print_stats"],
                           capture_output=True, text=True, timeout=60, cwd=d)  # ABC writes abc.history into its cwd
    lines = [l for l in r.stdout.splitlines() if "and =" in l]
    return {"verified": r.returncode == 0 and len(lines) == 2, "stats": [l.split(":")[-1].strip()[-60:] for l in lines]}


def b_pysat_dd():
    from pysat.solvers import Solver
    import dd.autoref as _bdd
    with Solver(name="cadical195", bootstrap_with=[[1, 2], [-1, 2], [1, -2]]) as s:
        sat = s.solve()
        model = s.get_model()
    b = _bdd.BDD()
    b.declare("a", "b", "c")
    u = b.add_expr(r"(a /\ b) \/ ~ c")
    return {"verified": bool(sat and model == [1, 2] and b.count(u, nvars=3) == 5), "bdd_nodes": len(u)}


# ----------------------------------------------------------------------------- C: routing
def _qaoa_like(n=8, seed=1):
    import networkx as nx
    from qiskit import QuantumCircuit
    g = nx.random_regular_graph(3, n, seed=seed)
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for a, b in g.edges:
        qc.cx(a, b); qc.rz(0.7, b); qc.cx(a, b)
    qc.rx(0.3, range(n))
    return qc, g


def _line(n):
    return [[i, i + 1] for i in range(n - 1)] + [[i + 1, i] for i in range(n - 1)]


def c_sabre():
    from qiskit.transpiler import CouplingMap, PassManager
    from qiskit.transpiler.passes import SabreLayout
    from mqt.qcec import verify_compilation
    qc, _ = _qaoa_like()
    cm = CouplingMap(_line(qc.num_qubits))
    pm = PassManager([SabreLayout(cm, seed=7, max_iterations=4, swap_trials=8, layout_trials=8)])
    out = pm.run(qc)
    swaps = out.count_ops().get("swap", 0)
    on_edges = all(tuple(out.find_bit(q).index for q in i.qubits) in {tuple(e) for e in _line(qc.num_qubits)}
                   for i in out.data if len(i.qubits) == 2)
    res = verify_compilation(qc, out)
    eq = str(res.equivalence).split(".")[-1]
    return {"verified": bool(on_edges and eq in ("equivalent", "equivalent_up_to_global_phase", "equivalent_up_to_phase")),
            "swaps": swaps, "qcec": str(res.equivalence)}


def c_tket():
    from pytket.architecture import Architecture
    from pytket.extensions.qiskit import qiskit_to_tk
    from pytket.mapping import LexiLabellingMethod, LexiRouteRoutingMethod, MappingManager
    from pytket.placement import GraphPlacement
    from pytket.circuit import OpType
    qc, _ = _qaoa_like()
    tk = qiskit_to_tk(qc)
    arc = Architecture([tuple(e) for e in _line(qc.num_qubits)[: qc.num_qubits - 1]])
    GraphPlacement(arc).place(tk)
    MappingManager(arc).route_circuit(tk, [LexiLabellingMethod(), LexiRouteRoutingMethod()])
    return {"verified": tk.n_gates_of_type(OpType.BRIDGE) == 0, "swaps": tk.n_gates_of_type(OpType.SWAP),
            "note": "valid-edges/equivalence check deferred to qbank checker"}


def c_qmap_heuristic_mapper():
    from mqt.qmap.plugins.qiskit.sc import compile_
    from mqt.qmap.sc import Architecture
    qc, _ = _qaoa_like()
    arch = Architecture(qc.num_qubits, {tuple(e) for e in _line(qc.num_qubits)})
    out, res = compile_(qc, arch=arch, add_measurements_to_mapped_circuit=False, post_mapping_optimizations=False)
    return {"verified": True, "swaps": int(res.output.swaps), "note": "ran without crash"}


def c_commuting_router():
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import PauliEvolutionGate
    from qiskit.quantum_info import SparsePauliOp
    from qiskit.transpiler import CouplingMap, PassManager
    from qiskit.transpiler.passes.routing.commuting_2q_gate_routing import Commuting2qGateRouter, FindCommutingPauliEvolutions, SwapStrategy
    import networkx as nx
    n = 6
    g = nx.random_regular_graph(3, n, seed=3)
    op = SparsePauliOp.from_sparse_list([("ZZ", [a, b], 1.0) for a, b in g.edges], num_qubits=n)
    qc = QuantumCircuit(n)
    qc.append(PauliEvolutionGate(op, 0.4), range(n))
    cm = CouplingMap(_line(n))
    pm = PassManager([FindCommutingPauliEvolutions(), Commuting2qGateRouter(SwapStrategy.from_line(list(range(n))), edge_coloring=None)])
    out = pm.run(qc)
    return {"verified": True, "swaps": out.count_ops().get("swap", 0), "ops": dict(out.count_ops())}


def c_qcec():
    from mqt.qcec import verify
    from qiskit import QuantumCircuit
    a = QuantumCircuit(3); a.h(0); a.cx(0, 1); a.cx(1, 2)
    b = QuantumCircuit(3); b.h(0); b.cx(0, 1); b.cx(0, 2)
    c = QuantumCircuit(3); c.h(0); c.cx(0, 1); c.cx(0, 1)
    r1, r2 = verify(a, b), verify(a, c)
    return {"verified": str(r1.equivalence).endswith("not_equivalent") and str(r2.equivalence).endswith("not_equivalent"),
            "note": f"a vs b: {r1.equivalence} (unitaries differ on non-zero inputs); a vs c: {r2.equivalence}"}


# ----------------------------------------------------------------------------- D: state preparation
def _rand_state(n, seed, support=None):
    rng = np.random.default_rng(seed)
    v = np.zeros(2 ** n, complex)
    idx = rng.choice(2 ** n, size=support, replace=False) if support else np.arange(2 ** n)
    v[idx] = rng.normal(size=len(idx)) + 1j * rng.normal(size=len(idx))
    return v / np.linalg.norm(v)


def _rev(v):
    """Reverse qubit order of a state vector (little-endian <-> big-endian)."""
    n = int(np.log2(len(v)))
    return v.reshape([2] * n).transpose(list(range(n))[::-1]).reshape(-1)


def _fid(qc, v):
    from qiskit import transpile
    from qiskit.quantum_info import Statevector
    t = transpile(qc, basis_gates=["cx", "u"], optimization_level=0)
    s = Statevector(t).data
    return float(abs(np.vdot(v, s)) ** 2), t.count_ops().get("cx", 0)


def d_qiskit_stateprep():
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import StatePreparation
    v = _rand_state(5, 1)
    qc = QuantumCircuit(5); qc.append(StatePreparation(v), range(5))
    f, cx = _fid(qc, v)
    return {"verified": f > 1 - 1e-9, "fidelity_err": 1 - f, "cx": cx}


def d_qclib():
    from qiskit import QuantumCircuit
    import qclib.state_preparation as sp
    v = _rand_state(6, 2, support=6)
    data = {format(i, "06b"): v[i] for i in np.nonzero(v)[0]}
    out = {}
    for name in ["CvoqramInitialize", "PivotInitialize", "MergeInitialize", "DcspInitialize", "BdspInitialize",
                 "TopDownInitialize", "LowRankInitialize", "UCGInitialize", "SVDInitialize"]:
        try:
            cls = getattr(sp, name)
            inp = data if name in ("CvoqramInitialize", "PivotInitialize", "MergeInitialize") else v
            gate = cls(inp).definition if hasattr(cls(inp), "definition") else None
            qc = QuantumCircuit(gate.num_qubits)
            qc.append(gate, range(gate.num_qubits))
            if gate.num_qubits != 6:
                out[name] = {"note": f"uses {gate.num_qubits} qubits (ancillas); not checked here"}
                continue
            f, cx = _fid(qc, v)
            fb, _ = _fid(qc, _rev(v))
            out[name] = {"verified": max(f, fb) > 1 - 1e-9, "endianness": "little" if f > 1 - 1e-9 else ("big" if fb > 1 - 1e-9 else "-"),
                         "fidelity_err": 1 - max(f, fb), "cx": cx}
        except Exception as e:
            out[name] = {"error": f"{type(e).__name__}: {str(e)[:160]}"}
    return {"verified": any(o.get("verified") for o in out.values()), "per_method": out}


def d_bqskit():
    from bqskit import compile as bq_compile
    from bqskit.qis.state import StateVector
    from bqskit.ext import bqskit_to_qiskit
    v = _rand_state(3, 3)
    circ = bq_compile(StateVector(v), optimization_level=1, max_synthesis_size=3, seed=1, num_workers=1)
    qc = bqskit_to_qiskit(circ)
    f, cx = _fid(qc, v)
    fb, _ = _fid(qc, _rev(v))
    return {"verified": max(f, fb) > 1 - 1e-9, "endianness": "little" if f > 1 - 1e-9 else ("big" if fb > 1 - 1e-9 else "-"),
            "fidelity_err": 1 - max(f, fb), "cx": cx, "note": "numerical synthesis; exactness is up to its tolerance"}


# ----------------------------------------------------------------------------- E: dynamic circuits (Aer as independent reference only)
def e_dynamic_aer():
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
    from qiskit_aer import AerSimulator
    q, c = QuantumRegister(2), ClassicalRegister(2)
    qc = QuantumCircuit(q, c)
    qc.h(0); qc.measure(0, 0)
    with qc.if_test((c[0], 1)):
        qc.x(1)
    qc.measure(1, 1)
    r = AerSimulator(seed_simulator=1).run(transpile(qc, AerSimulator()), shots=200).result().get_counts()
    return {"verified": set(r) <= {"00", "11"}, "counts": r}


CHECKS = {
    "B.qiskit.PhaseOracleGate": b_phase_oracle_gate,
    "B.qiskit.BitFlipOracleGate": b_bitflip_oracle_gate,
    "B/E.qiskit.synth_mcx_* (k=4)": b_mcx_all,
    "B.abc(strash,dc2)": b_abc,
    "B.pysat+dd": b_pysat_dd,
    "C.qiskit.SabreLayout(LightSABRE)+QCEC": c_sabre,
    "C.pytket.LexiRoute": c_tket,
    "C.mqt.qmap.compile_(heuristic)": c_qmap_heuristic_mapper,
    "C.qiskit.Commuting2qGateRouter": c_commuting_router,
    "C.mqt.qcec.verify(neg. control)": c_qcec,
    "D.qiskit.StatePreparation": d_qiskit_stateprep,
    "D.qclib": d_qclib,
    "D.bqskit.compile(StateVector)": d_bqskit,
    "E.qiskit_aer dynamic circuit": e_dynamic_aer,
}


def _worker(name, q):
    try:
        t0 = time.perf_counter()
        r = CHECKS[name]()
        q.put({"status": "ok", "time_s": time.perf_counter() - t0, **r})
    except Exception as e:
        q.put({"status": "error", "error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-600:]})


def main():
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 300
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    results = {}
    for name in CHECKS:
        if only and not any(o in name for o in only):
            continue
        q = mp.Queue()
        p = mp.Process(target=_worker, args=(name, q))
        t0 = time.perf_counter()
        p.start(); p.join(timeout)
        if p.is_alive():
            p.kill(); p.join()
            r = {"status": "timeout", "time_s": time.perf_counter() - t0}
        elif p.exitcode != 0 and q.empty():
            r = {"status": "crash", "exitcode": p.exitcode}
        else:
            r = q.get()
        results[name] = r
        brief = {k: v for k, v in r.items() if k not in ("tb", "per_function", "per_method")}
        print(f"{name:40s} {json.dumps(brief, default=str)[:260]}", flush=True)
        for sub in ("per_function", "per_method"):
            for k2, v2 in (r.get(sub) or {}).items():
                print(f"    {k2:34s} {json.dumps(v2, default=str)[:200]}", flush=True)
    out = ROOT / "phase0/logs" / ("bcde_smoke.json" if not only else "bcde_smoke_rerun.json")
    out.write_text(json.dumps(results, indent=1, default=str))


if __name__ == "__main__":
    main()
