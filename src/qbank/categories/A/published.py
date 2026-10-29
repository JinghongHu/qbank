"""Published |0_L> two-qubit-gate counts for category A, with provenance.

Every number below was read from the cited source during Phase 0 (see phase0/recon/recon_A.md; access date
2026-09-25) — nothing is filled in from memory. Semantics are recorded per entry. A value is eligible for best_known
only if (i) its metric matches ours (non-FT, unitary, all-to-all, |0...0>_L, CX/CZ count with no uncounted SWAPs) and
(ii) the code is the same as our instance's code (by definition of a standard code, or verified by matrix comparison).
Values whose circuits were released are ALSO re-verified locally as baseline records ("published:*" tools); such
entries are marked reproduced=True in the report.
"""
from __future__ import annotations

ACCESS = "2026-09-25"
P2605 = {"title": "Synthesis and Optimization of Encoding Circuits for Fault-Tolerant Quantum Computation",
         "authors": "Peham, Steinberg, Wille, Heußen", "arxiv": "2605.15266v1"}
P2603 = {"title": "Fast stabilizer state preparation via AI-optimized graph decimation",
         "authors": "Doherty, Puviani, Brewer, Matos, Amaro, Criger, Stephen", "arxiv": "2603.17743v1"}
P2408 = {"title": "Automated Synthesis of Fault-Tolerant State Preparation Circuits for Quantum Error Correction Codes",
         "authors": "Peham, Schmid, Berent, Müller, Wille", "arxiv": "2408.11894v3"}
P2503 = {"title": "Heuristic and Optimal Synthesis of CNOT and Clifford Circuits", "authors": "Webster, Koutsioumpas, Browne",
         "arxiv": "2503.14660v3"}
P1106 = {"title": "Fault-tolerant ancilla preparation and noise threshold lower bounds for the 23-qubit Golay code",
         "authors": "Paetznick, Reichardt", "arxiv": "1106.2190v2"}
P2601 = {"title": "Unitary fault-tolerant encoding of Pauli states in surface codes", "authors": "Colmenarez, Zen, Olle, Marquardt, Müller",
         "arxiv": "2601.05113v1"}

NONFT = "non-FT unitary |0...0>_L preparation, all-to-all, count of CNOT/CZ as printed"

# (instance id, value, source, location, raw, semantics, eligible, note)
ENTRIES = [
    ("A.css_zero.color_666.d3", 8, P2503, "Table 5 (A*, Greedy, RLFQC columns)", "8", NONFT, True, "Steane code"),
    ("A.css_zero.color_666.d3", 8, P1106, "Figure 5(b) caption", "eight CNOT gates", NONFT, True, "Steane code"),
    ("A.css_zero.rot_surface.d3", 8, P2408, "Table 1 (SAT column; optimal within the CNOT-only model)", "8", NONFT, True, ""),
    ("A.css_zero.rot_surface.d5", 28, P2408, "Table 1 (Heur column)", "28", NONFT, True, ""),
    ("A.css_zero.rot_surface.d7", 60, P2601, "Table 1, formula (3t+1)(d-1), t=floor((d-1)/2)", "(3t+1)(d-1) -> 60",
     "FT unitary encoder with plaquette-local gates (an upper bound for our non-FT all-to-all task); value computed from the printed formula", True, "formula-derived"),
    ("A.css_zero.rot_surface.d9", 104, P2601, "Table 1 formula", "(3t+1)(d-1) -> 104", "as above", True, "formula-derived"),
    ("A.css_zero.rot_surface.d11", 160, P2601, "Table 1 formula", "(3t+1)(d-1) -> 160", "as above", True, "formula-derived"),
    ("A.css_zero.qrm.m4", 22, P2408, "Table 1 (SAT column)", "22", NONFT, True, "[[15,1,3]] tetrahedral / QRM"),
    ("A.css_zero.qhamming.r4", 22, P2605, "Table 1 and Table 2 (Zero, Ours)", "22", NONFT, True, "[[15,7,3]]"),
    ("A.css_zero.color_488.d5", 23, P2605, "Table 1/2 (Zero, Ours)", "23", NONFT, True, "[[17,1,5]]"),
    ("A.css_zero.color_666.d5", 27, P2605, "Table 1/2 (Zero, Ours)", "27", NONFT, True, "[[19,1,5]]"),
    ("A.css_zero.color_488.d7", 45, P2605, "Table 2 (Zero, Ours)", "45", NONFT, True, "[[31,1,7]]"),
    ("A.css_zero.qhamming.r5", 52, P2605, "Table 1 (Zero, Ours)", "52", NONFT, True, "[[31,21,3]]"),
    ("A.css_zero.color_666.d7", 57, P2605, "Table 2 (Zero, Ours)", "57", NONFT, True, "[[37,1,7]]"),
    ("A.css_zero.sporadic.golay", 44, P2603, "Table 1 (QuSynth column) and Fig. 21", "(44, 8)", NONFT, True,
     "no circuit released (reported only); quantum Golay code is unique up to qubit permutation"),
    ("A.css_zero.sporadic.golay", 45, P2605, "Table 2 (Zero, Ours)", "45", NONFT, True, ""),
    ("A.css_zero.sporadic.golay", 57, P1106, "Figure 4 caption", "57 CNOT gates applied in seven rounds", NONFT, True, ""),
    ("A.css_zero.sporadic.carbon", 16, P2603, "Table 1 (BeFS column)", "(16, 4)", NONFT, True,
     "reported only; Carbon code identity by definition (C4 into C6), not compared matrix-by-matrix"),
    ("A.css_zero.sporadic.mqt_30_6_5", 61, P2605, "Table 2 (Zero, Ours)", "61", NONFT, True, "[[30,6,5]] symplectic double"),
    ("A.css_zero.shor_concat.3x3", 8, P2408, "Table 2 (SAT column)", "8", NONFT, True, "Shor [[9,1,3]]"),
    ("A.css_zero.bb_published.bravyi72", 150, P2605, "Table 2 (Zero, Ours)", "150", NONFT, True, "MQT's code = Bravyi's (identical row spaces)"),
    ("A.css_zero.bb_published.bravyi108", 402, P2605, "Table 2 (Zero, Ours); the text says 430", "402", NONFT, True,
     "MQT's code = Bravyi's up to the qubit permutation block-swap+transpose (verified in Phase 1)"),
    ("A.css_zero.bb_published.bravyi144", 330, P2605, "Table 2 (Zero, Ours); text: 330 CNOTs at depth 17", "330", NONFT, True,
     "MQT's code = Bravyi's up to block-swap+transpose (verified in Phase 1)"),
    ("A.css_zero.bb_published.bravyi144", 357, P2603, "Table 1 (RL, + LC-optimization row)", "(357, 18)", NONFT, True,
     "reported only; the paper cites Bravyi et al. for the code"),
    ("A.css_zero.bb_mqt_n90_d2.mqt90", 134, P2605, "Table 2 (Zero, Ours), row labelled [[90,8,10]]", "134", NONFT, True,
     "value for MQT's construct_bb_code(90) code (l and m swapped, distance <= 2), which is this instance; it is not a "
     "result for Bravyi's [[90,8,10]] (instance A.css_zero.bb_published.bravyi90)"),
    ("A.stab.sporadic.mqt_8_3_3", 11, P2605, "Table 2 (Zero, Ours)", "11", "G counts CX only; the released circuit also has 5 SWAPs",
     False, "metric mismatch: not eligible (released circuit re-costed separately if it verifies)"),
    ("A.stab.sporadic.mqt_15_3_5", 36, P2605, "Table 2 (Zero, Ours)", "36", "G counts CX only; the released circuit also has 11 SWAPs",
     False, "metric mismatch: not eligible"),
]


def published_entries(index_by_id: dict) -> list[dict]:
    out = []
    for iid, value, src, loc, raw, sem, eligible, note in ENTRIES:
        row = index_by_id.get(iid)
        out.append({"instance_id": iid, "instance_hash": row["hash"] if row else None, "track": "a2a_2q", "value": value,
                    "label": f"published: {src['arxiv']} {loc}", "reference": {**src, "location": loc, "raw_value": raw,
                                                                               "access_date": ACCESS},
                    "semantics": sem, "eligible_for_best_known": bool(eligible and row), "note": note,
                    "status": "reported only"})
    return out
