# qbank v1 - Category C (routing and commuting-gate scheduling) report

Generated: 2026-10-29. This report is generated entirely by `qbank report C` from the files in `data/v1/`.

## 1. Instances per split (by family and size bin)

Reproduce: `qbank generate C` (CSV: `C_counts.csv`)

| Split | Family | Size bin | Count |
|---|---|---|---|
| train | qaoa | L | 60 |
| train | qaoa | M | 60 |
| train | qaoa | S | 60 |
| train | struct_random | L | 60 |
| train | struct_random | M | 60 |
| train | struct_random | S | 60 |
| train | trotter | L | 60 |
| train | trotter | M | 60 |
| train | trotter | S | 60 |
| val | qaoa | L | 20 |
| val | qaoa | M | 20 |
| val | qaoa | S | 20 |
| val | struct_random | L | 20 |
| val | struct_random | M | 20 |
| val | struct_random | S | 20 |
| val | trotter | L | 20 |
| val | trotter | M | 20 |
| val | trotter | S | 20 |
| test_in | qaoa | L | 10 |
| test_in | qaoa | M | 10 |
| test_in | qaoa | S | 10 |
| test_in | qaoa | XL | 60 |
| test_in | struct_random | L | 10 |
| test_in | struct_random | M | 10 |
| test_in | struct_random | S | 10 |
| test_in | struct_random | XL | 60 |
| test_in | trotter | L | 10 |
| test_in | trotter | M | 10 |
| test_in | trotter | S | 10 |
| test_in | trotter | XL | 60 |
| test_ood | hamlib | L | 13 |
| test_ood | hamlib | M | 7 |
| test_ood | hamlib | S | 9 |
| test_ood | hamlib | XL | 26 |
| test_ood | mqtbench | L | 13 |
| test_ood | mqtbench | M | 14 |
| test_ood | mqtbench | S | 9 |
| test_ood | mqtbench | XL | 4 |
| test_ood | qubikos | L | 80 |
| test_ood | qubikos | S | 40 |
| test_ood | qubikos | XL | 40 |
| test_ood | queko | L | 150 |
| test_ood | queko | M | 50 |
| test_ood | queko | S | 100 |
| probe | queko | L | 30 |
| probe | queko | S | 30 |

Total: probe 60, test_in 270, test_ood 555, train 540, val 180; 1605 in all.

## 2. Share of instances on which each tool is the best baseline, per track

Definition: for each (instance, track), take the verified records with the smallest value of the track metric; on ties each tool is counted once. Reproduce: `qbank generate C && qbank baselines C && qbank optimal C && qbank aggregate C && qbank report C` (CSV: `C_best_tool_share.csv`)

### Track `depth2q` (1605 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| qiskit LightSABRE (anytime) | 1476 | 92.0% |
| pytket LexiRoute | 322 | 20.1% |
| OLSQ2 (TB, swap objective) | 70 | 4.4% |
| mqt.qmap heuristic | 20 | 1.2% |

### Track `swaps` (1605 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| qiskit LightSABRE (anytime) | 1464 | 91.2% |
| pytket LexiRoute | 329 | 20.5% |
| OLSQ2 (TB, swap objective) | 80 | 5.0% |
| mqt.qmap heuristic | 33 | 2.1% |

### Track `swaps_commuting` (715 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| qiskit LightSABRE + block reordering (anytime) | 673 | 94.1% |
| qiskit LightSABRE (anytime) | 63 | 8.8% |
| OLSQ2 (TB, swap objective) | 14 | 2.0% |
| mqt.qmap heuristic | 9 | 1.3% |
| pytket LexiRoute | 9 | 1.3% |

## 3. Known optima and lower bounds: gap of the best baseline

A "proven optimum" gives the true gap; the gap to a "lower bound" is an upper bound on the true gap; an "upper bound" is the value of a known construction (a published construction, or a constructed circuit verified by this benchmark). Reproduce as above (CSV: `C_optimum_gap.csv`)

| Split | Kind | Track | Entries | With verified baseline | Baseline reaches the value | Mean gap | Max gap |
|---|---|---|---|---|---|---|---|
| probe | proven optimum | depth2q | 60 | 60 | 43 | 2.12 | 12 |
| probe | proven optimum | swaps | 60 | 60 | 43 | 1.83 | 16 |
| test_ood | proven optimum | depth2q | 300 | 300 | 255 | 6.85 | 238 |
| test_ood | proven optimum | swaps | 300 | 300 | 243 | 8.20 | 265 |
| test_ood | constructed value (not independently verified) | swaps | 160 | 160 | 48 | 1010.79 | 4990 |

**probe, entry by entry**:

| Instance | Track | Kind | Value | Best baseline | Source | Gap |
|---|---|---|---|---|---|---|
| C.queko.16QBT_05CYC_TFL_0 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_0 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_1 | depth2q | proven optimum | 4 | 4 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_1 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_2 | depth2q | proven optimum | 4 | 4 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_2 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_3 | depth2q | proven optimum | 4 | 4 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_3 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_4 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_4 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_5 | depth2q | proven optimum | 4 | 4 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_5 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_6 | depth2q | proven optimum | 4 | 4 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_6 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_7 | depth2q | proven optimum | 4 | 4 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_7 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_8 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_8 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_9 | depth2q | proven optimum | 4 | 4 | pytket LexiRoute | 0 |
| C.queko.16QBT_05CYC_TFL_9 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_0 | depth2q | proven optimum | 7 | 7 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_0 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_1 | depth2q | proven optimum | 7 | 7 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_1 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_2 | depth2q | proven optimum | 7 | 7 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_2 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_3 | depth2q | proven optimum | 8 | 8 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_3 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_4 | depth2q | proven optimum | 7 | 7 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_4 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_5 | depth2q | proven optimum | 7 | 7 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_5 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_6 | depth2q | proven optimum | 7 | 7 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_6 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_7 | depth2q | proven optimum | 6 | 6 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_7 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_8 | depth2q | proven optimum | 7 | 7 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_8 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_9 | depth2q | proven optimum | 7 | 7 | pytket LexiRoute | 0 |
| C.queko.16QBT_10CYC_TFL_9 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_0 | depth2q | proven optimum | 11 | 11 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_0 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_1 | depth2q | proven optimum | 11 | 11 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_1 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_2 | depth2q | proven optimum | 10 | 10 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_2 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_3 | depth2q | proven optimum | 10 | 10 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_3 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_4 | depth2q | proven optimum | 9 | 9 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_4 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_5 | depth2q | proven optimum | 10 | 10 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_5 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_6 | depth2q | proven optimum | 9 | 9 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_6 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_7 | depth2q | proven optimum | 10 | 10 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_7 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_8 | depth2q | proven optimum | 10 | 10 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_8 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_9 | depth2q | proven optimum | 11 | 11 | pytket LexiRoute | 0 |
| C.queko.16QBT_15CYC_TFL_9 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_0 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_0 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_1 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_1 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_2 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_2 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_3 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_3 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_4 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_4 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_5 | depth2q | proven optimum | 4 | 12 | qiskit LightSABRE (anytime) | 8 |
| C.queko.54QBT_05CYC_QSE_5 | swaps | proven optimum | 0 | 12 | qiskit LightSABRE (anytime) | 12 |
| C.queko.54QBT_05CYC_QSE_6 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_6 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_7 | depth2q | proven optimum | 5 | 14 | qiskit LightSABRE (anytime) | 9 |
| C.queko.54QBT_05CYC_QSE_7 | swaps | proven optimum | 0 | 16 | qiskit LightSABRE (anytime) | 16 |
| C.queko.54QBT_05CYC_QSE_8 | depth2q | proven optimum | 5 | 5 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_8 | swaps | proven optimum | 0 | 0 | pytket LexiRoute | 0 |
| C.queko.54QBT_05CYC_QSE_9 | depth2q | proven optimum | 5 | 13 | qiskit LightSABRE (anytime) | 8 |
| C.queko.54QBT_05CYC_QSE_9 | swaps | proven optimum | 0 | 14 | qiskit LightSABRE (anytime) | 14 |
| ... (120 entries in all, see CSV) | | | | | | |

## 4. Instances where the best baseline already reaches the optimum

584 (instance, track) pairs in all (CSV: `C_baseline_at_optimum.csv`). By split: probe 86, test_ood 498.

## 5. Unavailable, crash, timeout, unverified and unsupported list

Aggregated by (tool, track, status); individual records in `data/v1/baselines/C/records.jsonl` (CSV: `C_non_pass.csv`)

| Tool | Track | Status | Count | Example instance | Reason (excerpt) |
|---|---|---|---|---|---|
| OLSQ2 (TB, swap objective) | depth2q | unsupported | 1356 | C.hamlib.heis.graph-2D-grid-nonpbc-qubitnodes_Lx-2_Ly-53_h-1 | OLSQ2 limited to <= 16 qubits and <= 80 gates here |
| OLSQ2 (TB, swap objective) | swaps | unsupported | 1356 | C.hamlib.heis.graph-2D-grid-nonpbc-qubitnodes_Lx-2_Ly-53_h-1 | OLSQ2 limited to <= 16 qubits and <= 80 gates here |
| OLSQ2 (TB, swap objective) | swaps_commuting | unsupported | 567 | C.hamlib.heis.graph-2D-grid-nonpbc-qubitnodes_Lx-2_Ly-53_h-1 | OLSQ2 limited to <= 16 qubits and <= 80 gates here |
| qiskit Commuting2qGateRouter | swaps_commuting | unsupported | 231 | C.hamlib.heis.graph-2D-grid-nonpbc-qubitnodes_Lx-2_Ly-53_h-1 | no simple device path covering the logical qubits was found |
| mqt.qmap heuristic | depth2q | timeout | 110 | C.mqtbench.graphstate.n24 | killed after 80.2 s (budget 60.0 s + grace 20.0 s) |
| mqt.qmap heuristic | swaps | timeout | 109 | C.mqtbench.graphstate.n24 | killed after 80.2 s (budget 60.0 s + grace 20.0 s) |
| OLSQ2 (TB, swap objective) | depth2q | timeout | 106 | C.hamlib.heis.graph-2D-grid-pbc-qubitnodes_Lx-3_Ly-3_h-1 | OLSQ2 did not finish within the budget |
| OLSQ2 (TB, swap objective) | swaps | timeout | 106 | C.hamlib.heis.graph-2D-grid-pbc-qubitnodes_Lx-3_Ly-3_h-1 | OLSQ2 did not finish within the budget |
| OLSQ2 (TB, swap objective) | swaps_commuting | timeout | 74 | C.hamlib.heis.graph-2D-grid-pbc-qubitnodes_Lx-3_Ly-3_h-1 | OLSQ2 did not finish within the budget |
| mqt.qmap heuristic | swaps_commuting | timeout | 61 | C.qaoa.heavy_hex.n147.s23306 | result delivered after the budget (72.1 s) |
| pytket LexiRoute | depth2q | timeout | 3 | C.hamlib.heis.graph-2D-triag-nonpbc-qubitnodes_Lx-13_Ly-13_h-1 | killed after 80.0 s (budget 60.0 s + grace 20.0 s) |
| pytket LexiRoute | swaps | timeout | 3 | C.hamlib.heis.graph-2D-triag-nonpbc-qubitnodes_Lx-13_Ly-13_h-1 | killed after 80.0 s (budget 60.0 s + grace 20.0 s) |
| pytket LexiRoute | swaps_commuting | timeout | 3 | C.hamlib.heis.graph-2D-triag-nonpbc-qubitnodes_Lx-13_Ly-13_h-1 | killed after 80.2 s (budget 60.0 s + grace 20.0 s) |
| qiskit LightSABRE (anytime) | swaps | timeout | 1 | C.queko.20QBT_700CYC_QSE_3 | result delivered after the budget (60.1 s) |
| qiskit LightSABRE + block reordering (anytime) | swaps_commuting | timeout | 1 | C.trotter.random_sparse.n46.s12400 | result delivered after the budget (60.0 s) |

## test_ood by source/family

Main track `swaps`. OOD conclusions should be reported per source; do not mix different sources into one average.

| Source/family | Instances | With verified baseline | Median best baseline | With known optimum/constructed value | Of these, baseline reaches the value | Note |
|---|---|---|---|---|---|---|
| hamlib | 55 | 55 | 284 | 0 | 0 | unseen lattice Hamiltonians (no known optimum) |
| mqtbench | 40 | 40 | 38.5 | 0 | 0 | algorithm families not used in training (no known optimum) |
| qubikos | 160 | 160 | 165.0 | 160 | 48 | constructed optimal SWAP count known (not independently verified): the external source with real room for improvement |
| queko | 300 | 300 | 0.0 | 300 | 243 | zero-SWAP construction (known optimum 0, with witness): mainly a correctness check, little room for improvement, should not be merged into a geometric-mean score |

## Compute consistency of time-limited baselines

Baselines run as parallel processes on an Apple M3 Max (12 performance cores + 4 efficiency cores), each job single-threaded with a 60 s wall-clock budget. When the number of parallel jobs exceeds the number of performance cores, some jobs land on efficiency cores; time-limited tools (searches that improve over time, wall-clock-limited solvers) therefore do not get exactly the same compute within the same 60 s.
The 17130 earlier records have no concurrency recorded at run time and were given `concurrency_estimate`: the number of simultaneously running qbank jobs reconstructed from the start/end times of all cached records (1 s resolution, excluding the load of other processes), median 16, maximum 22.

For the final evaluation, candidate programs and time-limited baselines should be compared under the same conditions: `qbank rebaseline <C> --split test --tools <time-limited tools>` reruns these baselines on the test instances at fixed concurrency (default = number of performance cores, i.e. 12); results are stored separately in `data/v1/baselines/<C>/rebaseline_w<concurrency>.jsonl` (cache namespace `<C>-rebaseline-w<concurrency>`) and do not overwrite best_known. Without `--tools`, the budget-sensitive tools of the quality-time curve are used.

## Quality-time curve (0.1x / 1x / 10x budget)

On 24 instances from stratified sampling (one per family x size bin, plus instances that timed out at 60 s), budget-sensitive tools (tools that improve over time, and tools that timed out at 60 s) were rerun at 6 s and 600 s; the 60 s point is the main baseline record. These results are stored separately and **do not enter best_known** (best_known is defined by the uniform 60 s budget). Individual rows in `C_quality_time.csv`, reproduce: `qbank curve C`.

| Tool | Instances | Pass at 6 s | Pass at 60 s | Pass at 600 s | Timeout at 60 s → pass at 600 s | 600 s better than 60 s | Median improvement (60 s/600 s) |
|---|---|---|---|---|---|---|---|
| OLSQ2 (TB, swap objective) | 24 | 1 | 2 | 4 | 2 | 0 | 1.000 |
| mqt.qmap heuristic | 24 | 18 | 19 | 19 | 0 | 0 | 1.000 |
| pytket LexiRoute | 24 | 20 | 22 | 22 | 0 | 0 | 1.000 |
| qiskit LightSABRE (anytime) | 24 | 24 | 24 | 24 | 0 | 11 | 1.006 |

(instance, tool) pairs that time out at 60 s and pass at 600 s: C.hamlib.tfim.graph-2D-triag-nonpbc-qubitnodes_Lx-3_Ly-5_h-1 / OLSQ2 (TB, swap objective) (value at 600 s 4); C.qaoa.grid.n14.s206 / OLSQ2 (TB, swap objective) (value at 600 s 5). On these instances the 60 s baseline underestimates existing tools; consult this table when using best_known.

## Baseline reproducibility (rerun of 20 random records)

Per task spec section 8, 20 randomly sampled passing baseline records were rerun: deterministic tools must give a gate-for-gate identical circuit, randomized tools are rerun once with the recorded trial seed. Result: **20/20 identical**. Reproduce: `qbank repro C` (CSV: `C_repro.csv`).

Excluded from sampling (time-limited searches whose results depend on run time and cannot be reproduced bit for bit under a different machine load): OLSQ2 (TB, swap objective).

| Instance | Track | Tool | Seed | Trial seed | Identical |
|---|---|---|---|---|---|
| C.struct_random.random_sparse.n14.s407 | swaps | pytket LexiRoute | 2074599965 |  | yes |
| C.qubikos.Aspen-4_10_300_3 | swaps | pytket LexiRoute | 1376907604 |  | yes |
| C.queko.54QBT_30CYC_QSE_4 | swaps | pytket LexiRoute | 983797610 |  | yes |
| C.qaoa.line.n9.s6 | swaps_commuting | qiskit LightSABRE (anytime) | 1014960913 | 1014961359 | yes |
| C.qaoa.line.n65.s23003 | swaps_commuting | qiskit Commuting2qGateRouter | 261816490 |  | yes |
| C.struct_random.ring.n25.s11101 | depth2q | qiskit LightSABRE (anytime) | 1589016593 | 1589018179 | yes |
| C.qaoa.line.n15.s8 | swaps_commuting | qiskit LightSABRE + block reordering (anytime) | 93103558 | 93539103 | yes |
| C.mqtbench.qpeexact.n16 | swaps | qiskit LightSABRE (anytime) | 1456943829 | 1456944096 | yes |
| C.hamlib.heis.graph-2D-grid-nonpbc-qubitnodes_Lx-5_Ly-31_h-1 | swaps_commuting | mqt.qmap heuristic | 1780396547 |  | yes |
| C.struct_random.ring.n14.s105 | depth2q | mqt.qmap heuristic | 229110376 |  | yes |
| C.queko.16QBT_400CYC_QSE_7 | swaps | pytket LexiRoute | 1630026076 |  | yes |
| C.qaoa.heavy_hex.n47.s2304 | depth2q | qiskit LightSABRE (anytime) | 1739989477 | 1739989846 | yes |
| C.trotter.ring.n34.s2110 | depth2q | qiskit LightSABRE (anytime) | 1836864244 | 1836866933 | yes |
| C.trotter.grid.n57.s2211 | depth2q | mqt.qmap heuristic | 1850633499 |  | yes |
| C.hamlib.heis.graph-2D-triag-pbc-qubitnodes_Lx-5_Ly-37_h-1 | depth2q | pytket LexiRoute | 1874709062 |  | yes |
| C.trotter.ring.n20.s11103 | swaps_commuting | pytket LexiRoute | 636698585 |  | yes |
| C.qaoa.random_sparse.n143.s23403 | swaps | mqt.qmap heuristic | 1602224923 |  | yes |
| C.queko.20QBT_500CYC_QSE_1 | depth2q | mqt.qmap heuristic | 704218070 |  | yes |
| C.trotter.heavy_hex.n37.s12303 | swaps_commuting | qiskit LightSABRE + block reordering (anytime) | 1305127667 | 1320086658 | yes |
| C.trotter.grid.n56.s12203 | swaps | qiskit LightSABRE (anytime) | 705836515 | 705838270 | yes |

