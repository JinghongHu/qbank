"""Category A data integrity: determinism, split integrity, variants, visibility, exclusions,
prompt isolation, external data checksums."""
import json
import os

import pytest

from qbank.categories.A import generate as G
from qbank.categories.A.build import SPLIT_RULES, apply_exclusions, matches_exclusion
from qbank.core import gf2
from qbank.core.canon import file_sha256, hash_hex
from qbank.core.instance import PKG_ROOT, data_root, load_index, load_private, load_public
from qbank.core.splits import load_manifest

O_FAMS = G.O_FAMILIES


@pytest.fixture(scope="module")
def manifest():
    return load_manifest("A")


@pytest.fixture(scope="module")
def index():
    return {r["id"]: r for r in load_index("A")}


# ------------------------------------------------------------------ determinism
@pytest.mark.parametrize("fn,args", [
    (G.gen_rand_stab, ("train", 12, 1200)), (G.gen_bb_rand, ("train", "M", 1003)), (G.gen_gb_rand, ("val", "L", 2001)),
    (G.gen_css_rand, ("test_in", "XL", 3004)), (G.gen_hgp_rand, ("M", 1002)),
])
def test_generation_is_deterministic(fn, args):
    a, b = fn(*args), fn(*args)
    assert a.inst.hash == b.inst.hash
    assert json.dumps(a.inst.public_record(), sort_keys=True) == json.dumps(b.inst.public_record(), sort_keys=True)
    assert json.dumps(a.inst.private_record(), sort_keys=True, default=str) == json.dumps(b.inst.private_record(), sort_keys=True, default=str)


def test_stored_instances_match_regeneration(index):
    """Regenerate a sample of stored instances and compare hashes with the manifest."""
    ids = [i for i in index if i.startswith(("A.css_zero.bb_rand", "A.stab.rand_stab", "A.css_zero.hgp_rand"))][:12]
    regen = {}
    for p in [G.gen_rand_stab("train", 12, 1200), G.gen_bb_rand("train", "M", 1003), G.gen_hgp_rand("M", 1002)]:
        regen[p.inst.id] = p.inst.hash
    for iid, h in regen.items():
        assert index[iid]["hash"] == h


@pytest.mark.slow
def test_full_rebuild_matches_manifest(manifest, tmp_path, monkeypatch):
    """Regenerate every A instance from scratch into a temporary data root, replay the recorded duplicate drops and
    refills (build_report.json; the refill seeds are deterministic), and compare all (split, hash) with the manifest."""
    import json
    rep = json.loads((data_root() / "instances" / "A" / "build_report.json").read_text())
    monkeypatch.setenv("QBANK_DATA", str(tmp_path))
    planned = G.generate_all()
    by_id = {p.inst.id: p for p in planned}
    got = {p.inst.id: (p.split, p.inst.hash) for p in planned if p.inst.id not in set(rep["dropped_as_duplicates"])}
    for r in rep["refills"]:
        if r["replacement"]:
            new = G.regenerate(by_id[r["dropped"]], r["attempts"])
            assert new.inst.id == r["replacement"]
            got[new.inst.id] = (new.split, new.inst.hash)
    # A 1.2.0 (10-28): build() adds the extension instances after the duplicate handling (categories/A/extend_v12.py)
    from qbank.categories.A import extend_v12
    insts = [by_id[i].inst for i in got if i in by_id]
    for r in rep["refills"]:
        if r["replacement"]:
            insts.append(G.regenerate(by_id[r["dropped"]], r["attempts"]).inst)
    ext, _ = extend_v12.extension(insts, log=lambda *a: None)
    for p in ext:
        got[p.inst.id] = (p.split, p.inst.hash)
    want = {e["id"]: (s, e["hash"]) for s, es in manifest["splits"].items() for e in es}
    assert got == want


# ------------------------------------------------------------------ split integrity
def test_no_hash_shared_between_splits(manifest):
    seen = {}
    for split, entries in manifest["splits"].items():
        for e in entries:
            assert e["hash"] not in seen or seen[e["hash"]] == split, (e["id"], seen.get(e["hash"]), split)
            seen[e["hash"]] = split


def test_heldout_families_only_in_test_ood_or_probe(manifest, index):
    for split in ("train", "val", "test_in"):
        for e in manifest["splits"][split]:
            assert index[e["id"]]["family"] not in O_FAMS, (split, e["id"])
    for e in manifest["splits"]["test_ood"]:
        assert index[e["id"]]["family"] in O_FAMS, e["id"]


def test_min_seeds_per_family_bin_in_train(manifest, index):
    from collections import Counter
    c = Counter()
    for e in manifest["splits"]["train"]:
        r = index[e["id"]]
        if r["family"] in ("rand_stab", "bb_rand", "gb_rand", "css_rand"):
            c[(r["family"], r["size_bin"])] += 1
    assert c and min(c.values()) >= 10, c


def test_no_cross_split_duplicates_recorded():
    rep = json.loads((data_root() / "instances" / "A" / "build_report.json").read_text())
    assert rep["cross_split_duplicates"] == []


def test_variants_same_split(manifest):
    split_of = {e["hash"]: s for s, es in manifest["splits"].items() for e in es}
    root = data_root() / "variants" / "A"
    n = 0
    for d in root.iterdir():
        for f in d.glob("v*.json"):
            v = json.loads(f.read_text())
            assert v["split"] == split_of[v["variant_of"]]
            n += 1
    tests = len(manifest["splits"]["test_in"]) + len(manifest["splits"]["test_ood"])
    assert n == 3 * tests


def test_variants_are_equivalent(manifest):
    """A relabelled variant is solved by the relabelled best circuit (sanity of the variant transforms)."""
    from qbank.categories.A.instances import verify
    from qbank.core.circuit import Circuit
    bk = data_root() / "baselines" / "A" / "best_known.jsonl"
    if not bk.exists():
        pytest.skip("baselines not aggregated yet")
    best = {(r["hash"], r["track"]): r for r in map(json.loads, bk.read_text().splitlines())}
    checked = 0
    for e in manifest["splits"]["test_in"][:15]:
        b = best.get((e["hash"], "a2a_2q"))
        if not b or b.get("source_kind") != "baseline":
            continue
        d = json.loads((data_root() / (b["circuit_path"] + ".json")).read_text())
        c = Circuit.from_json(d["circuit"])
        v1 = json.loads((data_root() / "variants" / "A" / hash_hex(e["hash"]) / "v1.json").read_text())
        perm = v1["transform"]["perm"]
        # relabelling the circuit by perm already moves code qubit q to perm[q]; an output map (graph tracks only) is
        # relabelled the same way
        om = [perm[q] for q in d["output_map"]] if d.get("output_map") else None
        assert verify(v1["public"], "a2a_2q", c.relabel(perm), om).status == "pass"
        v2 = json.loads((data_root() / "variants" / "A" / hash_hex(e["hash"]) / "v2.json").read_text())
        assert verify(v2["public"], "a2a_2q", c, d.get("output_map")).status == "pass"
        checked += 1
    assert checked > 0


def test_exclusion_list_blocks_test_instances(manifest, index):
    e = manifest["splits"]["test_ood"][0]
    pub = load_public("A", e["hash"])
    priv = load_private("A", e["id"])
    from qbank.core.instance import Instance
    inst = Instance.from_records(priv, {**pub})
    if pub["task"] == "css_logical_zero":
        n = pub["n"]
        # an equivalent form: permuted qubits + basis change must still match
        import numpy as np
        rng = np.random.default_rng(0)
        perm = rng.permutation(n)
        hx = gf2.from_sparse_rows(pub["hx"], n)
        hz = gf2.from_sparse_rows(pub["hz"], n)
        hx2 = np.zeros_like(hx); hx2[:, perm] = hx
        hz2 = np.zeros_like(hz); hz2[:, perm] = hz
        entry = {"category": "A", "type": "css_code", "n": n, "hx": gf2.sparse_rows(hx2), "hz": gf2.sparse_rows(hz2)}
    else:
        entry = {"category": "A", "type": "hash", "hash": e["hash"]}
    assert matches_exclusion(inst, entry)
    user = json.loads((data_root() / "exclusions" / "exclude.json").read_text())["entries"]
    for split in ("test_in", "test_ood"):
        for t in manifest["splits"][split]:
            ti = Instance.from_records(load_private("A", t["id"]), load_public("A", t["hash"]))
            assert not any(matches_exclusion(ti, u) for u in user if u.get("category", "A") == "A")


# ------------------------------------------------------------------ visibility
PRIVATE = {"id", "family", "source", "params", "private", "contracts", "qbank_version"}


def test_public_records_have_no_private_fields(manifest):
    for split, entries in manifest["splits"].items():
        for e in entries:
            pub = load_public("A", e["hash"])
            assert not (PRIVATE & set(pub)), (e["id"], PRIVATE & set(pub))
            txt = json.dumps(pub)
            assert e["id"] not in txt


def test_export_pack_contains_only_train_val_public(manifest, tmp_path):
    from qbank.eval.export import export_pack
    out = tmp_path / "pack"
    export_pack("A", out)
    allowed = {hash_hex(e["hash"]) for s in ("train", "val") for e in manifest["splits"][s]}
    test_hashes = {hash_hex(e["hash"]) for s in ("test_in", "test_ood", "probe") for e in manifest["splits"][s]}
    files = list((out / "candidate_view").rglob("*.json"))
    assert files
    for f in files:
        assert f.stem in allowed and f.stem not in test_hashes
        assert not (PRIVATE & set(json.loads(f.read_text())))
    for line in (out / "harness" / "best_known.jsonl").read_text().splitlines():
        assert hash_hex(json.loads(line)["hash"]) in allowed


def test_eval_api_public_view_hides_private(manifest):
    from qbank.eval.api import load_split, public_view
    inst = load_split("A", "train")[0]
    view = public_view(inst)
    assert not (PRIVATE & set(view))


def test_prompt_lint_flags_heldout_names():
    from qbank.core.prompts import lint
    assert lint("A", "Prepare the logical zero state of a CSS code given its X checks.") == []
    assert lint("A", "e.g. the Golay code or a hypergraph product code")
    assert lint("A", "the [[144,12,12]] code")


# ------------------------------------------------------------------ external data
def test_external_sources_recorded_and_checksums_match():
    src = json.loads((data_root() / "external" / "SOURCES_A.json").read_text())
    ext = PKG_ROOT / ".cache" / "external"
    for k in ("mqt-qecc", "qecirc", "stabilizerbench"):
        assert src[k]["commit"] and src[k]["licence"]
        assert (ext / f"{k}.COMMIT").read_text().strip() == src[k]["commit"]
    sb = ext / "stabilizerbench" / "data" / "benchmarks.json"
    assert file_sha256(sb) == src["stabilizerbench"]["data/benchmarks.json sha256"]
    # every external baseline record's file checksum still matches the fetched file
    recs = [json.loads(l) for l in (data_root() / "baselines" / "A" / "records.jsonl").read_text().splitlines()]
    ext_recs = [r for r in recs if r["tool"].startswith(("published:", "qecirc:"))]
    assert ext_recs
    for r in ext_recs[:50]:
        assert r["config"].get("file_sha256")
