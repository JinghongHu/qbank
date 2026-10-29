"""Quality-time curves: on a stratified subset, re-run the budget-sensitive tools at 0.1x (6 s) and 10x
(600 s) the default budget; the 1x (60 s) point is the main baseline record. Results live in their own cache namespace
("<C>-curve") and never enter best_known (which is defined at the common 60 s budget); they show how much the 60 s
baselines under-state the tools, in particular where a tool timed out at 60 s.

Outputs: data/v1/baselines/<C>/curve.jsonl and results/<date>/<C>_quality_time.csv.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict

from ..core.instance import data_root, load_index

MAIN_TRACK = {"A": "a2a_2q", "B": "tof@inf", "C": "swaps", "D": "cx"}
BUDGETS = (6.0, 600.0)
PER_CATEGORY = {"A": 16, "B": 24, "C": 24, "D": 24}


def _records(cat):
    p = data_root() / "baselines" / cat / "records.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def budget_sensitive_tools(cat: str, recs) -> set:
    track = MAIN_TRACK[cat]
    tools = {r["tool"] for r in recs if r["track"] == track and r["status"] == "timeout"}
    if cat == "A":
        from .tools_a import is_anytime
        tools |= {r["tool"] for r in recs if r["track"] == track and is_anytime(r["tool"])}
    elif cat == "C":
        from .tools_c import C_ANYTIME
        tools |= set(C_ANYTIME) | {"OLSQ2 (TB, swap objective)"}
    elif cat == "B":
        tools |= {"pebbling SAT (Meuli et al. 2019, re-impl.)", "XAG + MC (Meuli et al. 2019, re-impl.)"}
    elif cat == "D":
        tools |= {"bqskit compile(StateVector)"}
    return {t for t in tools if not t.startswith(("published:", "qecirc:", "mqt.qmap.synthesize_clifford(heur"))}


def sample(cat: str, recs, tools: set) -> list[str]:
    """One instance per (family, size bin) stratum (seeded), plus every instance on which a selected tool timed out
    at 60 s on the main track; capped at PER_CATEGORY[cat] (timeouts first)."""
    track = MAIN_TRACK[cat]
    idx = {r["id"]: r for r in load_index(cat)}
    timed_out = sorted({r["instance_id"] for r in recs if r["track"] == track and r["tool"] in tools and r["status"] == "timeout"})
    strata = defaultdict(list)
    for iid, r in sorted(idx.items()):
        strata[(r["family"], r["size_bin"])].append(iid)
    rng = random.Random(f"curve-{cat}")
    strat = [rng.choice(v) for _, v in sorted(strata.items())]
    rng.shuffle(strat)
    out = []
    cap = PER_CATEGORY[cat]
    for iid in timed_out[: cap // 2] + strat:
        if iid not in out:
            out.append(iid)
        if len(out) >= cap:
            break
    return out


def jobs(cat: str) -> tuple[list[dict], list[str], set]:
    recs = _records(cat)
    tools = budget_sensitive_tools(cat, recs)
    ids = sample(cat, recs, tools)
    track = MAIN_TRACK[cat]
    if cat == "A":
        from .plan_a import jobs_A as J
    elif cat == "B":
        from .job_b import jobs_B as J
    elif cat == "C":
        from .job_c import jobs_C as J
    else:
        from .job_d import jobs_D as J
    out = []
    for b in BUDGETS:
        for j in J(budget=b, only_ids=set(ids), tracks={track}, tools=tools):
            out.append({**j, "ns": f"{cat}-curve"})
    return out, ids, tools


def summarize(cat: str, out_dir=None) -> list[dict]:
    from . import runner
    recs = _records(cat)
    track = MAIN_TRACK[cat]
    tools = budget_sensitive_tools(cat, recs)
    ids = sample(cat, recs, tools)
    idx = {r["id"]: r for r in load_index(cat)}
    main = {(r["instance_id"], r["tool"]): r for r in recs if r["track"] == track}
    metric = None
    rows = []
    for iid in ids:
        h = idx[iid]["hash"]
        curve = [r for r in runner.load_cache(f"{cat}-curve", h).values() if r["track"] == track]
        for tool in sorted(tools):
            pts = {}
            ver = main.get((iid, tool), {}).get("version")
            for r in curve:
                # only curve runs of the tool version of the main record (older versions stay in the cache)
                if r["tool"] == tool and (ver is None or r.get("version") == ver):
                    pts[r["budget_s"]] = r
            if (iid, tool) in main:
                pts[60.0] = main[(iid, tool)]
            if not pts:
                continue
            row = {"instance_id": iid, "family": idx[iid]["family"], "size_bin": idx[iid]["size_bin"], "track": track, "tool": tool}
            for b in (6.0, 60.0, 600.0):
                r = pts.get(b)
                if r is None:
                    row[f"status_{int(b)}"], row[f"value_{int(b)}"] = None, None
                    continue
                if metric is None and r.get("costs"):
                    from ..core.instance import load_public
                    metric = load_public(cat, h)["tracks"][track]["metric"]
                row[f"status_{int(b)}"] = r["status"]
                row[f"value_{int(b)}"] = r["costs"][metric] if r["status"] == "pass" and metric else None
            rows.append(row)
    p = data_root() / "baselines" / cat / "curve.jsonl"
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    if out_dir is not None:
        import csv
        with open(out_dir / f"{cat}_quality_time.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["instance_id"])
            w.writeheader()
            w.writerows(rows)
    return rows


def extended_jobs(cat: str) -> list[dict]:
    """10x budget (600 s) runs of the anytime tools on every instance where they timed out at 60 s on the main track
    (A: rustiq). Stored in the "<C>-curve" namespace; aggregate() attaches the best result to best_known entries as a
    separately labelled `extended_10x` reference (best_known itself stays defined at 60 s)."""
    recs = _records(cat)
    track = MAIN_TRACK[cat]
    if cat == "A":
        from .plan_a import jobs_A as J
        tools = {"rustiq.stabilizer_state_synthesis"}
    elif cat == "C":
        from .job_c import jobs_C as J
        tools = {"qiskit LightSABRE (anytime)"}
    else:
        return []
    ids = {r["instance_id"] for r in recs if r["track"] == track and r["tool"] in tools and r["status"] == "timeout"}
    if not ids:
        return []
    return [{**j, "ns": f"{cat}-curve"} for j in J(budget=600.0, only_ids=ids, tracks={track}, tools=tools)]
