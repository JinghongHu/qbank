# Datasheet: qbank v1 · Category B (classical-function oracle compilation)

Generated: 2026-10-29 (by `qbank report B` from `data/v1/`).

## 1. Task and contract

- **oracle_bitflip_clean**: |x⟩|y⟩|0_anc⟩ → |x⟩|y ⊕ f(x)⟩|0_anc⟩; the phase must be exactly +1 for every input (including relative phases; nothing beyond a global phase is allowed); ancillas must return to |0⟩.
- **oracle_phase_clean** (single output): |x⟩|0_anc⟩ → (−1)^{f(x)} |x⟩|0_anc⟩.
- **Gate set**: x, cx, ccx, ccz, rccx, rc3x, swap, z, s, sdg, t, tdg, cz; the t_mbu track additionally allows `mbu` (X-basis measurement + classically controlled diagonal correction).
- **`mbu` rule**: the classically controlled correction of an `mbu` may not act on the measured qubit; such a circuit is rejected before any simulation (negative test in `tests/test_b_contracts.py`). None of the 226,854 `mbu` gates of the stored baseline circuits acts on its measured qubit.
- **Tracks**: tof@bmin, tof@1.5bmin (qubit budget = the minimum width b_min of the verified constructive baselines, and 1.5 times it), tof@inf (Toffoli/AND count), t_mbu@inf (T count, measurement-based uncomputation allowed), cx@inf (CX count, fixed decomposition: ccx = 6 CX), and the Toffoli side track tof_clifford@inf (contract version 2: Clifford + Toffoli-type gates, no `mbu`, cost = Toffoli count).
- **Main track**: the task packs and the paper use `t_mbu@inf` as B's main track; the tool-share table of this bank's report uses `tof@inf` as "main track", and the report gives the full results of every track.
- **Contract versions**: the tof_clifford@inf track exists on the 63 parametrised structural instances (compare.lt_const, compare.interval, arith.threshold, arith.mul_bit), whose public records carry contract version 2; the public records of the other 466 instances carry contract version 1 and have no such track.
- **Cost definitions**: Toffoli count (ccx/ccz/rccx count 1, rc3x counts 2); T count (ccx 7, ccz 7, rccx 4, rc3x 8, fixed after decomposition per the Qiskit 2.5.2 definitions); CX count (ccx 6, rccx 3, rc3x 6, swap 3).

## 2. Checking method and size limits

- Before any simulation the checker validates the circuit width and the number of qubits and parameters of every gate; an exception inside the checker is recorded as `error` (never a pass).
- Input + output registers ≤ 22 qubits: bit-parallel exhaustive simulation (uint64, phases kept as mod-8 bit planes), RCCX/RC3X via monomial tables, exact comparison including phases.
- Above 22 qubits: SAT equivalence miter (CaDiCaL 1.9.5, run in a subprocess, 600 s hard limit); when the circuit contains non-±1 phases (S/T/RCCX/RC3X) no symbolic phase check is possible and the result is "unverified".
- Negative controls in `tests/test_b_contracts.py` (wrong phase, ancilla not cleaned, gate outside the gate set, over budget).
- **Optimum reference for probe**: the multiplicative complexity MC(f) (minimum number of AND gates, XOR free) is computed exactly with SAT. Every reversible circuit with t Toffoli-type gates corresponds to an XAG with t AND gates, so Toffoli count ≥ MC(f); compiling an MC-optimal XAG into an oracle uses at most 2·MC(f) − 1 Toffolis (verified circuits stored in `optimal/B.jsonl`). The optimum is therefore bracketed in [MC, 2·MC − 1]. SAT solving is slow for 6-input functions; when it does not finish, the lower bound is the proven part (no less than deg − 1).

## 3. Families and split sizes

| Family | n range | train | val | test_in | test_ood | probe |
|---|---|---|---|---|---|---|
| arith | - | 41 | 15 | 7 | 0 | 0 |
| compare | - | 69 | 19 | 12 | 0 | 0 |
| epfl | - | 0 | 0 | 0 | 5 | 0 |
| iscas85 | - | 0 | 0 | 0 | 5 | 0 |
| mcnc | - | 0 | 0 | 0 | 20 | 0 |
| probe_small | - | 0 | 0 | 0 | 0 | 20 |
| rand3sat | - | 36 | 12 | 18 | 0 | 0 |
| satlib | - | 0 | 0 | 0 | 48 | 0 |
| sbox | - | 0 | 0 | 0 | 14 | 0 |
| simon3 | - | 36 | 12 | 18 | 0 | 0 |
| sudoku | - | 36 | 5 | 15 | 0 | 0 |
| triangle | - | 36 | 12 | 18 | 0 | 0 |

Total: probe 20, test_in 88, test_ood 92, train 254, val 75; 529 instances in all.

Split rules: B v1: T families (rand3sat, triangle, sudoku, simon3, compare, arith) -> train/val/test_in; random families: 12 train / 4 val seeds per size bin (S 6-12, M 13-18, L 19-24 inputs), test_in = XL (40-64 inputs) + 2 new seeds per train bin; deterministic functions by parameter (small -> train, L -> val, largest -> test_in); external sources (SATLIB, EPFL, S-boxes) -> test_ood; probe = small instances with a model-optimal value. Seed ranges disjoint per split.

Equivalent variants: 540 (3 per test instance, in the same split as the original, `data/v1/variants/B/`).
Cross-split deduplication removed 39 (all refilled with new seeds from the same split or recorded); see `data/v1/instances/B/build_report.json`.

## 4. Known limitations and implementation adjustments

- The verification limit determines the sizes: for arith/prod_parity at w ≥ 11 (23-qubit registers) the SAT miter exceeds 600 s, so test_in only goes up to w = 10.
- Instances that no constructive baseline can verify exactly are not included (`excluded_unverifiable` in `build_report.json`).
- Constant functions (e.g. triangle-free graphs, unsatisfiable formulas) correspond to empty circuits and are not included; unsatisfiable 3-SAT draws are rejected and redrawn (`draws_until_satisfiable`); constant functions are detected semantically (SAT), so unsatisfiable SATLIB formulas are not included.
- Deduplication is up to NP equivalence (input permutation + input negation, both requiring only free X gates): all eq_const of the same width are mutually equivalent; Sudokus with a unique solution, SATLIB formulas with a single model and random 3-SAT are all "point functions", equivalent to eq_const. These cross-split duplicates are removed (deterministic families cannot be refilled), so eq_const effectively has a single problem per width, and the SATLIB test_ood instances are reduced accordingly.
- QuantumEvo needs system dependencies such as Boost and was not built (recorded as unavailable); RevLib has no license and is not included.
- **XAG baseline** (the approach of Meuli et al., ICCAD 2019, reimplemented in this benchmark): XOR uses only CNOTs, one Toffoli per AND gate; ≤ 5 inputs use an MC-optimal XAG from SAT, 6 inputs use "optimal Shannon decomposition + exact 5-input subfunctions", larger functions use structural XOR extraction after ABC optimization.
- **"Solve first, then compile" baseline**: all solutions are found with SAT, then multi-controlled gates are built from the prefix tree of the solution set.
- **Solution-sparse instances** are decided by the fraction of solutions (see the report), listed separately and not used for the main conclusions.
- **XAG MC cut rewriting (mockturtle xag_minmc_resynthesis)**: mockturtle's (lsils/mockturtle @ d9e02495, MIT) multiplicative-complexity-oriented cut rewriting: `cut_rewriting_with_compatibility_graph` + minimum-MC database (≤ 5 inputs use mockturtle's bundled library, 6 inputs use the AND-optimal circuits of the 6-variable affine classes from NIST usnistgov/Circuits, converted to mockturtle format via kitty's spectral canonical form and each re-simulated and checked) + `mc_cost`; build script `env/build_minmc.sh`. Differences from the original implementation: exact spectral canonicalization of cut functions has a step limit (10⁴ steps during rewriting, 10⁸ steps for whole functions; cuts over the limit are not rewritten; the database lacks 6 classes whose canonicalization exceeds 10⁸ steps); networks with ≤ 6 inputs are additionally resynthesized by a whole-function database lookup, keeping whichever has fewer AND gates; cut_limit is mockturtle's default 25, and if cut rewriting at this commit triggers the topo_view assertion (a cycle appears), it is rerun with 12 (deterministic).
- **Deterministic SAT budgets**: XAG + MC and pebbling SAT use SAT conflict limits (exact MC: 50k conflicts per k; pebbling: 1M conflicts per call to find the first feasible schedule, then at most 10 bisection tightening calls of 100k conflicts each), so results do not depend on wall-clock time and machine load, and they are included in the 20-record reproducibility sample; the only thing that varies with load is whether the run finishes within 60 s.
- **Structural test_ood** includes three external sources (block-cipher S-boxes from RFCs, ISCAS-85, MCNC LGSynth'91), reported per source.
- **Parametrised structural instances**: 63 single-output bit-flip oracles with 8-21 inputs (compare.lt_const 17, compare.interval 15, arith.threshold 16, arith.mul_bit 15; 49 in train, 14 in val). Each satisfies the strict structural rule min(#solutions, 2^n − #solutions) ≥ 2^(n/2) (exact count by enumeration), uses every input, has an NPN signature different from all other instances and from each other, and has a constructive circuit verified by the checker. Every tool was run on them (2646 jobs: 1701 pass, 876 not applicable, 69 timeout, 0 fail).
- **Task-pack reference values**: for the 262 instances used by the task packs (199 other instances + the 63 parametrised structural instances) the reference circuits are verified with the current checker, cheapest first, and the first that passes gives the reference value.
- **Reference values of the Toffoli side track**: tof_clifford@inf has no tool runs of its own. During aggregation (`_reuse_tof_clifford` in `aggregate.py`) the verified circuits of the instance's other tracks are verified under the `tof_clifford@inf` contract in order of Toffoli count, and the first that passes is best_known (tool name suffix `[circuit reused, re-verified on tof_clifford@inf]`). All 63 parametrised structural instances have a reference value on this track, identical to the task-pack verification.
- The circuits of XAG MC cut rewriting differ strongly in structure from the original AIG, which makes the SAT miter harder above 22 qubits: on 14 large structural instances (11 simon3, majority n41/n51, mcnc my_adder) it cannot decide within 600 s; these are recorded as unverified (not counted as correct), and best_known on these instances comes from other tools; on majority n63 the tool does not finish within 60 s (timeout).
- The affine class of probe s40602 (6 inputs) is one of the 6 classes missing from the database, so XAG MC cut rewriting cannot resynthesize it by whole-function lookup (13 AND gates); best_known is 12 Toffolis (XAG + MC), short of the ≤ 11 target. The optimum file contains a verified circuit with 11 Toffolis (6 AND gates), but it comes from a long-running upper-bound computation, not from the 60 s baseline.

## 5. Sources and licenses

SATLIB uf20/uf50 (no license statement; uuf50 not used); EPFL combinational benchmarks @ 82d8cc69 (MIT); the AES S-box is constructed from the FIPS-197 definition; the S-box tables of Camellia, ARIA, CLEFIA, Kuznyechik and Magma are taken from the original texts of RFC 3713 / 5794 / 6114 / 7801 / 8891 (pinned by sha256, self-checked when parsed: permutation, the example values in the RFC, and the inverse table); ISCAS-85 and MCNC LGSynth'91 are taken from the benchmark collection of the Czech Technical University (the original CBL/MCNC hosts are no longer reachable; no license statement); mockturtle @ d9e02495 (MIT) and the NIST 6-variable AND-optimal circuits @ b7678d67 (the repository has no LICENSE; `env/build_minmc.sh` builds the database and checks its sha256). See `data/v1/external/fetch_B.sh` and `SOURCES_B.json`.

## 6. Baseline definitions

- Each (instance, tool, track) gets 60 s of single-core wall-clock time; randomized/iterative tools are rerun with different seeds within the budget and the best result is kept; results delivered after the budget are recorded as timeouts; output checking has a separate 600 s window that does not count toward the tool budget.
- The machine is an Apple M3 Max (12 performance cores + 4 efficiency cores). When baselines run 10-16 single-core jobs in parallel, the OS schedules some jobs on efficiency cores, where the same 60 s wall-clock budget corresponds to less compute, so the effective compute per record is not perfectly uniform (each record stores hardware information). This mainly affects tools that improve over time (rustiq, LightSABRE, OLSQ2, etc.) and has no effect on deterministic tools (category B's pebbling SAT and XAG use conflict limits and are deterministic).
- Records of some baselines carry `concurrency` measured at run time (number of concurrency slots, number of jobs running at start, 1-minute load); the others carry `concurrency_estimate`, computed during aggregation (the number of simultaneously running jobs reconstructed from the start/end times of all cached records, 1 s resolution, excluding other processes). For the final evaluation, `qbank rebaseline <C> --split test --tools <time-limited tools>` reruns the time-limited baselines on test instances at fixed concurrency (default = number of performance cores); results are stored separately and best_known is not changed.
- All baseline outputs are verified by this benchmark's checkers and their costs recomputed by `qbank.core.costs`; "unverified" never counts as correct.
- best_known = min(verified baselines, published values whose semantics and budget both match), with the source stated; known optima/lower bounds in `data/v1/optimal/B.jsonl`.

## 7. Reproduction

```
bash env/bootstrap_env.sh
qbank generate B && qbank baselines B && qbank optimal B && qbank aggregate B && qbank report B
```
