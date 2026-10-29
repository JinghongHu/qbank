"""Contract dispatch for category D (uses only the public part of an instance)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ...contracts.state import GATE_SET_D, verify_state
from ...core.circuit import Circuit


@dataclass
class DVerdict:
    status: str
    reason: str = ""
    circuit: Circuit | None = None
    fidelity: float | None = None
    details: dict = field(default_factory=dict)


def verify(public: dict, track: str, circuit: Circuit, output_map=None) -> DVerdict:
    spec = public["tracks"][track]
    thr = spec.get("min_fidelity") if spec["contract"] == "state_approx" else None
    if output_map is not None and not spec.get("output_map_allowed"):
        return DVerdict("fail", "output maps are only allowed on connectivity tracks")
    v = verify_state(circuit, public["n"], public["amplitudes"], thr, GATE_SET_D, spec.get("coupling_edges"), output_map)
    return DVerdict(v.status, v.reason, circuit if v.status == "pass" else None, v.fidelity, {**v.details})
