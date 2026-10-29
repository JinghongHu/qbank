"""Phase 0 smoke test for category A baselines.

For a handful of CSS codes, every candidate baseline tool synthesises a |0_L> preparation circuit.
Each output is checked by two independent checkers:
  * gf2:  a self-contained Aaronson-Gottesman symplectic propagation with sign tracking (no simulator library);
  * stim: stim.TableauSimulator + peek_observable_expectation.
Both must agree. Single-qubit Pauli corrections are appended by an explicit normalisation step (free of cost),
and both checks are re-run on the corrected circuit. Also runs two negative controls per code
(wrong sign without correction; a codespace state that is not |0_L>).

Every tool runs in its own subprocess with a wall-clock timeout (some native tools segfault).
Outputs: phase0/logs/a_smoke.json and a text table on stdout.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TWO_Q = {"cx": 1, "cz": 1, "cy": 1, "swap": 3}


# ----------------------------------------------------------------------------- GF(2) helpers
def gf2_rref(m: np.ndarray) -> tuple[np.ndarray, list[int]]:
    m = m.copy() % 2
    rows, cols = m.shape
    piv, r = [], 0
    for c in range(cols):
        if r == rows:
            break
        nz = np.nonzero(m[r:, c])[0]
        if nz.size == 0:
            continue
        p = r + nz[0]
        m[[r, p]] = m[[p, r]]
        for i in range(rows):
            if i != r and m[i, c]:
                m[i] ^= m[r]
        piv.append(c)
        r += 1
    return m[:r], piv


def gf2_rank(m: np.ndarray) -> int:
    return len(gf2_rref(m)[1]) if m.size else 0


def gf2_solve(a: np.ndarray, b: np.ndarray) -> np.ndarray | None:
    """Solve a x = b over GF(2) (a: r x c). Returns one solution or None."""
    aug = np.concatenate([a % 2, (b % 2).reshape(-1, 1)], axis=1).astype(np.uint8)
    red, piv = gf2_rref(aug)
    if a.shape[1] in piv:
        return None
    x = np.zeros(a.shape[1], dtype=np.uint8)
    for row, c in zip(red, piv):
        x[c] = row[-1]
    return x


def zero_state_stabilizers(hx: np.ndarray, hz: np.ndarray, lz: np.ndarray) -> list[str]:
    """Independent generators of |0_L>: X checks plus a basis of span(Hz, Lz). Stim convention, qubit 0 leftmost."""
    n = hx.shape[1]
    xs, _ = gf2_rref(hx.astype(np.uint8))
    zs, _ = gf2_rref(np.concatenate([hz, lz]).astype(np.uint8))
    assert len(xs) + len(zs) == n, (len(xs), len(zs), n)
    out = ["+" + "".join("X" if b else "I" for b in r) for r in xs]
    out += ["+" + "".join("Z" if b else "I" for b in r) for r in zs]
    return out


# ----------------------------------------------------------------------------- independent checker (gf2)
def _parse(p: str):
    sign = 1 if p[0] == "-" else 0
    body = p[1:] if p[0] in "+-" else p
    x = np.array([c in "XY" for c in body], dtype=np.uint8)
    z = np.array([c in "ZY" for c in body], dtype=np.uint8)
    return x, z, sign


def _g(x1, z1, x2, z2) -> int:
    # exponent of i when multiplying single-qubit Paulis (x1,z1)*(x2,z2), Aaronson-Gottesman
    if x1 == 0 and z1 == 0:
        return 0
    if x1 == 1 and z1 == 1:
        return int(z2) - int(x2)
    if x1 == 1 and z1 == 0:
        return int(z2) * (2 * int(x2) - 1)
    return int(x2) * (1 - 2 * int(z2))


class SymplecticState:
    """Stabilizer tableau (stabilizers only) of |0^n>, propagated gate by gate with signs."""

    def __init__(self, n: int):
        self.n = n
        self.x = np.zeros((n, n), dtype=np.uint8)
        self.z = np.eye(n, dtype=np.uint8)
        self.r = np.zeros(n, dtype=np.uint8)

    def h(self, a):
        self.r ^= self.x[:, a] & self.z[:, a]
        self.x[:, a], self.z[:, a] = self.z[:, a].copy(), self.x[:, a].copy()

    def s(self, a):
        self.r ^= self.x[:, a] & self.z[:, a]
        self.z[:, a] ^= self.x[:, a]

    def sdg(self, a):
        self.r ^= self.x[:, a] & (1 - self.z[:, a])
        self.z[:, a] ^= self.x[:, a]

    def px(self, a):
        self.r ^= self.z[:, a]

    def pz(self, a):
        self.r ^= self.x[:, a]

    def py(self, a):
        self.r ^= self.x[:, a] ^ self.z[:, a]

    def cx(self, a, b):
        self.r ^= self.x[:, a] & self.z[:, b] & (self.x[:, b] ^ self.z[:, a] ^ 1)
        self.x[:, b] ^= self.x[:, a]
        self.z[:, a] ^= self.z[:, b]

    def cz(self, a, b):
        self.h(b); self.cx(a, b); self.h(b)

    def cy(self, a, b):
        self.sdg(b); self.cx(a, b); self.s(b)

    def swap(self, a, b):
        for m in (self.x, self.z):
            m[:, [a, b]] = m[:, [b, a]]

    def sx(self, a):
        self.h(a); self.s(a); self.h(a)

    def sxdg(self, a):
        self.h(a); self.sdg(a); self.h(a)

    def apply(self, name: str, qs: list[int]):
        f = {"h": self.h, "s": self.s, "sdg": self.sdg, "x": self.px, "y": self.py, "z": self.pz,
             "cx": self.cx, "cz": self.cz, "cy": self.cy, "swap": self.swap, "sx": self.sx, "sxdg": self.sxdg}
        if name in ("id", "barrier"):
            return
        if name not in f:
            raise ValueError(f"gf2 checker: unsupported gate {name}")
        f[name](*qs)

    def membership_sign(self, target: str):
        """Return None if target not in the stabilizer group, else the sign bit of the group element."""
        tx, tz, _ = _parse(target)
        a = np.concatenate([self.x, self.z], axis=1).T  # 2n x n
        c = gf2_solve(a, np.concatenate([tx, tz]))
        if c is None:
            return None
        px, pz, ph = np.zeros(self.n, np.uint8), np.zeros(self.n, np.uint8), 0
        for i in np.nonzero(c)[0]:
            ph += 2 * int(self.r[i]) + sum(_g(self.x[i, j], self.z[i, j], px[j], pz[j]) for j in range(self.n))
            px ^= self.x[i]
            pz ^= self.z[i]
            ph %= 4
        assert ph in (0, 2)
        return ph // 2


def check_gf2(n: int, gates: list[tuple[str, list[int]]], targets: list[str]):
    st = SymplecticState(n)
    for g, qs in gates:
        st.apply(g, qs)
    bad_group, wrong_sign = [], []
    for j, t in enumerate(targets):
        s = st.membership_sign(t)
        if s is None:
            bad_group.append(j)
        elif s != _parse(t)[2]:
            wrong_sign.append(j)
    return bad_group, wrong_sign


# ----------------------------------------------------------------------------- stim checker
def check_stim(n: int, gates, targets):
    import stim
    sim = stim.TableauSimulator()
    sim.set_num_qubits(n)
    names = {"h": "H", "s": "S", "sdg": "S_DAG", "x": "X", "y": "Y", "z": "Z", "cx": "CX", "cz": "CZ",
             "cy": "CY", "swap": "SWAP", "sx": "SQRT_X", "sxdg": "SQRT_X_DAG"}
    c = stim.Circuit()
    for g, qs in gates:
        if g in ("id", "barrier"):
            continue
        c.append(names[g], qs)
    sim.do_circuit(c)
    bad_group, wrong_sign = [], []
    for j, t in enumerate(targets):
        e = sim.peek_observable_expectation(stim.PauliString(t))
        if e == 0:
            bad_group.append(j)
        elif e == -1:
            wrong_sign.append(j)
    return bad_group, wrong_sign


def pauli_correction(n: int, targets: list[str], wrong: list[int]) -> list[tuple[str, list[int]]]:
    """Single-qubit Paulis P with P anticommuting exactly with targets[wrong] (explicit normalisation step)."""
    rows, rhs = [], []
    for j, t in enumerate(targets):
        x, z, _ = _parse(t)
        rows.append(np.concatenate([z, x]))  # P = X^a Z^b anticommutes with (x,z) iff a.z + b.x = 1
        rhs.append(1 if j in wrong else 0)
    sol = gf2_solve(np.array(rows, np.uint8), np.array(rhs, np.uint8))
    a, b = sol[:n], sol[n:]
    out = []
    for q in range(n):
        if a[q] and b[q]:
            out.append(("y", [q]))
        elif a[q]:
            out.append(("x", [q]))
        elif b[q]:
            out.append(("z", [q]))
    return out


# ----------------------------------------------------------------------------- circuit conversion / costs
def qiskit_to_gates(qc) -> list[tuple[str, list[int]]]:
    from qiskit import transpile
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Clifford
    from qiskit.synthesis import synth_clifford_full
    basis = ["h", "s", "sdg", "x", "y", "z", "cx", "cz", "cy", "swap", "sx", "sxdg"]
    out = []
    for inst in qc.data:
        name = inst.operation.name
        qs = [qc.find_bit(q).index for q in inst.qubits]
        if name in ("barrier", "id"):
            continue
        if name in basis:
            out.append((name, qs))
        elif len(qs) > 1 and inst.operation.definition is not None:
            # composite block (e.g. qiskit's layered "H2"/"CZ" layers): expand through its definition
            sub = inst.operation.definition
            out += [(g, [qs[i] for i in sq]) for g, sq in qiskit_to_gates(sub)]
        elif len(qs) == 1:
            # a 1q gate given by angles (e.g. tket TK1 -> u3); must be Clifford, re-expressed exactly
            one = QuantumCircuit(1)
            one.append(inst.operation, [0])
            sub = synth_clifford_full(Clifford(one))
            sub = transpile(sub, basis_gates=basis, optimization_level=0)
            out += [(i.operation.name, [qs[0]]) for i in sub.data]
        else:
            raise ValueError(f"unsupported multi-qubit gate {name}")
    return out


def costs(gates, n):
    twoq = sum(TWO_Q.get(g, 0) for g, _ in gates)
    depth2 = [0] * n
    depth = [0] * n
    for g, qs in gates:
        d = max(depth[q] for q in qs) + 1
        for q in qs:
            depth[q] = d
        if len(qs) == 2:
            d2 = max(depth2[q] for q in qs) + 1
            for q in qs:
                depth2[q] = d2
    return {"two_qubit_gates": twoq, "depth": max(depth, default=0), "two_qubit_depth": max(depth2, default=0)}


# ----------------------------------------------------------------------------- codes
def load_codes():
    from mqt.qecc import CSSCode
    from mqt.qecc.codes import (RotatedSurfaceCode, HexagonalColorCode, SquareOctagonColorCode,
                                construct_quantum_hamming_code, construct_bb_code)
    codes = {}
    codes["steane_7"] = CSSCode.from_code_name("steane")
    codes["surface_rot_d3"] = RotatedSurfaceCode(distance=3)
    codes["carbon_12"] = CSSCode.from_code_name("carbon")
    codes["hamming_r4_15"] = construct_quantum_hamming_code(4)
    codes["color666_d5"] = HexagonalColorCode(distance=5)
    codes["golay_23"] = CSSCode.from_code_name("golay")
    codes["surface_rot_d5"] = RotatedSurfaceCode(distance=5)
    codes["color488_d5"] = SquareOctagonColorCode(distance=5)
    codes["bb_72"] = construct_bb_code(72)
    return codes


def code_arrays(code):
    hx, hz = np.asarray(code.Hx, np.uint8), np.asarray(code.Hz, np.uint8)
    lz = np.asarray(code.Lz, np.uint8)
    return hx, hz, lz


# ----------------------------------------------------------------------------- tools (each returns a qiskit circuit or gate list)
def tool_qiskit_from_stabilizers(code, stabs):
    from qiskit.synthesis import synth_circuit_from_stabilizers
    return synth_circuit_from_stabilizers(_to_qiskit_labels(stabs))


def tool_qiskit_stabilizer_layers(code, stabs):
    from qiskit.quantum_info import StabilizerState
    from qiskit.synthesis import synth_stabilizer_layers
    return synth_stabilizer_layers(StabilizerState.from_stabilizer_list(_to_qiskit_labels(stabs)))


def tool_qiskit_stabilizer_depth_lnn(code, stabs):
    from qiskit.quantum_info import StabilizerState
    from qiskit.synthesis import synth_stabilizer_depth_lnn
    return synth_stabilizer_depth_lnn(StabilizerState.from_stabilizer_list(_to_qiskit_labels(stabs)))


def _clifford_of(stabs):
    from qiskit.quantum_info import StabilizerState
    return StabilizerState.from_stabilizer_list(_to_qiskit_labels(stabs)).clifford


def tool_qiskit_clifford_greedy(code, stabs):
    from qiskit.synthesis import synth_clifford_greedy
    return synth_clifford_greedy(_clifford_of(stabs))


def tool_qiskit_clifford_ag(code, stabs):
    from qiskit.synthesis import synth_clifford_ag
    return synth_clifford_ag(_clifford_of(stabs))


def tool_qiskit_clifford_layers(code, stabs):
    from qiskit.synthesis import synth_clifford_layers
    return synth_clifford_layers(_clifford_of(stabs))


def _to_qiskit_labels(stabs):
    # qiskit labels are little-endian (qubit 0 rightmost)
    return [s[0] + s[1:][::-1] for s in stabs]


def tool_stim_elimination(code, stabs):
    import stim
    t = stim.Tableau.from_stabilizers([stim.PauliString(s) for s in stabs])
    return _stim_to_gates(t.to_circuit("elimination"))


def tool_stim_graph_state(code, stabs):
    import stim
    t = stim.Tableau.from_stabilizers([stim.PauliString(s) for s in stabs])
    return _stim_to_gates(t.to_circuit("graph_state"))


def _stim_to_gates(c):
    names = {"H": "h", "S": "s", "S_DAG": "sdg", "X": "x", "Y": "y", "Z": "z", "CX": "cx", "CZ": "cz",
             "SQRT_X": "sx", "SQRT_X_DAG": "sxdg", "SWAP": "swap", "CY": "cy"}
    out = []
    for inst in c.flattened():
        nm = inst.name
        ts = [t.value for t in inst.targets_copy()]
        if nm in ("RX",):  # reset to |+> from |0>: equivalent to H on a fresh qubit
            out += [("h", [q]) for q in ts]
            continue
        if nm in ("R", "RZ"):
            continue  # fresh qubits already |0>
        k = 2 if nm in ("CX", "CZ", "CY", "SWAP") else 1
        for i in range(0, len(ts), k):
            out.append((names[nm], ts[i:i + k]))
    return out


def tool_rustiq(code, stabs):
    import rustiq
    circ = rustiq.stabilizer_state_synthesis([s[1:] for s in stabs], rustiq.Metric("count"), syndrome_iter=100)
    names = {"CNOT": "cx", "CX": "cx", "CZ": "cz", "H": "h", "S": "s", "Sd": "sdg", "X": "x", "Z": "z",
             "SqrtX": "sx", "SqrtXd": "sxdg", "Y": "y"}
    return [(names[g], list(q)) for g, q in circ]


def tool_qecc_heuristic(code, stabs):
    from mqt.qecc.circuit_synthesis import heuristic_prep_circuit
    return heuristic_prep_circuit(code, optimize_depth=False).circ.to_qiskit_circuit()


def tool_qecc_gate_optimal(code, stabs):
    from mqt.qecc.circuit_synthesis import gate_optimal_prep_circuit
    r = gate_optimal_prep_circuit(code, max_gates=60, max_timeout=240)
    if r is None:
        raise RuntimeError("no circuit within limits")
    return r.circ.to_qiskit_circuit()


def tool_qmap_optimal(code, stabs):
    from mqt.qmap.clifford_synthesis import TargetMetric
    from mqt.qmap.plugins.qiskit.clifford_synthesis import synthesize_clifford
    qc, _ = synthesize_clifford(str(stabs), target_metric=TargetMetric.two_qubit_gates, heuristic=False)
    return qc


def tool_pytket_resynth(code, stabs):
    """pytket as optimiser: start from stim elimination circuit, run Clifford resynthesis passes."""
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import CliffordResynthesis, CliffordSimp, FullPeepholeOptimise, RemoveRedundancies, SequencePass
    from qiskit import QuantumCircuit
    g = tool_stim_elimination(code, stabs)
    qc = QuantumCircuit(len(stabs))
    for nm, qs in g:
        getattr(qc, nm)(*qs)
    tk = qiskit_to_tk(qc)
    from pytket.circuit import OpType
    from pytket.passes import AutoRebase
    SequencePass([CliffordResynthesis(), CliffordSimp(), FullPeepholeOptimise(allow_swaps=False), RemoveRedundancies(),
                  AutoRebase({OpType.CX, OpType.TK1})]).apply(tk)
    # tket may end with an implicit wire permutation. For preparation from |0..0> a final permutation is free:
    # relabel every gate by the permutation instead of inserting SWAPs.
    perm = {a.index[0]: b.index[0] for a, b in tk.implicit_qubit_permutation().items()}
    gates = qiskit_to_gates(tk_to_qiskit(tk, replace_implicit_swaps=False))
    return [(g, [perm[q] for q in qs]) for g, qs in gates]


TOOLS = {
    "qiskit.synth_circuit_from_stabilizers": tool_qiskit_from_stabilizers,
    "qiskit.synth_stabilizer_layers": tool_qiskit_stabilizer_layers,
    "qiskit.synth_stabilizer_depth_lnn": tool_qiskit_stabilizer_depth_lnn,
    "qiskit.synth_clifford_greedy": tool_qiskit_clifford_greedy,
    "qiskit.synth_clifford_ag": tool_qiskit_clifford_ag,
    "qiskit.synth_clifford_layers": tool_qiskit_clifford_layers,
    "stim.to_circuit(elimination)": tool_stim_elimination,
    "stim.to_circuit(graph_state)": tool_stim_graph_state,
    "rustiq.stabilizer_state_synthesis": tool_rustiq,
    "mqt.qecc.heuristic_prep_circuit": tool_qecc_heuristic,
    "mqt.qecc.gate_optimal_prep_circuit(SAT)": tool_qecc_gate_optimal,
    "mqt.qmap.synthesize_clifford(SAT,2q)": tool_qmap_optimal,
    "pytket.CliffordResynthesis+FPO": tool_pytket_resynth,
}


def _worker(tool_name, code_name, q):
    try:
        codes = load_codes()
        code = codes[code_name]
        stabs = zero_state_stabilizers(*code_arrays(code))
        t0 = time.perf_counter()
        out = TOOLS[tool_name](code, stabs)
        dt = time.perf_counter() - t0
        gates = out if isinstance(out, list) else qiskit_to_gates(out)
        q.put({"status": "ok", "time_s": dt, "gates": gates})
    except Exception as e:  # recorded, never hidden
        q.put({"status": "error", "error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-800:]})


def run_tool(tool_name, code_name, timeout):
    q = mp.Queue()
    p = mp.Process(target=_worker, args=(tool_name, code_name, q))
    t0 = time.perf_counter()
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.kill(); p.join()
        return {"status": "timeout", "time_s": time.perf_counter() - t0}
    if p.exitcode != 0 and q.empty():
        return {"status": "crash", "exitcode": p.exitcode, "time_s": time.perf_counter() - t0}
    return q.get()


def main():
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 300
    only_codes = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] else None
    only_tools = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else None
    codes = load_codes()
    results = []
    for cname, code in codes.items():
        if only_codes and cname not in only_codes:
            continue
        hx, hz, lz = code_arrays(code)
        n = hx.shape[1]
        stabs = zero_state_stabilizers(hx, hz, lz)
        k = n - gf2_rank(hx) - gf2_rank(hz)
        # negative controls for the checkers themselves
        ok_gates = tool_stim_elimination(code, stabs)
        neg = {}
        # (1) sign error: apply a single Pauli that anticommutes with at least one generator
        for q in range(n):
            test = ok_gates + [("x", [q])]
            g1, g2 = check_gf2(n, test, stabs), check_stim(n, test, stabs)
            if g1[1]:
                neg["wrong_sign_detected_gf2"] = bool(g1[1]) and not g1[0]
                neg["wrong_sign_detected_stim"] = bool(g2[1]) and not g2[0]
                break
        # (2) codespace but not |0_L>: apply a logical X (any row of Lx)
        lx = np.asarray(code.Lx, np.uint8)
        test = ok_gates + [("x", [q]) for q in np.nonzero(lx[0])[0]]
        b1, b2 = check_gf2(n, test, stabs), check_stim(n, test, stabs)
        neg["logical_flip_rejected_gf2"] = bool(b1[0] or b1[1])
        neg["logical_flip_rejected_stim"] = bool(b2[0] or b2[1])
        print(f"\n== {cname}: n={n} k={k}  negative controls: {neg}", flush=True)
        for tname in TOOLS:
            if only_tools and tname not in only_tools:
                continue
            r = run_tool(tname, cname, timeout)
            rec = {"code": cname, "n": n, "k": k, "tool": tname, **{kk: v for kk, v in r.items() if kk != "gates"}}
            if r["status"] == "ok":
                gates = [(g, list(map(int, qs))) for g, qs in r["gates"]]
                v1, v2 = check_gf2(n, gates, stabs), check_stim(n, gates, stabs)
                rec["raw_check_gf2"], rec["raw_check_stim"] = v1, v2
                if not v1[0] and v1[1]:
                    gates = gates + pauli_correction(n, stabs, v1[1])
                    rec["pauli_correction"] = True
                w1, w2 = check_gf2(n, gates, stabs), check_stim(n, gates, stabs)
                rec["verified_gf2"] = not w1[0] and not w1[1]
                rec["verified_stim"] = not w2[0] and not w2[1]
                rec["checkers_agree"] = rec["verified_gf2"] == rec["verified_stim"]
                rec.update(costs(gates, n))
            results.append(rec)
            short = {kk: rec.get(kk) for kk in ("status", "two_qubit_gates", "two_qubit_depth", "verified_gf2", "verified_stim", "pauli_correction")}
            print(f"  {tname:42s} {rec.get('time_s', 0):8.2f}s {short} {rec.get('error', '')[:120] if rec.get('error') else ''}", flush=True)
            if rec.get("exitcode"):
                print(f"    exitcode={rec['exitcode']}")
    tag = "_".join(filter(None, [f"t{int(timeout)}", (sys.argv[2].replace(',', '+') if len(sys.argv) > 2 and sys.argv[2] else "")]))[:80]
    out = ROOT / "phase0" / "logs" / f"a_smoke_{tag}.json"
    out.write_text(json.dumps(results, indent=1))
    print("written", out)


if __name__ == "__main__":
    main()
