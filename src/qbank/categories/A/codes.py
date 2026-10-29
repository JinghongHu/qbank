"""Category A code library: constructions from primary definitions + independent verification.

Every constructor returns a CodeSpec. verify_code() recomputes n, k, commutation and (when feasible) the exact
distance; nothing reported by a library or a paper is trusted without recomputation (MQT's
construct_bb_code(90) is not Bravyi's [[90,8,10]]).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

from ...core import gf2
from ...core.pauli import PauliRows, commutes, rref as pauli_rref


@dataclass
class CodeSpec:
    name: str
    family: str
    params: dict
    n: int
    css: bool
    hx: np.ndarray | None = None          # CSS X checks (rows), may be redundant
    hz: np.ndarray | None = None          # CSS Z checks (rows), may be redundant
    stabilizers: PauliRows | None = None  # non-CSS generators (independent after rref), signs included
    logical_z: PauliRows | None = None    # non-CSS: chosen logical Z basis (defines |0_L>)
    source: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    reported: dict = field(default_factory=dict)  # values quoted from elsewhere (e.g. d from a paper), never trusted

    def k(self) -> int:
        if self.css:
            return self.n - gf2.rank(self.hx) - gf2.rank(self.hz)
        return self.n - gf2.rank(self.stabilizers.symplectic())


# ============================================================================ CSS helpers
def css_commute(hx: np.ndarray, hz: np.ndarray) -> bool:
    return not ((hx.astype(np.int64) @ hz.T.astype(np.int64)) % 2).any()


def css_logicals(hx: np.ndarray, hz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Paired logical bases: Lx (k x n) with Hz Lx^T = 0, Lz with Hx Lz^T = 0, and Lx Lz^T = I."""
    n = hx.shape[1]

    def complement(kernel: np.ndarray, stab: np.ndarray) -> np.ndarray:
        base = gf2.rref(stab)[0] if stab.size else np.zeros((0, n), np.uint8)
        chosen = []
        cur = base
        for v in kernel:
            cand = np.vstack([cur, v]) if cur.size else v.reshape(1, -1)
            if gf2.rank(cand) > (gf2.rank(cur) if cur.size else 0):
                chosen.append(v)
                cur = cand
        return np.array(chosen, dtype=np.uint8).reshape(-1, n)

    lz = complement(gf2.nullspace(hx), hz)   # Z-type ops commuting with X checks, not Z stabilizers
    lx = complement(gf2.nullspace(hz), hx)
    if lx.shape[0] != lz.shape[0]:
        raise ValueError("inconsistent logical dimensions")
    m = (lx.astype(np.int64) @ lz.T.astype(np.int64)) % 2
    lz = (gf2.inverse(m).T.astype(np.int64) @ lz.astype(np.int64)) % 2
    lz = lz.astype(np.uint8)
    assert ((lx.astype(np.int64) @ lz.T.astype(np.int64)) % 2 == np.eye(lx.shape[0], dtype=np.int64)).all()
    return lx, lz


def css_zero_state_rows(hx: np.ndarray) -> PauliRows:
    """Full stabilizer group of |0...0>_L: independent X checks + basis of all Z operators commuting with them."""
    n = hx.shape[1]
    xs = gf2.rref(hx)[0]
    zs = gf2.nullspace(hx)
    return PauliRows.css(xs, zs, n)


# ============================================================================ distance
def _pack(rows: np.ndarray) -> np.ndarray:
    """(m, n) 0/1 -> (m, W) uint64 words (bit j of word w = column 64*w + j)."""
    m, n = rows.shape
    W = (n + 63) // 64
    out = np.zeros((m, W), dtype=np.uint64)
    for j in range(n):
        out[:, j // 64] |= rows[:, j].astype(np.uint64) << np.uint64(j % 64)
    return out


def _span_all(basis_w: np.ndarray) -> np.ndarray:
    """All 2^m combinations of the packed basis rows (including 0), as (2^m, W)."""
    m, W = basis_w.shape
    out = np.zeros((1 << m, W), dtype=np.uint64)
    for i in range(m):
        out[1 << i: 1 << (i + 1)] = out[: 1 << i] ^ basis_w[i]
    return out


def _min_weight_logical(ker: np.ndarray, anti: np.ndarray) -> int | None:
    """Exact min weight over span(ker) of vectors with odd overlap with at least one row of anti.

    Meet in the middle, vectorised: span = L xor R with L, R spans of the two halves of the basis."""
    kw, aw = _pack(ker), _pack(anti)
    m = kw.shape[0]
    h = m // 2
    left, right = _span_all(kw[:h]), _span_all(kw[h:])
    # parity of overlap with each anti row, for left and right parts (bitmask over anti rows, k <= 64 handled in chunks)
    def par(vs):
        cols = []
        for a in aw:
            cols.append((np.bitwise_count(vs & a).sum(axis=1) & 1).astype(np.uint64))
        return np.stack(cols, axis=1) if cols else np.zeros((len(vs), 0), np.uint64)
    pl, pr = par(left), par(right)
    best = None
    for i in range(left.shape[0]):
        v = right ^ left[i]
        logical = (pr ^ pl[i]).any(axis=1)
        if not logical.any():
            continue
        w = np.bitwise_count(v[logical]).sum(axis=1)
        mn = int(w.min())
        if best is None or mn < best:
            best = mn
    return best


def css_distance(hx: np.ndarray, hz: np.ndarray, max_dim: int = 26) -> dict:
    """Exact dX, dZ by kernel enumeration when the kernel dimension is <= max_dim; else a low-weight search bound."""
    lx, lz = css_logicals(hx, hz)
    out = {"k": int(lx.shape[0])}
    if lx.shape[0] == 0:
        return {"k": 0, "d": None, "method": "k=0"}
    res = {}
    for kind, check, anti in (("dZ", hx, lx), ("dX", hz, lz)):
        ker = gf2.nullspace(check)
        if ker.shape[0] <= max_dim:
            res[kind] = ("exact", _min_weight_logical(ker, anti))
        else:
            lb, found = low_weight_logical_search(check, anti, max_w=4)
            res[kind] = ("search", found if found is not None else None, lb)
    exact = all(r[0] == "exact" for r in res.values())
    if exact:
        out.update(dX=res["dX"][1], dZ=res["dZ"][1], d=min(res["dX"][1], res["dZ"][1]), method="exact_kernel_enumeration")
    else:
        found = [r[1] for r in res.values() if r[1] is not None]
        lower = min((r[2] if r[0] == "search" else r[1]) for r in res.values())
        out.update(d=min(found) if found else None, d_lower=lower if not found else None,
                   method="low_weight_search(w<=4)" + ("" if found else ": no logical of weight <= 4 found"),
                   dX=res["dX"][1] if res["dX"][0] == "exact" else None,
                   dZ=res["dZ"][1] if res["dZ"][0] == "exact" else None)
    return out


def low_weight_logical_search(check: np.ndarray, anti: np.ndarray, max_w: int = 4) -> tuple[int, int | None]:
    """Search vectors v of weight <= max_w with check v = 0 and odd overlap with some row of anti.

    Uses column-syndrome hashing (w=1,2,3 exactly; w=4 via pair-sum collisions). Returns (lower_bound, found_weight):
    if found_weight is None, no such vector of weight <= max_w exists and the distance is >= max_w + 1.
    """
    n = check.shape[1]
    cols = [bytes(np.packbits(check[:, j])) for j in range(n)]
    anti_cols = [gf2.row_ints(anti[:, [j]].T)[0] for j in range(n)]  # bitmask over logical rows for column j

    def is_logical(support) -> bool:
        acc = 0
        for j in support:
            acc ^= anti_cols[j]
        return acc != 0

    zero = bytes(np.packbits(np.zeros(check.shape[0], np.uint8)))
    # w = 1
    for j in range(n):
        if cols[j] == zero and is_logical([j]):
            return 1, 1
    colint = [int.from_bytes(c, "big") for c in cols]
    by_val: dict[int, list[int]] = {}
    for j, v in enumerate(colint):
        by_val.setdefault(v, []).append(j)
    # w = 2: equal columns
    for js in by_val.values():
        for a, b in itertools.combinations(js, 2):
            if is_logical([a, b]):
                return 2, 2
    if max_w < 3:
        return 3, None
    # w = 3: c_a ^ c_b == c_c
    for a in range(n):
        for b in range(a + 1, n):
            for c in by_val.get(colint[a] ^ colint[b], []):
                if c > b and is_logical([a, b, c]):
                    return 3, 3
    if max_w < 4:
        return 4, None
    # w = 4: c_a ^ c_b == c_c ^ c_d
    pairs: dict[int, list[tuple[int, int]]] = {}
    for a in range(n):
        for b in range(a + 1, n):
            pairs.setdefault(colint[a] ^ colint[b], []).append((a, b))
    for lst in pairs.values():
        if len(lst) < 2:
            continue
        for (a, b), (c, d) in itertools.combinations(lst, 2):
            s = {a, b, c, d}
            if len(s) == 4 and is_logical(sorted(s)):
                return 4, 4
    return max_w + 1, None


# ============================================================================ general stabilizer helpers
def symplectic_logicals(stabs: PauliRows) -> tuple[PauliRows, PauliRows]:
    """Paired logical operators (all with + sign) for a general stabilizer code via symplectic Gram–Schmidt."""
    n = stabs.n
    s = gf2.rref(stabs.symplectic())[0]
    # normalizer: v with s_x.v_z + s_z.v_x = 0
    form = np.concatenate([s[:, n:], s[:, :n]], axis=1)
    norm = gf2.nullspace(form)
    cur = s.copy()
    reps = []
    for v in norm:
        cand = np.vstack([cur, v])
        if gf2.rank(cand) > gf2.rank(cur):
            reps.append(v.copy())
            cur = cand

    def sp(a, b):
        return int((a[:n] @ b[n:] + a[n:] @ b[:n]) % 2)

    xs, zs = [], []
    reps = [r for r in reps]
    while reps:
        a = reps.pop(0)
        j = next((i for i, b in enumerate(reps) if sp(a, b)), None)
        if j is None:
            raise ValueError("symplectic Gram-Schmidt failed")
        b = reps.pop(j)
        xs.append(a)
        zs.append(b)
        new = []
        for u in reps:
            u = u.copy()
            if sp(u, b):
                u ^= a
            if sp(u, a):
                u ^= b
            new.append(u)
        reps = new
    k = len(xs)
    mk = lambda rows: PauliRows(np.array(rows, np.uint8)[:, :n].reshape(k, n), np.array(rows, np.uint8)[:, n:].reshape(k, n), np.zeros(k, np.uint8))
    if k == 0:
        e = PauliRows(np.zeros((0, n), np.uint8), np.zeros((0, n), np.uint8), np.zeros(0, np.uint8))
        return e, e
    return mk(xs), mk(zs)


def zero_state_rows(code: CodeSpec) -> PauliRows:
    """Full stabilizer group (n generators) of the code's |0...0>_L."""
    if code.css:
        return css_zero_state_rows(code.hx)
    lz = code.logical_z
    rows = PauliRows(np.vstack([code.stabilizers.x, lz.x]), np.vstack([code.stabilizers.z, lz.z]),
                     np.concatenate([code.stabilizers.r, lz.r]))
    return pauli_rref(rows)[0]


def code_stabilizer_rows(code: CodeSpec) -> PauliRows:
    if code.css:
        return PauliRows.css(gf2.rref(code.hx)[0], gf2.rref(code.hz)[0], code.n)
    return pauli_rref(code.stabilizers)[0]


def verify_code(code: CodeSpec, want: dict | None = None, max_dim: int = 26) -> dict:
    """Recompute n, k, commutation and distance (exact when feasible). Compares with `want` (e.g. {'k': 1})."""
    out = {"n": code.n}
    if code.css:
        if code.hx.shape[1] != code.n or code.hz.shape[1] != code.n:
            raise ValueError("width mismatch")
        out["commute"] = css_commute(code.hx, code.hz)
        out["k"] = code.k()
        out["rank_hx"] = gf2.rank(code.hx)
        out["rank_hz"] = gf2.rank(code.hz)
        out["max_x_weight"] = int(code.hx.sum(axis=1).max()) if code.hx.size else 0
        out["max_z_weight"] = int(code.hz.sum(axis=1).max()) if code.hz.size else 0
        if out["commute"] and out["k"] > 0:
            out["distance"] = css_distance(code.hx, code.hz, max_dim=max_dim)
    else:
        st = code.stabilizers
        out["commute"] = not commutes(st, st).any()
        out["k"] = code.k()
        if code.logical_z is not None:
            lz = code.logical_z
            out["logical_z_ok"] = (not commutes(st, lz).any()) and (not commutes(lz, lz).any()) and \
                gf2.rank(np.vstack([st.symplectic(), lz.symplectic()])) == gf2.rank(st.symplectic()) + lz.m
        out["distance"] = general_distance(st, max_dim=max_dim)
    if want:
        out["expected"] = want
        out["matches_expected"] = all(out.get(k) == v for k, v in want.items() if k in out)
    if not out["commute"]:
        raise ValueError(f"{code.name}: stabilizers do not commute")
    return out


def general_distance(stabs: PauliRows, max_dim: int = 22) -> dict:
    """Exact distance of a general stabilizer code by enumerating the normalizer when dim <= max_dim."""
    n = stabs.n
    s = gf2.rref(stabs.symplectic())[0]
    lx, lz = symplectic_logicals(stabs)
    k = lx.m
    if k == 0:
        return {"k": 0, "d": None}
    dim = s.shape[0] + 2 * k
    if dim > max_dim:
        return {"k": k, "d": None, "method": f"not computed (normalizer dim {dim} > {max_dim})"}
    logs = np.vstack([lx.symplectic(), lz.symplectic()])
    # element = stab combo + nonzero logical combo; weight = |supp(x|z)|
    st_ints = [(int("".join(map(str, r[:n][::-1])), 2), int("".join(map(str, r[n:][::-1])), 2)) for r in s]
    lg_ints = [(int("".join(map(str, r[:n][::-1])), 2), int("".join(map(str, r[n:][::-1])), 2)) for r in logs]
    best = None
    for lmask in range(1, 1 << len(lg_ints)):
        bx = bz = 0
        for j, (a, b) in enumerate(lg_ints):
            if lmask >> j & 1:
                bx ^= a; bz ^= b
        x, z = bx, bz
        for i in range(1 << len(st_ints)):
            if i:
                j = (i & -i).bit_length() - 1
                x ^= st_ints[j][0]; z ^= st_ints[j][1]
            w = bin(x | z).count("1")
            if best is None or w < best:
                best = w
    return {"k": k, "d": best, "method": "exact_normalizer_enumeration"}


# ============================================================================ constructions (training families T)
def _src(name: str, ref: str = "", license_: str = "qbank (CC0-style: generated by qbank code)") -> dict:
    return {"kind": "generator", "name": name, "version": "1", "ref": ref, "license": license_}


def rotated_surface(d: int) -> CodeSpec:
    """Rotated surface code [[d^2, 1, d]] on a d x d grid (any d >= 2). X/Z plaquettes in checkerboard,
    weight-2 X boundaries on top/bottom rows, weight-2 Z boundaries on left/right columns."""
    q = lambda r, c: r * d + c
    xs, zs = [], []
    for r in range(d - 1):
        for c in range(d - 1):
            sup = [q(r, c), q(r, c + 1), q(r + 1, c), q(r + 1, c + 1)]
            (xs if (r + c) % 2 == 0 else zs).append(sup)
    for c in range(d - 1):
        if (c % 2) == 1:            # top boundary faces continuing the checkerboard with X
            xs.append([q(0, c), q(0, c + 1)])
        if ((d - 1) + c) % 2 == 0:  # bottom boundary
            xs.append([q(d - 1, c), q(d - 1, c + 1)])
    for r in range(d - 1):
        if (r % 2) == 0:            # left boundary Z faces
            zs.append([q(r, 0), q(r + 1, 0)])
        if (r + (d - 1)) % 2 == 1:  # right boundary
            zs.append([q(r, d - 1), q(r + 1, d - 1)])
    n = d * d
    return CodeSpec(f"rot_surface_d{d}", "rot_surface", {"d": d}, n, True,
                    gf2.from_sparse_rows(xs, n), gf2.from_sparse_rows(zs, n),
                    source=_src("rotated_surface", "Bombin & Martin-Delgado 2007; Horsman et al. 2012 (rotated layout)"))


def color_code(kind: str, d: int) -> CodeSpec:
    """Triangular 6.6.6 or 4.8.8 color code (lattice from mqt.qecc 2.0.0, independently verified here)."""
    from mqt.qecc.codes import HexagonalColorCode, SquareOctagonColorCode
    cls = HexagonalColorCode if kind == "666" else SquareOctagonColorCode
    c = cls(distance=d)
    hx = gf2.as_gf2(c.Hx)
    hz = gf2.as_gf2(c.Hz)
    fam = f"color_{kind}"
    return CodeSpec(f"{fam}_d{d}", fam, {"d": d}, int(c.n), True, hx, hz,
                    source={"kind": "library", "name": f"mqt.qecc.codes.{cls.__name__}", "version": "mqt.qecc 2.0.0",
                            "ref": "Bombin & Martin-Delgado 2006 (topological color codes)", "license": "MIT"})


def hamming_matrix(r: int) -> np.ndarray:
    n = 2 ** r - 1
    return np.array([[(j + 1) >> i & 1 for j in range(n)] for i in range(r)], dtype=np.uint8)


def quantum_hamming(r: int) -> CodeSpec:
    h = hamming_matrix(r)
    n = h.shape[1]
    return CodeSpec(f"qhamming_r{r}", "qhamming", {"r": r}, n, True, h.copy(), h.copy(),
                    source=_src("quantum_hamming", "Steane 1996: CSS(H_r, H_r), [[2^r-1, 2^r-1-2r, 3]]"))


def quantum_reed_muller(m: int) -> CodeSpec:
    """[[2^m - 1, 1, 3]] punctured quantum Reed–Muller code. X checks: the m coordinate functions on nonzero points;
    Z checks: all monomials of degree 1..m-2 in those coordinates."""
    pts = [[(j + 1) >> i & 1 for i in range(m)] for j in range(2 ** m - 1)]
    pts = np.array(pts, dtype=np.uint8)      # (n, m)
    n = pts.shape[0]
    hx = pts.T.copy()
    zs = []
    for deg in range(1, m - 1):
        for S in itertools.combinations(range(m), deg):
            zs.append(np.prod(pts[:, list(S)], axis=1).astype(np.uint8))
    hz = np.array(zs, dtype=np.uint8)
    return CodeSpec(f"qrm_m{m}", "qrm", {"m": m}, n, True, hx, hz,
                    source=_src("quantum_reed_muller", "punctured QRM [[2^m-1,1,3]] (Steane 1999; Anderson et al. 2014)"))


def quantum_reed_muller_r(m: int, r: int) -> CodeSpec:
    """A 1.2.0 (10-28): punctured quantum Reed-Muller code QRM(r, m) = [[2^m - 1, 1, d]] for 1 <= r <= m - 2.
    X checks: all monomials of degree 1..r in the m coordinates on the nonzero points; Z checks: degree 1..m-1-r.
    A product of an X and a Z monomial has degree <= m - 1, hence even weight 2^(m - deg) on the nonzero points, so the
    checks commute; the ranks add up to 2^m - 2, so k = 1. r = 1 is quantum_reed_muller(m) (same matrices)."""
    if not 1 <= r <= m - 2:
        raise ValueError("QRM(r, m) needs 1 <= r <= m - 2")
    pts = np.array([[(j + 1) >> i & 1 for i in range(m)] for j in range(2 ** m - 1)], dtype=np.uint8)
    n = pts.shape[0]

    def mono(maxdeg):
        return np.array([np.prod(pts[:, list(S)], axis=1).astype(np.uint8)
                         for deg in range(1, maxdeg + 1) for S in itertools.combinations(range(m), deg)], dtype=np.uint8)
    hx, hz = mono(r), mono(m - 1 - r)
    name = f"qrm_m{m}" if r == 1 else f"qrm_m{m}r{r}"
    return CodeSpec(name, "qrm", {"m": m} if r == 1 else {"m": m, "r": r}, n, True, hx, hz,
                    source=_src("quantum_reed_muller", f"punctured QRM(r={r}, m={m}) [[2^m-1,1,d]] (Steane 1999; "
                                                       "Anderson et al. 2014); qbank A 1.2.0"))


def _shift(s: int, e: int = 1) -> np.ndarray:
    """Cyclic shift matrix S^e (S = identity rolled by one column)."""
    return np.roll(np.eye(s, dtype=np.uint8), e % s, axis=1)


def bivariate_bicycle(l: int, m: int, a_terms, b_terms, name: str | None = None) -> CodeSpec:
    """Bravyi et al. (arXiv:2308.07915) convention: x = S_l (x) I_m, y = I_l (x) S_m; terms are (i, j) for x^i y^j;
    H_X = [A | B], H_Z = [B^T | A^T]. (x^i y^j = S_l^i (x) S_m^j.)"""
    mono = lambda i, j: np.kron(_shift(l, i), _shift(m, j))
    A = np.zeros((l * m, l * m), dtype=np.uint8)
    B = np.zeros((l * m, l * m), dtype=np.uint8)
    for i, j in a_terms:
        A ^= mono(i, j)
    for i, j in b_terms:
        B ^= mono(i, j)
    hx = np.hstack([A, B]).astype(np.uint8)
    hz = np.hstack([B.T, A.T]).astype(np.uint8)
    params = {"l": l, "m": m, "A": [list(t) for t in a_terms], "B": [list(t) for t in b_terms]}
    return CodeSpec(name or f"bb_l{l}_m{m}", "bb", params, 2 * l * m, True, hx, hz,
                    source=_src("bivariate_bicycle", "Bravyi et al., arXiv:2308.07915, Nature 627, 778 (2024)"))


def generalized_bicycle(l: int, a_exps, b_exps) -> CodeSpec:
    A = np.zeros((l, l), dtype=np.uint8)
    B = np.zeros((l, l), dtype=np.uint8)
    for e in a_exps:
        A ^= _shift(l, e)
    for e in b_exps:
        B ^= _shift(l, e)
    hx = np.hstack([A, B]).astype(np.uint8)
    hz = np.hstack([B.T, A.T]).astype(np.uint8)
    return CodeSpec(f"gb_l{l}", "gb", {"l": l, "a": list(a_exps), "b": list(b_exps)}, 2 * l, True, hx, hz,
                    source=_src("generalized_bicycle", "Kovalev & Pryadko 2013; Panteleev & Kalachev 2021"))


def random_css(n: int, rx: int, rz: int, rng: np.random.Generator) -> CodeSpec:
    hx = gf2.random_full_rank(rx, n, rng)
    ker = gf2.nullspace(hx)
    r = gf2.random_full_rank(rz, ker.shape[0], rng)
    hz = ((r.astype(np.int64) @ ker.astype(np.int64)) % 2).astype(np.uint8)
    return CodeSpec(f"css_rand_n{n}", "css_rand", {"n": n, "rx": rx, "rz": rz}, n, True, hx, hz,
                    source=_src("random_css_dense"))


def random_stabilizer_state(n: int, seed: int) -> PauliRows:
    """Uniformly random n-qubit stabilizer state (qiskit.quantum_info.random_clifford(n, seed) applied to |0>)."""
    from qiskit.quantum_info import random_clifford
    cl = random_clifford(n, seed=seed)
    labels = cl.to_labels(mode="S")
    # qiskit labels are little-endian (qubit 0 rightmost): reverse the body, keep the sign
    return PauliRows.from_strings([lab[0] + lab[1:][::-1] if lab[0] in "+-" else "+" + lab[::-1] for lab in labels], n)


# ============================================================================ held-out families O and sporadic codes
def hypergraph_product(h1: np.ndarray, h2: np.ndarray, name: str, family: str, params: dict, src: dict) -> CodeSpec:
    m1, n1 = h1.shape
    m2, n2 = h2.shape
    hx = np.hstack([np.kron(h1, np.eye(n2, dtype=np.uint8)), np.kron(np.eye(m1, dtype=np.uint8), h2.T)]) % 2
    hz = np.hstack([np.kron(np.eye(n1, dtype=np.uint8), h2), np.kron(h1.T, np.eye(m2, dtype=np.uint8))]) % 2
    n = n1 * n2 + m1 * m2
    return CodeSpec(name, family, params, n, True, hx.astype(np.uint8), hz.astype(np.uint8), source=src)


def random_biregular_ldpc(n: int, dv: int, dc: int, rng: np.random.Generator) -> np.ndarray:
    """Random (dv, dc)-biregular parity-check matrix via the configuration model (multi-edges cancel mod 2)."""
    if (n * dv) % dc:
        raise ValueError("n*dv must be divisible by dc")
    m = n * dv // dc
    var_stubs = np.repeat(np.arange(n), dv)
    chk_stubs = np.repeat(np.arange(m), dc)
    rng.shuffle(chk_stubs)
    h = np.zeros((m, n), dtype=np.uint8)
    for v, c in zip(var_stubs, chk_stubs):
        h[c, v] ^= 1
    return h


def repetition_checks(d: int, cyclic: bool = False) -> np.ndarray:
    rows = d if cyclic else d - 1
    h = np.zeros((rows, d), dtype=np.uint8)
    for i in range(rows):
        h[i, i] = 1
        h[i, (i + 1) % d] = 1
    return h


def unrotated_surface(d: int) -> CodeSpec:
    h = repetition_checks(d)
    return hypergraph_product(h, h, f"unrot_surface_d{d}", "unrot_surface", {"d": d},
                              _src("hypergraph_product(rep_d, rep_d)", "Tillich & Zemor 2009; Kitaev planar code"))


def toric(d: int) -> CodeSpec:
    h = repetition_checks(d, cyclic=True)
    return hypergraph_product(h, h, f"toric_d{d}", "toric", {"d": d},
                              _src("hypergraph_product(cyclic_rep_d, cyclic_rep_d)", "Kitaev toric code"))


def iceberg(m: int) -> CodeSpec:
    n = 2 * m
    one = np.ones((1, n), dtype=np.uint8)
    return CodeSpec(f"iceberg_m{m}", "iceberg", {"m": m}, n, True, one.copy(), one.copy(),
                    source=_src("iceberg", "Self, Benedetti, Amaro, arXiv:2211.06703: [[k+2,k,2]]"))


def shor_type(a: int, b: int) -> CodeSpec:
    """[[a*b, 1, min(a,b)]]: a blocks of b-qubit bit-flip repetition codes, phase-flip repetition across blocks."""
    n = a * b
    zs, xs = [], []
    for blk in range(a):
        for j in range(b - 1):
            zs.append([blk * b + j, blk * b + j + 1])
    for blk in range(a - 1):
        xs.append(list(range(blk * b, (blk + 2) * b)))
    return CodeSpec(f"shor_concat_{a}x{b}", "shor_concat", {"a": a, "b": b}, n, True,
                    gf2.from_sparse_rows(xs, n), gf2.from_sparse_rows(zs, n),
                    source=_src("shor_type", "Shor 1995 ([[9,1,3]] = a=b=3)"))


def many_hypercube(level: int) -> CodeSpec:
    from mqt.qecc.codes import construct_many_hypercube_code
    c = construct_many_hypercube_code(level)
    return CodeSpec(f"many_hypercube_L{level}", "many_hypercube", {"L": level}, int(c.n), True,
                    gf2.as_gf2(c.Hx), gf2.as_gf2(c.Hz),
                    source={"kind": "library", "name": "mqt.qecc.codes.construct_many_hypercube_code", "version": "mqt.qecc 2.0.0",
                            "ref": "Goto, arXiv:2403.16054 ([[6^L,4^L,2^L]])", "license": "MIT"})


def mqt_named(name: str) -> CodeSpec:
    """Codes shipped in mqt.qecc 2.0.0 (src/mqt/qecc/codes/instances)."""
    from mqt.qecc import CSSCode
    c = CSSCode.from_code_name(name)
    return CodeSpec(name, name, {}, int(c.n), True, gf2.as_gf2(c.Hx), gf2.as_gf2(c.Hz),
                    source={"kind": "external", "name": f"mqt.qecc CSSCode.from_code_name('{name}')", "version": "mqt.qecc 2.0.0",
                            "ref": "github.com/munich-quantum-toolkit/qecc src/mqt/qecc/codes/instances", "license": "MIT"})


def mqt_misc(fname: str) -> CodeSpec:
    """misc/8_3_3.txt, 15_3_5.txt, 30_6_5.txt from mqt.qecc 2.0.0."""
    import os
    import mqt.qecc
    from mqt.qecc import CSSCode, StabilizerCode
    path = os.path.join(os.path.dirname(mqt.qecc.__file__), "codes", "instances", "misc", fname)
    src = {"kind": "external", "name": f"mqt.qecc instances/misc/{fname}", "version": "mqt.qecc 2.0.0",
           "ref": "github.com/munich-quantum-toolkit/qecc", "license": "MIT"}
    base = fname.replace(".txt", "")
    # NOTE: CSSCode.from_file silently mis-parses the non-CSS 8_3_3 file (it has Y terms) into a different CSS code,
    # so the general loader is tried first and a code is treated as CSS only if every generator is pure X or pure Z.
    try:
        c = StabilizerCode.from_file(path)
        strings = [s.lstrip("+-") for s in c.stabs_as_pauli_strings()]
    except Exception:
        c = CSSCode.from_file(path)
        return CodeSpec(f"mqt_{base}", "sporadic", {"file": fname}, int(c.n), True, gf2.as_gf2(c.Hx), gf2.as_gf2(c.Hz), source=src)
    n = int(c.n)
    if all(set(s) <= set("XI_") or set(s) <= set("ZI_") for s in strings):
        hx = [[j for j, ch in enumerate(s) if ch == "X"] for s in strings if set(s) & set("X")]
        hz = [[j for j, ch in enumerate(s) if ch == "Z"] for s in strings if set(s) & set("Z")]
        return CodeSpec(f"mqt_{base}", "sporadic", {"file": fname}, n, True, gf2.from_sparse_rows(hx, n),
                        gf2.from_sparse_rows(hz, n), source=src)
    st = PauliRows.from_strings(["+" + s for s in strings], n)
    return CodeSpec(f"mqt_{base}", "sporadic", {"file": fname}, n, False, stabilizers=st, source=src)


def five_qubit() -> CodeSpec:
    st = PauliRows.from_strings(["+XZZXI", "+IXZZX", "+XIXZZ", "+ZXIXZ"], 5)
    return CodeSpec("five_qubit", "sporadic", {}, 5, False, stabilizers=st,
                    source=_src("five_qubit", "Laflamme et al. 1996; Bennett et al. 1996 [[5,1,3]]"))


def with_logical_z(code: CodeSpec) -> CodeSpec:
    """Attach a canonical logical Z basis to a non-CSS code (defines its |0...0>_L)."""
    if not code.css and code.logical_z is None:
        _, lz = symplectic_logicals(code.stabilizers)
        code.logical_z = lz
    return code


# ============================================================================ concatenation (k_in = 1 inner codes)
def _inner_logicals(code: CodeSpec) -> tuple[PauliRows, PauliRows]:
    if code.css:
        lx, lz = css_logicals(code.hx, code.hz)
        if lx.shape[0] != 1:
            raise ValueError("inner code must have k = 1")
        return PauliRows.css(lx, None, code.n), PauliRows.css(None, lz, code.n)
    lx, lz = symplectic_logicals(code.stabilizers)
    if lx.m != 1:
        raise ValueError("inner code must have k = 1")
    return lx, lz


def _stab_rows(code: CodeSpec) -> PauliRows:
    return code_stabilizer_rows(code)


def concatenate(outer: CodeSpec, inner: CodeSpec, name: str, family: str = "composite") -> CodeSpec:
    """Replace every outer qubit by an inner block (k_in = 1); outer operators map via logical X/Y/Z of the inner code.
    This is the construction used by StabilizerBench's generate_concatenated_codes (its data calls them tensor products)."""
    from ...core.pauli import _g
    ilx, ilz = _inner_logicals(inner)
    ist = _stab_rows(inner)
    ost = _stab_rows(outer)
    nb = inner.n
    N = outer.n * nb
    # inner Y-bar = i * X-bar * Z-bar, as a Hermitian signed Pauli
    e = 1 + int(_g(ilx.x[0], ilx.z[0], ilz.x[0], ilz.z[0]).sum()) + 2 * int(ilx.r[0]) + 2 * int(ilz.r[0])
    e %= 4
    assert e % 2 == 0
    ly = (ilx.x[0] ^ ilz.x[0], ilx.z[0] ^ ilz.z[0], e // 2)
    lx1 = (ilx.x[0], ilx.z[0], int(ilx.r[0]))
    lz1 = (ilz.x[0], ilz.z[0], int(ilz.r[0]))
    xs, zs, rs = [], [], []
    # inner stabilizers on each block
    for b in range(outer.n):
        for i in range(ist.m):
            x = np.zeros(N, np.uint8); z = np.zeros(N, np.uint8)
            x[b * nb:(b + 1) * nb] = ist.x[i]; z[b * nb:(b + 1) * nb] = ist.z[i]
            xs.append(x); zs.append(z); rs.append(int(ist.r[i]))

    def lift(ox, oz, orr):
        x = np.zeros(N, np.uint8); z = np.zeros(N, np.uint8); r = int(orr)
        for q in range(outer.n):
            op = {(1, 0): lx1, (0, 1): lz1, (1, 1): ly}.get((int(ox[q]), int(oz[q])))
            if op is None:
                continue
            x[q * nb:(q + 1) * nb] = op[0]; z[q * nb:(q + 1) * nb] = op[1]; r ^= op[2]
        return x, z, r

    for i in range(ost.m):
        x, z, r = lift(ost.x[i], ost.z[i], ost.r[i])
        xs.append(x); zs.append(z); rs.append(r)
    rows = PauliRows(np.array(xs), np.array(zs), np.array(rs, np.uint8))
    is_css = bool(((rows.x.any(axis=1)) ^ (rows.z.any(axis=1))).all() and not rows.r.any())
    params = {"outer": outer.name, "inner": inner.name}
    src = {"kind": "generator", "name": "concatenate", "version": "1",
           "ref": "construction rule of StabilizerBench (arXiv:2604.21287, data/generate_code.py) re-implemented", "license": "qbank"}
    if is_css:
        hx = rows.x[rows.x.any(axis=1)]
        hz = rows.z[rows.z.any(axis=1)]
        code = CodeSpec(name, family, params, N, True, hx, hz, source=src)
    else:
        code = CodeSpec(name, family, params, N, False, stabilizers=rows, source=src)
        # |0_L> of the composite: outer logical Z lifted
        if outer.css:
            olx, olz = css_logicals(outer.hx, outer.hz)
            oz_rows = PauliRows.css(None, olz, outer.n)
        else:
            oz_rows = symplectic_logicals(outer.stabilizers)[1] if outer.logical_z is None else outer.logical_z
        lz_rows = [lift(oz_rows.x[i], oz_rows.z[i], oz_rows.r[i]) for i in range(oz_rows.m)]
        code.logical_z = PauliRows(np.array([a for a, _, _ in lz_rows]), np.array([b for _, b, _ in lz_rows]),
                                   np.array([c for _, _, c in lz_rows], np.uint8))
    return code
