"""Baseline reproducibility for all categories: the 20-record re-run (`qbank repro <C>`) must reproduce
every drawn record; additionally 3 records per category are re-run live here. FLOAT_DEPENDENT tools (D qclib) only
have to pass the checker on re-run, not reproduce gate by gate (user decision 10-28, see repro.py)."""
import json
import random

import pytest

from qbank.baselines import repro
from qbank.core.instance import data_root, load_public


@pytest.mark.parametrize("cat", ["A", "B", "C", "D"])
def test_stored_repro_all_reproduced(cat):
    p = data_root() / "baselines" / cat / "repro.json"
    assert p.exists(), f"run `qbank repro {cat}`"
    d = json.loads(p.read_text())
    assert d["n"] == 20 and d["reproduced"] == 20, [r for r in d["rows"] if not r["reproduced"]]


@pytest.mark.parametrize("cat", ["A", "B", "C", "D"])
def test_live_rerun_three_records(cat):
    recs = [r for r in repro._records(cat) if repro.eligible(r)]
    for rec in random.Random(f"live-{cat}").sample(recs, 3):
        pub = load_public(cat, rec["hash"])
        stored = repro._stored(rec)
        assert any(repro._matches(cat, cd, stored, pub, rec["track"], rec) for cd in repro._rerun(cat, rec, pub)), \
            (rec["instance_id"], rec["tool"], rec["track"])
