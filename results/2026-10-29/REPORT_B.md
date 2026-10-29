# qbank v1 - Category B (classical-function oracle compilation) report

Generated: 2026-10-29. This report is generated entirely by `qbank report B` from the files in `data/v1/`.

## 1. Instances per split (by family and size bin)

Reproduce: `qbank generate B` (CSV: `B_counts.csv`)

| Split | Family | Size bin | Count |
|---|---|---|---|
| train | arith | L | 4 |
| train | arith | M | 16 |
| train | arith | S | 21 |
| train | compare | L | 16 |
| train | compare | M | 24 |
| train | compare | S | 29 |
| train | rand3sat | L | 12 |
| train | rand3sat | M | 12 |
| train | rand3sat | S | 12 |
| train | simon3 | L | 12 |
| train | simon3 | M | 12 |
| train | simon3 | S | 12 |
| train | sudoku | L | 12 |
| train | sudoku | M | 12 |
| train | sudoku | S | 12 |
| train | triangle | L | 12 |
| train | triangle | M | 12 |
| train | triangle | S | 12 |
| val | arith | L | 6 |
| val | arith | M | 7 |
| val | arith | S | 2 |
| val | compare | L | 8 |
| val | compare | M | 5 |
| val | compare | S | 6 |
| val | rand3sat | L | 4 |
| val | rand3sat | M | 4 |
| val | rand3sat | S | 4 |
| val | simon3 | L | 4 |
| val | simon3 | M | 4 |
| val | simon3 | S | 4 |
| val | sudoku | L | 3 |
| val | sudoku | M | 2 |
| val | triangle | L | 4 |
| val | triangle | M | 4 |
| val | triangle | S | 4 |
| test_in | arith | L | 1 |
| test_in | arith | XL | 6 |
| test_in | compare | XL | 12 |
| test_in | rand3sat | L | 2 |
| test_in | rand3sat | M | 2 |
| test_in | rand3sat | S | 2 |
| test_in | rand3sat | XL | 12 |
| test_in | simon3 | L | 2 |
| test_in | simon3 | M | 2 |
| test_in | simon3 | S | 2 |
| test_in | simon3 | XL | 12 |
| test_in | sudoku | L | 2 |
| test_in | sudoku | M | 1 |
| test_in | sudoku | XL | 12 |
| test_in | triangle | L | 2 |
| test_in | triangle | M | 2 |
| test_in | triangle | S | 2 |
| test_in | triangle | XL | 12 |
| test_ood | epfl | S | 4 |
| test_ood | epfl | XL | 1 |
| test_ood | iscas85 | XL | 3 |
| test_ood | iscas85 | between | 2 |
| test_ood | mcnc | L | 4 |
| test_ood | mcnc | M | 4 |
| test_ood | mcnc | S | 5 |
| test_ood | mcnc | XS | 1 |
| test_ood | mcnc | between | 6 |
| test_ood | satlib | L | 24 |
| test_ood | satlib | XL | 24 |
| test_ood | sbox | S | 6 |
| test_ood | sbox | XS | 8 |
| probe | probe_small | probe | 20 |

Total: probe 20, test_in 88, test_ood 92, train 254, val 75; 529 in all.

## 2. Share of instances on which each tool is the best baseline, per track

Definition: for each (instance, track), take the verified records with the smallest value of the track metric; on ties each tool is counted once. Reproduce: `qbank generate B && qbank baselines B && qbank optimal B && qbank aggregate B && qbank report B` (CSV: `B_best_tool_share.csv`)

### Track `cx@inf` (529 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| XAG + MC (Meuli et al. 2019, re-impl.) | 218 | 41.2% |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 174 | 32.9% |
| solution enumeration + prefix-trie MCX | 126 | 23.8% |
| bennett(abc resyn2) | 74 | 14.0% |
| esop(qiskit EsopGenerator)+qiskit MCX | 30 | 5.7% |
| cone_bennett(abc resyn2) | 21 | 4.0% |
| per-clause MCX (qiskit MCX) | 7 | 1.3% |

### Track `t_mbu@inf` (529 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 395 | 74.7% |
| XAG + MC (Meuli et al. 2019, re-impl.) | 83 | 15.7% |
| solution enumeration + prefix-trie MCX | 72 | 13.6% |
| bennett(abc resyn2) | 57 | 10.8% |
| cone_bennett(abc resyn2) | 55 | 10.4% |
| bennett(aig) | 31 | 5.9% |

### Track `tof@1.5bmin` (529 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 286 | 54.1% |
| solution enumeration + prefix-trie MCX | 179 | 33.8% |
| XAG + MC (Meuli et al. 2019, re-impl.) | 107 | 20.2% |
| esop(qiskit EsopGenerator)+qiskit MCX | 62 | 11.7% |
| cone_bennett(abc resyn2) | 35 | 6.6% |
| per-clause MCX (qiskit MCX) | 24 | 4.5% |
| pebbling SAT (Meuli et al. 2019, re-impl.) | 12 | 2.3% |
| bennett(abc resyn2) | 3 | 0.6% |

### Track `tof@bmin` (529 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 201 | 38.0% |
| esop(qiskit EsopGenerator)+qiskit MCX | 162 | 30.6% |
| solution enumeration + prefix-trie MCX | 133 | 25.1% |
| cone_bennett(abc resyn2) | 56 | 10.6% |
| XAG + MC (Meuli et al. 2019, re-impl.) | 55 | 10.4% |
| per-clause MCX (qiskit MCX) | 9 | 1.7% |
| bennett(abc resyn2) | 2 | 0.4% |

### Track `tof@inf` (529 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 409 | 77.3% |
| solution enumeration + prefix-trie MCX | 156 | 29.5% |
| XAG + MC (Meuli et al. 2019, re-impl.) | 136 | 25.7% |
| per-clause MCX (qiskit MCX) | 29 | 5.5% |
| esop(qiskit EsopGenerator)+qiskit MCX | 23 | 4.3% |
| bennett(abc resyn2) | 3 | 0.6% |
| cone_bennett(abc resyn2) | 1 | 0.2% |

### Track `tof_clifford@inf` (63 instances with a verified baseline; 0 without any verified baseline)

| Tool | Times best (including ties) | Share |
|---|---|---|
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) [circuit reused, re-verified on tof_clifford@inf] | 40 | 63.5% |
| XAG + MC (Meuli et al. 2019, re-impl.) [circuit reused, re-verified on tof_clifford@inf] | 23 | 36.5% |

## 3. Known optima and lower bounds: gap of the best baseline

A "proven optimum" gives the true gap; the gap to a "lower bound" is an upper bound on the true gap; an "upper bound" is the value of a known construction (a published construction, or a constructed circuit verified by this benchmark). Reproduce as above (CSV: `B_optimum_gap.csv`)

| Split | Kind | Track | Entries | With verified baseline | Baseline reaches the value | Mean gap | Max gap |
|---|---|---|---|---|---|---|---|
| probe | lower bound | tof@1.5bmin | 20 | 20 | 3 | 29.00 | 128 |
| probe | lower bound | tof@bmin | 20 | 20 | 3 | 42.70 | 149 |
| probe | lower bound | tof@inf | 20 | 20 | 3 | 2.40 | 8 |
| probe | upper bound (constructed value) | tof@inf | 19 | 19 | 14 | -0.32 | 1 |

**probe, entry by entry**:

| Instance | Track | Kind | Value | Best baseline | Source | Gap |
|---|---|---|---|---|---|---|
| B.bitflip.probe.n3.s40300 | tof@1.5bmin | lower bound | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40300 | tof@bmin | lower bound | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40300 | tof@inf | lower bound | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40300 | tof@inf | upper bound (constructed value) | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40301 | tof@1.5bmin | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n3.s40301 | tof@bmin | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n3.s40301 | tof@inf | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n3.s40301 | tof@inf | upper bound (constructed value) | 3 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40302 | tof@1.5bmin | lower bound | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40302 | tof@bmin | lower bound | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40302 | tof@inf | lower bound | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40302 | tof@inf | upper bound (constructed value) | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40303 | tof@1.5bmin | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n3.s40303 | tof@bmin | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n3.s40303 | tof@inf | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n3.s40303 | tof@inf | upper bound (constructed value) | 3 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40304 | tof@1.5bmin | lower bound | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40304 | tof@bmin | lower bound | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40304 | tof@inf | lower bound | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n3.s40304 | tof@inf | upper bound (constructed value) | 1 | 1 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n4.s40400 | tof@1.5bmin | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n4.s40400 | tof@bmin | lower bound | 2 | 19 | esop(qiskit EsopGenerator)+qiskit MCX | 17 |
| B.bitflip.probe.n4.s40400 | tof@inf | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n4.s40400 | tof@inf | upper bound (constructed value) | 3 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n4.s40401 | tof@1.5bmin | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n4.s40401 | tof@bmin | lower bound | 2 | 14 | esop(qiskit EsopGenerator)+qiskit MCX | 12 |
| B.bitflip.probe.n4.s40401 | tof@inf | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n4.s40401 | tof@inf | upper bound (constructed value) | 3 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n4.s40402 | tof@1.5bmin | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n4.s40402 | tof@bmin | lower bound | 2 | 14 | esop(qiskit EsopGenerator)+qiskit MCX | 12 |
| B.bitflip.probe.n4.s40402 | tof@inf | lower bound | 2 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n4.s40402 | tof@inf | upper bound (constructed value) | 3 | 3 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n4.s40403 | tof@1.5bmin | lower bound | 3 | 5 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 2 |
| B.bitflip.probe.n4.s40403 | tof@bmin | lower bound | 3 | 12 | esop(qiskit EsopGenerator)+qiskit MCX | 9 |
| B.bitflip.probe.n4.s40403 | tof@inf | lower bound | 3 | 5 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 2 |
| B.bitflip.probe.n4.s40403 | tof@inf | upper bound (constructed value) | 5 | 5 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 0 |
| B.bitflip.probe.n4.s40404 | tof@1.5bmin | lower bound | 3 | 5 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 2 |
| B.bitflip.probe.n4.s40404 | tof@bmin | lower bound | 3 | 10 | esop(qiskit EsopGenerator)+qiskit MCX | 7 |
| B.bitflip.probe.n4.s40404 | tof@inf | lower bound | 3 | 5 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 2 |
| B.bitflip.probe.n4.s40404 | tof@inf | upper bound (constructed value) | 5 | 5 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 0 |
| B.bitflip.probe.n5.s40500 | tof@1.5bmin | lower bound | 4 | 7 | XAG + MC (Meuli et al. 2019, re-impl.) | 3 |
| B.bitflip.probe.n5.s40500 | tof@bmin | lower bound | 4 | 53 | esop(qiskit EsopGenerator)+qiskit MCX | 49 |
| B.bitflip.probe.n5.s40500 | tof@inf | lower bound | 4 | 7 | XAG + MC (Meuli et al. 2019, re-impl.) | 3 |
| B.bitflip.probe.n5.s40500 | tof@inf | upper bound (constructed value) | 7 | 7 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n5.s40501 | tof@1.5bmin | lower bound | 4 | 7 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 3 |
| B.bitflip.probe.n5.s40501 | tof@bmin | lower bound | 4 | 51 | esop(qiskit EsopGenerator)+qiskit MCX | 47 |
| B.bitflip.probe.n5.s40501 | tof@inf | lower bound | 4 | 7 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 3 |
| B.bitflip.probe.n5.s40501 | tof@inf | upper bound (constructed value) | 7 | 7 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 0 |
| B.bitflip.probe.n5.s40502 | tof@1.5bmin | lower bound | 3 | 5 | XAG + MC (Meuli et al. 2019, re-impl.) | 2 |
| B.bitflip.probe.n5.s40502 | tof@bmin | lower bound | 3 | 35 | esop(qiskit EsopGenerator)+qiskit MCX | 32 |
| B.bitflip.probe.n5.s40502 | tof@inf | lower bound | 3 | 5 | XAG + MC (Meuli et al. 2019, re-impl.) | 2 |
| B.bitflip.probe.n5.s40502 | tof@inf | upper bound (constructed value) | 5 | 5 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n5.s40503 | tof@1.5bmin | lower bound | 4 | 6 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 2 |
| B.bitflip.probe.n5.s40503 | tof@bmin | lower bound | 4 | 44 | esop(qiskit EsopGenerator)+qiskit MCX | 40 |
| B.bitflip.probe.n5.s40503 | tof@inf | lower bound | 4 | 6 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 2 |
| B.bitflip.probe.n5.s40503 | tof@inf | upper bound (constructed value) | 7 | 6 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | -1 |
| B.bitflip.probe.n5.s40504 | tof@1.5bmin | lower bound | 4 | 7 | XAG + MC (Meuli et al. 2019, re-impl.) | 3 |
| B.bitflip.probe.n5.s40504 | tof@bmin | lower bound | 4 | 46 | esop(qiskit EsopGenerator)+qiskit MCX | 42 |
| B.bitflip.probe.n5.s40504 | tof@inf | lower bound | 4 | 7 | XAG + MC (Meuli et al. 2019, re-impl.) | 3 |
| B.bitflip.probe.n5.s40504 | tof@inf | upper bound (constructed value) | 7 | 7 | XAG + MC (Meuli et al. 2019, re-impl.) | 0 |
| B.bitflip.probe.n6.s40600 | tof@1.5bmin | lower bound | 5 | 115 | esop(qiskit EsopGenerator)+qiskit MCX | 110 |
| B.bitflip.probe.n6.s40600 | tof@bmin | lower bound | 5 | 115 | esop(qiskit EsopGenerator)+qiskit MCX | 110 |
| B.bitflip.probe.n6.s40600 | tof@inf | lower bound | 5 | 9 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 4 |
| B.bitflip.probe.n6.s40600 | tof@inf | upper bound (constructed value) | 11 | 9 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | -2 |
| B.bitflip.probe.n6.s40601 | tof@1.5bmin | lower bound | 4 | 100 | esop(qiskit EsopGenerator)+qiskit MCX | 96 |
| B.bitflip.probe.n6.s40601 | tof@bmin | lower bound | 4 | 100 | esop(qiskit EsopGenerator)+qiskit MCX | 96 |
| B.bitflip.probe.n6.s40601 | tof@inf | lower bound | 4 | 9 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 5 |
| B.bitflip.probe.n6.s40601 | tof@inf | upper bound (constructed value) | 11 | 9 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | -2 |
| B.bitflip.probe.n6.s40602 | tof@1.5bmin | lower bound | 4 | 132 | solution enumeration + prefix-trie MCX | 128 |
| B.bitflip.probe.n6.s40602 | tof@bmin | lower bound | 4 | 153 | esop(qiskit EsopGenerator)+qiskit MCX | 149 |
| B.bitflip.probe.n6.s40602 | tof@inf | lower bound | 4 | 12 | XAG + MC (Meuli et al. 2019, re-impl.) | 8 |
| B.bitflip.probe.n6.s40602 | tof@inf | upper bound (constructed value) | 11 | 12 | XAG + MC (Meuli et al. 2019, re-impl.) | 1 |
| B.bitflip.probe.n6.s40603 | tof@1.5bmin | lower bound | 5 | 113 | esop(qiskit EsopGenerator)+qiskit MCX | 108 |
| B.bitflip.probe.n6.s40603 | tof@bmin | lower bound | 5 | 113 | esop(qiskit EsopGenerator)+qiskit MCX | 108 |
| B.bitflip.probe.n6.s40603 | tof@inf | lower bound | 5 | 9 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 4 |
| B.bitflip.probe.n6.s40603 | tof@inf | upper bound (constructed value) | 11 | 9 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | -2 |
| B.bitflip.probe.n6.s40604 | tof@1.5bmin | lower bound | 4 | 120 | solution enumeration + prefix-trie MCX | 116 |
| B.bitflip.probe.n6.s40604 | tof@bmin | lower bound | 4 | 126 | esop(qiskit EsopGenerator)+qiskit MCX | 122 |
| B.bitflip.probe.n6.s40604 | tof@inf | lower bound | 4 | 9 | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 5 |

## 4. Instances where the best baseline already reaches the optimum

0 (instance, track) pairs in all (CSV: `B_baseline_at_optimum.csv`). By split: .

## 5. Unavailable, crash, timeout, unverified and unsupported list

Aggregated by (tool, track, status); individual records in `data/v1/baselines/B/records.jsonl` (CSV: `B_non_pass.csv`)

| Tool | Track | Status | Count | Example instance | Reason (excerpt) |
|---|---|---|---|---|---|
| bennett(aig) | tof@bmin | unsupported | 488 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 12 qubits |
| per-clause MCX (qiskit MCX) | tof@bmin | unsupported | 423 | B.bitflip.arith.carry.n10 | function is not given as a CNF (AND of ORs) |
| per-clause MCX (qiskit MCX) | tof@1.5bmin | unsupported | 393 | B.bitflip.arith.carry.n10 | function is not given as a CNF (AND of ORs) |
| bennett(aig) | tof@1.5bmin | unsupported | 356 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 18 qubits |
| per-clause MCX (qiskit MCX) | cx@inf | unsupported | 350 | B.bitflip.arith.carry.n10 | function is not given as a CNF (AND of ORs) |
| per-clause MCX (qiskit MCX) | tof@inf | unsupported | 350 | B.bitflip.arith.carry.n10 | function is not given as a CNF (AND of ORs) |
| solution enumeration + prefix-trie MCX | tof@bmin | unsupported | 304 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 12 qubits |
| bennett(abc resyn2) | tof@bmin | unsupported | 294 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 12 qubits |
| pebbling SAT (Meuli et al. 2019, re-impl.) | tof@bmin | unsupported | 278 | B.bitflip.arith.carry.n10 | no pebbling schedule with 1 pebbles exists up to the step bound (UNSAT) |
| esop(qiskit EsopGenerator)+qiskit MCX | cx@inf | unsupported | 275 | B.bitflip.arith.carry.n20 | ESOP from the full truth table only for <= 16 inputs (Qiskit warns above 16) |
| esop(qiskit EsopGenerator)+qiskit MCX | tof@1.5bmin | unsupported | 275 | B.bitflip.arith.carry.n20 | ESOP from the full truth table only for <= 16 inputs (Qiskit warns above 16) |
| esop(qiskit EsopGenerator)+qiskit MCX | tof@bmin | unsupported | 275 | B.bitflip.arith.carry.n20 | ESOP from the full truth table only for <= 16 inputs (Qiskit warns above 16) |
| esop(qiskit EsopGenerator)+qiskit MCX | tof@inf | unsupported | 275 | B.bitflip.arith.carry.n20 | ESOP from the full truth table only for <= 16 inputs (Qiskit warns above 16) |
| XAG + MC (Meuli et al. 2019, re-impl.) | tof@bmin | unsupported | 271 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 12 qubits |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | tof@bmin | unsupported | 264 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 12 qubits |
| bennett(abc resyn2) | tof@1.5bmin | unsupported | 246 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 18 qubits |
| cone_bennett(abc resyn2) | tof@bmin | unsupported | 220 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 12 qubits |
| solution enumeration + prefix-trie MCX | tof@1.5bmin | unsupported | 220 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 18 qubits |
| XAG + MC (Meuli et al. 2019, re-impl.) | tof@1.5bmin | unsupported | 204 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 18 qubits |
| cone_bennett(abc resyn2) | tof@1.5bmin | unsupported | 190 | B.bitflip.arith.carry.n10 | does not fit the qubit budget: needs more than 18 qubits |
| solution enumeration + prefix-trie MCX | cx@inf | unsupported | 181 | B.bitflip.arith.carry.n14 | more than 4096 solutions (or enumeration out of time) |
| solution enumeration + prefix-trie MCX | t_mbu@inf | unsupported | 181 | B.bitflip.arith.carry.n14 | more than 4096 solutions (or enumeration out of time) |
| solution enumeration + prefix-trie MCX | tof@inf | unsupported | 181 | B.bitflip.arith.carry.n14 | more than 4096 solutions (or enumeration out of time) |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | tof@1.5bmin | unsupported | 178 | B.bitflip.arith.majority.n11 | does not fit the qubit budget: needs more than 20 qubits |
| pebbling SAT (Meuli et al. 2019, re-impl.) | tof@1.5bmin | timeout | 173 | B.bitflip.arith.carry.n12 | no pebbling schedule with 8 pebbles within the SAT conflict budget (1000000 conflicts per call) |
| pebbling SAT (Meuli et al. 2019, re-impl.) | tof@1.5bmin | unsupported | 149 | B.bitflip.arith.majority.n41 | SAT pebbling limited to <= 400 AND nodes |
| pebbling SAT (Meuli et al. 2019, re-impl.) | tof@bmin | timeout | 132 | B.bitflip.arith.majority.n21 | killed after 80.4 s (budget 60.0 s + grace 20.0 s) |
| pebbling SAT (Meuli et al. 2019, re-impl.) | cx@inf | unsupported | 122 | B.bitflip.arith.majority.n41 | SAT pebbling limited to <= 400 AND nodes |
| pebbling SAT (Meuli et al. 2019, re-impl.) | tof@inf | unsupported | 122 | B.bitflip.arith.majority.n41 | SAT pebbling limited to <= 400 AND nodes |
| pebbling SAT (Meuli et al. 2019, re-impl.) | cx@inf | timeout | 112 | B.bitflip.arith.majority.n21 | killed after 80.5 s (budget 60.0 s + grace 20.0 s) |
| pebbling SAT (Meuli et al. 2019, re-impl.) | tof@inf | timeout | 112 | B.bitflip.arith.majority.n21 | killed after 80.4 s (budget 60.0 s + grace 20.0 s) |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) [circuit reused, re-verified on tof_clifford@inf] | tof_clifford@inf | fail | 63 | B.bitflip.arith.mul_bit.n10.j4 | gates outside the allowed set: ['mbu'] |
| per-clause MCX (qiskit MCX) | cx@inf | unverified | 59 | B.bitflip.compare.eq.n22 | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| per-clause MCX (qiskit MCX) | tof@1.5bmin | unverified | 59 | B.bitflip.compare.eq.n22 | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| per-clause MCX (qiskit MCX) | tof@inf | unverified | 59 | B.bitflip.compare.eq.n22 | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| XAG + MC (Meuli et al. 2019, re-impl.) [circuit reused, re-verified on tof_clifford@inf] | tof_clifford@inf | fail | 47 | B.bitflip.arith.threshold.n10.k5 | gates outside the allowed set: ['mbu'] |
| per-clause MCX (qiskit MCX) | tof@bmin | unverified | 44 | B.bitflip.compare.eq.n22 | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| bennett(abc resyn2) [circuit reused, re-verified on tof_clifford@inf] | tof_clifford@inf | fail | 33 | B.bitflip.arith.threshold.n14.k4 | gates outside the allowed set: ['mbu'] |
| cone_bennett(abc resyn2) [circuit reused, re-verified on tof_clifford@inf] | tof_clifford@inf | fail | 33 | B.bitflip.arith.threshold.n14.k4 | gates outside the allowed set: ['mbu'] |
| esop(qiskit EsopGenerator)+qiskit MCX | cx@inf | unverified | 18 | B.bitflip.epfl.ctrl | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| esop(qiskit EsopGenerator)+qiskit MCX | tof@1.5bmin | unverified | 18 | B.bitflip.epfl.ctrl | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| esop(qiskit EsopGenerator)+qiskit MCX | tof@bmin | unverified | 18 | B.bitflip.epfl.ctrl | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| esop(qiskit EsopGenerator)+qiskit MCX | tof@inf | unverified | 18 | B.bitflip.epfl.ctrl | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | tof@inf | unverified | 16 | B.bitflip.arith.majority.n41 | unverified: SAT miter exceeded 600 s |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | cx@inf | unverified | 15 | B.bitflip.arith.majority.n41 | unverified: SAT miter exceeded 600 s |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | t_mbu@inf | unverified | 15 | B.bitflip.arith.majority.n41 | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| esop(qiskit EsopGenerator)+qiskit MCX | cx@inf | timeout | 15 | B.bitflip.arith.mul_bit.n14.j8 | killed after 80.1 s (budget 60.0 s + grace 20.0 s) |
| esop(qiskit EsopGenerator)+qiskit MCX | tof@1.5bmin | timeout | 15 | B.bitflip.arith.mul_bit.n14.j8 | killed after 80.3 s (budget 60.0 s + grace 20.0 s) |
| esop(qiskit EsopGenerator)+qiskit MCX | tof@bmin | timeout | 15 | B.bitflip.arith.mul_bit.n14.j8 | killed after 80.1 s (budget 60.0 s + grace 20.0 s) |
| esop(qiskit EsopGenerator)+qiskit MCX | tof@inf | timeout | 15 | B.bitflip.arith.mul_bit.n14.j8 | killed after 80.1 s (budget 60.0 s + grace 20.0 s) |
| bennett(aig) [circuit reused, re-verified on tof_clifford@inf] | tof_clifford@inf | fail | 9 | B.bitflip.compare.interval.n12.s5106 | gates outside the allowed set: ['mbu'] |
| solution enumeration + prefix-trie MCX | cx@inf | unverified | 7 | B.bitflip.compare.eq.n24 | verification exceeded 600 s |
| solution enumeration + prefix-trie MCX | t_mbu@inf | unverified | 7 | B.bitflip.compare.eq.n24 | verification exceeded 600 s |
| solution enumeration + prefix-trie MCX | tof@1.5bmin | unverified | 7 | B.bitflip.compare.eq.n24 | unverified: SAT miter exceeded 600 s |
| solution enumeration + prefix-trie MCX | tof@bmin | unverified | 7 | B.bitflip.compare.eq.n24 | unverified: SAT miter exceeded 600 s |
| solution enumeration + prefix-trie MCX | tof@inf | unverified | 7 | B.bitflip.compare.eq.n24 | unverified: SAT miter exceeded 600 s |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | tof@1.5bmin | unverified | 6 | B.bitflip.arith.majority.n41 | unverified: SAT miter exceeded 600 s |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | tof@bmin | unverified | 6 | B.bitflip.arith.majority.n41 | verification exceeded 600 s |
| XAG + MC (Meuli et al. 2019, re-impl.) | cx@inf | unverified | 3 | B.bitflip.arith.majority.n63 | verification exceeded 600 s |
| XAG + MC (Meuli et al. 2019, re-impl.) | t_mbu@inf | unverified | 3 | B.bitflip.arith.majority.n63 | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| XAG + MC (Meuli et al. 2019, re-impl.) | tof@1.5bmin | unverified | 3 | B.bitflip.arith.majority.n63 | unverified: SAT miter exceeded 600 s |
| XAG + MC (Meuli et al. 2019, re-impl.) | tof@bmin | unverified | 3 | B.bitflip.arith.majority.n63 | unverified: SAT miter exceeded 600 s |
| XAG + MC (Meuli et al. 2019, re-impl.) | tof@inf | unverified | 3 | B.bitflip.arith.majority.n63 | unverified: SAT miter exceeded 600 s |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | cx@inf | timeout | 2 | B.bitflip.arith.majority.n51 | minmc: out of time |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | t_mbu@inf | timeout | 2 | B.bitflip.arith.majority.n51 | minmc: out of time |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | tof@1.5bmin | timeout | 1 | B.bitflip.arith.majority.n63 | minmc: out of time |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | tof@bmin | timeout | 1 | B.bitflip.arith.majority.n63 | minmc: out of time |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | tof@inf | timeout | 1 | B.bitflip.arith.majority.n63 | minmc: out of time |
| bennett(aig) | cx@inf | unverified | 1 | B.bitflip.iscas85.c6288 | unverified: SAT miter exceeded 600 s |
| bennett(aig) | t_mbu@inf | unverified | 1 | B.bitflip.iscas85.c6288 | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| bennett(aig) | tof@1.5bmin | unverified | 1 | B.bitflip.iscas85.c6288 | unverified: SAT miter exceeded 600 s |
| bennett(aig) | tof@inf | unverified | 1 | B.bitflip.iscas85.c6288 | unverified: SAT miter exceeded 600 s |
| cone_bennett(abc resyn2) | cx@inf | unverified | 1 | B.bitflip.iscas85.c6288 | unverified: SAT miter exceeded 600 s |
| cone_bennett(abc resyn2) | t_mbu@inf | unverified | 1 | B.bitflip.iscas85.c6288 | unverified: non-+-1 phases (S/T/RCCX/RC3X) above the exhaustive limit: no symbolic phase check |
| cone_bennett(abc resyn2) | tof@1.5bmin | unverified | 1 | B.bitflip.iscas85.c6288 | unverified: SAT miter exceeded 600 s |
| cone_bennett(abc resyn2) | tof@bmin | unverified | 1 | B.bitflip.iscas85.c6288 | unverified: SAT miter exceeded 600 s |
| cone_bennett(abc resyn2) | tof@inf | unverified | 1 | B.bitflip.iscas85.c6288 | unverified: SAT miter exceeded 600 s |

## 6. Published records (with references)

Treated as "reported value only" unless both semantics and budget match this benchmark's contract (CSV: `B_published.csv`).

| Instance | Track | Value | Width | Reference | Counts toward best_known | Reason not counted |
|---|---|---|---|---|---|---|
| B.bitflip.sbox.aria_sb2 | tof@bmin | 34 | 100 | IACR ePrint 2024/1986 Table 2, row S2 / Boyar-Peralta / Ours | no | different contract |
| B.bitflip.sbox.aria_sb2 | tof@1.5bmin | 34 | 100 | IACR ePrint 2024/1986 Table 2, row S2 / Boyar-Peralta / Ours | no | different contract |
| B.bitflip.sbox.aria_sb2 | tof@inf | 34 | 100 | IACR ePrint 2024/1986 Table 2, row S2 / Boyar-Peralta / Ours | no | different contract |
| B.bitflip.sbox.camellia_s1 | tof@bmin | 54 | 20 | Sci. Sin. Phys. Mech. Astron. 53, 240313 (2023), DOI 10.1360/SSPMA-2022-0485 English abstract (full text not retrieved) | no | different contract |
| B.bitflip.sbox.camellia_s1 | tof@1.5bmin | 54 | 20 | Sci. Sin. Phys. Mech. Astron. 53, 240313 (2023), DOI 10.1360/SSPMA-2022-0485 English abstract (full text not retrieved) | no | different contract |
| B.bitflip.sbox.camellia_s1 | tof@inf | 54 | 20 | Sci. Sin. Phys. Mech. Astron. 53, 240313 (2023), DOI 10.1360/SSPMA-2022-0485 English abstract (full text not retrieved) | no | different contract |
| B.bitflip.sbox.aes | tof@bmin | 52 | 22 | IACR ePrint 2022/620 (ASIACRYPT 2022) Table 3 (this paper, C*) | no | width 22 > budget 17 |
| B.bitflip.sbox.aes | tof@1.5bmin | 52 | 22 | IACR ePrint 2022/620 (ASIACRYPT 2022) Table 3 (this paper, C*) | yes |  |
| B.bitflip.sbox.aes | tof@inf | 52 | 22 | IACR ePrint 2022/620 (ASIACRYPT 2022) Table 3 (this paper, C*) | yes |  |
| B.bitflip.sbox.aes | tof@bmin | 68 | 23 | ASIACRYPT 2020 (IACR archive PDF; no ePrint id found) Sec. 4.2, Algorithm 5 (C*) | no | width 23 > budget 17 |
| B.bitflip.sbox.aes | tof@1.5bmin | 68 | 23 | ASIACRYPT 2020 (IACR archive PDF; no ePrint id found) Sec. 4.2, Algorithm 5 (C*) | yes |  |
| B.bitflip.sbox.aes | tof@inf | 68 | 23 | ASIACRYPT 2020 (IACR archive PDF; no ePrint id found) Sec. 4.2, Algorithm 5 (C*) | yes |  |
| B.bitflip.sbox.aes | tof@bmin | 60 | 66 | IACR ePrint 2025/212 (EUROCRYPT 2025) Table 1 (this work, C0/C*) | no | width 66 > budget 17 |
| B.bitflip.sbox.aes | tof@1.5bmin | 60 | 66 | IACR ePrint 2025/212 (EUROCRYPT 2025) Table 1 (this work, C0/C*) | no | width 66 > budget 26 |
| B.bitflip.sbox.aes | tof@inf | 60 | 66 | IACR ePrint 2025/212 (EUROCRYPT 2025) Table 1 (this work, C0/C*) | yes |  |
| B.bitflip.sbox.aes | t_mbu@inf | 136 | 92 | IACR ePrint 2025/212 (EUROCRYPT 2025) Table 2 (this work, C0/C*) | yes |  |
| B.bitflip.sbox.aes | cx@inf | 600 | 66 | IACR ePrint 2025/212 (EUROCRYPT 2025) Table 1 (this work, C*) -> derived | yes |  |
| B.bitflip.sbox.aes | cx@inf | 648 | 22 | IACR ePrint 2022/620 Table 3 (C*) -> derived | yes |  |
| B.bitflip.sbox.aes | tof@bmin | 34 | 90 | IACR ePrint 2023/1417 (ASIACRYPT 2023) Table 3 (this paper) | no | different contract |
| B.bitflip.sbox.aes | tof@1.5bmin | 34 | 90 | IACR ePrint 2023/1417 (ASIACRYPT 2023) Table 3 (this paper) | no | different contract |
| B.bitflip.sbox.aes | tof@inf | 34 | 90 | IACR ePrint 2023/1417 (ASIACRYPT 2023) Table 3 (this paper) | no | different contract |

## test_ood by source/family

Main track `tof@inf`. OOD conclusions should be reported per source; do not mix different sources into one average.

| Source/family | Instances | With verified baseline | Median best baseline | With known optimum/constructed value | Of these, baseline reaches the value | Note |
|---|---|---|---|---|---|---|
| epfl | 5 | 5 | 346 | 0 | 0 |  |
| iscas85 | 5 | 5 | 772 | 0 | 0 |  |
| mcnc | 20 | 20 | 76.5 | 0 | 0 |  |
| satlib | 48 | 48 | 374.0 | 0 | 0 |  |
| sbox | 14 | 14 | 12.0 | 0 | 0 |  |

## Solution-sparse instances and structural-family instances reported separately (category B)

For functions that are true on only very few inputs, a candidate program can first find all solutions classically (by direct enumeration at training sizes, with a SAT solver at test sizes) and then build multi-controlled gates for the solution set. This is entirely legitimate, and the Toffoli count is often an order of magnitude below generic compilation. Therefore: (1) a "solution enumeration + prefix-tree multi-controlled gates" baseline was added and counts toward best_known; (2) solution-sparse instances are listed separately and **not used for the main conclusion of "beating the best baseline"**; (3) unsatisfiable formulas (constant functions, where the empty circuit is optimal) are not included.

The split is by each instance's fraction of solutions, not by family name: the rule is **single output and n_solutions < 2^(n/2)  (fraction n_solutions / 2^n < 2^(-n/2))**. The number of solutions `n_solutions` is computed exactly for all single-output instances (exhaustive for n ≤ 22; larger ones by exact BDD model counting, with SAT enumeration when the BDD exceeds its limit) and stored in the private fields; multi-output functions are not solution-sparse. Evolution experiments can use `load_split("B", split, subset="structural")` or `qbank export B --subset structural` to take only structural-family instances.

| Family type | Split | Instances | Instances whose main-track best baseline comes from a solution-enumeration tool |
|---|---|---|---|
| solution-sparse | probe | 2 | 0 |
| solution-sparse | test_in | 57 | 26 |
| solution-sparse | test_ood | 48 | 27 |
| solution-sparse | train | 138 | 87 |
| solution-sparse | val | 35 | 16 |
| structural | probe | 18 | 0 |
| structural | test_in | 31 | 0 |
| structural | test_ood | 44 | 0 |
| structural | train | 116 | 0 |
| structural | val | 40 | 0 |

Assignment of each family under the new rule (structural / solution-sparse): arith 63/0; compare 58/42; epfl 5/0; iscas85 5/0; mcnc 20/0; probe_small 18/2; rand3sat 0/66; satlib 0/48; sbox 14/0; simon3 66/0; sudoku 0/56; triangle 0/66.

## Compute consistency of time-limited baselines

Baselines run as parallel processes on an Apple M3 Max (12 performance cores + 4 efficiency cores), each job single-threaded with a 60 s wall-clock budget. When the number of parallel jobs exceeds the number of performance cores, some jobs land on efficiency cores; time-limited tools (searches that improve over time, wall-clock-limited solvers) therefore do not get exactly the same compute within the same 60 s.
Since v1.2 each record carries `concurrency` (number of concurrency slots, number of jobs running at start, 1-minute load); this category has 10234 such records, concurrency slots [2, 4, 8, 12].
The 11984 earlier records have no concurrency recorded at run time and were given `concurrency_estimate`: the number of simultaneously running qbank jobs reconstructed from the start/end times of all cached records (1 s resolution, excluding the load of other processes), median 12, maximum 20.

For the final evaluation, candidate programs and time-limited baselines should be compared under the same conditions: `qbank rebaseline <C> --split test --tools <time-limited tools>` reruns these baselines on the test instances at fixed concurrency (default = number of performance cores, i.e. 12); results are stored separately in `data/v1/baselines/<C>/rebaseline_w<concurrency>.jsonl` (cache namespace `<C>-rebaseline-w<concurrency>`) and do not overwrite best_known. Without `--tools`, the budget-sensitive tools of the quality-time curve are used.

## Quality-time curve (0.1x / 1x / 10x budget)

On 24 instances from stratified sampling (one per family x size bin, plus instances that timed out at 60 s), budget-sensitive tools (tools that improve over time, and tools that timed out at 60 s) were rerun at 6 s and 600 s; the 60 s point is the main baseline record. These results are stored separately and **do not enter best_known** (best_known is defined by the uniform 60 s budget). Individual rows in `B_quality_time.csv`, reproduce: `qbank curve B`.

| Tool | Instances | Pass at 6 s | Pass at 60 s | Pass at 600 s | Timeout at 60 s → pass at 600 s | 600 s better than 60 s | Median improvement (60 s/600 s) |
|---|---|---|---|---|---|---|---|
| XAG + MC (Meuli et al. 2019, re-impl.) | 24 | 12 | 23 | 13 | 0 | 0 | 1.000 |
| XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 24 | 0 | 22 | 12 | 0 | 0 | 1.000 |
| esop(qiskit EsopGenerator)+qiskit MCX | 24 | 3 | 7 | 3 | 0 | 0 | 1.000 |
| pebbling SAT (Meuli et al. 2019, re-impl.) | 24 | 1 | 5 | 6 | 3 | 0 | 1.000 |

(instance, tool) pairs that time out at 60 s and pass at 600 s: B.phase.sudoku4.k11.s2002 / pebbling SAT (Meuli et al. 2019, re-impl.) (value at 600 s 1002); B.bitflip.epfl.dec / pebbling SAT (Meuli et al. 2019, re-impl.) (value at 600 s 712); B.bitflip.epfl.router / pebbling SAT (Meuli et al. 2019, re-impl.) (value at 600 s 914). On these instances the 60 s baseline underestimates existing tools; consult this table when using best_known.

## Baseline reproducibility (rerun of 20 random records)

Per task spec section 8, 20 randomly sampled passing baseline records were rerun: deterministic tools must give a gate-for-gate identical circuit, randomized tools are rerun once with the recorded trial seed. Result: **20/20 identical**. Reproduce: `qbank repro B` (CSV: `B_repro.csv`).

| Instance | Track | Tool | Seed | Trial seed | Identical |
|---|---|---|---|---|---|
| B.phase.satlib.uf50-0115 | t_mbu@inf | XAG + MC (Meuli et al. 2019, re-impl.) | 255481376 |  | yes |
| B.phase.rand3sat.n24.s2009 | t_mbu@inf | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 1398831339 |  | yes |
| B.bitflip.arith.carry.n22 | cx@inf | pebbling SAT (Meuli et al. 2019, re-impl.) | 346055481 |  | yes |
| B.bitflip.compare.eq_const.n22.s2002 | tof@inf | bennett(aig) | 454276370 |  | yes |
| B.phase.sudoku6.k2.s207 | t_mbu@inf | bennett(aig) | 262939983 |  | yes |
| B.phase.satlib.uf50-0119 | tof@bmin | cone_bennett(abc resyn2) | 2083228584 |  | yes |
| B.phase.rand3sat.n58.s23002 | tof@bmin | bennett(abc resyn2) | 125206213 |  | yes |
| B.bitflip.compare.eq.n18 | tof@1.5bmin | per-clause MCX (qiskit MCX) | 1765264524 |  | yes |
| B.phase.triangle.v22.s22000 | t_mbu@inf | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 1328945438 |  | yes |
| B.bitflip.mcnc.cm162a | cx@inf | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 810680627 |  | yes |
| B.bitflip.compare.eq_const.n64.s23003 | tof@inf | pebbling SAT (Meuli et al. 2019, re-impl.) | 376090726 |  | yes |
| B.bitflip.compare.eq_const.n24.s2008 | tof@1.5bmin | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 108592926 |  | yes |
| B.bitflip.simon3.t10.s2001 | t_mbu@inf | XAG + MC (Meuli et al. 2019, re-impl.) | 779437688 |  | yes |
| B.bitflip.arith.carry.n14 | tof@1.5bmin | esop(qiskit EsopGenerator)+qiskit MCX | 758722580 |  | yes |
| B.bitflip.compare.lt.n52 | t_mbu@inf | XAG + MC (Meuli et al. 2019, re-impl.) | 376305682 |  | yes |
| B.phase.rand3sat.n8.s9 | t_mbu@inf | XAG MC cut rewriting (mockturtle xag_minmc_resynthesis) | 1698417928 |  | yes |
| B.phase.triangle.v16.s1007 | tof@bmin | XAG + MC (Meuli et al. 2019, re-impl.) | 586188069 |  | yes |
| B.bitflip.simon3.t7.s11001 | t_mbu@inf | bennett(aig) | 224665452 |  | yes |
| B.bitflip.mcnc.cordic | tof@bmin | pebbling SAT (Meuli et al. 2019, re-impl.) | 518152761 |  | yes |
| B.bitflip.probe.n3.s40303 | tof@1.5bmin | XAG + MC (Meuli et al. 2019, re-impl.) | 1460692850 |  | yes |

