"""Core algebra: GF(2) routines and the independent Pauli/tableau checker agree with stim (two
independent implementations must agree)."""
import numpy as np
import stim

from qbank.core import gf2
from qbank.core.circuit import Circuit
from qbank.core.pauli import PauliRows, Tableau, reduce_targets, rref

ONEQ = ["h", "s", "sdg", "x", "y", "z", "sx", "sxdg"]
TWOQ = ["cx", "cz", "cy", "swap"]


def random_circuit(rng, n, m):
    c = Circuit(n)
    for _ in range(m):
        if n >= 2 and rng.random() < 0.5:
            a, b = rng.choice(n, 2, replace=False)
            c.append(str(rng.choice(TWOQ)), [a, b])
        else:
            c.append(str(rng.choice(ONEQ)), [int(rng.integers(n))])
    return c


def test_gf2_solve_nullspace_inverse():
    rng = np.random.default_rng(0)
    for _ in range(200):
        r, c = rng.integers(1, 12, 2)
        a = rng.integers(0, 2, (r, c), dtype=np.uint8)
        b = np.concatenate([a @ rng.integers(0, 2, (c, 3)) % 2, rng.integers(0, 2, (r, 2))], axis=1).astype(np.uint8)
        x, ok = gf2.solve_many(a, b)
        for j in range(b.shape[1]):
            assert ok[j] == (gf2.rank(np.hstack([a, b[:, [j]]])) == gf2.rank(a))
            if ok[j]:
                assert ((a @ x[:, j]) % 2 == b[:, j]).all()
        ns = gf2.nullspace(a)
        assert (a.astype(int) @ ns.T.astype(int) % 2 == 0).all()
        assert ns.shape[0] == c - gf2.rank(a)
        m = gf2.random_invertible(int(r), rng)
        assert ((m.astype(int) @ gf2.inverse(m).astype(int)) % 2 == np.eye(r)).all()


def test_pauli_checker_matches_stim():
    rng = np.random.default_rng(1)
    for _ in range(150):
        n = int(rng.integers(1, 10))
        c = random_circuit(rng, n, int(rng.integers(0, 50)))
        tab = Tableau(n)
        for g, qs, _ in c.gates:
            tab.apply(g, qs)
        basis, piv = rref(tab.rows())
        sim = stim.TableauSimulator()
        sim.set_num_qubits(n)
        sim.do_circuit(c.to_stim())
        for _ in range(8):
            s = ("-" if rng.random() < .5 else "+") + "".join(rng.choice(list("IXYZ"), n))
            e = sim.peek_observable_expectation(stim.PauliString(s))
            ing, sg = reduce_targets(basis, piv, PauliRows.from_strings([s], n))
            mine = 0 if not ing[0] else (1 if sg[0] == 0 else -1)
            assert mine == e


def test_circuit_roundtrips():
    rng = np.random.default_rng(2)
    for _ in range(50):
        n = int(rng.integers(1, 7))
        c = random_circuit(rng, n, 30)
        assert Circuit.from_stim(c.to_stim(), n).gates == c.gates
        assert Circuit.from_qiskit(c.to_qiskit(), clifford_only=True).gates == c.gates
        assert Circuit.from_json(c.to_json()).gates == c.gates
