"""Category-D baselines added 10-28 (evoA/baselines_ext2; see evoA/docs/baseline_plan_1028/NB_LOG.md). New file only.

* qclib PivotInitialize (aux=False): the pivot method of Malvetti, Iten, Colbeck, "Quantum circuits for sparse
  isometries", Quantum 5, 412 (2021) (arXiv:2006.00016), as implemented in qclib (same qclib version as qbank's
  MergeInitialize baseline, Apache-2.0). With aux=False qclib allocates no extra qubit (it may borrow idle data qubits
  only inside its multi-controlled gate decompositions), so the output is on exactly n qubits; the checker decides.
* lower_qasm(): lowering of an external tool's OpenQASM 2 circuit (quantum walks) with exactly the same [u, cx]
  O0/O3 lowering as qbank's other D baselines (tools_d.lower).
"""
from __future__ import annotations

from . import tools_d as TD


def g_qclib_pivot(public, track, seed, deadline):
    import qclib.state_preparation as sp
    n, idx, a = TD._amps(public)
    d = {format(i, f"0{n}b"): complex(x) for i, x in zip(idx, a)}   # Pivot reads keys MSB-first (unlike MergeInitialize;
    #                                                                    checked on random sparse states, 10-28)
    g = sp.PivotInitialize(d, opt_params={"aux": False})
    qc = _expand_dirty_vchain(g.definition)
    if qc.num_qubits != n:
        raise NotImplementedError(f"PivotInitialize produced {qc.num_qubits} qubits (n = {n})")
    yield from TD.lower(qc, seed, "qclib PivotInitialize (aux=False; Malvetti-Iten-Colbeck pivot method)")


def _expand_dirty_vchain(qc):
    """qclib's pivot step calls QuantumCircuit.mcx(..., ancilla_qubits=<idle data qubits>, mode='v-chain-dirty'). With
    Qiskit 2.5.2 that instruction (name 'mcx_vchain', k controls + target + k-2 borrowed qubits) carries a definition on
    k+1 qubits only, which transpile rejects. Each such instruction is replaced by Qiskit's own dirty-ancilla V-chain
    synthesis (synth_mcx_n_dirty_i15, Iten et al. 2016 -- the construction the mode names) on the same qubits, in the
    order controls, target, borrowed qubits; the control state (all ones here) is applied with X conjugation. The
    method's output is otherwise unchanged; the checker verifies the final circuit."""
    from qiskit import QuantumCircuit
    from qiskit.synthesis import synth_mcx_n_dirty_i15
    out = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase)
    for ins in qc.data:
        op = ins.operation
        if op.name == "mcx_vchain":
            k = op.num_ctrl_qubits
            qs = list(ins.qubits)
            if len(qs) != 2 * k - 1:
                raise NotImplementedError(f"mcx_vchain with {len(qs)} qubits for {k} controls")
            cs = getattr(op, "ctrl_state", (1 << k) - 1)
            neg = [qs[i] for i in range(k) if not (cs >> i) & 1]
            for q in neg:
                out.x(q)
            syn = synth_mcx_n_dirty_i15(k)       # k <= 3: Qiskit returns the ancilla-free version on k+1 qubits
            out.compose(syn, qs[:syn.num_qubits], inplace=True)
            for q in neg:
                out.x(q)
        else:
            out.append(op, ins.qubits, ins.clbits)
    return out


def lower_qasm(qasm: str, seed: int, tag: str) -> list[dict]:
    from qiskit import qasm2
    qc = qasm2.loads(qasm, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    return TD.lower(qc, seed, tag)


D_EXT_TOOLS = {"qclib PivotInitialize (aux=False)": g_qclib_pivot}
