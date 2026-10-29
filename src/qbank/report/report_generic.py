"""Reports for categories B-E (counts, best-tool shares, probe gaps, baseline-at-optimum, non-pass list).
Everything is computed from data/v1 files; writes results/<date>/REPORT_<C>.md (English), report_<C>.json and CSVs."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from ..core.instance import PKG_ROOT, data_root, load_index, load_public
from ..core.splits import load_manifest

TITLE = {"B": "Category B (classical-function oracle compilation)", "C": "Category C (routing and commuting-gate scheduling)",
         "D": "Category D (non-Clifford state preparation)"}
STATUS_ZH = {"pass": "pass", "fail": "fail", "tool_error": "tool error", "unsupported": "unsupported", "timeout": "timeout",
             "crash": "crash", "unavailable": "unavailable", "unverified": "unverified", "checker_disagreement": "checker disagreement"}
KIND_ZH = {"optimal": "proven optimum", "lower_bound": "lower bound", "upper_bound": "upper bound (constructed value)",
           "numerical_optimum": "numerical optimum (unproven)", "reported_optimum": "constructed value (not independently verified)",
           None: "(see CSV)"}


def _read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def _csv(path: Path, header, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def make_report(cat: str, out_dir: Path | None = None, log=print) -> str:
    out = out_dir or (PKG_ROOT / "results" / date.today().isoformat())
    out.mkdir(parents=True, exist_ok=True)
    man = load_manifest(cat)
    idx = {r["id"]: r for r in load_index(cat)}
    split_of = {e["id"]: s for s, es in man["splits"].items() for e in es}
    base = data_root() / "baselines" / cat
    recs = _read_jsonl(base / "records.jsonl")
    best = _read_jsonl(base / "best_known.jsonl")
    opt = _read_jsonl(data_root() / "optimal" / f"{cat}.jsonl")
    published = _read_jsonl(data_root() / "published" / f"{cat}.jsonl")
    metric_of = {}
    for row in idx.values():
        for tr, spec in load_public(cat, row["hash"])["tracks"].items():
            metric_of[(row["id"], tr)] = spec["metric"]
    rep: dict = {"date": date.today().isoformat(), "category": cat, "totals": man["totals"]}
    md: list[str] = []
    add = md.append
    cmd = f"qbank generate {cat} && qbank baselines {cat} && qbank optimal {cat} && qbank aggregate {cat} && qbank report {cat}"

    # 1. counts
    counts = defaultdict(Counter)
    for iid, s in split_of.items():
        counts[s][(idx[iid]["family"], idx[iid]["size_bin"])] += 1
    rows = [[s, f, b, c] for s in ("train", "val", "test_in", "test_ood", "probe") for (f, b), c in sorted(counts[s].items())]
    _csv(out / f"{cat}_counts.csv", ["split", "family", "size_bin", "count"], rows)
    rep["counts"] = rows
    add("## 1. Instances per split (by family and size bin)\n")
    add(f"Reproduce: `qbank generate {cat}` (CSV: `{cat}_counts.csv`)\n")
    add("| Split | Family | Size bin | Count |\n|---|---|---|---|")
    for r in rows:
        add(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")
    add("\nTotal: " + ", ".join(f"{s} {man['totals'][s]}" for s in man["totals"]) + f"; {sum(man['totals'].values())} in all.\n")

    # 2. best-tool share per track
    by_it = defaultdict(list)
    for r in recs:
        by_it[(r["instance_id"], r["track"])].append(r)
    share = defaultdict(Counter)
    n_inst = Counter()
    no_pass = Counter()
    for (iid, tr), rs in by_it.items():
        ok = [r for r in rs if r["status"] == "pass"]
        if not ok:
            no_pass[tr] += 1
            continue
        m = metric_of.get((iid, tr))
        best_v = min(r["costs"][m] for r in ok)
        n_inst[tr] += 1
        for tool in sorted({r["tool"] for r in ok if r["costs"][m] == best_v}):
            share[tr][tool] += 1
    add("## 2. Share of instances on which each tool is the best baseline, per track\n")
    add(f"Definition: for each (instance, track), take the verified records with the smallest value of the track metric; on ties each tool is counted once. Reproduce: `{cmd}` (CSV: `{cat}_best_tool_share.csv`)\n")
    rows = []
    for tr in sorted(set(n_inst) | set(no_pass)):
        add(f"### Track `{tr}` ({n_inst[tr]} instances with a verified baseline; {no_pass[tr]} without any verified baseline)\n")
        add("| Tool | Times best (including ties) | Share |\n|---|---|---|")
        for tool, c in share[tr].most_common():
            add(f"| {tool} | {c} | {100 * c / max(1, n_inst[tr]):.1f}% |")
            rows.append([tr, tool, c, n_inst[tr], round(100 * c / max(1, n_inst[tr]), 2)])
        add("")
    _csv(out / f"{cat}_best_tool_share.csv", ["track", "tool", "best_count", "instances", "percent"], rows)
    rep["best_tool_share"] = rows

    # 3. probe / optimum gaps
    bk = {(b["instance_id"], b["track"]): b for b in best}
    add("## 3. Known optima and lower bounds: gap of the best baseline\n")
    add("A \"proven optimum\" gives the true gap; the gap to a \"lower bound\" is an upper bound on the true gap; an \"upper bound\" is the value "
        "of a known construction (a published construction, or a constructed circuit verified by this benchmark). "
        f"Reproduce as above (CSV: `{cat}_optimum_gap.csv`)\n")
    rows = []
    for o in sorted(opt, key=lambda o: (split_of.get(o["instance_id"], "?"), o["instance_id"], o["track"])):
        b = bk.get((o["instance_id"], o["track"]), {})
        bb = b.get("best_baseline_value")
        v = o.get("value")
        gap = None if (bb is None or v is None) else bb - v
        rows.append([o["instance_id"], split_of.get(o["instance_id"]), o["track"], o.get("kind"), v, bb, b.get("source"), gap,
                     o.get("status") or o.get("proof", "")[:120]])
    _csv(out / f"{cat}_optimum_gap.csv", ["instance", "split", "track", "kind", "value", "best_baseline", "best_source", "gap", "note"], rows)
    rep["optimum_gap"] = rows
    summ = defaultdict(lambda: [0, 0, 0, 0.0, 0])            # kind/split -> [n, with baseline, at bound, sum gap, max gap]
    for r in rows:
        key = (r[1], r[3], r[2])
        s = summ[key]
        s[0] += 1
        if r[7] is not None:
            s[1] += 1
            s[2] += int(r[7] == 0)
            s[3] += r[7]
            s[4] = max(s[4], r[7])
    add("| Split | Kind | Track | Entries | With verified baseline | Baseline reaches the value | Mean gap | Max gap |\n|---|---|---|---|---|---|---|---|")
    for (sp, kind, tr), s in sorted(summ.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]), kv[0][2])):
        avg = f"{s[3] / s[1]:.2f}" if s[1] else "-"
        add(f"| {sp} | {KIND_ZH.get(kind, kind)} | {tr} | {s[0]} | {s[1]} | {s[2]} | {avg} | {s[4] if s[1] else '-'} |")
    probe_rows = [r for r in rows if r[1] == "probe"]
    if probe_rows:
        add("\n**probe, entry by entry**:\n")
        add("| Instance | Track | Kind | Value | Best baseline | Source | Gap |\n|---|---|---|---|---|---|---|")
        for r in probe_rows[:80]:
            add(f"| {r[0]} | {r[2]} | {KIND_ZH.get(r[3], r[3])} | {r[4]} | {r[5]} | {r[6]} | {r[7]} |")
        if len(probe_rows) > 80:
            add(f"| ... ({len(probe_rows)} entries in all, see CSV) | | | | | | |")
    add("")

    # 4. baseline at optimum
    add("## 4. Instances where the best baseline already reaches the optimum\n")
    atopt = [r for r in rows if r[3] == "optimal" and r[7] == 0]
    _csv(out / f"{cat}_baseline_at_optimum.csv", ["instance", "split", "track", "value", "best_source"],
         [[r[0], r[1], r[2], r[4], r[6]] for r in atopt])
    rep["baseline_at_optimum"] = len(atopt)
    add(f"{len(atopt)} (instance, track) pairs in all (CSV: `{cat}_baseline_at_optimum.csv`). By split: "
        + ", ".join(f"{s} {c}" for s, c in sorted(Counter(r[1] for r in atopt).items())) + ".\n")
    # 5. non-pass
    add("## 5. Unavailable, crash, timeout, unverified and unsupported list\n")
    add(f"Aggregated by (tool, track, status); individual records in `data/v1/baselines/{cat}/records.jsonl` (CSV: `{cat}_non_pass.csv`)\n")
    c = Counter()
    ex = {}
    for r in recs:
        if r["status"] != "pass":
            k = (r["tool"], r["track"], r["status"])
            c[k] += 1
            ex.setdefault(k, (r["instance_id"], (r.get("reason") or "")[:150]))
    add("| Tool | Track | Status | Count | Example instance | Reason (excerpt) |\n|---|---|---|---|---|---|")
    rows = []
    for (tool, tr, st), n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])):
        e = ex[(tool, tr, st)]
        add(f"| {tool} | {tr} | {STATUS_ZH.get(st, st)} | {n} | {e[0]} | {e[1].replace('|', '/')} |")
        rows.append([tool, tr, st, n, e[0], e[1]])
    _csv(out / f"{cat}_non_pass.csv", ["tool", "track", "status", "count", "example_instance", "reason"], rows)
    rep["non_pass"] = rows

    # 6. published values
    if published:
        add("\n## 6. Published records (with references)\n")
        add(f"Treated as \"reported value only\" unless both semantics and budget match this benchmark's contract (CSV: `{cat}_published.csv`).\n")
        add("| Instance | Track | Value | Width | Reference | Counts toward best_known | Reason not counted |\n|---|---|---|---|---|---|---|")
        rows = []
        for p in published:
            ref = p["reference"]
            add(f"| {p['instance_id']} | {p['track']} | {p['value']} | {p.get('width')} | {ref.get('id')} {ref.get('location')} | "
                f"{'yes' if p['eligible_for_best_known'] else 'no'} | {p.get('ineligible_reason') or ''} |")
            rows.append([p["instance_id"], p["track"], p["value"], p.get("width"), ref.get("id"), p["eligible_for_best_known"]])
        _csv(out / f"{cat}_published.csv", ["instance", "track", "value", "width", "reference", "eligible"], rows)

    from .extras import all_extras
    md.append("")
    md.append(all_extras(cat, out))
    text = f"# qbank v1 - {TITLE[cat]} report\n\nGenerated: {date.today().isoformat()}. This report is generated entirely by `qbank report {cat}` from the files in `data/v1/`.\n\n" \
           + "\n".join(md) + "\n"
    (out / f"REPORT_{cat}.md").write_text(text, encoding="utf-8")
    (out / f"report_{cat}.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return str(out / f"REPORT_{cat}.md")
