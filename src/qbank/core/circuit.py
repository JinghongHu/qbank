"""Minimal circuit representation used by qbank (independent of any tool's IR).

A circuit is a list of gates (name, qubits, params) on qubits 0..n-1. Names are lower-case OpenQASM/Qiskit
names ("h", "cx", "swap", ...). Converters to/from Qiskit, stim, rustiq output, QASM3 and QPY live here.
"""
from __future__ import annotations

import io
import math
import numbers
from dataclasses import dataclass, field

CLIFFORD_1Q = ("h", "s", "sdg", "x", "y", "z", "sx", "sxdg", "id")
CLIFFORD_2Q = ("cx", "cz", "cy", "swap")
CLIFFORD_GATES = CLIFFORD_1Q + CLIFFORD_2Q

_STIM_TO_QB = {"H": "h", "S": "s", "S_DAG": "sdg", "X": "x", "Y": "y", "Z": "z", "SQRT_X": "sx",
               "SQRT_X_DAG": "sxdg", "CX": "cx", "CNOT": "cx", "ZCX": "cx", "CZ": "cz", "ZCZ": "cz", "CY": "cy",
               "ZCY": "cy", "SWAP": "swap", "I": "id"}
_QB_TO_STIM = {"h": "H", "s": "S", "sdg": "S_DAG", "x": "X", "y": "Y", "z": "Z", "sx": "SQRT_X",
               "sxdg": "SQRT_X_DAG", "cx": "CX", "cz": "CZ", "cy": "CY", "swap": "SWAP"}
_RUSTIQ_TO_QB = {"CNOT": "cx", "CX": "cx", "CZ": "cz", "H": "h", "S": "s", "Sd": "sdg", "X": "x", "Y": "y",
                 "Z": "z", "SqrtX": "sx", "SqrtXd": "sxdg"}


# Gate signatures (10-23, one table for every contract checker that takes candidate circuits: A, B, C, D):
# name -> (number of qubits, number of parameters). Qiskit conventions. Parameters must be finite real numbers
# (symbolic string parameters only where the caller allows them, e.g. routing of parametrised circuits). "mbu" (category
# B's measurement-based uncomputation) has one qubit and one parameter, the correction, checked by the oracle contract.
GATE_SIGNATURES = {
    **{g: (1, 0) for g in ("id", "h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "sxdg")},
    **{g: (1, 1) for g in ("rx", "ry", "rz", "p")},
    "u": (1, 3), "u3": (1, 3),
    **{g: (2, 0) for g in ("cx", "cz", "cy", "swap")},
    **{g: (2, 1) for g in ("cp", "crx", "cry", "crz", "rzz", "rxx", "ryy", "rzx")},
    **{g: (3, 0) for g in ("ccx", "ccz", "rccx")},
    "rc3x": (4, 0),
    "mbu": (1, 1),
}


# One correction gate of an "mbu" operation: a single layer of (gate, qubits) pairs, never a nested mbu (10-24 merge, C1/C8).
MBU_MAX_CORRECTION = 300_000


def _int_index(q) -> bool:
    """A qubit index must be an integer (Python or numpy), never a bool or a float (10-24 merge, C1)."""
    return isinstance(q, numbers.Integral) and not isinstance(q, bool)


def width_error(n) -> str | None:
    """None if n is a legal circuit width: an integer (Python or numpy, never a bool, float or string) >= 0; else the
    reason (Phase 7, VERIFY C1: the common entry of every circuit, also one built directly as Circuit(n), not only
    from_json). Every contract checks it before it simulates and returns a format failure."""
    if not _int_index(n) or n < 0:
        return f"circuit width must be a non-negative integer, got {n!r}"[:200]
    return None


def qubit_error(name, qubits, n: int | None = None) -> str | None:
    """None if every qubit index is an integer (not a bool), 0 <= q < n (when n is given) and all are distinct."""
    qs = list(qubits)
    if not all(_int_index(q) for q in qs):
        return f"gate {name}: qubit indices must be integers, got {qs!r}"[:300]
    if n is not None and any(q < 0 or q >= n for q in qs):
        return f"gate {name}: qubit index out of range {qs} (n={n})"[:300]
    if len(set(int(q) for q in qs)) != len(qs):
        return f"gate {name}: repeated qubit {qs}"[:300]
    return None


def _finite_param(x, symbolic: bool) -> bool:
    if isinstance(x, str):
        return symbolic
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        return False
    try:
        return math.isfinite(float(x))
    except (OverflowError, ValueError):          # e.g. 10**400: not a finite float
        return False


def gate_signature_error(name, qubits, params, symbolic: bool = False, n: int | None = None) -> str | None:
    """None if the gate has exactly the qubit and parameter count of GATE_SIGNATURES[name], integer distinct qubits
    (in range when n is given, 10-24 merge C1: a Circuit built directly, bypassing append, is checked too) and every
    parameter is a finite real number (or a string when symbolic=True); else the reason. Unknown names are an error.
    mbu: one parameter, the correction = a list of (gate, qubits) pairs, each a non-mbu gate with its own signature
    (which correction gates a contract allows is the contract's rule, e.g. oracle.MBU_CORRECTION_GATES)."""
    sig = GATE_SIGNATURES.get(name)
    if sig is None:
        return f"unknown gate {name!r}"
    nq, npar = sig
    if not isinstance(qubits, (list, tuple)) or not isinstance(params, (list, tuple)):
        return f"gate {name}: qubits and parameters must be lists"
    if len(qubits) != nq:
        return f"gate {name} takes exactly {nq} qubit{'s' if nq > 1 else ''}, got {len(qubits)} ({list(qubits)[:8]})"
    if len(params) != npar:
        return f"gate {name} takes exactly {npar} parameter{'s' if npar != 1 else ''}, got {len(params)}"
    e = qubit_error(name, qubits, n)
    if e:
        return e
    if name == "mbu":
        return mbu_correction_error(params[0], n)
    for x in params:
        if not _finite_param(x, symbolic):
            return f"gate {name}: parameter {str(x)[:40]!r} is not a finite real number"
    return None


def mbu_correction_error(corr, n: int | None = None) -> str | None:
    """None if corr is one layer of (gate, qubits) pairs with valid signatures (no nested mbu, no parameters)."""
    if not isinstance(corr, (list, tuple)):
        return "mbu correction must be a list of (gate, qubits) pairs"
    if len(corr) > MBU_MAX_CORRECTION:
        return f"mbu correction has {len(corr)} gates > {MBU_MAX_CORRECTION}"
    for item in corr:
        if not isinstance(item, (list, tuple)) or len(item) != 2 or not isinstance(item[0], str) \
                or not isinstance(item[1], (list, tuple)):
            return "mbu correction entries must be (gate, qubits) pairs"
        if item[0] == "mbu":
            return "mbu correction may not contain another mbu"
        e = gate_signature_error(item[0], item[1], (), n=n)
        if e:
            return f"mbu correction: {e}"
    return None


def signature_errors(c: "Circuit", symbolic: bool = False) -> str | None:
    """The width error of c (width_error, Phase 7 C1) or the first gate of c whose signature is wrong (see
    gate_signature_error, qubits checked against c.n), as a message; None if all are right."""
    e = width_error(c.n)
    if e:
        return e
    for k, (g, qs, p) in enumerate(c.gates):
        e = gate_signature_error(g, qs, p, symbolic, n=c.n)
        if e:
            return f"gate #{k}: {e}"
    return None


def _norm_correction(corr, n: int):
    """mbu correction -> the canonical form ((gate, (q, ...)), ...) with int qubits; ValueError when malformed."""
    e = mbu_correction_error(corr, n)
    if e:
        raise ValueError(e)
    return tuple((str(cg), tuple(int(q) for q in cqs)) for cg, cqs in corr)


@dataclass
class Circuit:
    n: int
    gates: list[tuple[str, tuple[int, ...], tuple]] = field(default_factory=list)

    # ------------------------------------------------------------------ basics
    def append(self, name: str, qubits, params=()) -> "Circuit":
        """10-24 merge (C1): qubit indices must be integers (Python or numpy, never bool / float; checked before the
        conversion), in range and distinct; a gate of GATE_SIGNATURES must have its exact qubit and parameter count
        with finite numeric (or symbolic string) parameters; an mbu correction is checked the same way and stored as
        ((gate, (q, ...)), ...). Other names (category E's measure, c:<g>, oracles) keep their own parameters."""
        qs = tuple(qubits)
        e = width_error(self.n) or qubit_error(name, qs, self.n)   # Phase 7 C1: the width first
        if e:
            raise ValueError(e)
        qs = tuple(int(q) for q in qs)
        params = tuple(params)
        if name in GATE_SIGNATURES:
            e = gate_signature_error(name, qs, params, symbolic=True, n=self.n)
            if e:
                raise ValueError(e)
            if name == "mbu":
                params = (_norm_correction(params[0], self.n),)
        self.gates.append((name, qs, params))
        return self

    def copy(self) -> "Circuit":
        return Circuit(self.n, list(self.gates))

    def relabel(self, perm, n_out: int | None = None) -> "Circuit":
        """Qubit q becomes qubit perm[q]."""
        out = Circuit(self.n if n_out is None else n_out)
        for g, qs, p in self.gates:
            if g == "mbu":    # the correction's qubits move with the circuit (10-24 merge)
                p = (tuple((cg, tuple(perm[q] for q in cqs)) for cg, cqs in p[0]),)
            out.append(g, [perm[q] for q in qs], p)
        return out

    def names(self) -> set[str]:
        return {g for g, _, _ in self.gates}

    def to_json(self) -> dict:
        return {"n": self.n, "gates": [[g, list(qs), [_param_json(x) for x in p]] for g, qs, p in self.gates]}

    @staticmethod
    def from_json(d: dict) -> "Circuit":
        """Inverse of to_json (and the plain list form [name, [qubits], [params]]); every gate goes through append's
        checks (10-24 merge, C1). n must be an integer >= 0."""
        n = d["n"]
        e = width_error(n)
        if e:
            raise ValueError(e)
        c = Circuit(int(n))
        for g, qs, p in d["gates"]:
            c.append(g, qs, [_param_from_json(x) for x in p])
        return c

    # ------------------------------------------------------------------ qiskit
    def to_qiskit(self):
        """String parameters become qiskit Parameters of the same name (symbolic circuits, e.g. QAOA angles)."""
        from qiskit import QuantumCircuit
        from qiskit.circuit import Parameter
        qc = QuantumCircuit(self.n)
        syms: dict[str, Parameter] = {}
        for g, qs, p in self.gates:
            if g == "id":
                qc.id(qs[0])
                continue
            args = [syms.setdefault(x, Parameter(x)) if isinstance(x, str) else x for x in p]
            getattr(qc, g)(*args, *qs)
        return qc

    @staticmethod
    def from_qiskit(qc, clifford_only: bool = False) -> "Circuit":
        """Convert a qiskit QuantumCircuit. Composite gates are expanded through their definitions.

        With clifford_only=True every 1-qubit gate outside the named Clifford set (e.g. u/u3 with Clifford angles,
        as emitted by tket) is re-expressed exactly via qiskit's Clifford class; a non-Clifford gate raises.
        """
        out = Circuit(qc.num_qubits)
        _from_qiskit_into(qc, out, list(range(qc.num_qubits)), clifford_only)
        return out

    def to_qasm3(self) -> str:
        from qiskit import qasm3
        return qasm3.dumps(self.to_qiskit())

    def to_qpy_bytes(self) -> bytes:
        from qiskit import qpy
        buf = io.BytesIO()
        qpy.dump(self.to_qiskit(), buf)
        return buf.getvalue()

    # ------------------------------------------------------------------ stim
    def to_stim(self):
        """Build the stim circuit from one text blob (much faster than per-gate appends). Qubits start in |0>."""
        import stim
        lines = []
        for g, qs, _ in self.gates:
            if g == "id":
                continue
            sg = _QB_TO_STIM.get(g)
            if sg is None:
                raise ValueError(f"gate {g} has no stim equivalent")
            lines.append(sg + " " + " ".join(map(str, qs)))
        c = stim.Circuit("\n".join(lines))
        if c.num_qubits < self.n:
            c.append("I", [self.n - 1])   # keep the declared width
        return c

    @staticmethod
    def from_stim(sc, n: int | None = None) -> "Circuit":
        """Unitary stim circuit, optionally starting with resets R/RZ (no-op on fresh qubits) and RX (= H).

        A reset after the first gate on that qubit, measurements, noise or any other instruction raises.
        """
        nq = sc.num_qubits if n is None else n
        out = Circuit(nq)
        touched: set[int] = set()
        for inst in sc.flattened():
            name = inst.name
            ts = [t.value for t in inst.targets_copy()]
            if name in ("TICK", "QUBIT_COORDS", "SHIFT_COORDS"):
                continue
            if name in ("R", "RZ", "RX"):
                for q in ts:
                    if q in touched:
                        raise ValueError("reset after use is not allowed")
                    if name == "RX":
                        out.append("h", [q])
                        touched.add(q)
                continue
            if name not in _STIM_TO_QB:
                raise ValueError(f"unsupported stim instruction {name}")
            g = _STIM_TO_QB[name]
            k = 2 if g in CLIFFORD_2Q else 1
            for i in range(0, len(ts), k):
                qs = ts[i:i + k]
                out.append(g, qs)
                touched.update(qs)
        return out

    # ------------------------------------------------------------------ rustiq
    @staticmethod
    def from_rustiq(gates, n: int) -> "Circuit":
        out = Circuit(n)
        for g, qs in gates:
            if g not in _RUSTIQ_TO_QB:
                raise ValueError(f"unsupported rustiq gate {g}")
            out.append(_RUSTIQ_TO_QB[g], qs)
        return out


def _param_json(x):
    if isinstance(x, float):
        return {"f": x.hex()}
    if isinstance(x, (int, str)):
        return x
    if isinstance(x, (list, tuple)):          # nested structures, e.g. the correction of an "mbu" operation
        return {"l": [_param_json(v) for v in x]}
    return {"s": str(x)}


def _param_from_json(x):
    if isinstance(x, dict) and "f" in x:
        return float.fromhex(x["f"])
    if isinstance(x, dict) and "l" in x:
        return tuple(_param_from_json(v) for v in x["l"])
    if isinstance(x, dict) and "s" in x:
        return x["s"]
    return x


def _clifford_1q_sequence(op) -> list[str]:
    """Exact re-expression of a 1-qubit Clifford operation in {h, s, sdg, x, y, z, sx, sxdg}."""
    from qiskit import QuantumCircuit, transpile
    from qiskit.quantum_info import Clifford
    from qiskit.synthesis import synth_clifford_full
    one = QuantumCircuit(1)
    one.append(op, [0])
    try:
        cl = Clifford(one)
    except Exception as e:  # non-Clifford
        raise ValueError(f"gate {op.name} is not a Clifford operation") from e
    sub = transpile(synth_clifford_full(cl), basis_gates=["h", "s", "sdg", "x", "y", "z", "sx", "sxdg"], optimization_level=0)
    return [i.operation.name for i in sub.data]


def _from_qiskit_into(qc, out: Circuit, qmap: list[int], clifford_only: bool) -> None:
    for inst in qc.data:
        op = inst.operation
        name = op.name
        qs = [qmap[qc.find_bit(q).index] for q in inst.qubits]
        if name == "barrier":
            continue
        if inst.clbits or name in ("measure", "reset"):
            raise ValueError(f"non-unitary operation {name} not supported here")
        if name in CLIFFORD_GATES:
            out.append(name, qs)
            continue
        if not clifford_only and name in ("rz", "rx", "ry", "p", "u", "u3", "t", "tdg", "ccx", "rccx", "rc3x", "ccz",
                                          "mcx", "cp", "crz", "rzz", "rxx", "ryy", "rzx", "cry", "crx"):
            out.append(name, qs, [float(p) if _is_number(p) else str(p) for p in op.params])
            continue
        if len(qs) == 1 and clifford_only:
            for g in _clifford_1q_sequence(op):
                out.append(g, qs)
            continue
        if op.definition is not None:
            _from_qiskit_into(op.definition, out, qs, clifford_only)
            continue
        raise ValueError(f"cannot convert gate {name}")


def _is_number(p) -> bool:
    try:
        float(p)
        return True
    except (TypeError, ValueError):
        return False


def is_clifford_name(g: str) -> bool:
    return g in CLIFFORD_GATES


def fmt_float(x: float) -> str:
    return float(x).hex() if math.isfinite(x) else str(x)
