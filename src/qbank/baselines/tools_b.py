"""Category-B baseline tools. Every tool returns circuits in qbank.contracts.oracle.GATE_SET_B.

Register layout: inputs 0..n-1, outputs n..n+m-1 (bit-flip oracles) and ancillas after; phase oracles have no
output register. Tools only see the public part of an instance.
"""
from __future__ import annotations

import base64
import os
import subprocess
import tempfile
import time

import numpy as np

from ..core.aig import AIG
from ..core.circuit import Circuit
from ..core.instance import PKG_ROOT

ABC = str(PKG_ROOT / "external" / "src" / "abc" / "abc")
# ABC's resyn2 script (abc.rc alias "b; rw; rf; b; rw; rwz; b; rfz; rwz; b") spelled out with real command names,
# because abc.rc is not loaded; preceded by strash and dc2.
ABC_RESYN2 = ("strash; dc2; balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; "
              "rewrite -z; balance")


class NeedQubits(Exception):
    """The construction does not fit into the qubit budget."""


def load_aig(public: dict) -> AIG:
    return AIG.from_aiger(base64.b64decode(public["aiger_b64"]))


def abc_optimize(aig: AIG, script: str = ABC_RESYN2, timeout: float = 30) -> AIG:
    with tempfile.TemporaryDirectory() as d:
        p, q = os.path.join(d, "in.aig"), os.path.join(d, "out.aig")
        open(p, "wb").write(aig.to_aiger_binary())
        r = subprocess.run([ABC, "-c", f"read {p}; {script}; write_aiger -s {q}"], capture_output=True, text=True,
                           timeout=timeout, cwd=d)
        if "error" in r.stdout.lower() or r.returncode != 0 or not os.path.exists(q):
            raise RuntimeError(f"ABC failed: {r.stdout[-300:]}")
        out = AIG.from_aiger(open(q, "rb").read())
    out.input_names, out.output_names = list(aig.input_names), list(aig.output_names)
    return out


# ------------------------------------------------------------------ helpers
class Builder:
    def __init__(self, n: int, m: int, kind: str, budget: int | None):
        self.n, self.m, self.kind, self.budget = n, m, kind, budget
        self.width = n + (m if kind == "bitflip" else 0)
        self.free: list[int] = []
        self.gates: list = []

    def alloc(self) -> int:
        if self.free:
            return self.free.pop()
        if self.budget is not None and self.width + 1 > self.budget:
            raise NeedQubits(f"needs more than {self.budget} qubits")
        self.width += 1
        return self.width - 1

    def release(self, q: int) -> None:
        self.free.append(q)

    def g(self, name, qs, params=()):
        self.gates.append((name, tuple(qs), tuple(params)))

    def circuit(self) -> Circuit:
        c = Circuit(self.width)
        for name, qs, p in self.gates:
            c.append(name, qs, p)
        return c


def _and_nodes(aig: AIG):
    I = aig.num_inputs
    return [(I + 1 + j, a, b) for j, (a, b) in enumerate(aig.ands)]


def _emit_and(B: Builder, qa, pa, qb, pb, t, style: str):
    """t ^= (qa xor pa) & (qb xor pb), with t a clean ancilla for 'rccx'/'gidney' styles."""
    for q, p in ((qa, pa), (qb, pb)):
        if p:
            B.g("x", [q])
    if style == "ccx":
        B.g("ccx", [qa, qb, t])
    elif style == "gidney":      # RCCX onto |0> + S^dagger: exact AND with 4 T (target must be |0>)
        B.g("rccx", [qa, qb, t])
        B.g("sdg", [t])
    else:
        raise ValueError(style)
    for q, p in ((qa, pa), (qb, pb)):
        if p:
            B.g("x", [q])


def _unemit_and(B: Builder, qa, pa, qb, pb, t, style: str):
    for q, p in ((qa, pa), (qb, pb)):
        if p:
            B.g("x", [q])
    if style == "ccx":
        B.g("ccx", [qa, qb, t])
    elif style == "mbu":          # measurement-based uncompute of t = a&b: X-measure t, CZ(a, b) if outcome 1
        B.g("mbu", [t], [(("cz", (qa, qb)),)])
    for q, p in ((qa, pa), (qb, pb)):
        if p:
            B.g("x", [q])


def _copy_out(B: Builder, lit_q, lit_neg, j, phase_tmp=None):
    if B.kind == "bitflip":
        tgt = B.n + j
        if lit_q is None:            # constant output
            if lit_neg:
                B.g("x", [tgt])
            return
        B.g("cx", [lit_q, tgt])
        if lit_neg:
            B.g("x", [tgt])
    else:
        if lit_q is None:
            return                   # constant: global phase only
        if lit_neg:
            B.g("x", [lit_q])
        B.g("z", [lit_q])
        if lit_neg:
            B.g("x", [lit_q])


# ------------------------------------------------------------------ Bennett (compute all AND nodes, copy, uncompute)
def bennett(aig: AIG, kind: str, budget=None, compute="ccx", uncompute="ccx") -> Circuit:
    n, m = aig.num_inputs, len(aig.outputs)
    if kind == "phase" and m != 1:
        raise NotImplementedError("phase oracles have a single output")
    B = Builder(n, m, kind, budget)
    q_of = {i + 1: i for i in range(n)}
    order = []
    for v, a, b in _and_nodes(aig):
        t = B.alloc()
        q_of[v] = t
        order.append((q_of[a >> 1], a & 1, q_of[b >> 1], b & 1, t))
        _emit_and(B, *order[-1], compute)
    for j, l in enumerate(aig.outputs):
        _copy_out(B, q_of[l >> 1] if l >> 1 else None, l & 1, j)
    for args in reversed(order):
        _unemit_and(B, *args, uncompute)
    return B.circuit()


def cone_bennett(aig: AIG, kind: str, budget=None, compute="ccx", uncompute="ccx") -> Circuit:
    """Output by output: compute the output's fan-in cone, copy, uncompute (reuses ancillas between outputs)."""
    n, m = aig.num_inputs, len(aig.outputs)
    if kind == "phase" and m != 1:
        raise NotImplementedError("phase oracles have a single output")
    B = Builder(n, m, kind, budget)
    I = aig.num_inputs
    for j, l in enumerate(aig.outputs):
        cone = set()
        stack = [l >> 1]
        while stack:
            v = stack.pop()
            if v <= I or v in cone:
                continue
            cone.add(v)
            a, b = aig.ands[v - I - 1]
            stack += [a >> 1, b >> 1]
        q_of = {i + 1: i for i in range(n)}
        order = []
        for v in sorted(cone):
            a, b = aig.ands[v - I - 1]
            t = B.alloc()
            q_of[v] = t
            order.append((q_of[a >> 1], a & 1, q_of[b >> 1], b & 1, t))
            _emit_and(B, *order[-1], compute)
        _copy_out(B, q_of[l >> 1] if l >> 1 else None, l & 1, j)
        for args in reversed(order):
            _unemit_and(B, *args, uncompute)
            B.release(args[-1])
    return B.circuit()


# ------------------------------------------------------------------ MCX via Qiskit's Toffoli-level syntheses
MCX_CHOICES = ("synth_mcx_n_clean_m15", "synth_mcx_2_clean_kg24", "synth_mcx_1_clean_kg24", "synth_mcx_2_dirty_kg24",
               "synth_mcx_1_dirty_kg24")
_MCX_CACHE: dict = {}


def _mcx_template(fn: str, k: int):
    key = (fn, k)
    if key not in _MCX_CACHE:
        import qiskit.synthesis as qs
        qc = getattr(qs, fn)(k)
        gates = []
        for inst in qc.data:
            gates.append((inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits)))
        tof = sum(1 for g, _ in gates if g in ("ccx", "rccx")) + 2 * sum(1 for g, _ in gates if g == "rc3x")
        _MCX_CACHE[key] = (qc.num_qubits - k - 1, gates, tof)
    return _MCX_CACHE[key]


def emit_mcx(B: Builder, controls: list[tuple[int, int]], target: int, busy: set[int]) -> str:
    """target ^= AND_i (q_i xor neg_i). Chooses the cheapest (Toffoli count) Qiskit construction that fits the budget;
    dirty variants borrow idle register/ancilla lines."""
    k = len(controls)
    for q, neg in controls:
        if neg:
            B.g("x", [q])
    ctl = [q for q, _ in controls]
    if k == 0:
        B.g("x", [target])
    elif k == 1:
        B.g("cx", [ctl[0], target])
    elif k == 2:
        B.g("ccx", [ctl[0], ctl[1], target])
    else:
        options = []
        for fn in MCX_CHOICES:
            n_anc, gates, tof = _mcx_template(fn, k)
            options.append((tof, fn, n_anc, gates))
        options.sort()
        used = set(ctl) | {target} | busy
        chosen = None
        for tof, fn, n_anc, gates in options:
            if "dirty" in fn:
                idle = [q for q in range(B.width) if q not in used]
                anc = idle[:n_anc]
                extra = n_anc - len(anc)
                try:
                    anc += [B.alloc() for _ in range(extra)]
                except NeedQubits:
                    continue
                chosen = (fn, gates, anc, anc[len(anc) - extra:] if extra else [])
                break
            try:
                anc = [B.alloc() for _ in range(n_anc)]
            except NeedQubits:
                continue
            chosen = (fn, gates, anc, anc)
            break
        if chosen is None:
            raise NeedQubits("no MCX construction fits the budget")
        fn, gates, anc, to_release = chosen
        qmap = ctl + [target] + anc
        for g, qs in gates:
            B.g(g, [qmap[q] for q in qs])
        for q in to_release:
            B.release(q)
    for q, neg in controls:
        if neg:
            B.g("x", [q])
    return "ok"


# ------------------------------------------------------------------ ESOP (Qiskit EsopGenerator) with MCX per cube
class _TT:
    def __init__(self, tt_row, n):
        self.row, self.num_bits = tt_row, n

    def __getitem__(self, assignment):
        x = 0
        for i, b in enumerate(assignment):
            x |= int(bool(b)) << i
        return bool(self.row[x])


def esop_cubes(aig: AIG, deadline: float) -> list[list[str]]:
    from qiskit.synthesis.boolean.boolean_expression_synth import EsopGenerator
    if aig.num_inputs > 16:
        raise NotImplementedError("ESOP from the full truth table only for <= 16 inputs (Qiskit warns above 16)")
    tt = aig.truth_tables()
    out = []
    for j in range(len(aig.outputs)):
        if time.monotonic() > deadline:
            raise TimeoutError("ESOP generation exceeded the budget")
        out.append(EsopGenerator(_TT(tt[j], aig.num_inputs)).esop)
    return out


def esop_oracle(aig: AIG, kind: str, budget, deadline) -> Circuit:
    n, m = aig.num_inputs, len(aig.outputs)
    if kind == "phase" and m != 1:
        raise NotImplementedError("phase oracles have a single output")
    cubes = esop_cubes(aig, deadline)
    B = Builder(n, m, kind, budget)
    if kind == "phase":
        t = B.alloc()
    for j, cs in enumerate(cubes):
        tgt = n + j if kind == "bitflip" else t
        for cube in cs:
            controls = [(i, 0 if ch == "1" else 1) for i, ch in enumerate(cube) if ch != "-"]
            emit_mcx(B, controls, tgt, busy=set())
    if kind == "phase":
        B.g("z", [t])
        for cube in reversed(cubes[0]):
            controls = [(i, 0 if ch == "1" else 1) for i, ch in enumerate(cube) if ch != "-"]
            emit_mcx(B, controls, t, busy=set())
    return B.circuit()


# ------------------------------------------------------------------ per-clause MCX for CNF-shaped functions
def extract_cnf(aig: AIG):
    """If the single output is an AND of ORs of input literals, return the clause list (as in DIMACS); else None."""
    if len(aig.outputs) != 1:
        return None
    I = aig.num_inputs

    def conj(l):   # flatten a positive AND tree into literals
        if l & 1 or (l >> 1) <= I:
            return [l]
        a, b = aig.ands[(l >> 1) - I - 1]
        return conj(a) + conj(b)

    def lits_of_or(l):   # l = NOT(AND(not a, not b, ...)) -> input literals
        if (l >> 1) <= I:
            return [l]
        if not l & 1:
            return None
        parts = conj(l ^ 1)
        out = []
        for p in parts:
            p = p ^ 1
            if (p >> 1) <= I:
                out.append(p)
            else:
                sub = lits_of_or(p)
                if sub is None:
                    return None
                out += sub
        return out
    clauses = []
    for c in conj(aig.outputs[0]):
        ls = lits_of_or(c)
        if ls is None:
            return None
        clauses.append([((l >> 1)) * (-1 if l & 1 else 1) for l in ls])
    return clauses


def clause_oracle(aig: AIG, kind: str, budget) -> Circuit:
    clauses = extract_cnf(aig)
    if clauses is None:
        raise NotImplementedError("function is not given as a CNF (AND of ORs)")
    n = aig.num_inputs
    B = Builder(n, 1, kind, budget)
    cq = []
    for cl in clauses:          # clause ancilla = NOT(AND of negated literals)
        a = B.alloc()
        cq.append(a)
        emit_mcx(B, [(abs(l) - 1, 1 if l > 0 else 0) for l in cl], a, busy=set(cq))
        B.g("x", [a])
    tgt = n if kind == "bitflip" else B.alloc()
    emit_mcx(B, [(q, 0) for q in cq], tgt, busy=set(cq))
    if kind == "phase":
        B.g("z", [tgt])
        emit_mcx(B, [(q, 0) for q in cq], tgt, busy=set(cq))
    for a, cl in reversed(list(zip(cq, clauses))):
        B.g("x", [a])
        emit_mcx(B, [(abs(l) - 1, 1 if l > 0 else 0) for l in cl], a, busy=set(cq))
    return B.circuit()


# ------------------------------------------------------------------ tool table
def _budget(public, track):
    return public["tracks"][track].get("qubit_budget")


def _kind(public):
    return "bitflip" if public["task"] == "oracle_bitflip_clean" else "phase"


def _mbu_track(public, track):
    return public["tracks"][track].get("mbu_allowed", False)


def t_bennett(public, track, seed, deadline, optimize=False, cone=False):
    aig = load_aig(public)
    if optimize:
        aig = abc_optimize(aig)
    fn = cone_bennett if cone else bennett
    kind, budget = _kind(public), _budget(public, track)
    out = [{"circuit": fn(aig, kind, budget), "meta": {"abc": ABC_RESYN2 if optimize else None}}]
    if _mbu_track(public, track):
        out.append({"circuit": fn(aig, kind, budget, compute="gidney", uncompute="mbu"),
                    "meta": {"abc": ABC_RESYN2 if optimize else None, "and": "RCCX+Sdg compute, measurement-based uncompute"}})
    return out


def t_esop(public, track, seed, deadline):
    return [{"circuit": esop_oracle(load_aig(public), _kind(public), _budget(public, track), deadline),
             "meta": {"esop": "qiskit EsopGenerator", "mcx": "cheapest fitting of " + ", ".join(MCX_CHOICES)}}]


def t_clause(public, track, seed, deadline):
    return [{"circuit": clause_oracle(load_aig(public), _kind(public), _budget(public, track)),
             "meta": {"mcx": "cheapest fitting of " + ", ".join(MCX_CHOICES)}}]


B_TOOLS = {
    "bennett(aig)": lambda p, t, s, d: t_bennett(p, t, s, d),
    "bennett(abc resyn2)": lambda p, t, s, d: t_bennett(p, t, s, d, optimize=True),
    "cone_bennett(abc resyn2)": lambda p, t, s, d: t_bennett(p, t, s, d, optimize=True, cone=True),
    "esop(qiskit EsopGenerator)+qiskit MCX": t_esop,
    "per-clause MCX (qiskit MCX)": t_clause,
}


def tool_fn(tool):
    fn = B_TOOLS[tool]

    def run(public, track, seed, deadline):
        try:
            return fn(public, track, seed, deadline)
        except NeedQubits as e:
            raise NotImplementedError(f"does not fit the qubit budget: {e}")
    return run


# ------------------------------------------------------------------ SAT-based reversible pebbling (Meuli et al., DATE 2019)
PEBBLE_CONFLICTS = 1000000   # per SAT call while searching for the first feasible schedule (deterministic, v1.2)
PEBBLE_CONFLICTS_TIGHTEN = 100000   # per SAT call in the binary search that tightens the step count
PEBBLE_MAX_STEPS = 10         # binary-search steps after the first feasible schedule


def pebbling_schedule(aig: AIG, max_pebbles: int, deadline: float, t_max: int | None = None):
    """Re-implementation of the SAT pebbling formulation of Meuli, Soeken, Roetteler, Bjorner, De Micheli,
    "Reversible Pebbling Game for Quantum Memory Management", arXiv:1904.02121: one pebble move per step, a pebble on
    node v may be placed/removed only while both fan-ins are pebbled (inputs are always available), at most
    `max_pebbles` pebbles at any time, start with none, end with exactly the output nodes pebbled.
    Search over the number of steps T: start at the lower bound 2|cone| - |outputs|, grow geometrically until SAT, then
    binary-search down for at most PEBBLE_MAX_STEPS steps. Every SAT call has a conflict budget (PEBBLE_CONFLICTS while
    looking for the first feasible schedule, PEBBLE_CONFLICTS_TIGHTEN in the binary search)
    (v1.2: deterministic -- the same instance gives the same schedule on any machine and under any load; before v1.2
    the calls were bounded by wall-clock slices). Returns the toggled nodes of the compute phase, or None."""
    import threading
    from pysat.card import CardEnc, EncType
    from pysat.formula import IDPool
    from pysat.solvers import Solver
    I = aig.num_inputs
    outs = sorted({l >> 1 for l in aig.outputs if (l >> 1) > I})
    kids = {v: [c for c in ((a >> 1), (b >> 1)) if c > I] for v, a, b in _and_nodes(aig)}
    if len(outs) > max_pebbles:
        return None
    need = set()
    stack = list(outs)
    while stack:
        v = stack.pop()
        if v in need:
            continue
        need.add(v)
        stack += kids[v]
    nodes = sorted(need)
    if not nodes:
        return []

    def solve(T, conflicts=None):
        pool = IDPool()
        P = lambda v, t: pool.id(("p", v, t))
        D = lambda v, t: pool.id(("d", v, t))
        cls = []
        for v in nodes:
            cls.append([-P(v, 0)])
            cls.append([P(v, T)] if v in outs else [-P(v, T)])
        for t in range(T):
            for v in nodes:
                a, b, d = P(v, t), P(v, t + 1), D(v, t)
                cls += [[-d, a, b], [-d, -a, -b], [d, -a, b], [d, a, -b]]      # d <-> (a xor b)
                for c in kids[v]:
                    cls += [[-d, P(c, t)], [-d, P(c, t + 1)]]
            cls += CardEnc.atmost([D(v, t) for v in nodes], bound=1, vpool=pool, encoding=EncType.seqcounter).clauses
        if max_pebbles < len(nodes):
            for t in range(1, T):
                cls += CardEnc.atmost([P(v, t) for v in nodes], bound=max_pebbles, vpool=pool, encoding=EncType.seqcounter).clauses
        from ..core.satutil import solve_budget
        status, model = solve_budget(cls, conflicts or PEBBLE_CONFLICTS, want_model=True)   # deterministic (v1.2)
        if status == "budget":
            return "timeout"
        if status == "unsat":
            return None
        model = set(x for x in model if x > 0)
        return [v for t in range(T) for v in nodes if D(v, t) in model]

    lo = 2 * len(nodes) - len(outs)
    t_max = t_max or 12 * len(nodes) + 8
    # steps without a move are allowed, so a generous T is found feasible quickly; the move count is then tightened
    T, best, last_unsat = min(t_max, max(lo, 3 * len(nodes))), None, lo - 1
    timed_out = False
    while T <= t_max:
        r = solve(T)
        if r == "timeout":
            timed_out = True
            break
        if r is None:
            last_unsat = T
            T = T + max(1, T // 2)
            continue
        best = r
        break
    if best is None:
        if timed_out:
            raise TimeoutError(f"no pebbling schedule with {max_pebbles} pebbles within the SAT conflict budget "
                               f"({PEBBLE_CONFLICTS} conflicts per call)")
        return None                 # UNSAT for every T up to t_max
    hi = len(best)
    steps = 0
    while hi - last_unsat > 1 and steps < PEBBLE_MAX_STEPS:        # tighten: a fixed number of binary-search steps
        steps += 1
        mid = (hi + last_unsat) // 2
        r = solve(mid, PEBBLE_CONFLICTS_TIGHTEN)
        if r == "timeout":
            break
        if r is None:
            last_unsat = mid
        else:
            best, hi = r, len(r)
    # peephole: drop immediately repeated toggles of the same node (they cancel)
    out = []
    for v in best:
        if out and out[-1] == v:
            out.pop()
        else:
            out.append(v)
    return out


def pebbling_oracle(aig: AIG, kind: str, budget: int, deadline: float) -> tuple[Circuit, dict]:
    n, m = aig.num_inputs, len(aig.outputs)
    if kind == "phase" and m != 1:
        raise NotImplementedError("phase oracles have a single output")
    reg = n + (m if kind == "bitflip" else 0)
    K = (budget - reg) if budget is not None else len(aig.ands)
    if K < 0:
        raise NeedQubits("budget below register size")
    moves = pebbling_schedule(aig, K, deadline)
    if moves is None:
        raise NotImplementedError(f"no pebbling schedule with {K} pebbles exists up to the step bound (UNSAT)")
    B = Builder(n, m, kind, budget)
    I = aig.num_inputs
    q_of = {i + 1: i for i in range(n)}
    on = {}
    def toggle(v):
        a, b = aig.ands[v - I - 1]
        if v in on:
            t = on.pop(v)
            _unemit_and(B, q_of_node(a, on), a & 1, q_of_node(b, on), b & 1, t, "ccx")
            B.release(t)
        else:
            t = B.alloc()
            _emit_and(B, q_of_node(a, on), a & 1, q_of_node(b, on), b & 1, t, "ccx")
            on[v] = t

    def q_of_node(l, on_):
        v = l >> 1
        return v - 1 if v <= I else on_[v]
    for v in moves:
        toggle(v)
    for j, l in enumerate(aig.outputs):
        v = l >> 1
        _copy_out(B, (v - 1 if v <= I else on[v]) if v else None, l & 1, j)
    for v in reversed(moves):
        toggle(v)
    return B.circuit(), {"pebbles": K, "compute_moves": len(moves)}


def t_pebble(public, track, seed, deadline):
    aig = abc_optimize(load_aig(public))
    if len(aig.ands) > 400:
        raise NotImplementedError("SAT pebbling limited to <= 400 AND nodes")
    # v1.2: the search is bounded by SAT conflict budgets and a fixed number of steps (deterministic); the wall-clock
    # budget is enforced only by the runner
    c, meta = pebbling_oracle(aig, _kind(public), _budget(public, track), deadline)
    return [{"circuit": c, "meta": {**meta, "method": "SAT pebbling re-implemented after arXiv:1904.02121 (Meuli et al. 2019)"}}]


B_TOOLS["pebbling SAT (Meuli et al. 2019, re-impl.)"] = t_pebble


# ------------------------------------------------------------------ XAG compilation (Meuli et al., ICCAD 2019)
def xag_oracle(x, kind: str, m: int, budget=None, compute="ccx", uncompute="ccx") -> Circuit:
    """Compile an XAG in linear normal form (core/xag.py): every AND gate = one Toffoli onto a fresh ancilla, its two
    affine input forms are accumulated with CNOTs into temporary ancillas (or used directly when a form is a single
    literal), outputs are affine forms applied with CNOTs (bit-flip) or Z/CZ (phase). An AND used only by one output is
    applied directly onto that output (bit-flip: 1 Toffoli; phase: a CZ between the two forms, no Toffoli).
    Toffoli count = 2 * #internal ANDs + #output-only ANDs (bit-flip)."""
    n = x.n
    if kind == "phase" and m != 1:
        raise NotImplementedError("phase oracles have a single output")
    B = Builder(n, m, kind, budget)
    q_of: dict = {("x", i): i for i in range(n)}
    users = {k: [] for k in range(x.num_ands)}
    for k, (fa, fb) in enumerate(x.ands):
        for t in fa[0] | fb[0]:
            if t[0] == "g":
                users[t[1]].append(("and", k))
    for j, f in enumerate(x.outputs):
        for t in f[0]:
            if t[0] == "g":
                users[t[1]].append(("out", j))
    out_only = {k: u[0][1] for k, u in users.items() if len(u) == 1 and u[0][0] == "out"}

    def load(form):
        """Return (qubit, negated, temp) holding the affine form; temp is an ancilla to unload afterwards."""
        terms, c = form
        ts = sorted(terms)
        if len(ts) == 1:
            return q_of[ts[0]], c, None
        t = B.alloc()
        for u in ts:
            B.g("cx", [q_of[u], t])
        return t, c, (t, ts)

    def unload(tmp):
        if tmp is None:
            return
        t, ts = tmp
        for u in reversed(ts):
            B.g("cx", [q_of[u], t])
        B.release(t)

    computed = []
    for k, (fa, fb) in enumerate(x.ands):
        if k in out_only:
            continue
        qa, pa, ta = load(fa)
        qb, pb, tb = load(fb)
        if len(fa[0]) == 0 or len(fb[0]) == 0:
            raise RuntimeError("constant AND input")
        t = B.alloc()
        _emit_and(B, qa, pa, qb, pb, t, compute)
        unload(tb)
        unload(ta)
        q_of[("g", k)] = t
        computed.append(k)
    for j, (terms, c) in enumerate(x.outputs):
        for k in sorted(kk for kk, jj in out_only.items() if jj == j):
            fa, fb = x.ands[k]
            qa, pa, ta = load(fa)
            qb, pb, tb = load(fb)
            for q, p in ((qa, pa), (qb, pb)):
                if p:
                    B.g("x", [q])
            if kind == "bitflip":
                B.g("ccx", [qa, qb, n + j])
            else:
                B.g("cz", [qa, qb])
            for q, p in ((qa, pa), (qb, pb)):
                if p:
                    B.g("x", [q])
            unload(tb)
            unload(ta)
        for t in sorted(terms):
            if t[0] == "g" and t[1] in out_only:
                continue
            if kind == "bitflip":
                B.g("cx", [q_of[t], n + j])
            else:
                B.g("z", [q_of[t]])
        if c and kind == "bitflip":
            B.g("x", [n + j])                    # phase oracle: a constant term is a global phase
    for k in reversed(computed):
        fa, fb = x.ands[k]
        qa, pa, ta = load(fa)
        qb, pb, tb = load(fb)
        _unemit_and(B, qa, pa, qb, pb, q_of[("g", k)], uncompute)
        unload(tb)
        unload(ta)
        B.release(q_of[("g", k)])
    return B.circuit()


def build_xag(aig: AIG, deadline: float):
    """n <= 6: exact MC-optimal XAG (n <= 5) or best Shannon split with exact 5-input cofactors (n = 6), per output
    (deterministic: SAT conflict budgets, no wall-clock limits);
    otherwise (or if that is not smaller) structural XOR extraction on the ABC-optimised AIG. Returns (xag, info)."""
    from ..core.xag import XAG, exact_mc, from_aig
    n, m = aig.num_inputs, len(aig.outputs)
    base = from_aig(abc_optimize(aig))
    info = {"structural_ands": base.num_ands}
    if n <= 6:
        from ..core.xag import shannon_mc
        tts = aig.truth_tables()
        parts = []
        cache: dict = {}
        for j in range(m):
            try:
                xj = shannon_mc(tts[j], n, 0.0, cache=cache)
            except RuntimeError:
                break
            if not np.array_equal(xj.truth_tables()[0], tts[j].astype(bool)):
                raise RuntimeError("XAG synthesis mismatch")
            parts.append((xj, n <= 5))
        if len(parts) == m:
            # merge single-output XAGs (ANDs renumbered per output)
            merged = XAG(n)
            for xj, _ in parts:
                off = merged.num_ands
                ren = lambda f: (frozenset(("g", t[1] + off) if t[0] == "g" else t for t in f[0]), f[1])
                merged.ands += [(ren(a), ren(b)) for a, b in xj.ands]
                merged.outputs.append(ren(xj.outputs[0]))
            if merged.num_ands < base.num_ands:
                info.update(exact_mc_per_output=[p[0].num_ands for p in parts], proven=[p[1] for p in parts])
                return merged, {**info, "method": "exact MC (SAT) for n <= 5, else best Shannon split with exact 5-input "
                                                  "cofactors, per output"}
    return base, {**info, "method": "structural XOR extraction on ABC resyn2 AIG"}


def t_xag(public, track, seed, deadline):
    aig = load_aig(public)
    kind = _kind(public)
    x, info = build_xag(aig, deadline - 5)
    mbu = bool(public["tracks"][track].get("mbu_allowed"))
    cands = [{"circuit": xag_oracle(x, kind, len(aig.outputs), _budget(public, track)),
              "meta": {**info, "ands": x.num_ands, "compile": "ccx/ccx"}}]
    if mbu:
        cands.append({"circuit": xag_oracle(x, kind, len(aig.outputs), _budget(public, track), "gidney", "mbu"),
                      "meta": {**info, "ands": x.num_ands, "compile": "logical-AND (4 T) / measurement-based uncompute"}})
    return cands


B_TOOLS["XAG + MC (Meuli et al. 2019, re-impl.)"] = t_xag


# ------------------------------------------------------------------ v1.2: MC-oriented XAG cut rewriting (mockturtle)
MINMC_BIN = PKG_ROOT / "external" / "src" / "qbank_minmc" / "minmc"          # built by env/build_minmc.sh
MINMC_DB6 = PKG_ROOT / ".cache" / "external" / "minmc" / "db6.txt"
MINMC_ROUNDS = 10          # rewriting rounds (stops earlier when a round gives no improvement)
# cut_limit: mockturtle's default 25; on some networks this commit's cut rewriting then trips the assertion
# "visited(n) != trav_id() - 1" in topo_view (a cycle); the driver exits with code 70+signal and the run is repeated
# with cut_limit 12 (deterministic: the same network always takes the same path)
MINMC_CUT_LIMITS = (25, 12)


def minmc_rewrite(aig: AIG, cut_size: int, deadline: float) -> "XAG":
    """Run mockturtle's MC-oriented cut rewriting (Testa, Soeken, Riener, Amaru, De Micheli, "A Logic Synthesis
    Toolbox for Reducing the Multiplicative Complexity in Logic Networks", DATE 2020) on the AIG. Deterministic; the
    wall-clock deadline only aborts the run (TimeoutError), it never changes the result."""
    import os
    import subprocess
    import tempfile
    from ..core.xag import from_minmc_text
    if not MINMC_BIN.exists():
        raise NotImplementedError("minmc driver not built (env/build_minmc.sh)")
    db = str(MINMC_DB6) if cut_size == 6 else "-"
    if cut_size == 6 and not MINMC_DB6.exists():
        raise NotImplementedError("6-input minimum-MC database not built (env/build_minmc.sh)")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "in.aig")
        open(p, "wb").write(aig.to_aiger_binary())
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("minmc: out of time")
        # last resort (0 rounds): no cut rewriting, only the whole-function resynthesis for <= 6 inputs (otherwise
        # the XAG of the input as it is); used when the topo_view assertion also fires with cut_limit 12
        for cut_limit, rounds in [(cl, MINMC_ROUNDS) for cl in MINMC_CUT_LIMITS] + [(MINMC_CUT_LIMITS[-1], 0)]:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError("minmc: out of time")
            try:
                r = subprocess.run([str(MINMC_BIN), p, str(cut_size), db, str(rounds), str(cut_limit)],
                                   capture_output=True, text=True, timeout=left, cwd=d)
            except subprocess.TimeoutExpired:
                raise TimeoutError("minmc: out of time")
            if not (70 <= r.returncode < 80 and "topo_view" in r.stderr):
                break
    if r.returncode != 0:
        raise RuntimeError(f"minmc failed ({r.returncode}): {r.stderr[-300:]}")
    x = from_minmc_text(r.stdout)
    stats = dict(l.split() for l in r.stderr.splitlines() if len(l.split()) == 2)
    x.minmc_stats = {**{k: int(v) for k, v in stats.items() if v.isdigit()}, "cut_limit": cut_limit, "rounds": rounds}
    return x


MINMC_VARIANTS = (("abc resyn2", 6), ("abc resyn2", 5), ("as given", 5))


def build_xag_minmc(aig: AIG, deadline: float):
    """Best of three deterministic runs (start network, cut size): (ABC-optimised AIG, 6 with the 6-input database),
    (ABC-optimised AIG, 5 with mockturtle's embedded database), (AIG as given, 5); fewest AND gates, ties broken by
    that order. (A sweep over all B v1.1 instances: the fourth combination, AIG as given with cut size 6, was the
    unique best on 1 of 428 instances but took 38 % of the total time, so it is not run.)"""
    starts = {"abc resyn2": abc_optimize(aig), "as given": aig}
    best, info = None, None
    tt = aig.truth_tables() if aig.num_inputs <= 16 else None
    for sname, cs in MINMC_VARIANTS:
        x = minmc_rewrite(starts[sname], cs, deadline)
        if tt is not None and not np.array_equal(x.truth_tables(), tt.astype(bool)):
            raise RuntimeError("minmc result differs from the function")
        if best is None or x.num_ands < best.num_ands:
            best, info = x, {"start": sname, "cut_size": cs, **getattr(x, "minmc_stats", {})}
    return best, info


def t_minmc(public, track, seed, deadline):
    aig = load_aig(public)
    kind = _kind(public)
    x, info = build_xag_minmc(aig, deadline - 5)
    meta = {**info, "ands": x.num_ands, "method": "mockturtle cut_rewriting_with_compatibility_graph + minimum-MC "
                                                  "resynthesis (<= 6-input cuts), mc_cost"}
    cands = [{"circuit": xag_oracle(x, kind, len(aig.outputs), _budget(public, track)), "meta": {**meta, "compile": "ccx/ccx"}}]
    if public["tracks"][track].get("mbu_allowed"):
        cands.append({"circuit": xag_oracle(x, kind, len(aig.outputs), _budget(public, track), "gidney", "mbu"),
                      "meta": {**meta, "compile": "logical-AND (4 T) / measurement-based uncompute"}})
    return cands


B_TOOLS["XAG MC cut rewriting (mockturtle xag_minmc_resynthesis)"] = t_minmc


# ------------------------------------------------------------------ solve first: enumerate solutions, prefix trie
ENUM_MAX_SOLUTIONS = 4096


def enumerate_solutions(aig: AIG, deadline: float, cap: int = ENUM_MAX_SOLUTIONS) -> list[int] | None:
    """All inputs x with f(x) = 1 (single output), by SAT with blocking clauses (Tseitin CNF of the AIG); None if more
    than `cap` solutions or out of time."""
    from pysat.solvers import Solver
    n = aig.num_inputs
    I = n
    cls = []
    for j, (a, b) in enumerate(aig.ands):
        v = I + 1 + j
        la = (a >> 1) * (-1 if a & 1 else 1)
        lb = (b >> 1) * (-1 if b & 1 else 1)
        cls += [[-v, la], [-v, lb], [v, -la, -lb]]
    o = aig.outputs[0]
    if (o >> 1) == 0:
        return [] if not (o & 1) else None
    cls.append([(o >> 1) * (-1 if o & 1 else 1)])
    sols = []
    with Solver(name="cadical195", bootstrap_with=cls) as s:
        while time.monotonic() < deadline:
            if not s.solve():
                return sols
            model = s.get_model()
            x = sum(1 << i for i in range(n) if model[i] > 0)
            sols.append(x)
            if len(sols) > cap:
                return None
            s.add_clause([-(i + 1) if (x >> i) & 1 else (i + 1) for i in range(n)])
    return None


def trie_oracle(sols: list[int], n: int, kind: str, budget=None) -> Circuit:
    """f = OR of the point functions of `sols`. Depth-first over the binary trie of solutions (variable order 0..n-1):
    a trie node at depth d holds AND(prefix literals) on an ancilla, computed once from its parent with one Toffoli and
    uncomputed on the way back; a leaf flips the output (bit-flip: Toffoli onto y) or applies the phase (CZ / Z)."""
    B = Builder(n, 1, kind, budget)
    y = n
    sols = sorted(set(sols))

    def lit(q, bit, fn):
        if not bit:
            B.g("x", [q])
        fn()
        if not bit:
            B.g("x", [q])

    def rec(prefix_q, depth, group):
        # prefix_q: qubit holding AND of the literals of variables < depth (None at depth 0)
        if depth == n:
            return
        for bit in (0, 1):
            sub = [s for s in group if (s >> depth) & 1 == bit]
            if not sub:
                continue
            if depth == n - 1:                       # leaf: apply f's contribution for this full assignment
                if prefix_q is None:
                    lit(depth, bit, lambda: B.g("cx", [depth, y]) if kind == "bitflip" else B.g("z", [depth]))
                else:
                    if kind == "bitflip":
                        lit(depth, bit, lambda: B.g("ccx", [prefix_q, depth, y]))
                    else:
                        lit(depth, bit, lambda: B.g("cz", [prefix_q, depth]))
                continue
            if prefix_q is None:
                if bit:
                    rec(depth, depth + 1, sub)
                else:
                    B.g("x", [depth])
                    rec(depth, depth + 1, sub)
                    B.g("x", [depth])
                continue
            t = B.alloc()
            lit(depth, bit, lambda: B.g("ccx", [prefix_q, depth, t]))
            rec(t, depth + 1, sub)
            lit(depth, bit, lambda: B.g("ccx", [prefix_q, depth, t]))
            B.release(t)
    if n == 0:
        raise NotImplementedError("no inputs")
    rec(None, 0, sols)
    return B.circuit()


def t_enum(public, track, seed, deadline):
    """'Solve first' baseline (legal for these contracts): enumerate all satisfying inputs of a single-output function
    with a SAT solver, then build the oracle from the prefix trie of the solution set."""
    aig = load_aig(public)
    if len(aig.outputs) != 1:
        raise NotImplementedError("single-output functions only")
    sols = enumerate_solutions(abc_optimize(aig), deadline - 5)
    if sols is None:
        raise NotImplementedError(f"more than {ENUM_MAX_SOLUTIONS} solutions (or enumeration out of time)")
    c = trie_oracle(sols, aig.num_inputs, _kind(public), _budget(public, track))
    return [{"circuit": c, "meta": {"solutions": len(sols), "method": "SAT enumeration + prefix-trie MCX"}}]


B_TOOLS["solution enumeration + prefix-trie MCX"] = t_enum
