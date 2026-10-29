"""Signed Hermitian Pauli operators in symplectic form, without any simulator library.

Convention (Aaronson–Gottesman): a row (x, z, r) denotes (-1)^r * prod_j P_j with P_j = I, X, Z, Y for
(x_j, z_j) = (0,0), (1,0), (0,1), (1,1). String form follows stim: optional sign, then one character per
qubit with qubit 0 leftmost ("I" or "_" for identity).
"""
from __future__ import annotations

import numpy as np

from . import gf2


class PauliRows:
    """A stack of m signed Pauli operators on n qubits."""

    __slots__ = ("x", "z", "r")

    def __init__(self, x: np.ndarray, z: np.ndarray, r: np.ndarray):
        self.x = np.asarray(x, dtype=np.uint8)
        self.z = np.asarray(z, dtype=np.uint8)
        self.r = np.asarray(r, dtype=np.uint8)

    @property
    def n(self) -> int:
        return self.x.shape[1]

    @property
    def m(self) -> int:
        return self.x.shape[0]

    def copy(self) -> "PauliRows":
        return PauliRows(self.x.copy(), self.z.copy(), self.r.copy())

    @staticmethod
    def from_strings(strings: list[str], n: int | None = None) -> "PauliRows":
        bodies, signs = [], []
        for s in strings:
            s = s.strip()
            sign = 0
            if s and s[0] in "+-":
                sign = 1 if s[0] == "-" else 0
                s = s[1:]
            bodies.append(s)
            signs.append(sign)
        if n is None:
            n = max((len(b) for b in bodies), default=0)
        x = np.zeros((len(bodies), n), dtype=np.uint8)
        z = np.zeros((len(bodies), n), dtype=np.uint8)
        for i, b in enumerate(bodies):
            if len(b) != n:
                raise ValueError(f"Pauli string of length {len(b)} != n={n}")
            for j, c in enumerate(b):
                if c in "XY":
                    x[i, j] = 1
                if c in "ZY":
                    z[i, j] = 1
                if c not in "IXYZ_":
                    raise ValueError(f"bad Pauli character {c!r}")
        return PauliRows(x, z, np.array(signs, dtype=np.uint8))

    @staticmethod
    def css(hx: np.ndarray | None, hz: np.ndarray | None, n: int) -> "PauliRows":
        """X-type rows from hx followed by Z-type rows from hz, all with + sign."""
        hx = np.zeros((0, n), np.uint8) if hx is None else gf2.as_gf2(hx)
        hz = np.zeros((0, n), np.uint8) if hz is None else gf2.as_gf2(hz)
        x = np.concatenate([hx, np.zeros_like(hz)])
        z = np.concatenate([np.zeros_like(hx), hz])
        return PauliRows(x, z, np.zeros(x.shape[0], dtype=np.uint8))

    def to_strings(self) -> list[str]:
        chars = np.array(["I", "X", "Z", "Y"])
        out = []
        for i in range(self.m):
            body = "".join(chars[self.x[i] + 2 * self.z[i]])
            out.append(("-" if self.r[i] else "+") + body)
        return out

    def symplectic(self) -> np.ndarray:
        return np.concatenate([self.x, self.z], axis=1)

    def relabel(self, perm: list[int] | np.ndarray, n_out: int | None = None) -> "PauliRows":
        """Move qubit i to position perm[i]."""
        perm = np.asarray(perm)
        n_out = self.n if n_out is None else n_out
        x = np.zeros((self.m, n_out), dtype=np.uint8)
        z = np.zeros((self.m, n_out), dtype=np.uint8)
        x[:, perm] = self.x
        z[:, perm] = self.z
        return PauliRows(x, z, self.r.copy())


def _g(x1, z1, x2, z2):
    """Exponent of i picked up by P1*P2 per qubit (vectorised, int array)."""
    x1 = x1.astype(np.int64); z1 = z1.astype(np.int64); x2 = x2.astype(np.int64); z2 = z2.astype(np.int64)
    both = x1 & z1
    xo = x1 & (1 - z1)
    zo = (1 - x1) & z1
    return both * (z2 - x2) + xo * (z2 * (2 * x2 - 1)) + zo * (x2 * (1 - 2 * z2))


def commutes(a: PauliRows, b: PauliRows) -> np.ndarray:
    """(a.m, b.m) matrix, 1 where the pair anticommutes."""
    return ((a.x.astype(np.int64) @ b.z.T.astype(np.int64)) + (a.z.astype(np.int64) @ b.x.T.astype(np.int64))) % 2


def mul_into(rows: PauliRows, targets: np.ndarray, src_x, src_z, src_r) -> None:
    """rows[t] <- src * rows[t] for every t in targets (all pairs must commute). In place."""
    if len(targets) == 0:
        return
    tx, tz = rows.x[targets], rows.z[targets]
    e = 2 * int(src_r) + 2 * rows.r[targets].astype(np.int64) + _g(src_x[None, :], src_z[None, :], tx, tz).sum(axis=1)
    e %= 4
    if np.any(e % 2):
        raise ValueError("multiplied anticommuting Paulis")
    rows.r[targets] = (e // 2).astype(np.uint8)
    rows.x[targets] = tx ^ src_x
    rows.z[targets] = tz ^ src_z


def rref(rows: PauliRows) -> tuple[PauliRows, list[int]]:
    """Signed reduced row echelon form over columns (x_0..x_{n-1}, z_0..z_{n-1}). Rows must pairwise commute."""
    p = rows.copy()
    n = p.n
    m = p.m
    piv: list[int] = []
    r = 0
    for c in range(2 * n):
        if r == m:
            break
        col = p.x[:, c] if c < n else p.z[:, c - n]
        nz = np.flatnonzero(col[r:])
        if nz.size == 0:
            continue
        k = r + int(nz[0])
        if k != r:
            for arr in (p.x, p.z):
                arr[[r, k]] = arr[[k, r]]
            p.r[[r, k]] = p.r[[k, r]]
        col = p.x[:, c] if c < n else p.z[:, c - n]
        tgt = np.flatnonzero(col)
        tgt = tgt[tgt != r]
        mul_into(p, tgt, p.x[r].copy(), p.z[r].copy(), p.r[r])
        piv.append(c)
        r += 1
    return PauliRows(p.x[:r], p.z[:r], p.r[:r]), piv


def reduce_targets(basis_rref: PauliRows, pivots: list[int], targets: PauliRows) -> tuple[np.ndarray, np.ndarray]:
    """Reduce each target by an RREF basis.

    Returns (in_group, sign): in_group[t] is True iff targets[t] is a product of basis rows up to sign;
    sign[t] is the sign bit of that product relative to the target (0 means the target itself, with its sign,
    is in the group; 1 means -target is).
    """
    n = targets.n
    in_group = np.zeros(targets.m, dtype=bool)
    sign = np.zeros(targets.m, dtype=np.uint8)
    # a target anticommuting with any group element cannot be in the group
    ok = ~commutes(basis_rref, targets).any(axis=0) if basis_rref.m else np.ones(targets.m, dtype=bool)
    idx = np.flatnonzero(ok)
    t = PauliRows(targets.x[idx], targets.z[idx], targets.r[idx])
    for i, c in enumerate(pivots):
        col = t.x[:, c] if c < n else t.z[:, c - n]
        hit = np.flatnonzero(col)
        mul_into(t, hit, basis_rref.x[i], basis_rref.z[i], basis_rref.r[i])
    # after reduction a member became (+/-) identity: product * target = (-1)^r I  =>  product = (-1)^r target
    in_group[idx] = ~(t.x.any(axis=1) | t.z.any(axis=1))
    sign[idx] = t.r
    return in_group, sign


class Tableau:
    """Stabilizer rows of |0^n> propagated through Clifford gates.

    Storage: for every qubit j, x[j], z[j] are Python-int bitsets over the n rows (bit i = row i), r is a bitset of
    signs. Every gate is a handful of big-int operations, independent of stim."""

    def __init__(self, n: int):
        self.n = n
        self.full = (1 << n) - 1
        self.x = [0] * n
        self.z = [1 << j for j in range(n)]
        self.r = 0

    def rows(self) -> PauliRows:
        n = self.n
        x = np.zeros((n, n), dtype=np.uint8)
        z = np.zeros((n, n), dtype=np.uint8)
        for j in range(n):
            x[:, j] = _bits(self.x[j], n)
            z[:, j] = _bits(self.z[j], n)
        return PauliRows(x, z, _bits(self.r, n))

    # --- gates (conjugation P -> U P U^dagger), Aaronson–Gottesman update rules
    def h(self, a):
        xa, za = self.x[a], self.z[a]
        self.r ^= xa & za
        self.x[a], self.z[a] = za, xa

    def s(self, a):
        self.r ^= self.x[a] & self.z[a]
        self.z[a] ^= self.x[a]

    def sdg(self, a):
        self.r ^= self.x[a] & (self.z[a] ^ self.full)
        self.z[a] ^= self.x[a]

    def px(self, a):
        self.r ^= self.z[a]

    def pz(self, a):
        self.r ^= self.x[a]

    def py(self, a):
        self.r ^= self.x[a] ^ self.z[a]

    def cx(self, a, b):
        if a == b:
            raise ValueError("cx on identical qubits")
        xa, za, xb, zb = self.x[a], self.z[a], self.x[b], self.z[b]
        self.r ^= xa & zb & (xb ^ za ^ self.full)
        self.x[b] = xb ^ xa
        self.z[a] = za ^ zb

    def cz(self, a, b):
        self.h(b); self.cx(a, b); self.h(b)

    def cy(self, a, b):
        self.sdg(b); self.cx(a, b); self.s(b)

    def swap(self, a, b):
        if a == b:
            raise ValueError("swap on identical qubits")
        self.x[a], self.x[b] = self.x[b], self.x[a]
        self.z[a], self.z[b] = self.z[b], self.z[a]

    def sx(self, a):
        self.h(a); self.s(a); self.h(a)

    def sxdg(self, a):
        self.h(a); self.sdg(a); self.h(a)

    GATES = {"h": "h", "s": "s", "sdg": "sdg", "x": "px", "y": "py", "z": "pz", "cx": "cx", "cz": "cz",
             "cy": "cy", "swap": "swap", "sx": "sx", "sxdg": "sxdg"}

    def apply(self, name: str, qubits) -> None:
        if name == "id":
            return
        meth = self.GATES.get(name)
        if meth is None:
            raise ValueError(f"not a supported Clifford gate: {name}")
        getattr(self, meth)(*qubits)


def _bits(v: int, n: int) -> np.ndarray:
    """Bitset -> 0/1 uint8 array of length n (bit i -> entry i)."""
    if n == 0:
        return np.zeros(0, dtype=np.uint8)
    b = np.frombuffer(v.to_bytes((n + 7) // 8, "little"), dtype=np.uint8)
    return np.unpackbits(b, bitorder="little")[:n].copy()
