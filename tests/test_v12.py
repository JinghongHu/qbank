"""Checks for the v1.2 changes: deterministic XAG / pebbling baselines and their
presence in the reproducibility draw, the solution-sparse rule, subset exports without private fields, the BB90
renaming in A, the new structural test_ood sources, and the concurrency fields."""
import json
import random

import numpy as np
import pytest

from qbank.baselines import repro
from qbank.core.instance import data_root, load_index, load_private, load_public
from qbank.core.splits import load_manifest, version_history

NEW_XAG = "XAG MC cut rewriting (mockturtle xag_minmc_resynthesis)"
OLD_XAG = "XAG + MC (Meuli et al. 2019, re-impl.)"
PEBBLE = "pebbling SAT (Meuli et al. 2019, re-impl.)"


# ------------------------------------------------------------------ §2 reproducibility of XAG / pebbling
def test_repro_draw_contains_xag_and_reproduces_gate_by_gate():
    d = json.loads((data_root() / "baselines" / "B" / "repro.json").read_text())
    tools = {r["tool"] for r in d["rows"]}
    assert OLD_XAG in tools and NEW_XAG in tools and PEBBLE in tools, tools
    assert all(r["reproduced"] for r in d["rows"] if r["tool"] in (OLD_XAG, NEW_XAG, PEBBLE))
    assert not any(t.startswith(("XAG", "pebbling")) for t in repro.TIME_DEPENDENT)


@pytest.mark.parametrize("tool", [OLD_XAG, NEW_XAG, PEBBLE])
def test_live_rerun_is_identical(tool):
    recs = [r for r in repro._records("B") if repro.eligible(r) and r["tool"] == tool and r["track"] == "tof@inf"]
    recs = [r for r in recs if (r.get("wall_tool_s") or 0) < 20]           # keep the test fast
    for rec in random.Random(f"v12-{tool}").sample(recs, 2):
        pub = load_public("B", rec["hash"])
        stored = repro._stored(rec)
        cands = repro._rerun("B", rec, pub)
        assert any(repro._matches("B", cd, stored, pub, rec["track"]) for cd in cands), rec["instance_id"]


def test_exact_mc_budget_is_deterministic():
    from qbank.core.xag import exact_mc_budget
    rng = np.random.default_rng(5)
    tt = rng.integers(0, 2, 32).astype(np.uint8)
    a = exact_mc_budget(tt, 5, 20000)
    b = exact_mc_budget(tt, 5, 20000)
    assert a[1] == b[1] and a[2] == b[2] and (a[0] is None) == (b[0] is None)
    if a[0] is not None:
        assert a[0].ands == b[0].ands and a[0].outputs == b[0].outputs


# ------------------------------------------------------------------ §1 probe acceptance
def test_probe_acceptance_new_xag():
    opt = {}
    for l in (data_root() / "optimal" / "B.jsonl").read_text().splitlines():
        o = json.loads(l)
        if o["track"] == "tof@inf" and o["kind"] == "lower_bound":
            opt[o["instance_id"]] = o
    recs = {(r["instance_id"], r["tool"]): r for r in repro._records("B") if r["track"] == "tof@inf"}
    for iid in [r["id"] for r in load_index("B") if ".probe.n5." in r["id"]]:
        r = recs[(iid, NEW_XAG)]
        assert r["status"] == "pass" and opt[iid]["mc_exact"]
        assert r["costs"]["toffoli_count"] <= 2 * opt[iid]["value"] - 1, iid
    # documented miss (report): the affine class of s40602 is one of the 6 classes left out of the 6-input
    # database (canonization > 10^8 steps), so the new tool cannot resynthesize the whole function; the best baseline
    # stays at 12 Toffoli (XAG + MC, as in v1.1)
    KNOWN_MISS = {"B.bitflip.probe.n6.s40602": 12}
    for iid in [r["id"] for r in load_index("B") if ".probe.n6." in r["id"]]:
        best = min(x["costs"]["toffoli_count"] for (i, t), x in recs.items() if i == iid and x["status"] == "pass")
        r = recs[(iid, NEW_XAG)]
        if iid in KNOWN_MISS:
            assert best <= KNOWN_MISS[iid] and r["meta"].get("db_misses", 0) >= 1 and r["meta"].get("ands_collapsed") == 0
            continue
        assert best <= 11, iid
        assert r["status"] == "pass" and r["costs"]["toffoli_count"] <= 11, iid


# ------------------------------------------------------------------ §3 solution-sparse rule
def test_solution_sparse_follows_fraction_rule():
    from qbank.categories.B.build import is_solution_sparse
    for row in load_index("B"):
        priv = load_private("B", row["id"])["private"]
        pub = load_public("B", row["hash"])
        assert "n_solutions" in priv and "solution_sparse" in priv
        assert priv["solution_sparse"] == is_solution_sparse(pub["n_inputs"], priv["n_solutions"])
        if pub["n_outputs"] > 1:
            assert priv["n_solutions"] is None and not priv["solution_sparse"]


def test_solution_counts_exact_on_sample():
    from qbank.baselines.tools_b import load_aig
    rows = [r for r in load_index("B") if load_public("B", r["hash"])["n_inputs"] <= 16]
    for row in random.Random("v12-count").sample(rows, 25):
        priv = load_private("B", row["id"])["private"]
        aig = load_aig(load_public("B", row["hash"]))
        if len(aig.outputs) == 1:
            assert priv["n_solutions"] == int(aig.truth_tables()[0].sum()), row["id"]


# ------------------------------------------------------------------ §8 subset filters
@pytest.mark.parametrize("subset", ["structural", "solution_sparse"])
def test_subset_export_public_only_and_matches_manifest(subset, tmp_path):
    from qbank.eval.export import PRIVATE_KEYS, export_pack
    from qbank.eval.subsets import predicate
    out = tmp_path / subset
    export_pack("B", out, subset)
    keep = predicate("B", subset)
    man = load_manifest("B")
    private_field_names = set()
    for s in ("train", "val"):
        want = {e["hash"] for e in man["splits"][s] if keep(load_private("B", e["id"])["private"])}
        files = sorted((out / "candidate_view" / s).glob("*.json")) if (out / "candidate_view" / s).exists() else []
        got = set()
        for f in files:
            d = json.loads(f.read_text())
            assert not (PRIVATE_KEYS & set(d)), f
            got.add(d["hash"])
            private_field_names |= set(d)
        assert got == want, (s, len(got), len(want))
    # no private field name (solution_sparse, n_solutions, b_min, ...) anywhere in the candidate view
    text = "".join(p.read_text() for p in (out / "candidate_view").rglob("*.json"))
    for k in ("solution_sparse", "n_solutions", "b_min", "size_bin", "family"):
        assert f'"{k}"' not in text, k
    m = json.loads((out / "MANIFEST.json").read_text())
    assert m["subset"] == subset


def test_load_split_subset_partition():
    from qbank.eval.api import load_split
    for s in ("train", "val"):
        allx = {i.id for i in load_split("B", s)}
        st = {i.id for i in load_split("B", s, subset="structural")}
        sp = {i.id for i in load_split("B", s, subset="solution_sparse")}
        assert st | sp == allx and not (st & sp)
    with pytest.raises(ValueError):
        load_split("A", "train", subset="structural")


# ------------------------------------------------------------------ §4 structural test_ood
def test_structural_test_ood_sources():
    idx = {r["id"]: r for r in load_index("B")}
    man = load_manifest("B")
    ood = [e["id"] for e in man["splits"]["test_ood"] if not load_private("B", e["id"])["private"]["solution_sparse"]]
    fams = {idx[i]["family"] for i in ood}
    assert len(ood) >= 30, len(ood)
    assert {"sbox", "iscas85", "mcnc", "epfl"} <= fams, fams
    for i in ood:
        src = load_private("B", i)["source"]
        assert src.get("license") and (src.get("sha256") or src.get("archive_sha256") or src.get("kind") == "definition"), i


def test_rfc_sboxes_parse_and_self_check():
    from qbank.categories.B import sboxes
    for name, bits, load, rfc, desc in sboxes.SBOXES:
        s = load()
        assert sorted(s) == list(range(1 << bits)), name


# ------------------------------------------------------------------ §6 BB90
def test_bb90_renamed_and_bravyi90_checked():
    from qbank.categories.A import codes as C
    from qbank.categories.A.generate import BRAVYI
    from qbank.core import gf2
    ids = {r["id"]: r for r in load_index("A")}
    assert "A.css_zero.bb_published.mqt90" not in ids
    assert ids["A.css_zero.bb_mqt_n90_d2.mqt90"]["family"] == "bb_mqt_n90_d2"
    assert ids["A.css_zero.bb_published.bravyi90"]["family"] == "bb_published"
    split = {e["id"]: s for s, es in load_manifest("A")["splits"].items() for e in es}
    assert split["A.css_zero.bb_published.bravyi90"] == "test_in" and split["A.css_zero.bb_mqt_n90_d2.mqt90"] == "test_in"
    assert any(e["version"] == "1.1.0" for e in version_history()["A"])
    l, m, a, b, k = BRAVYI[90]
    assert (l, m, a, b) == (15, 3, [(9, 0), (0, 1), (0, 2)], [(0, 0), (2, 0), (7, 0)])
    c = C.bivariate_bicycle(l, m, a, b, "bb_bravyi_90")
    hx, hz = gf2.as_gf2(c.hx), gf2.as_gf2(c.hz)
    assert hx.shape[1] - gf2.rank(hx) - gf2.rank(hz) == 8

    def low_weight_logical(Hx, Hz):
        import itertools
        n = Hx.shape[1]
        for w in (1, 2):
            for S in itertools.combinations(range(n), w):
                v = np.zeros(n, dtype=np.uint8)
                v[list(S)] = 1
                for H, G in ((Hx, Hz), (Hz, Hx)):
                    if not (H.astype(int) @ v % 2).any() and gf2.rank(np.vstack([G, v])) > gf2.rank(G):
                        return S
        return None
    assert low_weight_logical(hx, hz) is None
    from mqt.qecc.codes import construct_bb_code
    mq = construct_bb_code(90)
    assert low_weight_logical(gf2.as_gf2(mq.Hx), gf2.as_gf2(mq.Hz)) is not None
    best = [json.loads(l) for l in (data_root() / "baselines" / "A" / "best_known.jsonl").read_text().splitlines()]
    assert not any("bb_published.mqt90" in b["instance_id"] for b in best)
    assert any(b["instance_id"] == "A.css_zero.bb_mqt_n90_d2.mqt90" for b in best)


# ------------------------------------------------------------------ §5 concurrency
def test_new_b_records_carry_concurrency():
    recs = [r for r in repro._records("B") if r["tool"] == NEW_XAG]
    assert recs and all(r.get("concurrency") or r.get("concurrency_estimate") for r in recs)
    assert sum(1 for r in recs if r.get("concurrency")) >= len(recs) // 2


def test_rebaseline_jobs_are_separate_and_test_only():
    from qbank.baselines.rebaseline import job_list
    tool = "qiskit LightSABRE (anytime)"
    js = job_list("C", "test", {tool}, 12)
    man = load_manifest("C")
    test_ids = {e["id"] for s in ("test_in", "test_ood") for e in man["splits"][s]}
    assert js and all(j["ns"] == "C-rebaseline-w12" and j["config"]["concurrency"] == 12 and j["tool"] == tool for j in js)
    assert {j["iid"] for j in js} <= test_ids


def test_runner_hardware_mentions_core_types():
    from qbank.baselines.runner import core_counts, hardware
    p, e = core_counts()
    assert p >= 1 and f"{p} performance + {e} efficiency cores" in hardware()
