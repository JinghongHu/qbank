"""Exact contract checkers for category B oracles.

Register layout (from the instance's public part): inputs x on qubits 0..n-1, outputs y on n..n+m-1, the rest are
ancillas that start in |0>. Allowed gates (GATE_SET_B): classical reversible gates, diagonal phase gates, Qiskit's
relative-phase Toffolis RCCX / RC3X as whole gates, and the measurement-based uncomputation primitive
    ("mbu", (q,), (correction,))  -- measure q in the X basis; if the outcome is 1 apply `correction` (diagonal gates,
                                       never on q itself); afterwards q is |0>.
Checking:
  * exhaustive (n_in + n_y <= EXHAUSTIVE_BITS): every basis input is simulated as "permutation + phase" with
    bit-parallel words (64 inputs per word) and phases mod 8 (units of pi/4) kept as three bit-planes;
  * otherwise a SAT miter (CaDiCaL 1.9.5 via pysat, in a child process killed at the time limit). Only +-1 phases can be carried into the miter (phase parity as XOR);
    circuits with S/T/RCCX/RC3X phases above the exhaustive limit are reported "unverified" (never counted as correct).
mbu: branch analysis — the outcome-1 branch differs from the outcome-0 branch by phase (-1)^{q(x)} times the
correction's phase; both branches agree (up to a global phase) iff correction phase = 4*q(x) + const (mod 8).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..core.aig import AIG
from ..core.circuit import Circuit, gate_signature_error, signature_errors, width_error

GATE_SET_B = ("x", "cx", "ccx", "ccz", "rccx", "rc3x", "swap", "z", "s", "sdg", "t", "tdg", "cz", "id", "mbu")
DIAGONAL = {"z": 4, "s": 2, "sdg": 6, "t": 1, "tdg": 7}          # single-qubit phase in units of pi/4 when the bit is 1
DIAG_2Q = {"cz": 4}
DIAG_3Q = {"ccz": 4}
# (input basis index -> output basis index, phase in pi/4) for Qiskit 2.5.2's RCCXGate / RC3XGate (little-endian,
# gate qubit j = bit j). Re-derived from qiskit.quantum_info.Operator in tests/test_b_contracts.py.
RCCX = [(0, 0), (1, 0), (2, 0), (7, 2), (4, 0), (5, 4), (6, 0), (3, 6)]
RC3X = [(0, 0), (1, 0), (2, 0), (3, 2), (4, 0), (5, 0), (6, 0), (15, 4), (8, 0), (9, 0), (10, 0), (11, 6),
        (12, 0), (13, 0), (14, 0), (7, 0)]
EXHAUSTIVE_BITS = 22
ONES = np.uint64(0xFFFFFFFFFFFFFFFF)


@dataclass
class OracleVerdict:
    status: str                      # pass | fail | unverified | error
    reason: str = ""
    method: str = ""
    details: dict = field(default_factory=dict)


# ============================================================================ bit-parallel simulator
class _Phase:
    """Phase mod 8 per input as three packed bit-planes."""

    def __init__(self, W):
        self.b = [np.zeros(W, np.uint64) for _ in range(3)]

    def add(self, k: int, cond: np.ndarray) -> None:
        k %= 8
        for bit in range(3):
            if not (k >> bit) & 1:
                continue
            c = cond
            for j in range(bit, 3):     # ripple-carry add of c at position `bit`
                old = self.b[j]
                self.b[j] = old ^ c
                c = old & c
                if not c.any():
                    break

    def value(self, N: int) -> np.ndarray:
        out = np.zeros(N, dtype=np.int64)
        for j in range(3):
            out += AIG.unpack(self.b[j][None, :], N)[0].astype(np.int64) << j
        return out


def _pattern_cond(bits: list[np.ndarray], pattern: int) -> np.ndarray:
    c = np.full_like(bits[0], ONES)
    for j, v in enumerate(bits):
        c &= v if (pattern >> j) & 1 else (v ^ ONES)
    return c


class ClassicalSim:
    def __init__(self, width: int, inputs: dict[int, np.ndarray], W: int):
        self.v = [np.zeros(W, np.uint64) for _ in range(width)]
        for q, pat in inputs.items():
            self.v[q] = pat.copy()
        self.ph = _Phase(W)
        self.W = W
        self.mbu_residuals: list = []

    def apply(self, g: str, qs, params=()):
        v = self.v
        if g == "id":
            return
        if g == "x":
            v[qs[0]] = v[qs[0]] ^ ONES
        elif g == "cx":
            v[qs[1]] = v[qs[1]] ^ v[qs[0]]
        elif g == "ccx":
            v[qs[2]] = v[qs[2]] ^ (v[qs[0]] & v[qs[1]])
        elif g == "swap":
            v[qs[0]], v[qs[1]] = v[qs[1]], v[qs[0]]
        elif g in DIAGONAL:
            self.ph.add(DIAGONAL[g], v[qs[0]])
        elif g == "cz":
            self.ph.add(4, v[qs[0]] & v[qs[1]])
        elif g == "ccz":
            self.ph.add(4, v[qs[0]] & v[qs[1]] & v[qs[2]])
        elif g in ("rccx", "rc3x"):
            table = RCCX if g == "rccx" else RC3X
            bits = [v[q] for q in qs]
            for inp, (outp, ph) in enumerate(table):
                if ph:
                    self.ph.add(ph, _pattern_cond(bits, inp))
            ctrl = bits[0]
            for b in bits[1:-1]:
                ctrl = ctrl & b
            v[qs[-1]] = v[qs[-1]] ^ ctrl    # both tables permute exactly like a (multi-)controlled X on the last qubit
        elif g == "mbu":
            q = qs[0]
            corr = params[0] if params else ()
            # phase of the correction applied on the current state (fresh accumulator)
            acc = _Phase(self.W)
            for cg, cqs in corr:
                if cg in DIAGONAL:
                    acc.add(DIAGONAL[cg], v[cqs[0]])
                elif cg == "cz":
                    acc.add(4, v[cqs[0]] & v[cqs[1]])
                elif cg == "ccz":
                    acc.add(4, v[cqs[0]] & v[cqs[1]] & v[cqs[2]])
                elif cg == "id":
                    continue
                else:
                    raise ValueError(f"mbu correction may only contain diagonal gates, got {cg}")
            acc.add(4, v[q])          # the outcome-1 branch also carries (-1)^{q(x)}
            self.mbu_residuals.append(acc)
            v[q] = np.zeros(self.W, np.uint64)
        else:
            raise ValueError(f"gate {g} not supported by the oracle checker")


def _input_patterns(k: int) -> tuple[np.ndarray, int]:
    N = 1 << k
    return AIG.input_patterns(k), N


def _const(arr: np.ndarray) -> bool:
    return bool((arr == arr[0]).all())


# ============================================================================ exhaustive check
def check_exhaustive(c: Circuit, f: AIG, n: int, m: int, kind: str) -> OracleVerdict:
    """kind: 'bitflip' (x, y -> x, y xor f(x)) or 'phase' (x -> (-1)^f(x) x)."""
    k = n + (m if kind == "bitflip" else 0)
    pats, N = _input_patterns(k)
    W = pats.shape[1]
    inputs = {q: pats[q] for q in range(k)}
    sim = ClassicalSim(c.n, inputs, W)
    for g, qs, p in c.gates:
        sim.apply(g, qs, p)
    valid = AIG.unpack(np.full((1, W), ONES), N)[0]   # all ones (N may be < 64)
    fx = f.simulate(pats[:n])                          # (m, W) packed f(x) for every (x, y) pattern
    errs = []
    for q in range(n):
        if (AIG.unpack((sim.v[q] ^ pats[q])[None, :], N) & valid).any():
            errs.append(f"input qubit {q} changed")
    if kind == "bitflip":
        for j in range(m):
            want = pats[n + j] ^ fx[j]
            if AIG.unpack((sim.v[n + j] ^ want)[None, :], N).any():
                errs.append(f"output {j} != y xor f(x)")
    for q in range(k, c.n):
        if AIG.unpack(sim.v[q][None, :], N).any():
            errs.append(f"ancilla qubit {q} not returned to |0>")
    if errs:
        return OracleVerdict("fail", "; ".join(errs[:4]), "exhaustive", {"inputs": N})
    ph = sim.ph.value(N)
    for acc in sim.mbu_residuals:
        r = acc.value(N)
        if not _const(r):
            return OracleVerdict("fail", "mbu correction does not cancel the measurement phase on every input", "exhaustive")
    if kind == "bitflip":
        if not _const(ph):
            return OracleVerdict("fail", "input-dependent phase (relative phases not cancelled)", "exhaustive",
                                 {"distinct_phases": sorted(set(ph.tolist()))[:8]})
    else:
        f0 = AIG.unpack(fx, N)[0].astype(np.int64)
        rel = (ph - 4 * f0) % 8
        if not _const(rel):
            return OracleVerdict("fail", "phase is not (-1)^f(x) up to a global phase", "exhaustive")
    return OracleVerdict("pass", "", "exhaustive", {"inputs": N})


# ============================================================================ SAT miter (large inputs)
def check_sat(c: Circuit, f: AIG, n: int, m: int, kind: str, time_limit: float = 600.0) -> OracleVerdict:
    from pysat.formula import IDPool
    from pysat.solvers import Solver
    if any(g in ("s", "sdg", "t", "tdg", "rccx", "rc3x") for g, _, _ in c.gates) or \
            any(cg in ("s", "sdg", "t", "tdg") for g, _, p in c.gates if g == "mbu" for cg, _ in (p[0] if p else ())):
        return OracleVerdict("unverified", "non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check", "sat")
    pool = IDPool()
    cls: list[list[int]] = []
    TRUE = pool.id("TRUE")
    cls.append([TRUE])

    def new():
        return pool.id(("t", len(pool.obj2id)))

    def AND(a, b):
        if a == -TRUE or b == -TRUE:
            return -TRUE
        if a == TRUE:
            return b
        if b == TRUE:
            return a
        o = new()
        cls.extend([[-o, a], [-o, b], [o, -a, -b]])
        return o

    def XOR(a, b):
        if a == -TRUE:
            return b
        if b == -TRUE:
            return a
        if a == TRUE:
            return -b
        if b == TRUE:
            return -a
        o = new()
        cls.extend([[-o, a, b], [-o, -a, -b], [o, -a, b], [o, a, -b]])
        return o

    k = n + (m if kind == "bitflip" else 0)
    xin = [pool.id(("in", i)) for i in range(k)]
    val = xin + [-TRUE] * (c.n - k)
    phase = -TRUE
    mbu_res: list[int] = []
    for g, qs, p in c.gates:
        if g == "id":
            continue
        if g == "x":
            val[qs[0]] = -val[qs[0]]
        elif g == "cx":
            val[qs[1]] = XOR(val[qs[1]], val[qs[0]])
        elif g == "ccx":
            val[qs[2]] = XOR(val[qs[2]], AND(val[qs[0]], val[qs[1]]))
        elif g == "swap":
            val[qs[0]], val[qs[1]] = val[qs[1]], val[qs[0]]
        elif g == "z":
            phase = XOR(phase, val[qs[0]])
        elif g == "cz":
            phase = XOR(phase, AND(val[qs[0]], val[qs[1]]))
        elif g == "ccz":
            phase = XOR(phase, AND(AND(val[qs[0]], val[qs[1]]), val[qs[2]]))
        elif g == "mbu":
            q = qs[0]
            res = val[q]
            for cg, cqs in (p[0] if p else ()):
                if cg == "z":
                    res = XOR(res, val[cqs[0]])
                elif cg == "cz":
                    res = XOR(res, AND(val[cqs[0]], val[cqs[1]]))
                elif cg == "ccz":
                    res = XOR(res, AND(AND(val[cqs[0]], val[cqs[1]]), val[cqs[2]]))
            mbu_res.append(res)      # must be constant over all inputs (checked in the miter below)
            val[q] = -TRUE
        else:
            return OracleVerdict("error", f"gate {g} not supported by the SAT checker", "sat")
    # f(x) via Tseitin on the AIG
    lit_of = {0: -TRUE}
    for i in range(n):
        lit_of[i + 1] = xin[i]

    def aig_lit(l):
        v = lit_of[l >> 1]
        return -v if l & 1 else v
    for j, (a, b) in enumerate(f.ands):
        lit_of[f.num_inputs + 1 + j] = AND(aig_lit(a), aig_lit(b))
    fx = [aig_lit(l) for l in f.outputs]
    diffs = []
    for q in range(n):
        diffs.append(XOR(val[q], xin[q]))
    if kind == "bitflip":
        for j in range(m):
            diffs.append(XOR(val[n + j], XOR(xin[n + j], fx[j])))
    for q in range(k, c.n):
        diffs.append(val[q])
    # phase: evaluate at the all-zero input classically to get the constant, then require equality everywhere
    z = [0] * c.n
    ph0 = _eval_phase_parity(c, z)
    f0 = f.eval(0)[0] if kind == "phase" else 0
    want_phase = XOR(fx[0], TRUE if (ph0 ^ f0) else -TRUE) if kind == "phase" else (TRUE if ph0 else -TRUE)
    diffs.append(XOR(phase, want_phase))
    r0 = _eval_mbu_residual_at_zero(c)
    for res, r in zip(mbu_res, r0):
        diffs.append(XOR(res, TRUE if r else -TRUE))
    cls.append(diffs)
    from ..core.satutil import solve_with_timeout
    status, _ = solve_with_timeout(cls, time_limit)          # CaDiCaL in a child process, killed at the limit
    if status == "timeout":
        return OracleVerdict("unverified", f"SAT miter exceeded {time_limit:.0f} s", "sat")
    if status == "sat":
        return OracleVerdict("fail", "SAT miter found an input violating the contract", "sat")
    return OracleVerdict("pass", "", "sat", {"clauses": len(cls)})


def _eval_phase_parity(c: Circuit, bits: list[int]) -> int:
    b = list(bits)
    ph = 0
    for g, qs, p in c.gates:
        if g == "x":
            b[qs[0]] ^= 1
        elif g == "cx":
            b[qs[1]] ^= b[qs[0]]
        elif g == "ccx":
            b[qs[2]] ^= b[qs[0]] & b[qs[1]]
        elif g == "swap":
            b[qs[0]], b[qs[1]] = b[qs[1]], b[qs[0]]
        elif g == "z":
            ph ^= b[qs[0]]
        elif g == "cz":
            ph ^= b[qs[0]] & b[qs[1]]
        elif g == "ccz":
            ph ^= b[qs[0]] & b[qs[1]] & b[qs[2]]
        elif g == "mbu":
            b[qs[0]] = 0
    return ph


def _eval_mbu_residual_at_zero(c: Circuit) -> list[int]:
    b = [0] * c.n
    out = []
    for g, qs, p in c.gates:
        if g == "x":
            b[qs[0]] ^= 1
        elif g == "cx":
            b[qs[1]] ^= b[qs[0]]
        elif g == "ccx":
            b[qs[2]] ^= b[qs[0]] & b[qs[1]]
        elif g == "swap":
            b[qs[0]], b[qs[1]] = b[qs[1]], b[qs[0]]
        elif g == "mbu":
            r = b[qs[0]]
            for cg, cqs in (p[0] if p else ()):
                if cg == "z":
                    r ^= b[cqs[0]]
                elif cg == "cz":
                    r ^= b[cqs[0]] & b[cqs[1]]
                elif cg == "ccz":
                    r ^= b[cqs[0]] & b[cqs[1]] & b[cqs[2]]
            out.append(r)
            b[qs[0]] = 0
    return out


# ============================================================================ entry point
MBU_CORRECTION_GATES = ("z", "s", "sdg", "t", "tdg", "cz", "ccz", "id")


def _signature_error_b(c: Circuit) -> str | None:
    """Every gate must have exactly the qubits and parameters of GATE_SIGNATURES (e.g. rccx exactly 3 qubits: the
    simulator would otherwise treat extra qubits as extra controls), integer in-range distinct qubits (also for a
    Circuit built without append, 10-24 merge C1); an mbu correction is one layer of (gate, qubits) pairs, each gate
    in MBU_CORRECTION_GATES (the one list of allowed correction gates; the task statements quote it) with the same
    rule (circuit.gate_signature_error)."""
    err = signature_errors(c)
    if err:
        return err
    for k, (g, qs, p) in enumerate(c.gates):
        if g != "mbu":
            continue
        for cg, cqs in p[0]:
            if cg not in MBU_CORRECTION_GATES:
                return f"gate #{k}: mbu correction may only contain diagonal gates {MBU_CORRECTION_GATES}, got {cg!r}"
            # 10-29 (Codex review): the correction acts after the measurement, when the measured qubit no longer holds
            # its computational value; the simulators would price it with the pre-measurement value, so a correction
            # on the measured qubit is rejected (it has no physical effect on the other qubits anyway)
            if qs[0] in cqs:
                return f"gate #{k}: mbu correction acts on the measured qubit {qs[0]}"
    return None


def verify_oracle(c: Circuit, f: AIG, n: int, m: int, kind: str, budget: int | None = None,
                  gate_set=GATE_SET_B) -> OracleVerdict:
    werr = width_error(c.n)   # Phase 7 C1: the width before anything else (a format failure, never a crash)
    if werr:
        return OracleVerdict("fail", f"invalid circuit: {werr}")
    bad = sorted({g for g, _, _ in c.gates if g not in gate_set})
    if bad:
        return OracleVerdict("fail", f"gates outside the allowed set: {bad}")
    err = _signature_error_b(c)       # 10-23: exact qubit / parameter count of every gate before any simulation
    if err:
        return OracleVerdict("fail", f"malformed gate: {err}")
    k = n + (m if kind == "bitflip" else 0)
    if c.n < k:
        return OracleVerdict("fail", f"circuit has {c.n} qubits < {k} register qubits")
    if budget is not None and c.n > budget:
        return OracleVerdict("fail", f"circuit uses {c.n} qubits > budget {budget}")
    try:
        if k <= EXHAUSTIVE_BITS:
            return check_exhaustive(c, f, n, m, kind)
        return _check_sat_memo(c, f, n, m, kind)
    except ValueError as e:
        # 10-24 merge (C6 / Codex RECONCILE 17): every malformed gate is rejected above, before any simulation, so a
        # ValueError from the simulators is the checker's own failure, not a verdict on the circuit
        return OracleVerdict("error", f"checker error: {e}")


def _check_sat_memo(c: Circuit, f: AIG, n: int, m: int, kind: str) -> OracleVerdict:
    """check_sat with a verdict memo (v1.2): the SAT miter is the expensive part, and the same circuit is often checked
    once per track (e.g. tof@inf, cx@inf and the ccx variant of t_mbu@inf). The memo key is the SHA-256 of the
    function (AIGER bytes), n, m, kind and the exact circuit, so a hit is the verdict of the identical check. An
    "unverified" verdict (SAT limit reached) is memoised as well; it is never counted as correct."""
    import hashlib
    import json
    import os
    import tempfile
    from ..core.instance import data_root
    h = hashlib.sha256()
    h.update(f.to_aiger_binary())
    h.update(json.dumps([n, m, kind, c.to_json()], sort_keys=True).encode())
    key = h.hexdigest()
    p = data_root() / "cache" / "verify-B" / key[:2] / f"{key}.json"
    if p.exists():
        d = json.loads(p.read_text())
        return OracleVerdict(d["status"], d["reason"], d["method"], {**d.get("details", {}), "memo": key[:16]})
    v = check_sat(c, f, n, m, kind)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        json.dump({"status": v.status, "reason": v.reason, "method": v.method, "details": v.details}, fh)
    os.replace(tmp, p)
    return v
