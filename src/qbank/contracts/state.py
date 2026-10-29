"""State-preparation contracts for category D.

state_exact:  from |0...0> the circuit prepares the target state up to a global phase, i.e. fidelity
              |<target|psi>|^2 >= 1 - EXACT_TOL = 1 - 1e-9 (circuits carry floating-point angles).
state_approx: fidelity >= the track's threshold (separate tracks, never compared with exact ones).

Qubit order: little-endian (basis index = sum_q bit_q * 2^q), as in Qiskit. No ancillas: the circuit width must equal n.

Primary checker: an independent sparse state-vector simulator (numpy int64 keys for n <= 62, Python-int keys above) run
on an equivalent support-aware gate order (see simulate_sparse), bounded by MAX_NNZ nonzero amplitudes (DICT_MAX_NNZ for
n > 62) during the simulation; beyond it the verdict is "unverified". For n <= 16 the
result is cross-checked with qiskit.quantum_info.Statevector; disagreement (> 1e-9 in fidelity) -> "checker_disagreement".
"""
from __future__ import annotations

import cmath
import math
from dataclasses import dataclass, field

import numpy as np

from ..core.circuit import Circuit, signature_errors, width_error

EXACT_TOL = 1e-9
MAX_NNZ = 1 << 22
DICT_MAX_NNZ = 1 << 18
DROP = 1e-15
GATE_SET_D = ("h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "sxdg", "rx", "ry", "rz", "p", "u", "cx", "cz", "id")


@dataclass
class StateVerdict:
    status: str
    reason: str = ""
    fidelity: float | None = None
    details: dict = field(default_factory=dict)


def _u(theta, phi, lam):
    return np.array([[math.cos(theta / 2), -cmath.exp(1j * lam) * math.sin(theta / 2)],
                     [cmath.exp(1j * phi) * math.sin(theta / 2), cmath.exp(1j * (phi + lam)) * math.cos(theta / 2)]])


def one_qubit_matrix(g: str, p) -> np.ndarray:
    s2 = 1 / math.sqrt(2)
    if g == "h":
        return np.array([[s2, s2], [s2, -s2]], dtype=complex)
    if g == "x":
        return np.array([[0, 1], [1, 0]], dtype=complex)
    if g == "y":
        return np.array([[0, -1j], [1j, 0]], dtype=complex)
    if g == "z":
        return np.diag([1, -1]).astype(complex)
    if g == "s":
        return np.diag([1, 1j])
    if g == "sdg":
        return np.diag([1, -1j])
    if g == "t":
        return np.diag([1, cmath.exp(1j * math.pi / 4)])
    if g == "tdg":
        return np.diag([1, cmath.exp(-1j * math.pi / 4)])
    if g == "sx":
        return 0.5 * np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]])
    if g == "sxdg":
        return 0.5 * np.array([[1 - 1j, 1 + 1j], [1 + 1j, 1 - 1j]])
    if g == "rx":
        t = float(p[0])
        return np.array([[math.cos(t / 2), -1j * math.sin(t / 2)], [-1j * math.sin(t / 2), math.cos(t / 2)]])
    if g == "ry":
        t = float(p[0])
        return np.array([[math.cos(t / 2), -math.sin(t / 2)], [math.sin(t / 2), math.cos(t / 2)]], dtype=complex)
    if g == "rz":
        t = float(p[0])
        return np.diag([cmath.exp(-0.5j * t), cmath.exp(0.5j * t)])
    if g == "p":
        return np.diag([1, cmath.exp(1j * float(p[0]))])
    if g == "u":
        return _u(*(float(x) for x in p))
    raise ValueError(f"no matrix for gate {g}")


class _TooLarge(Exception):
    pass


def segments(c: Circuit):
    """Split the circuit into its two-qubit gates (global order) and, per qubit, the fused 2x2 matrices of the single-
    qubit gates before its first two-qubit gate (initial[q]) and after its k-th two-qubit gate (after[(k, q)])."""
    twoq, initial, after, last, cur = [], {}, {}, {}, {}

    def close(q):
        if q in cur:
            M = cur.pop(q)
            if q in last:
                after[(last[q], q)] = M
            else:
                initial[q] = M
    for g, qs, p in c.gates:
        if g in ("id", "barrier"):
            continue
        if len(qs) == 1:
            U = one_qubit_matrix(g, p)
            cur[qs[0]] = U @ cur[qs[0]] if qs[0] in cur else U
            continue
        for q in qs:
            close(q)
        twoq.append((g, qs[0], qs[1]))
        for q in qs:
            last[q] = len(twoq) - 1
    for q in list(cur):
        close(q)
    return twoq, initial, after


def simulate_sparse(c: Circuit, max_nnz: int = MAX_NNZ):
    """Returns (keys, amps): int64 keys for n <= 62, Python-int (object) keys above (with a lower nnz cap).

    Simulation order: two-qubit gates in circuit order; each fused single-qubit segment is applied right after the
    preceding two-qubit gate on its qubit if that does not enlarge the support, otherwise just before the next two-qubit
    gate on that qubit (or at the end). Every such order is a topological order of the circuit DAG, so the final state is
    that of the circuit; the choice only keeps transient supports small."""
    kdt = np.int64 if c.n <= 62 else object
    cap = max_nnz if c.n <= 62 else min(max_nnz, DICT_MAX_NNZ)
    one = np.int64(1) if kdt is np.int64 else 1
    keys = np.zeros(1, dtype=kdt)
    if kdt is object:
        keys[0] = 0
    st = [keys, np.ones(1, dtype=complex)]
    twoq, initial, after = segments(c)
    pending: dict = {}

    def try_apply(q, M):
        k2, a2 = _apply_u(st[0], st[1], one << q, M)
        if len(k2) > len(st[0]):
            pending[q] = M
        else:
            st[0], st[1] = k2, a2

    def must_apply(q, M):
        k2, a2 = _apply_u(st[0], st[1], one << q, M)
        if len(k2) > cap:
            raise _TooLarge(len(k2))
        st[0], st[1] = k2, a2
    for q, M in sorted(initial.items()):
        try_apply(q, M)
    for k, (g, a, b) in enumerate(twoq):
        for q in (a, b):
            if q in pending:
                must_apply(q, pending.pop(q))
        keys, amps = st
        if g == "cx":
            cb, tb = one << a, one << b
            keys = np.where((keys & cb) != 0, keys ^ tb, keys)
        elif g == "cz":
            m = (one << a) | (one << b)
            amps = np.where((keys & m) == m, -amps, amps)
        else:
            raise ValueError(f"two-qubit gate {g} is not simulated")
        st[0], st[1] = keys, amps
        for q in (a, b):
            if (k, q) in after:
                try_apply(q, after[(k, q)])
    for q in sorted(pending):
        must_apply(q, pending[q])
    return st[0], st[1]


def _apply_u(keys, amps, b, U):
    bit = (keys & b) != 0
    if abs(U[0, 1]) < 1e-300 and abs(U[1, 0]) < 1e-300:          # diagonal
        return keys, np.where(bit, U[1, 1] * amps, U[0, 0] * amps)
    if abs(U[0, 0]) < 1e-300 and abs(U[1, 1]) < 1e-300:          # anti-diagonal: permutation + phases
        return keys ^ b, np.where(bit, U[0, 1] * amps, U[1, 0] * amps)
    base = keys & ~b
    ub, inv = np.unique(base, return_inverse=True)
    a0 = np.zeros(len(ub), dtype=complex)
    a1 = np.zeros(len(ub), dtype=complex)
    a0[inv[~bit]] = amps[~bit]
    a1[inv[bit]] = amps[bit]
    n0 = U[0, 0] * a0 + U[0, 1] * a1
    n1 = U[1, 0] * a0 + U[1, 1] * a1
    keys = np.concatenate([ub, ub | b])
    amps = np.concatenate([n0, n1])
    keep = np.abs(amps) > DROP
    return keys[keep], amps[keep]


def target_arrays(target: list) -> tuple[list[int], np.ndarray]:
    """target: [[index as decimal string, re, im], ...] (normalised by the checker)."""
    idx = [int(t[0]) for t in target]
    amp = np.array([complex(float(t[1]), float(t[2])) for t in target])
    return idx, amp / np.linalg.norm(amp)


def fidelity_sparse(c: Circuit, target: list, max_nnz: int = MAX_NNZ) -> float:
    idx, amp = target_arrays(target)
    keys, amps = simulate_sparse(c, max_nnz)
    nrm = float(np.linalg.norm(amps))
    psi = dict(zip(keys.tolist(), amps.tolist()))
    ov = sum(amp[i].conjugate() * psi.get(k, 0) for i, k in enumerate(idx))
    return float(abs(ov / nrm) ** 2)


def fidelity_qiskit(c: Circuit, target: list) -> float:
    from qiskit.quantum_info import Statevector
    idx, amp = target_arrays(target)
    sv = Statevector.from_instruction(c.to_qiskit()).data
    t = np.zeros(1 << c.n, dtype=complex)
    t[idx] = amp
    return float(abs(np.vdot(t, sv)) ** 2)


def permute_target(target: list, output_map: list[int]) -> list:
    """State qubit q is held by physical qubit output_map[q]: relabel the basis indices of the target."""
    out = []
    for k, re, im in target:
        x = int(k)
        y = 0
        for q, pq in enumerate(output_map):
            if (x >> q) & 1:
                y |= 1 << pq
        out.append([str(y), re, im])
    return out


def verify_state(c: Circuit, n: int, target: list, min_fidelity: float | None = None,
                 gate_set=GATE_SET_D, edges=None, output_map=None) -> StateVerdict:
    werr = width_error(c.n)   # Phase 7 C1: the width before anything else (a format failure, never a crash)
    if werr:
        return StateVerdict("fail", f"invalid circuit: {werr}")
    bad = sorted({g for g, _, _ in c.gates if g not in gate_set})
    if bad:
        return StateVerdict("fail", f"gates outside the allowed set: {bad}")
    err = signature_errors(c)        # 10-23: exact qubit / parameter count of every gate, finite numeric parameters
    if err:
        return StateVerdict("fail", f"malformed gate: {err}")
    if c.n != n:
        return StateVerdict("fail", f"circuit has {c.n} qubits, the state has {n} (no ancillas)")
    if edges is not None:
        es = {frozenset(e) for e in edges}
        off = [(g, qs) for g, qs, _ in c.gates if len(qs) == 2 and frozenset(qs) not in es]
        if off:
            return StateVerdict("fail", f"two-qubit gate {off[0][0]}{tuple(off[0][1])} not on a coupling edge")
    if output_map is not None:
        if edges is None:
            return StateVerdict("fail", "an output map is only allowed on connectivity tracks")
        if sorted(output_map) != list(range(n)):
            return StateVerdict("fail", "output map is not a permutation")
        target = permute_target(target, output_map)
    if any(isinstance(x, str) for _, _, p in c.gates for x in p):
        return StateVerdict("fail", "symbolic parameters are not allowed")
    thr = 1 - EXACT_TOL if min_fidelity is None else min_fidelity
    try:
        f = fidelity_sparse(c, target)
    except _TooLarge as e:
        return StateVerdict("unverified", f"sparse simulation exceeded {MAX_NNZ} nonzero amplitudes ({e.args[0]})")
    method = "sparse simulation"
    if n <= 16:
        f2 = fidelity_qiskit(c, target)
        method += f" + qiskit Statevector ({f2:.12f})"
        if abs(f - f2) > 1e-9:
            return StateVerdict("checker_disagreement", f"sparse {f} vs qiskit {f2}", f, {"method": method})
    if f >= thr:
        return StateVerdict("pass", "", f, {"method": method, "threshold": thr})
    return StateVerdict("fail", f"fidelity {f:.12f} < {thr}", f, {"method": method, "threshold": thr})
