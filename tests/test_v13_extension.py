"""qbank A 1.2.0 / B 1.3.0 (10-28): the added instances (core/extend.py, categories/A/extend_v12.py,
categories/B/extend_v13.py; evoA/docs/baseline_plan_1028/AB_design.md)."""
import base64
import json

import numpy as np
import pytest

from qbank.categories.A import codes as C
from qbank.categories.B import extend_v13 as XB
from qbank.core import gf2
from qbank.core.aig import AIG
from qbank.core.instance import iter_instances, load_index, load_private, load_public
from qbank.core.splits import DATA_VERSIONS, load_manifest, verify_frozen, version_history


def _new(cat, ver):
    return [i for i in iter_instances(cat) if i.private.get("added_in") == ver]


def test_versions_frozen_and_archived():
    assert DATA_VERSIONS["A"] == "1.2.0" and DATA_VERSIONS["B"] == "1.3.0"
    for cat, old, new in (("A", "1.1.0", "1.2.0"), ("B", "1.2.0", "1.3.0")):
        assert load_manifest(cat)["qbank_version"] == new and verify_frozen(cat)
        h = {e["version"]: e for e in version_history()[cat]}
        assert h[old]["superseded_by"] == new and h[old]["sha256"] and h[new]["reason"]
        arch = json.loads((load_manifest.__globals__["data_root"]() / h[old]["archived"]).read_text())
        cur = load_manifest(cat)
        for sp, es in arch["splits"].items():          # every old entry is kept with its split and hash
            assert {(e["id"], e["hash"]) for e in es} <= {(e["id"], e["hash"]) for e in cur["splits"][sp]}


@pytest.mark.parametrize("cat,ver,count", [("A", "1.2.0", 6), ("B", "1.3.0", 63)])
def test_new_instances_only_in_train_val_and_consistent(cat, ver, count):
    new = _new(cat, ver)
    assert len(new) == count
    split_of = {e["id"]: sp for sp, es in load_manifest(cat)["splits"].items() for e in es}
    for i in new:
        assert split_of[i.id] == {"test": "val"}.get(i.private["pack_v2_split"], "train")
        assert i.qbank_version == ver


def test_qrm_general_order_matches_r1_and_is_a_code():
    for m in (4, 5, 6):
        a, b = C.quantum_reed_muller(m), C.quantum_reed_muller_r(m, 1)
        assert np.array_equal(a.hx, b.hx) and np.array_equal(a.hz, b.hz)
    for m, r in ((6, 2), (7, 2)):
        c = C.quantum_reed_muller_r(m, r)
        assert C.css_commute(c.hx, c.hz) and c.k() == 1


def test_new_a_codes_distinct_row_spaces():
    keys = {}
    for i in iter_instances("A"):
        if i.public["task"] != "css_logical_zero":
            continue
        n = i.public["n"]
        red, piv = gf2.rref(gf2.from_sparse_rows(i.public["hx"], n))
        k = (n, json.dumps(gf2.sparse_rows(red[:len(piv)])))
        if i.private.get("added_in") == "1.2.0":
            assert k not in keys, (i.id, keys.get(k))
        keys.setdefault(k, i.id)


def test_new_b_functions_strict_structural_and_npn_unique():
    sigs = {}
    new_ids = set()
    for i in iter_instances("B"):
        aig = AIG.from_aiger(base64.b64decode(i.public["aiger_b64"]))
        n = aig.num_inputs
        if n > 22:
            continue
        tt = aig.truth_tables()
        s = XB.npn_signature(tt, n)
        if i.private.get("added_in") == "1.3.0":
            new_ids.add(i.id)
            ok, cnt = XB.strict_structural(tt[0], n)
            assert ok and cnt == i.private["n_solutions"] and not i.private["solution_sparse"]
            assert XB.all_inputs_matter(tt[0], n)
            assert s == i.private["npn_signature"]
        sigs.setdefault(s, []).append(i.id)
    for s, ids in sigs.items():
        if len(ids) > 1:
            assert not (set(ids) & new_ids), ids


def test_new_b_functions_compute_what_they_say():
    for i in _new("B", "1.3.0"):
        aig = AIG.from_aiger(base64.b64decode(i.public["aiger_b64"]))
        n = aig.num_inputs
        x = np.arange(1 << n)
        p = i.params
        sub = i.private["subtype"]
        if sub == "lt_const":
            ref = x < p["c"]
        elif sub == "interval":
            ref = (x >= p["c1"]) & (x < p["c2"])
        elif sub == "threshold":
            ref = np.array([bin(int(v)).count("1") for v in x]) >= p["k"]
        else:
            w = p["w"]
            ref = (((x & ((1 << w) - 1)) * (x >> w)) >> p["j"]) & 1
        assert np.array_equal(aig.truth_tables()[0].astype(int), np.asarray(ref, dtype=int)), i.id
