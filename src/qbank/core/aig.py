"""And-Inverter Graphs for category B (Boolean functions stored as AIGER).

Literals follow AIGER: variable v has literals 2v (positive) and 2v+1 (negated); literal 0 = false, 1 = true.
Inputs are variables 1..I, AND gates follow in topological order. Only combinational AIGs (no latches).
Binary AIGER is used on disk because ABC's `read` does not accept ASCII .aag files (Phase 0).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class AIG:
    num_inputs: int
    ands: list[tuple[int, int]] = field(default_factory=list)   # (rhs0, rhs1) for variables I+1, I+2, ...
    outputs: list[int] = field(default_factory=list)            # literals
    input_names: list[str] = field(default_factory=list)
    output_names: list[str] = field(default_factory=list)
    _strash: dict = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------ building
    @property
    def max_var(self) -> int:
        return self.num_inputs + len(self.ands)

    def input_lit(self, i: int) -> int:
        return 2 * (i + 1)

    def AND(self, a: int, b: int) -> int:
        if a > b:
            a, b = b, a
        if a == 0:
            return 0
        if a == 1:
            return b
        if a == b:
            return a
        if a ^ 1 == b:
            return 0
        key = (a, b)
        v = self._strash.get(key)
        if v is None:
            self.ands.append(key)
            v = 2 * self.max_var
            self._strash[key] = v
        return v

    @staticmethod
    def NOT(a: int) -> int:
        return a ^ 1

    def OR(self, a: int, b: int) -> int:
        return self.AND(a ^ 1, b ^ 1) ^ 1

    def XOR(self, a: int, b: int) -> int:
        return self.OR(self.AND(a, b ^ 1), self.AND(a ^ 1, b))

    def AND_n(self, lits) -> int:
        lits = list(lits)
        if not lits:
            return 1
        while len(lits) > 1:   # balanced tree
            nxt = [self.AND(lits[i], lits[i + 1]) for i in range(0, len(lits) - 1, 2)]
            if len(lits) % 2:
                nxt.append(lits[-1])
            lits = nxt
        return lits[0]

    def OR_n(self, lits) -> int:
        return self.AND_n([l ^ 1 for l in lits]) ^ 1

    def XOR_n(self, lits) -> int:
        lits = list(lits)
        if not lits:
            return 0
        while len(lits) > 1:
            nxt = [self.XOR(lits[i], lits[i + 1]) for i in range(0, len(lits) - 1, 2)]
            if len(lits) % 2:
                nxt.append(lits[-1])
            lits = nxt
        return lits[0]

    def MAJ(self, a, b, c) -> int:
        return self.OR(self.AND(a, b), self.AND(c, self.OR(a, b)))

    def add_output(self, lit: int, name: str = "") -> None:
        self.outputs.append(lit)
        self.output_names.append(name or f"y{len(self.outputs) - 1}")

    # ------------------------------------------------------------------ cleanup / canonical form
    def cleanup(self) -> "AIG":
        """Keep only ANDs in the transitive fan-in of the outputs; renumber in topological order (deterministic)."""
        need = set()
        stack = [l >> 1 for l in self.outputs]
        I = self.num_inputs
        while stack:
            v = stack.pop()
            if v <= I or v in need:
                continue
            need.add(v)
            a, b = self.ands[v - I - 1]
            stack += [a >> 1, b >> 1]
        new = AIG(I, input_names=list(self.input_names))
        remap = {0: 0, **{v: v for v in range(1, I + 1)}}

        def m(l):
            return 2 * remap[l >> 1] + (l & 1)
        for v in range(I + 1, self.max_var + 1):
            if v in need:
                a, b = self.ands[v - I - 1]
                lit = new.AND(m(a), m(b))
                remap[v] = lit >> 1
                if lit & 1:
                    raise AssertionError("AND of normalised operands cannot be negated")
        for l, nm in zip(self.outputs, self.output_names):
            new.add_output(m(l), nm)
        return new

    # ------------------------------------------------------------------ evaluation
    def simulate(self, inputs: np.ndarray) -> np.ndarray:
        """inputs: (num_inputs, W) uint64 bit-parallel patterns -> (num_outputs, W) uint64."""
        W = inputs.shape[1]
        vals = np.zeros((self.max_var + 1, W), dtype=np.uint64)
        vals[1:self.num_inputs + 1] = inputs
        ones = np.uint64(0xFFFFFFFFFFFFFFFF)

        def lit(l):
            v = vals[l >> 1]
            return v ^ ones if l & 1 else v
        I = self.num_inputs
        for k, (a, b) in enumerate(self.ands):
            vals[I + 1 + k] = lit(a) & lit(b)
        return np.stack([lit(l) for l in self.outputs]) if self.outputs else np.zeros((0, W), np.uint64)

    @staticmethod
    def input_patterns(n: int) -> np.ndarray:
        """(n, W) uint64: bit (x mod 64) of word (x // 64) of row i equals bit i of x, for x in [0, 2^n)."""
        W = max(1, (1 << n) // 64)
        masks = [0xAAAAAAAAAAAAAAAA, 0xCCCCCCCCCCCCCCCC, 0xF0F0F0F0F0F0F0F0, 0xFF00FF00FF00FF00,
                 0xFFFF0000FFFF0000, 0xFFFFFFFF00000000]
        pats = np.zeros((n, W), dtype=np.uint64)
        w = np.arange(W, dtype=np.uint64)
        for i in range(n):
            if i < 6:
                pats[i] = np.uint64(masks[i])
            else:
                pats[i] = np.where((w >> np.uint64(i - 6)) & np.uint64(1), np.uint64(0xFFFFFFFFFFFFFFFF), np.uint64(0))
        return pats

    @staticmethod
    def unpack(words: np.ndarray, N: int) -> np.ndarray:
        """(k, W) uint64 -> (k, N) uint8 using the same bit order as input_patterns."""
        b = np.unpackbits(np.ascontiguousarray(words).astype("<u8").view(np.uint8), axis=-1, bitorder="little")
        return b[..., :N]

    def truth_tables(self) -> np.ndarray:
        """All 2^n input patterns (n <= 24): (num_outputs, 2^n) uint8; column x is input assignment x (bit i = input i)."""
        n = self.num_inputs
        if n > 24:
            raise ValueError("truth table too large")
        return self.unpack(self.simulate(self.input_patterns(n)), 1 << n)

    def eval(self, x: int) -> list[int]:
        n = self.num_inputs
        vals = [0] * (self.max_var + 1)
        for i in range(n):
            vals[i + 1] = (x >> i) & 1
        lv = lambda l: vals[l >> 1] ^ (l & 1)
        for k, (a, b) in enumerate(self.ands):
            vals[n + 1 + k] = lv(a) & lv(b)
        return [lv(l) for l in self.outputs]

    # ------------------------------------------------------------------ AIGER I/O
    def to_aiger_binary(self) -> bytes:
        """Binary AIGER ('aig M I L O A') with symbol table."""
        a = self.cleanup() if not self._is_clean() else self
        M, I, O, A = a.max_var, a.num_inputs, len(a.outputs), len(a.ands)
        out = bytearray(f"aig {M} {I} 0 {O} {A}\n".encode())
        for l in a.outputs:
            out += f"{l}\n".encode()
        for k, (r0, r1) in enumerate(a.ands):
            lhs = 2 * (I + 1 + k)
            r0, r1 = max(r0, r1), min(r0, r1)
            for delta in (lhs - r0, r0 - r1):
                while delta & ~0x7F:
                    out.append((delta & 0x7F) | 0x80)
                    delta >>= 7
                out.append(delta)
        for i, nm in enumerate(a.input_names or [f"x{i}" for i in range(I)]):
            out += f"i{i} {nm}\n".encode()
        for i, nm in enumerate(a.output_names):
            out += f"o{i} {nm}\n".encode()
        return bytes(out)

    def _is_clean(self) -> bool:
        return all(max(a, b) < 2 * (self.num_inputs + 1 + k) for k, (a, b) in enumerate(self.ands))

    @staticmethod
    def from_aiger(data: bytes) -> "AIG":
        """Read binary ('aig') or ASCII ('aag') combinational AIGER."""
        hdr_end = data.index(b"\n")
        hdr = data[:hdr_end].decode().split()
        kind, M, I, L, O, A = hdr[0], *map(int, hdr[1:6])
        if L:
            raise ValueError("latches are not supported (combinational AIGs only)")
        pos = hdr_end + 1
        lines = data[pos:].split(b"\n")
        g = AIG(I)
        if kind == "aag":
            k = 0
            ins = [int(lines[k + i]) for i in range(I)]
            k += I
            outs = [int(lines[k + i]) for i in range(O)]
            k += O
            defs = {}
            for i in range(A):
                l, a, b = map(int, lines[k + i].split())
                defs[l >> 1] = (a, b)
            k += A
            if ins != [2 * (i + 1) for i in range(I)]:
                raise ValueError("non-standard input numbering")
            remap = {0: 0, **{i + 1: i + 1 for i in range(I)}}
            for v in sorted(defs):
                a, b = defs[v]
                lit = g.AND(2 * remap[a >> 1] + (a & 1), 2 * remap[b >> 1] + (b & 1))
                remap[v] = lit >> 1
                if lit & 1:
                    raise ValueError("unsupported AIG structure")
            g.outputs = [2 * remap[o >> 1] + (o & 1) for o in outs]
            sym_lines = lines[k:]
        else:
            outs = []
            for i in range(O):
                outs.append(int(lines[i]))
            # binary AND section starts after the O output lines
            off = pos + sum(len(lines[i]) + 1 for i in range(O))
            buf = data[off:]
            p = 0
            for k in range(A):
                lhs = 2 * (I + 1 + k)
                ds = []
                for _ in range(2):
                    x, sh = 0, 0
                    while True:
                        c = buf[p]
                        p += 1
                        x |= (c & 0x7F) << sh
                        if not c & 0x80:
                            break
                        sh += 7
                    ds.append(x)
                r0 = lhs - ds[0]
                r1 = r0 - ds[1]
                g.ands.append((r1, r0))
                g._strash[(min(r0, r1), max(r0, r1))] = lhs
            g.outputs = outs
            sym_lines = buf[p:].split(b"\n")
        g.output_names = [f"y{i}" for i in range(O)]
        g.input_names = [f"x{i}" for i in range(I)]
        for ln in sym_lines:
            s = ln.decode(errors="replace")
            if s.startswith("c"):
                break
            if len(s) > 1 and s[0] in "io" and " " in s:
                t, name = s.split(" ", 1)
                j = int(t[1:])
                (g.input_names if s[0] == "i" else g.output_names)[j] = name
        return g
