"""Dense GF(2) linear algebra on numpy uint8 arrays (0/1 entries).

All functions copy their inputs; nothing is modified in place for the caller.
"""
from __future__ import annotations

import numpy as np


def as_gf2(m) -> np.ndarray:
    a = np.array(m, dtype=np.uint8, copy=True)
    a &= 1
    return a


def rref(m) -> tuple[np.ndarray, list[int]]:
    """Reduced row echelon form. Returns (R, pivot_columns); R has exactly rank(m) rows."""
    a = as_gf2(m)
    if a.ndim != 2:
        raise ValueError("rref expects a 2-d array")
    rows, cols = a.shape
    piv: list[int] = []
    r = 0
    for c in range(cols):
        if r == rows:
            break
        nz = np.flatnonzero(a[r:, c])
        if nz.size == 0:
            continue
        p = r + int(nz[0])
        if p != r:
            a[[r, p]] = a[[p, r]]
        mask = a[:, c].astype(bool)
        mask[r] = False
        a[mask] ^= a[r]
        piv.append(c)
        r += 1
    return a[:r], piv


def rank(m) -> int:
    a = as_gf2(m)
    if a.size == 0:
        return 0
    return len(rref(a)[1])


def rowspace_equal(a, b) -> bool:
    ra, rb = rref(a)[0], rref(b)[0]
    return ra.shape == rb.shape and bool(np.array_equal(ra, rb))


def in_rowspace(v, m) -> bool:
    m = as_gf2(m)
    if m.size == 0:
        return not as_gf2(v).any()
    return rank(np.vstack([m, as_gf2(v).reshape(1, -1)])) == rank(m)


def nullspace(m) -> np.ndarray:
    """Basis (rows) of {x : m x = 0}."""
    a = as_gf2(m)
    n = a.shape[1]
    r, piv = rref(a)
    free = [c for c in range(n) if c not in set(piv)]
    basis = np.zeros((len(free), n), dtype=np.uint8)
    for i, f in enumerate(free):
        basis[i, f] = 1
        for row, p in zip(r, piv):
            if row[f]:
                basis[i, p] = 1
    return basis


def solve_many(a, b) -> tuple[np.ndarray, np.ndarray]:
    """Solve a @ X = b column-wise over GF(2).

    a: (r, c), b: (r, t). Returns (X, ok) with X of shape (c, t) and ok a bool mask of length t
    telling which right-hand sides are solvable (X columns of unsolvable ones are undefined).
    """
    a = as_gf2(a)
    b = as_gf2(b)
    if b.ndim == 1:
        b = b.reshape(-1, 1)
    rows, cols = a.shape
    aug = np.concatenate([a, b], axis=1)
    red, piv = rref(aug)
    piv_a = [p for p in piv if p < cols]
    x = np.zeros((cols, b.shape[1]), dtype=np.uint8)
    ok = np.ones(b.shape[1], dtype=bool)
    # a column j of b is unsolvable iff some reduced row has zero a-part and 1 in column j
    zero_a_rows = ~red[:, :cols].any(axis=1)
    if zero_a_rows.any():
        bad = red[zero_a_rows][:, cols:].any(axis=0)
        ok &= ~bad
    for i, p in enumerate(piv_a):
        x[p] = red[i, cols:]
    return x, ok


def solve(a, b) -> np.ndarray | None:
    x, ok = solve_many(a, as_gf2(b).reshape(-1, 1))
    return x[:, 0] if ok[0] else None


def inverse(m) -> np.ndarray:
    a = as_gf2(m)
    n = a.shape[0]
    if a.shape != (n, n):
        raise ValueError("square matrix expected")
    red, piv = rref(np.concatenate([a, np.eye(n, dtype=np.uint8)], axis=1))
    if piv[:n] != list(range(n)):
        raise ValueError("matrix is singular over GF(2)")
    return red[:n, n:]


def random_invertible(k: int, rng: np.random.Generator) -> np.ndarray:
    while True:
        m = rng.integers(0, 2, size=(k, k), dtype=np.uint8)
        if rank(m) == k:
            return m


def random_full_rank(r: int, n: int, rng: np.random.Generator, density: float = 0.5) -> np.ndarray:
    if r > n:
        raise ValueError("r > n")
    while True:
        m = (rng.random((r, n)) < density).astype(np.uint8)
        if rank(m) == r:
            return m


def sparse_rows(m) -> list[list[int]]:
    return [np.flatnonzero(row).tolist() for row in as_gf2(m)]


def from_sparse_rows(rows: list[list[int]], n: int) -> np.ndarray:
    m = np.zeros((len(rows), n), dtype=np.uint8)
    for i, r in enumerate(rows):
        m[i, r] = 1
    return m


def row_ints(m) -> list[int]:
    """Rows as Python ints (bit j = column j); handy for fast enumeration."""
    out = []
    for row in as_gf2(m):
        v = 0
        for j in np.flatnonzero(row):
            v |= 1 << int(j)
        out.append(v)
    return out
