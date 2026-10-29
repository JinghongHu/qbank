"""Exact contract checkers for category A.

Two independent implementations must agree:
  * "gf2":  qbank.core.pauli — symplectic propagation + signed group membership (no simulator library);
  * "stim": stim.TableauSimulator + peek_observable_expectation.
Normalisation: single-qubit Pauli corrections are free; if every target is in the prepared group up to sign,
an explicit Pauli layer is appended (recorded) and both checks are re-run on the corrected circuit.
Rejected outright: gates outside the whitelist, qubit count != required width, 2-qubit gates off the
connectivity graph, circuits that fail to parse.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..core import gf2
from ..core.circuit import Circuit, signature_errors, width_error
from ..core.pauli import PauliRows, Tableau, reduce_targets, rref

GATE_SET_A = ("h", "s", "sdg", "x", "y", "z", "sx", "sxdg", "cx", "cz", "cy", "swap", "id")


@dataclass
class Verdict:
    status: str                      # "pass" | "fail" | "error"
    reason: str = ""
    pauli_correction: list = field(default_factory=list)
    circuit: Circuit | None = None   # the (possibly corrected) circuit that was checked and must be costed
    details: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"status": self.status, "reason": self.reason, "pauli_correction": self.pauli_correction, "details": self.details}


# ------------------------------------------------------------------ targets
def targets_css_zero(hx: np.ndarray) -> PauliRows:
    """|0...0>_L of a CSS code: stabilised by all X checks and all Z operators commuting with them (+1 each)."""
    n = hx.shape[1]
    return PauliRows.css(gf2.rref(hx)[0], gf2.nullspace(hx), n)


def targets_css_codespace(hx: np.ndarray, hz: np.ndarray) -> PauliRows:
    n = hx.shape[1]
    return PauliRows.css(gf2.rref(hx)[0], gf2.rref(hz)[0], n)


def targets_from_strings(stabs: list[str], n: int) -> PauliRows:
    return rref(PauliRows.from_strings(stabs, n))[0]


# ------------------------------------------------------------------ the two checkers
def check_gf2(c: Circuit, targets: PauliRows) -> tuple[np.ndarray, np.ndarray]:
    tab = Tableau(c.n)
    for g, qs, _ in c.gates:
        tab.apply(g, qs)
    basis, piv = rref(tab.rows())
    return reduce_targets(basis, piv, targets)


def check_stim(c: Circuit, targets: PauliRows) -> tuple[np.ndarray, np.ndarray]:
    import stim
    sim = stim.TableauSimulator()
    sim.set_num_qubits(c.n)
    sim.do_circuit(c.to_stim())
    in_group = np.zeros(targets.m, dtype=bool)
    sign = np.zeros(targets.m, dtype=np.uint8)
    for i, s in enumerate(targets.to_strings()):
        e = sim.peek_observable_expectation(stim.PauliString(s))
        in_group[i] = e != 0
        sign[i] = 1 if e == -1 else 0
    return in_group, sign


def pauli_correction(targets: PauliRows, wrong: np.ndarray) -> list[tuple[str, tuple[int, ...], tuple]]:
    """Single-qubit Paulis P anticommuting exactly with targets[wrong] (targets independent)."""
    n = targets.n
    a = np.concatenate([targets.z, targets.x], axis=1)  # X^a Z^b anticommutes with (x,z) iff a.z + b.x = 1
    sol = gf2.solve(a, wrong.astype(np.uint8))
    if sol is None:
        raise ValueError("no Pauli correction exists (targets dependent?)")
    ax, bz = sol[:n], sol[n:]
    out = []
    for q in range(n):
        if ax[q] and bz[q]:
            out.append(("y", (q,), ()))
        elif ax[q]:
            out.append(("x", (q,), ()))
        elif bz[q]:
            out.append(("z", (q,), ()))
    return out


# ------------------------------------------------------------------ main entry
def verify_stabilizer_contract(c: Circuit, targets: PauliRows, *, width: int, edges=None, output_map=None,
                               gate_set=GATE_SET_A, normalize: bool = True) -> Verdict:
    """targets live on code qubits 0..targets.n-1; output_map[i] = physical qubit holding code qubit i."""
    if not isinstance(c, Circuit):
        return Verdict("error", "not a qbank Circuit")
    werr = width_error(c.n)   # Phase 7 C1: the width before anything else (a format failure, never a crash)
    if werr:
        return Verdict("fail", f"invalid circuit: {werr}")
    bad = sorted({g for g, _, _ in c.gates if g not in gate_set})
    if bad:
        return Verdict("fail", f"gates outside the allowed set: {bad}")
    err = signature_errors(c)        # 10-23: exact qubit / parameter count of every gate
    if err:
        return Verdict("fail", f"malformed gate: {err}")
    if c.n != width:
        return Verdict("fail", f"circuit width {c.n} != required {width} (no extra qubits allowed)")
    if edges is not None:
        es = {frozenset(e) for e in edges}
        off = [(g, qs) for g, qs, _ in c.gates if len(qs) == 2 and frozenset(qs) not in es]
        if off:
            return Verdict("fail", f"{len(off)} two-qubit gates off the connectivity graph, e.g. {off[0]}")
    if output_map is not None:
        om = [int(v) for v in output_map]
        if len(om) != targets.n or len(set(om)) != len(om) or any(v < 0 or v >= width for v in om):
            return Verdict("fail", "invalid output_map")
        tg = targets.relabel(om, n_out=width)
    else:
        if targets.n != width:
            return Verdict("error", "targets/width mismatch")
        tg = targets
    try:
        in_g, sg = check_gf2(c, tg)
    except ValueError as e:
        # 10-24 merge (C6 / Codex RECONCILE 17): gate names and signatures were checked above, so an exception of the
        # GF(2) routines is the checker's own failure, not a verdict on the circuit
        return Verdict("error", f"gf2 checker error: {e}")
    corr = []
    if not in_g.all():
        v_stim = check_stim(c, tg)
        agree = bool((v_stim[0] == in_g).all())
        return Verdict("fail", f"{int((~in_g).sum())} target stabilizers not in the prepared state's group",
                       details={"checkers_agree": agree})
    circ = c
    if sg.any():
        if not normalize:
            return Verdict("fail", f"{int(sg.sum())} stabilizers have the wrong sign")
        corr = pauli_correction(tg, sg.astype(bool))
        circ = c.copy()
        for g, qs, p in corr:
            circ.append(g, qs, p)
        in_g, sg = check_gf2(circ, tg)
    s_in, s_sg = check_stim(circ, tg)
    gf2_ok = bool(in_g.all() and not sg.any())
    stim_ok = bool(s_in.all() and not s_sg.any())
    if gf2_ok != stim_ok or not np.array_equal(in_g, s_in) or not np.array_equal(sg, s_sg):
        return Verdict("error", "checker disagreement (gf2 vs stim)", details={"gf2": gf2_ok, "stim": stim_ok})
    if not gf2_ok:
        return Verdict("fail", "wrong state after Pauli normalisation")
    return Verdict("pass", "", [[g, list(qs)] for g, qs, _ in corr], circ, {"checkers": ["gf2", "stim"], "checkers_agree": True})
