"""XOR-AND graphs (XAG) for low-T oracle compilation (Meuli, Soeken, Campbell, Roetteler, De Micheli,
"The role of multiplicative complexity in compiling low T-count oracle circuits", ICCAD 2019, arXiv:1908.01609).

An XAG here is kept in "linear normal form": a list of AND gates, each AND of two affine forms over the primary inputs
and earlier AND outputs, and per output an affine form. XOR costs nothing (CNOTs); every AND costs one Toffoli to
compute (and one to uncompute, unless it feeds an output only). The multiplicative complexity MC(f) is the minimum
number of ANDs; a reversible circuit with t Toffoli-like gates yields an XAG with t ANDs, so MC(f) is a lower bound on
the Toffoli count of any oracle for f, and the XAG construction gives an upper bound 2 MC(f) - 1 (single output).

- from_aig():    structural conversion AIG -> XAG normal form with XOR detection (AND(~AND(a,b), ~AND(~a,~b)) = a^b).
- exact_mc():    SAT-based exact synthesis of an MC-optimal XAG for a single-output function of n <= ~8 inputs
                 (searching k = lower bound, lower bound + 1, ...; every UNSAT answer proves that k ANDs do not suffice).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

# affine form: (frozenset of term ids, constant bit); term ids: ("x", i) primary input i, ("g", k) AND gate k


@dataclass
class XAG:
    n: int
    ands: list = field(default_factory=list)       # [(formA, formB)]
    outputs: list = field(default_factory=list)    # [form]

    @property
    def num_ands(self) -> int:
        return len(self.ands)

    def evaluate(self, x: np.ndarray) -> np.ndarray:
        """x: (N, n) bool array -> (N, m) bool outputs."""
        vals: dict = {("x", i): x[:, i] for i in range(self.n)}

        def form(f):
            terms, c = f
            v = np.full(x.shape[0], bool(c))
            for t in terms:
                v = v ^ vals[t]
            return v
        for k, (fa, fb) in enumerate(self.ands):
            vals[("g", k)] = form(fa) & form(fb)
        return np.stack([form(f) for f in self.outputs], axis=1)

    def truth_tables(self) -> np.ndarray:
        N = 1 << self.n
        x = ((np.arange(N)[:, None] >> np.arange(self.n)[None, :]) & 1).astype(bool)
        return self.evaluate(x).T

    def prune(self) -> "XAG":
        """Drop AND gates not reachable from the outputs; renumber."""
        used = set()
        stack = [t for f in self.outputs for t in f[0] if t[0] == "g"]
        while stack:
            t = stack.pop()
            if t in used:
                continue
            used.add(t)
            fa, fb = self.ands[t[1]]
            stack += [u for u in fa[0] | fb[0] if u[0] == "g"]
        keep = sorted(k for _, k in used)
        ren = {("g", old): ("g", new) for new, old in enumerate(keep)}

        def rf(f):
            return (frozenset(ren.get(t, t) for t in f[0]), f[1])
        return XAG(self.n, [(rf(self.ands[k][0]), rf(self.ands[k][1])) for k in keep], [rf(f) for f in self.outputs])


def _xor_forms(a, b):
    return (a[0] ^ b[0], a[1] ^ b[1])


def from_aig(aig) -> XAG:
    """AIG -> XAG normal form. Each AIG node becomes an affine form; AND nodes whose fanins are the complemented pair
    (AND(a,b), AND(~a,~b)) or (AND(a,~b), AND(~a,b)) are recognised as XOR / XNOR and cost no AND gate."""
    I = aig.num_inputs
    forms: dict = {0: (frozenset(), 0)}
    for i in range(I):
        forms[i + 1] = (frozenset([("x", i)]), 0)
    x = XAG(I)
    nodes = {I + 1 + j: (a, b) for j, (a, b) in enumerate(aig.ands)}

    def lit_form(l):
        f = forms[l >> 1]
        return (f[0], f[1] ^ (l & 1))
    for v in sorted(nodes):
        a, b = nodes[v]
        form = None
        if (a & 1) and (b & 1) and (a >> 1) in nodes and (b >> 1) in nodes:
            p, q = nodes[a >> 1], nodes[b >> 1]
            # v = ~(p0 & p1) & ~(q0 & q1); XOR pattern when {q0, q1} = {~p0, ~p1}
            if {q[0], q[1]} == {p[0] ^ 1, p[1] ^ 1}:
                f0, f1 = lit_form(p[0]), lit_form(p[1])
                form = _xor_forms(f0, f1)                       # ~(ab) & ~(~a~b) = a ^ b
            elif {q[0], q[1]} == {p[0] ^ 1, p[1]} and False:
                pass
        if form is None:
            fa, fb = lit_form(a), lit_form(b)
            x.ands.append((fa, fb))
            form = (frozenset([("g", len(x.ands) - 1)]), 0)
        forms[v] = form
    x.outputs = [lit_form(l) for l in aig.outputs]
    return x.prune()


def from_minmc_text(text: str) -> XAG:
    """Parse the XAG printed by the qbank driver around mockturtle (external/src/qbank_minmc/minmc.cpp):
    "pis n", then "g id and|xor a b" in topological order (signal = 2*node + complement; node 0 is the constant,
    nodes 1..n the primary inputs), then one "po sig" per output."""
    lines = [l.split() for l in text.splitlines() if l.strip()]
    if not lines or lines[0][0] != "pis":
        raise ValueError("minmc output: missing 'pis' header")
    n = int(lines[0][1])
    forms: dict = {0: (frozenset(), 0)}
    for i in range(n):
        forms[i + 1] = (frozenset([("x", i)]), 0)
    x = XAG(n)

    def sig(s):
        f = forms[int(s) >> 1]
        return (f[0], f[1] ^ (int(s) & 1))
    for l in lines[1:]:
        if l[0] == "g":
            fa, fb = sig(l[3]), sig(l[4])
            if l[2] == "xor":
                forms[int(l[1])] = _xor_forms(fa, fb)
            elif l[2] == "and":
                x.ands.append((fa, fb))
                forms[int(l[1])] = (frozenset([("g", len(x.ands) - 1)]), 0)
            else:
                raise ValueError(f"minmc output: unknown gate {l[2]}")
        elif l[0] == "po":
            x.outputs.append(sig(l[1]))
        else:
            raise ValueError(f"minmc output: bad line {' '.join(l)}")
    return x.prune()


# ------------------------------------------------------------------ exact multiplicative complexity (SAT)
def anf_degree(tt: np.ndarray, n: int) -> int:
    a = tt.astype(np.uint8).copy()
    for i in range(n):
        step = 1 << i
        for s in range(0, 1 << n, 2 * step):
            a[s + step: s + 2 * step] ^= a[s: s + step]
    return max((bin(u).count("1") for u in range(1 << n) if a[u]), default=0)


def _encode(tt: np.ndarray, n: int, k: int):
    from pysat.formula import IDPool
    pool = IDPool()
    cls = []
    N = 1 << n
    terms = lambda i: [("c",)] + [("x", j) for j in range(n)] + [("g", p) for p in range(i)]
    A = {(i, t): pool.id(("A", i, t)) for i in range(k) for t in terms(i)}
    Bv = {(i, t): pool.id(("B", i, t)) for i in range(k) for t in terms(i)}
    O = {t: pool.id(("O", t)) for t in terms(k)}
    G = {(i, s): pool.id(("G", i, s)) for i in range(k) for s in range(N)}
    ctr = [0]

    def fresh():
        ctr[0] += 1
        return pool.id(("aux", ctr[0]))

    def xor_chain(lits):
        """Return a literal equal to XOR of lits (lits: ints, may be empty -> None meaning constant 0)."""
        if not lits:
            return None
        cur = lits[0]
        for l in lits[1:]:
            y = fresh()
            cls.extend([[-y, cur, l], [-y, -cur, -l], [y, -cur, l], [y, cur, -l]])
            cur = y
        return cur

    def form_lit(S, i, s):
        """XOR over selected terms of gate i's form (selector dict S) at input s."""
        lits = []
        for t in terms(i):
            sel = S[(i, t)] if i < k else O[t]
            if t[0] == "c":
                lits.append(sel)
            elif t[0] == "x":
                if (s >> t[1]) & 1:
                    lits.append(sel)
            else:
                g = G[(t[1], s)]
                y = fresh()
                cls.extend([[-y, sel], [-y, g], [y, -sel, -g]])
                lits.append(y)
        return xor_chain(lits)
    for i in range(k):
        # symmetry breaking / non-degeneracy: both forms non-constant; gate i used later (or by the output)
        cls.append([A[(i, t)] for t in terms(i) if t[0] != "c"])
        cls.append([Bv[(i, t)] for t in terms(i) if t[0] != "c"])
        cls.append([A[(j, ("g", i))] for j in range(i + 1, k)] + [Bv[(j, ("g", i))] for j in range(i + 1, k)] + [O[("g", i)]])
        for s in range(N):
            la, lb = form_lit(A, i, s), form_lit(Bv, i, s)
            g = G[(i, s)]
            if la is None or lb is None:
                cls.append([-g])
                continue
            cls.extend([[-g, la], [-g, lb], [g, -la, -lb]])
    for s in range(N):
        lo = form_lit(None, k, s)
        want = bool(tt[s])
        if lo is None:
            if want:
                cls.append([])
            continue
        cls.append([lo] if want else [-lo])
    return cls, A, Bv, O, terms


def _decode(model, n, k, A, Bv, O, terms) -> XAG:
    m = set(x for x in model if x > 0)

    def tid(t):
        return ("x", t[1]) if t[0] == "x" else ("g", t[1])

    def form(sel_of, lst):
        ts = frozenset(tid(t) for t in lst if t[0] != "c" and sel_of(t) in m)
        c = int(any(t[0] == "c" and sel_of(t) in m for t in lst))
        return (ts, c)
    x = XAG(n)
    for i in range(k):
        x.ands.append((form(lambda t: A[(i, t)], terms(i)), form(lambda t: Bv[(i, t)], terms(i))))
    x.outputs = [form(lambda t: O[t], terms(k))]
    return x


def exact_mc_budget(tt: np.ndarray, n: int, conflicts_per_k: int, k_max: int = 12, give_up_after: int = 3):
    """Deterministic variant (v1.2): SAT with a conflict budget per AND count k, starting at deg(f) - 1.
    A k whose budget runs out is skipped (MC not proven); the search stops after `give_up_after` consecutive
    budget-outs. Returns (xag | None, k, proven)."""
    from .satutil import solve_budget
    deg = anf_degree(tt, n)
    if deg <= 1:
        a = tt.astype(np.uint8)
        c = int(a[0])
        return XAG(n, [], [(frozenset(("x", j) for j in range(n) if a[1 << j] ^ c), c)]), 0, True
    k = max(1, deg - 1)
    proven, misses = True, 0
    while k <= k_max:
        cls, A, Bv, O, terms = _encode(tt, n, k)
        st, model = solve_budget(cls, conflicts_per_k, want_model=True)
        if st == "sat":
            x = _decode(model, n, k, A, Bv, O, terms)
            if not np.array_equal(x.truth_tables()[0], tt.astype(bool)):
                raise RuntimeError("exact MC decode mismatch")
            return x, k, proven or k == max(1, deg - 1)
        if st == "budget":
            proven = False
            misses += 1
            if misses >= give_up_after:
                return None, k, False
        k += 1
    return None, k, False


def exact_mc(tt: np.ndarray, n: int, deadline: float, k_max: int = 12, per_k: float | None = None) -> tuple[XAG | None, int, bool]:
    """Returns (xag, k, proven): an XAG with k ANDs realising tt; proven = every smaller k was shown UNSAT (or k equals
    the degree lower bound deg(f) - 1). With per_k, a k whose SAT call times out is skipped (not proven) instead of
    ending the search -- for constructions that do not need a minimality proof."""
    from .satutil import solve_with_timeout
    deg = anf_degree(tt, n)
    k = max(0, deg - 1)
    proven = True
    while k <= k_max and time.monotonic() < deadline:
        if k == 0:
            # affine function?
            if deg <= 1:
                a = tt.astype(np.uint8)
                c = int(a[0])
                terms = frozenset(("x", j) for j in range(n) if a[1 << j] ^ c)
                return XAG(n, [], [(terms, c)]), 0, True
            k += 1
            continue
        cls, A, Bv, O, terms = _encode(tt, n, k)
        limit = deadline - time.monotonic()
        if per_k is not None:
            limit = min(limit, per_k)
        st, model = solve_with_timeout(cls, limit, want_model=True)
        if st == "sat":
            x = _decode(model, n, k, A, Bv, O, terms)
            if not np.array_equal(x.truth_tables()[0], tt.astype(bool)):
                raise RuntimeError("exact MC decode mismatch")
            return x, k, proven or k == max(0, deg - 1)
        if st == "timeout":
            if per_k is None or time.monotonic() >= deadline:
                return None, k, False              # MC(f) >= k (all smaller k proven UNSAT)
            proven = False
        k += 1
    return None, k, False


def _embed(x: XAG, n: int, var_map: list[int], and_offset: int):
    """Rename a sub-XAG (inputs 0..k-1 -> var_map) with AND ids shifted by and_offset; returns (ands, outputs)."""
    def rf(f):
        return (frozenset(("x", var_map[t[1]]) if t[0] == "x" else ("g", t[1] + and_offset) for t in f[0]), f[1])
    return [(rf(a), rf(b)) for a, b in x.ands], [rf(o) for o in x.outputs]


def _affine(tt: np.ndarray, n: int):
    """Affine form of tt if it is affine, else None."""
    a = tt.astype(np.uint8)
    c = int(a[0])
    terms = frozenset(("x", j) for j in range(n) if a[1 << j] ^ c)
    idx = np.arange(1 << n)
    val = np.full(1 << n, c, dtype=np.uint8)
    for t in terms:
        val ^= ((idx >> t[1]) & 1).astype(np.uint8)
    return (terms, c) if np.array_equal(val, a) else None


EXACT_CONFLICTS = 50000


def shannon_mc(tt: np.ndarray, n: int, deadline: float, exact_n: int = 5, cache: dict | None = None) -> XAG:
    """MC-aware synthesis for small n: exact MC for n <= exact_n; otherwise the best split f = f0 ^ x_v & (f0 ^ f1) over
    all variables v, recursing on the cofactors (AND count <= MC(f0) + MC(f0 ^ f1) + 1). Deterministic since v1.2: the
    exact search uses a SAT conflict budget (EXACT_CONFLICTS per AND count) and every split is examined; `deadline`
    is ignored."""
    cache = {} if cache is None else cache
    key = (n, tt.astype(np.uint8).tobytes())
    if key in cache:
        return cache[key]
    aff = _affine(tt, n)
    if aff is not None:
        res = XAG(n, [], [aff])
    elif n <= exact_n:
        x, k, _ = exact_mc_budget(tt, n, EXACT_CONFLICTS)          # deterministic (v1.2): no wall-clock slices
        if x is None and n > 3:
            x = shannon_mc(tt, n, deadline, exact_n=n - 1, cache=cache)
        if x is None:
            raise RuntimeError("exact MC: conflict budget exhausted")
        res = x
    else:
        best = None
        idx = np.arange(1 << n)
        for v in range(n):
            rest = [j for j in range(n) if j != v]
            sub = np.array([sum(((s >> i) & 1) << rest[i] for i in range(n - 1)) for s in range(1 << (n - 1))])
            f0, f1 = tt[sub], tt[sub | (1 << v)]
            d = f0 ^ f1
            x0 = shannon_mc(f0, n - 1, deadline, exact_n, cache)
            xd = shannon_mc(d, n - 1, deadline, exact_n, cache)
            cost = x0.num_ands + xd.num_ands + (0 if _affine(d, n - 1) is not None and not d.any() else 1)
            if best is None or cost < best[0]:
                best = (cost, v, rest, x0, xd, d)
        _, v, rest, x0, xd, d = best
        res = XAG(n)
        a0, o0 = _embed(x0, n, rest, 0)
        ad, od = _embed(xd, n, rest, len(a0))
        res.ands = a0 + ad
        if not d.any():
            res.outputs = [o0[0]]
        else:
            res.ands.append(((frozenset([("x", v)]), 0), od[0]))
            g = ("g", len(res.ands) - 1)
            res.outputs = [(o0[0][0] ^ frozenset([g]), o0[0][1])]
        res = res.prune()
    cache[key] = res
    return res
