# Datasheet: qbank v1 · Category C (routing and commuting-gate scheduling)

Generated: 2026-10-29 (by `qbank report C` from `data/v1/`).

## 1. Task and contract

- **routing_equiv**: output a routed circuit on n_physical qubits (only explicit SWAPs, no bridges) and an initial layout initial_layout[l] (the physical qubit holding logical qubit l, chosen by the method). Every two-qubit gate (including SWAPs) must lie on an edge of the coupling graph; after replaying the mapping, the circuit must be a topological reordering of the input circuit's gate DAG (gate names, parameters and qubit order identical gate by gate).
- **routing_commuting**: as above, but gates within the same commuting block (`blocks` in public) may be reordered arbitrarily; between blocks the order is kept on each qubit.
- **Tracks**: swaps (number of inserted SWAPs, main); depth2q (two-qubit gate depth, a SWAP counts as 3 layers); swaps_commuting (QAOA/Trotter/HamLib only, block partition given).
- Input circuits contain no swap gates (swap is reserved for routing); logical gate set: h, x, y, z, s, sdg, t, tdg, sx, rz, rx, ry, cx, cz, rzz, rxx, ryy; parameters may be symbolic (name strings).

## 2. Checking method and size limits

- Main checker: mapping replay (`qbank/contracts/routing.py`), polynomial time, no size limit.
- For n_physical ≤ 16 on the routing_equiv track, MQT QCEC is used as an independent second check (symbolic parameters replaced by random values; the routing permutation is undone with SWAPs before comparing); disagreement between the two is judged "checker disagreement".
- Negative controls in `tests/test_c_contracts.py`: missing SWAP, wrong parameter, DAG order violation, reordering across blocks, invalid initial layout.

## 3. Families and split sizes

| Family | n range | train | val | test_in | test_ood | probe |
|---|---|---|---|---|---|---|
| hamlib | 9-155 | 0 | 0 | 0 | 55 | 0 |
| mqtbench | 8-100 | 0 | 0 | 0 | 40 | 0 |
| qaoa | 8-156 | 180 | 60 | 90 | 0 | 0 |
| qubikos | 16-127 | 0 | 0 | 0 | 160 | 0 |
| queko | 16-54 | 0 | 0 | 0 | 300 | 60 |
| struct_random | 8-156 | 180 | 60 | 90 | 0 | 0 |
| trotter | 8-156 | 180 | 60 | 90 | 0 | 0 |

Total: probe 60, test_in 270, test_ood 555, train 540, val 180; 1605 instances in all.

Split rules: C v1: 3 generator families (qaoa, trotter, struct_random) x 5 device kinds (line, ring, grid, heavy_hex, random_sparse); per (family, device kind): train 12 / val 4 / test_in 2 seeds per size bin S 8-16, M 17-32, L 33-64 logical qubits, plus 12 XL (65-156) in test_in; seed ranges disjoint per split. test_ood = external sources never used in train: QUEKO (300), QUBIKOS (160), MQT Bench families not used in train, HamLib lattice Hamiltonians; unseen devices (Aspen-4, Tokyo, Rochester, Sycamore). probe = 60 small QUEKO instances with a verified zero-SWAP witness.

Equivalent variants: 2475 (3 per test instance, in the same split as the original, `data/v1/variants/C/`).
Cross-split deduplication removed 5 (all refilled with new seeds from the same split or recorded); see `data/v1/instances/C/build_report.json`.

## 4. Known limitations and implementation adjustments

- The deduplication invariant (Weisfeiler-Lehman hash) cannot distinguish regular graphs: random regular QAOA graphs of the same size in different splits are conservatively treated as duplicates (5 were actually removed and refilled).
- pytket and MQT QMAP cannot take this benchmark's gates directly (symbolic parameters, rxx/ryy): they route a "placeholder circuit" (same interaction structure; two-qubit gates → cx/rzz, single-qubit gates → rz, leading ry labels mark the initial position of each logical qubit), which is then replayed along the DAG to substitute the original gates back.
- Qiskit 2.5's Commuting2qGateRouter misreads the layout when there are several commuting blocks (`_make_op_layers` and `_position_in_cmap` use opposite directions), so from the second block on gates may land on non-adjacent qubits; this benchmark calls it block by block and tracks the permutation itself. It applies only to devices with a simple path covering all logical qubits (on heavy-hex and random sparse graphs it is often "unsupported").
- OLSQ2 (UCLA-VAST @ 0d7066f4, patched for Qiskit 2) is a small-scale baseline (≤ 16 logical qubits, ≤ 80 gates, transition mode, SWAP objective): its SWAP count is minimal only within its time-step range and is not taken as a proven optimum. The small-scale known optima come only from QUEKO (zero-SWAP witness) and QUBIKOS (constructed values, not independently verified).
- In the qiskit-ibm-runtime version used, FakeCairoV2 has only 26 mutually connected qubits (1 isolated qubit): device selection requires the largest connected component to be ≥ the number of logical qubits, otherwise the next device tier is used.
- MQT Bench's graphstate generator sets no random seed by default; this benchmark calls its create_circuit directly with a derived seed for reproducibility (covered by the full-rebuild test in `tests/test_cde_data.py`).
- **test_ood is reported per source**: 300 of the 555 are QUEKO, with known optimum 0 SWAPs; the baselines already reach the optimum on most of them, so they serve mainly as a correctness check and should not be merged into a geometric-mean score; the real room for improvement is on QUBIKOS (median ratio of best baseline to constructed optimum about 15x).

## 5. Sources and licenses

QUEKO @ 2ee23a12 (BSD-3, redistributable); QUBIKOS @ 442a9948 (no license); MQT Bench 2.3.0 (MIT, INDEP level, families not used in training); HamLib v1.1 condensedmatter/tfim, heisenberg (no license on the portal). See `data/v1/external/fetch_C.sh`.

## 6. Baseline definitions

- Each (instance, tool, track) gets 60 s of single-core wall-clock time; randomized/iterative tools are rerun with different seeds within the budget and the best result is kept; results delivered after the budget are recorded as timeouts; output checking has a separate 600 s window that does not count toward the tool budget.
- The machine is an Apple M3 Max (12 performance cores + 4 efficiency cores). When baselines run 10-16 single-core jobs in parallel, the OS schedules some jobs on efficiency cores, where the same 60 s wall-clock budget corresponds to less compute, so the effective compute per record is not perfectly uniform (each record stores hardware information). This mainly affects tools that improve over time (rustiq, LightSABRE, OLSQ2, etc.) and has no effect on deterministic tools (category B's pebbling SAT and XAG use conflict limits and are deterministic).
- Records of some baselines carry `concurrency` measured at run time (number of concurrency slots, number of jobs running at start, 1-minute load); the others carry `concurrency_estimate`, computed during aggregation (the number of simultaneously running jobs reconstructed from the start/end times of all cached records, 1 s resolution, excluding other processes). For the final evaluation, `qbank rebaseline <C> --split test --tools <time-limited tools>` reruns the time-limited baselines on test instances at fixed concurrency (default = number of performance cores); results are stored separately and best_known is not changed.
- All baseline outputs are verified by this benchmark's checkers and their costs recomputed by `qbank.core.costs`; "unverified" never counts as correct.
- best_known = min(verified baselines, published values whose semantics and budget both match), with the source stated; known optima/lower bounds in `data/v1/optimal/C.jsonl`.

## 7. Reproduction

```
bash env/bootstrap_env.sh
qbank generate C && qbank baselines C && qbank optimal C && qbank aggregate C && qbank report C
```
