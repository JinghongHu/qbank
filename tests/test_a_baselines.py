"""Baseline reproducibility: rerun 20 random baseline records; deterministic tools must reproduce the
same circuit exactly, randomised tools (rustiq, patched) the same circuit under the recorded trial seed."""
import json
import os
import random
import time

import pytest

from qbank.baselines import tools_a as T
from qbank.core.circuit import Circuit
from qbank.core.instance import data_root, load_public
from qbank.categories.A.instances import verify


def _records():
    p = data_root() / "baselines" / "A" / "records.jsonl"
    if not p.exists():
        pytest.skip("baselines not aggregated yet")
    return [json.loads(l) for l in p.read_text().splitlines()]


def _stored_circuit(rec):
    import gzip
    path, key = rec["circuit_path"].split("#")
    with gzip.open(data_root() / path, "rt") as f:
        for line in f:
            d = json.loads(line)
            if d["cache_key"] == key:
                return Circuit.from_json(d["circuit"]), d.get("output_map")
    raise KeyError(key)


def _rerun(rec, pub):
    tool, track = rec["tool"], rec["track"]
    fn = T.tools_for(pub, track)[tool]
    if T.is_anytime(tool):
        seed = rec["meta"]["trial_seed"]
        base = T.A2A_TOOLS["rustiq.stabilizer_state_synthesis"]
        # one trial with the recorded seed (deadline in the past -> exactly one iteration)
        cands = base(pub, "a2a_2q", seed, time.monotonic() - 1)
        if "+sabre" in tool:
            rc, om = T.sabre_route(cands[0]["circuit"], pub["tracks"][track]["connectivity"]["edges"], rec["seed"])
            cands = [{"circuit": rc, "output_map": om}]
    else:
        cands = fn(pub, track, rec["seed"], time.monotonic() + rec["budget_s"])
    return cands


@pytest.mark.slow
def test_random_20_records_reproduce():
    recs = [r for r in _records() if r["status"] == "pass" and not r["tool"].startswith(("published:", "qecirc:", "mqt.qmap"))
            and "reused" not in r["tool"] and r.get("n_candidates")]
    rng = random.Random(20260925)
    sample = rng.sample(recs, 20)
    for rec in sample:
        pub = load_public("A", rec["hash"])
        want, want_om = _stored_circuit(rec)
        cands = _rerun(rec, pub)
        got = [c for c in cands]
        # the stored circuit is the verified (Pauli-normalised) version of one candidate: re-verify each rerun candidate
        ok = False
        for c in got:
            v = verify(pub, rec["track"], c["circuit"], c.get("output_map"))
            if v.status == "pass" and v.circuit.gates == want.gates and (c.get("output_map") or None) == (want_om or None):
                ok = True
                break
        assert ok, (rec["instance_id"], rec["track"], rec["tool"])
