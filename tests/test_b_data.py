"""Category B data integrity."""
import base64
import json

import numpy as np
import pytest

from qbank.categories.B import generate as G
from qbank.categories.B.build import permute_inputs
from qbank.core.aig import AIG
from qbank.core.canon import hash_hex
from qbank.core.instance import data_root, load_index, load_private, load_public
from qbank.core.splits import load_manifest

EXTERNAL = {"satlib", "epfl", "sbox", "iscas85", "mcnc"}   # iscas85, mcnc: v1.2
PRIVATE = {"id", "family", "source", "params", "private", "contracts", "qbank_version"}


@pytest.fixture(scope="module")
def manifest():
    return load_manifest("B")


@pytest.fixture(scope="module")
def index():
    return {r["id"]: r for r in load_index("B")}


def test_generation_deterministic():
    for fn, args in ((G.gen_rand3sat, ("train", "S", 3)), (G.gen_triangle, ("val", "M", 1001)), (G.gen_simon3, ("train", "S", 2))):
        a, b = fn(*args), fn(*args)
        assert a.inst.hash == b.inst.hash
        assert json.dumps(a.inst.public_record(), sort_keys=True) == json.dumps(b.inst.public_record(), sort_keys=True)


def test_no_hash_across_splits(manifest):
    seen = {}
    for split, es in manifest["splits"].items():
        for e in es:
            assert seen.get(e["hash"], split) == split
            seen[e["hash"]] = split


def test_external_sources_only_in_test_ood(manifest, index):
    for split in ("train", "val", "test_in"):
        for e in manifest["splits"][split]:
            assert index[e["id"]]["family"] not in EXTERNAL
    fams = {index[e["id"]]["family"] for e in manifest["splits"]["test_ood"]}
    assert fams <= EXTERNAL and fams


def test_no_cross_split_duplicates_left():
    rep = json.loads((data_root() / "instances" / "B" / "build_report.json").read_text())
    dropped = set(rep["dropped"])
    for d in rep["cross_split_pairs"]:
        assert d["a"] in dropped or d["b"] in dropped


def test_variants_same_split_and_equivalent(manifest):
    split_of = {e["hash"]: s for s, es in manifest["splits"].items() for e in es}
    root = data_root() / "variants" / "B"
    n = 0
    for d in list(root.iterdir())[:40]:
        orig = load_public("B", "sha256:" + d.name)
        a0 = AIG.from_aiger(base64.b64decode(orig["aiger_b64"]))
        for f in sorted(d.glob("v*.json")):
            v = json.loads(f.read_text())
            assert v["split"] == split_of[v["variant_of"]]
            a1 = AIG.from_aiger(base64.b64decode(v["public"]["aiger_b64"]))
            if a0.num_inputs <= 16:
                perm, operm = v["transform"]["input_perm"], v["transform"]["output_perm"]
                t0, t1 = a0.truth_tables(), a1.truth_tables()
                x = np.arange(1 << a0.num_inputs)
                y = np.zeros_like(x)
                for i, p in enumerate(perm):
                    y |= ((x >> i) & 1) << p
                for j in range(len(a0.outputs)):
                    jj = operm[j] if operm else j
                    assert np.array_equal(t1[jj][y], t0[j])
            n += 1
    assert n > 0


def test_public_has_no_private_fields(manifest, index):
    for split, es in manifest["splits"].items():
        for e in es:
            pub = load_public("B", e["hash"])
            assert not (PRIVATE & set(pub))
            assert e["id"] not in json.dumps(pub)


def test_non_redistributable_flagged(index):
    for iid, row in index.items():
        if row["family"] == "satlib":
            assert load_private("B", iid)["private"]["redistributable"] is False


def test_permute_inputs_roundtrip():
    g = AIG(4)
    a, b, c, d = (g.input_lit(i) for i in range(4))
    g.add_output(g.XOR(g.AND(a, b), g.OR(c, d ^ 1)))
    g.add_output(g.AND(a, d))
    p = permute_inputs(g, [2, 0, 3, 1], [1, 0])
    inv = [0] * 4
    for i, q in enumerate([2, 0, 3, 1]):
        inv[q] = i
    assert np.array_equal(permute_inputs(p, inv, [1, 0]).truth_tables(), g.truth_tables())
