"""Re-run the time-limited baselines of the test instances at a fixed concurrency.

The main baselines ran many jobs in parallel on a machine with performance and efficiency cores, so a time-limited
tool (anytime search, SAT with a wall-clock limit, ...) did not always get the same compute within its 60 s. For the
final evaluation, candidate programs and these baselines should be compared under the same conditions:

    qbank rebaseline C --split test --tools "qiskit LightSABRE (anytime)" --workers 12

runs every (test instance, track, tool) job with at most `workers` jobs at a time (default: the number of performance
cores). Results go to their own cache namespace "<C>-rebaseline-w<workers>" and to
data/v1/baselines/<C>/rebaseline_w<workers>.jsonl + results/<date>/<C>_rebaseline_w<workers>.csv; they never change
best_known (which stays defined by the main 60 s runs).
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.instance import data_root
from ..core.splits import load_manifest
from . import runner

SPLITS = {"test": ("test_in", "test_ood"), "test_in": ("test_in",), "test_ood": ("test_ood",), "val": ("val",),
          "train": ("train",)}


def time_limited_tools(cat: str) -> set:
    """Default tool set: the budget-sensitive tools of the quality-time curves (anytime tools, and tools that timed
    out at 60 s on the main track)."""
    from .curve import MAIN_TRACK, _records, budget_sensitive_tools
    if cat not in MAIN_TRACK:
        return set()
    return budget_sensitive_tools(cat, _records(cat))


def job_list(cat: str, split: str, tools: set, workers: int, budget: float = 60.0) -> list[dict]:
    man = load_manifest(cat)
    ids = {e["id"] for s in SPLITS[split] for e in man["splits"][s]}
    if cat == "A":
        from .plan_a import jobs_A as J
    elif cat == "B":
        from .job_b import jobs_B as J
    elif cat == "C":
        from .job_c import jobs_C as J
    else:
        from .job_d import jobs_D as J
    out = []
    for j in J(budget=budget, only_ids=ids, tools=tools):
        # the concurrency is part of the configuration, so each concurrency level has its own cache entries
        out.append({**j, "config": {**j["config"], "concurrency": workers}, "ns": f"{cat}-rebaseline-w{workers}"})
    return out


def summarize(cat: str, workers: int, jobs: list[dict], out_dir: Path | None = None) -> list[dict]:
    main = {}
    p = data_root() / "baselines" / cat / "records.jsonl"
    for line in p.read_text().splitlines():
        r = json.loads(line)
        main[(r["hash"], r["track"], r["tool"])] = r
    rows = []
    seen = set()
    for j in jobs:
        key = (j["hash"], j["track"], j["tool"])
        if key in seen:
            continue
        seen.add(key)
        cache = runner.load_cache(j["ns"], j["hash"])
        k = runner.cache_key(j["hash"], j["tool"], j["version"], j["config"], j["track"])
        r = cache.get(k)
        if r is None:
            continue
        m = main.get(key, {})
        metric = (r.get("costs") or m.get("costs") or {})
        rows.append({"instance_id": j["iid"], "track": j["track"], "tool": j["tool"], "workers": workers,
                     "status": r["status"], "value": (r.get("costs") or {}).get(_metric(cat, j)),
                     "main_status": m.get("status"), "main_value": (m.get("costs") or {}).get(_metric(cat, j)),
                     "wall_tool_s": r.get("wall_tool_s"), "concurrency": r.get("concurrency")})
    base = data_root() / "baselines" / cat
    (base / f"rebaseline_w{workers}.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    if out_dir is not None:
        import csv
        with open(out_dir / f"{cat}_rebaseline_w{workers}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["instance", "track", "tool", "workers", "status", "value", "main_status", "main_value"])
            for r in rows:
                w.writerow([r["instance_id"], r["track"], r["tool"], r["workers"], r["status"], r["value"],
                            r["main_status"], r["main_value"]])
    return rows


def _metric(cat: str, job: dict) -> str:
    from ..core.instance import load_public
    return load_public(cat, job["hash"])["tracks"][job["track"]]["metric"]
