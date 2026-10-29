"""Data integrity for categories C, D: splits, OOD separation, public/private separation, licences,
variants."""
import json

import pytest

from qbank.categories.C.build import relabel
from qbank.contracts.routing import check_routing_equiv
from qbank.core.circuit import Circuit
from qbank.core.instance import data_root, load_index, load_private, load_public
from qbank.core.splits import load_manifest

PRIVATE = {"id", "family", "source", "params", "private", "contracts", "qbank_version"}
OOD_ONLY = {"C": {"queko", "qubikos", "mqtbench", "hamlib"}, "D": {"sparse_struct"}}


@pytest.mark.parametrize("cat", ["C", "D"])
def test_splits_disjoint_and_public_clean(cat):
    man = load_manifest(cat)
    idx = {r["id"]: r for r in load_index(cat)}
    seen = {}
    for split, es in man["splits"].items():
        for e in es:
            assert seen.setdefault(e["hash"], split) == split
            pub = load_public(cat, e["hash"])
            assert not (PRIVATE & set(pub))
            assert e["id"] not in json.dumps(pub)
            if split in ("train", "val"):
                assert idx[e["id"]]["family"] not in OOD_ONLY[cat]
    fams = {idx[e["id"]]["family"] for e in man["splits"]["test_ood"]}
    assert fams & OOD_ONLY[cat]


def test_c_non_redistributable_flagged():
    for row in load_index("C"):
        if row["family"] in ("qubikos", "hamlib"):
            priv = load_private("C", row["id"])
            assert priv["source"]["redistributable"] is False and priv["private"]["redistributable"] is False


def test_c_variants_equivalent():
    """A relabelled instance is routed by relabelling the answer: check with the original's SABRE routing."""
    import time
    from qbank.baselines.tools_c import t_sabre
    root = data_root() / "variants" / "C"
    dirs = sorted(root.iterdir())[:6]
    for d in dirs:
        pub = load_public("C", "sha256:" + d.name)
        if pub["n_logical"] > 40:
            continue
        r = t_sabre(pub, "swaps", 1, time.monotonic())[0]
        for f in sorted(d.glob("v*.json")):
            v = json.loads(f.read_text())
            lp, pp = v["transform"]["logical_perm"], v["transform"]["physical_perm"]
            c2 = Circuit(r["circuit"].n)
            for g, qs, p in r["circuit"].gates:
                c2.append(g, [pp[q] for q in qs], p)
            lay = [0] * len(lp)
            for l, p in enumerate(r["initial_layout"]):
                lay[lp[l]] = pp[p]
            o2 = Circuit.from_json(v["public"]["circuit"])
            assert check_routing_equiv(o2, c2, lay, v["public"]["coupling_edges"]).status == "pass"
            assert relabel(pub, lp, pp)["coupling_edges"] == v["public"]["coupling_edges"]


def test_c_queko_witness_optima_recorded():
    rows = [json.loads(l) for l in (data_root() / "optimal" / "C.jsonl").read_text().splitlines() if l.strip()]
    q = [r for r in rows if r["instance_id"].startswith("C.queko.")]
    assert q and all(str(r["status"]).startswith("optimal") for r in q)


@pytest.mark.parametrize("cat", ["B", "C"])
def test_external_sources_recorded_and_checksums_match(cat):
    from qbank.core.canon import file_sha256
    from qbank.core.instance import PKG_ROOT
    src = json.loads((data_root() / "external" / f"SOURCES_{cat}.json").read_text())
    X = PKG_ROOT / ".cache" / "external"
    for k, v in src.items():
        if k.startswith("_"):
            continue
        assert v.get("licence")
        for f, h in (v.get("files") or {}).items():
            base = X / k if (X / k).exists() else X / k.split(".")[0]
            assert file_sha256(base / f) == h


def test_c_full_rebuild_matches_manifest(tmp_path, monkeypatch):
    """Regenerate every C instance (generators + external sources) into a temporary data root, replay the recorded
    duplicate drops and refills, and compare every (split, hash) with the manifest (determinism of the whole build)."""
    from qbank.categories.C import build as CB
    from qbank.categories.C import external as X
    from qbank.categories.C import generate as G
    rep = json.loads((data_root() / "instances" / "C" / "build_report.json").read_text())
    man = load_manifest("C")
    monkeypatch.setenv("QBANK_DATA", str(tmp_path))
    planned = G.generate_all(log=lambda *a: None) + X.generate_external(log=lambda *a: None)
    by_id = {p.inst.id: p for p in planned}
    got = {p.inst.id: (p.split, p.inst.hash) for p in planned if p.inst.id not in set(rep["dropped"])}
    for r in rep["refills"]:
        if r["replacement"]:
            new = CB.regenerate(by_id[r["dropped"]], r["attempts"])
            got[new.inst.id] = (new.split, new.inst.hash)
    want = {e["id"]: (s, e["hash"]) for s, es in man["splits"].items() for e in es}
    assert got == want
