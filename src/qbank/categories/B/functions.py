"""Boolean-function generators for category B. Every generator returns (AIG, params, meta).

Input bit i is AIG input i. Multi-output functions list outputs in a fixed documented order.
"""
from __future__ import annotations

import itertools

import numpy as np

from ...core.aig import AIG


# ------------------------------------------------------------------ random 3-SAT
def random_3sat(nv: int, alpha: float, rng: np.random.Generator):
    m = int(round(alpha * nv))
    clauses = []
    for _ in range(m):
        vs = rng.choice(nv, 3, replace=False)
        clauses.append([int(v + 1) * (1 if rng.random() < 0.5 else -1) for v in vs])
    return clauses


def cnf_to_aig(nv: int, clauses) -> AIG:
    g = AIG(nv, input_names=[f"v{i + 1}" for i in range(nv)])
    cl = []
    for c in clauses:
        cl.append(g.OR_n([g.input_lit(abs(l) - 1) ^ (1 if l < 0 else 0) for l in c]))
    g.add_output(g.AND_n(cl), "sat")
    return g.cleanup()


def is_satisfiable(nv: int, clauses) -> bool:
    from pysat.solvers import Solver
    with Solver(name="cadical195", bootstrap_with=clauses) as s:
        return bool(s.solve())


def gen_3sat(nv: int, alpha: float, rng):
    clauses = random_3sat(nv, alpha, rng)
    return cnf_to_aig(nv, clauses), {"n_vars": nv, "alpha": alpha, "n_clauses": len(clauses)}, \
        {"clauses": clauses, "satisfiable": is_satisfiable(nv, clauses)}


# ------------------------------------------------------------------ triangle detection (QCircuitBench grover_triangle, parametrised)
def gen_triangle(v: int, rng, p: float = 0.5):
    """Fixed random graph G(v, p); input = vertex-subset indicator; f(S) = 1 iff S is exactly a triangle of G."""
    edges = {(i, j) for i in range(v) for j in range(i + 1, v) if rng.random() < p}
    tris = [t for t in itertools.combinations(range(v), 3) if all(e in edges for e in itertools.combinations(t, 2))]
    g = AIG(v, input_names=[f"s{i}" for i in range(v)])
    xs = [g.input_lit(i) for i in range(v)]
    # exactly-three via "at least 3" and "not at least 4" would be larger; OR over triangles of (all three in, rest out)
    terms = []
    for t in tris:
        inside = [xs[i] for i in t]
        outside = [xs[i] ^ 1 for i in range(v) if i not in t]
        terms.append(g.AND(g.AND_n(inside), g.AND_n(outside)))
    g.add_output(g.OR_n(terms) if terms else 0, "is_triangle")
    return g.cleanup(), {"v": v, "p": p}, {"edges": sorted(map(list, edges)), "n_triangles": len(tris)}


# ------------------------------------------------------------------ comparators / equality
def _bits(g, off, w):
    return [g.input_lit(off + i) for i in range(w)]   # little-endian


def less_than(g, a, b):
    """a < b for little-endian bit lists."""
    lt = 0
    eq = 1
    for i in reversed(range(len(a))):         # from MSB
        lt = g.OR(lt, g.AND(eq, g.AND(a[i] ^ 1, b[i])))
        eq = g.AND(eq, g.XOR(a[i], b[i]) ^ 1)
    return lt


def gen_compare(kind: str, w: int, rng=None):
    if kind == "lt":
        g = AIG(2 * w, input_names=[f"a{i}" for i in range(w)] + [f"b{i}" for i in range(w)])
        g.add_output(less_than(g, _bits(g, 0, w), _bits(g, w, w)), "a_lt_b")
        return g.cleanup(), {"kind": "lt", "w": w}, {}
    if kind == "eq":
        g = AIG(2 * w, input_names=[f"a{i}" for i in range(w)] + [f"b{i}" for i in range(w)])
        a, b = _bits(g, 0, w), _bits(g, w, w)
        g.add_output(g.AND_n([g.XOR(a[i], b[i]) ^ 1 for i in range(w)]), "a_eq_b")
        return g.cleanup(), {"kind": "eq", "w": w}, {}
    if kind == "eq_const":
        n = 2 * w       # same input width as the other kinds
        c = sum(int(bit) << i for i, bit in enumerate(rng.integers(0, 2, size=n)))   # n may exceed 63 bits
        g = AIG(n, input_names=[f"a{i}" for i in range(n)])
        g.add_output(g.AND_n([g.input_lit(i) ^ (0 if (c >> i) & 1 else 1) for i in range(n)]), "a_eq_c")
        return g.cleanup(), {"kind": "eq_const", "w": w, "const": c}, {}
    raise ValueError(kind)


# ------------------------------------------------------------------ small arithmetic
def gen_arith(kind: str, w: int):
    if kind == "carry":       # carry-out of a + b (w-bit each)
        g = AIG(2 * w, input_names=[f"a{i}" for i in range(w)] + [f"b{i}" for i in range(w)])
        a, b = _bits(g, 0, w), _bits(g, w, w)
        c = 0
        for i in range(w):
            c = g.MAJ(a[i], b[i], c)
        g.add_output(c, "carry")
        return g.cleanup(), {"kind": "carry", "w": w}, {}
    if kind == "prod_parity":  # parity of all bits of a*b (w-bit each)
        g = AIG(2 * w, input_names=[f"a{i}" for i in range(w)] + [f"b{i}" for i in range(w)])
        a, b = _bits(g, 0, w), _bits(g, w, w)
        acc = [0] * (2 * w)
        for i in range(w):                      # shift-and-add multiplier
            carry = 0
            for j in range(w):
                pp = g.AND(a[j], b[i])
                s = g.XOR(g.XOR(acc[i + j], pp), carry)
                carry = g.MAJ(acc[i + j], pp, carry)
                acc[i + j] = s
            k = i + w
            while carry != 0 and k < 2 * w:
                s = g.XOR(acc[k], carry)
                carry = g.AND(acc[k], carry)
                acc[k] = s
                k += 1
        g.add_output(g.XOR_n(acc), "parity_of_product")
        return g.cleanup(), {"kind": "prod_parity", "w": w}, {}
    if kind == "majority":     # majority of n = w inputs (w odd)
        n = w
        g = AIG(n, input_names=[f"x{i}" for i in range(n)])
        xs = [g.input_lit(i) for i in range(n)]
        # popcount >= (n+1)/2 via a ripple counter
        cnt = []
        for x in xs:
            carry = x
            for k in range(len(cnt)):
                s = g.XOR(cnt[k], carry)
                carry = g.AND(cnt[k], carry)
                cnt[k] = s
            if carry != 0:
                cnt.append(carry)
        thr = (n + 1) // 2
        # cnt >= thr  <=>  not (cnt < thr)
        tb = [(thr >> i) & 1 for i in range(len(cnt))]
        lt = less_than(g, cnt, [1 if b else 0 for b in tb])
        g.add_output(lt ^ 1, "majority")
        return g.cleanup(), {"kind": "majority", "n": n}, {}
    raise ValueError(kind)


# ------------------------------------------------------------------ 4x4 Sudoku with k blanks (QCircuitBench grover_sudoku, parametrised)
def _latin_4x4(rng):
    base = np.array([[0, 1, 2, 3], [2, 3, 0, 1], [1, 0, 3, 2], [3, 2, 1, 0]])
    perm = rng.permutation(4)
    g = perm[base]
    rows = [0, 1] if rng.random() < .5 else [1, 0]
    rows2 = [2, 3] if rng.random() < .5 else [3, 2]
    g = g[rows + rows2]
    cols = [0, 1] if rng.random() < .5 else [1, 0]
    cols2 = [2, 3] if rng.random() < .5 else [3, 2]
    return g[:, cols + cols2]


def gen_sudoku(k: int, rng):
    """Valid 4x4 Sudoku with k blank cells; each blank = 2 input bits (value 0..3); f = 1 iff all constraints hold."""
    sol = _latin_4x4(rng)
    cells = [(r, c) for r in range(4) for c in range(4)]
    blanks = [cells[i] for i in sorted(rng.choice(16, k, replace=False))]
    g = AIG(2 * k, input_names=[f"cell{r}{c}_b{b}" for (r, c) in blanks for b in range(2)])
    val = {}
    for (r, c) in cells:
        if (r, c) in blanks:
            j = blanks.index((r, c))
            val[(r, c)] = ("var", g.input_lit(2 * j), g.input_lit(2 * j + 1))
        else:
            val[(r, c)] = ("const", int(sol[r, c]))

    def neq(u, v):
        if u[0] == "const" and v[0] == "const":
            return 1 if u[1] != v[1] else 0
        if u[0] == "const":
            u, v = v, u
        if v[0] == "const":
            v0, v1 = v[1] & 1, (v[1] >> 1) & 1
            return g.OR(u[1] ^ v0, u[2] ^ v1)          # bit differs from the constant bit
        return g.OR(g.XOR(u[1], v[1]), g.XOR(u[2], v[2]))
    groups = [[(r, c) for c in range(4)] for r in range(4)] + [[(r, c) for r in range(4)] for c in range(4)] + \
             [[(br + i, bc + j) for i in range(2) for j in range(2)] for br in (0, 2) for bc in (0, 2)]
    cons = []
    for grp in groups:
        for u, v in itertools.combinations(grp, 2):
            cons.append(neq(val[u], val[v]))
    g.add_output(g.AND_n(cons), "valid")
    return g.cleanup(), {"k": k}, {"solution": sol.tolist(), "blanks": [list(b) for b in blanks]}


# ------------------------------------------------------------------ ternary generalized Simon oracle
def gen_simon3(n: int, r: int, rng):
    """f: Z_3^n -> Z_3^n, f(x) = M x (mod 3) with ker M of dimension r (the hidden subgroup).
    Each trit = 2 bits (t = b0 + 2 b1 mod 3; the code 11 is read as 0). Outputs: 2 bits per output trit."""
    while True:
        # random M of rank n - r: rows spanned by n - r random independent rows
        basis = rng.integers(0, 3, size=(n - r, n))
        if _rank3(basis) == n - r:
            break
    mix = rng.integers(0, 3, size=(n, n - r))
    M = (mix @ basis) % 3
    g = AIG(2 * n, input_names=[f"x{i}_b{b}" for i in range(n) for b in range(2)])
    # trit value as one-hot (t==1, t==2); code 11 -> 0
    one = []
    two = []
    for i in range(n):
        b0, b1 = g.input_lit(2 * i), g.input_lit(2 * i + 1)
        one.append(g.AND(b0, b1 ^ 1))
        two.append(g.AND(b1, b0 ^ 1))
    for j in range(n):
        # sum_i M[j,i]*t_i mod 3 with a mod-3 accumulator in one-hot form (is1, is2)
        is1, is2 = 0, 0
        for i in range(n):
            c = int(M[j, i])
            if c == 0:
                continue
            a1, a2 = (one[i], two[i]) if c == 1 else (two[i], one[i])   # contribution c*t_i
            # (acc + a) mod 3 in one-hot
            is0 = g.AND(is1 ^ 1, is2 ^ 1)
            a0 = g.AND(a1 ^ 1, a2 ^ 1)
            n1 = g.OR_n([g.AND(is0, a1), g.AND(is1, a0), g.AND(is2, a2)])
            n2 = g.OR_n([g.AND(is0, a2), g.AND(is2, a0), g.AND(is1, a1)])
            is1, is2 = n1, n2
        g.add_output(is1, f"f{j}_b0")
        g.add_output(is2, f"f{j}_b1")
    return g.cleanup(), {"n_trits": n, "r": r}, {"M": M.tolist()}


def _rank3(A) -> int:
    A = np.array(A, dtype=np.int64) % 3
    r = 0
    rows, cols = A.shape
    for c in range(cols):
        piv = next((i for i in range(r, rows) if A[i, c] % 3), None)
        if piv is None:
            continue
        A[[r, piv]] = A[[piv, r]]
        inv = 1 if A[r, c] == 1 else 2
        A[r] = (A[r] * inv) % 3
        for i in range(rows):
            if i != r and A[i, c]:
                A[i] = (A[i] - A[i, c] * A[r]) % 3
        r += 1
        if r == rows:
            break
    return r


# ------------------------------------------------------------------ generalized Sudoku (4x4 with 2x2 boxes, 6x6 with 2x3 boxes)
def _sudoku_solution(size: int, rng) -> np.ndarray:
    a, b = (2, 2) if size == 4 else (2, 3)          # box: a rows x b columns
    grid = np.array([[(b * (r % a) + r // a + c) % size for c in range(size)] for r in range(size)])
    grid = rng.permutation(size)[grid]              # relabel digits
    bands = [list(range(i * a, (i + 1) * a)) for i in range(size // a)]
    rows = [r for band in rng.permutation(len(bands)) for r in rng.permutation(bands[band])]
    stacks = [list(range(j * b, (j + 1) * b)) for j in range(size // b)]
    cols = [c for st in rng.permutation(len(stacks)) for c in rng.permutation(stacks[st])]
    grid = grid[rows][:, cols]
    assert _sudoku_valid(grid, size), "internal: invalid Sudoku solution"
    return grid


def _sudoku_groups(size: int):
    a, b = (2, 2) if size == 4 else (2, 3)
    rows = [[(r, c) for c in range(size)] for r in range(size)]
    cols = [[(r, c) for r in range(size)] for c in range(size)]
    boxes = [[(br + i, bc + j) for i in range(a) for j in range(b)] for br in range(0, size, a) for bc in range(0, size, b)]
    return rows + cols + boxes


def _sudoku_valid(grid, size) -> bool:
    return all(len({int(grid[r][c]) for r, c in g}) == size for g in _sudoku_groups(size)) and bool((np.asarray(grid) < size).all())


def gen_sudoku_n(size: int, k: int, rng):
    """size x size Sudoku (4 or 6) with k blank cells; each blank = ceil(log2 size) input bits (codes >= size invalid);
    f = 1 iff every blank holds a valid digit and all row/column/box constraints hold."""
    bits = 2 if size == 4 else 3
    sol = _sudoku_solution(size, rng)
    cells = [(r, c) for r in range(size) for c in range(size)]
    blanks = [cells[i] for i in sorted(rng.choice(size * size, k, replace=False))]
    g = AIG(bits * k, input_names=[f"cell{r}{c}_b{t}" for (r, c) in blanks for t in range(bits)])
    val = {}
    valid_code = []
    for (r, c) in cells:
        if (r, c) in blanks:
            j = blanks.index((r, c))
            lits = [g.input_lit(bits * j + t) for t in range(bits)]
            val[(r, c)] = ("var", lits)
            if size == 6:            # codes 6 (110) and 7 (111) are invalid: not(b1 and b2)
                valid_code.append(g.AND(lits[1], lits[2]) ^ 1)
        else:
            val[(r, c)] = ("const", int(sol[r, c]))

    def neq(u, v):
        if u[0] == "const" and v[0] == "const":
            return 1 if u[1] != v[1] else 0
        if u[0] == "const":
            u, v = v, u
        if v[0] == "const":
            return g.OR_n([u[1][t] ^ ((v[1] >> t) & 1) for t in range(bits)])
        return g.OR_n([g.XOR(u[1][t], v[1][t]) for t in range(bits)])
    cons = list(valid_code)
    for grp in _sudoku_groups(size):
        for u, v in itertools.combinations(grp, 2):
            cons.append(neq(val[u], val[v]))
    g.add_output(g.AND_n(cons), "valid")
    return g.cleanup(), {"size": size, "k": k}, {"solution": sol.tolist(), "blanks": [list(b) for b in blanks]}


# ------------------------------------------------------------------ v1.3 (10-28): parametrised structural sub-types
# Single-output functions with a free parameter, so that one input width carries many functions that are not
# equivalent under input negation / permutation and output negation (task-pack v2: structural test instances inside
# the training size range). Input bit i is AIG input i (little-endian numbers).
def _const_bits(c: int, n: int) -> list[int]:
    return [(c >> i) & 1 for i in range(n)]       # AIG constant literals 0 / 1


def gen_lt_const(n: int, c: int):
    """f(a) = [a < c] for an n-bit number a and a constant 0 < c < 2^n."""
    g = AIG(n, input_names=[f"a{i}" for i in range(n)])
    g.add_output(less_than(g, _bits(g, 0, n), _const_bits(c, n)), "a_lt_c")
    return g.cleanup(), {"kind": "lt_const", "n": n, "c": c}, {}


def gen_interval(n: int, c1: int, c2: int):
    """f(a) = [c1 <= a < c2] for an n-bit number a and constants 0 < c1 < c2 < 2^n."""
    g = AIG(n, input_names=[f"a{i}" for i in range(n)])
    a = _bits(g, 0, n)
    g.add_output(g.AND(less_than(g, a, _const_bits(c1, n)) ^ 1, less_than(g, a, _const_bits(c2, n))), "c1_le_a_lt_c2")
    return g.cleanup(), {"kind": "interval", "n": n, "c1": c1, "c2": c2}, {}


def _popcount(g, xs):
    cnt = []
    for x in xs:                                   # ripple counter (as in gen_arith "majority")
        carry = x
        for k in range(len(cnt)):
            s = g.XOR(cnt[k], carry)
            carry = g.AND(cnt[k], carry)
            cnt[k] = s
        if carry != 0:
            cnt.append(carry)
    return cnt


def gen_threshold(n: int, k: int):
    """f(x) = [popcount(x) >= k] (k = (n + 1) / 2 for odd n is the existing "majority" kind)."""
    g = AIG(n, input_names=[f"x{i}" for i in range(n)])
    cnt = _popcount(g, [g.input_lit(i) for i in range(n)])
    lt = less_than(g, cnt, _const_bits(k, len(cnt)))
    g.add_output(lt ^ 1, "popcount_ge_k")
    return g.cleanup(), {"kind": "threshold", "n": n, "k": k}, {}


def gen_mul_bit(w: int, j: int):
    """f(a, b) = bit j of the product a * b of two w-bit numbers (shift-and-add multiplier as in "prod_parity")."""
    g = AIG(2 * w, input_names=[f"a{i}" for i in range(w)] + [f"b{i}" for i in range(w)])
    a, b = _bits(g, 0, w), _bits(g, w, w)
    acc = [0] * (2 * w)
    for i in range(w):
        carry = 0
        for jj in range(w):
            pp = g.AND(a[jj], b[i])
            s = g.XOR(g.XOR(acc[i + jj], pp), carry)
            carry = g.MAJ(acc[i + jj], pp, carry)
            acc[i + jj] = s
        kk = i + w
        while carry != 0 and kk < 2 * w:
            s = g.XOR(acc[kk], carry)
            carry = g.AND(acc[kk], carry)
            acc[kk] = s
            kk += 1
    g.add_output(acc[j], f"product_bit{j}")
    return g.cleanup(), {"kind": "mul_bit", "w": w, "j": j}, {}
