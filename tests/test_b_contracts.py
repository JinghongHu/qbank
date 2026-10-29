"""Category B oracle contracts: positive and negative controls."""
import cmath

import numpy as np
import pytest

from qbank.contracts.oracle import RC3X, RCCX, verify_oracle
from qbank.core.aig import AIG
from qbank.core.circuit import Circuit


def maj3():
    g = AIG(3)
    a, b, c = (g.input_lit(i) for i in range(3))
    g.add_output(g.MAJ(a, b, c))
    return g.cleanup()


def bennett(f: AIG, and_gate="ccx", uncompute="same", phase=False):
    """Textbook Bennett: one ancilla per AND node, copy outputs, uncompute in reverse order."""
    n, m = f.num_inputs, len(f.outputs)
    k = n + (0 if phase else m)
    anc0 = k
    width = k + len(f.ands) + (1 if phase else 0)
    c = Circuit(width)
    q_of = {i + 1: i for i in range(n)}
    ops = []
    for j, (a, b) in enumerate(f.ands):
        t = anc0 + j
        q_of[n + 1 + j] = t
        qa, qb = q_of[a >> 1], q_of[b >> 1]
        flips = [q for q, lit in ((qa, a), (qb, b)) if lit & 1]
        ops.append((flips, qa, qb, t))
    for flips, qa, qb, t in ops:
        for q in flips:
            c.append("x", [q])
        c.append(and_gate, [qa, qb, t])
        for q in flips:
            c.append("x", [q])
    out_q = [q_of[l >> 1] for l in f.outputs]
    if phase:
        tq = width - 1
        c.append("cx", [out_q[0], tq])
        if f.outputs[0] & 1:
            c.append("x", [tq])
        c.append("z", [tq])
        if f.outputs[0] & 1:
            c.append("x", [tq])
        c.append("cx", [out_q[0], tq])
    else:
        for j, (l, q) in enumerate(zip(f.outputs, out_q)):
            c.append("cx", [q, n + j])
            if l & 1:
                c.append("x", [n + j])
    for flips, qa, qb, t in reversed(ops):
        if uncompute == "none":
            continue
        for q in flips:
            c.append("x", [q])
        if uncompute == "mbu":
            c.append("mbu", [t], [(("cz", (qa, qb)),)])
        elif uncompute == "mbu_nocorr":
            c.append("mbu", [t], [()])
        else:
            c.append(and_gate if uncompute == "same" else uncompute, [qa, qb, t])
        for q in flips:
            c.append("x", [q])
    return c


def test_rccx_rc3x_tables_match_qiskit():
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import RC3XGate, RCCXGate
    from qiskit.quantum_info import Operator
    for gate, k, table in ((RCCXGate(), 3, RCCX), (RC3XGate(), 4, RC3X)):
        qc = QuantumCircuit(k)
        qc.append(gate, range(k))
        U = Operator(qc).data
        for col in range(2 ** k):
            row = int(np.argmax(np.abs(U[:, col])))
            ph = round(cmath.phase(U[row, col]) / (np.pi / 4)) % 8
            assert (row, ph) == table[col]


def test_bennett_positive_and_dirty_negative():
    f = maj3()
    assert verify_oracle(bennett(f), f, 3, 1, "bitflip").status == "pass"
    assert verify_oracle(bennett(f, uncompute="none"), f, 3, 1, "bitflip").status == "fail"


def test_relative_phase_toffoli():
    f = maj3()
    assert verify_oracle(bennett(f, and_gate="rccx"), f, 3, 1, "bitflip").status == "pass"      # RCCX is self-inverse
    v = verify_oracle(bennett(f, and_gate="rccx", uncompute="ccx"), f, 3, 1, "bitflip")          # phases not cancelled
    assert v.status == "fail" and "phase" in v.reason


def test_mbu_uncompute():
    f = maj3()
    assert verify_oracle(bennett(f, uncompute="mbu"), f, 3, 1, "bitflip").status == "pass"
    assert verify_oracle(bennett(f, uncompute="mbu_nocorr"), f, 3, 1, "bitflip").status == "fail"


def test_phase_oracle_and_wrong_contract():
    f = maj3()
    assert verify_oracle(bennett(f, phase=True), f, 3, 1, "phase").status == "pass"
    # a bit-flip oracle is not a phase oracle (and vice versa)
    assert verify_oracle(bennett(f), f, 3, 1, "phase").status == "fail"


def test_entangled_ancilla_rejected():
    """Output bit correct but an ancilla keeps a copy of the data (entangled garbage)."""
    f = maj3()
    c = bennett(f)
    c2 = Circuit(c.n + 1, list(c.gates))
    c2.append("cx", [0, c.n])            # garbage copy of x0 left in a fresh ancilla
    assert verify_oracle(c2, f, 3, 1, "bitflip").status == "fail"


def test_sat_path_large_inputs():
    """> 22 register bits: SAT miter (+-1 phases only)."""
    n = 24
    g = AIG(n)
    lits = [g.input_lit(i) for i in range(n)]
    g.add_output(g.XOR(g.AND_n(lits[:12]), g.OR_n(lits[12:])))
    f = g.cleanup()
    c = bennett(f)
    assert verify_oracle(c, f, n, 1, "bitflip").status == "pass"
    bad = Circuit(c.n, list(c.gates[:-1]))       # drop the last uncompute gate
    assert verify_oracle(bad, f, n, 1, "bitflip").status == "fail"
    c_rc = bennett(f, and_gate="rccx")
    assert verify_oracle(c_rc, f, n, 1, "bitflip").status == "unverified"   # non-+-1 phases above the exhaustive limit
    assert verify_oracle(bennett(f, uncompute="mbu"), f, n, 1, "bitflip").status == "pass"
    assert verify_oracle(bennett(f, uncompute="mbu_nocorr"), f, n, 1, "bitflip").status == "fail"


def test_budget_and_gate_set():
    f = maj3()
    c = bennett(f)
    assert verify_oracle(c, f, 3, 1, "bitflip", budget=c.n - 1).status == "fail"
    weird = Circuit(c.n, list(c.gates) + [("h", (0,), ())])
    assert verify_oracle(weird, f, 3, 1, "bitflip").status == "fail"
    js = bennett(f, uncompute="mbu")
    assert Circuit.from_json(js.to_json()).gates == js.gates


def test_mbu_correction_on_measured_qubit_rejected():
    """10-29 (Codex review): f(x) = x; CX(x,y), CX(x,a), mbu(a) with the correction Z(a) on the measured qubit itself.
    The correction cannot remove the measurement phase (-1)^x from the data register (fidelity 1/2 on superposed
    inputs), so the circuit is wrong; the correct correction Z(x) passes."""
    g = AIG(1)
    g.add_output(g.input_lit(0))
    bad = Circuit(3, [("cx", (0, 1), ()), ("cx", (0, 2), ()), ("mbu", (2,), ((("z", (2,)),),))])
    good = Circuit(3, [("cx", (0, 1), ()), ("cx", (0, 2), ()), ("mbu", (2,), ((("z", (0,)),),))])
    assert verify_oracle(bad, g, 1, 1, "bitflip").status == "fail"
    assert verify_oracle(good, g, 1, 1, "bitflip").status == "pass"
