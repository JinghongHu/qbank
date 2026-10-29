# Datasheet: qbank v1 · Category D (non-Clifford state preparation)

Generated: 2026-10-29 (by `qbank report D` from `data/v1/`).

## 1. Task and contract

- **state_exact**: prepare the target state from |0…0⟩ with fidelity |⟨target|ψ⟩|² ≥ 1 − 1e−9 (task spec §4.4); the comparison includes relative phases, a global phase is allowed; no ancillas allowed.
- **state_approx**: fidelity ≥ 0.99, a separate track (cx@F0.99), not compared with the exact tracks.
- **Tracks**: cx (CX count, all-to-all, main); depth2q@line (two-qubit gate depth under linear connectivity; an output map is allowed: qubit q of the state is carried by physical qubit output_map[q], since the input is |0…0⟩); cx@F0.99 (dense and sparse families).
- **Gate set**: any single-qubit gate (h, x, y, z, s, sdg, t, tdg, sx, sxdg, rx, ry, rz, p, u) + cx, cz; parameters must be numeric.
- public gives only n and the list of target amplitudes (little-endian, global phase fixed), no family name and no construction hints.

## 2. Checking method and size limits

- Main checker: an independent sparse state-vector simulation (int64 keys for n ≤ 62, Python integer keys beyond), executed in a "support-aware" equivalent topological order: a fused single-qubit segment runs right after the preceding two-qubit gate if it does not enlarge the support, otherwise it is postponed until just before the next two-qubit gate; this changes only the intermediate support, not the final state.
- More than 2^22 intermediate nonzero entries (2^18 for n > 62) is judged "unverified"; for n ≤ 16 qiskit Statevector is used as a second check, and disagreement is judged "checker disagreement".
- Negative controls in `tests/test_d_contracts.py`: angle perturbation, relative phase, ancilla, gate set, non-line edge.

## 3. Families and split sizes

| Family | n range | train | val | test_in | test_ood | probe |
|---|---|---|---|---|---|---|
| dense | 2-10 | 96 | 30 | 30 | 0 | 30 |
| dicke | 4-40 | 17 | 4 | 16 | 40 | 0 |
| sparse | 8-40 | 108 | 36 | 36 | 0 | 0 |
| sparse_struct | 7-32 | 0 | 0 | 0 | 48 | 0 |
| w | 4-128 | 24 | 5 | 10 | 0 | 0 |

Total: probe 30, test_in 92, test_ood 88, train 245, val 75; 530 instances in all.

Split rules: D v1: dicke k=2 (n=4-24 -> train, val n in {6,11,16,21}; n=25-40 -> test_in; k>=3, C(n,k)<=4096 -> test_ood); w (n=4-32 -> train, val n in {7,13,19,25,31}; n in {33,...,128} -> test_in); dense Haar-random (n=3-8: 16 train / 5 val seeds per n; n=9,10 -> test_in); sparse random support (S 8-14, M 15-22, L 23-30 qubits, 2-64 nonzeros: 36 train / 12 val / 4 test_in per bin; XL 31-40 qubits, up to 128 nonzeros -> test_in); test_ood = structured supports (simplex, first-order Reed-Muller, Hamming codewords, fixed weight) + Dicke k>=3; probe = dense n=2,3. Seed ranges disjoint per split.

Equivalent variants: 540 (3 per test instance, in the same split as the original, `data/v1/variants/D/`).

## 4. Known limitations and implementation adjustments

- Dicke k = 1 is the W state, so the dicke family uses k = 2 in train/val/test_in and W is a separate family; k ≥ 3 goes only to test_ood, with C(n, k) ≤ 4096.
- Dense methods (Qiskit StatePreparation, qclib LowRank/SVD/UCGE) are used only for n ≤ 14; BQSKit only for n ≤ 4 (O3 compilation at n = 5 took more than 500 s in measurements), run in a separate process group and killed when time is up.
- qclib MergeInitialize is big-endian (bit-reversed keys); PivotInitialize raises an error under Qiskit 2.5.2 and is not used; CVO-QRAM and similar introduce ancillas and do not fit the ancilla-free contract.
- Qiskit 2.5.2's StatePreparation produces wrong states for a few highly sparse 13-14-qubit vectors (fidelities 0.57, 0.25, 0.002 computed with Qiskit's own Statevector, and results differ between runs; another vector triggers "Input matrix is not unitary"). This is an upstream numerical issue, not the adapter; the checker judges these as fail, as observed.
- Known optima: the n = 2 probes need 1 CX (proof in `qbank/optimal/bde_optimal.py`); n = 3 has only the lower bound 2 and the published upper bound 3 (Znidaric, Giraud & Georgeot, PRA 77, 032320 (2008)); for the other instances the proven lower bounds come only from robust certificates (`certificate` of each entry in `data/v1/optimal/D.jsonl`: n − 1 when the two-qubit correlation graph is connected, or half the number of single qubits proven to be mixed, rounded up); "all single-qubit marginals are mixed" alone does not imply n − 1 (e.g. two Bell pairs need only 2 CX), and an n − 1 that a certificate cannot confirm is only an unproven reference (kind `unproven_bound`: a numerical reference, never used for "distance to optimum").
- **Known-optimum file** `data/v1/optimal/D.jsonl`: every record carries a `certificate`; a lower bound marked proven comes only from a robust certificate that holds for every state within the contract tolerance. Contents: 520 proven lower bounds, 18 unproven references, 10 proven optima, 41 upper bounds, 41 numerical optima. The D lower bounds of task pack v2 equal this file record by record.

## 5. Sources and licenses

Everything is generated by this benchmark's generators from the definitions (no external data).

## 6. Baseline definitions

- Each (instance, tool, track) gets 60 s of single-core wall-clock time; randomized/iterative tools are rerun with different seeds within the budget and the best result is kept; results delivered after the budget are recorded as timeouts; output checking has a separate 600 s window that does not count toward the tool budget.
- The machine is an Apple M3 Max (12 performance cores + 4 efficiency cores). When baselines run 10-16 single-core jobs in parallel, the OS schedules some jobs on efficiency cores, where the same 60 s wall-clock budget corresponds to less compute, so the effective compute per record is not perfectly uniform (each record stores hardware information). This mainly affects tools that improve over time (rustiq, LightSABRE, OLSQ2, etc.) and has no effect on deterministic tools (category B's pebbling SAT and XAG use conflict limits and are deterministic).
- Records of some baselines carry `concurrency` measured at run time (number of concurrency slots, number of jobs running at start, 1-minute load); the others carry `concurrency_estimate`, computed during aggregation (the number of simultaneously running jobs reconstructed from the start/end times of all cached records, 1 s resolution, excluding other processes). For the final evaluation, `qbank rebaseline <C> --split test --tools <time-limited tools>` reruns the time-limited baselines on test instances at fixed concurrency (default = number of performance cores); results are stored separately and best_known is not changed.
- All baseline outputs are verified by this benchmark's checkers and their costs recomputed by `qbank.core.costs`; "unverified" never counts as correct.
- best_known = min(verified baselines, published values whose semantics and budget both match), with the source stated; known optima/lower bounds in `data/v1/optimal/D.jsonl`.

## 7. Reproduction

```
bash env/bootstrap_env.sh
qbank generate D && qbank baselines D && qbank optimal D && qbank aggregate D && qbank report D
```
