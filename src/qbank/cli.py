"""qbank command line (generate, import, verify, baselines, split, report, export).

  qbank generate A                  build instances, variants and the (unfrozen) split manifest
  qbank baselines A [--budget 60] [--workers 10] [--tracks ...] [--tools ...] [--ids ...] [--anytime-only]
  qbank import A                    external baseline circuits (MQT QECC releases, QECirc) + published values
  qbank optimal A [--max-n 12] [--timeout 1800]
  qbank aggregate A                 baseline table + best_known
  qbank verify <C> <instance_id> <track> <answer.(json|qasm|stim)> [--output-map 0,1,...]
  qbank split A --freeze | --check
  qbank report A                    results/<date>/ (REPORT_A.md, report_A.json, CSV tables)
  qbank export A --out DIR          evolution pack: candidate_view (train/val public) + harness (best_known, verifier)
  qbank rebaseline C --split test --tools T...     re-run time-limited baselines at fixed concurrency (separate)
  qbank export B --out DIR --subset structural     the same, restricted to a named subset (qbank.eval.subsets)
  qbank prompt-lint A FILE          check an LLM task description against the forbidden-term list
  qbank rebuild A|B|C|D|all         generate -> [import] -> baselines -> optimal -> aggregate -> report (uses the cache);
                                    "all" also writes results/<date>/REPORT.md
  qbank report all                  overall report only (REPORT.md) from the per-category outputs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _log(*a):
    print(*a, flush=True)


def cmd_generate(args):
    if args.category in ("B", "C", "D"):
        import importlib
        build_x = importlib.import_module(f".categories.{args.category}.build", __package__).build
        r = build_x(log=_log)
        _log(json.dumps({k: v for k, v in r.items() if k not in ("cross_split_pairs",)}, indent=1))
        return
    if args.category != "A":
        sys.exit(f"category {args.category} not implemented yet")
    from .categories.A.build import build
    r = build(include_756=not args.no_756)
    _log(json.dumps({k: v for k, v in r.items() if k != "suspected_duplicates"}, indent=1))
    _log(f"suspected duplicates within a split: {len(r['suspected_duplicates'])}")


def cmd_baselines(args):
    from .baselines.runner import run_jobs
    kw = dict(only_ids=set(args.ids) if args.ids else None, tracks=set(args.tracks) if args.tracks else None,
              tools=set(args.tools) if args.tools else None)
    if args.category == "A":
        from .baselines.plan_a import jobs_A
        jobs = jobs_A(budget=args.budget, anytime_only=args.anytime_only, **kw)
    elif args.category == "B":
        from .baselines.job_b import jobs_B
        jobs = jobs_B(budget=args.budget, **kw)
    elif args.category == "C":
        from .baselines.job_c import jobs_C
        jobs = jobs_C(budget=args.budget, **kw)
    elif args.category == "D":
        from .baselines.job_d import jobs_D
        jobs = jobs_D(budget=args.budget, **kw)
    else:
        sys.exit(f"category {args.category} not implemented yet")
    if args.limit:
        jobs = jobs[: args.limit]
    run_jobs(jobs, workers=args.workers, log=_log)


def cmd_import(args):
    from .baselines import external_a
    _log("[import] MQT QECC released circuits")
    n1 = external_a.import_mqt(log=_log)
    _log("[import] QECirc circuits")
    n2 = external_a.import_qecirc(log=_log)
    _log(f"[import] stored {n1 + n2} external records")
    write_published()
    write_sources()


def write_published():
    from .categories.A.published import published_entries
    from .core.instance import data_root, load_index
    idx = {r["id"]: r for r in load_index("A")}
    ents = published_entries(idx)
    p = data_root() / "published" / "A.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n" for e in ents), encoding="utf-8")
    return ents


def write_sources():
    from .core.canon import dump_json, file_sha256
    from .core.instance import PKG_ROOT, data_root
    ext = PKG_ROOT / ".cache" / "external"
    src = {
        "mqt-qecc": {"url": "https://github.com/munich-quantum-toolkit/qecc", "licence": "MIT", "redistributed": False,
                     "used": "scripts/encoding_circuits/best_circuits, scripts/ft_stateprep/eval/circuits (released circuits)"},
        "qecirc": {"url": "https://github.com/qecirc/qecirc-website", "licence": "code MIT, data CC BY-SA 4.0", "redistributed": False,
                   "used": "data_yaml/circuits (|0_L>/|+_L> preparations) and data_yaml/matrices", "paper": "arXiv:2609.20182"},
        "stabilizerbench": {"url": "https://github.com/uw-math-ai/quantum-ai", "licence": "none (all rights reserved)", "redistributed": False,
                            "used": "construction rule for composite codes only (re-implemented); data/benchmarks.json checksum",
                            "paper": "arXiv:2604.21287"},
        "mqt.qecc (PyPI 2.0.0)": {"url": "https://pypi.org/project/mqt.qecc/2.0.0/", "licence": "MIT", "redistributed": False,
                                  "used": "code instances (steane/shor/golay/carbon/tetrahedral, misc/*.txt), color-code and many-hypercube lattices"},
    }
    for k in ("mqt-qecc", "qecirc", "stabilizerbench"):
        cf = ext / f"{k}.COMMIT"
        src[k]["commit"] = cf.read_text().strip() if cf.exists() else None
    sb = ext / "stabilizerbench" / "data" / "benchmarks.json"
    if sb.exists():
        src["stabilizerbench"]["data/benchmarks.json sha256"] = file_sha256(sb)
    src["_fetch_script"] = "data/v1/external/fetch_A.sh"
    src["_access_date"] = "2026-09-25"
    dump_json(src, data_root() / "external" / "SOURCES_A.json")


def cmd_optimal(args):
    if args.category in ("B", "D"):
        from .optimal.bde_optimal import run as run_bde
        _log(json.dumps(run_bde(args.category, log=_log)))
        return
    if args.category == "C":
        from .optimal.c_optimal import run as run_c
        _log(json.dumps(run_c(log=_log)))
        return
    from .optimal.a_optimal import run
    run(max_n=args.max_n, timeout=args.timeout, workers=args.workers, log=_log)


def cmd_aggregate(args):
    from .baselines.aggregate import aggregate
    if args.category == "A":
        pub = write_published()
    elif args.category == "B":
        pub = write_published_b()
    else:
        pub = []
    _log(json.dumps(aggregate(args.category, workers=args.workers, published=pub, log=_log)))


def write_published_b():
    from .categories.B.published import published_entries
    from .core.instance import data_root, load_index, load_public
    idx = {r["id"]: r for r in load_index("B")}
    budgets = {}
    for iid, row in idx.items():
        if iid.startswith("B.bitflip.sbox"):
            for tr, spec in load_public("B", row["hash"])["tracks"].items():
                budgets[(iid, tr)] = spec.get("qubit_budget")
    ents = published_entries(idx, budgets)
    p = data_root() / "published" / "B.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n" for e in ents), encoding="utf-8")
    return ents


def cmd_verify(args):
    """Answer file: .json {"circuit": <qbank JSON>, "output_map"?, "initial_layout"?, "outputs"?, "estimator"?} (any
    category), or for A also .stim / .qasm (circuit only)."""
    from .core.circuit import Circuit
    from .core.costs import costs
    from .core.instance import load_instance
    from .eval.api import verify
    inst = load_instance(args.category, args.instance_id)
    p = Path(args.circuit)
    extra = {}
    om = [int(x) for x in args.output_map.split(",")] if args.output_map else None
    if p.suffix == ".json":
        d = json.loads(p.read_text())
        c = Circuit.from_json(d.get("circuit", d))
        om = d.get("output_map", om)
        for k in ("initial_layout", "outputs", "estimator"):
            if d.get(k) is not None:
                extra[k] = d[k]
    elif p.suffix == ".stim":
        import stim
        c = Circuit.from_stim(stim.Circuit(p.read_text()), inst.public["n"])
    else:
        from qiskit import qasm3
        c = Circuit.from_qiskit(qasm3.loads(p.read_text()), clifford_only=(args.category == "A"))
    v = verify(inst, c, args.track, om, **extra)
    out = v.to_json() if hasattr(v, "to_json") else {"status": v.status, "reason": v.reason,
                                                       "details": getattr(v, "details", {})}
    if v.status == "pass":
        out["costs"] = costs(c)
    _log(json.dumps(out, indent=1, default=str))


def cmd_curve(args):
    """Quality-time curve: 0.1x and 10x budget reruns on a stratified subset (namespace <C>-curve)."""
    from datetime import date
    from .baselines.curve import jobs, summarize
    from .baselines.runner import run_jobs
    from .core.instance import PKG_ROOT
    if args.extended:
        from .baselines.curve import extended_jobs
        ej = extended_jobs(args.category)
        _log(f"[curve {args.category}] extended 10x runs: {len(ej)} jobs")
        run_jobs(ej, workers=args.workers, log=_log)
        return
    js, ids, tools = jobs(args.category)
    _log(f"[curve {args.category}] {len(ids)} instances, tools {sorted(tools)}, {len(js)} jobs")
    if not args.summary_only:
        run_jobs(js, workers=args.workers, log=_log)
    out = PKG_ROOT / "results" / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    rows = summarize(args.category, out)
    _log(f"[curve {args.category}] {len(rows)} (instance, tool) rows")


def cmd_rebaseline(args):
    """Re-run time-limited baselines on test instances at a fixed concurrency; stored separately,
    never part of best_known."""
    from datetime import date
    from .baselines.rebaseline import job_list, summarize, time_limited_tools
    from .baselines.runner import core_counts, run_jobs
    from .core.instance import PKG_ROOT
    p_cores, _ = core_counts()
    workers = args.workers or p_cores
    if workers > p_cores:
        _log(f"[rebaseline] note: {workers} workers > {p_cores} performance cores (jobs beyond that run on efficiency cores)")
    tools = set(args.tools) if args.tools else time_limited_tools(args.category)
    js = job_list(args.category, args.split, tools, workers, args.budget)
    if args.limit:
        js = js[: args.limit]
    _log(f"[rebaseline {args.category}] split {args.split}, tools {sorted(tools)}, {len(js)} jobs, {workers} workers")
    run_jobs(js, workers=workers, log=_log)
    out = PKG_ROOT / "results" / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    rows = summarize(args.category, workers, js, out)
    _log(f"[rebaseline {args.category}] {len(rows)} rows -> data/v1/baselines/{args.category}/rebaseline_w{workers}.jsonl")


def cmd_repro(args):
    """Baseline reproducibility: re-run 20 random baseline records."""
    from datetime import date
    from .baselines.repro import run
    from .core.instance import PKG_ROOT
    out = PKG_ROOT / "results" / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    rows = run(args.category, out, log=_log)
    _log(f"[repro {args.category}] {sum(r['reproduced'] for r in rows)}/{len(rows)} reproduced")


def cmd_split(args):
    from .core import splits
    if args.freeze:
        _log(f"frozen {args.category}: sha256 {splits.freeze(args.category)}")
    if args.check:
        _log(f"frozen manifest intact: {splits.verify_frozen(args.category)}")


def cmd_report(args):
    if args.category == "all":
        from .report.overall import make_overall
        _log(make_overall(log=_log))
        return
    if args.category != "A":
        from .report.datasheet_bcde import make_datasheet as ds
        from .report.report_generic import make_report as rp
        _log(rp(args.category, log=_log))
        _log(ds(args.category, log=_log))
        return
    from .report.datasheet_a import make_datasheet
    from .report.report_a import make_report
    _log(make_report(log=_log))
    _log(make_datasheet(log=_log))


def cmd_export(args):
    from .eval.export import export_pack
    _log(json.dumps(export_pack(args.category, Path(args.out), args.subset), indent=1))


def cmd_prompt_lint(args):
    from .core.prompts import lint
    hits = lint(args.category, Path(args.file).read_text(encoding="utf-8"))
    _log(json.dumps(hits, indent=1, ensure_ascii=False))
    sys.exit(1 if hits else 0)


def cmd_rebuild(args):
    """generate -> [import (A)] -> baselines -> optimal -> aggregate -> report; `qbank rebuild all` does A..D and the
    overall report. Cached baseline runs are reused (cache key = instance hash, tool, version, config, track)."""
    import copy
    cats = ["A", "B", "C", "D"] if args.category == "all" else [args.category]
    for cat in cats:
        a = copy.copy(args)
        a.category = cat
        steps = [cmd_generate] + ([cmd_import] if cat == "A" else []) + [cmd_baselines, cmd_optimal, cmd_aggregate, cmd_report]
        for f in steps:
            f(a)
    if args.category == "all":
        from .report.overall import make_overall
        _log(make_overall(log=_log))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="qbank", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **kw):
        p = sub.add_parser(name, **kw)
        p.add_argument("category")
        p.set_defaults(fn=fn)
        return p
    g = add("generate", cmd_generate)
    g.add_argument("--no-756", action="store_true")
    b = add("baselines", cmd_baselines)
    for p in (b,):
        p.add_argument("--budget", type=float, default=60.0)
        p.add_argument("--workers", type=int, default=10)
        p.add_argument("--tracks", nargs="*")
        p.add_argument("--tools", nargs="*")
        p.add_argument("--ids", nargs="*")
        p.add_argument("--limit", type=int, default=0)
        p.add_argument("--anytime-only", action="store_true")
    add("import", cmd_import)
    o = add("optimal", cmd_optimal)
    o.add_argument("--max-n", type=int, default=12)
    o.add_argument("--timeout", type=int, default=1800)
    o.add_argument("--workers", type=int, default=8)
    a = add("aggregate", cmd_aggregate)
    a.add_argument("--workers", type=int, default=10)
    v = add("verify", cmd_verify)
    v.add_argument("instance_id")
    v.add_argument("track")
    v.add_argument("circuit")
    v.add_argument("--output-map")
    cu = add("curve", cmd_curve)
    cu.add_argument("--workers", type=int, default=8)
    cu.add_argument("--summary-only", action="store_true")
    cu.add_argument("--extended", action="store_true", help="10x runs on every instance where an anytime tool timed out")
    add("repro", cmd_repro)
    rb = add("rebaseline", cmd_rebaseline)
    rb.add_argument("--split", default="test", choices=["test", "test_in", "test_ood", "val", "train"])
    rb.add_argument("--tools", nargs="*", default=None, help="tool names (default: the category's time-limited tools)")
    rb.add_argument("--workers", type=int, default=0, help="concurrent jobs (default: number of performance cores)")
    rb.add_argument("--budget", type=float, default=60.0)
    rb.add_argument("--limit", type=int, default=0, help="run only the first N jobs (smoke test)")
    s = add("split", cmd_split)
    s.add_argument("--freeze", action="store_true")
    s.add_argument("--check", action="store_true")
    add("report", cmd_report)
    e = add("export", cmd_export)
    e.add_argument("--out", required=True)
    e.add_argument("--subset", default=None, help="named subset, e.g. B: structural | solution_sparse")
    pl = add("prompt-lint", cmd_prompt_lint)
    pl.add_argument("file")
    r = add("rebuild", cmd_rebuild)
    r.add_argument("--workers", type=int, default=10)
    r.set_defaults(no_756=False, budget=60.0, tracks=None, tools=None, ids=None, limit=0, anytime_only=False,
                   max_n=12, timeout=1800)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
