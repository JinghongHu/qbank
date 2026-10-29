# qbank Phase-0 Recon: External Data Sources (verified)

- Access date: **2026-09-25**. Every fact below comes from something fetched in this session: `git ls-remote` / shallow `git clone`, GitHub REST API (unauthenticated), PyPI JSON API, `curl` of official pages, arXiv abs/HTML/PDF, WebSearch (used only to locate URLs).
- Scratch dir: `/private/tmp/claude-502/-Users-hjh-PycharmProjects-Qevovle/1f29f559-556e-45a5-8721-319594d33bc5/scratchpad/recon_datasets/` (clones under `clones/`, PyPI wheels under `pypi/`, SATLIB archives under `satlib/`, HamLib listing/CSVs under `hamlib/`, RevLib archives under `revlib/`). Nothing was written under the project dir.
- HEAD SHAs come from `git ls-remote` at query time. Commit dates come from the GitHub API `commits/{sha}` and were cross-checked against the shallow clone's `git log -1`. Several MQT/ABC repos got commits **today**, so their HEAD moves quickly.
- Method notes:
  - Local `~/.gitconfig` rewrites `https://github.com/` to SSH, and parallel SSH clones were reset. Clones were therefore done with `GIT_CONFIG_GLOBAL=/dev/null` over HTTPS. The user config was not changed.
  - The GitHub API unauthenticated quota (60/h) ran out near the end. The repo metadata for `reversiblebenchmarks.github.io` therefore came from a clone instead of the API.

---

## Summary table

| # | Resource | Official URL | HEAD / version (date) | License | Scale | Format |
|---|---|---|---|---|---|---|
| 1 | QCircuitBench | https://github.com/EstelYang/QCircuitBench (arXiv:2410.07961) | `bdeb8c4e7e64935e684cff604d6739415eec8329` (2026-05-06) | MIT (LICENSE file) | Paper: 3 suites, 25 algorithms, 120,290 data points. Repo: 59,423 files, ~801 MB (API size). Full zip on Google Drive: 6.8G | OpenQASM 3.0 + `.inc` + Python verification; Cirq version too |
| 2 | MQT Bench | https://github.com/munich-quantum-toolkit/bench (cda-tum/mqt-bench redirects here); PyPI `mqt.bench` | repo `2c4e6327e5c976f9b7b7866e0b2228c96904e651` (2026-09-25); PyPI **2.3.0** (2026-09-12) | MIT | 36 benchmark generators | Qiskit `QuantumCircuit` → QASM2 / QASM3 / QPY |
| 3 | QED-C App-Oriented Benchmarks | https://github.com/SRI-International/QC-App-Oriented-Benchmarks | `feb22a900d9d94d40e81bc1d25e149bd8f3cbc18` (2026-07-30, branch `master`); PyPI `qedcbench` 2.0.8 | Apache-2.0 | 17 benchmarks | Python generators (Qiskit / CUDA-Q) |
| 4 | QUBIKOS | https://github.com/ping-shuo-hao/qubikos (arXiv:2502.08839) | `442a994884a6a5fd37725f59b8b42c90fd1be387` (2025-04-30) | **No LICENSE file** (API: null) | 160 example QASM (5.2 MB) + generator | OpenQASM 2.0 |
| 5 | QUEKO | https://github.com/UCLA-VAST/QUEKO-benchmark (arXiv:2002.09783) | `2ee23a12aff894f1861d3d49eb14d09d9f9956bd` (2022-02-07) | BSD-3-Clause | 900 QASM + 540 meta CSV + 540 solution CSV | OpenQASM 2.0 + CSV |
| 6 | HamLib | https://portal.nersc.gov/cfs/m888/dcamps/hamlib/ (arXiv:2306.13126, Quantum 8, 1559 (2024)) | dataset v1.1 (Aug 2024; latest file 2024-09-24) | **No license file on the portal**; readme asks for citation; paper is CC BY 4.0 | 2,035 files, ~41.5 GiB, ~1.61 M Hamiltonian entries | HDF5 inside ZIP (+ CSV summaries) |
| 7 | SATLIB uniform random 3-SAT | https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html | SATLIB v1.4.4 (page says "01/05/11") | **No license/terms statement found** | uf20-91: 1000; uf50/uuf50-218: 1000 each; uf/uuf75-325: 100 each; … | DIMACS CNF in .tar.gz |
| 8 | EPFL combinational suite | https://github.com/lsils/benchmarks | `82d8cc6910419298e713a46644ed59fd3df53038` (2026-08-13) | MIT | 10 arithmetic + 10 random_control (+3 MtM on Zenodo) | AIGER (.aig), BLIF, Verilog, VHDL |
| 9 | RevLib | https://revlib.org (= www.revlib.org = informatik.uni-bremen.de/rev_lib/) | **Reachable** (HTTP 200) | **No license**; page meta "(C) RevLib"; cite request | Site: 154 functions / 454 circuits. Bulk tgz: 317 .real, 133 .pla + 6 .src | .real, .pla, .src (SyReC) |
| 10 | Optimal 4-bit reversible (Golubitsky/Falconer/Maslov) | arXiv:1003.1914, arXiv:1103.2686 | — | — | **No public database/code found**. Only the 5 (144 with symmetries) 15-gate functions on Maslov's page | .tfc |
| 11 | OLSQ2 | https://github.com/UCLA-VAST/OLSQ2 | `0d7066f45b073bfd5f163a424b758026639f5acf` (2024-05-29) | BSD-3-Clause | 30 benchmark QASM in repo | Python package (not on PyPI) |
| 12 | ABC | https://github.com/berkeley-abc/abc | `ab2139ee0c418f54136deb4e8e89eeea3b87efc8` (2026-09-25) | UC Regents permissive text (`copyright.txt`); GitHub SPDX = NOASSERTION | — | C source |
| 13 | MQT QMAP / QCEC / QECC | github.com/munich-quantum-toolkit/{qmap,qcec,qecc} | PyPI: qmap **3.10.0** (2026-09-12), qcec **3.10.0** (2026-09-08), qecc **2.0.0** (2026-07-13) | MIT (all three) | QECC ships 5 named CSS codes + 3 lifted-product + 3 misc | — |

---

## 1. QCircuitBench

**Official sources**
- Paper: https://arxiv.org/abs/2410.07961. Title "QCircuitBench: A Large-Scale Dataset for Benchmarking Quantum Algorithm Design". Versions v1 2024-10-10, v2 2025-11-06, v3 2025-12-16. The paper is on the arXiv non-exclusive license. The paper HTML (v3) states NeurIPS 2025 Datasets & Benchmarks Track (also in the README BibTeX) and lists the repo URL `https://github.com/EstelYang/QCircuitBench`.
- Repo: https://github.com/EstelYang/QCircuitBench. The URL `github.com/estelyang/qcircuitnet_dataset` from search results redirects to it: the API returns full_name `EstelYang/QCircuitBench`, and ls-remote shows the same SHA.
  - Default branch `main`, HEAD `bdeb8c4e7e64935e684cff604d6739415eec8329`, commit date 2026-05-06T13:50:01Z ("fix random import").
  - License: MIT (LICENSE: "Copyright (c) 2026 Rui Yang and Ziruo Wang"); API SPDX `MIT`.
  - Repo size (API `size`): 819,984 KB (~801 MB). 59,423 files at HEAD; top file types: 16,589 .qasm, 15,279 .py, 13,862 .txt, 8,092 .png, 4,028 .inc.
- Full dataset: the README says GitHub holds a "demo version"; the complete dataset is on Google Drive at https://drive.google.com/file/d/1dawEUtGcX4AryN2djZ8VVaLwPe6kpziA/view. The Drive page shows file name `QCircuitBench_full_dataset.zip` and size **6.8G**. **Not downloaded**, so no sha256.
- Environment (`environment.yml`): python 3.10.9, qiskit==1.1.0, qiskit-aer==0.15.1, qiskit-qasm3-import==0.6.0, qiskit-algorithms==0.3.0, qiskit-machine-learning==0.7.2, networkx==3.4.2.

**Scale (from the paper, v3 HTML)**
- 3 task suites, 25 algorithms, **120,290 data points**:
  - Task I Oracle Construction: 35,872
  - Task II Quantum Algorithm Design: 6,534
  - Task III Random Circuit Synthesis: 77,884
- Random circuits are sampled from the Clifford set {H, S, CNOT} and the universal set {H, S, T, CNOT}. The task is to reproduce the specified state.
- Custom gates such as multi-controlled X ship in `customgates.inc`. The paper quotes "45,060 lines for 14 qubits".

**Parametrization / max sizes (derived from repo directory names `…_n{N}`)**

N is the size parameter used in file names, not always the circuit width. Simon-type circuits use 2n qubits.

| Area | Algorithm dir | n range in repo | QASM files in repo |
|---|---|---|---|
| Algorithm_Design/Quantum_Computing | bernstein_vazirani, deutsch_jozsa, simon, generalized_simon_multi, quantum_fourier_transform | 2..30 | 29 each |
| | generalized_simon_ternary | 2..11 | 10 |
| | grover | 2..14 | 13 |
| | phase_estimation | 2..14 | 26 |
| | shor | (no n in names) | 7 |
| Algorithm_Design/Quantum_Information | ghz_state 2..133; w_state 2..133; random_number_generator 1..133; swap_test 1..20; quantum_key_distribution 20..50; quantum_teleportation, superdense_coding (no n) | | 132 / 264 / 133 / 20 / 31 / 1 / 4 |
| Algorithm_Design/Variational_Circuits | efficient_su2 2..12; qaoa 2..12; qae, data_encoding (no n) | | 44 / 80 / 63 / 3 |
| Oracle_Construction/Quantum_Logic_Synthesis | bernstein_vazirani, deutsch_jozsa, grover, diffusion_operator 2..14; simon 2..8; generalized_simon_multi 2..30; **generalized_simon_ternary 2..7** | | 36 / 39 / 35 / 13 / 19 / 85 / 16 |
| Oracle_Construction/Problem_Encoding | grover_sudoku (single instance); grover_triangle 3..14 | | 2 / 120 |
| Random_Circuits | clifford 2..12; universal 2..12 | | 1,155 / 5,745 |

**"Problem Encoding" tasks that exist (important for parametric extension)**
- The repo `Oracle_Construction/Problem_Encoding/` contains exactly **two** tasks. The Cirq_Version mirrors them.
  1. `grover_sudoku`
     - One fixed instance: a **2×2** binary Sudoku with clause list `[[0,1],[0,2],[1,3],[2,3]]`.
     - Oracle = XOR clause bits + `mcx` onto the output qubit; 4 variable qubits, 4 clause ancillas, 1 output.
     - Files: `sudoku_description.txt`, `sudoku_generation.py`, `sudoku_dataset.py`, `sudoku.qasm`, `customgates.inc`.
  2. `grover_triangle`
     - Triangle finding on a random graph (each edge included with p = 1/2, `generate_edges`), for n = 3..14 nodes, with `CASE_NUM = 5` trials each: 60 instances, 120 QASM (full_circuit + extracted).
     - The input is restricted to 3-hot states. The oracle uses `Adder`/`Reverse_Adder` gates on 2 edge ancillas plus the output.
     - `info_trial{i}.txt` stores the edge list.
- **generalized_simon_ternary is NOT a Problem-Encoding task.** In the repo it sits in `Oracle_Construction/Quantum_Logic_Synthesis/` (oracle, n = 2..7) and in `Algorithm_Design/Quantum_Computing/` (algorithm, n = 2..11). The paper describes the generalized Simon problem as p-ary with a rank-k subgroup and runs experiments for p = 3 (ternary). It sits alongside `generalized_simon_multi` (multi-secret-string).
- The paper (Appendix A.4) calls Problem Encoding "demonstrations", mentions SAT and triangle finding, and says "will include more applications in future work".
- Caveat: **Problem_Encoding has no `*_verification.py`, `*_utils.py` or `*_post_processing.py`** (0 matching files in the tree), and no lm_eval task. Verification for these would have to be built by us.

**Verification (paper §4.1 + repo `*_verification.py`)**
- Returns the triplet (V_QASM syntax, V_code/Python syntax, E_sem).
- Algorithm-design and oracle tasks: E_sem = the fraction of (test case × shots) where the result equals ground truth. Test cases are the `test_oracle/n{N}/trial{t}/oracle.inc` files. Simulation uses Qiskit AerSimulator.
- State-preparation and random-circuit tasks: E_sem = fidelity |⟨ψ*|ψ⟩|².
- The paper explicitly says it does *not* do formal equivalence checking: "we use a suite of end-to-end test cases".
- A syntax failure falls back to the ground-truth circuit or post-processing so the other parts can still be scored.

**Efficiency metrics (paper + code `efficiency_check`)**
- **Gate Count Ratio** = model `sum(count_ops())` / reference.
- **Shot Count Ratio** = model query complexity / reference.
- **Time Count Ratio** = model post-processing wall time / reference.
- Lower is better. The code returns NaN where not applicable (e.g., W-state shots).
- Evaluation harness: `lm_eval_tasks/` has yaml tasks for EleutherAI lm-evaluation-harness (qasm_/cirq_ algo, oracle, random; bleu/ppl variants). `benchmark_subset/` has one instance per algorithm for Terminal-Bench/Harbor. `task_difficulty.json` has easy/medium/hard labels for 28 task keys.

**Benchmark caveats**
- It is a code-generation benchmark for LLMs: the task is text description → QASM + Python post-processing.
- Many families are single deterministic circuits per n (e.g., GHZ/W/QFT). Oracle families vary the secret or key strings via `trial` subdirs.
- The Problem-Encoding part is tiny: 1 Sudoku instance and 60 triangle instances, with no verifier.
- References are "a valid reference implementation", not proven-optimal circuits.

---

## 2. MQT Bench

**Official**
- Repo: https://github.com/munich-quantum-toolkit/bench. `cda-tum/mqt-bench` resolves to the same repo (API full_name `munich-quantum-toolkit/bench`, same SHA).
  - Branch `main`, HEAD `2c4e6327e5c976f9b7b7866e0b2228c96904e651`, 2026-09-25T15:08:40Z.
  - License MIT ("Copyright (c) 2023 - 2026 Chair for Design Automation, TUM; (c) 2025 - 2026 Munich Quantum Software Company GmbH").
  - Homepage in the API: https://mqt-bench.app/ (a JS app; returns 200 but no static content).
- PyPI `mqt.bench`: **latest 2.3.0**, uploaded 2026-09-12. Requires Python >=3.11 and `qiskit[qasm3-import]>=2.1`, networkx, numpy, scikit-learn. Earlier releases: 2.2.3 (2026-07-07), 2.2.2, 2.2.1, 2.1.0.
  - Wheel `mqt_bench-2.3.0-py3-none-any.whl` sha256 `90337047f042037e7f2e62221a8a77f3c41a974e0ac1b87238e53b6841b6a78e` (downloaded and verified).
  - sdist sha256 per PyPI: `f754fbb0bafcbdbd7e93c27cc9a1dab40887b77a56866169d446a0c9d7bc432a`.

**Benchmarks in 2.3.0 (36)**

Verified by installing 2.3.0 in a scratch venv (qiskit 2.5.2) and calling `get_available_benchmark_names()`:

`ae, bmw_quark_cardinality, bmw_quark_copula, bv, cdkm_ripple_carry_adder, dj, draper_qft_adder, dynamic_qft, full_adder, ghz, ghz_dynamic, graphstate, grover, half_adder, hhl, hrs_cumulative_multiplier, iqpe, modular_adder, multiplier, qaoa, qft, qftentangled, qnn, qpeexact, qpeinexact, qwalk, randomcircuit, rg_qft_multiplier, seven_qubit_steane_code, shor, shors_nine_qubit_code, vbe_ripple_carry_adder, vqe_real_amp, vqe_su2, vqe_two_local, wstate`

- `shor` only accepts circuit_size ∈ {18, 42, 58, 74}.

**Abstraction levels**
- `BenchmarkLevel`: `ALG`, `INDEP`, `NATIVEGATES`, `MAPPED`.
- ALG is the raw algorithmic circuit.
- INDEP = `transpile(opt_level, seed_transpiler=10)` with no target.
- NATIVEGATES/MAPPED need a Target:
  - Gatesets: clifford+t, clifford+t+rotations, ibm_falcon, ibm_eagle, ibm_heron, ionq_forte, ionq_aria, iqm, quantinuum, rigetti.
  - Devices: ibm_falcon_27, ibm_falcon_127, ibm_eagle_127, ibm_heron_133, ibm_heron_156, ionq_aria_25, ionq_forte_36, iqm_crystal_5, iqm_crystal_20, iqm_crystal_54, quantinuum_h2_56, rigetti_ankaa_84.
- A mirror-circuit option exists (`generate_mirror_circuit=True`, U·U†).
- Output: `OutputFormat` = qasm2 | qasm3 | qpy.

**Uniqueness per (algorithm, n)**
- In general deterministic, with hard-coded seeds:
  - dj uses rng(10)
  - qpeexact/qpeinexact use random.seed(10)
  - randomcircuit uses seed=10
  - qaoa uses seed=10 for its random adjacency matrix
  - iqpe uses seed=10
  - parameter binding uses rng(10)
  - transpile uses seed_transpiler=10
- Empirically, qaoa/randomcircuit/dj/vqe_su2 gave identical circuits across two calls. **Exception: `graphstate` defaults to `seed=None`**, so it gave a different random regular graph on each call; with `seed=1` it was identical.
- Variation comes only through extra kwargs, for example:
  - bv `hidden_string` (default alternating 1/0)
  - dj `balanced`
  - ae `probability`
  - qaoa `repetitions`, `seed`
  - graphstate `degree`, `seed`
  - qwalk `depth`
  - vqe_* `reps`, `entanglement`
  - adders `kind`
  - iqpe `exact`, `seed`
- So by default there is essentially **one circuit per (family, n)**.

**Parameters**
- `random_parameters=True` (the default) binds all parameters with `np.random.default_rng(10)` uniform in [0, 2π), so it is deterministic.
- `random_parameters=False` keeps them **symbolic**. Verified: qaoa(5) has 4 free Parameters; vqe_su2(4) has 32.

**Caveats**
- These are circuits, not problems: there are no task specs or verifiers.
- QAOA uses a random MaxCut instance without a stored optimum.

---

## 3. QED-C Application-Oriented Benchmarks

**Repo**
- https://github.com/SRI-International/QC-App-Oriented-Benchmarks. Default branch **`master`**, HEAD `feb22a900d9d94d40e81bc1d25e149bd8f3cbc18`, 2026-07-30T04:56:54Z ("Fix bug in hamlib with data_suffix").
- A v1.x-compatible branch `master-260411-v1.2.2` is referenced in the README.

**License**
- **Apache-2.0**: API SPDX `Apache-2.0`; the LICENSE file is the Apache 2.0 text with the unfilled "Copyright [yyyy] [name of copyright owner]" template.
- Caveat: the README footer also says "© 2025 Quantum Economic Development Consortium (QED-C). All Rights Reserved."
- PyPI `qedcbench` 2.0.8 and `qedclib` 2.0.8 both declare Apache-2.0.

**Application benchmarks: 17**

Listed in `doc/docs/benchmarks.md`; 17 dirs under `qedcbench/`.

| Level | Benchmarks |
|---|---|
| L1 | Deutsch-Jozsa, Bernstein-Vazirani, Hidden Shift |
| L2 | Quantum Fourier Transform, Grover's Search |
| L3 | Phase Estimation, Amplitude Estimation, HHL Linear Solver |
| L4 | Monte Carlo, Hamiltonian Simulation, HamLib Simulation, VQE, Shor's Algorithm |
| L5 | MaxCut (QAOA), Hydrogen Lattice, Image Recognition |
| Other | Quantum Reinforcement Learning |

**How it works**
- Python generators per qubit width. Default `run_all`: 5 benchmarks, 2..8 qubits, `max_circuits` 3 per qubit group, 100 shots.
- Success is measured by fidelity to the expected output distribution (`qedclib/metrics.py`: `hellinger_fidelity_with_expected`, `polarization_fidelity`).
- Size on disk: clone ~108 MB (qedcbench/ 60 MB, doc/ 17 MB, .git 29 MB).

**Caveats**
- It is a hardware-performance (volumetric) suite: circuits are generated on the fly, not a static dataset.
- The HamLib benchmark pulls HamLib data.

---

## 4. QUBIKOS

**Paper**
- https://arxiv.org/abs/2502.08839 (fetched, HTTP 200): "Assessing Quantum Layout Synthesis Tools via Known Optimal-SWAP Cost Benchmarks". Authors Ping, Lin, Tan, Cong. v1 2025-02-12, v2 2025-03-04, 8 pages.
- The arXiv license for the paper is CC BY 4.0.
- The abstract reports optimality gaps: LightSabre 63×, ML-QLS 117×, QMAP 250×, t|ket> 330×.

**Code/data repo**
- https://github.com/ping-shuo-hao/qubikos (found via WebSearch; the README cites arXiv:2502.08839). Branch `main`, HEAD `442a994884a6a5fd37725f59b8b42c90fd1be387`, 2025-04-30T22:01:41Z ("Add files via upload").
- **License: no LICENSE file.** API license = null. No redistribution grant, so the default is all rights reserved and only the paper is CC BY 4.0.
- Contents:
  - `QUBIKOS.py` (327 lines; deps networkx, qiskit). API: `generate_qubikos_circuit(benchmark_file, compiled_file, coupling_list, number_of_swap, n_2q_gates, n_1q_gates=0)`. It returns (benchmark circuit, compiled witness circuit with SWAPs) and writes both as QASM2.
  - Also a `checker(coupling, initial_mapping, answer)` helper.
  - `examples/` (5.2 MB): 4 devices × SWAP counts {5, 10, 15, 20} × 10 seeds = **160 QASM** plus a coupling-graph text file per device (Python-literal list; the Aspen file is misspelled `couping.txt`).
- Example file naming: `{Device}_{optSWAP}_{#2q gates}_{idx}.qasm`.

| Device dir | Physical qubits (qreg) | 2Q gates / file (repo) | Paper setting |
|---|---|---|---|
| aspen (Aspen-4) | 16 | 300 | 300 |
| Sycamore | 54 | 1500 | 1500 |
| Rochester | 53 | 1500 | 1500 |
| Eagle | 127 | **4000** | **3000** (paper text) |

**What instances look like**
- A random-looking CX-only circuit over **all** physical qubits (logical = physical count).
- It is built from "sections": each required SWAP is forced because the interaction graph of the section is not isomorphic to any subgraph of the coupling graph. Redundant gates on currently-adjacent pairs are padded in.
- The optimal SWAP count is known by construction. The paper additionally checked optimality with OLSQ2 on Aspen-4 and a 3×3 grid: 400 circuits per architecture, SWAP 1..4, ≤30 two-qubit gates, using PySAT 1.8.dev13 and z3 4.13.3.0.

**Caveats**
- Example files contain only `cx` (292,000 cx total). The current generator randomly emits cx/cz and x/y/z/h/s/t, so the examples came from an earlier version.
- The compiled/witness circuits and the optimality-study circuits are **not** in the repo.
- Eagle gate count mismatch between repo (4000) and paper (3000).

---

## 5. QUEKO

**Repo and paper**
- https://github.com/UCLA-VAST/QUEKO-benchmark. Branch `master`, HEAD `2ee23a12aff894f1861d3d49eb14d09d9f9956bd`, 2022-02-07T01:02:44Z.
- License **BSD-3-Clause** ("Copyright (c) 2020, Bochen Tan").
- Paper: arXiv:2002.09783, "Optimality Study of Existing Quantum Computing Layout Synthesis Tools", IEEE Trans. Computers 2020 per README. The abstract says the benchmarks have "known optimal depths and gate counts".

**Instances: 900 QASM (OpenQASM 2.0) + `meta/` 1,080 CSV**

| Set | Files | Device(s) | Optimal depth (cycles) | Gate density |
|---|---|---|---|---|
| BNTF (near-term feasible) | 180 | 16QBT Aspen-4 (TFL) and 54QBT Sycamore (QSE) | 5, 10, …, 45 | TFL / QSE |
| BSS (scalability) | 360 | 16QBT, 20QBT Tokyo, 53QBT Rochester, 54QBT Sycamore | 100, 200, …, 900 | QSE |
| BIGD (gate-density impact) | 360 | 20QBT Tokyo | 45 | 36 (d1, d2) combinations, e.g. `.0D1_.5D2` |

- 10 instances per configuration (serial 0..9).
- Device graphs (`CONNECTION.py` `INDEX_CONNECTION_LIST`):

| Device | Qubits | Edges |
|---|---|---|
| Aspen-4 | 16 | 18 |
| Tokyo | 20 | 43 |
| Rochester | 53 | 58 |
| Sycamore | 54 | 88 |
| Ourense | 5 | 4 (not used by files) |

- Gates: only `x` and `cx` (3,429,220 x + 1,371,930 cx over all 900 files). The largest file (54QBT_900CYC) has 34,509 lines.
- Known optimum: depth = the `CYC` number in the name. Circuits are SWAP-free-optimal (QUBIKOS's abstract describes prior work as "SWAP-free benchmarks with known-optimal depths").
- `meta/*_solution.csv` gives an optimal initial mapping (line i = physical qubit of q[i]). Solution files exist **only for BNTF + BSS** (540 meta + 540 solution); **BIGD has no meta/solution files** in the repo.
- Size: BSS 48 MB, meta 25 MB, BIGD 2.2 MB, BNTF 1.5 MB (clone total 91 MB).
- Generator `queko.py` (networkx) can make new instances for any edge list, depth and density.

---

## 6. HamLib

**Official**
- Download site: https://portal.nersc.gov/cfs/m888/dcamps/hamlib/. The paper states: "At the time of publication, the HamLib dataset is downloadable from the following URL". It is an Apache directory index, HTTP 200.
- Paper: https://arxiv.org/abs/2306.13126, v1 2023-06-22 … v5 2024-11-18, journal ref *Quantum 8, 1559 (2024)*, arXiv license CC BY 4.0.
- Code snippets: `hamlib_snippets.py` on the portal, plus https://github.com/Azulene-Labs/hamlib_functions (API: Apache-2.0, branch main).
- Note: PyPI name `hamlib` (0.0.1, 2023, author "HaveTwoBrush") is **unrelated**.

**License**
- **No license file on the portal.** `readme.txt` only asks users to cite the paper, and redistribution terms are not stated.
- Release history in readme: v1.0 June 2023, v1.1 August 2024. The H70/H80 chains were removed for corruption; biqmac archives changed to zip.

**Scale (recursive crawl of the directory index; sizes are the Apache "Size" column, so approximate)**
- 2,035 files, ~41.5 GiB total: 1,906 .zip, 48 .csv, 62 .png, 16 .txt, 2 .hdf5 (test), 1 .py. File dates 2023-02-20 … 2024-09-24.
- The summary CSVs (columns `File, Dataset, nqubits, terms, one_norm`) list **1,609,769 Hamiltonian entries**, nqubits 2..44,851.

| Category/subcategory | Files | Size | Entries in CSVs | nqubits |
|---|---|---|---|---|
| binaryoptimization/max3sat (random + SATLIB-derived uf/uuf/aim/flat/lran) | 29 | 1.83 GB | 979,164 | 2..2000 |
| binaryoptimization/maxcut (random, biqmac, ciqube) | 37 | 0.29 GB | 73,822 | 2..44,851 |
| binaryoptimization/qmaxcut | 25 | 0.51 GB | 73,821 | 2..44,851 |
| chemistry/electronic (standard, hydrogen chains/rings/sheets, bond_breaking, transition_metals) | 532 | 8.09 GB | 1,989 | 4..120 |
| chemistry/vibrational | 38 | 3.28 GB | 1,689 | 2..288 |
| condensedmatter/bosehubbard | 9 | 14.77 GB (one file BH_D-2_d-8.zip = 12G) | 23,780 | 4..10,768 |
| condensedmatter/fermihubbard | 6 | 0.39 GB | 14,688 | 4..5,384 |
| condensedmatter/heisenberg | 3 | 0.05 GB | 5,698 | 2..2,692 |
| condensedmatter/tfim | 3 | 0.02 GB | 7,326 | 2..2,692 |
| discreteoptimization/maxkcut | 1,282 | 10.66 GB | 423,264 | 2..5,706 |
| discreteoptimization/tsp (Ncity 4..64) | 59 | 1.57 GB | 4,528 | 8..4,096 |

**Format**
- Each .zip holds one .hdf5.
- Each HDF5 dataset key (e.g. `reg-3_n-100_rinst-00`) is a string in OpenFermion-QubitOperator text form, e.g. `75.0 [] + -0.5 [Z0 Z26] + ...`. It carries attributes `nqubits`, `terms`, `one_norm`.
- Graph and clause-list instances are stored in separate zips (`graphs/`, `instances/`).
- Discrete problems (Max-k-Cut, TSP) come in unary/one-hot, Gray and standard-binary encodings. "Unencoded" Hamiltonians are also included for some models.
- Checked sample: `binaryoptimization/maxcut/random/ham-graph-regular_reg-3.zip` (sha256 `7b0ee8a2afdb93977d88fdaa1da557c1403e34d05238d29e07722becf0579a90`) has 920 keys. The whole MaxCut-random subset has 7,984 entries (circulant, complete_bipart, gnp_k-2..5, regular_reg-3..6, star), n = 2..900.

**Selective download**
- Browse the HTTP index, grab one small per-subdirectory CSV to filter by nqubits/terms, then fetch only the needed zip. The paper's snippet A.3 streams a zip into memory with `requests` + `zipfile`.
- Reader helpers: `print_hdf5_structure`, `get_hdf5_keys`, `read_openfermion_hdf5`, `read_qiskit_hdf5`, `read_graph_hdf5`, `read_clause_list_hdf5`, etc.

**Caveats**
- These are problem Hamiltonians, not circuits.
- The summary CSVs contain **no optimal values or ground energies**. The paper only mentions "approximate ground states" as auxiliary info for some sets.
- Some zips are huge (12G).

---

## 7. SATLIB – Uniform Random-3-SAT

**Official**
- Page: https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html (HTTP 200). It describes itself as the Canadian SATLIB site at UBC. The main site listed is http://www.satlib.org (not checked). SATLIB "Version 1.4.4, 01/05/11".
- Family description: https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/descr.html.
  - Instances are unforced, phase-transition region, split by a complete solver into uf* (all satisfiable) and uuf* (all unsatisfiable).
  - n = 20, 50, 100 have 1000 instances; the other sizes have 100.

**License/terms**
- **No license or terms-of-use statement found** on benchm.html, descr.html or index-ubc.html. The site invites submissions.

**Archives** (base `https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/`). All downloaded and hashed; each archive contains only .cnf files.

| Set | Vars/clauses | Instances (verified) | Archive bytes | sha256 |
|---|---|---|---|---|
| uf20-91.tar.gz | 20/91 | 1000 | 323,695 | `be2835295e8500bb28f0314eba70bd0deaff1250b187260f7b6d0772bdf111a5` |
| uf50-218.tar.gz | 50/218 | 1000 | 878,261 | `a40862e52dfdce78620b037254579a02dbda8182d2879433658a4c15cb00327c` |
| uuf50-218.tar.gz | 50/218 | 1000 | 876,573 | `24cc9f492673e0f975fecc56b3a4d8ac21c385cc46205d83b7491a787f43e13d` |
| uf75-325.tar.gz | 75/325 | 100 | 139,242 | `f879d4f619e8cd4b24be6c70b86b1bc1ed851cf0c5cc0ee97cd750e0cadb5ff5` |
| uuf75-325.tar.gz | 75/325 | 100 | 139,278 | `7f8a97aa4d4cbe0d5681746644aac23dc0b5d182065df97e62977716bbccd046` |
| uf100-430.tar.gz | 100/430 | 1000 | 1,906,370 | `7f691acb8c45790ef8178dd01bb362cf50da608d478be9965599131f0a763e59` |
| uuf100-430.tar.gz | 100/430 | 1000 | 1,908,531 | `736c6f94fecae346a00501b197c482e146b1c6ab05fb6d2e4666e520b8e8508a` |

- Also listed but not downloaded: uf/uuf125-538, 150-645, 175-753, 200-860, 225-960, 250-1065, with 100 instances each per the page.

**Caveats**
- Format is DIMACS CNF, e.g. header `p cnf 20  91`.
- **Files end with a non-standard trailer `%\n0\n`**, which strict parsers must handle.
- Paths inside the archives are inconsistent: uf20/uf50/uf100 are flat; uuf50 uses `UUF50.218.1000/`; uf75 uses `ai/hoos/Shortcuts/UF75.325.100/`.
- Only SAT/UNSAT status is known (by set membership). **No models or solutions are shipped.**
- HamLib already hosts Max-3-SAT Hamiltonians derived from uf20/uf100/uf200/uf250/uuf… (see §6).

---

## 8. EPFL Combinational Benchmark Suite

**Repo**
- https://github.com/lsils/benchmarks. Branch `master`, HEAD `82d8cc6910419298e713a46644ed59fd3df53038`, 2026-08-13T22:17:40Z ("Merge pull request #36 from lsils/new_2026_results").
- License **MIT** ("Copyright (c) 2018").
- Tags (best-results snapshots): v2015, v2016, v2017.1, v2018.1, v2019.1, v2020.1, v2021.1, v2022.1, v2023.1, v2025.1.

**Formats**
- Each circuit ships as `.aig` (binary AIGER), `.blif`, `.v` (Verilog) and `.vhd` (VHDL).
- `best_results/{size,depth}/`: 43 LUT-6 BLIFs (best-known).
- Size on disk: arithmetic/ 46 MB, random_control/ 8.9 MB, best_results/ 105 MB. The 20 .aig files total 1.43 MB.

**Circuits** (inputs/outputs from AIGER headers `aig M I L O A`, matching the README tables; LUT-6/levels from README, ABC `if -K 6`)

| Arithmetic | In | Out | AND nodes | LUT-6 | Levels |
|---|---|---|---|---|---|
| adder | 256 | 129 | 1,020 | 254 | 51 |
| bar (barrel shifter) | 135 | 128 | 3,336 | 512 | 4 |
| div | 128 | 128 | 57,247 | 9,311 | 867 |
| hyp | 256 | 128 | 214,335 | 44,635 | 4,194 |
| log2 | 32 | 32 | 32,060 | 8,008 | 77 |
| max | 512 | 130 | 2,865 | 842 | 56 |
| multiplier | 128 | 128 | 27,062 | 5,913 | 53 |
| sin | 24 | 25 | 5,416 | 1,458 | 42 |
| sqrt | 128 | 64 | 24,618 | 5,720 | 1,033 |
| square | 64 | 128 | 18,484 | 3,985 | 50 |

| Random/control | In | Out | AND nodes | LUT-6 | Levels |
|---|---|---|---|---|---|
| arbiter | 256 | 129 | 11,839 | 2,722 | 18 |
| cavlc | 10 | 11 | 693 | 122 | 4 |
| ctrl | 7 | 26 | 174 | 29 | 2 |
| dec | 8 | 256 | 304 | 287 | 2 |
| i2c | 147 | 142 | 1,342 | 365 | 4 |
| int2float | 11 | 7 | 260 | 49 | 3 |
| mem_ctrl | 1,204 | 1,231 | 46,836 | 12,096 | 25 |
| priority | 128 | 8 | 978 | 210 | 31 |
| router | 60 | 30 | 257 | 89 | 7 |
| voter | 1,001 | 1 | 13,758 | 2,691 | 16 |

- MtM (sixteen/twenty/twentythree, 117–153 inputs, 5.6–8.2 M LUT-6) is **not in the repo**. The README links https://zenodo.org/record/2572934 (not fetched).
- Caveat for quantum use: only ctrl, cavlc, int2float and dec have ≤ 11 inputs. Most circuits are far too wide for exact reversible or quantum synthesis.

---

## 9. RevLib

- **Reachable**: http(s)://revlib.org, www.revlib.org and https://www.informatik.uni-bremen.de/rev_lib/ all return HTTP 200 with the same page, so there is no need for a mirror.
- **License/terms: none stated.** Pages carry `<meta name="copyright" content="(C) RevLib">`. cite.php asks for citation of Wille, Große, Teuber, Dueck, Drechsler, "RevLib: An Online Resource for Reversible Functions and Reversible Circuits", ISMVL 2008. No explicit redistribution permission.
- Website counts (index): All functions **154**; All circuits **454**. By library: MCT 252, MCF 6, P 1, NCT 9, MCT+P 19, MCT+MCF 150, EQ 17. `realizations.php` has 457 links to `doc/real/*.real`.
- Bulk archives (downloaded):
  - `https://revlib.org/doc/real/reals.tgz`: 540,042 B, sha256 `a423cea1ea42e77d6e95acc185e1a08878185031940ac0925c6cbb08e9713d2e`. **317 .real**, 5.04 MB uncompressed.
  - `https://revlib.org/doc/func/func.tgz`: 657,177 B, sha256 `b1aa4e245dfa5aec5e229d607c651b70483e0cea51bea4f0343bb71bdd7505d4`. **133 .pla + 6 .src** (SyReC), 6.44 MB uncompressed.
  - The bulk archives therefore hold **fewer files than the site lists** (317 vs 454 circuits). The rest must be scraped per file.
- Formats:
  - `.real` (RevLib v1.0/2.0; spec PDF at `doc/docu/revlib_2_0.pdf`): header `.version .numvars .variables .inputs .outputs .constants .garbage`, then `.begin … .end`.
  - Gate lines in the bulk set: t (Toffoli) 257,339; f (Fredkin) 574; v 484; v+ 199; p (Peres) 56; pi 11.
  - `.numvars` ranges 3..1,617.
  - `.pla` is used for function specs.
- Related but separate resource: D. Maslov's "Reversible Logic Synthesis Benchmarks Page" (see §10), https://reversiblebenchmarks.github.io/. It is *not* a RevLib mirror.

---

## 10. Optimal 4-bit reversible circuit library (Golubitsky / Falconer / Maslov)

- Papers (arXiv license: non-exclusive distribution):
  - arXiv:1003.1914, "Synthesis of the Optimal 4-bit Reversible Circuits" (Golubitsky, Falconer, Maslov). ACM DL lists it in the Proceedings of the 47th DAC (doi 10.1145/1837274.1837440, from search result).
  - arXiv:1103.2686, "A Study of Optimal 4-bit Reversible Toffoli Circuits and Their Synthesis" (Golubitsky, Maslov).
  - Both abstracts: 16! ≈ 2^44 functions; listing optimal circuits for all would need ">100 terabytes". Their method uses hash tables of canonical representatives up to k = 9 gates, with 43.04 GB RAM reported.
- **Data/code availability: none found.** A text search of both PDFs finds no download or code URL. The only data-related reference is [6] "D. Maslov. Reversible logic synthesis benchmarks page. http://webhome.cs.uvic.ca/~dmaslov/". That URL now **redirects to https://reversiblebenchmarks.github.io/** (verified).
- What *is* public on that page:
  - Repo `github.com/reversiblebenchmarks/reversiblebenchmarks.github.io`: branch `main`, HEAD `f88512f6a4c6149ac522ba6f23780c74ca92cfbd`, 2024-02-29. **No LICENSE file.** 228 .tfc, 12 .pla, 178 .html; clone 118 MB.
  - "4-bit with maximal gate count": the **5** functions `4b15g_1..5` needing **15** NOT/CNOT/Toffoli/Toffoli-4 gates in the optimal implementation (144 functions with symmetries). They ship with .tfc circuits marked "m" (minimal) for gate count, from Golubitsky & Maslov (Jan 2011) and Szyprowski & Kerntopf.
  - Plus the classic benchmark functions (hwb*, gf2^n mult, ham*, rd*, nth_prime*, …) with best-known, not necessarily optimal, circuits.
- Other exact-synthesis code: `msoeken/reversible-sota` (HEAD `a5c6fdd2306ecc3321650d9d30bda0ed0b69e1f7`) is a literature survey README, not data.
- A WebSearch summary mentioned Prasad et al. 2006 (optimal ≤6-gate 4-bit NCT circuits) and an "all 3,120,218,828 optimal 4-bit circuits with ≤8 gates" work. **Unverified (not fetched).**
- Practical implication: optimal 3- or 4-bit reference data would have to be **regenerated** by us, e.g. BFS/meet-in-the-middle over NCT.

---

## 11. OLSQ2

- Repo https://github.com/UCLA-VAST/OLSQ2: branch `main`, HEAD `0d7066f45b073bfd5f163a424b758026639f5acf`, 2024-05-29T21:41:18Z ("Update README.md"). License **BSD-3-Clause** ("Copyright (c) 2022, UCLA VAST Lab").
- The README points to https://github.com/WanHsuanLin/OLSQ2 as "the most recent implementation" (z3 C++ interface, and Bitwuzla in branch "Bitwuzla"). Cloned: branch `main`, HEAD `2b83601bd91c2c366688d9bc17e04d26d21dc1eb`, 2024-05-29, BSD-3-Clause. It differs from UCLA-VAST in `solve.py`, `run_olsq.py` and the README.
- **pip-installable? No.**
  - Neither repo has `setup.py` or `pyproject.toml`.
  - PyPI `olsq2` and `OLSQ2` return 404.
  - PyPI `olsq` 0.0.4.1 (2022-05-02, BSD, home https://github.com/tbcdebug/OLSQ) is the *original OLSQ*, not OLSQ2.
  - Use it by cloning (README: `git clone …`).
- Dependencies:
  - `z3-solver` is imported directly. The README asks for >=4.8.15.0, and 4.8.15.0 to reproduce the paper.
  - `pysat` (`from pysat.card import CardEnc`, lazily in solve.py) is used for cardinality encodings 1/2/3/6/7/8/9. The README asks for >=0.1.7.
  - `qiskit` is used for the SABRE upper bound in `olsq/run_h_compiler.py`.
- **Caveat (verified):** `run_h_compiler.py` does `from qiskit.transpiler.passes import Unroller`, which **fails on qiskit 2.5.2**. `olsq/solve.py` imports it at module top, so `from olsq import OLSQ` needs an older Qiskit or a patch.
- Modes: objective depth or SWAP; normal vs transition-based (TB-OLSQ2).
- The repo ships 30 benchmark QASM (queko/, qaoa/, others/).

---

## 12. ABC

- Repo https://github.com/berkeley-abc/abc: branch `master`, HEAD `ab2139ee0c418f54136deb4e8e89eeea3b87efc8`, 2026-09-25T16:10:20Z ("Merge pull request #570 from calewis/fix-cli-and-null-bugs").
- License: GitHub SPDX **NOASSERTION** ("Other"). The file is `copyright.txt`, with no LICENSE file:
  > "Copyright (c) The Regents of the University of California. All rights reserved. Permission is hereby granted, without written agreement and without license or royalty fees, to use, copy, modify, and distribute this software and its documentation for any purpose, provided that the above copyright notice and the following two paragraphs appear in all copies of this software." (followed by the UC liability and warranty disclaimer paragraphs)

  This is permissive and allows redistribution with the notice.

---

## 13. MQT QMAP / QCEC / QECC

| Package | PyPI latest (upload) | License | Repo HEAD (date) | Notes |
|---|---|---|---|---|
| `mqt.qmap` (dist `mqt-qmap`) | **3.10.0** (2026-09-12); Python `!=3.14.1,>=3.11`; 10 wheels | MIT | `916884b6e9beb9e3ebabb040bffc7371d69bbea5` (2026-09-25T20:25:41Z) | deps `mqt-core~=3.10.0`, qiskit[qasm3-import]>=2.1, rustworkx. Modules `sc` (superconducting mapping: `Method.exact` / `heuristic`, encodings naive/commander…), `clifford_synthesis`, `hybrid_mapper`, `na`, `ph` |
| `mqt.qcec` (dist `mqt-qcec`) | **3.10.0** (2026-09-08); Python >=3.11 | MIT | `a502cc2413f52200aa5ff0a63bc5783bf05bfd73` (2026-09-25T20:41:10Z) | deps `mqt-core~=3.10.0`, numpy; `verify`, `verify_compilation_flow`, parameterized checking |
| `mqt.qecc` | **2.0.0** (2026-07-13); Python >=3.10; pure wheel sha256 `4dd54b320aef9c6a4df34ca4ad2a13674c77fe9f812adf0cfdb845d1b8ff652d` | MIT | `accd7be9c93d6dc777ebfd9d36263250e5350746` (2026-09-25T19:19:17Z) | deps include **z3-solver>=4.15.3**, stim, qiskit, ldpc, bposd, pymatching, qecsim, sinter |

**MQT QECC 2.0.0 code library (inspected inside the downloaded wheel)**
- `mqt/qecc/codes/instances/`:
  - Named CSS codes, loadable with `CSSCode.from_code_name(...)`: `steane/` [[7,1,3]], `shor/` [[9,1,3]], `tetrahedral/` [[15,1,3]], `carbon/` [[12,2,4]], `golay/` [[23,1,7]]. Each is stored as `hx.npy` and `hz.npy`.
  - `lifted_product/`: `lp_l=16`, `lp_l=21`, `lp_l=30` (hx/hz as sparse `.npz`).
  - `misc/`: `8_3_3.txt`, `15_3_5.txt`, `30_6_5.txt`, in the text formats accepted by `CSSCode.from_file`.
- Constructions exported from `mqt.qecc.codes`: `RotatedSurfaceCode`, `ColorCode` / `HexagonalColorCode` / `SquareOctagonColorCode` (`LatticeType`), `construct_bb_code` (bivariate bicycle), `ConcatenatedCode` / `ConcatenatedCSSCode`, `construct_iceberg_code`, `construct_many_hypercube_code`, `construct_quantum_hamming_code`. A `hypergraph_product_code.py` module is also present.
- **State-preparation / encoding synthesis** (`mqt.qecc.circuit_synthesis`):
  - Prep: `heuristic_prep_circuit(code, optimize_depth=True, state="all_zero", rollout=0, …)`, `depth_optimal_prep_circuit(code, zero_state=True, min_depth=1, max_depth=10, …)`, `gate_optimal_prep_circuit(code, zero_state=True, min_gates=1, max_gates=10, …)`. The optimal variants use z3/SAT, return `FaultyStatePrepCircuit | None` and take timeouts.
  - Verification: `gate_optimal_verification_circuit`, `gate_optimal_verification_stabilizers`, `heuristic_verification_circuit`, `heuristic_verification_stabilizers`, `naive_verification_circuit`, and deterministic `DeterministicVerification` / `DeterministicVerificationHelper`.
  - Encoding: `gottesman_encoding_circuit`, `cnot_encoding_circuit`, `depth_optimal_encoding_circuit`, `depth_optimal_encoding_circuit_non_css`, `gate_optimal_encoding_circuit`, `synthesize_encoding_circuit`.
  - Others: `synthesize_cnot`, `synthesize_non_css`, `SynthesisConfig`, `cat_state_line`, `cat_state_balanced_tree`, `CatStatePreparationExperiment`, simulators `SteaneNDFTStatePrepSimulator` and `VerificationNDFTStatePrepSimulator`, `LutDecoder`.
- **Not shipped in the wheel but in the repo (`scripts/`):**
  - `scripts/encoding_circuits/best_circuits/` has best encoding circuits for codes 8_3_3, 15_1_3, 15_3_5, 15_7_3, 17_1_5, 19_1_5, 23_1_7, 30_6_5, 31_1_7, 31_21_3, 37_1_7, 72_12_6, 90_8_10, 108_8_10, 144_12_12, plus a `best_circuits_manifest.csv`.
  - `scripts/ft_stateprep/eval/circuits/{steane, shor, tetrahedral, carbon, hamming, rotated_surface_d3, rotated_surface_d5, cc_4_8_8, cc_4_8_8_d7, cc_6_6_6}/` has `.stim` files (`zero|plus|encoder`_`optgates|optdepth`).
  - `scripts/cat_states/circuits/` has 212 files.

  These are useful as "known-good/optimal" references for state-prep tasks.

---

## Cross-cutting notes for qbank design
- **Instances that come with a known optimum:**
  - QUEKO: optimal depth, SWAP-free, with an optimal mapping file for BNTF/BSS.
  - QUBIKOS: optimal SWAP count by construction. The generator is available but the repo has no license.
  - Maslov's 4b15g: 15-gate minimal.
  - MQT QECC: gate/depth-optimal prep via SAT, computed on demand.
  - SATLIB: SAT/UNSAT status only.
  - EPFL: best-known, not optimal, LUT-6.
- **Circuits rather than problems:** MQT Bench, QED-C, QUEKO/QUBIKOS inputs, RevLib .real.
- **Problems rather than circuits:** HamLib, SATLIB, EPFL functions, RevLib .pla, QCircuitBench descriptions.
- **Licensing red flags for redistribution:**
  - No license file: QUBIKOS, HamLib data, SATLIB, RevLib, Maslov's benchmark page.
  - QED-C: Apache-2.0 but the README says "All Rights Reserved".
  - Safe (OSI-style) licenses: QCircuitBench MIT, MQT* MIT, EPFL MIT, QUEKO/OLSQ2 BSD-3, ABC UC-permissive.
