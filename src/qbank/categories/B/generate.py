"""Category B instances: oracle compilation.

Tracks (all share the instance's register layout and contract):
  tof@bmin     Toffoli/AND count, qubit budget = b_min
  tof@1.5bmin  Toffoli/AND count, qubit budget = ceil(1.5 * b_min)
  tof@inf      Toffoli/AND count, no budget
  t_mbu@inf    T count, measurement-based uncomputation ("mbu") allowed, no budget
  cx@inf       CX count (fixed decompositions, core/costs.py), no budget
  tof_clifford@inf  (contract version 2, 10-24 merge) Toffoli count, no budget, gate set GATE_SET_B without t, tdg,
               mbu and id (instances.TRACKS_V2): the clean Toffoli track without free non-Clifford gates
b_min ("the smallest budget at which a baseline is feasible") = the smallest width among the
constructive baselines run at generation time (Bennett, cone-Bennett after ABC resyn2, ESOP+MCX for <= 16 inputs,
per-clause MCX for CNF-shaped functions); every one of those circuits is checked with the exact oracle checker.
"""
from __future__ import annotations

import base64
import itertools
import math
import time
from dataclasses import dataclass

import numpy as np

from ...core.aig import AIG
from ...core.canon import content_hash, sha256_hex
from ...core.instance import Instance
from ...core.seeds import rng_for, split_seed
from ...contracts.oracle import GATE_SET_B, verify_oracle
from . import functions as F
from .instances import CONTRACT_VERSION, TRACKS_V2

SIZE_BINS = [("S", 6, 12), ("M", 13, 18), ("L", 19, 24), ("XL", 40, 64)]


def size_bin(n: int) -> str:
    for b, lo, hi in SIZE_BINS:
        if lo <= n <= hi:
            return b
    return "XS" if n < 6 else ("between" if n < 40 else "XXL")


@dataclass
class Planned:
    split: str
    inst: Instance
    regen: tuple | None = None


def function_canon(aig: AIG) -> dict:
    """Canonical function identity: truth-table hash per output (n <= 24), else the ABC-strashed binary AIGER."""
    if aig.num_inputs <= 24:
        tt = aig.truth_tables()
        return {"kind": "truth_table", "n": aig.num_inputs, "outputs": [sha256_hex(np.packbits(r).tobytes()) for r in tt]}
    from ...baselines.tools_b import abc_optimize
    s = abc_optimize(aig, "strash").to_aiger_binary()
    return {"kind": "strashed_aig", "n": aig.num_inputs, "sha256": sha256_hex(s)}


def compute_bmin(aig: AIG, kind: str) -> tuple[int, dict]:
    from ...baselines import tools_b as T
    n, m = aig.num_inputs, len(aig.outputs)
    widths = {}
    cands = [("bennett(abc resyn2)", lambda: T.bennett(T.abc_optimize(aig), kind)),
             ("cone_bennett(abc resyn2)", lambda: T.cone_bennett(T.abc_optimize(aig), kind))]
    if n <= 12:   # Qiskit's ESOP merging is super-linear; bounded here because generation has no hard kill
        cands.append(("esop+mcx", lambda: T.esop_oracle(aig, kind, None, time.monotonic() + 120)))
    if T.extract_cnf(aig) is not None:
        cands.append(("per-clause mcx", lambda: T.clause_oracle(aig, kind, None)))
    for name, fn in cands:
        try:
            c = fn()
        except (NotImplementedError, TimeoutError):
            continue
        v = verify_oracle(c, aig, n, m, kind)
        if v.status == "pass":
            widths[name] = c.n
    reg = n + (m if kind == "bitflip" else 0)
    b = min(widths.values()) if widths else None
    if b is None:
        raise RuntimeError("no constructive baseline verified")
    return max(b, reg), widths


def make_instance(iid, aig: AIG, kind: str, family, params, source, private) -> Instance:
    n, m = aig.num_inputs, len(aig.outputs)
    if kind == "phase" and m != 1:
        raise ValueError("phase oracle needs one output")
    bmin, widths = compute_bmin(aig, kind)
    task = "oracle_bitflip_clean" if kind == "bitflip" else "oracle_phase_clean"
    gates = [g for g in GATE_SET_B if g not in ("mbu", "id")]
    tracks = {
        "tof@bmin": {"contract": task, "metric": "toffoli_count", "qubit_budget": bmin, "mbu_allowed": False},
        "tof@1.5bmin": {"contract": task, "metric": "toffoli_count", "qubit_budget": math.ceil(1.5 * bmin), "mbu_allowed": False},
        "tof@inf": {"contract": task, "metric": "toffoli_count", "qubit_budget": None, "mbu_allowed": False},
        "t_mbu@inf": {"contract": task, "metric": "t_count", "qubit_budget": None, "mbu_allowed": True},
        "cx@inf": {"contract": task, "metric": "cx_count", "qubit_budget": None, "mbu_allowed": False},
    }
    v1_tracks = dict(tracks)          # the content hash keeps the version-1 tracks: instance hashes do not change
    tracks.update({k: {"contract": task, **v} for k, v in TRACKS_V2.items()})   # contract version 2 (10-24 merge, C2)
    aig_bytes = aig.to_aiger_binary()
    public = {"format": "qbank.public/1", "task": task, "n_inputs": n, "n_outputs": m,
              "register": {"inputs": list(range(n)), "outputs": list(range(n, n + m)) if kind == "bitflip" else []},
              "aiger_b64": base64.b64encode(aig_bytes).decode(), "input_names": aig.input_names, "output_names": aig.output_names,
              "gate_set": gates, "mbu_op": "(\"mbu\", [q], [correction]) : X-measure q, apply the diagonal correction if outcome 1; q ends in |0>",
              "tracks": tracks, "contract_version": CONTRACT_VERSION}
    canon = {"function": function_canon(aig), "task": task, "tracks": v1_tracks, "gate_set": gates}
    h = content_hash("B", task, canon)
    priv = {**private, "b_min": bmin, "b_min_widths": widths, "size_bin": private.get("size_bin", size_bin(n)),
            "aig_ands": len(aig.ands), "n": n, "m": m}
    tl = [{"name": k, "contract": v["contract"], "metric": v["metric"], "qubit_budget": v["qubit_budget"]} for k, v in tracks.items()]
    return Instance(iid, "B", task, family, source, params, public, priv, [task], tl, h)


def _src(name, ref=""):
    return {"kind": "generator", "name": name, "version": "1", "ref": ref, "license": "qbank"}


# ------------------------------------------------------------------ family generators
def gen_rand3sat(split, bin_, i, n_range=None):
    lo, hi = n_range or {b: (a, c) for b, a, c in SIZE_BINS}[bin_]
    seed = split_seed(split, i)
    rng = rng_for("B.rand3sat", bin_, seed)
    nv = int(rng.integers(lo, hi + 1))
    alpha = [3.8, 4.26, 4.7][i % 3]
    for draw in range(1, 1001):       # unsatisfiable formulas give the constant-0 oracle (trivial): rejected, redrawn
        aig, params, meta = F.gen_3sat(nv, alpha, rng)
        if meta["satisfiable"]:
            break
    params = {**params, "seed": seed, "draws_until_satisfiable": draw}
    return Planned(split, make_instance(f"B.phase.rand3sat.n{nv}.s{seed}", aig, "phase", "rand3sat", params,
                                        _src("random_3sat", "uniform random 3-SAT near/around the threshold alpha=4.26"),
                                        {"satisfiable": meta["satisfiable"], "clauses": meta["clauses"], "size_bin": bin_}))


def gen_triangle(split, bin_, i):
    lo, hi = {b: (a, c) for b, a, c in SIZE_BINS}[bin_]
    seed = split_seed(split, i)
    rng = rng_for("B.triangle", bin_, seed)
    v = int(rng.integers(lo, hi + 1))
    aig, params, meta = F.gen_triangle(v, rng)
    return Planned(split, make_instance(f"B.phase.triangle.v{v}.s{seed}", aig, "phase", "triangle", {**params, "seed": seed},
                                        _src("triangle", "parametrised QCircuitBench grover_triangle"), {**meta, "size_bin": bin_}))


def gen_sudoku(split, bin_, i, size=None):
    lo, hi = {b: (a, c) for b, a, c in SIZE_BINS}[bin_]
    seed = split_seed(split, i)
    rng = rng_for("B.sudoku", bin_, seed)
    size = size or (6 if bin_ == "XL" else (4 if i % 2 == 0 else 6))
    bits = 2 if size == 4 else 3
    k = int(rng.integers(max(1, math.ceil(lo / bits)), hi // bits + 1))
    aig, params, meta = F.gen_sudoku_n(size, k, rng)
    return Planned(split, make_instance(f"B.phase.sudoku{size}.k{k}.s{seed}", aig, "phase", "sudoku", {**params, "seed": seed},
                                        _src("sudoku", "parametrised QCircuitBench grover_sudoku (4x4 and 6x6)"), {**meta, "size_bin": bin_}))


def gen_simon3(split, bin_, i):
    lo, hi = {b: (a, c) for b, a, c in SIZE_BINS}[bin_]
    seed = split_seed(split, i)
    rng = rng_for("B.simon3", bin_, seed)
    t = int(rng.integers(math.ceil(lo / 2), hi // 2 + 1))
    r = int(rng.integers(1, t))
    aig, params, meta = F.gen_simon3(t, r, rng)
    return Planned(split, make_instance(f"B.bitflip.simon3.t{t}.s{seed}", aig, "bitflip", "simon3", {**params, "seed": seed},
                                        _src("simon3", "ternary generalized Simon oracle (QCircuitBench, parametrised)"),
                                        {**meta, "size_bin": bin_}))


def gen_eq_const(split, bin_, i):
    lo, hi = {b: (a, c) for b, a, c in SIZE_BINS}[bin_]
    seed = split_seed(split, i)
    rng = rng_for("B.eq_const", bin_, seed)
    w = int(rng.integers(math.ceil(lo / 2), hi // 2 + 1))
    aig, params, meta = F.gen_compare("eq_const", w, rng)
    return Planned(split, make_instance(f"B.bitflip.compare.eq_const.n{2 * w}.s{seed}", aig, "bitflip", "compare",
                                        {**params, "seed": seed}, _src("compare"), {"size_bin": bin_}))


def gen_param(family, kind_name, arg, split):
    if family == "compare":
        aig, params, _ = F.gen_compare(kind_name, arg)
    else:
        aig, params, _ = F.gen_arith(kind_name, arg)
    n = aig.num_inputs
    return Planned(split, make_instance(f"B.bitflip.{family}.{kind_name}.n{n}", aig, "bitflip", family, params,
                                        _src(family), {"size_bin": size_bin(n)}))


def _tag(p, name, args, i):
    p.regen = (name, args, i)
    return p


EXCLUDED: list[dict] = []


def generate_all(log=print) -> list[Planned]:
    P: list[Planned] = []
    t0 = time.time()
    for fam, fn in (("rand3sat", gen_rand3sat), ("triangle", gen_triangle), ("sudoku", gen_sudoku), ("simon3", gen_simon3)):
        for bi, bin_ in enumerate(("S", "M", "L")):
            for sp, cnt in (("train", 12), ("val", 4), ("test_in", 2)):
                for j in range(cnt):
                    P.append(_tag(fn(sp, bin_, 1000 * bi + j), fn.__name__, (sp, bin_), 1000 * bi + j))
        for j in range(12):
            P.append(_tag(fn("test_in", "XL", 3000 + j), fn.__name__, ("test_in", "XL"), 3000 + j))
        log(f"[B] {fam}: {sum(1 for p in P if p.inst.family == fam)} instances ({time.time() - t0:.0f}s)")
    # compare: deterministic lt/eq by width (small -> train, L -> val, XL -> test_in) + random eq_const seeds
    for kind_name in ("lt", "eq"):
        for w in (3, 4, 5, 6, 7, 8, 9):
            P.append(gen_param("compare", kind_name, w, "train"))
        for w in (10, 11, 12):
            P.append(gen_param("compare", kind_name, w, "val"))
        for w in (20, 26, 32):
            P.append(gen_param("compare", kind_name, w, "test_in"))
    for bi, bin_ in enumerate(("S", "M", "L")):
        for sp, cnt in (("train", 10), ("val", 4), ("test_in", 2)):
            for j in range(cnt):
                P.append(_tag(gen_eq_const(sp, bin_, 1000 * bi + j), "gen_eq_const", (sp, bin_), 1000 * bi + j))
    for j in range(6):
        P.append(_tag(gen_eq_const("test_in", "XL", 3000 + j), "gen_eq_const", ("test_in", "XL"), 3000 + j))
    log(f"[B] compare done ({time.time() - t0:.0f}s)")
    # arith: deterministic, by parameter
    for kind_name, train, val, test in (("carry", (3, 4, 5, 6, 7, 8), (9, 10, 11, 12), (20, 26, 32)),
                                        ("prod_parity", (3, 4, 5, 6, 7), (8, 9), (10,)),     # w >= 11: SAT miter > 600 s
                                        ("majority", (7, 9, 11, 13, 15, 17), (19, 21, 23), (41, 51, 63))):
        for sp, args in (("train", train), ("val", val), ("test_in", test)):
            for a in args:
                try:
                    P.append(gen_param("arith", kind_name, a, sp))
                except RuntimeError as e:        # no constructive baseline could be verified exactly: excluded, logged
                    EXCLUDED.append({"family": "arith", "kind": kind_name, "w": a, "split": sp, "reason": str(e)})
                    log(f"[B] arith {kind_name} w={a} excluded: {e}")
    log(f"[B] arith done ({time.time() - t0:.0f}s)")
    return P


def regenerate(p: Planned, attempt: int) -> Planned:
    name, args, i = p.regen
    return _tag(globals()[name](*args, i + 100 * attempt), name, args, i + 100 * attempt)
