"""Category A data version 1.2.0 (10-28): named codes inside the training size range of the task packs' v2 splits.

qbank's test_in holds color_666 d9, color_488 d9, qrm m7 / m8 (and qhamming r6 / r7), which never enter a task pack, so
the upper end of the pack's training range needs larger named codes that are not in qbank yet:
  color_666 d13 (n = 127), color_488 d13 (n = 97), qrm.m7r2 = QRM(2, 7) (n = 127)        -> qbank train (pack train)
  color_666 d11 (n = 91), color_488 d11 (n = 71), qrm.m6r2 = QRM(2, 6) (n = 63)           -> qbank val (pack test)
(AB_design.md 3). Every code is verified (commutation, k; distance exact when the kernel is small, else a low-weight
search bound) and must differ from every existing A instance (all five splits) in (n, row space of Hx) -- the A task
depends only on it -- and in the permutation invariants of build.invariants (stricter: equal invariants = rejected).
"""
from __future__ import annotations

from ...core import gf2
from . import codes as C
from .generate import Planned, _css

VERSION = "1.2.0"
RULES_NOTE = ("A 1.2.0 (10-28): named codes color_666 d11 / d13, color_488 d11 / d13, qrm QRM(2, m) m = 6, 7 added "
              "to train (pack train / val) and val (pack test); existing entries unchanged (core/extend.py)")
QBANK_SPLIT = {"train": "train", "val": "train", "test": "val"}
# (family, parameters, task-pack split)
CODES = [("color_666", {"d": 13}, "train"), ("color_666", {"d": 11}, "test"),
         ("color_488", {"d": 13}, "train"), ("color_488", {"d": 11}, "test"),
         ("qrm", {"m": 7, "r": 2}, "train"), ("qrm", {"m": 6, "r": 2}, "test")]
# not added: qrm.m5r2 = QRM(2, 5) [[31,1,7]] has the same build.invariants as color_488 d7 [[31,1,7]] (pack test), so it is
# treated as a duplicate (10-28 run; AB_LOG.md)


def _code(fam, p):
    if fam == "qrm":
        c = C.quantum_reed_muller_r(p["m"], p["r"])
        c.reported = {"d": min(2 ** (p["r"] + 1) - 1, 2 ** (p["m"] - p["r"]) - 1),
                      "source": "QRM(r, m) distance min(2^(r+1) - 1, 2^(m-r) - 1) (formula; not recomputed)"}
        return c, f"A.css_zero.qrm.m{p['m']}r{p['r']}"
    c = C.color_code(fam.split("_")[1], p["d"])
    return c, f"A.css_zero.{fam}.d{p['d']}"


def _rowspace_key(n, hx_rows):
    m = gf2.from_sparse_rows(hx_rows, n)
    red, piv = gf2.rref(m)
    return n, tuple(map(tuple, gf2.sparse_rows(red[:len(piv)])))


def extension(existing, log=print) -> tuple[list[Planned], dict]:
    """New planned instances of A 1.2.0 given the existing instances (Instance objects, all splits)."""
    from .build import invariants
    keys, invs = {}, {}
    for inst in existing:
        if inst.public["task"] != "css_logical_zero":
            continue
        keys.setdefault(_rowspace_key(inst.public["n"], inst.public["hx"]), inst.id)
        invs.setdefault(invariants(inst), inst.id)
    ids = {i.id for i in existing}
    planned, report = [], {"version": VERSION, "instances": []}
    for fam, p, pack_split in CODES:
        code, iid = _code(fam, p)
        if iid in ids:
            raise RuntimeError(f"A 1.2.0: {iid} exists already")
        qsplit = QBANK_SPLIT[pack_split]
        pl = _css(iid, code, fam, dict(p), qsplit, extra={"added_in": VERSION, "pack_v2_split": pack_split})
        v = pl.inst.private["code"]["verification"]
        if not v["commute"] or v["k"] != 1:
            raise RuntimeError(f"A 1.2.0: {iid} fails verification {v}")
        k = _rowspace_key(code.n, pl.inst.public["hx"])
        if k in keys:
            raise RuntimeError(f"A 1.2.0: {iid} has the Hx row space of {keys[k]}")
        inv = invariants(pl.inst)
        if inv in invs:
            raise RuntimeError(f"A 1.2.0: {iid} has the invariants of {invs[inv]} (treated as a duplicate)")
        keys[k], invs[inv] = iid, iid
        ids.add(iid)
        planned.append(pl)
        report["instances"].append({"id": iid, "qbank_split": qsplit, "pack_v2_split": pack_split, "n": code.n,
                                    "verification": v, "reported": code.reported or None})
        log(f"[A 1.2.0] {iid} n={code.n} k={v['k']} d={v.get('distance')} -> qbank {qsplit} (pack {pack_split})")
    return planned, report
