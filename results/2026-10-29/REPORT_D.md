# qbank v1 - Category D (non-Clifford state preparation) report

Generated: 2026-10-29. This report is generated entirely by `qbank report D` from the files in `data/v1/`.

## 1. Instances per split (by family and size bin)

Reproduce: `qbank generate D` (CSV: `D_counts.csv`)

| Split | Family | Size bin | Count |
|---|---|---|---|
| train | dense | S | 96 |
| train | dicke | L | 3 |
| train | dicke | M | 10 |
| train | dicke | S | 4 |
| train | sparse | L | 36 |
| train | sparse | M | 36 |
| train | sparse | S | 36 |
| train | w | L | 10 |
| train | w | M | 10 |
| train | w | S | 4 |
| val | dense | S | 30 |
| val | dicke | L | 1 |
| val | dicke | M | 2 |
| val | dicke | S | 1 |
| val | sparse | L | 12 |
| val | sparse | M | 12 |
| val | sparse | S | 12 |
| val | w | L | 2 |
| val | w | M | 2 |
| val | w | S | 1 |
| test_in | dense | M | 30 |
| test_in | dicke | L | 16 |
| test_in | sparse | L | 4 |
| test_in | sparse | M | 4 |
| test_in | sparse | S | 4 |
| test_in | sparse | XL | 24 |
| test_in | w | L | 3 |
| test_in | w | XL | 7 |
| test_ood | dicke | L | 8 |
| test_ood | dicke | M | 29 |
| test_ood | dicke | S | 3 |
| test_ood | sparse_struct | L | 18 |
| test_ood | sparse_struct | M | 18 |
| test_ood | sparse_struct | S | 12 |
| probe | dense | S | 30 |

Total: probe 30, test_in 92, test_ood 88, train 245, val 75; 530 in all.

## 2. Share of instances on which each tool is the best baseline, per track

Definition: for each (instance, track), take the verified records with the smallest value of the track metric; on ties each tool is counted once. Reproduce: `qbank generate D && qbank baselines D && qbank optimal D && qbank aggregate D && qbank report D` (CSV: `D_best_tool_share.csv`)

### Track `cx` (530 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| qclib MergeInitialize | 249 | 47.0% |
| qclib LowRankInitialize | 140 | 26.4% |
| Dicke construction (Bärtschi-Eidenbenz) | 73 | 13.8% |
| bqskit compile(StateVector) | 72 | 13.6% |
| qclib SVDInitialize | 56 | 10.6% |
| qclib UCGEInitialize | 11 | 2.1% |
| qiskit StatePreparation | 11 | 2.1% |

### Track `cx@F0.99` (414 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| qclib MergeInitialize | 210 | 50.7% |
| qclib BaaLowRankInitialize (approx) | 135 | 32.6% |
| qclib LowRankInitialize | 134 | 32.4% |
| bqskit compile(StateVector) | 70 | 16.9% |
| qclib SVDInitialize | 53 | 12.8% |
| qclib UCGEInitialize | 9 | 2.2% |
| qiskit StatePreparation | 9 | 2.2% |

### Track `depth2q@line` (530 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| qclib MergeInitialize | 207 | 39.1% |
| qclib LowRankInitialize | 148 | 27.9% |
| Dicke construction (Bärtschi-Eidenbenz) | 73 | 13.8% |
| qclib SVDInitialize | 69 | 13.0% |
| bqskit compile(StateVector) | 53 | 10.0% |
| W constructions (cascade, log-depth tree) | 39 | 7.4% |
| qclib UCGEInitialize | 10 | 1.9% |
| qiskit StatePreparation | 10 | 1.9% |

## 3. Known optima and lower bounds: gap of the best baseline

A "proven optimum" gives the true gap; the gap to a "lower bound" is an upper bound on the true gap; an "upper bound" is the value of a known construction (a published construction, or a constructed circuit verified by this benchmark). Reproduce as above (CSV: `D_optimum_gap.csv`)

| Split | Kind | Track | Entries | With verified baseline | Baseline reaches the value | Mean gap | Max gap |
|---|---|---|---|---|---|---|---|
| probe | lower bound | cx | 20 | 20 | 0 | 1.00 | 1 |
| probe | numerical optimum (unproven) | cx | 20 | 20 | 20 | 0.00 | 0 |
| probe | proven optimum | cx | 10 | 10 | 10 | 0.00 | 0 |
| probe | upper bound (constructed value) | cx | 20 | 20 | 20 | 0.00 | 0 |
| test_in | lower bound | cx | 92 | 92 | 0 | 519.51 | 3580 |
| test_ood | lower bound | cx | 88 | 88 | 0 | 399.53 | 1937 |
| test_ood | unproven_bound | cx | 18 | 18 | 0 | 590.22 | 1922 |
| train | lower bound | cx | 245 | 245 | 1 | 116.63 | 1196 |
| train | numerical optimum (unproven) | cx | 16 | 16 | 15 | 0.06 | 1 |
| train | upper bound (constructed value) | cx | 16 | 16 | 15 | 0.06 | 1 |
| val | lower bound | cx | 75 | 75 | 0 | 174.88 | 1148 |
| val | numerical optimum (unproven) | cx | 5 | 5 | 5 | 0.00 | 0 |
| val | upper bound (constructed value) | cx | 5 | 5 | 5 | 0.00 | 0 |

**probe, entry by entry**:

| Instance | Track | Kind | Value | Best baseline | Source | Gap |
|---|---|---|---|---|---|---|
| D.dense.n2.s40200 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n2.s40201 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n2.s40202 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n2.s40203 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n2.s40204 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n2.s40205 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n2.s40206 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n2.s40207 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n2.s40208 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n2.s40209 | cx | proven optimum | 1 | 1 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40300 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40300 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40300 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40301 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40301 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40301 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40302 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40302 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40302 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40303 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40303 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40303 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40304 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40304 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40304 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40305 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40305 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40305 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40306 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40306 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40306 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40307 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40307 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40307 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40308 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40308 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40308 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40309 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40309 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40309 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40310 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40310 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40310 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40311 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40311 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40311 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40312 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40312 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40312 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40313 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40313 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40313 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40314 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40314 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40314 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40315 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40315 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40315 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40316 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40316 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40316 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40317 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40317 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40317 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40318 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40318 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40318 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40319 | cx | lower bound | 2 | 3 | bqskit compile(StateVector) | 1 |
| D.dense.n3.s40319 | cx | upper bound (constructed value) | 3 | 3 | bqskit compile(StateVector) | 0 |
| D.dense.n3.s40319 | cx | numerical optimum (unproven) | 3 | 3 | bqskit compile(StateVector) | 0 |

## 4. Instances where the best baseline already reaches the optimum

10 (instance, track) pairs in all (CSV: `D_baseline_at_optimum.csv`). By split: probe 10.

## 5. Unavailable, crash, timeout, unverified and unsupported list

Aggregated by (tool, track, status); individual records in `data/v1/baselines/D/records.jsonl` (CSV: `D_non_pass.csv`)

| Tool | Track | Status | Count | Example instance | Reason (excerpt) |
|---|---|---|---|---|---|
| W constructions (cascade, log-depth tree) | cx | unsupported | 491 | D.dense.n10.s21000 | target is not a W state |
| W constructions (cascade, log-depth tree) | depth2q@line | unsupported | 491 | D.dense.n10.s21000 | target is not a W state |
| Dicke construction (Bärtschi-Eidenbenz) | cx | unsupported | 414 | D.dense.n10.s21000 | target is not a Dicke state |
| Dicke construction (Bärtschi-Eidenbenz) | cx@F0.99 | unsupported | 414 | D.dense.n10.s21000 | target is not a Dicke state |
| Dicke construction (Bärtschi-Eidenbenz) | depth2q@line | unsupported | 414 | D.dense.n10.s21000 | target is not a Dicke state |
| W constructions (cascade, log-depth tree) | cx@F0.99 | unsupported | 414 | D.dense.n10.s21000 | target is not a W state |
| qclib MergeInitialize | depth2q@line | fail | 19 | D.dense.n10.s21000 | fail: fidelity 0.999999977744 < 0.999999999 |
| qclib MergeInitialize | depth2q@line | unverified | 10 | D.dicke.n17.k4 | verification exceeded 600 s |
| qclib MergeInitialize | depth2q@line | timeout | 7 | D.dicke.n13.k6 | routing finished after the budget |
| bqskit compile(StateVector) | depth2q@line | tool error | 3 | D.dense.n3.s40308 | RuntimeError: BQSKit failed (exit 1) |
| qiskit StatePreparation | cx | fail | 3 | D.sparse.n13.m59.s20003 | fail: fidelity 0.570450619557 < 0.999999999 |
| qiskit StatePreparation | cx@F0.99 | fail | 3 | D.sparse.n13.m59.s20003 | fail: fidelity 0.570450619557 < 0.99 |
| qiskit StatePreparation | depth2q@line | fail | 3 | D.sparse.n13.m59.s20003 | fail: fidelity 0.570450619557 < 0.999999999 |
| bqskit compile(StateVector) | cx | timeout | 2 | D.dense.n3.s305 | BQSKit did not finish within the budget |
| bqskit compile(StateVector) | cx@F0.99 | timeout | 1 | D.dense.n2.s40200 | BQSKit did not finish within the budget |
| bqskit compile(StateVector) | depth2q@line | timeout | 1 | D.dense.n4.s407 | BQSKit did not finish within the budget |
| qclib LowRankInitialize | cx | fail | 1 | D.sparse.n14.m55.s30 | fail: fidelity 0.999999997545 < 0.999999999 |
| qclib LowRankInitialize | depth2q@line | fail | 1 | D.sparse.n14.m55.s30 | fail: fidelity 0.999999997545 < 0.999999999 |
| qclib MergeInitialize | cx | timeout | 1 | D.dicke.n14.k7 | result delivered after the budget (65.2 s) |
| qiskit StatePreparation | cx | tool error | 1 | D.sparse.n14.m7.s15 | TranspilerError: 'HighLevelSynthesis is unable to synthesize "state_preparation"' |
| qiskit StatePreparation | cx@F0.99 | tool error | 1 | D.sparse.n14.m7.s15 | TranspilerError: 'HighLevelSynthesis is unable to synthesize "state_preparation"' |
| qiskit StatePreparation | depth2q@line | tool error | 1 | D.sparse.n14.m7.s15 | TranspilerError: 'HighLevelSynthesis is unable to synthesize "state_preparation"' |

## test_ood by source/family

Main track `cx`. OOD conclusions should be reported per source; do not mix different sources into one average.

| Source/family | Instances | With verified baseline | Median best baseline | With known optimum/constructed value | Of these, baseline reaches the value | Note |
|---|---|---|---|---|---|---|
| dicke | 40 | 40 | 230.0 | 40 | 0 |  |
| sparse_struct | 48 | 48 | 471.5 | 48 | 0 |  |

## Compute consistency of time-limited baselines

Baselines run as parallel processes on an Apple M3 Max (12 performance cores + 4 efficiency cores), each job single-threaded with a 60 s wall-clock budget. When the number of parallel jobs exceeds the number of performance cores, some jobs land on efficiency cores; time-limited tools (searches that improve over time, wall-clock-limited solvers) therefore do not get exactly the same compute within the same 60 s.
The 8283 earlier records have no concurrency recorded at run time and were given `concurrency_estimate`: the number of simultaneously running qbank jobs reconstructed from the start/end times of all cached records (1 s resolution, excluding the load of other processes), median 15, maximum 20.

For the final evaluation, candidate programs and time-limited baselines should be compared under the same conditions: `qbank rebaseline <C> --split test --tools <time-limited tools>` reruns these baselines on the test instances at fixed concurrency (default = number of performance cores, i.e. 12); results are stored separately in `data/v1/baselines/<C>/rebaseline_w<concurrency>.jsonl` (cache namespace `<C>-rebaseline-w<concurrency>`) and do not overwrite best_known. Without `--tools`, the budget-sensitive tools of the quality-time curve are used.

## Quality-time curve (0.1x / 1x / 10x budget)

On 19 instances from stratified sampling (one per family x size bin, plus instances that timed out at 60 s), budget-sensitive tools (tools that improve over time, and tools that timed out at 60 s) were rerun at 6 s and 600 s; the 60 s point is the main baseline record. These results are stored separately and **do not enter best_known** (best_known is defined by the uniform 60 s budget). Individual rows in `D_quality_time.csv`, reproduce: `qbank curve D`.

| Tool | Instances | Pass at 6 s | Pass at 60 s | Pass at 600 s | Timeout at 60 s → pass at 600 s | 600 s better than 60 s | Median improvement (60 s/600 s) |
|---|---|---|---|---|---|---|---|
| bqskit compile(StateVector) | 2 | 1 | 0 | 2 | 2 | 0 | - |
| qclib MergeInitialize | 19 | 17 | 18 | 19 | 1 | 0 | 1.000 |

(instance, tool) pairs that time out at 60 s and pass at 600 s: D.dense.n3.s305 / bqskit compile(StateVector) (value at 600 s 3); D.dense.n4.s10400 / bqskit compile(StateVector) (value at 600 s 6); D.dicke.n14.k7 / qclib MergeInitialize (value at 600 s 344447). On these instances the 60 s baseline underestimates existing tools; consult this table when using best_known.

## Baseline reproducibility (rerun of 20 random records)

Per task spec section 8, 20 randomly sampled passing baseline records were rerun: deterministic tools must give a gate-for-gate identical circuit, randomized tools are rerun once with the recorded trial seed. Result (run 2026-10-29): of 20 records, **5 gate-for-gate identical**, **15 reruns pass the checker** (tools that depend on the system's floating-point linear algebra are only required to pass the checker on rerun; cost differences in the table below), 0 not reproduced. Reproduce: `qbank repro D` (CSV: `D_repro.csv`).

| Instance | Track | Tool | Seed | Trial seed | Identical |
|---|---|---|---|---|---|
| D.sparse.n23.m16.s2024 | cx | qclib MergeInitialize | 1532836623 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'two_qubit_gates': [202, 221], 'depth': [260, 311], 'two_qubit_depth': [197, 211], 'gate_count': [327, 399], 'cx_count': [202, 221]}) |
| D.dense.n9.s20911 | depth2q@line | qclib UCGEInitialize | 627574927 |  | yes (rerun passes the checker; same costs) |
| D.dense.n7.s712 | cx | qiskit StatePreparation | 467882571 |  | yes |
| D.dense.n3.s303 | cx@F0.99 | qiskit StatePreparation | 1560890044 |  | yes |
| D.dense.n3.s40305 | cx@F0.99 | qiskit StatePreparation | 703849371 |  | yes |
| D.dense.n5.s514 | depth2q@line | qclib SVDInitialize | 1557861124 |  | yes (rerun passes the checker; same costs) |
| D.dense.n3.s310 | cx@F0.99 | bqskit compile(StateVector) | 1837881123 |  | yes |
| D.sparse_struct.hamming_r3.ph.s30500 | cx@F0.99 | qclib SVDInitialize | 847196274 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'two_qubit_gates': [119, 126], 'depth': [190, 228], 'two_qubit_depth': [95, 103], 'gate_count': [317, 377], 'cx_count': [119, 126]}) |
| D.sparse_struct.hamming_r3.ph.s30502 | cx@F0.99 | qclib SVDInitialize | 1586529203 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'two_qubit_gates': [116, 125], 'depth': [190, 228], 'two_qubit_depth': [95, 103], 'gate_count': [307, 371], 'cx_count': [116, 125]}) |
| D.sparse_struct.rm1_m3.amp.s30200 | depth2q@line | qclib UCGEInitialize | 1063933543 |  | yes (rerun passes the checker; same costs) |
| D.sparse.n12.m5.s3 | cx | qiskit StatePreparation | 671501780 |  | yes |
| D.sparse.n9.m60.s17 | cx@F0.99 | qclib LowRankInitialize | 842779240 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'depth': [657, 769], 'gate_count': [1148, 1351]}) |
| D.dense.n4.s413 | depth2q@line | qclib MergeInitialize | 1596396825 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'two_qubit_gates': [278, 282], 'depth': [390, 405], 'two_qubit_depth': [246, 250], 'gate_count': [556, 575], 'cx_count': [278, 282]}) |
| D.sparse_struct.rm1_m3.ph.s30202 | depth2q@line | qclib SVDInitialize | 1436896107 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'two_qubit_gates': [341, 370], 'depth': [287, 315], 'two_qubit_depth': [175, 192], 'gate_count': [803, 872], 'cx_count': [341, 370]}) |
| D.dense.n2.s40201 | cx@F0.99 | qclib MergeInitialize | 328629383 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'two_qubit_gates': [3, 5], 'depth': [7, 15], 'two_qubit_depth': [3, 5], 'gate_count': [11, 17], 'cx_count': [3, 5]}) |
| D.dense.n7.s10700 | cx | qclib SVDInitialize | 1390919129 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'depth': [205, 233], 'gate_count': [336, 386]}) |
| D.dense.n9.s20913 | cx@F0.99 | qclib BaaLowRankInitialize (approx) | 1905468415 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'depth': [657, 769], 'gate_count': [1149, 1351]}) |
| D.dense.n3.s40313 | cx@F0.99 | qclib SVDInitialize | 352228611 |  | yes (rerun passes the checker; same costs) |
| D.sparse.n8.m8.s6 | cx | qclib MergeInitialize | 490860361 |  | yes (rerun passes the checker; cost differs from stored (stored, rerun): {'two_qubit_gates': [28, 32], 'depth': [45, 57], 'two_qubit_depth': [28, 32], 'gate_count': [61, 69], 'cx_count': [28, 32]}) |
| D.dense.n8.s810 | depth2q@line | qclib UCGEInitialize | 1987486850 |  | yes (rerun passes the checker; same costs) |

