"""Worker-side execution of one category-C baseline job, and the C job list."""
from __future__ import annotations

import time
import traceback

from ..core.instance import load_index, load_public
from ..core.seeds import derive_int


def run_job_C(job: dict, public: dict, signal_verify) -> dict:
    from ..categories.C.instances import verify
    from ..core.costs import costs
    from . import tools_c as T
    tool, track = job["tool"], job["track"]
    res = {"tool": tool, "track": track}
    t0 = time.monotonic()
    c0 = time.process_time()
    try:
        cands = T.C_TOOLS[tool](public, track, job["seed"], t0 + job["budget"])
    except NotImplementedError as e:
        return {**res, "status": "unsupported", "reason": str(e), "wall_tool_s": time.monotonic() - t0}
    except TimeoutError as e:
        return {**res, "status": "timeout", "reason": str(e), "wall_tool_s": time.monotonic() - t0}
    except Exception as e:
        return {**res, "status": "tool_error", "reason": f"{type(e).__name__}: {str(e)[:300]}",
                "trace": traceback.format_exc()[-1500:], "wall_tool_s": time.monotonic() - t0}
    wall_tool, cpu_tool = time.monotonic() - t0, time.process_time() - c0
    signal_verify()
    if wall_tool > job["budget"]:
        return {**res, "status": "timeout", "reason": f"result delivered after the budget ({wall_tool:.1f} s)",
                "wall_tool_s": wall_tool}
    metric = public["tracks"][track]["metric"]
    alt = "two_qubit_depth" if metric == "swaps" else "swaps"
    scored = sorted(((costs(cd["circuit"])[metric], costs(cd["circuit"])[alt], i, cd) for i, cd in enumerate(cands)),
                    key=lambda s: s[:3])
    fails = []
    tv = time.monotonic()
    for _, _, i, cd in scored[:5]:
        v = verify(public, track, cd["circuit"], cd["initial_layout"])
        if v.status == "pass":
            return {**res, "status": "pass", "costs": costs(v.circuit), "meta": cd.get("meta", {}), "n_candidates": len(cands),
                    "circuit": v.circuit.to_json(), "initial_layout": [int(x) for x in cd["initial_layout"]],
                    "verify_method": v.details.get("method"), "wall_tool_s": wall_tool, "cpu_tool_s": cpu_tool,
                    "wall_verify_s": time.monotonic() - tv}
        fails.append(f"{v.status}: {v.reason}")
    return {**res, "status": "fail", "reason": fails[0] if fails else "no candidate", "all_reasons": fails[:5],
            "n_candidates": len(cands), "wall_tool_s": wall_tool, "cpu_tool_s": cpu_tool, "wall_verify_s": time.monotonic() - tv}


def tool_version(tool: str) -> str:
    import importlib.metadata as md
    v = f"qbank-c-tools-1; qiskit=={md.version('qiskit')}"
    if "tket" in tool:
        v += f"; pytket=={md.version('pytket')}; pytket-qiskit=={md.version('pytket-qiskit')}"
    if "qmap" in tool:
        v += f"; mqt.qmap=={md.version('mqt.qmap')}"
    if "OLSQ2" in tool:
        v += f"; OLSQ2@0d7066f45b07+env/patches/olsq2_qiskit2.patch; z3-solver=={md.version('z3-solver')}"
    return v


def jobs_C(budget: float = 60.0, only_ids=None, tracks=None, tools=None) -> list[dict]:
    from . import tools_c as T
    jobs = []
    for row in sorted(load_index("C"), key=lambda r: (r.get("n") or 0, r["id"])):
        if only_ids and row["id"] not in only_ids:
            continue
        pub = load_public("C", row["hash"])
        for track, spec in pub["tracks"].items():
            if tracks and track not in tracks:
                continue
            for tool in T.C_TOOLS:
                if tools and tool not in tools:
                    continue
                if tool in T.COMMUTING_ONLY and spec["contract"] != "routing_commuting":
                    continue
                jobs.append({"category": "C", "iid": row["id"], "hash": row["hash"], "track": track, "tool": tool,
                             "version": tool_version(tool), "config": {"budget_s": budget, "threads": 1}, "budget": budget,
                             "seed": derive_int("C-baseline", row["hash"], tool, track) % (2 ** 31)})
    return jobs
