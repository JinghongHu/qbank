"""Job list for category-A baselines: every instance x track x applicable tool."""
from __future__ import annotations

from ..core.instance import iter_instances, load_index, load_public
from ..core.seeds import derive_int
from . import tools_a as T

QMAP_HEUR = "mqt.qmap.synthesize_clifford(heuristic)"
QMAP_SAT = "mqt.qmap.synthesize_clifford(SAT, two_qubit_gates)"


def tool_version(tool: str) -> str:
    v = T._versions()
    for prefix, dist in (("qiskit.", "qiskit"), ("stim.", "stim"), ("rustiq.", "rustiq"), ("mqt.qecc", "mqt.qecc"),
                         ("mqt.qmap", "mqt.qmap"), ("pytket", "pytket")):
        if tool.startswith(prefix):
            ver = f"{dist}=={v[dist]}"
            if "+sabre" in tool:
                ver += f"; router qiskit=={v['qiskit']}"
            if dist == "pytket":
                ver += f"; pytket-qiskit=={v['pytket-qiskit']}; stim=={v['stim']}"
            return ver
    return "unknown"


def jobs_A(budget: float = 60.0, only_ids: set | None = None, tracks: set | None = None, tools: set | None = None,
           anytime_only: bool = False) -> list[dict]:
    jobs = []
    for row in sorted(load_index("A"), key=lambda r: (r["n"], r["id"])):   # small instances first
        if only_ids and row["id"] not in only_ids:
            continue
        pub = load_public("A", row["hash"])
        for track, spec in pub["tracks"].items():
            if tracks and track not in tracks:
                continue
            names = list(T.tools_for(pub, track))
            if spec["connectivity"] == "all" and spec["contract"] != "codespace_state":
                # QMAP heuristic mode segfaults deterministically on this machine (Phase 0; 11 further crashes in this
                # run). It is no longer re-run per instance (each crash raises a macOS crash-report dialog); aggregation
                # records it as "unavailable" with a pointer to the crash evidence.
                names += [QMAP_SAT] if pub["n"] <= 3 else []
            for tool in names:
                if tools and tool not in tools:
                    continue
                anytime = T.is_anytime(tool)
                if anytime_only and not anytime:
                    continue
                cfg = {"budget_s": budget, "anytime": anytime, "threads": 1,
                       "params": {"syndrome_iter": 100} if "rustiq" in tool else {}}
                jobs.append({"category": "A", "iid": row["id"], "hash": row["hash"], "track": track, "tool": tool,
                             "version": tool_version(tool), "config": cfg, "budget": budget,
                             "seed": derive_int("A-baseline", row["hash"], tool, track) % (2 ** 31)})
    return jobs
