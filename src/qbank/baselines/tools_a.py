"""Category-A baseline tool adapters.

Each tool is a function(public, track, seed, deadline) -> list of candidate dicts
{"circuit": Circuit, "output_map": list|None, "meta": {...}}; the runner verifies every candidate with the
qbank checkers and keeps the best verified one. Tools only see the public part of an instance.
Anytime tools loop over seeds seed, seed+1, ... until the deadline and return every candidate they produced.
"""
from __future__ import annotations

import os
import time

import numpy as np

from ..core import gf2
from ..core.circuit import Circuit
from ..core.pauli import PauliRows
from ..categories.A.instances import targets_for

VERSIONS = {}


def _versions():
    if not VERSIONS:
        import importlib.metadata as md
        for d in ("qiskit", "stim", "rustiq", "mqt.qecc", "mqt.qmap", "pytket", "pytket-qiskit"):
            try:
                VERSIONS[d] = md.version(d)
            except md.PackageNotFoundError:
                VERSIONS[d] = None
        VERSIONS["rustiq"] = f"{VERSIONS['rustiq']}+qbank-seed-patch (rustiq@4250002, rustiq-core 0.0.11)"
    return VERSIONS


# ------------------------------------------------------------------ inputs derived from the public part
def synth_targets(public: dict, track: str) -> tuple[PauliRows, bool]:
    """Stabilizer generators the synthesis tools receive, and whether the target is under-constrained (codespace)."""
    contract = public["tracks"][track]["contract"]
    return targets_for(public, contract), contract == "codespace_state"


def stim_strings(rows: PauliRows) -> list[str]:
    return rows.to_strings()


def qiskit_labels(rows: PauliRows) -> list[str]:
    return [s[0] + s[1:][::-1] for s in rows.to_strings()]   # qiskit: qubit 0 rightmost


# ------------------------------------------------------------------ synthesis tools (all-to-all circuits)
def t_qiskit_from_stabilizers(public, track, seed, deadline):
    from qiskit.synthesis import synth_circuit_from_stabilizers
    rows, under = synth_targets(public, track)
    qc = synth_circuit_from_stabilizers(qiskit_labels(rows), allow_redundant=True, allow_underconstrained=under)
    return [{"circuit": Circuit.from_qiskit(qc, clifford_only=True)}]


def _stab_state(public, track):
    from qiskit.quantum_info import StabilizerState
    rows, under = synth_targets(public, track)
    if under:
        raise NotImplementedError("needs a full-rank stabilizer list")
    return StabilizerState.from_stabilizer_list(qiskit_labels(rows), allow_redundant=True)


def t_qiskit_stab_layers(public, track, seed, deadline):
    from qiskit.synthesis import synth_stabilizer_layers
    return [{"circuit": Circuit.from_qiskit(synth_stabilizer_layers(_stab_state(public, track)), clifford_only=True)}]


def t_qiskit_stab_depth_lnn(public, track, seed, deadline):
    from qiskit.synthesis import synth_stabilizer_depth_lnn
    return [{"circuit": Circuit.from_qiskit(synth_stabilizer_depth_lnn(_stab_state(public, track)), clifford_only=True)}]


def _clifford_tool(fn_name):
    def tool(public, track, seed, deadline):
        import qiskit.synthesis as qs
        cl = _stab_state(public, track).clifford
        return [{"circuit": Circuit.from_qiskit(getattr(qs, fn_name)(cl), clifford_only=True)}]
    return tool


def _stim_tableau(public, track):
    import stim
    rows, under = synth_targets(public, track)
    return stim.Tableau.from_stabilizers([stim.PauliString(s) for s in stim_strings(rows)], allow_redundant=True,
                                         allow_underconstrained=under)


def _stim_tool(method):
    def tool(public, track, seed, deadline):
        t = _stim_tableau(public, track)
        return [{"circuit": Circuit.from_stim(t.to_circuit(method), public["n"])}]
    return tool


def t_rustiq(public, track, seed, deadline):
    import rustiq
    rows, under = synth_targets(public, track)
    if under:
        raise NotImplementedError("rustiq stabilizer_state_synthesis needs n independent stabilizers")
    strings = [s[1:] for s in stim_strings(rows)]
    out = []
    i = 0
    slowest = 0.0
    while True:
        t0 = time.monotonic()
        os.environ["QBANK_RUSTIQ_SEED"] = f"{seed + i}:{time.perf_counter_ns()}"
        gates = rustiq.stabilizer_state_synthesis(strings, rustiq.Metric("count"), syndrome_iter=100)
        out.append({"circuit": Circuit.from_rustiq(gates, public["n"]), "meta": {"trial_seed": seed + i, "syndrome_iter": 100}})
        i += 1
        slowest = max(slowest, time.monotonic() - t0)
        # anytime policy: never start a trial that would not finish within the budget (first trial always runs)
        if time.monotonic() + slowest >= deadline:
            break
    return out


def _mqt_css(public):
    from mqt.qecc import CSSCode
    n = public["n"]
    return CSSCode(Hx=gf2.from_sparse_rows(public["hx"], n).astype(np.int8), Hz=gf2.from_sparse_rows(public["hz"], n).astype(np.int8))


def t_qecc_heuristic(public, track, seed, deadline):
    if public["task"] != "css_logical_zero":
        raise NotImplementedError("CSS codes only")
    from mqt.qecc.circuit_synthesis import heuristic_prep_circuit
    contract = public["tracks"][track]["contract"]
    out = [{"circuit": Circuit.from_qiskit(heuristic_prep_circuit(_mqt_css(public), optimize_depth=False, state="all_zero")
                                           .circ.to_qiskit_circuit(), clifford_only=True), "meta": {"state": "all_zero"}}]
    if contract == "codespace_state":
        out.append({"circuit": Circuit.from_qiskit(heuristic_prep_circuit(_mqt_css(public), optimize_depth=False, state="all_plus")
                                                   .circ.to_qiskit_circuit(), clifford_only=True), "meta": {"state": "all_plus"}})
    return out


def t_tket(public, track, seed, deadline):
    from pytket.circuit import OpType
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import AutoRebase, CliffordResynthesis, CliffordSimp, FullPeepholeOptimise, RemoveRedundancies, SequencePass
    start = _stim_tool("elimination")(public, track, seed, deadline)[0]["circuit"]
    tk = qiskit_to_tk(start.to_qiskit())
    SequencePass([CliffordResynthesis(), CliffordSimp(), FullPeepholeOptimise(allow_swaps=False), RemoveRedundancies(),
                  AutoRebase({OpType.CX, OpType.TK1})]).apply(tk)
    # a final implicit wire permutation is free when preparing from |0..0>: relabel gates instead of adding SWAPs
    perm = {a.index[0]: b.index[0] for a, b in tk.implicit_qubit_permutation().items()}
    c = Circuit.from_qiskit(tk_to_qiskit(tk, replace_implicit_swaps=False), clifford_only=True)
    return [{"circuit": c.relabel([perm[q] for q in range(c.n)]), "meta": {"start": "stim elimination"}}]


A2A_TOOLS = {
    "qiskit.synth_circuit_from_stabilizers": t_qiskit_from_stabilizers,
    "qiskit.synth_stabilizer_layers": t_qiskit_stab_layers,
    "qiskit.synth_stabilizer_depth_lnn": t_qiskit_stab_depth_lnn,
    "qiskit.synth_clifford_greedy": _clifford_tool("synth_clifford_greedy"),
    "qiskit.synth_clifford_ag": _clifford_tool("synth_clifford_ag"),
    "qiskit.synth_clifford_layers": _clifford_tool("synth_clifford_layers"),
    "stim.to_circuit(elimination)": _stim_tool("elimination"),
    "stim.to_circuit(graph_state)": _stim_tool("graph_state"),
    "rustiq.stabilizer_state_synthesis": t_rustiq,
    "mqt.qecc.heuristic_prep_circuit": t_qecc_heuristic,
    "pytket.CliffordResynthesis+FPO": t_tket,
}
ANYTIME = {"rustiq.stabilizer_state_synthesis"}


# ------------------------------------------------------------------ connectivity tracks
def sabre_route(c: Circuit, edges, seed: int) -> tuple[Circuit, list[int]]:
    """LightSABRE layout+routing (qiskit preset pass manager, optimisation level 0, fixed seed); returns the routed
    circuit (explicit swaps, before any optimisation) and the output map (code qubit -> physical qubit)."""
    from qiskit.transpiler import CouplingMap
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    cm = CouplingMap([list(e) for e in edges] + [[b, a] for a, b in edges])
    pm = generate_preset_pass_manager(optimization_level=0, coupling_map=cm, layout_method="sabre", routing_method="sabre",
                                      basis_gates=["h", "s", "sdg", "x", "y", "z", "sx", "sxdg", "cx", "cz", "cy", "swap"],
                                      seed_transpiler=seed)
    out = pm.run(c.to_qiskit())
    omap = out.layout.final_index_layout()
    return Circuit.from_qiskit(out, clifford_only=True), [int(v) for v in omap]


def routed(tool_name: str):
    base = A2A_TOOLS[tool_name]

    def tool(public, track, seed, deadline):
        edges = public["tracks"][track]["connectivity"]["edges"]
        a2a_track = "a2a_2q"
        out = []
        now = time.monotonic()
        cands = base(public, a2a_track, seed, now + (deadline - now) / 2 if tool_name in ANYTIME else deadline)
        if len(cands) > 1:
            # anytime synthesis produced several candidates: route the cheapest ones first while time remains
            from ..core.costs import costs as _c
            cands = sorted(cands, key=lambda c: _c(c["circuit"])["two_qubit_gates"])
        slowest = 0.0
        for cand in cands:
            t0 = time.monotonic()
            rc, omap = sabre_route(cand["circuit"], edges, seed)
            out.append({"circuit": rc, "output_map": omap, "meta": {**cand.get("meta", {}), "router": "qiskit LightSABRE (preset opt-level 0)"}})
            slowest = max(slowest, time.monotonic() - t0)
            if time.monotonic() + slowest >= deadline:
                break
        return out
    return tool


def snake_path(n: int, cols: int) -> list[int] | None:
    order = []
    rows = (n + cols - 1) // cols
    for r in range(rows):
        rng_ = range(r * cols, min((r + 1) * cols, n))
        order.extend(rng_ if r % 2 == 0 else reversed(list(rng_)))
    return order


def t_native_lnn(public, track, seed, deadline):
    """qiskit synth_stabilizer_depth_lnn (nearest-neighbour on a line) laid along a Hamiltonian path of the graph."""
    conn = public["tracks"][track]["connectivity"]
    n = public["n"]
    base = t_qiskit_stab_depth_lnn(public, "a2a_2q", seed, deadline)[0]["circuit"]
    if conn["kind"] == "line":
        path = list(range(n))
    else:
        path = snake_path(n, conn["cols"])
        es = {frozenset(e) for e in conn["edges"]}
        if any(frozenset((path[i], path[i + 1])) not in es for i in range(n - 1)):
            raise NotImplementedError("grid has no row-snake Hamiltonian path for this n")
    return [{"circuit": base.relabel(path), "output_map": path, "meta": {"layout": "line/snake path"}}]


GRAPH_TOOLS = {f"{t}+sabre": routed(t) for t in A2A_TOOLS}
GRAPH_TOOLS["qiskit.synth_stabilizer_depth_lnn(native path)"] = t_native_lnn
GRAPH_ANYTIME = {"rustiq.stabilizer_state_synthesis+sabre"}

CODESPACE_TOOLS = {
    "qiskit.synth_circuit_from_stabilizers(underconstrained)": t_qiskit_from_stabilizers,
    "stim.from_stabilizers(underconstrained).elimination": _stim_tool("elimination"),
    "stim.from_stabilizers(underconstrained).graph_state": _stim_tool("graph_state"),
    "mqt.qecc.heuristic_prep_circuit(|0_L>,|+_L>)": t_qecc_heuristic,
}


def tools_for(public: dict, track: str) -> dict:
    spec = public["tracks"][track]
    if spec["contract"] == "codespace_state":
        return CODESPACE_TOOLS
    if spec["connectivity"] == "all":
        return A2A_TOOLS
    return GRAPH_TOOLS


def is_anytime(tool: str) -> bool:
    return tool in ANYTIME or tool in GRAPH_ANYTIME


# ------------------------------------------------------------------ MQT QMAP (isolated: its heuristic segfaults on this machine)
QMAP_SCRIPT = r"""
import json, sys
from mqt.qmap.clifford_synthesis import TargetMetric
from mqt.qmap.plugins.qiskit.clifford_synthesis import synthesize_clifford
stabs, heuristic = json.loads(sys.stdin.read())
qc, res = synthesize_clifford(str(stabs), target_metric=TargetMetric.two_qubit_gates, heuristic=heuristic)
from qiskit import qasm2
print(json.dumps({"qasm": qasm2.dumps(qc)}))
"""
