"""Contract dispatch for category C (uses only the public part of an instance).

A candidate answer is (routed circuit on n_physical qubits, initial_layout). Primary checker: mapping replay
(contracts/routing.py). For n_physical <= QCEC_MAX the answer is also cross-checked with MQT QCEC on the fixed-order
reading of the routed circuit (routing_equiv track only; commuting reorders are not unitary-equivalent gate by gate
unless the block gates commute, which QCEC would confirm but at higher cost, so the commuting track relies on replay).
Disagreement between the two checkers is reported as "checker_disagreement" and never counts as a pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ...contracts.routing import check_routing_equiv, crosscheck_qcec
from ...core.circuit import Circuit

QCEC_MAX = 16


@dataclass
class CVerdict:
    status: str
    reason: str = ""
    circuit: Circuit | None = None
    details: dict = field(default_factory=dict)


def verify(public: dict, track: str, circuit: Circuit, initial_layout, qcec: bool = True) -> CVerdict:
    spec = public["tracks"][track]
    orig = Circuit.from_json(public["circuit"])
    if circuit.n != public["n_physical"]:
        return CVerdict("fail", f"routed circuit has {circuit.n} qubits, device has {public['n_physical']}")
    if initial_layout is None:
        return CVerdict("fail", "initial_layout is required")
    blocks = public.get("blocks") if spec["contract"] == "routing_commuting" else None
    v = check_routing_equiv(orig, circuit, list(initial_layout), public["coupling_edges"], blocks)
    method = "mapping replay" + (" (commuting blocks)" if blocks is not None else "")
    if v.status != "pass":
        return CVerdict(v.status, v.reason, None, {"method": method, **v.details})
    if qcec and blocks is None and circuit.n <= QCEC_MAX:
        q = crosscheck_qcec(orig, circuit, list(initial_layout))
        method += f" + QCEC ({q})"
        if q not in ("equivalent", "equivalent_up_to_global_phase", "equivalent_up_to_phase"):
            return CVerdict("checker_disagreement", f"replay passed but QCEC says {q}", None, {"method": method, **v.details})
    return CVerdict("pass", "", circuit, {"method": method, **v.details})
