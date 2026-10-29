"""Category A contract checks: positive and negative controls."""
import json

import numpy as np
import pytest

from qbank.categories.A import codes as C
from qbank.categories.A.instances import css_instance, stab_instance, verify
from qbank.contracts.stabilizer import targets_css_zero, verify_stabilizer_contract
from qbank.core.circuit import Circuit
from qbank.core.instance import data_root, load_index, load_public


def _stim_prep(rows):
    import stim
    t = stim.Tableau.from_stabilizers([stim.PauliString(s) for s in rows.to_strings()], allow_redundant=True)
    return Circuit.from_stim(t.to_circuit("elimination"), rows.n)


CODES = [C.color_code("666", 3), C.rotated_surface(3), C.mqt_named("carbon"), C.quantum_hamming(4), C.rotated_surface(4),
         C.quantum_reed_muller(4), C.shor_type(3, 5), C.iceberg(3)]


@pytest.mark.parametrize("code", CODES, ids=lambda c: c.name)
def test_positive_and_negative_css(code):
    inst = css_instance("t", code, "t", {}, {}, {})
    pub = inst.public
    good = _stim_prep(targets_css_zero(code.hx))
    assert verify(pub, "a2a_2q", good).status == "pass"
    # (1) wrong sign, no Pauli correction allowed -> rejected
    bad = good.copy()
    for q in range(code.n):
        trial = good.copy()
        trial.append("x", [q])
        v = verify_stabilizer_contract(trial, targets_css_zero(code.hx), width=code.n, normalize=False)
        if v.status == "fail":
            bad = trial
            break
    assert verify_stabilizer_contract(bad, targets_css_zero(code.hx), width=code.n, normalize=False).status == "fail"
    # ... but with the explicit normalisation step it is repaired and passes (free Pauli layer)
    assert verify(pub, "a2a_2q", bad).status == "pass"
    # (2) codespace states that are not |0_L>:
    #   |1_L> (= X-bar |0_L>) differs only by signs: rejected without Pauli normalisation. (With the free single-qubit
    #   Pauli normalisation of the contract it is repaired, because X-bar is itself a product of single-qubit Paulis.)
    lx, _ = C.css_logicals(code.hx, code.hz)
    flip = good.copy()
    for q in np.flatnonzero(lx[0]):
        flip.append("x", [int(q)])
    assert verify_stabilizer_contract(flip, targets_css_zero(code.hx), width=code.n, normalize=False).status == "fail"
    assert verify(pub, "codespace_a2a_2q", flip).status == "pass"
    #   |+_L> has a different stabilizer group: rejected under css_logical_zero even with normalisation,
    #   accepted under codespace_state.
    from qbank.core.pauli import PauliRows
    zt = targets_css_zero(code.hz)
    plus = _stim_prep(PauliRows(zt.z.copy(), zt.x.copy(), zt.r.copy()))
    assert verify(pub, "a2a_2q", plus).status == "fail"
    assert verify(pub, "codespace_a2a_2q", plus).status == "pass"
    # (3) gates outside the whitelist, extra qubits, off-graph gates -> rejected
    weird = good.copy()
    weird.gates.append(("iswap", (0, 1), ()))
    assert verify(pub, "a2a_2q", weird).status == "fail"
    wide = Circuit(code.n + 1, list(good.gates))
    assert verify(pub, "a2a_2q", wide).status == "fail"
    off = [g for g in good.gates if len(g[1]) == 2 and abs(g[1][0] - g[1][1]) > 1]
    if off:
        assert verify(pub, "line_2q", good).status == "fail"


def test_output_map_relabelling():
    code = C.rotated_surface(3)
    pub = css_instance("t", code, "t", {}, {}, {}).public
    good = _stim_prep(targets_css_zero(code.hx))
    perm = list(np.random.default_rng(0).permutation(code.n))
    moved = good.relabel(perm)
    assert verify(pub, "a2a_2q", moved).status == "fail"
    assert verify(pub, "a2a_2q", moved, output_map=perm).status == "pass"


def test_noncss_zero_state():
    code = C.with_logical_z(C.five_qubit())
    zero, st = C.zero_state_rows(code), C.code_stabilizer_rows(code)
    pub = stab_instance("t", zero, "t", {}, {}, {}, code_stabs=st, graphs=False).public
    good = _stim_prep(zero)
    assert verify(pub, "a2a_2q", good).status == "pass"
    x_bar = good.copy()
    for q in range(5):
        x_bar.append("x", [q])   # XXXXX is a logical X: |1_L> differs from |0_L> only by a sign
    from qbank.contracts.stabilizer import targets_from_strings
    assert verify_stabilizer_contract(x_bar, targets_from_strings(pub["stabilizers"], 5), width=5, normalize=False).status == "fail"
    assert verify(pub, "codespace_a2a_2q", x_bar).status == "pass"
    # |+_L>: code stabilizers + X-bar -> a different stabilizer group: rejected even after normalisation
    from qbank.core.pauli import PauliRows
    plus_rows = PauliRows.from_strings(st.to_strings() + ["+XXXXX"], 5)
    plus = _stim_prep(plus_rows)
    assert verify(pub, "a2a_2q", plus).status == "fail"
    assert verify(pub, "codespace_a2a_2q", plus).status == "pass"


def test_recorded_best_circuits_reverify():
    """Every best_known circuit on disk re-verifies (positive control over the correct outputs of the baseline tools)."""
    p = data_root() / "baselines" / "A" / "best_known.jsonl"
    if not p.exists():
        pytest.skip("baselines not aggregated yet")
    rows = [json.loads(l) for l in p.read_text().splitlines()]
    idx = {r["id"]: r for r in load_index("A")}
    checked = 0
    for r in rows:
        if r.get("source_kind") != "baseline":
            continue
        d = json.loads((data_root() / (r["circuit_path"] + ".json")).read_text())
        pub = load_public("A", idx[r["instance_id"]]["hash"])
        v = verify(pub, r["track"], Circuit.from_json(d["circuit"]), d.get("output_map"))
        assert v.status == "pass", (r["instance_id"], r["track"], v.reason)
        checked += 1
    assert checked > 0
