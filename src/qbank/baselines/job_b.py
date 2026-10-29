"""Worker-side execution of one category-B baseline job, and the B job list."""
from __future__ import annotations

import functools
import time
import traceback

from ..core.instance import load_index, load_public
from ..core.seeds import derive_int


def run_job_B(job: dict, public: dict, signal_verify) -> dict:
    from ..categories.B.instances import verify
    from ..core.costs import costs
    from . import tools_b as T
    tool, track = job["tool"], job["track"]
    res = {"tool": tool, "track": track}
    t0 = time.monotonic()
    c0 = time.process_time()
    try:
        cands = T.tool_fn(tool)(public, track, job["seed"], t0 + job["budget"])
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
    scored = sorted(((costs(cd["circuit"])[metric], cd["circuit"].n, i, cd) for i, cd in enumerate(cands)), key=lambda s: s[:3])
    fails = []
    tv = time.monotonic()
    for _, _, i, cd in scored:
        v = verify(public, track, cd["circuit"])
        if v.status == "pass":
            return {**res, "status": "pass", "costs": costs(v.circuit), "meta": cd.get("meta", {}), "n_candidates": len(cands),
                    "circuit": v.circuit.to_json(), "output_map": None, "pauli_correction": [], "verify_method": v.details.get("method"),
                    "wall_tool_s": wall_tool, "cpu_tool_s": cpu_tool, "wall_verify_s": time.monotonic() - tv}
        fails.append(f"{v.status}: {v.reason}")
    status = "unverified" if fails and all(f.startswith("unverified") for f in fails) else "fail"
    return {**res, "status": status, "reason": fails[0] if fails else "no candidate", "n_candidates": len(cands),
            "wall_tool_s": wall_tool, "cpu_tool_s": cpu_tool, "wall_verify_s": time.monotonic() - tv}


@functools.lru_cache(maxsize=None)
def tool_version(tool: str) -> str:
    import importlib.metadata as md
    from ..core.instance import PKG_ROOT
    abc = (PKG_ROOT / "external" / "src" / "abc.COMMIT")
    abc_c = abc.read_text().strip() if abc.exists() else "ab2139ee0c418f54136deb4e8e89eeea3b87efc8"
    v = f"qbank-b-tools-1; qiskit=={md.version('qiskit')}; python-sat=={md.version('python-sat')}"
    if "abc" in tool or "pebbling" in tool:
        v += f"; ABC@{abc_c}"
    if tool.startswith(("pebbling SAT", "XAG + MC")):
        # v1.2: SAT conflict budgets instead of wall-clock slices (deterministic results)
        from .tools_b import PEBBLE_CONFLICTS, PEBBLE_CONFLICTS_TIGHTEN, PEBBLE_MAX_STEPS
        from ..core.xag import EXACT_CONFLICTS
        if tool.startswith("pebbling SAT"):
            v += (f"; deterministic budgets (v1.2b): {PEBBLE_CONFLICTS} conflicts/call to the first schedule, then "
                  f"<= {PEBBLE_MAX_STEPS} tightening calls of {PEBBLE_CONFLICTS_TIGHTEN}")
        else:
            v += f"; deterministic budgets (v1.2): exact MC {EXACT_CONFLICTS} conflicts per AND count"
    if "mockturtle" in tool:
        from ..core.canon import file_sha256
        from .tools_b import MINMC_BIN, MINMC_DB6
        mt = (PKG_ROOT / "external" / "src" / "mockturtle.COMMIT")
        drv = PKG_ROOT / "env" / "minmc" / "minmc.cpp"
        v += (f"; mockturtle@{mt.read_text().strip() if mt.exists() else '?'}; driver sha256 "
              f"{file_sha256(drv)[:16] if drv.exists() else '?'}; db6 sha256 {file_sha256(MINMC_DB6)[:16] if MINMC_DB6.exists() else 'missing'}; ABC@{abc_c}")
    return v


def jobs_B(budget: float = 60.0, only_ids=None, tracks=None, tools=None) -> list[dict]:
    from . import tools_b as T
    jobs = []
    for row in sorted(load_index("B"), key=lambda r: (r.get("n") or 0, r["id"])):
        if only_ids and row["id"] not in only_ids:
            continue
        pub = load_public("B", row["hash"])
        for track, spec in pub["tracks"].items():
            if tracks and track not in tracks:
                continue
            for tool in T.B_TOOLS:
                if tools and tool not in tools:
                    continue
                if spec.get("mbu_allowed") and not tool.startswith(("bennett", "cone_bennett", "XAG", "solution enumeration")):
                    continue       # MBU track: tools that emit measurement-based-uncomputation variants (XAG, Bennett) or
                    #                whose unitary circuits are cheap enough to compete (solution enumeration)
                jobs.append({"category": "B", "iid": row["id"], "hash": row["hash"], "track": track, "tool": tool,
                             "version": tool_version(tool), "config": {"budget_s": budget, "threads": 1}, "budget": budget,
                             "seed": derive_int("B-baseline", row["hash"], tool, track) % (2 ** 31)})
    # v1.2: all tof@inf jobs first, then the other tracks, so that identical circuits of the other tracks find the
    # verdict of the SAT miter in the memo (contracts/oracle.py) instead of repeating it
    order = {"tof@inf": 0, "cx@inf": 1, "t_mbu@inf": 2, "tof@1.5bmin": 3, "tof@bmin": 4}
    jobs.sort(key=lambda j: order.get(j["track"], 5))       # stable: keeps the size order within a track
    return jobs
