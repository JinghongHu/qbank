"""Contract dispatch for category B (uses only the public part of an instance)."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field

from ...contracts.oracle import GATE_SET_B, verify_oracle
from ...core.aig import AIG
from ...core.circuit import Circuit


@dataclass
class BVerdict:
    status: str
    reason: str = ""
    circuit: Circuit | None = None
    pauli_correction: list = field(default_factory=list)
    details: dict = field(default_factory=dict)


# Contract version of category B (10-24 merge, C2): 2 adds the track tof_clifford@inf. Version-1 tracks (tof@*, t_mbu@inf,
# cx@inf) are unchanged; their instances keep their spec. tof_clifford@inf = clean oracle, Toffoli count, with the gate
# set GATE_SET_B without t, tdg, mbu and id: every free gate is a Clifford gate, so every non-Clifford effect comes
# from a charged gate (ccx, ccz, rccx: 1 Toffoli; rc3x: 2). tof@inf itself allows t / tdg (a CCZ written as 7 T + CX
# costs 0 Toffolis there) and stays as it was: a historical contract, never changed in place.
CONTRACT_VERSION = 2
GATE_SET_TOF_CLIFFORD = tuple(g for g in GATE_SET_B if g not in ("t", "tdg", "mbu", "id"))
TRACKS_V2 = {
    "tof_clifford@inf": {"metric": "toffoli_count", "qubit_budget": None, "mbu_allowed": False,
                         "gate_set": list(GATE_SET_TOF_CLIFFORD), "contract_version": 2},
}


def track_spec(public: dict, track: str) -> dict:
    """The track spec of an instance: its own record, or for a version-2 track an instance generated before it existed,
    the frozen TRACKS_V2 entry (same register and contract, only the gate set differs). Unknown track: KeyError."""
    spec = public.get("tracks", {}).get(track)
    if spec is None and track in TRACKS_V2:
        spec = {"contract": public["task"], **TRACKS_V2[track]}
    if spec is None:
        raise KeyError(f"category B has no track {track!r}")
    return spec


def track_gates(spec: dict) -> tuple:
    """Allowed gate names of a track spec (an explicit gate_set wins; else GATE_SET_B, mbu only when allowed)."""
    if spec.get("gate_set") is not None:
        return tuple(spec["gate_set"])
    return tuple(g for g in GATE_SET_B if spec.get("mbu_allowed") or g != "mbu")


def verify(public: dict, track: str, circuit: Circuit, output_map=None) -> BVerdict:
    if output_map is not None:
        return BVerdict("fail", "output maps are not part of the oracle contract")
    spec = track_spec(public, track)
    aig = AIG.from_aiger(base64.b64decode(public["aiger_b64"]))
    kind = "bitflip" if public["task"] == "oracle_bitflip_clean" else "phase"
    gates = track_gates(spec)
    v = verify_oracle(circuit, aig, public["n_inputs"], public["n_outputs"], kind, budget=spec.get("qubit_budget"),
                      gate_set=gates)
    return BVerdict(v.status, v.reason, circuit if v.status == "pass" else None, [], {"method": v.method, **v.details})
