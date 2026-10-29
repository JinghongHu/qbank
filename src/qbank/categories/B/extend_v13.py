"""Category B data version 1.3.0 (10-28): parametrised structural sub-types for the task packs' v2 splits.

Four single-output bit-flip sub-types whose free parameter gives many functions per input width (functions.py):
  compare.lt_const   [a < c]            c odd, 2^(n/2) <= c < 2^(n-1)  ([a < c] ~ [a < 2^n - c] under NPN)
  compare.interval   [c1 <= a < c2]     1 <= c1 < c2 <= 2^n - 1, 2^(n/2) <= c2 - c1 <= 2^n - 2^(n/2), c1 or c2 odd
  arith.threshold    [popcount >= k]    2 <= k <= n/2 (k ~ n + 1 - k; odd n, k = (n+1)/2 is "majority")
  arith.mul_bit      bit j of a * b     w-bit operands, n = 2w, w - 1 <= j <= 2w - 1
Every accepted function (stricter than qbank's solution-sparse rule, AB_design.md 2.2):
  * min(n_solutions, 2^n - n_solutions) >= 2^(n/2)  (f and NOT f are both not solution-sparse);
  * every input matters (flipping it changes f on some input);
  * its NPN signature (output-complement-symmetric weight, |Walsh spectrum| multiset, one-input cofactor weights;
    invariant under input negation / permutation and output negation) differs from that of every existing B
    instance (all five splits, either oracle kind, n <= 22) and of every other new function: two functions with
    different signatures are never NPN-equivalent, so no new function duplicates another task.
Slots (sub-type, task-pack split, n): the pack's test instances go to qbank val, the pack's train / val instances to
qbank train (the pack convention: pack test = qbank val, pack train + val = qbank train); qbank's test_in / test_ood /
probe are never touched. Parameters come from rng_for("B.v13", sub-type, n, seed) with seed = split_seed(split, 5000 +
100 * sub-type index + slot), redrawn (up to 500 times) until accepted. Deterministic given the existing instances.
"""
from __future__ import annotations

import base64
import collections
import hashlib
import json
import math

import numpy as np

from ...core.aig import AIG
from ...core.seeds import rng_for, split_seed
from . import functions as F
from .generate import Planned, _src, make_instance, size_bin

VERSION = "1.3.0"
RULES_NOTE = ("B 1.3.0 (10-28): 63 parametrised structural instances (compare.lt_const, compare.interval, "
              "arith.threshold, arith.mul_bit; 8-21 inputs) added to train (pack train / val) and val (pack test); "
              "existing entries unchanged (core/extend.py)")
SUBTYPES = ("lt_const", "interval", "threshold", "mul_bit")
FAMILY = {"lt_const": "compare", "interval": "compare", "threshold": "arith", "mul_bit": "arith"}
# (task-pack split, n) slots per sub-type (AB_design.md 2.4): training at both ends of the size range, test inside
SLOTS = {
    "lt_const": [("train", n) for n in (8, 8, 20, 20)] + [("val", n) for n in (9, 10, 11, 12, 13, 15, 17, 18, 19)]
                + [("test", n) for n in (11, 13, 15, 17)],
    "interval": [("train", n) for n in (8, 8, 20, 20)] + [("val", n) for n in (9, 10, 12, 13, 15, 16, 18, 19)]
                + [("test", n) for n in (11, 14, 17)],
    "threshold": [("train", n) for n in (8, 9, 20, 21)] + [("val", n) for n in (10, 11, 12, 13, 15, 16, 17, 19)]
                 + [("test", n) for n in (12, 14, 16, 18)],
    "mul_bit": [("train", n) for n in (8, 8, 20)] + [("val", n) for n in (10, 10, 12, 14, 14, 16, 16, 18, 18)]
               + [("test", n) for n in (12, 14, 16)],
}
QBANK_SPLIT = {"train": "train", "val": "train", "test": "val"}
MAX_DRAWS = 500
STRICT_RULE = "min(n_solutions, 2^n - n_solutions) >= 2^(n/2) and every input matters"


# ------------------------------------------------------------------ NPN signature (same quantity as qbank_split_v2.sig_B)
def _fwht(v):
    v = v.astype(np.int64).copy()
    h, n = 1, len(v)
    while h < n:
        v = v.reshape(-1, 2, h)
        a, b = v[:, 0, :].copy(), v[:, 1, :].copy()
        v[:, 0, :], v[:, 1, :] = a + b, a - b
        v = v.reshape(n)
        h *= 2
    return v


def npn_signature(tt: np.ndarray, n: int) -> str:
    """tt: (m, 2^n) 0/1 truth tables. Invariant under input negation / permutation, output negation and order."""
    N = 1 << n
    idx = np.arange(N)
    per = []
    for f in tt.astype(np.int64):
        w = int(f.sum())
        spec = collections.Counter(np.abs(_fwht(1 - 2 * f)).tolist())
        cof = []
        for i in range(n):
            bit = (idx >> i) & 1
            a, b = int(f[bit == 0].sum()), int(f[bit == 1].sum())
            cof.append(tuple(sorted((min(a, N // 2 - a), min(b, N // 2 - b)))))
        per.append((min(w, N - w), tuple(sorted(spec.items())), tuple(sorted(cof))))
    return hashlib.sha1(json.dumps([n, len(tt), sorted(per)]).encode()).hexdigest()


def strict_structural(tt1: np.ndarray, n: int) -> tuple[bool, int]:
    c = int(tt1.sum())
    m = min(c, (1 << n) - c)
    return m * m >= (1 << n), c                     # min(...) >= 2^(n/2), exact


def all_inputs_matter(tt1: np.ndarray, n: int) -> bool:
    x = np.arange(1 << n)
    return all(bool((tt1[x ^ (1 << i)] != tt1).any()) for i in range(n))


def existing_signatures(instances) -> dict:
    """{signature: instance id} of every existing B instance with <= 22 inputs."""
    out = {}
    for inst in instances:
        pub = inst.public
        aig = AIG.from_aiger(base64.b64decode(pub["aiger_b64"]))
        if aig.num_inputs > 22:
            continue
        out.setdefault(npn_signature(aig.truth_tables(), aig.num_inputs), inst.id)
    return out


# ------------------------------------------------------------------ parameter draws
def _draw(sub, n, rng, used):
    """-> (aig, params, id suffix) or None for a draw that does not fit the sub-type's parameter rule."""
    if sub == "lt_const":
        lo, hi = math.ceil(2 ** (n / 2)), 2 ** (n - 1) - 1
        c = int(rng.integers(lo, hi + 1)) | 1
        if c > hi:
            return None
        aig, params, _ = F.gen_lt_const(n, c)
        return aig, params, None
    if sub == "interval":
        N = 1 << n
        c1 = int(rng.integers(1, N - 1))
        c2 = int(rng.integers(c1 + 1, N))
        L = c2 - c1
        if L * L < N or (N - L) ** 2 < N or not (c1 & 1 or c2 & 1):
            return None
        aig, params, _ = F.gen_interval(n, c1, c2)
        return aig, params, None
    if sub == "threshold":
        ks = [k for k in range(2, n // 2 + 1) if (n, k) not in used]
        if not ks:
            return None
        k = int(ks[int(rng.integers(len(ks)))])
        aig, params, _ = F.gen_threshold(n, k)
        return aig, params, f"k{k}"
    if sub == "mul_bit":
        w = n // 2
        js = [j for j in range(w - 1, 2 * w) if (n, j) not in used]
        if not js:
            return None
        j = int(js[int(rng.integers(len(js)))])
        aig, params, _ = F.gen_mul_bit(w, j)
        return aig, params, f"j{j}"
    raise ValueError(sub)


def extension(existing, log=print) -> tuple[list[Planned], dict]:
    """New planned instances of B 1.3.0 given the existing instances (Instance objects, all splits)."""
    sigs = existing_signatures(existing)
    ids = {i.id for i in existing}
    planned, report = [], {"version": VERSION, "rule": STRICT_RULE, "instances": []}
    for si, sub in enumerate(SUBTYPES):
        used = set()
        for slot, (pack_split, n) in enumerate(SLOTS[sub]):
            qsplit = QBANK_SPLIT[pack_split]
            seed = split_seed(qsplit, 5000 + 100 * si + slot)
            rng = rng_for("B.v13", sub, n, seed)
            rejected = collections.Counter()
            for draw in range(1, MAX_DRAWS + 1):
                d = _draw(sub, n, rng, used)
                if d is None:
                    rejected["parameter rule"] += 1
                    continue
                aig, params, suffix = d
                tt = aig.truth_tables()
                ok, cnt = strict_structural(tt[0], n)
                if not ok:
                    rejected["strict structural rule"] += 1
                    continue
                if not all_inputs_matter(tt[0], n):
                    rejected["an input does not matter"] += 1
                    continue
                sig = npn_signature(tt, n)
                if sig in sigs:
                    rejected["NPN signature of " + sigs[sig].split(".s")[0]] += 1
                    continue
                break
            else:
                raise RuntimeError(f"B 1.3.0: no acceptable {sub} function with n={n} in {MAX_DRAWS} draws")
            fam = FAMILY[sub]
            iid = f"B.bitflip.{fam}.{sub}.n{n}." + (suffix or f"s{seed}")
            assert iid not in ids, iid
            ids.add(iid)
            used.add((n, params.get("k", params.get("j"))))
            params = {**params, "seed": seed, "draws": draw}
            priv = {"size_bin": size_bin(n), "added_in": VERSION, "subtype": sub, "pack_v2_split": pack_split,
                    "n_solutions": cnt, "n_solutions_method": "exhaustive",
                    "solution_fraction_log2": round(math.log2(cnt) - n, 4), "solution_sparse": False,
                    "strict_structural": {"rule": STRICT_RULE, "passed": True,
                                          "min_count": min(cnt, (1 << n) - cnt), "threshold_2^(n/2)": round(2 ** (n / 2), 3)},
                    "npn_signature": sig, "rejected_draws": dict(rejected)}
            inst = make_instance(iid, aig, "bitflip", fam, params,
                                 _src(f"{fam}.{sub}", "qbank B 1.3.0 parametrised structural sub-type (10-28)"), priv)
            sigs[sig] = iid
            planned.append(Planned(qsplit, inst))
            report["instances"].append({"id": iid, "qbank_split": qsplit, "pack_v2_split": pack_split, "n": n,
                                        "params": params, "n_solutions": cnt, "b_min": inst.private["b_min"],
                                        "rejected_draws": dict(rejected)})
            log(f"[B 1.3.0] {iid} -> qbank {qsplit} (pack {pack_split}); solutions {cnt}; draws {draw}")
    return planned, report
