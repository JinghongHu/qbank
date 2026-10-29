"""Known optima for category C (data/v1/optimal/C.jsonl).

QUEKO    swaps = 0 and depth2q = two-qubit depth of the input circuit, both witnessed by the zero-SWAP routing built from
         meta/*_solution.csv and checked with the routing contract (a routed circuit replays to a topological order of
         the input DAG, so its two-qubit depth is at least the input's; the witness attains it).
QUBIKOS  swaps = the construction value from the file name (arXiv:2502.08839); no witness is shipped, so the record is
         marked verified_by_qbank = false and is used only as a reported optimum.
"""
from __future__ import annotations

import json

from ..categories.C.instances import verify
from ..core.circuit import Circuit
from ..core.costs import costs
from ..core.instance import data_root, load_index, load_private, load_public


def run(log=print) -> dict:
    out = []
    for row in load_index("C"):
        if row["family"] not in ("queko", "qubikos"):
            continue
        priv = load_private("C", row["id"])
        ko = priv["private"]["known_optimal"]
        pub = load_public("C", row["hash"])
        if row["family"] == "queko":
            from ..categories.C.external import queko_witness
            c = Circuit.from_json(pub["circuit"])
            lay = ko["witness_initial_layout"]
            w = queko_witness(c, lay, pub["n_physical"])
            v = verify(pub, "swaps", w, lay)
            d2 = costs(c)["two_qubit_depth"]
            for track, val in (("swaps", 0), ("depth2q", d2)):
                out.append({"instance_id": row["id"], "hash": row["hash"], "track": track, "kind": "optimal", "proven": v.status == "pass",
                            "value": val if v.status == "pass" else None,
                            "status": "optimal (witness verified)" if v.status == "pass" else f"witness failed: {v.reason}",
                            "proof": "QUEKO zero-SWAP construction; lower bound: SWAP count >= 0 / routed 2q depth >= input 2q depth",
                            "witness": {"initial_layout": lay, "circuit": "input circuit relabelled by initial_layout (no SWAPs)"},
                            "verify_method": v.details.get("method")})
        else:
            out.append({"instance_id": row["id"], "hash": row["hash"], "track": "swaps", "kind": "reported_optimum", "proven": False,
                        "value": ko["swaps"],
                        "status": "reported optimal by construction (not verified by qbank)", "proof": ko["source"],
                        "verified_by_qbank": False})
    p = data_root() / "optimal" / "C.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in out))
    n_ok = sum(1 for r in out if str(r["status"]).startswith("optimal"))
    log(f"[optimal C] {len(out)} records, {n_ok} witnessed optima")
    return {"records": len(out), "witnessed": n_ok}
