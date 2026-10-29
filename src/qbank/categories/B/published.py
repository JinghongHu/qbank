"""Published resource counts relevant to category-B instances, with provenance (Phase-0 recon, access 2026-09-25).

Only rows whose circuit semantics match our bit-flip contract (|x>|y> -> |x>|y xor S(x)>, the "C*" form) are eligible;
a row is eligible for a budgeted track only if its stated width fits the budget. Out-of-place (C0: output starts |0>)
and in-place rows are recorded but NOT eligible (different contract). CX-track values are derived with qbank's fixed
decomposition (Toffoli = 6 CX) and labelled as derived. All are "reported only" (no circuit reproduced locally).
"""
from __future__ import annotations

ACCESS = "2026-09-25"

ENTRIES = [
    # (track, value, width, eligible_semantics, source, location, raw, note)
    ("tof@*", 52, 22, True, {"title": "Synthesizing Quantum Circuits of AES with Lower T-depth and Less Qubits",
                             "authors": "Huang, Sun", "id": "IACR ePrint 2022/620 (ASIACRYPT 2022)"},
     "Table 3 (this paper, C*)", "6 anc / Tof-d 41 / 52 Tof / 336 CNOT / 4 X", "C* form; width = 8 + 8 + 6"),
    ("tof@*", 68, 23, True, {"title": "Quantum Circuit Implementations of AES with Fewer Qubits", "authors": "Zou, Wei, Sun, Liu, Wu",
                             "id": "ASIACRYPT 2020 (IACR archive PDF; no ePrint id found)"},
     "Sec. 4.2, Algorithm 5 (C*)", "7 ancilla, 68 Tof, 352 CNOT, 4 NOT, Tof-d 60", "C* form; width = 8 + 8 + 7"),
    ("tof@*", 60, 66, True, {"title": "Constructing Quantum Implementations with the Minimal T-depth or Minimal Width and Their Applications",
                             "authors": "Huang, Zhang, Lin", "id": "IACR ePrint 2025/212 (EUROCRYPT 2025)"},
     "Table 1 (this work, C0/C*)", "4 / 227/240 / 60 / 8 / 60 / 66", "C* column: 240 CNOT, 60 Tof, width 66"),
    ("t_mbu@inf", 136, 92, True, {"title": "Constructing Quantum Implementations with the Minimal T-depth or Minimal Width and Their Applications",
                                  "authors": "Huang, Zhang, Lin", "id": "IACR ePrint 2025/212 (EUROCRYPT 2025)"},
     "Table 2 (this work, C0/C*)", "525/539 CNOT, 206/238 1qC, 136 T, 26/34 M, T-d 4, FD 93/92, width 84/92",
     "Clifford+T with AND gates and measurement-based uncomputation; C* column"),
    ("cx@inf", 240 + 6 * 60, 66, True, {"title": "Constructing Quantum Implementations with the Minimal T-depth or Minimal Width and Their Applications",
                                        "authors": "Huang, Zhang, Lin", "id": "IACR ePrint 2025/212 (EUROCRYPT 2025)"},
     "Table 1 (this work, C*) -> derived", "240 CNOT + 60 Tof", "derived: CNOT + 6 x Toffoli (qbank fixed decomposition)"),
    ("cx@inf", 336 + 6 * 52, 22, True, {"title": "Synthesizing Quantum Circuits of AES with Lower T-depth and Less Qubits",
                                        "authors": "Huang, Sun", "id": "IACR ePrint 2022/620"},
     "Table 3 (C*) -> derived", "336 CNOT + 52 Tof", "derived: CNOT + 6 x Toffoli (qbank fixed decomposition)"),
    ("tof@*", 34, 90, False, {"title": "Improved Quantum Circuits for AES: Reducing the Depth and the Number of Qubits",
                              "authors": "Liu, Preneel, Zhao, Wang", "id": "IACR ePrint 2023/1417 (ASIACRYPT 2023)"},
     "Table 3 (this paper)", "74+16 / 34 Tof / 168 CNOT / 4 / Tof-d 4",
     "out-of-place (C0): output register must start in |0>; not our bit-flip contract (reference only)"),
]


# v1.2: the new S-box instances (literature search 2026-09-26; values read from the fetched documents). No row with our
# contract (C*: |x>|y> -> |x>|y xor S(x)> with clean ancillas) was found for Camellia, ARIA SB2, CLEFIA, Kuznyechik or
# Magma; the rows below are recorded for reference and are NOT eligible for best_known.
ACCESS_V12 = "2026-09-26"
SBOX_REFS = [
    # (instance id, track, value, width, source, location, raw, note)
    ("B.bitflip.sbox.aria_sb2", "tof@*", 34, 100,
     {"title": "Improved Quantum Analysis of ARIA", "authors": "Oh, Jang, Seo", "id": "IACR ePrint 2024/1986"},
     "Table 2, row S2 / Boyar-Peralta / Ours", "225 CNOT / 4 X / 34 Toffoli / Toffoli-depth 4 / 100 qubits / depth 44",
     "out-of-place with garbage: the output goes to a fresh register and the ancillas are left unclean (compute pass "
     "only); not our contract"),
    ("B.bitflip.sbox.camellia_s1", "tof@*", 54, 20,
     {"title": "(Camellia S-box quantum circuit)", "authors": "Li, Gao, Qin, Wen",
      "id": "Sci. Sin. Phys. Mech. Astron. 53, 240313 (2023), DOI 10.1360/SSPMA-2022-0485"},
     "English abstract (full text not retrieved)", "20 qubits, 54 Toffoli, 196 CNOT, 13 NOT, Toffoli depth 42",
     "semantics not determinable from the abstract (in-place or out-of-place); not eligible"),
]


def published_entries(index_by_id: dict, track_budgets: dict) -> list[dict]:
    """track_budgets: {(instance_id, track): budget or None}."""
    out = []
    for iid, track, value, width, src, loc, raw, note in SBOX_REFS:
        row = index_by_id.get(iid)
        for tr in (["tof@bmin", "tof@1.5bmin", "tof@inf"] if track == "tof@*" else [track]):
            out.append({"instance_id": iid, "instance_hash": row["hash"] if row else None, "track": tr, "value": value,
                        "width": width, "label": f"published: {src['id']} {loc}",
                        "reference": {**src, "location": loc, "raw_value": raw, "access_date": ACCESS_V12},
                        "semantics": note, "eligible_for_best_known": False, "ineligible_reason": "different contract",
                        "status": "reported only"})
    iid = "B.bitflip.sbox.aes"
    row = index_by_id.get(iid)
    for track, value, width, sem_ok, src, loc, raw, note in ENTRIES:
        tracks = ["tof@bmin", "tof@1.5bmin", "tof@inf"] if track == "tof@*" else [track]
        for tr in tracks:
            budget = track_budgets.get((iid, tr))
            fits = budget is None or width <= budget
            out.append({"instance_id": iid, "instance_hash": row["hash"] if row else None, "track": tr, "value": value,
                        "width": width, "label": f"published: {src['id']} {loc}",
                        "reference": {**src, "location": loc, "raw_value": raw, "access_date": ACCESS},
                        "semantics": note, "eligible_for_best_known": bool(row and sem_ok and fits),
                        "ineligible_reason": None if (sem_ok and fits) else ("different contract" if not sem_ok else f"width {width} > budget {budget}"),
                        "status": "reported only"})
    return out
