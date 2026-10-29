"""Generate all category-A instances with their split assignment.

Deterministic: every random choice comes from seeds.rng_for(family, params, seed) with seeds drawn from the
split's disjoint seed range. Running generate_all() twice yields byte-identical records.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...core import gf2
from ...core.seeds import rng_for, split_seed
from . import codes as C
from .instances import css_instance, stab_instance

# held-out (O) families and sporadic codes: never produced for train/val
O_FAMILIES = {"hgp_rand", "many_hypercube", "shor_concat", "iceberg", "unrot_surface", "toric", "sporadic", "composite"}
T_FAMILIES = {"rand_stab", "bb_rand", "gb_rand", "css_rand", "rot_surface", "color_666", "color_488", "qhamming",
              "qrm", "bb_published", "bb_mqt_n90_d2"}
# (l, m) of every published BB code (Bravyi et al. Table 3, and the l=15,m=3 code shipped by MQT): excluded from bb_rand
PUBLISHED_BB_LM = {(6, 6), (15, 3), (9, 6), (12, 6), (12, 12), (30, 6), (21, 18)}
BRAVYI = {  # arXiv:2308.07915v2 Table 3: (l, m, A terms, B terms, k)
    72: (6, 6, [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)], 12),
    90: (15, 3, [(9, 0), (0, 1), (0, 2)], [(0, 0), (2, 0), (7, 0)], 8),
    108: (9, 6, [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)], 8),
    144: (12, 6, [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)], 12),
    288: (12, 12, [(3, 0), (0, 2), (0, 7)], [(0, 3), (1, 0), (2, 0)], 12),
    360: (30, 6, [(9, 0), (0, 1), (0, 2)], [(0, 3), (25, 0), (26, 0)], 12),
    756: (21, 18, [(3, 0), (0, 10), (0, 17)], [(0, 5), (3, 0), (19, 0)], 16),
}
CODE_BINS = [("S", 20, 60), ("M", 61, 120), ("L", 121, 200), ("XL", 201, 400)]


def code_bin(n: int) -> str:
    for name, lo, hi in CODE_BINS:
        if lo <= n <= hi:
            return name
    return "XS" if n < 20 else "XXL"


def stab_bin(n: int) -> str:
    return "S" if n <= 8 else "M" if n <= 16 else "L" if n <= 32 else "XL"


@dataclass
class Planned:
    split: str
    inst: object          # Instance
    regen: tuple | None = None   # (generator name, args before the seed index, seed index) for random families


def _priv(code, extra: dict | None = None, size_bin: str | None = None) -> dict:
    v = C.verify_code(code)
    p = {"code": {"n": code.n, "k": v["k"], "verification": v}, "size_features": {"n": code.n, "k": v["k"]},
         "composite": False, "no_room": False, "aliases": [], "size_bin": size_bin or code_bin(code.n),
         "notes": list(code.notes)}
    if code.reported:
        p["reported"] = code.reported
    if extra:
        p.update(extra)
    return p


def _css(iid, code, family, params, split, source=None, extra=None, size_bin=None) -> Planned:
    return Planned(split, css_instance(iid, code, family, params, source or code.source, _priv(code, extra, size_bin)))


def _noncss(iid, code, family, params, split, extra=None) -> Planned:
    code = C.with_logical_z(code)
    zero = C.zero_state_rows(code)
    stabs = C.code_stabilizer_rows(code)
    priv = _priv(code, extra, code_bin(code.n))
    priv["logical_z"] = code.logical_z.to_strings()
    return Planned(split, stab_instance(iid, zero, family, params, code.source, priv, code_stabs=stabs, graphs=False))


# ------------------------------------------------------------------ random T families
def gen_rand_stab(split: str, n: int, i: int) -> Planned:
    seed = split_seed(split, i)
    qseed = int(rng_for("rand_stab", n, seed).integers(0, 2**31 - 1))
    stabs = C.random_stabilizer_state(n, qseed)
    src = {"kind": "generator", "name": "random_stabilizer_state", "version": "1",
           "ref": "qiskit.quantum_info.random_clifford(n, seed) applied to |0^n>", "license": "qbank"}
    priv = {"size_features": {"n": n}, "composite": False, "no_room": False, "aliases": [], "size_bin": stab_bin(n),
            "qiskit_seed": qseed}
    return Planned(split, stab_instance(f"A.stab.rand_stab.n{n}.s{seed}", stabs, "rand_stab", {"n": n, "seed": seed},
                                        src, priv))


def _pick_n(rng, lo, hi, even=True):
    n = int(rng.integers(lo, hi + 1))
    return n + (n % 2) if even and n % 2 else n


def gen_bb_rand(split: str, bin_: str, i: int) -> Planned:
    lo, hi = {b: (a, c) for b, a, c in CODE_BINS}[bin_]
    seed = split_seed(split, i)
    rng = rng_for("bb_rand", bin_, seed)
    for attempt in range(20000):
        l, m = int(rng.integers(2, 21)), int(rng.integers(2, 21))
        if not (lo <= 2 * l * m <= hi) or (l, m) in PUBLISHED_BB_LM or (m, l) in PUBLISHED_BB_LM:
            continue
        a = [(int(rng.integers(l)), 0)] + [(0, int(b)) for b in rng.choice(m, 2, replace=False)]
        b = [(0, int(rng.integers(m)))] + [(int(x), 0) for x in rng.choice(l, 2, replace=False)]
        code = C.bivariate_bicycle(l, m, a, b)
        if code.k() >= 2:
            params = {**code.params, "seed": seed, "attempt": attempt}
            return _css(f"A.css_zero.bb_rand.n{code.n}.s{seed}", code, "bb_rand", params, split,
                        source={**code.source, "name": "bb_poly_random"})
    raise RuntimeError("bb_rand: no code with k>=2 found")


def gen_gb_rand(split: str, bin_: str, i: int) -> Planned:
    lo, hi = {b: (a, c) for b, a, c in CODE_BINS}[bin_]
    seed = split_seed(split, i)
    rng = rng_for("gb_rand", bin_, seed)
    for attempt in range(50000):
        l = int(rng.integers(max(3, lo // 2), hi // 2 + 1))
        w = int(rng.integers(3, 5))
        a = sorted(int(x) for x in rng.choice(l, w, replace=False))
        b = sorted(int(x) for x in rng.choice(l, w, replace=False))
        code = C.generalized_bicycle(l, a, b)
        if code.k() >= 2:
            params = {**code.params, "seed": seed, "attempt": attempt}
            return _css(f"A.css_zero.gb_rand.n{code.n}.s{seed}", code, "gb_rand", params, split,
                        source={**code.source, "name": "gb_poly_random"})
    raise RuntimeError("gb_rand: no code with k>=2 found")


def gen_css_rand(split: str, bin_: str, i: int, n_range=None) -> Planned:
    lo, hi = n_range or {b: (a, c) for b, a, c in CODE_BINS}[bin_]
    seed = split_seed(split, i)
    rng = rng_for("css_rand", bin_, seed)
    n = int(rng.integers(lo, hi + 1))
    k = int(rng.integers(1, max(2, n // 8) + 1))
    rx = int(rng.integers((n - k) // 3, 2 * (n - k) // 3 + 1))
    rz = n - k - rx
    code = C.random_css(n, rx, rz, rng)
    params = {"n": n, "rx": rx, "rz": rz, "k": k, "seed": seed}
    return _css(f"A.css_zero.css_rand.n{n}.s{seed}", code, "css_rand", params, split,
                size_bin=bin_ if n_range is None else "probe")


# ------------------------------------------------------------------ O families (test_ood only)
HGP_SHAPES = {  # bin -> list of (n_c, dv, dc) giving n = n_c^2 + m_c^2
    "S": [(6, 2, 3), (8, 3, 6), (8, 2, 4)],
    "M": [(8, 3, 4), (9, 2, 3), (10, 3, 6), (12, 3, 6)],
    "L": [(12, 2, 3), (12, 3, 4), (14, 3, 6), (16, 3, 6), (16, 3, 4)],
}


def gen_hgp_rand(bin_: str, i: int) -> Planned:
    seed = split_seed("test_ood", i)
    shapes = HGP_SHAPES[bin_]
    nc, dv, dc = shapes[i % len(shapes)]
    rng = rng_for("hgp_rand", bin_, seed)
    for attempt in range(1000):
        h1 = C.random_biregular_ldpc(nc, dv, dc, rng)
        h2 = C.random_biregular_ldpc(nc, dv, dc, rng)
        code = C.hypergraph_product(h1, h2, f"hgp_rand_{nc}", "hgp_rand",
                                    {"n_c": nc, "dv": dv, "dc": dc, "seed": seed, "attempt": attempt},
                                    {"kind": "generator", "name": "hgp_random_ldpc", "version": "1",
                                     "ref": "Tillich & Zemor 2009 (hypergraph product)", "license": "qbank"})
        if code.k() >= 1:
            return _css(f"A.css_zero.hgp_rand.n{code.n}.s{seed}", code, "hgp_rand", code.params, "test_ood")
    raise RuntimeError("hgp_rand failed")


def _tag(p: Planned, fn_name: str, args: tuple, index: int) -> Planned:
    p.regen = (fn_name, args, index)
    return p


def regenerate(p: Planned, attempt: int) -> Planned:
    """Same family/bin/split, fresh seed index (index + 100*attempt, attempt <= 9: stays inside the split's seed range)."""
    fn_name, args, index = p.regen
    new_index = index + 100 * attempt
    return _tag(globals()[fn_name](*args, new_index), fn_name, args, new_index)


def generate_all(include_756: bool = True) -> list[Planned]:
    P: list[Planned] = []
    # ---- rand_stab (stabilizer_state)
    for n in (4, 6, 8, 12, 16, 24, 32):
        for j in range(12):
            P.append(gen_rand_stab("train", n, n * 100 + j))
        for j in range(4):
            P.append(gen_rand_stab("val", n, n * 100 + j))
        for j in range(2):
            P.append(gen_rand_stab("test_in", n, n * 100 + j))
    for n in (48, 64):
        for j in range(10):
            P.append(gen_rand_stab("test_in", n, n * 100 + j))
    # ---- random CSS families
    for fam, fn in (("bb_rand", gen_bb_rand), ("gb_rand", gen_gb_rand), ("css_rand", gen_css_rand)):
        for bi, bin_ in enumerate(("S", "M", "L")):
            for sp, cnt in (("train", 12), ("val", 4), ("test_in", 2)):
                for j in range(cnt):
                    P.append(_tag(fn(sp, bin_, 1000 * bi + j), fn.__name__, (sp, bin_), 1000 * bi + j))
        for j in range(12):
            P.append(_tag(fn("test_in", "XL", 3000 + j), fn.__name__, ("test_in", "XL"), 3000 + j))
    # ---- parametric T families (smaller parameters -> train/val, largest one or two -> test_in)
    for d, sp in ((3, "train"), (4, "train"), (5, "train"), (6, "train"), (7, "train"), (8, "val"),
                  (9, "test_in"), (10, "test_in"), (11, "test_in")):
        c = C.rotated_surface(d)
        P.append(_css(f"A.css_zero.rot_surface.d{d}", c, "rot_surface", {"d": d}, sp))
    for d, sp in ((3, "train"), (5, "train"), (7, "val"), (9, "test_in")):
        c = C.color_code("666", d)
        extra = {"aliases": ["steane_[[7,1,3]]", "color_488_d3", "qhamming_r3", "qrm_m3"]} if d == 3 else None
        P.append(_css(f"A.css_zero.color_666.d{d}", c, "color_666", {"d": d}, sp, extra=extra))
    for d, sp in ((5, "train"), (7, "val"), (9, "test_in")):
        c = C.color_code("488", d)
        P.append(_css(f"A.css_zero.color_488.d{d}", c, "color_488", {"d": d}, sp))
    for r, sp in ((4, "train"), (5, "val"), (6, "test_in"), (7, "test_in")):
        c = C.quantum_hamming(r)
        P.append(_css(f"A.css_zero.qhamming.r{r}", c, "qhamming", {"r": r}, sp))
    for m, sp in ((4, "train"), (5, "train"), (6, "val"), (7, "test_in"), (8, "test_in")):
        c = C.quantum_reed_muller(m)
        P.append(_css(f"A.css_zero.qrm.m{m}", c, "qrm", {"m": m}, sp))
    # ---- published codes of a T family -> test_in
    for n, (l, m, a, b, k) in BRAVYI.items():
        if n == 756 and not include_756:
            continue
        c = C.bivariate_bicycle(l, m, a, b, f"bb_bravyi_{n}")
        c.reported = {"d": {72: 6, 90: 10, 108: 10, 144: 12, 288: 18, 360: "<=24", 756: "<=34"}[n],
                      "source": "Bravyi et al., arXiv:2308.07915v2 Table 3"}
        extra = {"published": True, "note": "extrapolation beyond the generator range (n > 400)"} if n == 756 else {"published": True}
        P.append(_css(f"A.css_zero.bb_published.bravyi{n}", c, "bb_published", c.params, "test_in",
                      source={**c.source, "kind": "literature"}, extra=extra))
    # MQT QECC 2.0.0 construct_bb_code(90) passes l and m the wrong way round (_cyclic_code_check_matrix(m, l, ...)
    # with l = 15, m = 3) and so builds a different code with k = 8 but distance <= 2; it is NOT Bravyi's [[90,8,10]]
    # (which is bravyi90 above). v1.1 (A): own family bb_mqt_n90_d2 instead of bb_published.
    from mqt.qecc.codes import construct_bb_code
    mq = construct_bb_code(90)
    c = C.CodeSpec("bb_mqt_90", "bb_mqt_n90_d2", {"l": 15, "m": 3, "constructor": "mqt.qecc construct_bb_code(90)"}, 90, True,
                   gf2.as_gf2(mq.Hx), gf2.as_gf2(mq.Hz),
                   source={"kind": "external", "name": "mqt.qecc.codes.construct_bb_code(90)", "version": "mqt.qecc 2.0.0",
                           "ref": "labelled [[90,8,10]] by MQT/StabilizerBench/QECirc; actually has a weight-2 logical",
                           "license": "MIT"})
    c.notes.append("labelled [[90,8,10]] in mqt.qecc, StabilizerBench and QECirc (90-8-10) but has distance 2 "
                   "(weight-2 Z logical on qubits 45,60); not Bravyi's code")
    P.append(_css("A.css_zero.bb_mqt_n90_d2.mqt90", c, "bb_mqt_n90_d2", c.params, "test_in", extra={"published": True}))
    # ---- O families -> test_ood
    for bi, bin_ in enumerate(("S", "M", "L")):
        for j in range(12):
            P.append(_tag(gen_hgp_rand(bin_, 1000 * bi + j), "gen_hgp_rand", (bin_,), 1000 * bi + j))
    for L in (2, 3):
        c = C.many_hypercube(L)
        P.append(_css(f"A.css_zero.many_hypercube.L{L}", c, "many_hypercube", {"L": L}, "test_ood"))
    for a in (3, 5, 7, 9, 11):
        for b in (3, 5, 7, 9, 11):
            if a <= b:
                c = C.shor_type(a, b)
                P.append(_css(f"A.css_zero.shor_concat.{a}x{b}", c, "shor_concat", {"a": a, "b": b}, "test_ood",
                              extra={"aliases": ["shor_[[9,1,3]]"]} if a == b == 3 else None))
    for m in (8, 16, 32, 64):
        c = C.iceberg(m)
        P.append(_css(f"A.css_zero.iceberg.m{m}", c, "iceberg", {"m": m}, "test_ood",
                      extra={"known_optimal": {"value": 2 * m - 1, "kind": "lower_bound_attained",
                                               "reason": "|0..0>_L is the 2m-qubit GHZ state; any n-qubit connected "
                                                         "entangled state needs >= n-1 two-qubit gates, and n-1 CNOTs suffice"}}))
    for d in (3, 5, 7, 9, 11):
        c = C.unrotated_surface(d)
        P.append(_css(f"A.css_zero.unrot_surface.d{d}", c, "unrot_surface", {"d": d}, "test_ood"))
    for d in (3, 4, 5, 6):
        c = C.toric(d)
        P.append(_css(f"A.css_zero.toric.d{d}", c, "toric", {"d": d}, "test_ood"))
    # sporadic codes (MQT library + definitions)
    for nm in ("golay", "carbon"):
        c = C.mqt_named(nm)
        P.append(_css(f"A.css_zero.sporadic.{nm}", c, "sporadic", {"code": nm}, "test_ood"))
    for fname in ("30_6_5.txt",):
        c = C.mqt_misc(fname)
        P.append(_css(f"A.css_zero.sporadic.mqt_{fname[:-4]}", c, "sporadic", c.params, "test_ood"))
    for fname in ("8_3_3.txt", "15_3_5.txt"):
        c = C.mqt_misc(fname)
        P.append(_noncss(f"A.stab.sporadic.mqt_{fname[:-4]}", c, "sporadic", c.params, "test_ood"))
    P.append(_noncss("A.stab.sporadic.five_qubit", C.five_qubit(), "sporadic", {"code": "five_qubit"}, "test_ood"))
    # composites (StabilizerBench construction rule), only components outside the training families T
    P.extend(gen_composites())
    # ---- probe (known optimum or bound)
    for n in (6, 7, 8, 9):
        for j in range(5):
            P.append(gen_css_rand("probe", "probe", n * 100 + j, n_range=(n, n)))
    for j in range(10):
        P.append(gen_rand_stab("probe", 3, 300 + j))
    for m in (2, 4, 5, 6):
        c = C.iceberg(m)
        P.append(_css(f"A.css_zero.iceberg.m{m}", c, "iceberg", {"m": m}, "probe",
                      extra={"known_optimal": {"value": 2 * m - 1, "kind": "lower_bound_attained",
                                               "reason": "GHZ on n qubits: >= n-1 two-qubit gates, attained by a CNOT chain"}}))
    return P


def gen_composites() -> list[Planned]:
    """Concatenations outer∘inner (inner k=1), as in StabilizerBench, restricted to non-T components and n < 200."""
    outer = {"five_qubit": C.five_qubit(), "shor": C.shor_type(3, 3), "golay": C.mqt_named("golay"),
             "iceberg_m2": C.iceberg(2), "iceberg_m3": C.iceberg(3), "iceberg_m4": C.iceberg(4),
             "many_hypercube_L2": C.many_hypercube(2), "carbon": C.mqt_named("carbon")}
    inner = {"five_qubit": outer["five_qubit"], "shor": outer["shor"], "golay": outer["golay"]}
    out = []
    for on, oc in outer.items():
        for inn, ic in inner.items():
            if oc.n * ic.n >= 200:
                continue
            c = C.concatenate(C.with_logical_z(oc) if not oc.css else oc, ic, f"{on}∘{inn}")
            extra = {"composite": True, "components": [on, inn]}
            iid = f"A.{'css_zero' if c.css else 'stab'}.composite.{on}_o_{inn}"
            if c.css:
                out.append(_css(iid, c, "composite", c.params, "test_ood", extra=extra))
            else:
                out.append(_noncss(iid, c, "composite", c.params, "test_ood", extra=extra))
    return out
