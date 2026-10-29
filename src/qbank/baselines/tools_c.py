"""Category-C baseline routers. Each returns candidates {"circuit", "initial_layout", "meta"}.

Routers that cannot take the instance's gates directly (QMAP needs CX + 1q; pytket's Qiskit converter rejects symbolic
angles) route a placeholder circuit with the same qubit-interaction structure (2q gate -> cx, 1q gate -> rz(tag)); the
original gates are then substituted back by mapping replay (the placeholder routing is a valid routing of the original
because routing depends only on the interaction pattern). Every result is re-verified by contracts/routing.py.
The routed circuit is taken after routing and before any optimisation.
"""
from __future__ import annotations

import time
from collections import deque

from ..core.circuit import Circuit

TAG_GATE, TAG_STEP = "ry", 1e-3        # layout tags: ry((l+1)*TAG_STEP) on logical qubit l (the only ry in a placeholder)
ROUTER_BASIS = ["h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "rz", "rx", "ry", "cx", "cz", "rzz", "rxx", "ryy", "swap"]


def _orig(public) -> Circuit:
    return Circuit.from_json(public["circuit"])


def _edges(public):
    return [list(e) for e in public["coupling_edges"]]


def placeholder_qiskit(c: Circuit, two_qubit: str = "cx"):
    """Same interaction structure; 2q gates become `two_qubit` (cx for QMAP; rzz for tket, which bridges CX gates),
    1q gates become rz with a numeric tag."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(c.n)
    for l in range(c.n):                      # leading tags identify logical qubit l in the router output
        qc.ry((l + 1) * TAG_STEP, l)
    for k, (g, qs, _) in enumerate(c.gates):
        if len(qs) == 2:
            if two_qubit == "cx":
                qc.cx(*qs)
            else:
                qc.rzz(0.1 + 1e-4 * k, *qs)
        else:
            qc.rz(0.1 + 1e-4 * k, qs[0])
    return qc


def layout_from_tags(routed: list[tuple[str, tuple, float | None]], n: int, N: int):
    """routed: (name, physical qubits, first numeric parameter or None). Returns (initial_layout, gates without tags)."""
    token = list(range(N))                 # token[p] = physical position the wire at p started from
    layout = [None] * n
    out = []
    for g, qs, par in routed:
        if g == "swap":
            a, b = qs
            token[a], token[b] = token[b], token[a]
            out.append((g, qs))
            continue
        if g == TAG_GATE:
            l = int(round(par / TAG_STEP)) - 1
            if not (0 <= l < n) or layout[l] is not None:
                raise RuntimeError(f"bad layout tag {par}")
            layout[l] = token[qs[0]]
            continue
        out.append((g, qs))
    if any(x is None for x in layout):
        raise RuntimeError("layout tags missing in the router output")
    return layout, out


def substitute(orig: Circuit, routed_gates: list[tuple[str, tuple]], initial_layout: list[int], n_phys: int) -> Circuit:
    """Replace each non-swap routed gate by the original gate it corresponds to (DAG replay)."""
    per_q = [deque() for _ in range(orig.n)]
    for i, (g, qs, p) in enumerate(orig.gates):
        for q in qs:
            per_q[q].append(i)
    phys2log = {p: l for l, p in enumerate(initial_layout)}
    out = Circuit(n_phys)
    for g, qs in routed_gates:
        if g in ("barrier", "id", "measure"):
            continue
        if g == "swap":
            a, b = qs
            la, lb = phys2log.pop(a, None), phys2log.pop(b, None)
            if la is not None:
                phys2log[b] = la
            if lb is not None:
                phys2log[a] = lb
            out.append("swap", qs)
            continue
        lq = [phys2log[q] for q in qs]
        heads = {per_q[q][0] for q in lq}
        if len(heads) != 1:
            raise RuntimeError("routed placeholder does not follow the input DAG")
        i = heads.pop()
        og, oqs, op = orig.gates[i]
        if sorted(oqs) != sorted(lq):
            raise RuntimeError("placeholder/original qubit mismatch")
        for q in lq:
            per_q[q].popleft()
        out.append(og, [initial_layout_inverse_map(phys2log, l) for l in oqs], op)
    return out


def initial_layout_inverse_map(phys2log: dict, l: int) -> int:
    for p, ll in phys2log.items():
        if ll == l:
            return p
    raise KeyError(l)


def _qiskit_gates(qc) -> list[tuple[str, tuple]]:
    return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]


# ------------------------------------------------------------------ Qiskit LightSABRE (anytime over seeds)
def t_sabre(public, track, seed, deadline):
    from qiskit.transpiler import CouplingMap
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    orig = _orig(public)
    n, N = orig.n, public["n_physical"]
    es = _edges(public)
    cm = CouplingMap(es + [[b, a] for a, b in es])
    qc = orig.to_qiskit()
    out = []
    i = 0
    slowest = 0.0
    while True:
        t0 = time.monotonic()
        pm = generate_preset_pass_manager(optimization_level=0, coupling_map=cm, layout_method="sabre",
                                          routing_method="sabre", basis_gates=ROUTER_BASIS, seed_transpiler=seed + i)
        r = pm.run(qc)
        init = r.layout.initial_index_layout()[:n]
        rc = Circuit(N)
        for g, qs, p in Circuit.from_qiskit(r).gates:
            rc.append(g, qs, p)
        out.append({"circuit": rc, "initial_layout": [int(x) for x in init],
                    "meta": {"trial_seed": seed + i, "router": "qiskit LightSABRE (SabreLayout+SabreSwap, preset opt-level 0)"}})
        i += 1
        slowest = max(slowest, time.monotonic() - t0)
        if time.monotonic() + slowest >= deadline:
            break
    return out


def t_sabre_shuffle(public, track, seed, deadline):
    """Commuting track only: LightSABRE on random reorderings of the gates inside each commuting block (trial 0 keeps
    the given order). Any within-block order is allowed by the routing_commuting contract."""
    import numpy as np
    orig = _orig(public)
    blocks = public.get("blocks")
    if public["tracks"][track]["contract"] != "routing_commuting" or blocks is None:
        raise NotImplementedError("block reordering only applies to the commuting-block track")
    rng = np.random.default_rng(seed)
    out = []
    slowest = 0.0
    i = 0
    while True:
        t0 = time.monotonic()
        order = []
        k = 0
        while k < len(orig.gates):
            j = k
            while j < len(orig.gates) and blocks[j] == blocks[k]:
                j += 1
            idx = list(range(k, j))
            if i > 0:
                rng.shuffle(idx)
            order += idx
            k = j
        re = Circuit(orig.n)
        for x in order:
            re.append(*orig.gates[x])
        pub = {**public, "circuit": re.to_json()}
        r = t_sabre(pub, track, seed + 7919 * i, time.monotonic())[0]     # one SABRE trial per reordering
        r["meta"] = {**r["meta"], "block_shuffle_trial": i, "router": "qiskit LightSABRE on a random within-block reordering"}
        out.append(r)
        i += 1
        slowest = max(slowest, time.monotonic() - t0)
        if time.monotonic() + slowest >= deadline:
            break
    return out


def t_sabre_shuffle_trial(public, track, seed, trial: int):
    """Re-create exactly trial `trial` of t_sabre_shuffle (same reordering stream and SABRE seed) -- reproducibility."""
    import numpy as np
    orig = _orig(public)
    blocks = public.get("blocks")
    rng = np.random.default_rng(seed)
    out = None
    for i in range(trial + 1):
        order = []
        k = 0
        while k < len(orig.gates):
            j = k
            while j < len(orig.gates) and blocks[j] == blocks[k]:
                j += 1
            idx = list(range(k, j))
            if i > 0:
                rng.shuffle(idx)
            order += idx
            k = j
        if i == trial:
            re = Circuit(orig.n)
            for x in order:
                re.append(*orig.gates[x])
            out = t_sabre({**public, "circuit": re.to_json()}, track, seed + 7919 * i, time.monotonic())
    return out


# ------------------------------------------------------------------ tket (GraphPlacement + LexiRoute), placeholder routing
def t_tket(public, track, seed, deadline):
    from pytket.architecture import Architecture
    from pytket.circuit import OpType
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.mapping import LexiLabellingMethod, LexiRouteRoutingMethod, MappingManager
    from pytket.placement import GraphPlacement
    orig = _orig(public)
    n, N = orig.n, public["n_physical"]
    tk = qiskit_to_tk(placeholder_qiskit(orig, two_qubit="rzz"))   # tket may BRIDGE CX gates; ZZPhase cannot be bridged
    arc = Architecture([tuple(e) for e in _edges(public)])
    placement = "GraphPlacement"
    try:                                        # default GraphPlacement settings (pytket's documented defaults)
        GraphPlacement(arc).place(tk)
    except RuntimeError as e:                   # "execution time has exceeded allowed limits" on large circuits
        from pytket.placement import LinePlacement
        tk = qiskit_to_tk(placeholder_qiskit(orig, two_qubit="rzz"))
        LinePlacement(arc).place(tk)
        placement = f"LinePlacement (GraphPlacement failed: {str(e)[:60]})"
    MappingManager(arc).route_circuit(tk, [LexiLabellingMethod(), LexiRouteRoutingMethod()])
    if tk.n_gates_of_type(OpType.BRIDGE):
        raise RuntimeError("tket inserted BRIDGE gates (not allowed in this track)")
    import math
    routed = []
    for cmd in tk.get_commands():
        t = cmd.op.type
        qs = tuple(a.index[0] for a in cmd.args)
        if t == OpType.SWAP:
            routed.append(("swap", qs, None))
        elif t in (OpType.CX, OpType.ZZPhase):
            routed.append(("cx", qs, None))
        elif t == OpType.Rz:
            routed.append(("rz", qs, None))
        elif t == OpType.Ry:
            routed.append((TAG_GATE, qs, float(cmd.op.params[0]) * math.pi))   # tket angles are in half-turns
        elif t == OpType.Barrier:
            continue
        else:
            raise RuntimeError(f"unexpected tket op {t}")
    init, gates = layout_from_tags(routed, n, N)
    return [{"circuit": substitute(orig, gates, init, N), "initial_layout": init,
             "meta": {"router": "pytket placement + LexiLabelling + LexiRoute (placeholder routing)", "placement": placement}}]


# ------------------------------------------------------------------ MQT QMAP heuristic mapper, placeholder routing
def t_qmap(public, track, seed, deadline):
    from mqt.qmap.plugins.qiskit.sc import compile_
    from mqt.qmap.sc import Architecture
    orig = _orig(public)
    n, N = orig.n, public["n_physical"]
    es = _edges(public)
    arch = Architecture(N, {tuple(e) for e in es} | {tuple(e[::-1]) for e in es})
    out, res = compile_(placeholder_qiskit(orig), arch=arch, add_measurements_to_mapped_circuit=False,
                        post_mapping_optimizations=False, pre_mapping_optimizations=False)
    routed = [(i.operation.name, tuple(out.find_bit(q).index for q in i.qubits),
               float(i.operation.params[0]) if i.operation.params else None) for i in out.data if i.operation.name != "barrier"]
    init, gates = layout_from_tags(routed, n, N)
    return [{"circuit": substitute(orig, gates, init, N), "initial_layout": init,
             "meta": {"router": "mqt.qmap heuristic mapper (compile_, no pre/post optimisation; placeholder routing)"}}]


# ------------------------------------------------------------------ Qiskit commuting-gate router (swap strategy on a path)
def hamiltonian_path(edges, N) -> list[int] | None:
    """A Hamiltonian path of a line/ring device, else None."""
    adj = {i: set() for i in range(N)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    if not all(len(s) <= 2 for s in adj.values()):
        return None
    ends = [v for v, s in adj.items() if len(s) == 1]
    start = ends[0] if ends else 0
    path, prev = [start], None
    while len(path) < N:
        nxt = [u for u in adj[path[-1]] if u != prev and u not in path]
        if not nxt:
            return None
        prev = path[-1]
        path.append(nxt[0])
    return path


def grid_snake(edges, N) -> list[int] | None:
    adj = {frozenset(e) for e in edges}
    for r in range(2, N):
        if N % r == 0:
            c = N // r
            snake = [i * c + (j if i % 2 == 0 else c - 1 - j) for i in range(r) for j in range(c)]
            if all(frozenset((snake[k], snake[k + 1])) in adj for k in range(N - 1)):
                return snake
    return None


def long_path(edges, N, need: int, seed: int, deadline: float) -> list[int] | None:
    """Heuristic simple path with >= need vertices (randomised Warnsdorff DFS with restarts, bounded by the deadline)."""
    import random
    adj = {i: [] for i in range(N)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    rnd = random.Random(seed)
    best = []
    starts = sorted(range(N), key=lambda v: len(adj[v]))
    k = 0
    while time.monotonic() < deadline and k < 200:
        v0 = starts[k % N] if k < N else rnd.randrange(N)
        k += 1
        path, seen = [v0], {v0}
        while True:
            nxt = [u for u in adj[path[-1]] if u not in seen]
            if not nxt:
                break
            deg = lambda u: sum(1 for w in adj[u] if w not in seen)
            m = min(deg(u) for u in nxt)
            u = rnd.choice([u for u in nxt if deg(u) == m])
            path.append(u)
            seen.add(u)
        if len(path) > len(best):
            best = path
        if len(best) >= need:
            return best
    return best if len(best) >= need else None


def t_commuting(public, track, seed, deadline):
    """Qiskit's Commuting2qGateRouter with a line swap strategy along a device path.

    Qiskit 2.5's router mis-tracks the layout once a circuit has more than one commuting block (the distance lookup in
    _make_op_layers reads the layout in the opposite direction from _position_in_cmap, so blocks after the first can be
    placed on non-adjacent qubits). We therefore route every commuting block separately from a trivial layout and track
    the logical->physical permutation ourselves; single-qubit gates between blocks are emitted at the current positions.
    """
    if public["tracks"][track]["contract"] != "routing_commuting" or public.get("blocks") is None:
        raise NotImplementedError("commuting-gate router only applies to the commuting-block track")
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter
    from qiskit.circuit.library import PauliEvolutionGate
    from qiskit.quantum_info import SparsePauliOp
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes.routing.commuting_2q_gate_routing import (Commuting2qGateRouter,
                                                                            FindCommutingPauliEvolutions, SwapStrategy)
    orig = _orig(public)
    n, N = orig.n, public["n_physical"]
    es = _edges(public)
    path = hamiltonian_path(es, N) or grid_snake(es, N)
    how = "Hamiltonian path"
    if path is None:
        path = long_path(es, N, n, seed, min(deadline, time.monotonic() + 10))
        how = "heuristic simple path"
    if path is None:
        raise NotImplementedError("no simple device path covering the logical qubits was found")
    path = path[:n]
    strat = SwapStrategy.from_line(path)
    pm = PassManager([FindCommutingPauliEvolutions(), Commuting2qGateRouter(strat)])
    pos = list(path)                                  # pos[l] = current physical qubit of logical l
    rc = Circuit(N)
    syms: dict = {}

    def route_block(block):
        at = {p: l for l, p in enumerate(pos)}
        terms, theta = [], None
        for g, qs, p in block:
            terms.append(({"rzz": "ZZ", "rxx": "XX", "ryy": "YY"}[g], [pos[q] for q in qs], 0.5))
            theta = p[0]
        t = syms.setdefault(theta, Parameter(theta)) if isinstance(theta, str) else theta
        qc = QuantumCircuit(N)
        qc.append(PauliEvolutionGate(SparsePauliOp.from_sparse_list(terms, num_qubits=N), time=t), range(N))
        dec = _expand_pauli_evolutions(pm.run(qc))
        for inst in dec.data:
            name = inst.operation.name
            qs = tuple(dec.find_bit(q).index for q in inst.qubits)
            rc.append(name, qs, tuple(norm_param(x) for x in inst.operation.params))
            if name == "swap":
                a, b = qs
                la, lb = at.pop(a, None), at.pop(b, None)
                if la is not None:
                    pos[la] = b
                    at[b] = la
                if lb is not None:
                    pos[lb] = a
                    at[a] = lb
    blocks = public["blocks"]
    cur, b0 = [], None
    for (g, qs, p), b in zip(orig.gates, blocks):
        if len(qs) == 2 and g in ("rzz", "rxx", "ryy"):
            if b != b0 and cur:
                route_block(cur)
                cur = []
            cur.append((g, qs, p))
            b0 = b
            continue
        if cur:
            route_block(cur)
            cur = []
        b0 = None
        if len(qs) != 1:
            raise NotImplementedError(f"two-qubit gate {g} outside a commuting ZZ/XX/YY block")
        rc.append(g, (pos[qs[0]],), p)
    if cur:
        route_block(cur)
    return [{"circuit": rc, "initial_layout": list(path),
             "meta": {"router": f"qiskit Commuting2qGateRouter + SwapStrategy.from_line ({how}), per-block routing"}}]


def norm_param(x):
    """float for numeric parameters; the symbol's name if the expression is exactly one symbol (e.g. 1.0*gamma)."""
    try:
        return float(x)
    except TypeError:
        ps = list(x.parameters)
        if len(ps) == 1 and (x - ps[0]).sympify() == 0:
            return ps[0].name
        return str(x)


def _expand_pauli_evolutions(qc):
    """PauliEvolutionGate on two qubits with a single ZZ/XX/YY term of coefficient 0.5 -> rzz/rxx/ryy(time)."""
    from qiskit import QuantumCircuit
    out = QuantumCircuit(*qc.qregs)
    for inst in qc.data:
        op = inst.operation
        if op.name == "PauliEvolution":
            spo = op.operator if not isinstance(op.operator, list) else op.operator[0]
            for label, coeff in spo.to_list():
                qidx = [i for i, ch in enumerate(reversed(label)) if ch != "I"]
                kind = {"ZZ": "rzz", "XX": "rxx", "YY": "ryy"}[label.replace("I", "")]
                t = op.params[0]
                getattr(out, kind)(2 * coeff.real * t, *[_qidx(qc, inst, i) for i in qidx])
        else:
            out.append(op, inst.qubits, inst.clbits)
    return out


def _qidx(qc, inst, logical_index_in_op):
    return qc.find_bit(inst.qubits[logical_index_in_op]).index


OLSQ2_SCRIPT = r"""
import sys, json, io, contextlib
d = json.loads(sys.stdin.read())
sys.path.insert(0, d["path"])
from olsq import OLSQ
from olsq.device import qcdevice
s = OLSQ(True, "transition", 1)
s.setdevice(qcdevice(name="dev", nqubits=d["N"], connection=[tuple(e) for e in d["edges"]], swap_duration=1))
s.setprogram([d["n"], [tuple(g) for g in d["gates"]], d["names"]], input_mode="IR")
with contextlib.redirect_stdout(io.StringIO()):
    depth, names, qubits, final_map, init_map, obj = s.solve(False, output_mode="IR")
print("OLSQ2JSON" + json.dumps({"names": names, "qubits": qubits, "init": init_map}))
"""
OLSQ2_MAX_QUBITS, OLSQ2_MAX_GATES = 16, 80


def t_olsq2(public, track, seed, deadline):
    """OLSQ2 (UCLA-VAST, BSD-3; patched for Qiskit 2, env/patches/olsq2_qiskit2.patch) in transition-based mode with the
    SWAP-count objective, on the placeholder circuit; small instances only. Run in its own process group and killed at
    the deadline (z3 is not interruptible). SWAP counts are minimal within OLSQ2's time horizon, not a proof of global
    optimality."""
    import json
    import os
    import signal
    import subprocess
    import sys
    from ..core.instance import PKG_ROOT
    orig = _orig(public)
    n, N = orig.n, public["n_physical"]
    if n > OLSQ2_MAX_QUBITS or len(orig.gates) > OLSQ2_MAX_GATES:
        raise NotImplementedError(f"OLSQ2 limited to <= {OLSQ2_MAX_QUBITS} qubits and <= {OLSQ2_MAX_GATES} gates here")
    gates = [tuple(qs) for _, qs, _ in orig.gates]
    names = ["cx" if len(q) == 2 else "h" for q in gates]
    payload = json.dumps({"path": str(PKG_ROOT / "external" / "src" / "OLSQ2"), "N": N, "edges": _edges(public), "n": n,
                          "gates": gates, "names": names})
    import tempfile
    with tempfile.TemporaryDirectory(prefix="qbank-olsq2-") as tmp:     # OLSQ2 writes intermediate_result_*.qasm to cwd
        p = subprocess.Popen([sys.executable, "-c", OLSQ2_SCRIPT], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True, start_new_session=True, cwd=tmp)
        try:
            out, _ = p.communicate(payload, timeout=max(1.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            raise TimeoutError("OLSQ2 did not finish within the budget")
        finally:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    if "OLSQ2JSON" not in out:
        raise RuntimeError(f"OLSQ2 failed (exit {p.returncode})")
    r = json.loads(out[out.index("OLSQ2JSON") + 9:].strip().splitlines()[0])
    routed = []
    for names_t, qubits_t in zip(r["names"], r["qubits"]):
        for g, qs in zip(names_t, qubits_t):
            if g == "SWAP":
                continue
            routed.append(("cx" if len(qs) == 2 else "rz", tuple(qs)))
        for g, qs in zip(names_t, qubits_t):
            if g == "SWAP":
                routed.append(("swap", tuple(qs)))
    init = [int(x) for x in r["init"]]
    return [{"circuit": substitute(orig, routed, init, N), "initial_layout": init,
             "meta": {"router": "OLSQ2 (transition-based, SWAP objective; placeholder routing)"}}]


C_TOOLS = {
    "qiskit LightSABRE (anytime)": t_sabre,
    "pytket LexiRoute": t_tket,
    "mqt.qmap heuristic": t_qmap,
    "qiskit Commuting2qGateRouter": t_commuting,
    "qiskit LightSABRE + block reordering (anytime)": t_sabre_shuffle,
    "OLSQ2 (TB, swap objective)": t_olsq2,
}
C_ANYTIME = {"qiskit LightSABRE (anytime)", "qiskit LightSABRE + block reordering (anytime)"}
COMMUTING_ONLY = {"qiskit Commuting2qGateRouter", "qiskit LightSABRE + block reordering (anytime)"}
