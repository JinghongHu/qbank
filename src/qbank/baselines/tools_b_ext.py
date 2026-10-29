"""Category-B baselines added 10-28 (evoA/baselines_ext2; see evoA/docs/baseline_plan_1028/NB_LOG.md).

New file only: it imports qbank's B helpers and never changes them.

1. caterpillar (gmeuli/caterpillar @ 4c6f766c, MIT; Meuli, Soeken, De Micheli, "Xor-And-Inverter Graphs for Quantum
   Compilation", npj QI 8, 7 (2022), whose code-availability statement points to caterpillar). Built from the pinned
   commit with two recorded compile patches (evoA/baselines_ext2/patches); a small C++ driver
   (evoA/baselines_ext2/tools/caterpillar_driver/cat_driver.cpp) reads an XAG, runs caterpillar's
   logic_network_synthesis with one mapping strategy and prints the reversible netlist (X / CX / MCX on caterpillar's
   qubits; inputs, outputs, ancillas as caterpillar allocated them).
   * "caterpillar XAG low-T": xag_mapping_strategy and xag_fast_lowt_mapping_strategy, on two XAGs of the instance
     (structural XAG of the ABC resyn2 AIG; qbank's mockturtle MC-cut-rewritten XAG).
   * "caterpillar LHRS-style": caterpillar's lhrs.hpp framework on a k-LUT network (mockturtle lut_mapping, k = 4, 6)
     with bennett_mapping_strategy and tweedledum stg_from_pprm. LHRS-style, NOT the original LHRS (RevKit lhrs).
2. Re-screen of the qbank B tools that never ran on t_mbu@inf (it allows measurement-based uncomputation since 10-24):
   ESOP + MCX, per-clause MCX, SAT pebbling. Each runs unchanged (unitary circuit) and, as a second candidate, with
   the generic logical-AND lowering below; SAT pebbling additionally with its AND moves compiled as logical-AND
   (compute) / MBU (uncompute), the same switch the Bennett and XAG tools already use.

Netlist -> qbank circuit (stage 1, used for every track): caterpillar computes outputs out of place on qubits that start
in |0>. If no output qubit is an input, a duplicate or a control of any gate, output j is mapped straight onto the
oracle's output line n+j (every gate only toggles its target, so |y> -> |y xor f(x)> holds for every y) -- "direct";
otherwise the outputs live on ancillas, are copied (CX, or Z for a phase oracle) and the netlist is undone in reverse
-- "wrapped". MCX with k >= 3 controls use qbank's emit_mcx (cheapest Qiskit construction, as for the other B tools).
Logical-AND lowering (stage 2, t_mbu@inf candidates only): every plain ccx whose target is |0> on all inputs becomes
the 4-T logical AND (rccx + sdg); every ccx that returns its target to |0> (target = AND of its controls) becomes an
X-basis measurement with a CZ correction (0 T); any other ccx becomes logical AND into a fresh ancilla, CX onto the
target, MBU of the ancilla (4 T). This is the T-count convention of Meuli et al. (4 T per computed AND, Clifford
uncompute). Targets are classified by bit-parallel simulation (all inputs for n <= 14, else 4096 random inputs plus 0);
the qbank checker is the only judge of correctness.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

from ..core.circuit import Circuit
from . import tools_b as TB

CAT_DRIVER = Path(os.environ.get("QBANK_CAT_DRIVER", Path(__file__).resolve().parents[4] / "evoA" / "baselines_ext2"
                                 / "build" / "cat_driver" / "cat_driver"))


# ------------------------------------------------------------------ XAG text for the driver
def xag_text(x) -> str:
    def form(f):
        terms, c = f
        toks = [f"x{i}" if k == "x" else f"g{i}" for k, i in sorted(terms)]
        return " ".join(toks + ["|", str(int(c))])
    lines = [f"{x.n} {len(x.outputs)} {len(x.ands)}"]
    lines += [f"A {form(a)} ; {form(b)}" for a, b in x.ands]
    lines += [f"O {form(o)}" for o in x.outputs]
    return "\n".join(lines) + "\n"


def run_cat(x, mode: str, deadline: float) -> dict:
    if not CAT_DRIVER.exists():
        raise NotImplementedError(f"caterpillar driver not built ({CAT_DRIVER})")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.txt")
        open(p, "w").write(xag_text(x))
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("caterpillar: out of time")
        try:
            r = subprocess.run([str(CAT_DRIVER), p, mode], capture_output=True, text=True, timeout=left, cwd=d)
        except subprocess.TimeoutExpired:
            raise TimeoutError("caterpillar: out of time")
    if r.returncode != 0:
        raise RuntimeError(f"cat_driver {mode} failed ({r.returncode}): {r.stderr[-300:]}")
    net = {"gates": [], "stats": r.stderr.strip()}
    for line in r.stdout.splitlines():
        t = line.split()
        if t[0] == "QUBITS":
            net["qubits"] = int(t[1])
        elif t[0] in ("INPUTS", "OUTPUTS"):
            net[t[0].lower()] = [int(v) for v in t[1:]]
        else:
            ctl = [(int(c.lstrip("-")), 1 if c.startswith("-") else 0) for c in t[1:-1]]
            net["gates"].append((ctl, int(t[-1])))
    return net


# ------------------------------------------------------------------ stage 1: netlist -> circuit
def netlist_circuit(net: dict, n: int, m: int, kind: str) -> tuple[Circuit, str]:
    ins, outs = net["inputs"], net["outputs"]
    if len(ins) != n or len(outs) != m:
        raise RuntimeError("caterpillar netlist has an unexpected interface")
    ctl_qubits = {q for ctl, _ in net["gates"] for q, _ in ctl}
    direct = (kind == "bitflip" and len(set(outs)) == m and not (set(outs) & set(ins)) and not (set(outs) & ctl_qubits))
    B = TB.Builder(n, m, kind, None)
    qmap = {q: i for i, q in enumerate(ins)}
    if direct:
        qmap.update({q: n + j for j, q in enumerate(outs)})

    def q(c):
        if c not in qmap:
            qmap[c] = B.alloc()
        return qmap[c]

    def emit(gates):
        for ctl, t in gates:
            TB.emit_mcx(B, [(q(c), neg) for c, neg in ctl], q(t), busy=set())
    emit(net["gates"])
    if not direct:
        for j, o in enumerate(outs):
            if kind == "bitflip":
                B.g("cx", [q(o), n + j])
            else:
                B.g("z", [q(o)])
        emit(list(reversed(net["gates"])))
    return B.circuit(), "direct" if direct else "wrapped (compute, copy, reverse)"


# ------------------------------------------------------------------ stage 2: logical-AND / MBU lowering of ccx
def _patterns(n: int, width: int, seed: int = 1):
    if n <= 14:
        P = 1 << n
        x = ((np.arange(P)[:, None] >> np.arange(n)[None, :]) & 1).astype(bool)
    else:
        rng = np.random.default_rng(seed)
        x = rng.integers(0, 2, size=(4097, n)).astype(bool)
        x[0] = False
    rng = np.random.default_rng(seed + 1)
    vals = np.zeros((width, x.shape[0]), dtype=bool)
    vals[:n] = x.T
    return vals, rng


def mbu_lower(c: Circuit, n: int, m: int, kind: str) -> Circuit:
    reg = n + (m if kind == "bitflip" else 0)
    extra = sum(1 for g, _, _ in c.gates if g == "ccx")        # worst case: one fresh ancilla per ccx
    vals, rng = _patterns(n, c.n + 1)
    if kind == "bitflip":
        vals[n:reg] = rng.integers(0, 2, size=(m, vals.shape[1])).astype(bool)     # arbitrary output register
    out: list = []
    width = c.n
    free: list[int] = []
    rows = {}

    def v(qq):
        if qq not in rows:
            rows[qq] = vals[qq].copy() if qq < vals.shape[0] else np.zeros(vals.shape[1], dtype=bool)
        return rows[qq]
    for g, qs, p in c.gates:
        if g == "ccx":
            a, b, t = qs
            va, vb, vt = v(a), v(b), v(t)
            if not vt.any():
                out += [("rccx", (a, b, t), ()), ("sdg", (t,), ())]
                rows[t] = va & vb
            elif np.array_equal(vt, va & vb):
                out.append(("mbu", (t,), ((("cz", (a, b)),),)))
                rows[t] = np.zeros_like(vt)
            else:
                if free:
                    z = free.pop()
                else:
                    z, width = width, width + 1
                out += [("rccx", (a, b, z), ()), ("sdg", (z,), ()), ("cx", (z, t), ()), ("mbu", (z,), ((("cz", (a, b)),),))]
                rows[t] = vt ^ (va & vb)
                rows[z] = np.zeros_like(vt)
                free.append(z)
            continue
        out.append((g, qs, p))
        if g == "x":
            rows[qs[0]] = ~v(qs[0])
        elif g == "cx":
            rows[qs[1]] = v(qs[1]) ^ v(qs[0])
        elif g in ("rccx",):
            rows[qs[2]] = v(qs[2]) ^ (v(qs[0]) & v(qs[1]))
        elif g == "rc3x":
            rows[qs[3]] = v(qs[3]) ^ (v(qs[0]) & v(qs[1]) & v(qs[2]))
        elif g == "swap":
            rows[qs[0]], rows[qs[1]] = v(qs[1]), v(qs[0])
        elif g == "mbu":
            rows[qs[0]] = np.zeros(vals.shape[1], dtype=bool)
        elif g in ("z", "s", "sdg", "t", "tdg", "cz", "ccz", "id", "h"):
            pass
        else:
            raise RuntimeError(f"mbu_lower: unexpected gate {g}")
    del extra
    oc = Circuit(width)
    for g, qs, p in out:
        oc.append(g, qs, p)
    return oc


# ------------------------------------------------------------------ tools (generators: yield candidates as found)
def _xag_inputs(public, deadline):
    from ..core.xag import from_aig
    aig = TB.load_aig(public)
    yield "structural XAG of ABC resyn2 AIG", from_aig(TB.abc_optimize(aig))
    try:
        x, info = TB.build_xag_minmc(aig, deadline - 1)
        yield f"qbank mockturtle MC cut rewriting XAG ({info.get('start')}, cut {info.get('cut_size')})", x
    except (NotImplementedError, TimeoutError):
        return


def _cands(c: Circuit, public, track, meta: dict):
    n, m, kind = public["n_inputs"], public["n_outputs"], TB._kind(public)
    yield {"circuit": c, "meta": {**meta, "lowering": "unitary (ccx / qbank emit_mcx)"}}
    if TB._mbu_track(public, track):
        yield {"circuit": mbu_lower(c, n, m, kind), "meta": {**meta, "lowering": "logical-AND (4 T) / MBU"}}


def g_cat_lowt(public, track, seed, deadline):
    n, m, kind = public["n_inputs"], public["n_outputs"], TB._kind(public)
    for src, x in _xag_inputs(public, deadline):
        for mode in ("lowt", "lowt_fast"):
            net = run_cat(x, mode, deadline)
            c, how = netlist_circuit(net, n, m, kind)
            yield from _cands(c, public, track, {"xag": src, "xag_ands": x.num_ands, "strategy": mode, "outputs": how,
                                                 "cat_qubits": net["qubits"]})


def g_cat_lhrs(public, track, seed, deadline):
    from ..core.xag import from_aig
    n, m, kind = public["n_inputs"], public["n_outputs"], TB._kind(public)
    x = from_aig(TB.abc_optimize(TB.load_aig(public)))
    for k in (4, 6):
        net = run_cat(x, f"lhrs{k}", deadline)
        c, how = netlist_circuit(net, n, m, kind)
        yield from _cands(c, public, track, {"xag": "structural XAG of ABC resyn2 AIG", "lut_size": k,
                                             "strategy": "bennett + stg_from_pprm", "outputs": how,
                                             "stats": net["stats"]})


def _rescreen(fn):
    def g(public, track, seed, deadline):
        try:
            cands = fn(public, track, seed, deadline)
        except TB.NeedQubits as e:
            raise NotImplementedError(f"does not fit the qubit budget: {e}")
        for cd in cands:
            yield from _cands(cd["circuit"], public, track, cd.get("meta", {}))
    return g


def g_pebble_mbu(public, track, seed, deadline):
    """SAT pebbling (qbank re-implementation) with logical-AND compute / MBU uncompute of every pebble move."""
    if not TB._mbu_track(public, track):
        raise NotImplementedError("measurement-based variant only on the MBU track")
    aig = TB.abc_optimize(TB.load_aig(public))
    if len(aig.ands) > 400:
        raise NotImplementedError("SAT pebbling limited to <= 400 AND nodes")
    kind, budget = TB._kind(public), TB._budget(public, track)
    n, m = aig.num_inputs, len(aig.outputs)
    reg = n + (m if kind == "bitflip" else 0)
    K = (budget - reg) if budget is not None else len(aig.ands)
    moves = TB.pebbling_schedule(aig, K, deadline)
    if moves is None:
        raise NotImplementedError("no pebbling schedule (UNSAT up to the step bound)")
    B = TB.Builder(n, m, kind, budget)
    I = aig.num_inputs
    on: dict = {}

    def qn(l):
        v = l >> 1
        return v - 1 if v <= I else on[v]

    def toggle(v):
        a, b = aig.ands[v - I - 1]
        if v in on:
            t = on.pop(v)
            TB._unemit_and(B, qn(a), a & 1, qn(b), b & 1, t, "mbu")
            B.release(t)
        else:
            t = B.alloc()
            TB._emit_and(B, qn(a), a & 1, qn(b), b & 1, t, "gidney")
            on[v] = t
    for v in moves:
        toggle(v)
    for j, l in enumerate(aig.outputs):
        v = l >> 1
        TB._copy_out(B, (v - 1 if v <= I else on[v]) if v else None, l & 1, j)
    for v in reversed(moves):
        toggle(v)
    yield {"circuit": B.circuit(), "meta": {"pebbles": K, "compute_moves": len(moves),
                                            "and": "logical-AND compute / MBU uncompute per pebble move"}}


B_EXT_TOOLS = {
    "caterpillar XAG low-T (Meuli et al., official code)": g_cat_lowt,
    "caterpillar LHRS-style (lhrs.hpp, k-LUT + PPRM; not original LHRS)": g_cat_lhrs,
    "esop(qiskit EsopGenerator)+qiskit MCX [MBU re-screen]": _rescreen(TB.t_esop),
    "per-clause MCX (qiskit MCX) [MBU re-screen]": _rescreen(TB.t_clause),
    "pebbling SAT (Meuli et al. 2019, re-impl.) [MBU re-screen]": _rescreen(TB.t_pebble),
    "pebbling SAT + logical-AND/MBU (Meuli et al. 2019, re-impl.)": g_pebble_mbu,
}
# re-screen tools only add information on the MBU track (their tof / cx results already exist in qbank)
B_EXT_TRACKS = {k: (("t_mbu@inf",) if "re-screen" in k or "logical-AND/MBU" in k else ("t_mbu@inf", "tof_clifford@inf"))
                for k in B_EXT_TOOLS}
