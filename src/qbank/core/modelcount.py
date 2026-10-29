"""Exact model counting for single-output AIGs (v1.2, used to classify B instances as solution-sparse by the fraction
of satisfying inputs): a small reduced ordered BDD without complement edges, variables ordered by first visit in a
depth-first walk from the output (keeps bit-sliced functions such as comparators, adders and majority small).

bdd_count(aig) returns the exact number of inputs with f(x) = 1, or None if the BDD grows beyond `max_nodes`.
"""
from __future__ import annotations


class _BDD:
    def __init__(self, nvars: int, max_nodes: int):
        self.nvars = nvars
        self.max_nodes = max_nodes
        self.node = [(nvars, 0, 0), (nvars, 1, 1)]      # 0 = false, 1 = true (level nvars = terminal)
        self.unique: dict = {}
        self.memo: dict = {}

    def mk(self, lvl: int, lo: int, hi: int) -> int:
        if lo == hi:
            return lo
        key = (lvl, lo, hi)
        u = self.unique.get(key)
        if u is None:
            if len(self.node) >= self.max_nodes:
                raise MemoryError("BDD node limit")
            u = len(self.node)
            self.node.append(key)
            self.unique[key] = u
        return u

    def var(self, lvl: int) -> int:
        return self.mk(lvl, 0, 1)

    def apply(self, op: str, u: int, v: int) -> int:
        if op == "and":
            if u == 0 or v == 0:
                return 0
            if u == 1:
                return v
            if v == 1 or u == v:
                return u
        else:                                              # xor
            if u == 0:
                return v
            if v == 0:
                return u
            if u == v:
                return 0
        if u > v:
            u, v = v, u
        key = (op, u, v)
        r = self.memo.get(key)
        if r is not None:
            return r
        lu, lv = self.node[u][0], self.node[v][0]
        lvl = min(lu, lv)
        u0, u1 = (self.node[u][1], self.node[u][2]) if lu == lvl else (u, u)
        v0, v1 = (self.node[v][1], self.node[v][2]) if lv == lvl else (v, v)
        r = self.mk(lvl, self.apply(op, u0, v0), self.apply(op, u1, v1))
        self.memo[key] = r
        return r

    def neg(self, u: int) -> int:
        return self.apply("xor", u, 1)

    def count(self, root: int) -> int:
        """Number of assignments to all nvars variables that reach terminal 1."""
        memo = {0: 0, 1: 1}

        def rec(u):                                        # models over the variables at levels >= level(u)
            if u in memo:
                return memo[u]
            lvl, lo, hi = self.node[u]
            r = rec(lo) * (1 << (self.node[lo][0] - lvl - 1)) + rec(hi) * (1 << (self.node[hi][0] - lvl - 1))
            memo[u] = r
            return r
        import sys
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old, 10 * self.nvars + 1000))
        try:
            return rec(root) * (1 << self.node[root][0])
        finally:
            sys.setrecursionlimit(old)


def _dfs_input_order(aig) -> list[int]:
    I = aig.num_inputs
    ands = {I + 1 + j: ab for j, ab in enumerate(aig.ands)}
    order, seen, stack = [], set(), [aig.outputs[0] >> 1]
    while stack:
        v = stack.pop()
        if v in seen or v == 0:
            continue
        seen.add(v)
        if v <= I:
            order.append(v - 1)
            continue
        a, b = ands[v]
        stack += [b >> 1, a >> 1]                          # visit the first fan-in first
    order += [i for i in range(I) if i not in set(order)]  # inputs the function does not depend on
    return order


def bdd_count(aig, max_nodes: int = 2_000_000) -> int | None:
    if len(aig.outputs) != 1:
        raise ValueError("single-output AIG expected")
    I = aig.num_inputs
    order = _dfs_input_order(aig)
    level = {v: k for k, v in enumerate(order)}
    bdd = _BDD(I, max_nodes)
    try:
        f = {0: 0}
        for i in range(I):
            f[i + 1] = bdd.var(level[i])

        def lit(l):
            u = f[l >> 1]
            return bdd.neg(u) if l & 1 else u
        for j, (a, b) in enumerate(aig.ands):
            f[I + 1 + j] = bdd.apply("and", lit(a), lit(b))
        return bdd.count(lit(aig.outputs[0]))
    except MemoryError:
        return None
