"""Exact contract checkers for category C.

routing_equiv: every 2-qubit gate (including SWAPs) acts on a coupling-graph edge, and after "mapping replay" — drop the
  SWAPs while tracking the logical<->physical permutation, and map every other gate back to logical qubits — the
  resulting gate list is a topological reordering of the input circuit's gate DAG (each gate matches the next pending
  gate on every one of its logical qubits, with identical name and parameters, and qubit order). The initial mapping is
  chosen by the method; bridges and any other movement primitive are rejected (only explicit SWAPs move qubits).
routing_commuting: as above, but within each given commuting block the gates may appear in any order; blocks keep their
  relative order on every qubit (a gate of block b may not appear on a qubit before all gates of earlier blocks on it).
A small-scale QCEC cross-check (compilation-flow equivalence) is available via crosscheck_qcec().
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field

from ..core.circuit import Circuit, gate_signature_error, width_error


@dataclass
class RoutingVerdict:
    status: str
    reason: str = ""
    details: dict = field(default_factory=dict)


def _norm_params(p) -> tuple:
    out = []
    for x in p:
        out.append(float(x).hex() if isinstance(x, float) else str(x))
    return tuple(out)


def replay(routed: Circuit, initial_layout: list[int], n_logical: int, edges) -> tuple[list | None, str, int]:
    """Returns (logical gate list, error, swap count). initial_layout[l] = physical qubit of logical qubit l."""
    werr = width_error(routed.n)   # Phase 7 C1: the routed circuit's width first (a format failure, never a crash)
    if werr:
        return None, f"invalid circuit: {werr}", 0
    es = {frozenset(e) for e in edges}
    if len(initial_layout) != n_logical or len(set(initial_layout)) != n_logical:
        return None, "invalid initial layout", 0
    if any(p < 0 or p >= routed.n for p in initial_layout):
        return None, "initial layout outside the device", 0
    phys2log = {p: l for l, p in enumerate(initial_layout)}
    out = []
    swaps = 0
    for g, qs, params in routed.gates:
        if g in ("barrier", "id"):
            continue
        if len(qs) > 2:
            return None, f"{g} acts on {len(qs)} qubits: only 1- and 2-qubit gates may be routed", swaps
        sig = gate_signature_error(g, qs, params, symbolic=True)   # 10-23: exact qubit / parameter count (e.g. swap)
        if sig:
            return None, f"malformed gate: {sig}", swaps
        if len(qs) == 2 and frozenset(qs) not in es:
            return None, f"two-qubit gate {g}{qs} not on a coupling edge", swaps
        if g == "swap":
            a, b = qs
            la, lb = phys2log.get(a), phys2log.get(b)
            phys2log.pop(a, None)
            phys2log.pop(b, None)
            if la is not None:
                phys2log[b] = la
            if lb is not None:
                phys2log[a] = lb
            swaps += 1
            continue
        if g in ("bridge",):
            return None, "bridge gates are not allowed in this track", swaps
        try:
            lq = tuple(phys2log[q] for q in qs)
        except KeyError:
            return None, f"gate {g}{qs} acts on a physical qubit that holds no logical qubit", swaps
        out.append((g, lq, _norm_params(params)))
    return out, "", swaps


def check_routing_equiv(original: Circuit, routed: Circuit, initial_layout, edges, blocks=None) -> RoutingVerdict:
    if width_error(original.n):   # the instance's own circuit: a data / checker error, not the candidate's
        return RoutingVerdict("error", f"input circuit: {width_error(original.n)}")
    logical, err, swaps = replay(routed, initial_layout, original.n, edges)
    if logical is None:
        return RoutingVerdict("fail", err)
    orig = [(g, tuple(qs), _norm_params(p)) for g, qs, p in original.gates if g not in ("barrier", "id")]
    if blocks is None:
        per_q = [deque() for _ in range(original.n)]
        for i, (g, qs, p) in enumerate(orig):
            for q in qs:
                per_q[q].append(i)
        done = [False] * len(orig)
        for g, qs, p in logical:
            heads = {per_q[q][0] if per_q[q] else None for q in qs}
            if len(heads) != 1 or None in heads:
                return RoutingVerdict("fail", f"gate {g}{qs} does not match the input DAG", {"swaps": swaps})
            i = heads.pop()
            if orig[i] != (g, qs, p):
                return RoutingVerdict("fail", f"gate {g}{qs}{p} does not match the input gate {orig[i]}", {"swaps": swaps})
            for q in qs:
                per_q[q].popleft()
            done[i] = True
        if not all(done):
            return RoutingVerdict("fail", f"{done.count(False)} input gates missing", {"swaps": swaps})
        return RoutingVerdict("pass", "", {"swaps": swaps})
    # commuting blocks: blocks[i] = block index of input gate i (non-decreasing along the input gate list)
    blk = list(blocks)
    if len(blk) != len(orig):
        return RoutingVerdict("error", "block annotation length mismatch")
    remaining: dict = {}
    for i, (g, qs, p) in enumerate(orig):
        remaining.setdefault(blk[i], Counter())[(g, qs if g not in _SYMMETRIC else tuple(sorted(qs)), p)] += 1
    qubit_block = [min(blk) if blk else 0] * original.n
    # per qubit: which block is "current" = smallest block that still has unmatched gates on that qubit
    pending_on_q = [Counter() for _ in range(original.n)]
    for i, (g, qs, p) in enumerate(orig):
        for q in qs:
            pending_on_q[q][blk[i]] += 1
    for g, qs, p in logical:
        key = (g, qs if g not in _SYMMETRIC else tuple(sorted(qs)), p)
        cands = [b for b, c in remaining.items() if c.get(key)]
        # the gate must belong to the earliest open block on each of its qubits
        ok = None
        for b in sorted(cands):
            if all(min(k for k, v in pending_on_q[q].items() if v) == b for q in qs):
                ok = b
                break
        if ok is None:
            return RoutingVerdict("fail", f"gate {g}{qs} violates block order or is not in the input", {"swaps": swaps})
        remaining[ok][key] -= 1
        for q in qs:
            pending_on_q[q][ok] -= 1
    if any(v for c in remaining.values() for v in c.values()):
        return RoutingVerdict("fail", "input gates missing", {"swaps": swaps})
    return RoutingVerdict("pass", "", {"swaps": swaps})


_SYMMETRIC = {"cz", "rzz", "swap", "iswap", "rxx", "ryy"}   # qubit order irrelevant inside commuting blocks


def crosscheck_qcec(original: Circuit, routed: Circuit, initial_layout, seed: int = 0) -> str:
    """Independent small-scale cross-check with MQT QCEC: the input circuit laid out by the initial mapping must equal
    the routed circuit followed by SWAPs that undo the wire permutation induced by the routing SWAPs.
    Symbolic parameters are bound to random values first."""
    import numpy as np
    from mqt.qcec import verify
    from qiskit import QuantumCircuit
    rng = np.random.default_rng(seed)
    n = routed.n
    vals = {}

    def num(p):
        out = []
        for x in p:
            if isinstance(x, str):
                vals.setdefault(x, float(rng.uniform(0, 2 * np.pi)))
                out.append(vals[x])
            else:
                out.append(x)
        return out
    a = QuantumCircuit(n)
    for g, qs, p in original.gates:
        getattr(a, g)(*num(p), *[initial_layout[q] for q in qs])
    b = QuantumCircuit(n)
    content = list(range(n))            # content[p] = wire that currently sits at position p
    for g, qs, p in routed.gates:
        getattr(b, g)(*num(p), *qs)
        if g == "swap":
            x, y = qs
            content[x], content[y] = content[y], content[x]
    for target in range(n):             # restore every wire to its own position (checking aid, not part of the answer)
        cur = content.index(target)
        if cur != target:
            b.swap(cur, target)
            content[cur], content[target] = content[target], content[cur]
    return str(verify(a, b, parallel=False, nthreads=1, timeout=300.0).equivalence).split(".")[-1]
