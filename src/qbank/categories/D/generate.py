"""Category D: exact (and separately approximate) preparation of non-Clifford states.

Public part: n and the target amplitudes [[basis index (decimal string, little-endian), re, im], ...] (normalised), the
gate set and the tracks. No family names, no construction hints. Tracks:
  cx            state_exact (fidelity >= 1 - 1e-9), metric cx_count (cx = cz = 1; single-qubit gates free), all-to-all
  depth2q@line  state_exact on a line (two-qubit gates only on (q, q+1)), metric two_qubit_depth; the answer may give
                an output map (state qubit q held by physical qubit output_map[q]), as the input is |0...0>
  cx@F0.99  state_approx (fidelity >= 0.99),       metric cx_count     (dense and sparse families only)
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from ...contracts.state import GATE_SET_D
from ...core.canon import content_hash
from ...core.instance import Instance
from ...core.seeds import rng_for, split_seed

APPROX_F = 0.99


def size_bin(n: int) -> str:
    return "S" if n <= 8 else "M" if n <= 20 else "L" if n <= 40 else "XL"


def amplitudes_to_public(amp: dict) -> list:
    """amp: {index: complex}. Global phase fixed (first nonzero amplitude real positive), normalised, sorted by index."""
    items = sorted((k, complex(v)) for k, v in amp.items() if abs(v) > 1e-15)
    nrm = math.sqrt(sum(abs(v) ** 2 for _, v in items))
    ph = items[0][1] / abs(items[0][1])
    out = []
    for k, v in items:
        w = v / ph / nrm
        out.append([str(k), float(w.real), float(w.imag)])
    return out


def canon_amplitudes(pub_amp: list) -> list:
    """Amplitudes rounded to 12 decimals, as strings (hashed content carries no binary floats)."""
    def f(x):
        s = f"{round(x, 12) + 0.0:.12f}"
        return "0.000000000000" if s == "-0.000000000000" else s
    return [[k, f(re), f(im)] for k, re, im in pub_amp]


def canon_tracks(tracks: dict) -> dict:
    return {t: {k: (repr(v) if isinstance(v, float) else v) for k, v in spec.items()} for t, spec in tracks.items()}


def make_instance(iid, n, amp: dict, family, params, source, private, approx: bool) -> Instance:
    tracks = {"cx": {"contract": "state_exact", "metric": "cx_count", "tolerance": 1e-9},
              "depth2q@line": {"contract": "state_exact", "metric": "two_qubit_depth", "tolerance": 1e-9,
                               "coupling_edges": [[q, q + 1] for q in range(n - 1)], "output_map_allowed": True}}
    if approx:
        tracks["cx@F0.99"] = {"contract": "state_approx", "metric": "cx_count", "min_fidelity": APPROX_F}
    pa = amplitudes_to_public(amp)
    public = {"format": "qbank.public/1", "task": "state_prep", "n": n, "amplitudes": pa, "n_nonzero": len(pa),
              "gate_set": [g for g in GATE_SET_D if g != "id"], "tracks": tracks,
              "output": "circuit on exactly n qubits starting from |0...0>; qubit q is bit q of the basis index (little-endian); "
                        "global phase is irrelevant"}
    canon = {"n": n, "amplitudes": canon_amplitudes(pa), "tracks": canon_tracks(tracks)}
    h = content_hash("D", "state_prep", canon)
    priv = {**private, "size_bin": private.get("size_bin", size_bin(n))}
    tl = [{"name": k, **v} for k, v in tracks.items()]
    return Instance(iid, "D", "state_prep", family, source, params, public, priv, sorted({v["contract"] for v in tracks.values()}), tl, h)


def _src(name):
    return {"kind": "generator", "name": name, "version": "1", "ref": "", "license": "qbank"}


class Planned:
    def __init__(self, split, inst, regen=None):
        self.split, self.inst, self.regen = split, inst, regen


# ------------------------------------------------------------------ states
def dicke(n: int, k: int) -> dict:
    a = 1 / math.sqrt(math.comb(n, k))
    return {sum(1 << q for q in S): a for S in itertools.combinations(range(n), k)}


def random_amplitudes(m: int, rng) -> np.ndarray:
    v = rng.normal(size=m) + 1j * rng.normal(size=m)
    return v / np.linalg.norm(v)


def gen_dicke(n: int, k: int, split: str):
    inst = make_instance(f"D.dicke.n{n}.k{k}", n, dicke(n, k), "dicke", {"n": n, "k": k}, _src("dicke"),
                         {"size_bin": size_bin(n), "nonzeros": math.comb(n, k)}, approx=False)
    return Planned(split, inst)


def gen_w(n: int, split: str):
    inst = make_instance(f"D.w.n{n}", n, dicke(n, 1), "w", {"n": n}, _src("w"), {"size_bin": size_bin(n), "nonzeros": n}, approx=False)
    return Planned(split, inst)


def gen_dense(split: str, n: int, i: int):
    seed = split_seed(split, i)
    rng = rng_for("D.dense", n, seed)
    v = random_amplitudes(1 << n, rng)
    inst = make_instance(f"D.dense.n{n}.s{seed}", n, dict(enumerate(v)), "dense", {"n": n, "seed": seed}, _src("dense (Haar via complex Gaussian)"),
                         {"size_bin": size_bin(n)}, approx=True)
    return Planned(split, inst, ("gen_dense", (split, n), i))


SPARSE_BINS = {"S": (8, 14), "M": (15, 22), "L": (23, 30), "XL": (31, 40)}


def gen_sparse(split: str, bin_: str, i: int):
    seed = split_seed(split, i)
    rng = rng_for("D.sparse", bin_, seed)
    lo, hi = SPARSE_BINS[bin_]
    n = int(rng.integers(lo, hi + 1))
    mmax = 128 if bin_ == "XL" else 64
    m = int(round(math.exp(rng.uniform(math.log(2), math.log(mmax)))))
    support = set()
    while len(support) < m:
        support.add(int(rng.integers(0, 1 << n)))
    v = random_amplitudes(m, rng)
    amp = dict(zip(sorted(support), v))
    inst = make_instance(f"D.sparse.n{n}.m{m}.s{seed}", n, amp, "sparse", {"n": n, "nonzeros": m, "seed": seed},
                         _src("sparse (uniform random support, complex Gaussian amplitudes)"), {"size_bin": bin_}, approx=True)
    return Planned(split, inst, ("gen_sparse", (split, bin_), i))


def _codewords(G: np.ndarray) -> list[int]:
    k, n = G.shape
    out = []
    for x in range(1 << k):
        bits = np.array([(x >> i) & 1 for i in range(k)], dtype=np.uint8)
        w = bits @ G % 2
        out.append(int(sum(int(b) << q for q, b in enumerate(w))))
    return sorted(set(out))


def simplex_code(m: int) -> np.ndarray:
    cols = [[(c >> i) & 1 for i in range(m)] for c in range(1, 1 << m)]
    return np.array(cols, dtype=np.uint8).T


def rm1_code(m: int) -> np.ndarray:
    pts = [[(c >> i) & 1 for i in range(m)] for c in range(1 << m)]
    return np.array([[1] * (1 << m)] + [[p[i] for p in pts] for i in range(m)], dtype=np.uint8)


def hamming_code(r: int) -> np.ndarray:
    """Generator of the [2^r - 1, 2^r - 1 - r] Hamming code (nullspace of the simplex generator)."""
    from ...core.gf2 import nullspace
    return np.array(nullspace(simplex_code(r)), dtype=np.uint8)


def structured_supports() -> list[tuple[str, int, list[int]]]:
    out = [("simplex_m4", 15, _codewords(simplex_code(4))), ("simplex_m5", 31, _codewords(simplex_code(5))),
           ("rm1_m3", 8, _codewords(rm1_code(3))), ("rm1_m4", 16, _codewords(rm1_code(4))), ("rm1_m5", 32, _codewords(rm1_code(5))),
           ("hamming_r3", 7, _codewords(hamming_code(3)))]
    return out


def gen_structured(name: str, n: int, support: list[int], split: str, i: int, phases_only: bool):
    seed = split_seed(split, i)
    rng = rng_for("D.sparse_struct", name, seed, phases_only)
    m = len(support)
    v = np.exp(2j * np.pi * rng.random(m)) / math.sqrt(m) if phases_only else random_amplitudes(m, rng)
    amp = dict(zip(support, v))
    kind = "random phases" if phases_only else "complex Gaussian amplitudes"
    inst = make_instance(f"D.sparse_struct.{name}.{'ph' if phases_only else 'amp'}.s{seed}", n, amp, "sparse_struct",
                         {"n": n, "nonzeros": m, "support": name, "seed": seed, "amplitudes": kind},
                         _src(f"structured support ({name}), {kind}"), {"size_bin": size_bin(n)}, approx=True)
    return Planned(split, inst)


def gen_fixed_weight(split: str, i: int):
    seed = split_seed(split, i)
    rng = rng_for("D.fixed_weight", seed)
    n = int(rng.integers(12, 31))
    w = int(rng.integers(2, 5))
    m = int(rng.integers(16, 65))
    m = min(m, math.comb(n, w))
    sup = set()
    while len(sup) < m:
        S = rng.choice(n, w, replace=False)
        sup.add(int(sum(1 << int(q) for q in S)))
    v = random_amplitudes(m, rng)
    inst = make_instance(f"D.sparse_struct.fixed_weight.n{n}.w{w}.m{m}.s{seed}", n, dict(zip(sorted(sup), v)), "sparse_struct",
                         {"n": n, "nonzeros": m, "support": f"fixed Hamming weight {w}", "seed": seed},
                         _src("fixed-weight support, complex Gaussian amplitudes"), {"size_bin": size_bin(n)}, approx=True)
    return Planned(split, inst)


def generate_all(log=print) -> list:
    P = []
    # dicke k = 2 (k = 1 is the W family); k >= 3 only in test_ood
    val_n = {6, 11, 16, 21}
    for n in range(4, 25):
        P.append(gen_dicke(n, 2, "val" if n in val_n else "train"))
    for n in range(25, 41):
        P.append(gen_dicke(n, 2, "test_in"))
    ood = []
    for n in range(6, 41):
        for k in range(3, n // 2 + 1):
            if math.comb(n, k) <= 4096:
                ood.append((n, k))
    pick = sorted(ood, key=lambda nk: (nk[0] * 7919 + nk[1] * 104729) % 1009)[:40]
    for n, k in sorted(pick):
        P.append(gen_dicke(n, k, "test_ood"))
    log(f"[D] dicke: {sum(1 for p in P if p.inst.family == 'dicke')}")
    # W
    val_w = {7, 13, 19, 25, 31}
    for n in range(4, 33):
        P.append(gen_w(n, "val" if n in val_w else "train"))
    for n in (33, 36, 40, 48, 56, 64, 80, 96, 112, 128):
        P.append(gen_w(n, "test_in"))
    log(f"[D] w: {sum(1 for p in P if p.inst.family == 'w')}")
    # dense: train/val n = 3..8, test_in n = 9, 10
    for n in range(3, 9):
        for j in range(16):
            P.append(gen_dense("train", n, 100 * n + j))
        for j in range(5):
            P.append(gen_dense("val", n, 100 * n + j))
    for n in (9, 10):
        for j in range(15):
            P.append(gen_dense("test_in", n, 100 * n + j))
    log(f"[D] dense: {sum(1 for p in P if p.inst.family == 'dense')}")
    # sparse: random support
    for bi, b in enumerate(("S", "M", "L")):
        for sp, cnt in (("train", 36), ("val", 12), ("test_in", 4)):
            for j in range(cnt):
                P.append(gen_sparse(sp, b, 1000 * bi + j))
    for j in range(24):
        P.append(gen_sparse("test_in", "XL", 3000 + j))
    log(f"[D] sparse: {sum(1 for p in P if p.inst.family == 'sparse')}")
    # test_ood: structured supports
    k = 0
    for name, n, sup in structured_supports():
        for ph in (True, False):
            for j in range(3):
                P.append(gen_structured(name, n, sup, "test_ood", 100 * k + j, ph))
        k += 1
    for j in range(12):
        P.append(gen_fixed_weight("test_ood", 5000 + j))
    log(f"[D] sparse_struct: {sum(1 for p in P if p.inst.family == 'sparse_struct')}")
    # probe: small dense states (2 and 3 qubits)
    for n, cnt in ((2, 10), (3, 20)):
        for j in range(cnt):
            P.append(gen_dense("probe", n, 100 * n + j))
    log(f"[D] total {len(P)}")
    return P


def regenerate(p, attempt: int):
    name, args, i = p.regen
    return globals()[name](*args, i + 100 * attempt)
