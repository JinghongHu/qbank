"""Category-D baseline state preparation tools. Each returns candidates {"circuit", "meta"}.

Every tool's circuit is lowered to qbank's gate set with Qiskit transpile(basis ["u", "cx"], optimization_level 0) and,
as a second candidate, re-optimised with optimization_level 3 (fixed seed); the runner keeps the best verified one.

Generic (dense) methods apply up to DENSE_MAX qubits; sparse and structure-specific methods work from the nonzero list.
Structure-specific constructions recognise their state from the public amplitudes (Dicke / W) and are "unsupported"
otherwise:
  Dicke: Bärtschi & Eidenbenz, "Deterministic Preparation of Dicke States", FCT 2019 (arXiv:1904.07358), split-and-
         cyclic-shift construction (own implementation; CRY = 2 CX, CCRY = 4 CX exact decompositions).
  W:     linear cascade and the log-depth tree of Cruz et al., "Efficient quantum algorithms for GHZ and W states"
         (arXiv:1807.05572) (own implementations).
"""
from __future__ import annotations

import math
import time

import numpy as np

from ..core.circuit import Circuit

DENSE_MAX = 14
BQSKIT_MAX = 4


def _amps(public) -> tuple[int, list[int], np.ndarray]:
    n = public["n"]
    idx = [int(t[0]) for t in public["amplitudes"]]
    a = np.array([complex(t[1], t[2]) for t in public["amplitudes"]])
    return n, idx, a / np.linalg.norm(a)


def _dense(public) -> np.ndarray:
    n, idx, a = _amps(public)
    if n > DENSE_MAX:
        raise NotImplementedError(f"dense method limited to n <= {DENSE_MAX}")
    v = np.zeros(1 << n, dtype=complex)
    v[idx] = a
    return v


def lower(qc, seed: int, tag: str) -> list[dict]:
    """[u, cx] lowering at O0 and O3; returns candidate dicts."""
    from qiskit import transpile
    out = []
    for lvl in (0, 3):
        t = transpile(qc, basis_gates=["u", "cx"], optimization_level=lvl, seed_transpiler=seed)
        c = Circuit(t.num_qubits)
        for ins in t.data:
            g = ins.operation.name
            if g in ("barrier", "id", "delay"):
                continue
            if g == "global_phase":
                continue
            c.append(g, [t.find_bit(q).index for q in ins.qubits], [float(x) for x in ins.operation.params])
        out.append({"circuit": c, "meta": {"method": tag, "transpile_optimization_level": lvl}})
    return out


def _qc_from(c: Circuit):
    return c.to_qiskit()


# ------------------------------------------------------------------ generic dense methods
def t_qiskit_sp(public, track, seed, deadline):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import StatePreparation
    v = _dense(public)
    n = public["n"]
    qc = QuantumCircuit(n)
    qc.append(StatePreparation(v), range(n))
    return lower(qc, seed, "qiskit StatePreparation")


def _qclib(cls_name, public, seed, **kw):
    import qclib.state_preparation as sp
    v = _dense(public)
    g = getattr(sp, cls_name)(v, **kw)
    return lower(g.definition, seed, f"qclib {cls_name}")


def t_qclib_lowrank(public, track, seed, deadline):
    return _qclib("LowRankInitialize", public, seed)


def t_qclib_svd(public, track, seed, deadline):
    return _qclib("SVDInitialize", public, seed)


def t_qclib_ucge(public, track, seed, deadline):
    return _qclib("UCGEInitialize", public, seed)


def t_qclib_baa(public, track, seed, deadline):
    """Approximate track only: BAA low-rank with a fidelity-loss budget below the track's threshold."""
    spec = public["tracks"][track]
    if spec["contract"] != "state_approx":
        raise NotImplementedError("BAA with fidelity loss is an approximate method")
    loss = (1 - spec["min_fidelity"]) * 0.9
    return _qclib("BaaLowRankInitialize", public, seed, opt_params={"max_fidelity_loss": loss, "strategy": "greedy"})


def t_qclib_merge(public, track, seed, deadline):
    """Gleinig & Hoefler sparse method (qclib MergeInitialize; big-endian keys, so bit strings are reversed)."""
    import qclib.state_preparation as sp
    n, idx, a = _amps(public)
    d = {format(i, f"0{n}b")[::-1]: complex(x) for i, x in zip(idx, a)}
    g = sp.MergeInitialize(d)
    return lower(g.definition, seed, "qclib MergeInitialize (Gleinig-Hoefler)")


BQSKIT_SCRIPT = r"""
import sys, json, numpy as np
from bqskit import compile as bq_compile
from bqskit.ext import bqskit_to_qiskit
from bqskit.qis import StateVector
from qiskit import qasm2
d = json.loads(sys.stdin.read())
v = np.array([complex(a, b) for a, b in d["v"]])
circ = bq_compile(StateVector(v), optimization_level=d["opt"], seed=d["seed"], num_workers=1, max_synthesis_size=d["n"])
qc = bqskit_to_qiskit(circ)
print(qasm2.dumps(qc))
"""


def t_bqskit(public, track, seed, deadline):
    """BQSKit numerical synthesis in its own process group (hard-killed at the deadline, so its runtime server cannot
    outlive the job). BQSKit's state vectors are big-endian: amplitudes are bit-reversed on the way in; the circuit
    returned by bqskit_to_qiskit is then already in Qiskit's (little-endian) qubit order (checked by the verifier)."""
    import json
    import os
    import signal
    import subprocess
    import sys
    n = public["n"]
    if n > BQSKIT_MAX:
        raise NotImplementedError(f"BQSKit state synthesis limited to n <= {BQSKIT_MAX} here")
    from qiskit import qasm2
    v = _dense(public)
    rev = np.array([v[int(format(i, f"0{n}b")[::-1], 2)] for i in range(1 << n)])
    payload = json.dumps({"v": [[float(x.real), float(x.imag)] for x in rev], "opt": 1, "seed": int(seed), "n": n})
    p = subprocess.Popen([sys.executable, "-c", BQSKIT_SCRIPT], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, start_new_session=True)
    try:
        out, _ = p.communicate(payload, timeout=max(1.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.wait()
        raise TimeoutError("BQSKit did not finish within the budget")
    finally:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if p.returncode != 0 or "OPENQASM" not in out:
        raise RuntimeError(f"BQSKit failed (exit {p.returncode})")
    qc = qasm2.loads(out[out.index("OPENQASM"):])     # bqskit_to_qiskit already maps BQSKit's order to Qiskit's
    return lower(qc, seed, "bqskit compile(StateVector, O1)")


# ------------------------------------------------------------------ structure-specific constructions
def recognise_dicke(public) -> int | None:
    n, idx, a = _amps(public)
    if not np.allclose(a, a[0], atol=1e-12):
        return None
    ws = {bin(i).count("1") for i in idx}
    if len(ws) != 1:
        return None
    k = ws.pop()
    if len(idx) != math.comb(n, k):
        return None
    return k


def _cry(c: Circuit, ctrl: int, tgt: int, theta: float) -> None:
    c.append("ry", [tgt], [theta / 2])
    c.append("cx", [ctrl, tgt])
    c.append("ry", [tgt], [-theta / 2])
    c.append("cx", [ctrl, tgt])


def _ccry(c: Circuit, a: int, b: int, tgt: int, theta: float) -> None:
    q = theta / 4
    c.append("ry", [tgt], [q])
    c.append("cx", [b, tgt])
    c.append("ry", [tgt], [-q])
    c.append("cx", [a, tgt])
    c.append("ry", [tgt], [q])
    c.append("cx", [b, tgt])
    c.append("ry", [tgt], [-q])
    c.append("cx", [a, tgt])


def dicke_circuit(n: int, k: int) -> Circuit:
    """Bärtschi-Eidenbenz U_{n,k} applied to |0^{n-k} 1^k> (paper qubit j = our qubit j-1)."""
    c = Circuit(n)
    for j in range(n - k + 1, n + 1):
        c.append("x", [j - 1])

    def scs(m: int, kk: int) -> None:          # SCS_{m,kk} on paper qubits m-kk .. m
        c.append("cx", [m - 2, m - 1])
        _cry(c, m - 1, m - 2, 2 * math.acos(math.sqrt(1 / m)))
        c.append("cx", [m - 2, m - 1])
        for l in range(2, kk + 1):
            c.append("cx", [m - l - 1, m - 1])
            _ccry(c, m - 1, m - l, m - l - 1, 2 * math.acos(math.sqrt(l / m)))
            c.append("cx", [m - l - 1, m - 1])
    for m in range(n, k, -1):
        scs(m, k)
    for m in range(k, 1, -1):
        scs(m, m - 1)
    return c


def t_dicke(public, track, seed, deadline):
    k = recognise_dicke(public)
    if k is None or k == 0:
        raise NotImplementedError("target is not a Dicke state")
    n = public["n"]
    kk = min(k, n - k)
    c = dicke_circuit(n, kk)
    if kk != k:                                 # D(n, n-k) = X^n D(n, k)
        for q in range(n):
            c.append("x", [q])
    return lower(_qc_from(c), seed, f"Dicke (Bärtschi-Eidenbenz), k={k}")


def w_cascade(n: int) -> Circuit:
    c = Circuit(n)
    c.append("x", [0])
    for i in range(n - 1):
        _cry(c, i, i + 1, 2 * math.acos(math.sqrt(1 / (n - i))))
        c.append("cx", [i + 1, i])
    return c


def w_tree(n: int) -> Circuit:
    c = Circuit(n)
    c.append("x", [0])

    def split(lo: int, hi: int) -> None:       # excitation (if any) sits on qubit lo; spread it uniformly over [lo, hi)
        size = hi - lo
        if size <= 1:
            return
        mid = lo + size // 2
        _cry(c, lo, mid, 2 * math.asin(math.sqrt((hi - mid) / size)))
        c.append("cx", [mid, lo])
        split(lo, mid)
        split(mid, hi)
    split(0, n)
    return c


def t_w(public, track, seed, deadline):
    if recognise_dicke(public) != 1:
        raise NotImplementedError("target is not a W state")
    n = public["n"]
    return lower(_qc_from(w_cascade(n)), seed, "W linear cascade") + lower(_qc_from(w_tree(n)), seed, "W log-depth tree (Cruz et al.)")


def route_line(cd: dict, n: int, edges, seed: int) -> list[dict]:
    """Map an all-to-all candidate onto the line with Qiskit (SabreLayout + SabreSwap, basis u/cx, optimisation level 3).
    The input is |0...0>, so the initial layout is irrelevant; the final layout becomes the output map."""
    from qiskit import transpile
    from qiskit.transpiler import CouplingMap
    cm = CouplingMap([tuple(e) for e in edges] + [tuple(e[::-1]) for e in edges])
    t = transpile(cd["circuit"].to_qiskit(), coupling_map=cm, basis_gates=["u", "cx"], optimization_level=3,
                  seed_transpiler=seed, layout_method="sabre", routing_method="sabre")
    fl = t.layout.final_index_layout()
    c = Circuit(n)
    for ins in t.data:
        g = ins.operation.name
        if g in ("barrier", "id", "delay", "global_phase"):
            continue
        c.append(g, [t.find_bit(q).index for q in ins.qubits], [float(x) for x in ins.operation.params])
    return [{"circuit": c, "output_map": [int(x) for x in fl[:n]],
             "meta": {**cd.get("meta", {}), "routing": "qiskit transpile O3, SABRE layout+routing on the line"}}]


D_TOOLS = {
    "qiskit StatePreparation": t_qiskit_sp,
    "qclib LowRankInitialize": t_qclib_lowrank,
    "qclib SVDInitialize": t_qclib_svd,
    "qclib UCGEInitialize": t_qclib_ucge,
    "qclib BaaLowRankInitialize (approx)": t_qclib_baa,
    "qclib MergeInitialize": t_qclib_merge,
    "bqskit compile(StateVector)": t_bqskit,
    "Dicke construction (Bärtschi-Eidenbenz)": t_dicke,
    "W constructions (cascade, log-depth tree)": t_w,
}
APPROX_ONLY = {"qclib BaaLowRankInitialize (approx)"}
