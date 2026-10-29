"""Worker-side execution of one category-D baseline job, and the D job list."""
from __future__ import annotations

import time
import traceback

from ..core.instance import load_index, load_public
from ..core.seeds import derive_int


def run_job_D(job: dict, public: dict, signal_verify) -> dict:
    from ..categories.D.instances import verify
    from ..core.costs import costs
    from . import tools_d as T
    tool, track = job["tool"], job["track"]
    res = {"tool": tool, "track": track}
    t0 = time.monotonic()
    c0 = time.process_time()
    try:
        cands = T.D_TOOLS[tool](public, track, job["seed"], t0 + job["budget"])
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
    edges = public["tracks"][track].get("coupling_edges")
    if edges is not None:                       # connectivity track: route every candidate onto the line (SABRE, O3)
        from .tools_d import route_line
        routed = []
        for cd in cands:
            try:
                routed += route_line(cd, public["n"], edges, job["seed"])
            except Exception as e:
                routed.append({"error": f"{type(e).__name__}: {e}"})
        errs = [r["error"] for r in routed if "error" in r]
        cands = [r for r in routed if "error" not in r]
        if not cands:
            return {**res, "status": "tool_error", "reason": f"routing failed: {errs[:1]}", "wall_tool_s": wall_tool}
        if time.monotonic() - t0 > job["budget"]:
            return {**res, "status": "timeout", "reason": "routing finished after the budget", "wall_tool_s": time.monotonic() - t0}
    scored = sorted(((costs(cd["circuit"])[metric], costs(cd["circuit"])["gate_count"], i, cd) for i, cd in enumerate(cands)),
                    key=lambda s: s[:3])
    fails = []
    tv = time.monotonic()
    for _, _, i, cd in scored[:8]:
        v = verify(public, track, cd["circuit"], cd.get("output_map"))
        if v.status == "pass":
            return {**res, "status": "pass", "costs": costs(v.circuit), "meta": cd.get("meta", {}), "n_candidates": len(cands),
                    "circuit": v.circuit.to_json(), "output_map": cd.get("output_map"), "fidelity": v.fidelity, "verify_method": v.details.get("method"),
                    "wall_tool_s": wall_tool, "cpu_tool_s": cpu_tool, "wall_verify_s": time.monotonic() - tv}
        fails.append(f"{v.status}: {v.reason}")
    status = "unverified" if fails and all(f.startswith("unverified") for f in fails) else "fail"
    return {**res, "status": status, "reason": fails[0] if fails else "no candidate", "all_reasons": fails[:6],
            "n_candidates": len(cands), "wall_tool_s": wall_tool, "cpu_tool_s": cpu_tool, "wall_verify_s": time.monotonic() - tv}


def tool_version(tool: str) -> str:
    import importlib.metadata as md
    v = f"qbank-d-tools-1; qiskit=={md.version('qiskit')}"
    if "qclib" in tool:
        v += f"; qclib=={md.version('qclib')}"
    if "bqskit" in tool:
        v += f"; bqskit=={md.version('bqskit')}"
    return v


def jobs_D(budget: float = 60.0, only_ids=None, tracks=None, tools=None) -> list[dict]:
    from . import tools_d as T
    jobs = []
    for row in sorted(load_index("D"), key=lambda r: (r.get("n") or 0, r["id"])):
        if only_ids and row["id"] not in only_ids:
            continue
        pub = load_public("D", row["hash"])
        n = pub["n"]
        for track, spec in pub["tracks"].items():
            if tracks and track not in tracks:
                continue
            for tool in T.D_TOOLS:
                if tools and tool not in tools:
                    continue
                if tool in T.APPROX_ONLY and spec["contract"] != "state_approx":
                    continue
                dense_tool = tool.startswith(("qiskit", "qclib")) and "Merge" not in tool
                if dense_tool and n > T.DENSE_MAX:
                    continue            # recorded as "not applicable" by the report (dense methods need 2^n amplitudes)
                if "bqskit" in tool and n > T.BQSKIT_MAX:
                    continue
                jobs.append({"category": "D", "iid": row["id"], "hash": row["hash"], "track": track, "tool": tool,
                             "version": tool_version(tool), "config": {"budget_s": budget, "threads": 1}, "budget": budget,
                             "seed": derive_int("D-baseline", row["hash"], tool, track) % (2 ** 31)})
    return jobs
