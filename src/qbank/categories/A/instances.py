"""Build category-A Instance records and dispatch contract checks per track.

Tracks:
  CSS code:       a2a_2q (css_logical_zero), line_2q, grid_2q (css_logical_zero on a graph, output map free),
                  codespace_a2a_2q (codespace_state)
  rand_stab:      a2a_2q, line_2q, grid_2q (stabilizer_state)
  non-CSS code:   a2a_2q (stabilizer_state = |0..0>_L for the published logical-Z basis), codespace_a2a_2q
Metric of every track: two_qubit_gates (cx = cz = cy = 1, swap = 3).
"""
from __future__ import annotations

import math

import numpy as np

from ...core import gf2
from ...core.canon import content_hash
from ...core.circuit import Circuit
from ...core.instance import Instance
from ...core.pauli import PauliRows, rref as pauli_rref
from ...contracts.stabilizer import (GATE_SET_A, Verdict, targets_css_codespace, targets_css_zero,
                                     targets_from_strings, verify_stabilizer_contract)

GATE_SET_PUBLIC = [g for g in GATE_SET_A if g != "id"]


def line_edges(n: int) -> list[list[int]]:
    return [[i, i + 1] for i in range(n - 1)]


def grid_edges(n: int) -> tuple[int, list[list[int]]]:
    """n nodes laid out row-major on a grid with ceil(sqrt(n)) columns (last row may be partial)."""
    cols = max(1, math.ceil(math.sqrt(n)))
    e = []
    for i in range(n):
        if (i % cols) + 1 < cols and i + 1 < n:
            e.append([i, i + 1])
        if i + cols < n:
            e.append([i, i + cols])
    return cols, e


def _tracks(n: int, main_contract: str, with_graphs: bool, with_codespace: bool) -> dict:
    t = {"a2a_2q": {"contract": main_contract, "metric": "two_qubit_gates", "connectivity": "all"}}
    if with_graphs:
        t["line_2q"] = {"contract": main_contract, "metric": "two_qubit_gates", "output_map": "free",
                        "connectivity": {"kind": "line", "edges": line_edges(n)}}
        cols, ge = grid_edges(n)
        t["grid_2q"] = {"contract": main_contract, "metric": "two_qubit_gates", "output_map": "free",
                        "connectivity": {"kind": "grid", "cols": cols, "edges": ge}}
    if with_codespace:
        t["codespace_a2a_2q"] = {"contract": "codespace_state", "metric": "two_qubit_gates", "connectivity": "all"}
    return t


def _track_list(tracks: dict) -> list[dict]:
    out = []
    for name, spec in tracks.items():
        conn = spec["connectivity"]
        out.append({"name": name, "contract": spec["contract"], "metric": spec["metric"],
                    "connectivity": conn if isinstance(conn, str) else conn["kind"]})
    return out


def css_instance(iid: str, code, family: str, params: dict, source: dict, private: dict, graphs: bool = True) -> Instance:
    n = code.n
    tracks = _tracks(n, "css_logical_zero", graphs, True)
    public = {"format": "qbank.public/1", "task": "css_logical_zero", "n": n,
              "hx": gf2.sparse_rows(code.hx), "hz": gf2.sparse_rows(code.hz),
              "gate_set": GATE_SET_PUBLIC, "tracks": tracks}
    canon = {"n": n, "hx_rref": gf2.sparse_rows(gf2.rref(code.hx)[0]), "hz_rref": gf2.sparse_rows(gf2.rref(code.hz)[0]),
             "gate_set": GATE_SET_PUBLIC, "tracks": tracks}
    h = content_hash("A", "css_logical_zero", canon)
    return Instance(iid, "A", "css_logical_zero", family, source, params, public, private,
                    ["css_logical_zero", "codespace_state"], _track_list(tracks), h)


def stab_instance(iid: str, stabs: PauliRows, family: str, params: dict, source: dict, private: dict,
                  code_stabs: PauliRows | None = None, graphs: bool = True) -> Instance:
    n = stabs.n
    tracks = _tracks(n, "stabilizer_state", graphs, code_stabs is not None)
    public = {"format": "qbank.public/1", "task": "stabilizer_state", "n": n, "stabilizers": stabs.to_strings(),
              "gate_set": GATE_SET_PUBLIC, "tracks": tracks}
    canon = {"n": n, "stab_rref": pauli_rref(stabs)[0].to_strings(), "gate_set": GATE_SET_PUBLIC, "tracks": tracks}
    if code_stabs is not None:
        public["code_stabilizers"] = code_stabs.to_strings()
        canon["code_stab_rref"] = pauli_rref(code_stabs)[0].to_strings()
    h = content_hash("A", "stabilizer_state", canon)
    contracts = ["stabilizer_state"] + (["codespace_state"] if code_stabs is not None else [])
    return Instance(iid, "A", "stabilizer_state", family, source, params, public, private, contracts, _track_list(tracks), h)


# ------------------------------------------------------------------ contract dispatch (uses ONLY the public part)
def targets_for(public: dict, contract: str) -> PauliRows:
    n = public["n"]
    if contract == "css_logical_zero":
        return targets_css_zero(gf2.from_sparse_rows(public["hx"], n))
    if contract == "codespace_state":
        if public["task"] == "css_logical_zero":
            return targets_css_codespace(gf2.from_sparse_rows(public["hx"], n), gf2.from_sparse_rows(public["hz"], n))
        return targets_from_strings(public["code_stabilizers"], n)
    if contract == "stabilizer_state":
        return targets_from_strings(public["stabilizers"], n)
    raise ValueError(f"unknown contract {contract}")


def verify(public: dict, track: str, circuit: Circuit, output_map=None) -> Verdict:
    spec = public["tracks"][track]
    conn = spec["connectivity"]
    edges = None if conn == "all" else conn["edges"]
    # an output map is allowed on every track (10-29, after the Codex review: kept on purpose). From |0...0> a final
    # relabelling of the qubits costs nothing on all-to-all tracks -- relabelling the wires of the whole circuit gives
    # the same gates on the target qubits -- so it never lowers the optimum; on grid / line it is the free layout.
    return verify_stabilizer_contract(circuit, targets_for(public, spec["contract"]), width=public["n"],
                                      edges=edges, output_map=output_map)
