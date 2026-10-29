"""Category D state contracts and data integrity."""
import json
import math

import numpy as np
import pytest

from qbank.baselines import tools_d as T
from qbank.categories.D import generate as G
from qbank.categories.D.instances import verify
from qbank.contracts.state import fidelity_sparse, simulate_sparse
from qbank.core.circuit import Circuit
from qbank.core.instance import data_root, load_index, load_public
from qbank.core.splits import load_manifest


def test_sparse_simulator_matches_qiskit():
    from qiskit.quantum_info import Statevector
    rng = np.random.default_rng(3)
    for _ in range(100):
        n = int(rng.integers(1, 6))
        c = Circuit(n)
        for _ in range(30):
            if rng.random() < 0.3 and n > 1:
                a, b = rng.choice(n, 2, replace=False)
                c.append(str(rng.choice(["cx", "cz"])), [int(a), int(b)])
            else:
                g = str(rng.choice(["h", "t", "sx", "ry", "rz", "u"]))
                p = [float(x) for x in rng.uniform(-3, 3, {"ry": 1, "rz": 1, "u": 3}.get(g, 0))]
                c.append(g, [int(rng.integers(n))], p)
        sv = Statevector.from_instruction(c.to_qiskit()).data
        tgt = [[str(i), a.real, a.imag] for i, a in enumerate(sv) if abs(a) > 1e-14]
        assert abs(fidelity_sparse(c, tgt) - 1) < 1e-10


def test_exact_passes_and_perturbation_fails():
    pub = G.gen_dicke(8, 2, "train").inst.public
    c = T.dicke_circuit(8, 2)
    assert verify(pub, "cx", c).status == "pass"
    g = list(c.gates)
    i = next(j for j, x in enumerate(g) if x[0] == "ry")
    g[i] = ("ry", g[i][1], (g[i][2][0] + 1e-4,))
    c2 = Circuit(8)
    for x in g:
        c2.append(*x)
    assert verify(pub, "cx", c2).status == "fail"


def test_relative_phase_matters_and_global_phase_does_not():
    pub = G.gen_w(3, "train").inst.public
    c = T.w_cascade(3)
    c_glob = Circuit(3)
    for x in c.gates:
        c_glob.append(*x)
    c_glob.append("x", [0]); c_glob.append("z", [0]); c_glob.append("x", [0]); c_glob.append("z", [0])   # -1 global phase
    assert verify(pub, "cx", c_glob).status == "pass"
    c_rel = Circuit(3)
    for x in c.gates:
        c_rel.append(*x)
    c_rel.append("z", [0])                                               # relative phase on one term
    assert verify(pub, "cx", c_rel).status == "fail"


def test_ancilla_gate_set_and_line_rules():
    pub = G.gen_w(4, "train").inst.public
    c = T.w_cascade(4)
    wide = Circuit(5)
    for x in c.gates:
        wide.append(*x)
    assert verify(pub, "cx", wide).status == "fail"                      # no ancillas
    bad = Circuit(4)
    for x in c.gates:
        bad.append(*x)
    bad.append("ccx", [0, 1, 2])
    assert verify(pub, "cx", bad).status == "fail"                       # gate set
    far = Circuit(4)
    far.append("x", [0]); far.append("cx", [0, 3]); far.append("cx", [0, 3])
    assert verify(pub, "depth2q@line", far).status == "fail"             # (0, 3) is not a line edge


def test_output_map_only_on_line_track():
    pub = G.gen_dense("train", 3, 1).inst.public
    c = T.t_qiskit_sp(pub, "cx", 1, 0)[0]["circuit"]
    assert verify(pub, "cx", c, [2, 1, 0]).status == "fail"


def test_large_w_verified_by_sparse_path():
    pub = G.gen_w(100, "x").inst.public
    assert verify(pub, "cx", T.w_tree(100)).status == "pass"


@pytest.fixture(scope="module")
def manifest():
    return load_manifest("D")


def test_no_hash_across_splits_and_ood_only_in_test(manifest):
    idx = {r["id"]: r for r in load_index("D")}
    seen = {}
    for split, es in manifest["splits"].items():
        for e in es:
            assert seen.setdefault(e["hash"], split) == split
            if split in ("train", "val"):
                assert idx[e["id"]]["family"] != "sparse_struct"
                if idx[e["id"]]["family"] == "dicke":
                    assert e["id"].endswith(".k2")


def test_variants_equivalent_under_local_gates(manifest):
    root = data_root() / "variants" / "D"
    k = 0
    for d in sorted(root.iterdir())[:20]:
        orig = load_public("D", "sha256:" + d.name)
        for f in sorted(d.glob("v*.json")):
            v = json.loads(f.read_text())
            a = sorted(round(re * re + im * im, 9) for _, re, im in orig["amplitudes"])
            b = sorted(round(re * re + im * im, 9) for _, re, im in v["public"]["amplitudes"])
            assert a == b
            k += 1
    assert k > 0
