"""Report sections shared by all categories (added after the 2026-09-26 review): data version, test_ood split by
family/source, quality-time curve, baseline reproducibility, and for B the split into
solution-sparse vs structured families."""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from ..core.instance import data_root, load_index, load_private
from ..core.splits import load_manifest, version_history

MAIN_TRACK = {"A": "a2a_2q", "B": "tof@inf", "C": "swaps", "D": "cx"}
SOURCE_NOTE = {
    "queko": "zero-SWAP construction (known optimum 0, with witness): mainly a correctness check, little room for improvement, should not be merged into a geometric-mean score",
    "qubikos": "constructed optimal SWAP count known (not independently verified): the external source with real room for improvement",
    "mqtbench": "algorithm families not used in training (no known optimum)", "hamlib": "unseen lattice Hamiltonians (no known optimum)",
}


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def version_lines(cat: str) -> list[str]:
    man = load_manifest(cat)
    v = man.get("qbank_version", "1.0.0")
    L = [f"Data version: **{cat} v{v}**."]
    hist = version_history().get(cat, [])
    for e in hist:
        if e.get("reason"):
            L.append(f"Changes in v{e['version']}: {e['reason']}.")
        if e.get("sha256"):
            L.append(f"v{e['version']} was superseded by v{e.get('superseded_by', '?')} (frozen on {e.get('frozen')}, manifest sha256 "
                     f"`{e['sha256'][:16]}...`, archived at `data/v1/{e['archived']}`).")
    return [" ".join(L), ""]


def ood_by_family(cat: str) -> list[str]:
    man = load_manifest(cat)
    idx = {r["id"]: r for r in load_index(cat)}
    track = MAIN_TRACK[cat]
    best = {(b["instance_id"], b["track"]): b for b in _jsonl(data_root() / "baselines" / cat / "best_known.jsonl")}
    opt = defaultdict(list)
    for o in _jsonl(data_root() / "optimal" / f"{cat}.jsonl"):
        if o.get("track", track) == track and o.get("value") is not None:
            opt[o["instance_id"]].append(o)
    fam = defaultdict(list)
    for e in man["splits"]["test_ood"]:
        fam[idx[e["id"]]["family"]].append(e["id"])
    L = ["## test_ood by source/family", "",
         f"Main track `{track}`. OOD conclusions should be reported per source; do not mix different sources into one average.", "",
         "| Source/family | Instances | With verified baseline | Median best baseline | With known optimum/constructed value | Of these, baseline reaches the value | Note |", "|---|---|---|---|---|---|---|"]
    for f, ids in sorted(fam.items()):
        vals = [best[(i, track)]["value"] for i in ids if best.get((i, track), {}).get("value") is not None]
        with_opt = [i for i in ids if opt.get(i)]
        at = sum(1 for i in with_opt if best.get((i, track), {}).get("best_baseline_value") is not None
                 and best[(i, track)]["best_baseline_value"] <= min(o["value"] for o in opt[i]))
        med = statistics.median(vals) if vals else "-"
        L.append(f"| {f} | {len(ids)} | {len(vals)} | {med} | {len(with_opt)} | {at} | {SOURCE_NOTE.get(f, '')} |")
    return L + [""]


def curve_section(cat: str, out: Path) -> list[str]:
    p = out / f"{cat}_quality_time.csv"
    if not p.exists():
        return ["## Quality-time curve (0.1x / 1x / 10x budget)", "", "Not run for this category (category E has no tool that improves with budget and no tool that times out within 60 s).", ""]
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    by_tool = defaultdict(list)
    for r in rows:
        by_tool[r["tool"]].append(r)
    L = ["## Quality-time curve (0.1x / 1x / 10x budget)", "",
         f"On {len({r['instance_id'] for r in rows})} instances from stratified sampling (one per family x size bin, plus instances that timed out at 60 s), "
         "budget-sensitive tools (tools that improve over time, and tools that timed out at 60 s) were rerun at 6 s and 600 s; the 60 s point is the main baseline record. "
         f"These results are stored separately and **do not enter best_known** (best_known is defined by the uniform 60 s budget). Individual rows in `{cat}_quality_time.csv`, "
         f"reproduce: `qbank curve {cat}`.", "",
         "| Tool | Instances | Pass at 6 s | Pass at 60 s | Pass at 600 s | Timeout at 60 s → pass at 600 s | 600 s better than 60 s | Median improvement (60 s/600 s) |",
         "|---|---|---|---|---|---|---|---|"]
    for tool, rs in sorted(by_tool.items()):
        p6 = sum(1 for r in rs if r.get("status_6") == "pass")
        p60 = sum(1 for r in rs if r.get("status_60") == "pass")
        p600 = sum(1 for r in rs if r.get("status_600") == "pass")
        rescued = sum(1 for r in rs if r.get("status_60") != "pass" and r.get("status_600") == "pass")
        better, ratios = 0, []
        for r in rs:
            try:
                a, b = float(r["value_60"]), float(r["value_600"])
            except (TypeError, ValueError):
                continue
            if b < a:
                better += 1
            if b > 0:
                ratios.append(a / b)
        med = f"{statistics.median(ratios):.3f}" if ratios else "-"
        L.append(f"| {tool} | {len(rs)} | {p6} | {p60} | {p600} | {rescued} | {better} | {med} |")
    resc = [r for r in rows if r.get("status_60") != "pass" and r.get("status_600") == "pass"]
    if resc:
        L += ["", "(instance, tool) pairs that time out at 60 s and pass at 600 s: " + "; ".join(f"{r['instance_id']} / {r['tool']} (value at 600 s {r['value_600']})"
                                                            for r in resc[:12]) + ("..." if len(resc) > 12 else "") + ". "
              "On these instances the 60 s baseline underestimates existing tools; consult this table when using best_known."]
    return L + [""]


def repro_section(cat: str, out: Path) -> list[str]:
    p = data_root() / "baselines" / cat / "repro.json"
    if not p.exists():
        return ["## Baseline reproducibility (rerun of 20 random records)", "", "(Not run yet: `qbank repro " + cat + "`)", ""]
    d = json.loads(p.read_text())
    L = ["## Baseline reproducibility (rerun of 20 random records)", "",
         f"{d['n']} randomly sampled passing baseline records were rerun: deterministic tools must give a gate-for-gate identical circuit, randomized tools are rerun once with the recorded trial seed. "
         + (f"Result: **{d['reproduced']}/{d['n']} identical**. " if "reverified" not in d or not d["reverified"] else
          f"Result (run {d.get('run_date', '')}): of {d['n']} records, **{d['gate_identical']} gate-for-gate identical**, "
          f"**{d['reverified']} reruns pass the checker** (tools that depend on the system's floating-point linear algebra are only required to pass the checker on rerun; cost differences in the table below), "
          f"{d['n'] - d['reproduced']} not reproduced. ") + f"Reproduce: `qbank repro {cat}` (CSV: `{cat}_repro.csv`).", ""]
    if d.get("excluded_tools"):
        L.append("Excluded from sampling (time-limited searches whose results depend on run time and cannot be reproduced bit for bit under a different machine load): " + ", ".join(d["excluded_tools"]) + ".")
        L.append("")
    L += ["| Instance | Track | Tool | Seed | Trial seed | Identical |", "|---|---|---|---|---|---|"]
    for r in d["rows"]:
        ok = ("yes (rerun passes the checker; " + r["note"] + ")" if r.get("match") == "reverified" else "yes") if r["reproduced"] \
            else "no: " + r["note"]
        L.append(f"| {r['instance_id']} | {r['track']} | {r['tool']} | {r['seed']} | {r.get('trial_seed') or ''} | {ok} |")
    return L + [""]


def b_sparse_split() -> list[str]:
    idx = {r["id"]: r for r in load_index("B")}
    man = load_manifest("B")
    split_of = {e["id"]: s for s, es in man["splits"].items() for e in es}
    recs = _jsonl(data_root() / "baselines" / "B" / "records.jsonl")
    sparse = {i for i in idx if load_private("B", i)["private"].get("solution_sparse")}
    from ..categories.B.build import SPARSE_RULE
    L = ["## Solution-sparse instances and structural-family instances reported separately (category B)", "",
         "For functions that are true on only very few inputs, a candidate program can first find all solutions classically (by direct enumeration at training sizes, with a SAT solver at test sizes) and then build multi-controlled gates for the solution set. "
         "This is entirely legitimate, and the Toffoli count is often an order of magnitude below generic compilation. Therefore: (1) a \"solution enumeration + prefix-tree multi-controlled gates\" baseline was added and counts toward best_known; "
         "(2) solution-sparse instances are listed separately and **not used for the main conclusion of \"beating the best baseline\"**; (3) unsatisfiable formulas (constant functions, where the empty circuit is optimal) are not included.", "",
         f"The split is by each instance's fraction of solutions, not by family name: the rule is **{SPARSE_RULE}**. "
         "The number of solutions `n_solutions` is computed exactly for all single-output instances (exhaustive for n ≤ 22; larger ones by exact BDD model counting, with SAT enumeration when the BDD exceeds its limit) and stored in the private fields; "
         "multi-output functions are not solution-sparse. Evolution experiments can use `load_split(\"B\", split, subset=\"structural\")` or "
         "`qbank export B --subset structural` to take only structural-family instances.", "",
         "| Family type | Split | Instances | Instances whose main-track best baseline comes from a solution-enumeration tool |", "|---|---|---|---|"]
    best = {(b["instance_id"], b["track"]): b for b in _jsonl(data_root() / "baselines" / "B" / "best_known.jsonl")}
    cnt = defaultdict(lambda: [0, 0])
    for iid, s in split_of.items():
        k = ("solution-sparse" if iid in sparse else "structural", s)
        cnt[k][0] += 1
        b = best.get((iid, "tof@inf"), {})
        if "enumeration" in str(b.get("ties", [])) or "enumeration" in str(b.get("source", "")):
            cnt[k][1] += 1
    for (t, s), (n, e) in sorted(cnt.items()):
        L.append(f"| {t} | {s} | {n} | {e} |")
    return L + [""]


def b_sparse_by_family() -> list[str]:
    idx = {r["id"]: r for r in load_index("B")}
    cnt = defaultdict(lambda: [0, 0])
    for iid, r in idx.items():
        cnt[r["family"]][1 if load_private("B", iid)["private"].get("solution_sparse") else 0] += 1
    L = ["Assignment of each family under the new rule (structural / solution-sparse): " + "; ".join(f"{f} {a}/{b}" for f, (a, b) in sorted(cnt.items())) + ".", ""]
    return L


def concurrency_section(cat: str) -> list[str]:
    """Task list v1.2 §5: compute consistency of time-limited baselines."""
    recs = _jsonl(data_root() / "baselines" / cat / "records.jsonl")
    rec_c = [r["concurrency"] for r in recs if r.get("concurrency")]
    est = [r["concurrency_estimate"]["concurrent_runner_jobs_at_start"] for r in recs if r.get("concurrency_estimate")]
    L = ["## Compute consistency of time-limited baselines", "",
         "Baselines run as parallel processes on an Apple M3 Max (12 performance cores + 4 efficiency cores), each job single-threaded with a 60 s wall-clock budget. When the number of parallel jobs exceeds the number of performance cores, "
         "some jobs land on efficiency cores; time-limited tools (searches that improve over time, wall-clock-limited solvers) therefore do not get exactly the same compute within the same 60 s."]
    if rec_c:
        ws = sorted({c["workers"] for c in rec_c})
        L.append(f"Since v1.2 each record carries `concurrency` (number of concurrency slots, number of jobs running at start, 1-minute load); this category has {len(rec_c)} such records, concurrency slots {ws}.")
    if est:
        L.append(f"The {len(est)} earlier records have no concurrency recorded at run time and were given `concurrency_estimate`: the number of simultaneously running qbank jobs "
                 f"reconstructed from the start/end times of all cached records (1 s resolution, excluding the load of other processes), median {statistics.median(est):.0f}, maximum {max(est)}.")
    L += ["", "For the final evaluation, candidate programs and time-limited baselines should be compared under the same conditions: `qbank rebaseline <C> --split test --tools <time-limited tools>` "
          "reruns these baselines on the test instances at fixed concurrency (default = number of performance cores, i.e. 12); results are stored separately in "
          "`data/v1/baselines/<C>/rebaseline_w<concurrency>.jsonl` (cache namespace `<C>-rebaseline-w<concurrency>`) and do not overwrite best_known. "
          "Without `--tools`, the budget-sensitive tools of the quality-time curve are used.", ""]
    return L


def all_extras(cat: str, out: Path) -> str:
    L = ood_by_family(cat)
    if cat == "B":
        L += b_sparse_split() + b_sparse_by_family()
    L += concurrency_section(cat)
    L += curve_section(cat, out) + repro_section(cat, out)
    return "\n".join(L)
