"""Cost metrics recomputed by qbank. Tool self-reports are never used.

two_qubit_gates: cx = cz = cy = 1, swap = 3 (other 2-qubit gates are rejected by the contracts before costing;
                 here they count 1 and are listed in 'other_2q').
depth / two_qubit_depth: ASAP layering; for depth purposes a swap counts as 3 consecutive 2-qubit layers.
t_count: fixed decomposition table T_COUNT (frozen for v1; documented in the datasheets).
Dynamic-circuit gates: "measure" counts one measurement; "c:<g>" counts max(1, #condition records) classical-control
operations and is costed as <g>; feedforward_rounds = longest chain measurement -> classically controlled gate ->
measurement ... (qubit light cones propagate levels); opaque oracles (cu^p counts p, prep_* count 1) go to oracle_calls
and are not two-qubit gates. For B's "mbu" (no "c:" gates) feedforward_rounds = number of mbu measurements, as before.
"""
from __future__ import annotations

from .circuit import Circuit

TWO_Q_WEIGHT = {"cx": 1, "cz": 1, "cy": 1, "swap": 3}
# Fixed decompositions (frozen for v1), taken from Qiskit 2.5.2's definitions of CCXGate, CCZGate, RCCXGate, RC3XGate
# transpiled to {cx, h, t, tdg, s, sdg, x, z} (see phase-2 log / tests/test_b_contracts.py):
#   ccx: 7 T, 6 CX | ccz: 7 T, 6 CX | rccx: 4 T, 3 CX | rc3x: 8 T, 6 CX
T_COUNT = {"t": 1, "tdg": 1, "ccx": 7, "ccz": 7, "rccx": 4, "rc3x": 8}
CX_COUNT = {"cx": 1, "cz": 1, "cy": 1, "swap": 3, "ccx": 6, "ccz": 6, "rccx": 3, "rc3x": 6}
TOFFOLI_WEIGHT = {"ccx": 1, "ccz": 1, "rccx": 1, "rc3x": 2}   # AND count: a 3-control gate is two ANDs
TOFFOLI_LIKE = set(TOFFOLI_WEIGHT)


def costs(c: Circuit) -> dict:
    two_q = 0
    other_2q = {}
    swaps = 0
    depth = [0] * c.n
    depth2 = [0] * c.n
    t = 0
    tof = 0
    cxc = 0
    meas = 0
    cc_ops = 0
    ff_level = [0] * c.n          # dynamic circuits (category E): feedforward level reaching each qubit
    rec_level: dict = {}
    ff_rounds = 0
    oracle_calls = 0
    for g, qs, params in c.gates:
        if g == "id":
            continue
        if g == "measure":            # mid-circuit / final Z measurement into a classical record
            meas += 1
            rec_level[int(params[0])] = ff_level[qs[0]]
            d = max(depth[q] for q in qs) + 1
            depth[qs[0]] = d
            continue
        if g in ("cu", "prep_psi", "prep_phi"):     # opaque oracles: counted separately, not as two-qubit gates
            oracle_calls += int(params[0]) if g == "cu" else 1
            continue
        if g.startswith("c:"):        # classically controlled gate: parity of the listed records
            cond = params[0]
            cc_ops += max(1, len(cond))
            lvl = max([ff_level[q] for q in qs] + [1 + max((rec_level.get(int(r), 0) for r in cond), default=0)])
            ff_rounds = max(ff_rounds, lvl)
            for q in qs:
                ff_level[q] = lvl
            g = g[2:]
            params = tuple(params[1:])
        elif len(qs) == 2:
            lv = max(ff_level[q] for q in qs)
            for q in qs:
                ff_level[q] = lv
        if g == "mbu":       # X-basis measurement + classically controlled diagonal correction
            # 10-24 merge (C8 / Codex RECONCILE 58): the correction gates are real (conditional) gates: their T and CX
            # are charged, and they also count in two_qubit_gates (cz), gate_count, depth (the measurement is one
            # layer on q, each correction gate a layer on its qubits after it) and qubits_used. Their Toffoli count is
            # 0 (only diagonal gates; ccz = 1 if it ever appears). Depth is the ASAP depth of the unconditional
            # circuit, i.e. an upper bound when the outcome is 0 (no correction applied).
            meas += 1
            corr = params[0] if params else ()
            cc_ops += sum(1 for cg, _ in corr if cg != "id")
            t += sum(T_COUNT.get(cg, 0) for cg, _ in corr)
            cxc += sum(CX_COUNT.get(cg, 0) for cg, _ in corr)
            tof += sum(TOFFOLI_WEIGHT.get(cg, 0) for cg, _ in corr)
            q0 = qs[0]
            dm = depth[q0] + 1
            depth[q0] = dm
            for cg, cqs in corr:
                if cg == "id":
                    continue
                cqs = list(cqs)
                d = max([depth[q] for q in cqs] + [dm]) + 1
                for q in cqs:
                    depth[q] = d
                if len(cqs) == 2:
                    two_q += TWO_Q_WEIGHT.get(cg, 1)
                    d2 = max([depth2[q] for q in cqs]) + 1
                    for q in cqs:
                        depth2[q] = d2
            continue
        cxc += CX_COUNT.get(g, 0)
        w = 3 if g == "swap" else 1
        if len(qs) == 2:
            if g in TWO_Q_WEIGHT:
                two_q += TWO_Q_WEIGHT[g]
            else:
                two_q += 1
                other_2q[g] = other_2q.get(g, 0) + 1
            if g == "swap":
                swaps += 1
            d2 = max(depth2[q] for q in qs) + w
            for q in qs:
                depth2[q] = d2
        d = max(depth[q] for q in qs) + w
        for q in qs:
            depth[q] = d
        t += T_COUNT.get(g, 0)
        tof += TOFFOLI_WEIGHT.get(g, 0)
    touched = {q for _, qs, _ in c.gates for q in qs}
    touched |= {q for g, _, p in c.gates if g == "mbu" and p for _, cqs in p[0] for q in cqs}   # correction qubits (10-24)
    return {
        "two_qubit_gates": two_q,
        "swaps": swaps,
        "depth": max(depth, default=0),
        "two_qubit_depth": max(depth2, default=0),
        "gate_count": sum((1 + sum(1 for cg, _ in p[0] if cg != "id")) if g == "mbu" and p else 1
                          for g, _, p in c.gates if g != "id"),
        "t_count": t,
        "toffoli_count": tof,
        "width": c.n,
        "qubits_used": len(touched),
        "other_2q": other_2q,
        "cx_count": cxc,
        "measurements": meas,
        "feedforward_rounds": ff_rounds if any(g.startswith("c:") for g, _, _ in c.gates) else meas,
        "classical_control_ops": cc_ops,
        "oracle_calls": oracle_calls,
    }


def cost(c: Circuit, metric: str):
    return costs(c)[metric]
