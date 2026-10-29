# qbank Phase-0 reconnaissance: B (Boolean oracle compilation) / C (routing) / D (non-Clifford state preparation) / E (MCX, dynamic circuits)

Access date: **2026-09-25**. Every fact in this report comes from content actually fetched in this session; source types include curl, `git ls-remote`, shallow clones (placed in `scratchpad/recon_BCDE/`), the GitHub API, PyPI JSON, arXiv abs/HTML/PDF pages, and WebSearch (used only to discover ids; once an id was found it was always verified on the abs page). Anything that could not be verified is recorded as "unavailable" with the reason stated. No files were written under the project directory `/Users/hjh/PycharmProjects/Qevovle`.

**Limitations of this run**
- From about 17:40 onward, the `export.arxiv.org` query API returned HTTP 429. After that, arXiv ids were discovered via WebSearch and then verified on arxiv.org/abs pages.
- The unauthenticated GitHub REST API quota was exhausted (60/h, reset at about 18:33 local time). After that, SHAs and dates were obtained with `git ls-remote` or a shallow clone plus `git log -1`, and licenses were read from the LICENSE file in the repository.

## 0. Key points at a glance
- **QuantumEvo (2609.05327)**
  - It optimizes the BDD variable order; the metric is the NCT-level **SK2013 quantum cost (QCC)**, not T-count.
  - The repository is MIT and has only one commit, `4c6b0d4f` (2026-09-04).
  - The heuristic HGA-QE selected by the paper is kept as C source in `quantumevo/bdd_ordering/test/gpt_cuddFunc_hga.c`, so **the evaluation can be rerun without calling an LLM**, but cirkit/revkit (which depends on Boost etc.) must be compiled first.
  - The `.tex` tables used for the paper's baselines are not in the repository.
  - Main tables: Table 2 and Table 4 (all 148 functions: Best 70.9%, Strict 13.5%, Mean Best QCC 1923.83).
- **Pebbling toolchain**
  - SAT pebbling implementations with code: caterpillar (`gmeuli/caterpillar`, not updated since 2020), spooky-pebble-game (Quist-A), Reqomp.
  - No public code was found for new 2025–2026 oracle/pebbling work (Zhang–Li–Ying TCAD 2025, etc.).
  - `tweedledum` on PyPI is still at 1.1.1 (2021), with wheels up to cp310 only. I tried building from the sdist locally with py3.11 and it **failed** (pyproject validation error).
  - `revkit` on PyPI is stuck at 3.0a2.dev2 (2018).
- **Qiskit 2.5.2** (current latest on PyPI)
  - `PhaseOracle` still exists but has been **deprecated** since 2.2 and is scheduled for removal in 3.0; replacements are `PhaseOracleGate` / `BitFlipOracleGate`.
  - The backend has switched from tweedledum to **ESOP synthesis based on the full truth table**.
  - There are 12 MCX functions in total in `qiskit.synthesis` (names and ancilla requirements in §3).
- **Routing**
  - LightSABRE = arXiv 2409.08368.
  - The commuting two-qubit gate router is at `qiskit.transpiler.passes.routing.commuting_2q_gate_routing`.
  - pytket 2.18.4 (py>=3.10); mqt.qmap 3.10.0 (py>=3.11, interface is `compile_`).
  - OLSQ2 is not on PyPI; Q-Synth is on PyPI (`q-synth` 5.1).
  - QUBIKOS has **no data tables**. Gap numbers appear only in the abstract and in the body text of §IV-B: the abstract states LightSABRE 63x, ML-QLS 117x, QMAP 250x, tket 330x; the body additionally gives per-architecture values.
- **S-box**
  - I compiled 15 rows of AES data and 8 rows of lightweight S-box data, each number annotated with its table number.
  - Examples usable as unitary reference values: Zou+20 is 22 qubits, 52 Toffoli, 326 CNOT; Chen+25 in-place is 32 qubits, 125 Toffoli; Huang–Zhang–Lin 2025 in-place minimum width is 9 qubits, 833 Toffoli.
- **Category D**
  - Bärtschi–Eidenbenz 2019 CNOT upper bound is 5kn+O(n); the explicit formula given by Mukherjee is 5(nk-k(k+1)/2-n+1)+4(n-1).
  - The W state can be done with 2n-3 CNOTs.
  - qclib 0.1.15 contains 5 sparse methods, but some of them are already broken under Qiskit 2.5.2.
  - Qiskit has no dedicated Dicke/W construction.
- **Literature basis for Category E "no_room"**
  - Griffiths–Niu (quant-ph/9511007): the measured QFT needs no two-qubit gates.
  - Mosca–Ekert §5.2 and Dobšíček (quant-ph/0610214): iterative QPE uses only 1 ancilla.
  - Constant-depth GHZ/W/Dicke (dynamic circuits): Buhrman et al. 2307.14840 and Bäumer et al. 2308.13065.
- **HamLib**: arXiv 2306.13126; download URL https://portal.nersc.gov/cfs/m888/dcamps/hamlib/ , reachable today (HTTP 200).

---

## 1. QuantumEvo (arXiv:2609.05327 + github.com/syj5268/Quantumevo)

**Paper metadata** (source: https://arxiv.org/abs/2609.05327 , accessed 2026-09-25)
- Title: *LLM-Driven Algorithm Design for Quantum Circuit Synthesis based on Binary Decision Diagrams*
- Authors: Yoonju Sim, Federico Berto, Chuanbo Hua, Jinkyoo Park, Changhyun Kwon
- v1: 2026-09-04 16:25:01 UTC (612 KB); subjects: cs.AI, cs.AR
- The repository README says "TMLR 2026 Accepted" and links to OpenReview `https://openreview.net/forum?id=iL7YeQp7je`. I could not verify the OpenReview record: api2.openreview.net returned HTTP 403 `ChallengeRequiredError`, and the forum page returned 307. So TMLR acceptance status = **unavailable (I cannot verify it; only the repository README claims it)**.
- The source URL given in footnote 1 of the paper is `https://github.com/syj5268/Quantumevo`.

**Repository** (source: GitHub API + `git ls-remote` + shallow clone)
- HEAD: `4c6b0d4f0a7181a2bce90b2903fc81117d64a1f8`, committed 2026-09-05 00:24:32 +0900 (= 2026-09-04 15:24 UTC), author Yoonju Sim, commit message "Initial public release". This is the only commit in the whole repository.
- License: MIT (GitHub API spdx=MIT; LICENSE says "Copyright (c) 2026 Yoonju Sim and contributors"). Third-party code has its own licenses: `cirkit/` comes from msoeken/cirkit (MIT, © 2018 Mathias Soeken), the evolutionary framework from ai4co/reevo (MIT), plus range-v3 headers (Boost SL 1.0).
- Language: GitHub labels it C++. The repository consists of `cirkit/` (C++, RevKit + CUDD, 5335+2114+... files in total) and `quantumevo/` (Python). The shallow clone is about 171 MB.
- Python dependencies (`quantumevo/pyproject.toml`): `requires-python >=3.11`; the README uses `uv venv --python 3.12`. Dependencies include openai>=1.8.0, hydra-core>=1.3.2, omegaconf, numpy, scipy, wandb>=0.16.0, httpx, pydantic, etc. Among the extras: `bdd = [blifparser>=2.0.0, networkx>=2.6.0]`.
- C++ build (README): `cmake -S cirkit -B cirkit/build -Denable_cirkit-addon-reversible=ON -Denable_cirkit-addon-formal=OFF && cmake --build cirkit/build --target revkit`. Requires `build-essential g++ cmake libboost-all-dev libgmp3-dev libxml2-dev zlib1g-dev liblapack-dev libopenblas-dev libreadline-dev`, which are Debian/Ubuntu package names. **I did not try building locally**.
- LLM client configs are in `quantumevo/cfg/llm_client/{openai,gpt_oss,qwen,llama_api}.yaml` and need `OPENAI_API_KEY` or `GPT_OSS_API_KEY`.

**Inputs / benchmarks** (source: repository `quantumevo/README.md`, data directories, and paper §4.1)
- Inputs are Boolean functions in BLIF/PLA format. `revkit` uses `hdbs --pla <file>` for BDD synthesis (hierarchical/BDD-based synthesis), producing NCT reversible circuits.
- Final evaluation set "paper148" (paper text): "148 reversible functions ... 96 RevLib, 48 LGSynth91, and 4 ISCAS85/89 circuits". In the repository these are `dataset/use4eval/revlib_pla_blif/` (96 .blif files, e.g. 4gt10_22, rd53_68, sym9_71, urf4_89, apex5_104 ...) and `dataset/use4eval/lgsync91_iscas85_blif/` (52 = 48+4, including c432, c880, c17, s1196 ...).
- Search/validation sets: `use4train/all_dataset/` holds 150 instances augmented from RevLib (input negation / output complement / don't-care expansion); `train_pla_100.txt` lists 100 for training and `val_pla_50.txt` 50 for validation. Each instance comes with a `_BDD_all/` directory containing precomputed QC results for the five CUDD reorderings SIFT/SYMM_SIFT/GROUP_SIFT/ANNEALING/GENETIC.

**Cost metric**
- Paper §2.1 text: "Each gate in the NCT library with k∈{0,1,2} control bits is assigned a QCC of Cost(k)=2k²-2k+1 ... following Szyprowski and Kerntopf (2013). The total QCC of a circuit is the sum of its gate costs."
- The code implementation `cirkit/addons/cirkit-addon-reversible/src/reversible/utils/costs.cpp::sk2013_quantum_costs` is `2*nc + 2*ac*ac - 2*ac + 1`, where ac is the number of controls and nc the number of negative controls. That is, **the code adds an extra 2 for each negative-polarity control**, a term not present in the paper's formula. The revkit `ps -c` output line is `QC (SK2013): <n>`, and `eval.py::_parse_quantum_cost` parses this line.
- In the same output revkit also prints `Lines / Gates / T-count / Logic qubits / Transistor`. For example, the SIFT result for `4gt10_22_in1_m4` is: Lines 7, Gates 5, T-count 21, QC(SK2013) 17. But QuantumEvo **only optimizes and reports QCC(SK2013)**, not T-count.
- Evolutionary fitness (README): `gap % = (QC_evolved - QC_best_known)/QC_best_known × 100`, lower is better. best_known is the best value among the 5 CUDD reorderings.

**Can it be rerun offline (without calling an LLM)**: **partially**.
- The final heuristic HGA-QE selected by the paper is kept in the repository as a C source file: `quantumevo/bdd_ordering/test/gpt_cuddFunc_hga.c` (719 lines). The README says: `python compare_results.py --c-file gpt_cuddFunc_hga.c --dataset paper148 --best-of 3`. `compare_results.py` imports only the standard library; via `build_evolved.sh` it compiles the C file into CUDD's reordering slot no. 22 and then calls revkit.
- Paper Appendix E text: "The online phase ... requires no LLM calls".
- **Gap**: `compare_results.py::parse_tex_tables(SCRIPT_DIR)` needs `table6_new.tex / table7_new.tex / table6b_new.tex / table7b_new.tex` to load the paper's baseline numbers, and these files are **not in the repository**. The script handles missing files by printing `[WARN] ... not found – skipping`, so a rerun's comparison table will lack the paper's baseline columns. In addition, the BDD2Seq values are quoted directly from the original paper; its code is not in the repository. `baseline.py` can locally recompute CUDD baselines such as SIFT.
- The evolutionary process itself needs an LLM. Paper Table 15 (average per production run): LLM Calls 291.6 | Input Tokens 3.11M | Output Tokens 1.04M | Wall-clock 108.5 min | Hardware 1× NVIDIA RTX PRO 6000 (local gpt-oss-120b).

**Paper result tables** (source: https://arxiv.org/html/2609.05327v1 , accessed 2026-09-25; QCC = SK2013 quantum cost, lower is better; stochastic methods use 5 seeds)

*Table 2: Per-suite benchmark performance* (Best includes ties; Strict = unique best)

| Suite | Method | Best | Strict | Mean Best QCC | Mean Avg QCC | Mean Worst QCC |
|---|---|---|---|---|---|---|
| RevLib (96) | HGA-QE | 70 | 6 | 1416.04 | 1434.31 | 1450.76 |
| | SA | 68 | 5 | 1416.25 | 1437.27 | 1463.44 |
| | BDD2Seq | 65 | 13 | 1456.03 | – | – |
| | GA | 58 | 1 | 1445.28 | 1457.55 | 1468.35 |
| | SIFT | 42 | 0 | 1767.24 | – | – |
| | SYMM SIFT | 41 | 0 | 1757.90 | – | – |
| | GROUP SIFT | 41 | 1 | 1688.56 | – | – |
| LGSynth91 (48) | HGA-QE | 31 | 13 | 2088.54 | 2218.05 | 2344.25 |
| | SA | 22 | 3 | 2153.58 | 2267.06 | 2447.79 |
| | BDD2Seq | 22 | 5 | 2466.00 | – | – |
| | GA | 23 | 6 | 125739.94 | 202778.95 | 293303.17 |
| | SIFT | 16 | 1 | 4687.90 | – | – |
| | SYMM SIFT | 16 | 0 | 4682.71 | – | – |
| | GROUP SIFT | 15 | 0 | 5762.81 | – | – |
| ISCAS85/89 (4) | HGA-QE | 4 | 1 | 12134.25 | 12211.23 | 12288.75 |
| | SA | 3 | 0 | 12286.00 | 12403.25 | 12589.00 |
| | BDD2Seq | 1 | 0 | 13549.50 | – | – |
| | GA | 3 | 0 | 12296.00 | 12518.60 | 12681.25 |
| | SIFT | 0 | 0 | 19230.00 | – | – |
| | SYMM SIFT | 0 | 0 | 19230.00 | – | – |
| | GROUP SIFT | 1 | 0 | 23486.00 | – | – |

*Table 4 first row (full QuantumEvo setting, all 148 functions, 5 seeds)*: Best/Total 70.9% | Strictly Best/Total 13.5% | Mean Best QCC 1923.83 | Mean Avg 1979.76 | Mean Worst 2033.46. Ablation results: Non-LLM 66.9 / 5.4 / 2075.15; GA initialization only 63.5 / 3.4 / 2061.84; SA initialization only 66.2 / 0.7 / 1949.11; Sifting initialization only 55.4 / 4.1 / 2203.34; BDD size as fitness 61.5 / 5.4 / 1944.65.

*Table 7 (LLM choice)*: gpt-oss-120b 70.9 / 13.5 / 1923.83 / 1979.76 / 2033.46; gpt-5.4-mini 66.9 / 6.1 / 2080.71 / 2147.33 / 2211.11.

*Table 1 (search set, best-of-3, mean QCC gap relative to best-known)*: GA with sifting 2.096%; GA with MiniSift 0.532% (W/T/L 34/53/13); GA with MiniSift + local refinement 0.527% (34/53/13).

*Table 3 (functions where HGA-QE is strictly best, Best QCC)* excerpt: apex5_104 9184 (GA 9551, SA 9397, BDD2Seq(B*) 9852, SIFT 10358); c432 10494 (GA 11141, SA 11101, BDD2Seq(B*) 12255); rot_orig 23926 (GA 5928978, SA 24124, BDD2Seq(B*) 38453, SIFT 78639); urf4_89 28406 (GA 28538, SA 28489, BDD2Seq(B*) 28488); misex1_178 279; cordic_138 304; dalu_orig 5230; pair_orig 20236; seq_201 9080; x4_orig 2437.

*Tables 16–21* are the full per-function results (RevLib in 2 parts, plus ISCAS/LGSynth91). I fetched the whole tables into `scratchpad/recon_BCDE/qe_tables16_21.txt` (314 lines). Small-function excerpt (HGA-QE Best QCC = GA = SA): 4gt10_22 17; 4gt11_23 5; 4gt13_25 10; 4mod5_8 24; rd53_68 98; sym9_71 206.

**Implications for qbank Category B**: QuantumEvo's "QCC" is an NCT-level quantum cost counted per SK2013, **not** a T-count / CNOT count. Its circuits come from BDD synthesis (each BDD node corresponds to one line; the ancilla count is determined by the BDD size), with no qubit budget considered. If qbank cites its numbers, they must be labelled "SK2013 QCC, BDD-based hdbs, including ancilla lines" and cannot be compared directly with T-count-type baselines.

---

## 2. Oracle compilation under a qubit budget: pebbling strategies, code and toolchain

### 2.1 Papers (all verified on arxiv.org/abs pages, accessed 2026-09-25)
| Paper | arXiv | Venue / notes (verbatim) | Code |
|---|---|---|---|
| Meuli, Soeken, Roetteler, Bjørner, De Micheli, *Reversible Pebbling Game for Quantum Memory Management* | 1904.02121 (v1 2019-04-03) | comments: "In Proc. Design Automation and Test in Europe (DATE 2019)" | Implemented in caterpillar: `include/caterpillar/synthesis/strategies/pebbling_mapping_strategy.hpp` (uses `z3_pebble_solver`); README text "pebbling mapping strategy, that is a SAT-based method enabling constraints on the number of qubits", parameter `ps.pebble_limit` |
| Meuli, Soeken, Campbell, Roetteler, De Micheli, *The Role of Multiplicative Complexity in Compiling Low T-count Oracle Circuits* | 1908.01609 | "To appear in: Proc. ICCAD 2019" | caterpillar (XAG strategy) |
| Meuli, Soeken, Roetteler, De Micheli, *ROS: Resource-constrained Oracle Synthesis for Quantum Computers* | 2005.00211 | jref: EPTCS 318, 2020, pp. 119-130 (QPL 2019); DOI 10.4204/EPTCS.318.8 | — |
| Parent, Roetteler, Svore, *Reversible circuit compilation with space constraints* | 1510.00377 | 32 pages (REVS) | Unavailable (no repository found) |
| Knill, *An analysis of Bennett's pebble game* | math/9508218 | 1995 | — |
| Li, Tromp, Vitányi, *Reversible Simulation of Irreversible Computation by Pebble Games* | quant-ph/9703009 | Physica D120 (1998) 168-176 | — |
| Kornerup, Sadun, Soloveichik, *Tight Bounds on the Spooky Pebble Game: Recycling Qubits with Measurements* | 2110.08973 | Quantum 9, 1636 (2025); DOI 10.22331/q-2025-02-18-1636 | Unavailable |
| Quist, Laarman, *Trade-offs between classical and quantum space using spooky pebbling* | 2401.10579 (v7) | LMCS 21(4) (2025); DOI 10.46298/lmcs-21(4:29)2025 | Code of the same group's RC 2023 paper *Optimizing Quantum Space using Spooky Pebble Games*: `github.com/Quist-A/spooky-pebble-game` (MIT, Python + z3 submodule; HEAD `e70f52f33226ccb27a296815a3c6619fd97fb72f`, last commit 2023-08-21). The RC 2023 DOI 10.1007/978-3-031-38100-3_10 appeared only in WebSearch results; I did not fetch the Springer page |
| Kahanamoku-Meyer, Ragavan, Van Kirk, *Parallel Spooky Pebbling Makes Regev Factoring More Practical* | 2510.08432 (v3) | DOI 10.1007/978-3-032-25291-3_14 | `github.com/GregDMeyer/parallel-spooky-pebbling` (MIT, Julia; HEAD `a5803e9663219f213452f9d2bb44241cebf7de37`, 2025-10-09) |
| Paradis, Bichsel, Vechev, *Reqomp: Space-constrained Uncomputation for Quantum Circuits* | 2212.10395 | Quantum 8, 1258 (2024) | `github.com/eth-sri/Reqomp` (MIT, Python, integrated into Qiskit; README recommends python=3.10; HEAD `fd2256e2643d6e0d3b3f07db225c979faebb6c69`, 2022-12-22 "init commit") |
| Unqomp (PLDI 2021, ETH SRI) | Unavailable (arXiv API returned no results for ti:Unqomp) | — | `github.com/eth-sri/Unqomp` (MIT; HEAD `9d7e885af1eb...`, 2021-04-01) |
| Ding et al., *SQUARE: Strategic Quantum Ancilla Reuse ...* | 2004.08539 | DOI 10.1109/ISCA45697.2020.00054 | Not verified |
| Zhang, Li, Ying, *A divide-and-conquer pebbling strategy for oracle synthesis in quantum computing* | Unavailable (no results from arXiv or GitHub searches) | Citation in reference [21] of arXiv:2607.11401: "IEEE TCAD, vol. 44, no. 12, pp. 4601–4614, Dec. 2025". arXiv:2605.21380 paraphrases its effect as "reduces the total qubit count by up to 90% compared with the commonly used eager clean-up strategy, at the cost of three to four times more quantum operations" (second-hand paraphrase, not numbers from the original) | Unavailable |
| Li et al., *Modeling and Resource Optimization for Quantum Oracles* (FORM / ShallowGrow) | 2605.21380 (v2 2026-08-30) | comments mention that leaf synthesis uses "pebbling-based leaf syntheses (LHRS, Zhang et al.)" | No code link in the HTML |
| Hong, Zhang, Dai, Li, Ying, Ying, *Oracle Synthesis Based on X-Map Decision Diagrams* | 2609.20854 (v1 2026-08-26) | — | The only non-arXiv GitHub link in the HTML is `github.com/hriener/easy` (an ESOP tool, a cited tool); no repository of the authors' own |
| Liu, Zhou, Meng, *Quantum Uncomputation of Clean and Dirty Ancilla Qubits* | 2608.09578 | 2026-08-10 | Not verified |

### 2.2 Toolchain status (GitHub API / `git ls-remote` / PyPI JSON, accessed 2026-09-25)
| Project | Repository | License | HEAD (last commit) | PyPI | Installable / buildable today? |
|---|---|---|---|---|---|
| caterpillar | github.com/gmeuli/caterpillar (`lsils/caterpillar` returns 404) | MIT | `4c6f766cd0ffc62d37ab45edfe80c9f1eae44764`, 2020-11-05 "More strategies for XAGs. (#20)" | None. `caterpillar` on PyPI is an unrelated package (Kapiche, AGPLv3+, 0.15.10, 2019) | C++17 header-only library, depends on mockturtle/tweedledum/z3 (pebbling); **build not attempted** |
| mockturtle | github.com/lsils/mockturtle | MIT | `d9e02495f537bac460f7994557184054a3eebd75`, 2026-09-23 "Update fmt version to 12.1.0 (#710)" (still active) | None. `mockturtle` 0.1.6 on PyPI is an unrelated package (Turtle Services) | README: "a C++-17 logic network library" |
| tweedledum | github.com/boschmitt/tweedledum | MIT | `3d765c357ea6b9300be8eb77ee3f9d7e4102ed8c`, 2026-07-16 "Update changelog". There is a 2026-05-17 commit "Update project to version 1.2.0, drop pybind11 support, and integrate nanobind", but **1.2.0 has no GitHub release and was not published to PyPI** (latest release v1.1.1, 2021-09-08). CHANGELOG [Unreleased]: pybind11 replaced by nanobind (>=2.12), minimum Python 3.9 | `tweedledum` 1.1.1 (2021-09-08), requires_python >=3.6, wheels only for cp36–cp310 | Tested `pip download tweedledum==1.1.1 --only-binary=:all:`: py3.10 succeeds (`tweedledum-1.1.1-cp310-cp310-manylinux_2_12_x86_64.manylinux2010_x86_64.whl`); py3.11 / py3.12 report "No matching distribution". That is, **there is no wheel for Python >=3.11**; it can only be built from the sdist (tweedledum-1.1.1.tar.gz). I tested the sdist build locally: macOS, Python 3.11.4, Apple clang 16, cmake 3.27.7, command `pip wheel tweedledum==1.1.1 --no-deps --no-binary=tweedledum`. Result: **failed**, stopping at the "Getting requirements to build wheel" step with the error `ValueError: invalid pyproject.toml config: project. configuration error: project must contain ['version'] properties` (via scikit-build `setuptools_wrap.setup`; the isolated build environment had the current setuptools). I did not test whether pinning an old setuptools works around this. I also did not test 1.2.0 (the nanobind version) on GitHub master |
| RevKit (Python) | github.com/msoeken/revkit (README "RevKit 3.1 ... based on tweedledum and caterpillar") | MIT | `a59fa132f73a2483a00b11c23f5f1c599a34f074`, 2019-04-29 "CI." | `revkit` latest 3.0a2.dev2 (2018-09-17, sdist only); earlier 3.0a1/3.0a2.dev1 have only cp27/34/36/37 macOS wheels | Effectively abandoned; no 3.1 on PyPI |
| CirKit (incl. RevKit C++ command line) | github.com/msoeken/cirkit (default branch cirkit3) | MIT | `4531533394725864a304e710d82087ff74fbe801`, 2020-02-23 "CI." | None | QuantumEvo ships its own modified copy of cirkit (see §1) |

### 2.3 Summary
- Implementations with code that can do SAT pebbling under a qubit budget: caterpillar's `pebbling_mapping_strategy` (z3), not updated since 2020; the spooky pebbling SAT solver (Quist-A, z3); Reqomp (Qiskit-integrated, uncomputation under space constraints).
- For the newer 2025–2026 oracle/pebbling work (Zhang–Li–Ying TCAD 2025; arXiv 2605.21380, 2607.11401, 2609.20854), **no public code was found**.

---

## 3. PhaseOracle / BitFlipOracle and MCX synthesis in Qiskit (latest version 2.5.2)

**Version**: latest PyPI `qiskit` is **2.5.2** (uploaded 2026-08-13T19:08:04), requires_python >=3.10, classifiers 3.10–3.14, Apache-2.0, wheel is cp310-abi3. git tag `2.5.2` → `c1c01ada399af13e495c27b9b22b4ff942bbad7e` (2026-08-13, "Prepare 2.5.2 (#16763)"); `git ls-remote` shows no newer 2.6 tag. All source-code conclusions below come from a shallow clone of this tag.

**PhaseOracle / PhaseOracleGate / BitFlipOracleGate**
- Module paths: `qiskit/circuit/library/phase_oracle.py` (`class PhaseOracle(QuantumCircuit)`, `class PhaseOracleGate(Gate)`) and `qiskit/circuit/library/bit_flip_oracle.py` (`class BitFlipOracleGate(Gate)`). All three are exported from `qiskit.circuit.library`.
- `PhaseOracle.__init__` carries `@deprecate_func(since="2.2", additional_msg="Use the class qiskit.circuit.library.PhaseOracleGate instead.", removal_timeline="in Qiskit 3.0")`. Conclusion: **PhaseOracle still exists in 2.5.2, but has been deprecated since 2.2 and is scheduled for removal in 3.0**.
- **The backend is no longer tweedledum**. Synthesis is now done by `qiskit/synthesis/boolean/boolean_expression.py::BooleanExpression.synth()`; the source comment says "generating the esop currently requires generating the full truth table", and the pipeline is `EsopGenerator(self.truth_table).esop` → `synth_phase_oracle_from_esop` / `synth_bit_oracle_from_esop` (`qiskit/synthesis/boolean/boolean_expression_synth.py`), implemented with multi-controlled Z / X. Docstring text: "From 16 variables on, possible performance issues should be expected when using the default synthesizer."
- Release note `releasenotes/notes/2.0/boolean_expression_update-39c19edbbe71ba0d.yaml` text: "The PhaseOracle no longer relies on the tweedledum library but might not be synthesized as effectively as before. BitFlipOracleGate was added ... A PhaseOracleGate was added and will replace PhaseOracle in Qiskit 3.0." Another note, `2.0/remove_classical_function-...yaml`, text: "The classical_function was removed. This module was dependent on the tweedledum library which is no longer compatible with newer versions of Python."
- `qiskit/utils/optionals.py` still keeps `HAS_TWEEDLEDUM`, with the comment "In the past Qiskit's PhaseOracle used this but it is no longer used by Qiskit."
- Input formats: Python-style Boolean expressions (`& | ~ ^`), or DIMACS CNF (`from_dimacs_file`).

**MCX synthesis functions (`qiskit.synthesis`; source `qiskit/synthesis/multi_controlled/mcx_synthesis.py`)**
The names listed in the official documentation https://quantum.cloud.ibm.com/docs/en/api/qiskit/synthesis (accessed 2026-09-25, page labelled 2.5.0) match the source `__all__` exactly. The numbers in the table below are quoted from each function's docstring; k = number of control qubits:

| Function | ancilla | total qubits | gate count (docstring verbatim) | Reference |
|---|---|---|---|---|
| `synth_mcx_n_dirty_i15(num_ctrl_qubits, relative_phase=False, action_only=False)` | k-2 **dirty** (k>=4; no ancilla for k<=3) | 2k-1 | "at most 8*k - 6 CX gates" | Iten et al., arXiv:1501.06911 |
| `synth_mcx_n_clean_m15(num_ctrl_qubits)` | k-2 **clean** (k>=3) | 2k-1 | "at most 6*k - 6 CX gates" | Maslov, arXiv:1508.03273 |
| `synth_mcx_1_clean_b95(num_ctrl_qubits)` | 1 **clean** (k>=3) | k+2 | "at most 16*k - 24 CX gates" | Barenco et al. quant-ph/9503016; Iten et al. |
| `synth_mcx_1_clean_kg24(num_ctrl_qubits)` | 1 **clean** | — | "2k-3 Toffoli gates or 6k-6 CX gates and depth O(k)" (Sec. 5.1) | Khattar & Gidney, arXiv:2407.17966 |
| `synth_mcx_1_dirty_kg24(num_ctrl_qubits)` | 1 **dirty** | — | "4k-8 Toffoli gates or 12k-18 CX gates and depth O(k)" (Sec. 5.3) | same |
| `synth_mcx_2_clean_kg24(num_ctrl_qubits)` | 2 **clean** | — | "2k-3 Toffoli gates or 6k-6 CX gates and depth O(log(k))" (Sec. 5.2) | same |
| `synth_mcx_2_dirty_kg24(num_ctrl_qubits)` | 2 **dirty** | — | "4k-8 Toffoli gates or 12k-18 CX gates and depth O(log(k))" (Sec. 5.4) | same |
| `synth_mcx_noaux_v24(num_ctrl_qubits)` | 0 | k+1 | "The number of CX-gates is quadratic in k" (via MCPhase) | Vale et al., arXiv:2302.06377 |
| `synth_mcx_noaux_hp24(num_ctrl_qubits)` | 0 | k+1 | “The number of CX-gates is linear in k” | Huang & Palsberg, PLDI 2024, doi 10.1145/3656436 |
| `synth_mcx_gray_code(num_ctrl_qubits)` | 0 | k+1 | "exponentially many CX gates ... only for small values of k" | — |
| `synth_c3x()` / `synth_c4x()` | 0 | 4 / 5 | “Efficient synthesis of 3-/4-controlled X-gate” | — |

There are also two internal functions, `synth_mcx_1_kg24(num_ctrl_qubits, clean)` and `synth_mcx_2_kg24(num_ctrl_qubits, clean)`, which are not in `__all__`. The related `synth_mcmt_vchain` and `synth_mcmt_xgate` are also in `qiskit.synthesis`.

**HighLevelSynthesis plugins** (`pyproject.toml` entry-points `qiskit.synthesis`): `mcx.n_dirty_i15, mcx.n_clean_m15, mcx.2_clean_kg24, mcx.2_dirty_kg24, mcx.1_clean_kg24, mcx.1_dirty_kg24, mcx.1_clean_b95, mcx.gray_code, mcx.noaux_v24, mcx.noaux_hp24, mcx.default`.
Behaviour of `MCXSynthesisDefault` (`qiskit/transpiler/passes/synthesis/hls_plugins.py`):
- Default `optimization_metric=COUNT_2Q`; the order tried is 2CleanKG24 → 1CleanKG24 → NCleanM15 → NDirtyI15 → 2DirtyKG24 → 1DirtyKG24 → 1CleanB95 → (NoAuxV24 if k<=5 else NoAuxHP24).
- With `COUNT_T` the order is 2CleanKG24 → 1CleanKG24 → 2DirtyKG24 → 1DirtyKG24 → 1CleanB95 → NCleanM15 → NDirtyI15 → (as above).
- Plugin options: `num_clean_ancillas`, `num_dirty_ancillas`.

---

---

## 4. Published quantum-circuit resource counts for block-cipher S-boxes

Access date for every source below: **2026-09-25**. I read every number from a PDF I downloaded (converted with `pdftotext -layout`) or from arXiv HTML. The local copies are in `scratchpad/recon_BCDE/sbox/`. "Table N" means the paper's own table number. Where a number comes from running text or an algorithm listing, the section or algorithm is given instead.

Abbreviations: Tof = Toffoli (CCX) count; T-d = T-depth; Tof-d = Toffoli-depth; 1qC = single-qubit Clifford count; #M = measurements (from measurement-based AND uncomputation); FD = full depth.
- **Out-of-place**: |x⟩|0⟩ → |x⟩|S(x)⟩.
- **In-place**: |x⟩ → |S(x)⟩.
- **C\***: |x⟩|b⟩ → |x⟩|b⊕S(x)⟩.

### 4.1 AES S-box (8-bit)

| # | Source (id) | Where | Circuit semantics | Raw values as printed |
|---|---|---|---|---|
| A1 | Grassl, Langenberg, Roetteler, Steinwandt, "Applying Grover's algorithm to AES: quantum resource estimates", **arXiv:1512.04965** (PQCrypto 2016) | Sec. 3.2.1 text (p. 6), not a table | Itoh–Tsujii inversion using 8 GF(2^8) multiplications (Maslov et al. multiplier: 64 Tof + 21 CNOT each). Output is \|x⟩\|S(x)⟩ plus 24 reinitialised qubits, 40 qubits total | "one 8-bit S-box requires **3584 T-gates and 4569 Clifford gates**", "fits into **40 qubits** total" |
| A2 | same paper | Sec. 3.2.1 "alternative implementation minimizing qubits" | In-place permutation with 1 ancilla (**9 qubits**). The inversion is an odd permutation, so an ancilla is required | "no more than **9695 T-gates and 12631 Clifford gates** … using only 9 instead of 40 qubits". Caveat: 2025/212 (row A11) prints this as "≤ 9295" T in its Table 5 but "9695" in its own text. The original paper says 9695 |
| A3 | Langenberg, Pham, Steinwandt, "Reducing the Cost of Implementing AES as a Quantum Circuit", **IACR ePrint 2019/854** (IEEE TQE 1, 2020, per refs of 2023/1417) | Abstract / Sec. 3.2 text | \|x⟩\|0^24⟩ → \|x⟩\|S(x)⟩\|0^16⟩ (a = 24 ancillas incl. 8 output), Boyar–Peralta based, **uncomputation included** | **32 qubits, 55 Tof, 314 CNOT, 4 NOT, Tof-d 40, NCT depth 298**. A naive BP conversion gives 126 qubits, 32 Tof, 166 CNOT, 4 NOT without cleanup (Sec. 3.2). ProjectQ source is printed in Appendix A |
| A4 | Jaques, Naehrig, Roetteler, Virdia, "Implementing Grover oracles for quantum key search on AES and LowMC", **ePrint 2019/1146** (latest rev. 2023-06-07; EUROCRYPT 2020) | **Table 1** | Out-of-place, Q# resource estimator, T-depth-1 AND gates (Selinger/Jones) with measurement-based uncompute | [GLRS16] S-box: #CNOT 8683, #1qC 1028, #T 3584, #M 0, T-d 512, FD 3668, width 44. [BP10] (LPS19 port): 793 / 275 / 164 / 41 / 35 / 589 / 81. **[BP12] S-box: 649 / 225 / 136 / 34 / 6 / 125 / 145** |
| A4′ | same paper, **arXiv:1910.01700v1** (2019-10-03) | Table 1 (v1) | same | These values differ from the ePrint final version: [GLRS16] T-d 217, FD 1692. [BP12]: 654 CNOT, 184 1qC, 136 T, 34 M, T-d 6, FD 101, width 137. **Use the ePrint final version.** The repo README warns that a Q# ResourcesEstimator bug (qsharp-runtime issue #192) could give depth/width lower bounds that cannot both be reached at once |
| A5 | Zou, Wei, Sun, Liu, Wu, "Quantum Circuit Implementations of AES with Fewer Qubits", ASIACRYPT 2020 (PDF from iacr.org/archive/asiacrypt2020/12491370/12491370.pdf; **no ePrint id found**) | Sec. 4.2, Algorithm 4 | Out-of-place, output qubits zero, 6 ancillas (8 in + 8 out + 6 = 22 qubits), cleanup included | **6 ancilla, 52 Tof, 326 CNOT, 4 NOT, Tof-d 41**. Trade-off for i = 1..2: 6+i ancilla, 52−2(i+1) Tof, 326+2(i+1) CNOT, Tof-d 41−2i |
| A6 | same | Sec. 4.2, Algorithm 5 | C\* (output register not zero) | **7 ancilla, 68 Tof, 352 CNOT, 4 NOT, Tof-d 60** |
| A7 | same | Sec. 4.3, Algorithm 7 | **S-box⁻¹** | **7 ancilla, 69 Tof, 335 CNOT, 24 NOT, "depth 62"** (trade-off: 7+i ancilla, 69−2i Tof, i ≤ 3, Tof-d 60) |
| A8 | Huang & Sun, "Synthesizing Quantum Circuits of AES with Lower T-depth and Less Qubits", **ePrint 2022/620** (ASIACRYPT 2022) | **Table 3** | NCT; C⁰ = out-of-place, C\* = XOR into non-zero target | [ZWS+20] C⁰: 6 anc / Tof-d 41 / 52 Tof / 326 CNOT / 4 X, and 7 / 60 / 68 / 352 / 4. **This paper C\*: 6 anc / Tof-d 41 / 52 Tof / 336 CNOT / 4 X** |
| A9 | same | **Table 4** | Clifford+T with AND gates, out-of-place incl. uncompute. Widths estimated by hand (Remark 3) | JNRV20: 664 CNOT / 205 1qC / 136 T / 34 M / T-d 6 / FD 117 / width 136. **T-depth-4: 718 / 208 / 136 / 34 / 4 / 109 / 136. T-depth-3: 1395 / 467 / 312 / 78 / 3 / 113 / 218** |
| A10 | Liu, Preneel, Zhao, Wang, "Improved Quantum Circuits for AES: Reducing the Depth and the Number of Qubits", **ePrint 2023/1417** (ASIACRYPT 2023) | **Table 3** (Toffoli-based comparison; width = ancilla + 16 I/O) | Out-of-place NCT | [LPS19] 16+16, 55 Tof, 314 CNOT, 4 1qC, Tof-d 40. [ZWS+20] 6+16/52/326/4/41, 7+16/48/330/4/39, 8+16/46/332/4/37. [Lin et al. 2023/146] 5+16/57/193/4/24, 6+16/57/195/4/22. [JNRV] 120+16/34/186/4/6. [HS22] 120+16/34/214/4/4. **This paper 74+16 / 34 Tof / 168 CNOT / 4 / Tof-d 4** |
| A10′ | same | **Table 4** (AND-gate / Q# comparison) | Clifford+T with AND gates | [19]=JNRV: width 136, 664 CNOT, 205 1qC, 136 T, 34 M, T-d 6, FD 117. [16]=HS22: 136 / 718 / 208 / 136 / 34 / 4 / 109. **This paper: 99 / 624 / 204 / 136 / 34 / 4 / 101** |
| A11 | Huang, Zhang, Lin, "Constructing Quantum Implementations with the Minimal T-depth or Minimal Width and Their Applications", **ePrint 2025/212** (EUROCRYPT 2025) | **Table 1** (out-of-place NCT incl. uncompute, BP AND-depth-4 circuit) | NCT | [39]=LPZW23 C\*: 4 NOT / 312 CNOT / 68 Tof / Tof-d 8 / FD 78 / width 90. C\*: 4 / 368 / 68 / 8 / 105 / 76. **This work C⁰/C\*: 4 / 227/240 / 60 / 8 / 60 / 66** |
| A11′ | same | **Table 2** (out-of-place Clifford+T incl. uncompute) | Clifford+T | [39] C⁰/C\*: 618/608 CNOT, 220 1qC, 136 T, 34 M, T-d 4, FD 109, width 99/107. [54]=Zhang–Shi–Wu–Sui IEEE TC 2024: 527/554, 206/238, 136, 26/34, 4, 95/90, 84/92. **This work: 525/539, 206/238, 136, 26/34, 4, 93/92, 84/92** |
| A11″ | same | **Table 3** (T-depth 3) | Clifford+T | [28]=HS22: 1396/1398 CNOT, 494 1qC, 312 T, 78 M, T-d 3, FD 119, width 218/226. [54]: 1110, 448, 264, 66, 3, 92, 129. **This work: 827/856, 266/298, 168, 34/42, 3, 85/87, 89/97** |
| A12 | same | **Table 4** / **Table 5** | **In-place, minimal width 9 qubits** (the S-box is an odd permutation) | NCT: **233 NOT, 885 CNOT, 833 Tof, width 9, Tof-d 793, FD 1594**. Clifford+T: 7465 Clifford (6028 CNOT + 1437 1qC), **3783 T**, width 9, T-d 1501, FD 7180. T-par variant: 13008 Clifford, **3447 T**, T-d 1274, FD 9954 |
| A13 | same | **Table 6** | Pair of S-boxes in 16 qubits (each uses the other as a dirty ancilla) | NCT: 502 NOT, 1770 CNOT, 2140 Tof, width 16, Tof-d 1714, FD 2990. Clifford+T: 3628 1qC, 14786 CNOT, 9008 T, T-d 2949, FD 15253. T-par: 5066 / 23976 / 8360 / 2774 / 18883 |
| A14 | Chen, Cai, Gao, Lin, "Quantum circuit for implementing AES S-box with low costs", **arXiv:2503.06097v2** (= ePrint 2025/454) | **Table VI** (c₁ = \|a⟩\|0⟩\|0⟩→\|a⟩\|S(a)⟩\|0⟩) | Out-of-place NCT | c₁¹: **36 qubits, 67 Tof, 300 CNOT, 4 NOT, Tof-d 15**. c₁²: 41 / 100 / 377 / 4 / 16. Clifford+T in Table VII: c₁¹ 44 qubits, 168 T, 990 Clifford, T-d 10 |
| A15 | same | **Table X** (c₃ = \|a⟩\|0⟩→\|S(a)⟩\|0⟩) | **In-place** NCT | c₃¹: **32 qubits, 125 Tof, 424 CNOT, 4 NOT, Tof-d 47**. c₃²: 36/111/410/4/33. c₃³: 40/130/473/4/20. c₃⁴: 60/130/489/4/16 |

**Classical multiplicative complexity (AND count) of the AES S-box, as read:** Zou et al. (ASIACRYPT 2020), **Table 2**, lists ref [5] = Boyar & Peralta, SEA 2010, as **83 XOR/XNOR + 32 AND** for the S-box. Its ref [1] (CMT) is 81 XOR + 32 AND, and "Sect. 3.3" gives 82 XOR + 32 AND + 4 NOT for S-box⁻¹. LPS19 (Sec. 3.2) says: "no more than 32 Toffoli gates are needed to evaluate SubByte" before cleanup.

### 4.2 Lightweight 4-bit (and 3-/8-bit) S-boxes

| # | Source (id) | Where | Semantics | Raw values |
|---|---|---|---|---|
| L1 | Jang, Song, Kim, Kwon, Kim, Seo, "Efficient Implementation of PRESENT and GIFT on Quantum Computers", *Applied Sciences* 11(11):4776, 2021, DOI 10.3390/app11114776 (PDF fetched from mdpi-res.com; mdpi.com HTML returned 403) | **Algorithm 2** (PRESENT, LIGHTER-R generated) | **In-place, 4 qubits, no ancilla.** Output qubits permuted by relabeling; SWAPs not counted | I counted the listing's lines: **4 Tof, 5 CNOT, 2 X** |
| L2 | same | **Algorithm 6** (GIFT, hardware-oriented S-box) | In-place, 4 qubits, no ancilla | I counted the listing's lines: **4 Tof, 2 CNOT, 7 X** (lines 7–8 are "reverse" X gates) |
| L3 | Bijwe, Chauhan, Sanadhya, "Quantum Search for Lightweight Block Ciphers: GIFT, SKINNY, SATURNIN", **ePrint 2020/1485** | Sec. 3 text + **Table 2** | GIFT S-box, in-place. Q# with Selinger's Toffoli (7 T, 16 CNOT, 2 1qC, 4 ancillas, T-depth 1) | Text: "**4 Toffoli gates, 2 CNOT gates, and 6 Pauli-X gates**". Table 2 "In-place S-box": 66 CNOT, 14 1qC, 28 T, 0 M, T-d 4, FD 32, initial width 4, ancillas 4 |
| L4 | same | Sec. 4 text + **Table 5** | SKINNY-64, 4-bit S-box, in-place | Text: "**4 Toffoli gates and 10 Pauli-X gates**". Table 5: 64 CNOT, 18 1qC, 28 T, T-d 4, FD 32, width 4, 4 ancillas |
| L5 | same | Sec. 4 text + **Table 6** | SKINNY-128, 8-bit S-box, in-place | Text: "**8 Toffoli gates and 22 Pauli-X gates**". Table 6: 128 CNOT, 38 1qC, 56 T, T-d 4, FD 33, width 8, 4 ancillas |
| L6 | Rahman & Paul, "Grover on Present: Quantum Resource Estimation", **ePrint 2021/1655** | Sec. text + **Table 3** | PRESENT S-box made by **RevKit `PermutationOracle`** (automatic synthesis) inside ProjectQ, 4 qubits | Text: "**19 toffoli gates, 5 CNOT gates and 2 NOT gates**". Table 3 by Toffoli decomposition: T-d-4 version: 119 CNOT / 36 1qC / 133 T / 4 M / T-d 63 / FD 190 / width 8. T-d-3: 138 / 59 / 133 / 4 / 34 / 177 / 8. T-d-1: 309 / 36 / 133 / 4 / 19 / 139 / 84. Compared with L1's 4 Tof, the automatic synthesis is far from optimal |
| L7 | Chun, Baksi, Chattopadhyay, "DORCIS: Depth Optimized Quantum Implementation of Substitution Boxes", **ePrint 2023/286** | **Table II(b)** (4-bit), **II(a)** (3-bit) | Depth and T-depth only, after decomposition with T-depth-1 Toffoli (ancilla per T gate; Fig. 2). Compares LIGHTER-R vs DORCIS | (LIGHTER-R depth / T-d → DORCIS depth / T-d) **GIFT 32/4 → 31/4. PRESENT 33/4 → 32/4. SKINNY 32/4 → 30/4.** PICCOLO 32/4 → 30/4. RECTANGLE 33/4 → 31/4. ELEPHANT 35/4 → 33/4. PYJAMASK-4 32/4 → 31/4. DEFAULT-CORE 45/6 → 31/4. PRINCE 44/5 → 42/5. NOEKEON 32/4 → 30/4. TWINE 56/7 → 54/7. QARMA 42/5 → 41/5. JH S0 43/5 → 41/5. 3-bit (DORCIS only): LowMC 23/3, PYJAMASK-3 23/3, SEA 23/3 |
| L8 | Jaques et al., ePrint 2019/1146 | **Table 5** | **LowMC 3-bit S-box** | In-place S-box: 50 CNOT, 6 1qC, 21 T, 0 M, T-d 3, FD 23, width 7. Shallow S-box: 60 / 6 / 21 / 0 / 1 / 11 / 13 |

### 4.3 Code or circuit files released

- `microsoft/grover-blocks` (JNRV, Q#). The README cites ePrint 2019/1146 and says MIT License. GitHub API: `archived: true`. HEAD `fe65e0b29f6c3c3be02ca839259b91f2e71233bc`, last commit 2023-06-05.
- `hzy-cas/AES-quantum-circuit` (Huang–Sun 2022). The LICENSE file is MIT ("Copyright (c) 2022 hzy-cas"). HEAD `8bc3a4614cd128b9df902eb23111de4b0136a1dc`, 2022-09-14. Files: `New_Sbox_Mixcolumns_fixed.qs`, `aes_low_width_sbox_check.cpp`, `MixColumn-check.sage`.
- `hzy-cas/Minimal_T-depth_Width` (Huang–Zhang–Lin 2025). HEAD `1e7892f77d1acc94a8b1b4826af50dbfa6cf3a0c`, 2025-02-12. **There is no LICENSE file at the top level** (raw /LICENSE returned 404; `git ls-tree` does not list one), so the license is unavailable (unknown). Directories: `Classical_to_Quantum`, `Our_new_circuits_AES+SHA3`, `Other_Applications_SKINNY+ASCON`, `Resource_Estimator`, `SAT-based-method-for-minimal_width_NCT`, and others.
- `QunLiu-sdu/Improved-Quantum-Circuits-for-AES` (Liu et al. 2023, ProjectQ). MIT (LICENSE: "Copyright (c) 2023 QunLiu"). HEAD `fe9aad7ae0a4648f70b9094ed22d2341f17a5e00`, 2023-11-01. Has a `Check_Sbox` directory.
- `matthewchunqed/dorcis-public` (DORCIS). **Eclipse Public License 2.0** (LICENSE file). HEAD `fa8f299c6a91447ad3f40b429c922e5740ce7242`, 2024-07-08. Has `3-Bit Implementations` and `4-Bit Implementations` directories.
- `amitcrypto/LWC-Q` (Bijwe et al. 2020, Q#). MIT ("Copyright (c) 2020 Amit Kumar Chauhan"). HEAD `6bcaa077d62858c83e78ec93df5de872a59cffdd`, 2020-12-08. Directories: `gift/`, `skinny/`, `saturnin/`, `numbers-results/`.
- LPS19 (ePrint 2019/854) prints its ProjectQ S-box code in Appendix A. I did not look for a separate repository.
- Jang et al. 2021 (Applied Sciences): the text names ProjectQ. I found no repository link.
- 2025/212 is an ePrint of a EUROCRYPT 2025 paper under CC BY. Paper licenses (ePrint): 2019/854 CC BY, 2019/1146 CC BY, 2022/620 CC BY, 2023/1417 CC BY, 2023/286 **CC BY-NC-ND**, 2025/454 CC BY.

### 4.4 Caveats for using these as qbank reference values

- The rows are **not directly comparable**. They mix NCT counts (Toffoli/CNOT/NOT) with Clifford+T counts, which use AND gates with measurement-based uncompute (#M > 0), so they are not unitary-only. They also mix in-place, out-of-place and C\* forms, and widths that include or exclude the 16 I/O qubits.
- For a unitary-only, measurement-free target, use the NCT rows: A3, A5–A8, A10 Table 3, A11 Table 1, A12, A14–A15, L1–L6.
- The Q# depth and width figures in JNRV (A4/A4′) are affected by the resource-estimator issue noted in the grover-blocks README. HS22 (A9) says in Remark 3 that it estimated widths by hand for this reason.
- The Grassl minimal-width T-count is internally inconsistent in 2025/212 (text 9695, Table 5 "≤ 9295"). The original arXiv:1512.04965 text says 9695.
- For Zou et al. (ASIACRYPT 2020) I found no ePrint id. I cite the IACR archive PDF.
- Not fetched (unavailable in this pass): MDPI HTML for Jang 2021 (HTTP 403 for both curl and WebFetch; the PDF worked through mdpi-res.com). I did not read Shi–Feng ePrint 2024/381, Liao–Luo ePrint 2025/1494, Lin et al. ePrint 2023/146, Li et al. ePrint 2023/018, or Jang et al. "Quantum Analysis of AES" ePrint 2022/683 (CiC 2025). I only confirmed their titles on ePrint, so none of their numbers are included.

---

## 5. Routing

### 5.1 LightSABRE and Qiskit's built-in routing (Qiskit 2.5.2 source)
- **LightSABRE**: arXiv **2409.08368**, *LightSABRE: A Lightweight and Enhanced SABRE Algorithm*, Zou, Treinish, Hartman, Ivrii, Lishman (v1 2024-09-12). Abstract text: "approximately 200 times faster than the implementation in Qiskit 0.20.1 … an average decrease of 18.9% in SWAP gate count" (compared with Li et al.'s SABRE). The docstrings of Qiskit's `qiskit/transpiler/passes/routing/sabre_swap.py` and `layout/sabre_layout.py` both cite arXiv:2409.08368 and 1809.02573.
  - `SabreSwap(coupling_map, heuristic="basic", seed=None, fake_run=False, trials=None)`.
  - Routing-stage plugins (`qiskit.transpiler.routing`): `default, basic, lookahead, none, sabre`.
- **SwapStrategy / commuting two-qubit gate router**: location confirmed at `qiskit/transpiler/passes/routing/commuting_2q_gate_routing/`; files include `swap_strategy.py` (`SwapStrategy`, class method `from_line(line, num_swap_layers=None)`), `commuting_2q_gate_router.py` (`Commuting2qGateRouter(TransformationPass)`, routes only `Commuting2qBlock`), `pauli_2q_evolution_commutation.py` (`FindCommutingPauliEvolutions`), `commuting_2q_block.py`.
  - Imports: `from qiskit.transpiler.passes import Commuting2qGateRouter`; `from qiskit.transpiler.passes.routing import SwapStrategy`; the docstring example uses `from qiskit.transpiler.passes.routing.commuting_2q_gate_routing import SwapStrategy, FindCommutingPauliEvolutions, Commuting2qGateRouter`.
  - The module docstring cites arXiv:2202.03459. I verified that entry: Weidenfeller et al., *Scaling of the quantum approximate optimization algorithm on superconducting qubit based hardware*, Quantum 6, 870 (2022).

### 5.2 pytket
- Latest PyPI `pytket` is **2.18.4** (uploaded 2026-09-24T09:33:10), requires_python **>=3.10**, classifiers 3.10/3.11/3.12/3.13/3.14, license "Apache 2". Wheels exist for cp310, cp311 and **cp312-abi3** (covers 3.12+), on platforms macOS 14 arm64, macOS 15 x86_64, manylinux_2_26 aarch64, manylinux_2_27 x86_64, win_amd64. Source repository github.com/Quantinuum/tket (Apache-2.0, pushed 2026-09-25).
- Routing API (from `pytket/_tket/*.pyi` in the 2.18.4 wheel):
  - `pytket.passes`: `RoutingPass(arc)`, `DefaultMappingPass(arc, delay_measures=True)`, `FullMappingPass(arc, placer, config)`, `CustomRoutingPass(arc, config)`, `PlacementPass(placer)`, `NaivePlacementPass(arc)`, `CXMappingPass(arc, placer, **kwargs)`, `AASRouting(arc, **kwargs)`.
  - `pytket.mapping`: `LexiRouteRoutingMethod`, `LexiLabellingMethod`, `AASRouteRoutingMethod`, `AASLabellingMethod`, `MultiGateReorderRoutingMethod`, `BoxDecompositionRoutingMethod`, `RoutingMethodCircuit`, `MappingManager`.
  - `pytket.placement`: `Placement`, `LinePlacement`, `GraphPlacement`, `NoiseAwarePlacement`.

### 5.3 MQT QMAP
- Latest PyPI `mqt.qmap` is **3.10.0** (uploaded 2026-09-12T07:34:19), requires_python `!=3.14.1,>=3.11`, classifiers 3.11–3.15, MIT. Wheels are cp311-abi3 and cp315-abi3t, on platforms macOS 13 arm64, manylinux aarch64/x86_64, win amd64/arm64. **There is no macOS x86_64 wheel**. Depends on `mqt-core~=3.10.0`, `qiskit[qasm3-import]>=2.1`. Tag v3.10.0 = `8fbcd3e27cee816ef2c5a8780518983d6480a7c1` (2026-09-12).
- Heuristic mapping API (v3.10.0 source `python/mqt/qmap/plugins/qiskit/sc/compile.py`):
  `from mqt.qmap.plugins.qiskit.sc import compile_`
  `compile_(circ, arch, calibration=None, method=Method.heuristic, heuristic=Heuristic.gate_count_max_distance, initial_layout=InitialLayout.dynamic, iterative_bidirectional_routing_passes=None, layering=Layering.individual_gates, automatic_layer_splits_node_limit=5000, early_termination=EarlyTermination.none, early_termination_limit=0, lookahead_heuristic=LookaheadHeuristic.gate_count_max_distance, lookaheads=15, lookahead_factor=0.5, encoding=Encoding.commander, commander_grouping=CommanderGrouping.fixed3, swap_reduction=SwapReduction.coupling_limit, swap_limit=0, include_wcnf=False, use_subsets=True, subgraph=None, pre_mapping_optimizations=True, post_mapping_optimizations=True, add_measurements_to_mapped_circuit=True, add_barriers_between_layers=False, verbose=False, debug=False, visualizer=None) -> tuple[QuantumCircuit, MappingResults]`
  - Enums in `mqt.qmap.sc`: `Method{heuristic=2, exact=1}`; `InitialLayout{identity, static, dynamic}`; `Heuristic{gate_count_max_distance, gate_count_sum_distance, gate_count_sum_distance_minus_shared_swaps, gate_count_max_distance_or_sum_distance_minus_shared_swaps, fidelity_best_location}`; `LookaheadHeuristic{none, gate_count_max_distance, gate_count_sum_distance}`.
  - Note: UPGRADING.md [3.6.0] states "`mqt.qmap.plugins.qiskit.sc.compile` has been renamed to `compile_`", but the README.md example still writes `from mqt.qmap.plugins.qiskit.sc import compile` (the docs were not updated). `docs/mapping.md` uses `compile_`.

### 5.4 Exact / near-optimal routers (with code)
| Tool | Paper (arXiv verified) | Repository / license / HEAD | PyPI |
|---|---|---|---|
| OLSQ (incl. TB-OLSQ) | Tan & Cong, *Optimal Layout Synthesis for Quantum Computing*, arXiv 2007.15671 ("to appear in ICCAD'20", DOI 10.1145/3400302.3415620) | github.com/UCLA-VAST/OLSQ, BSD-3-Clause, HEAD `63f11f24018e416af49bbb6451859b4f1c6b0112`, pushed 2023-09-05 | `olsq` 0.0.4.1 (2022-05-02, requires >=3.6, sdist only; homepage github.com/tbcdebug/OLSQ) |
| OLSQ2 (incl. TB-OLSQ2 = `mode="transition"`) | DAC'23, *Scalable Optimal Layout Synthesis for NISQ Quantum Processors* (Lin, Kimko, Tan, Bjørner, Cong; from WebSearch). arXiv version: unavailable (not found). IEEE Xplore page 10247760 fetched with curl returned 202; content not obtained | github.com/UCLA-VAST/OLSQ2, BSD-3-Clause, HEAD `0d7066f45b073bfd5f163a424b758026639f5acf` (2024-05-29). README points to the newer github.com/WanHsuanLin/OLSQ2 (BSD-3-Clause, HEAD `2b83601bd91c2c366688d9bc17e04d26d21dc1eb`, 2024-05-29), depends on pySAT>=0.1.7, z3-solver>=4.8.15.0, installed via git clone | **None** (PyPI `olsq2` returns 404) |
| SATMAP | Molavi et al., *Qubit Mapping and Routing via MaxSAT*, arXiv 2208.13679 (MICRO 2022). Abstract text: "solves more than 3x benchmarks with 40x speedup … an average of ~5x swap reduction" | github.com/qqq-wisc/satmap, **no license declared** (API license=None), HEAD `a0e6206e4310c821aa3f6bd1cf96fa064fe27c96` (2024-01-30) | None (`satmap` 404) |
| Q-Synth | Shaik & van de Pol, arXiv 2304.12014 (planning); Jakobsen, Clausen, van de Pol, Shaik, *Depth-Optimal Quantum Layout Synthesis as SAT*, arXiv 2506.06752 (SAT 2025). Abstract text: "speedups of more than 10-100x compared to OLSQ2". Also Milkevych et al., arXiv 2507.12976 (subarchitectures) | github.com/irfansha/Q-Synth, MIT, HEAD `95a820e16ac578289ea692ce8665afb48788892d` (2026-06-29 "Version 6.0.beta (#19)") | `q-synth` 5.1 (2025-10-29, requires >=3.10) |
| MQT QMAP exact | — | same as 5.3, `method=Method.exact` | mqt.qmap 3.10.0 |
| TOQM | — | — | `qiskit-toqm` 0.1.0 (2022-10-28, wheels cp37–cp310, i.e. **no wheel for py≥3.11**) |
| ML-QLS (heuristic, compared against in QUBIKOS) | Lin & Cong, arXiv 2405.18371 (v3 2024-12-03) | Not verified | — |
| QUEKO (benchmark with known optimal depth and zero SWAPs) | — | github.com/qu-tan-um/QUEKO-benchmark, BSD-3-Clause, pushed 2022-07-21 | — |

### 5.5 QUBIKOS (arXiv:2502.08839)
- *Assessing Quantum Layout Synthesis Tools via Known Optimal-SWAP Cost Benchmarks*, Ping, Lin, Tan, Cong; v2 2025-03-04; comments "8 pages".
- Code: github.com/ping-shuo-hao/qubikos (GitHub API license = None, i.e. **no license declared**; HEAD `442a994884a6a5fd37725f59b8b42c90fd1be387`, 2025-04-30). The interface in the README is `generate_qubikos_circuit(benchmark.qasm, compiled.qasm, coupling_graph, optimal_swaps, n_2q, n_1q)`. The paper's HTML has no link to this repository; I found it via GitHub search.
- **This paper has no data tables at all (no ltx_table in the HTML).** Results appear only in Figure 4 and the body text. All values below are verbatim from the original (accessed 2026-09-25, source https://arxiv.org/html/2502.08839v2):
  - Metric definition (§IV-B): "The optimality gap is defined based on the SWAP ratio … Average SWAP count / Optimal SWAP count. This ratio is always greater than or equal to 1".
  - Tools tested and versions (§IV): "LightSABRE from Qiskit version 1.2.4, t|ket⟩ version 1.34.0, QMAP version 2.7.0, and ML-QLS … For LightSABRE, we test it with 1000 trials". Optimality is verified with OLSQ2 (PySAT 1.8.dev13, z3-solver 4.13.3.0).
  - §IV-A (optimality verification): Aspen-4 (16 qubits) and a 3x3 grid, 400 circuits per architecture, 100 each with SWAP count 1–4, ≤30 two-qubit gates. Original text: "all generated circuits have the desired SWAP counts".
  - §IV-B (tool evaluation): 40 circuits each for Aspen-4, Sycamore(54), Rochester(53), Eagle(127), 10 each with SWAP=5/10/15/20; two-qubit gate counts are 300 for Aspen-4, 1500 for Sycamore/Rochester, and 3000 for Eagle.
  - **Abstract text**: "LightSabre from IBM delivers the best performance with an optimality gap of 63x, followed by ML-QLS with an optimality gap of 117x. Similarly, QMAP and t|ket⟩ exhibit significantly larger gaps of 250x and 330x, respectively."
  - **§IV-B body text**: "ML-QLS achieves optimal results on Aspen-4 and Rochester, and LightSABRE performs the best on the other architectures … t|ket⟩ and QMAP exhibit a significantly larger optimality gap with an average of 185x and 207x respectively on Aspen-4 and as high as 846x and 930x on Eagle … on Aspen-4, ML-QLS finds the optimal solutions in all cases. But on Sycamore, Rochester, and Eagle, LightSABRE has an optimality gap of 1.95x, 12.17x, and 233.97x respectively … despite the Rochester architecture having a similar number of physical qubits to the Sycamore architecture, its optimality gap is six times larger."
  - Note: the paper does not explain how the abstract's 63x / 117x / 250x / 330x relate to the per-architecture values in the body. "ML-QLS achieves optimal results on … Rochester" and "LightSABRE … 12.17x on Rochester" can both hold. The full per-architecture bar data exist only in Figure 4 and **cannot be read as a table; recorded as unavailable (image data)**.
  - §IV-C text: "In Qiskit, the extended set size is 20 with a weight of 0.5" (LightSABRE's lookahead setting).

---

## 6. D-category baselines: Dicke, W, sparse and dense state preparation

Access date for everything below: **2026-09-25**. Sources were fetched from arxiv.org/abs (metadata), arxiv.org/pdf (read with `pdftotext`), arxiv.org/html, PyPI JSON, `git clone --depth 1` / `git ls-remote`, and raw LICENSE files. Scratch artifacts are in `recon_BCDE/pdf6/`, `recon_BCDE/sc6/`, `recon_BCDE/qclib_repo/` and `recon_BCDE/venv_qclib/`.

**Limitations.**
- The unauthenticated GitHub REST API was exhausted partway through (resets about 18:33 local). After that, SHAs and dates come from `git clone --depth 1` + `git log -1`, and licenses come from the LICENSE file in the clone.
- `export.arxiv.org` API search returned empty/429 for later queries. Paper ids were then found with WebSearch and verified on arxiv.org/abs pages.

### 6a. Bärtschi & Eidenbenz, "Deterministic Preparation of Dicke States"

- **Paper:** arXiv:**1904.07358** (v1 15 Apr 2019). Authors: Bärtschi, Andreas; Eidenbenz, Stephan. FCT'19, pp. 126–139, DOI 10.1007/978-3-030-25027-0_9. Report LA-UR-19-22718.
- **Headline claim (abstract):** "our scheme uses O(kn) gates, has depth O(n)".
- **§3 "Circuit Size and Depth", Theorem 1 (as printed):** "Dicke states |D^n_k⟩ can be prepared with a circuit of size O(min(k, n − k) · n) and depth O(n), even on Linear Nearest Neighbor architectures."
- **Explicit counts in the proof of Theorem 1:** "compiling U_{n,k} down to at most **5kn + O(n) CNOT-gates** and **4kn + O(n) arbitrary precision Ry-gates**."
  - The construction uses "n − 1 many 2-qubit gates (i)" and "(n − k)·(k − 1) + Σ_{i=3}^{k}(i − 2) = kn − k² + O(n) many 3-qubit gates (ii)_ℓ".
  - Each "(ii)_ℓ-gate can be implemented with 5 CNOT gates and 4 Ry gates" (Fig. 3).
  - Ancillas: none (input |0⟩^{⊗n−k}|1⟩^{⊗k}).
- **Third-party code (not by the authors):** github.com/andre-juan/dicke_states_preparation. HEAD `c6785cfae94fa12c12951d598496640c9b99318b` (2024-06-10, "Create LICENSE"), Apache-2.0 LICENSE.
  - Static check: `dicke_states.py` does `from qiskit import QuantumRegister, QuantumCircuit, Aer, execute`.
  - Qiskit 1.0 release notes (`releasenotes/notes/1.0/remove-aer-hooks-…yaml`, `remove-execute-…yaml` in the Qiskit 2.5.2 clone) say `qiskit.Aer` and `execute` were removed. So this code will not import on Qiskit ≥1.0 without edits. This is inferred from reading the code; I did not run it.

### 6b. Newer Dicke constructions

| Paper | arXiv | Printed result (quoted) | Where |
|---|---|---|---|
| Bärtschi & Eidenbenz, "Short-Depth Circuits for Dicke State Preparation", QCE'22, DOI 10.1109/QCE53715.2022.00027 | **2207.09998** | Thm 1 (all-to-all): "U^n_k can be implemented with a circuit of depth O(k log(n/k)) on all-to-all connectivities, with O(kn) 2-qubit gates in total and without ancilla qubits." Thm 2 (grid): "depth O(k√(n/k)) on grid topologies of size Ω(√(n/s)) × O(√(ns)), where 1 ≤ s ≤ k, with O(kn) 2-qubit gates in total and without ancilla qubits." Concrete: \|D^8_2⟩ with "total CNOT count is 27" all-to-all (Fig. 6; "improves on previous work with an explicit CNOT gate count of 44 [25]") and "31" on grid (Fig. 7). | Thm 1, Thm 2, Figs. 6–7, Table I |
| Aktar, Bärtschi, Badawy, Eidenbenz, "A Divide-and-Conquer Approach to Dicke State Preparation", IEEE TQE 3 (2022), DOI 10.1109/TQE.2022.3174547 | **2112.12435** | **Table 2, CNOT counts.** LNN: k=1, n=2..6: 1, 3, 5, 7, 9; k=2, n=4..6: 10, 17, 24; k=3, n=6: 32. Ladder: k=1: 1, 3, 5, 7, 9; k=2: 7, 14, 21; k=3: 23. "prev # CNOTs" (Cruz for k=1, Mukherjee for k=2,3): k=1: 1, 3, 5, 7, 9; k=2: 12, 20, 28; k=3: 33. Text: for W states "this method retrieves the best-known CNOT counts of 2n − 3". | Table 2, §1 |
| Mukherjee, Maitra, Gaurav, Roy, "On Actual Preparation of Dicke State on a Quantum Computer" | **2007.01681** (v2 19 Jul 2020) | **Table I** ("Gates needed to prepare \|D^n_k⟩ as in [2]", i.e. Bärtschi–Eidenbenz 2019): CNOT = 5(nk − k(k+1)/2 − n + 1) + 4(n − 1); single-qubit = 4(nk − k(k+1)/2 − n + 1) + 2(n − 1). Improved circuit: "total number of CNOT gates present in the circuit is … = **5nk − 5k² − 2n**", single-qubit "= 4nk − 4k² − 2n + 1". For k=1: "2n − 2 CNOT and 2n − 2 single qubit gates". | Table I and the gate-count derivation in §III/IV (pdftotext; section numbers not reliably extracted) |
| Yuan & Zhang, "Depth-Efficient Quantum Circuit Synthesis for Deterministic Dicke State Preparation" | **2505.15413** (v1 21 May 2025) | Abstract / Thm 13: all-to-all depth **O(log(k) log(n/k) + k)** (previous best O(k log(n/k)) [BE22]). Grid (n1×n2): O(k log(n/k) + n2) for k ≥ n2/n1; optimal O(n2) for k < n2/n1. Lower bounds Ω(log n) (all-to-all) and Ω(n2) (grid) (Thm 20). Table 1 is depth only; no CNOT total printed in the grepped text. | Table 1, Thm 13, Thm 14 / Coro 15, Thm 20 |
| Joshi & Vasconcelos, "Constant-Depth Unitary Preparation of Dicke States" | **2601.10693** (v3 25 Aug 2026) | Abstract: constant depth using unbounded CZ (QAC⁰) with polynomial ancillae for constant-weight Dicke; with FAN-OUT (QAC⁰_f), exact arbitrary-weight Dicke with polynomial ancillae. Not the standard 2-qubit-gate model. | abstract |
| Yu, Muleady, Wang, Schine, Gorshkov, Childs, "Efficient preparation of Dicke states" (DOI 10.1103/9gjk-rgql) | **2411.03428** | Abstract: mid-circuit measurement + feedback; "polylogarithmically many ancillas and polylogarithmic depth". Dynamic circuit, relevant to E. | abstract |
| Luo & Li, "Optimal Circuit Size for Fixed-Hamming-Weight Quantum States Preparation" | **2508.17197** | Abstract: any n-qubit HW-k state with size O(C(n,k)) "using at most max{0, n−3} ancillary qubits". | abstract |

Others the arXiv search surfaced; I did not read beyond the title: 2601.20393 (multi-QPU Dicke), 2608.22168, 2301.04989 / 2402.03233 / 2507.13308 (qudit/spin-s Dicke).

### 6c. W state: log-depth construction

- **Paper:** Cruz, Fournier, Gremion, Jeannerot, Komagata, Tosic, Thiesbrummel, Chan, Macris, Dupertuis, Javerzac-Galy, "Efficient quantum algorithms for GHZ and W states, and implementation on the IBM quantum computer". arXiv:**1807.05572** (v1 15 Jul 2018), Adv. Quantum Technol. 1900015 (2019), DOI 10.1002/qute.201900015. The paper's sections are unnumbered.
- **Linear circuit:** blocks B(1/N), …, B(1/2); "total number of such gates and time steps are N−1 … multiplies this complexity by a factor 5 or 4".
- **Section "Logarithmic time complexity circuit" (N = 2^m):** "In general the time complexity is k log2 N and the total number of gates in the circuit is kN", with k = 5 or 4 depending on the controlled-G(1/2) implementation.
- **As implemented:** "(for N = 2^m) the implemented version requires **4N − 5 gates** and **4 log2(N) − 2 steps**, to produce a W_N state".
- **In other papers' tables:**
  - 2207.09998 Table I: Cruz et al. 2018 is "W states, O(log n) depth, O(n) CNOT, no ancilla, all-to-all".
  - 2112.12435: best-known W CNOT count is **2n − 3**.

### 6d. Sparse state preparation (d or s = number of non-zero amplitudes)

| Method | arXiv / venue | Printed complexity (quoted) | Code (verified) |
|---|---|---|---|
| Gleinig & Hoefler, "An efficient algorithm for sparse quantum state preparation", DAC 2021 pp. 433–438, DOI 10.1109/DAC18074.2021.9586240 | **No arXiv version found.** arXiv author search "Gleinig" lists 5 papers (2302.01066, 2301.01048, 2208.11469, 1801.01357, 1710.03522); none is this one. I did not read the paper itself (IEEE). | As summarized by Li & Luo arXiv:2406.16142 §1.3: "circuit of size O(nd) without using ancillary qubits". | qclib `MergeInitialize` (`qclib/state_preparation/merge.py`, docstring cites ieeexplore 9586240) |
| Malvetti, Iten, Colbeck, "Quantum Circuits for Sparse Isometries", Quantum 5, 412 (2021) | **2006.00016** | **Table 1:** state preparation with 0 ancilla ("1 dirty if s = n − 1"): C-not count **(n + 16s − 9)·nnz(v) + (23/24)·2^s**. With ⌈s/2 − 1⌉ clean ancillas: **(n + 6s − 7)·nnz(v) + (23/24)·2^s**, where s = ⌈log2 nnz(v)⌉ (Corollary 5). The fraction layout is reconstructed from pdftotext. | Authors: UniversalQCompiler (Mathematica; linked from the abstract page). github.com/Q-Compiler/UniversalQCompiler, Apache-2.0, HEAD `c72cd84a537786756ae8490c07f3f599aa411323` (2025-09-25), needs Wolfram Mathematica + QI.m. qclib `PivotInitialize` ("Pivot State Preparation arXiv:2006.00016"). |
| Mozafari, De Micheli, Yang, "Efficient Deterministic Preparation of Quantum States Using Decision Diagrams", PRA 106, 022617 (2022) | **2206.08588** | Abstract: "circuit complexity that is linear in the number of paths in the decision diagram". Up to 31.85% fewer (vs SOTA) on generic states and 86.61%–99.9% fewer CNOTs on sparse-DD states. Li & Luo §1.3: "circuit size O(kn), using 1 ancillary qubit, where k denotes the number of paths". | github.com/fmozafari/angel (C++), MIT, HEAD `3ca5f2978a8e47c59c3bee138e220ab7a8c3935b` (2023-01-05). The paper says the code is in `include/angel/quantum state preparation/`. The clone has `include/angel/quantum_state_preparation/{qsp_bdd,sparse_qsp,sparse_uniform_qsp,…}.hpp`. |
| Zhang, Li, Yuan, "Quantum State Preparation with Optimal Circuit Depth: Implementations and Applications", PRL 129, 230504 (2022) | **2201.11495** | Abstract: arbitrary state Θ(n) depth with exponential ancillas. Sparse (d ≥ 2): depth **Θ(log(nd))** with **O(nd log d)** ancillary qubits. 2207.09998 Table I lists it as "O(log(dn)) depth, O(dn log(dn)) CNOT, O(dn log d) ancilla". | No code link in the PDF text (grep for github/gitlab/zenodo: none). |
| Mao, Tian, Sun, "Towards Optimal Circuit Size for Sparse Quantum State Preparation" (PRA 110, 032439 per Li–Luo refs) | **2404.05147** | Abstract: "The first algorithm uses O(ns/log n + n) gates", plus a matching lower bound for non-amplitude-aware algorithms with ≤ poly(n) ancillas. U(1)-invariant (incl. Bethe) states: O(C(n,k) log n). | No code link in PDF text. |
| Li & Luo, "Nearly Optimal Circuit Size for Sparse Quantum State Preparation" (ICALP 2025 per arXiv comments; author order Li, Lvzhou; Luo, Jingquan) | **2406.16142** | Abstract: no ancilla, size **O(nd/log n + n)**. With m ancillas, **O(nd/log(n+m) + n)** for m ∈ O(nd/log(nd) + n), with matching lower bound Ω(nd/log(n+m) + n) "under some reasonable assumptions". Unlimited ancillas **Θ(nd/log(nd) + n)**. | No code link in PDF text. |
| Ramacciotti, Lefterovici, Rotundo, "A simple quantum algorithm to efficiently prepare sparse states" | **2310.19309** | Abstract: Grover–Rudolph on sparse states is "linear in the number of non-zero amplitudes … and quadratic in the number of qubits"; the modified version is linear in both. Li & Luo §1.3: O(nd) with 1 ancilla. | No code link in PDF text. |
| de Veras, de Araujo, Park, da Silva, "Circuit-based QRAM for classical data with continuous amplitudes" (CVQRAM), IEEE TC 70(12) | **2011.07977** | Li & Luo §1.3: "same circuit size [O(nd)] by employing 2 ancillary qubits". | qclib `CvqramInitialize` |
| de Veras, da Silva, da Silva, "Double sparse quantum state preparation" (CVO-QRAM), QIP 21, 204 (2022) | **2108.13527** | Abstract: "computational cost O(kM), where M is the number of nonzero probability amplitudes and k is the maximum number of bits with value 1". | PDF links github.com/qclib/qclib; qclib `CvoqramInitialize` |
| Rupprecht & Wölk, "Sparse quantum state preparation with improved Toffoli cost", Quantum 10, 2208 (2026-09-10), DOI 10.22331/q-2026-09-10-2208 | **2601.09388** (from the journal page's `citation_arxiv_id`) | Abstract: worst-case Toffoli cost of the isometry step "essentially 2s for sufficiently large n", about a log(s)/2 improvement. | No GitHub link on the abs page. |
| Luo & Li, "Sparse Quantum State Preparation with Sublinear T-Count" | **2608.00414** | Abstract: Õ(min{s, n^{3/4}√s} + √(s log(1/ε)) + log(1/ε)) T gates; lower bound Ω(min{s, √(ns)}). | not checked |

### 6e. qclib

- **PyPI:** latest **0.1.15**, uploaded 2025-07-28T15:42:11. `requires_python >=3.8`. PyPI `license` field empty; classifiers only "Programming Language :: Python :: 3". Pure `py3` wheel.
- **Repo:** github.com/qclib/qclib. GitHub API (before the rate limit): license **Apache-2.0**, language Python, pushed 2026-04-07. `LICENSE.md` in the clone is Apache License 2.0.
  - HEAD `cf069817b0ea226aec93b59a1c4307f750673ef4` (2026-04-07, "test ucge target state (#213)").
  - `setup.py` at HEAD still says `version="0.1.15"`, `python_requires='>=3.8'`, `install_requires=[scipy>=1.7.1, qiskit>=1.0.0, deprecation, tensorly>=0.8.0, keras, graphviz, scikit-image, sympy]`.
- **Methods in `qclib/state_preparation/`** (reference taken from each module's docstring):

| Module / class | Type | Reference in source |
|---|---|---|
| `merge.py` `MergeInitialize` | sparse (InitializeSparse) | Gleinig & Hoefler DAC'21, ieeexplore 9586240 |
| `pivot.py` `PivotInitialize` | sparse | "Pivot State Preparation arXiv:2006.00016" (Malvetti–Iten–Colbeck) |
| `cvoqram.py` `CvoqramInitialize` | sparse | "cvo-qram" (paper 2108.13527 names the algorithm CVO-QRAM) |
| `cvqram.py` `CvqramInitialize` | sparse | arXiv:2011.07977 |
| `fnpoints.py` `FnPointsInitialize` | sparse | arXiv:quant-ph/9807054 (Ventura & Martinez, Found. Phys. Lett. 12 (1999)) |
| `lowrank.py` `LowRankInitialize` | dense | arXiv:2111.03132 (Araujo, Blank, Araújo, da Silva, "Low-rank quantum state preparation", DOI 10.1109/TCAD.2023.3297972); also cites 1003.5760 |
| `baa_lowrank.py` `BaaLowRankInitialize` | dense, approximate | arXiv:2111.03132; 1003.5760 |
| `svd.py` `SVDInitialize` | dense | arXiv:1003.5760 (Plesch & Brukner, PRA 83, 032302) |
| `ucg.py` `UCGInitialize` | dense | Bergholm et al. PRA 71, 052330 / quant-ph/0410066 |
| `ucge.py` `UCGEInitialize` | dense | arXiv:2409.05618 ("Quantum Multiplexer Simplification for State Preparation", ACM TQC 6(4) 2025) |
| `isometry.py` `IsometryInitialize` | dense | arXiv:1501.06911 (Iten et al.) |
| `topdown.py` `TopDownInitialize` | dense | quant-ph/0407010; 2108.10182 |
| `bdsp.py` `BdspInitialize` | dense, sublinear depth with ancillas | arXiv:2108.10182 ("Configurable sublinear circuits for quantum state preparation", DOI 10.1007/s11128-023-03869-7) |
| `dcsp.py` `DcspInitialize` | dense, divide-and-conquer | DOI 10.1038/s41598-021-85474-1; 2108.10182 |
| `blackbox.py` `BlackBoxInitialize` | dense | Grover, PRL 85, 1334 (2000) |
| `frqi.py` `FrqiInitialize` | image encoding | Springer s11128-010-0177-y |
| `mixed.py` `MixedInitialize` | mixed states | — |

- **README table** ("same random 15-qubit state"; I read it, did not re-run it):

| method | qubits | CNOTs | depth |
|---|---|---|---|
| low-rank | 15 | 30998 | 53643 |
| svd | 15 | 38814 | 71580 |
| ucg | 15 | 32752 | 65505 |
| qiskit isometry | 15 | 32752 | 65505 |
| qiskit multiplexor | 15 | 65504 | 131025 |
| bdsp | 1151 | 72320 | 1603 |
| dcsp | 32767 | 262016 | 899 |

- **Install/run smoke test** (my own run in a scratch venv; Python 3.11.4, macOS; `pip install qiskit==2.5.2 qclib==0.1.15` installed cleanly):
  - `import qclib.state_preparation` failed with `ModuleNotFoundError: No module named 'qiskit_aer'`. `qclib/util.py` imports `qiskit_aer`, but `setup.py` does not declare it. After `pip install qiskit-aer` (got 0.17.2) the import works.
  - Test state: 6-qubit, 5-sparse, real positive amplitudes, seed 1. Each circuit was built from `Gate(...).definition`, then `transpile(basis_gates=['cx','u'], optimization_level=0)`. Fidelity was checked on the n data qubits over both register placements and both bit orders.

| Method | Result |
|---|---|
| `MergeInitialize` | 6 qubits, **15 CX**, fidelity 1.0 |
| `PivotInitialize(opt_params={'aux':True})` | 8 qubits, **69 CX**, fidelity 1.0 |
| `PivotInitialize` (default, no aux) | **fails:** `TranspilerError: HighLevelSynthesis: number of input qubits (5) does not match the circuit size (4)`, i.e. an internal sub-gate size mismatch under Qiskit 2.5.2 |
| `CvqramInitialize` | **fails:** `AttributeError: 'QuantumCircuit' object has no attribute 'cu3'` (`cvqram.py` lines 108/117 call `circuit.cu3`; Qiskit Terra 0.23 release note `remove-deprecated-circuit-methods-…yaml` removed `cu1`/`cu3`) |
| `CvoqramInitialize` | 12 qubits / 121 CX with aux; 7 qubits / 149 CX without aux. My fidelity check gave 0.679, which is **inconclusive** (probably my register mapping; qclib's tests pad "work qubits") |
| `FnPointsInitialize` | 13 qubits / 337 CX, my check 0.072, **inconclusive** |

  - Appending the gate objects directly (`qc.append(g, range(g.num_qubits))`) instead of using `.definition` failed for pivot and cvoqram because gate width does not match definition width.

### 6f. BQSKit

- **PyPI:** latest **1.2.1**, uploaded 2025-08-30T22:35:58. `requires_python <4,>=3.8`. PyPI license "BSD 3-Clause License". Classifiers 3.8, 3.9, 3.10, 3.11, 3.12. Pure `py3` wheel.
- **Repo:** github.com/BQSKit/bqskit. GitHub API: license NOASSERTION, pushed 2026-08-11. The LICENSE file is BSD-style ("Berkeley Quantum Synthesis Toolkit (BQSKit) Copyright (c) 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory … and Massachusetts Institute of Technology (MIT)").
- **HEAD** `9324d64a65f147ecffec005a122eb5a491a3fefc` (2026-08-11, "Merge pull request #384 …"). At HEAD, `pyproject.toml` has `requires-python = ">=3.10, <4"`, `license = "BSD-3-Clause"`, classifiers 3.10–3.14, and `bqskit/_version.py` = 1.2.1. So HEAD tightens Python support compared with the 1.2.1 release on PyPI.
- **State-prep relevance:** `bqskit/compiler/compile.py` accepts `CompilationInput = Union[Circuit, UnitaryMatrix, StateVector, StateSystem]`, so `compile()` can take a target state vector (numerical, instantiation-based synthesis). I did not run it.

### 6g. Qiskit 2.5.2 native state preparation (clone at tag 2.5.2, `c1c01ada399af13e495c27b9b22b4ff942bbad7e`, 2026-08-13)

| Class | Location | Notes from docstring/source |
|---|---|---|
| `StatePreparation(Gate)` | `qiskit/circuit/library/data_preparation/state_preparation.py:34` | `_define` → `_define_synthesis_isom()` → `Isometry(self.params, 0, 0)` |
| `UniformSuperpositionGate(Gate)` | same file, line 250 | Shukla–Vedula (QIP 23, 38 (2024)), "O(log2(M)) qubits and O(log2(M)) gates" |
| `Initialize(Instruction)` | `qiskit/circuit/library/data_preparation/initializer.py:33` | reset + StatePreparation; "based on the Isometry synthesis" (Iten et al. PRA 93, 032318) |
| `Isometry(Instruction)` | `qiskit/circuit/library/generalized_gates/isometry.py:37` | Iten et al. 2016 |
| `UCGate(Gate)` | `qiskit/circuit/library/generalized_gates/uc.py:39` | uniformly controlled gates |
| `GraphStateGate(Gate)` | `qiskit/circuit/library/graph_state.py:89` | graph states |

- No Dicke or W-state class or synthesis function: `grep -rli dicke qiskit/` returns nothing, and there is no `w_state` export in `qiskit/circuit/library/__init__.py` or `qiskit/synthesis/__init__.py`.
- Qiskit has no sparse-specific state-prep method. Sparse vectors go through the dense Isometry path (inferred from the `_define` code path above).

---

## 7. E-category: citable sources for "no_room" flags and dynamic-circuit state preparation

Access date for everything below: 2026-09-25. Metadata comes from arXiv abs pages (`arxiv.org/abs/<id>`). Quotes come from the arXiv abstract, the arXiv HTML (`arxiv.org/html/<id>`), or `pdftotext` of `arxiv.org/pdf/<id>`, and each one gives its location. Partway through, the arXiv API (`export.arxiv.org/api/query`) returned HTTP 429 (rate limit), so I switched to abs/HTML/PDF pages and WebSearch.

### 7(i) Measured (semiclassical) QFT needs no two-qubit gates
- **Griffiths & Niu, "Semiclassical Fourier Transform for Quantum Computation"**, arXiv:**quant-ph/9511007**, Phys. Rev. Lett. 76, 3228–3231 (1996), DOI 10.1103/PhysRevLett.76.3228.
  - Abstract: "In this way the two-bit gates in the Fourier transform can all be replaced by a smaller number of one-bit gates controlled by classical signals."
  - PDF p.1 (intro): "…quantum Fourier transforms which in Shor's algorithms immediately precede a final measurement can be carried out in a semi-classical fashion which requires no two-bit gates. The trick is to measure a particular bit and then use the result to produce a classical signal which controls a one-bit transformation carried out on the next bit just before it is measured, and so forth." Also: "computing the Fourier transform is considerably simplified in the sense that it requires no two-bit gates."
  - PDF, text for Fig. 2: "…the arrangement shown in Fig. 2, where all the two bit gates in Fig. 1 have been eliminated, and their work taken over by one-bit gates controlled by classical signals (double lines) and followed by measurements."
  - Supports: a QFT followed by measurement can be done with **0 two-qubit gates**, using mid-circuit measurement plus classically controlled one-qubit rotations. Caveat: this only holds when the QFT output is measured right away.

### 7(ii) Iterative / semiclassical QPE with a single control (ancilla) qubit
- **Mosca & Ekert, "The Hidden Subgroup Problem and Eigenvalue Estimation on a Quantum Computer"**, arXiv:**quant-ph/9903071** (Proc. 1st NASA QCQC, Springer; the abs page gives no DOI).
  - Abstract: "…certain instances of these problems can be solved with only one control qubit, or `flying qubits', instead of entire registers of control qubits."
  - §5.2 "One Control Bit", Fig. 3 (PDF): "This means we could in fact do all the quantum controlled multiplications with a single control qubit provided we can execute the 'semi-classical' controls which allow us to reset a qubit to |0⟩+|1⟩ and perform a rotation dependent upon the previous measurements." It cites [GN] = Griffiths & Niu.
- **Dobšíček, Johansson, Shumeiko, Wendin, "Arbitrary accuracy iterative phase estimation algorithm as a two qubit benchmark"**, arXiv:**quant-ph/0610214** (v3), DOI 10.1103/PhysRevA.76.030306 (Phys. Rev. A 76, 030306).
  - Abstract: "We discuss the implementation of an iterative quantum phase estimation algorithm, with a single ancillary qubit. … we describe in detail the smallest possible realization, using only two qubits…"
  - PDF p.1: "…the QFT-based PEA can be implemented in a multiround fashion, using a single ancillary qubit, based on the semiclassical QFT. In this paper, we refer to this single ancilla QFT based PEA as iterative PEA (IPEA)." On Kitaev's variant: "…run either log m rounds (iterations) with m ancillary qubits or m log(m) rounds with only a single ancilla."
- **Parker & Plenio, "Efficient factorization with a single pure qubit and log N mixed qubits"**, arXiv:**quant-ph/0001066**, Phys. Rev. Lett. 85, 3049 (2000), DOI 10.1103/PhysRevLett.85.3049. Abstract: "…a single pure qubit together with a collection of log₂ N qubits in an arbitrary mixed state is sufficient to implement Shor's factorization algorithm efficiently."
- **Kitaev, "Quantum measurements and the Abelian Stabilizer Problem"**, arXiv:**quant-ph/9511026** (the abs page gives no jref or DOI). Abstract: "Our method is based on a procedure for measuring an eigenvalue of a unitary operator." The abstract has no explicit "single qubit" wording; use Dobšíček's summary of Kitaev's variant quoted above.
- Supports: iterative QPE uses **1 ancilla**, so peak width is n_system + 1. For a one-qubit U the smallest realization is 2 qubits (Dobšíček).

### 7(iii) Unitary-depth lower bounds (light cone) for GHZ / W / Dicke
- **Bäumer et al. (IBM), "Efficient Long-Range Entanglement using Dynamic Circuits"**, arXiv:**2308.13065** (v2), PRX Quantum 5, 030339 (2024), DOI 10.1103/PRXQuantum.5.030339.
  - §I Introduction (HTML): "Given that the entanglement cannot spread faster than its information light cone [17, 18], entangling two qubits that are a distance n apart requires a minimum two-qubit gate-depth that scales as 𝒪(n), and even when assuming all-to-all connectivity, the generation of entanglement over n qubits necessitates a minimum two-qubit gate depth of 𝒪(log n)." Refs [17,18] are Lieb & Robinson 1972 and Bravyi–Hastings–Verstraete 2006.
  - §III, Fig. 2(b) caption: "Circuits to prepare an n-qubit GHZ state using either a unitary (left) or dynamic (right) circuit. For a 1D qubit chain, the depth of the unitary (resp., dynamic) circuit scales as 𝒪(n) (resp., 𝒪(1))." Also: "If the final state is not directly used, the feed-forward operations can be implemented in classical post-processing on the output bits."
  - §III: "Although we do not see a clear advantage of dynamic circuits over unitary ones in this case [GHZ on hardware]…"
  - Appendix B.2: "…dynamic circuits can perform entangled gates between arbitrary qubits in constant depth instead of linear depth with only unitary operations…"
- **Bravyi, Hastings, Verstraete, "Lieb-Robinson bounds and the generation of correlations and topological quantum order"**, arXiv:**quant-ph/0603121**, Phys. Rev. Lett. 97, 050401 (2006), DOI 10.1103/PhysRevLett.97.050401. Abstract: "…there is a finite speed at which correlations and entanglement can be distributed… prove lower bounds on the time it takes to convert states without topological quantum order to states with that property."
- **Piroli, Styliaris, Cirac, "Quantum Circuits assisted by LOCC: Transformations and Phases of Matter"**, arXiv:**2103.13367** (v4), Phys. Rev. Lett. 127, 220503 (2021), DOI 10.1103/PhysRevLett.127.220503.
  - Proposition 1 (HTML): for d(A,B) > 2ℓ, a state prepared from |0⟩ by a depth-ℓ QC has ⟨X_A Y_B⟩ = ⟨X_A⟩⟨Y_B⟩. "This proposition is useful to prove that some states cannot be prepared by QC."
  - Example 1 "(The GHZ and W states)": "For both states it is simple to find X_A, Y_B with d(A,B)=N/2 s.t. (1) is not verified. Let us show that they can be prepared by QCcc₂." For GHZ it uses one ancilla per site (except the first) and a depth-2 QC: "This state can be transformed into |GHZ⟩ via LOCC… apply a local CNOT gate between each qubit and its ancilla… and measure all ancillas in the computational basis."
- **Tantivasadakarn, Thorngren, Vishwanath, Verresen, "Long-range entanglement from measuring symmetry-protected topological phases"**, arXiv:**2112.01519** (v3), Phys. Rev. X 14, 021040 (2024), DOI 10.1103/PhysRevX.14.021040. Abstract: "…long-range entanglement (SRE and LRE). The latter cannot be created by finite-depth circuits, underscoring the nonlocal nature of Schrödinger cat states…"
- **Smith, Crane, Wiebe, Girvin, "Deterministic constant-depth preparation of the AKLT state on a quantum processor using fusion measurements"**, arXiv:**2210.17548** (v2), DOI 10.1103/PRXQuantum.4.020315. Abstract: "Having a nonzero correlation length, the AKLT state cannot be exactly prepared by a constant-depth unitary circuit composed of local gates… this no-go limit can be evaded by augmenting a constant-depth circuit with fusion measurements…"
- **Joshi & Vasconcelos, "Constant-Depth Unitary Preparation of Dicke States"**, arXiv:**2601.10693** (v3, no jref). Abstract: "…unitary preparation of Dicke states is limited to logarithmic depth in standard circuit models and existing constant-depth protocols require measurement and feed-forward." The paper gets past this with unbounded CZ gates (QAC⁰) or FAN-OUT (QAC⁰_f), which are outside the standard circuit model.

### 7(iv) Constant-depth GHZ / W / Dicke with measurement and feed-forward (dynamic circuits)
- **Buhrman, Folkertsma, Loff, Neumann, "State preparation by shallow circuits using feed forward"**, arXiv:**2307.14840** (v5), Quantum 8, 1552 (2024), DOI 10.22331/q-2024-12-09-1552. Model: LAQCC (constant-depth nearest-neighbour quantum layers plus log-depth classical control).
  - §3 Corollary 3.10 / Fig. 2 (HTML): "Figure 2 shows a LAQCC circuit using 2n−1 qubits placed on a line that prepares an n-qubit GHZ state." It follows the "poor man's cat state approach of [Wat+19]".
  - Theorem 4.1: "There is a deterministic LAQCC circuit that prepares the uniform superposition of size q. This circuit requires 𝒪(⌈log₂ q⌉²) qubits."
  - Theorem 4.5: "There exists a circuit in LAQCC that prepares the |W_n⟩ state. This circuit requires 𝒪(n log n) qubits placed in a grid of size n×log(n)."
  - Theorem 4.10: "For any n and k=𝒪(√n) there exists an LAQCC circuit preparing the Dicke-(n,k) state… using 𝒪(n² log n) qubits." The abstract notes that it "fails for higher k due to the birthday paradox."
  - Theorem 4.21: an LAQCC-LOG circuit (log-depth quantum) prepares Dicke-(n,k) for any k ≤ n with poly(n) qubits.
  - §4.3 also restates the unitary baseline: "There exists an efficient deterministic method to prepare a |D^n_k⟩ state that requires a circuit of width 𝒪(n) and depth 𝒪(n), independent of k [BE19]."
  - §1 on Piroli 2021's W circuit: "These dependent measurements translate to sequential alternations between the quantum and classical circuits and therefore increase the total depth to linear depth…"
- **Piroli, Styliaris, Cirac, "Approximating many-body quantum states with quantum circuits and measurements"**, arXiv:**2403.07604** (v3), Phys. Rev. Lett. 133, 230401 (2024), DOI 10.1103/PhysRevLett.133.230401. Abstract: "…by lifting the requirement of exact preparation… the so-called W and, more generally, Dicke states require a circuit depth and number of ancillas per site that are independent of the system size." Table 1 compares depth D, ancillas per site N_a and repetitions N_r against Ref. [30]; the row for Ref. [30] reads "O(1) | O(N ln N) | 1". Text: "In Ref. [16] a protocol was proposed to prepare the W state that uses a QC with D=O(1), but requires sequential use of LOCC, i.e. a O(N) preparation time."
- **Luo, Chen, Ma, "Constant-depth adaptive preparation of Dicke and symmetric states"**, arXiv:**2608.01144** (v1, 2026-08-02, no jref). Abstract: this is an exact, probabilistic, constant-depth protocol for Dicke-(n,k) using O(n² + k² log² n + kn log n log log n) ancillas. The uniform-subset primitive has success probability at least 1/k, and parallel repetition suppresses the failure probability.
- **Tantivasadakarn, Verresen, Vishwanath, "Shortest Route to Non-Abelian Topological Order on a Quantum Processor"**, arXiv:**2209.03964** (v2), Phys. Rev. Lett. 131, 060405 (2023), DOI 10.1103/PhysRevLett.131.060405. This is about topological order, not GHZ/W. It is a finite-depth circuit plus one measurement round with no feed-forward: "D4 non-Abelian topological order… using a depth-11 circuit and a single layer of measurements."
- Unitary log-depth baseline (for comparison): **Cruz et al., "Efficient quantum algorithms for GHZ and W states, and implementation on the IBM quantum computer"**, arXiv:**1807.05572**, Adv. Quantum Technol. 1900015 (2019), DOI 10.1002/qute.201900015. Abstract: "We propose efficient algorithms with logarithmic step complexities for the generation of entangled GHZ_N and W_N states…" This one belongs to item 6 but is listed here for completeness.
- Not found or not verified: I did not look for a separate "Yu Xu constant-depth Dicke" paper. The arXiv API search for constant-depth Dicke with measurement returned only the entries above (2601.10693, 2608.01144, 2307.14840, plus 2609.08925, an error-detection paper by Smith et al. that is not about state preparation).

### 7(v) Qiskit 2.5.2 dynamic-circuit support (clone `recon_BCDE/qiskit_252`, tag 2.5.2, commit c1c01ada399a, 2026-08-13)
- `QuantumCircuit` has `if_test`, `if_else`, `switch`, `while_loop`, `for_loop`, `break_loop`, `continue_loop`, `box`, `measure`, `reset`, `add_var`, `add_input` and `add_stretch` (grep of `qiskit/circuit/quantumcircuit.py`). The control-flow ops live in `qiskit/circuit/controlflow/` (`if_else.py`, `switch_case.py`, `while_loop.py`, `for_loop.py`, `box.py`, …). Classical expressions live in `qiskit/circuit/classical/expr` and `…/types`.
- `c_if` is removed. `releasenotes/notes/2.0/remove-deadweight-*.yaml`: "The deprecated method `InstructionSet.c_if` has been removed. This method was deprecated in the 1.3.0 release. This functionality has been superseded by the IfElseOp class…" The same note says the `condition` attribute was removed from the data model.
- Grepping `qiskit/circuit/library/*.py` found no ready-made measurement-based GHZ, W or Dicke builder. Dynamic constructions have to be written by hand with `if_test` / `IfElseOp`.

## 8. HamLib

- Paper: **Sawaya et al., "HamLib: A library of Hamiltonians for benchmarking quantum algorithms and hardware"**, arXiv:**2306.13126** (v5), Quantum 8, 1559 (2024), DOI 10.22331/q-2024-12-11-1559. The abs page lists 16 authors (Sawaya … Klymko, Camps) and the comment "41 pages; small changes in v1.1 of dataset". The abstract says it has "problem sizes ranging from 2 to 1000 qubits."
- Official download, from HTML §1.4 "Availability and dataset structure": "At the time of publication, the HamLib dataset is downloadable from the following URL: https://portal.nersc.gov/cfs/m888/dcamps/hamlib/"
  - Verified today: `curl` returns HTTP 200, an Apache "Index of /cfs/m888/dcamps/hamlib" listing with `binaryoptimization/`, `chemistry/`, `condensedmatter/`, `discreteoptimization/` (all 2024-08-20 16:57), `hamlib.png`, `hamlib_snippets.py` (4.3K, 2024-09-13 19:00; HTTP 200, content-type text/x-python), `readme.txt` (1.7K, 2024-09-24 19:06) and `test/`.
  - `readme.txt` release history: "v1.0: June 2023 — first release" and "v1.1: August 2024". The v1.1 changelog adds "nqubits", "terms" and "one_norm" attributes, CSV summaries, and Qiskit SparsePauliOp support in `hamlib_snippets.py`. It removes the H70/H80 hydrogen chains "due to file corruption", and so on.
  - The files are HDF5 (Appendix A: "Loading HDF5 file structure"), and the HTML example URL shows zip archives (`…/hamlib/test/graph/test_graph.zip`).
- Helper code: Appendix A says the snippets are "also available via: https://portal.nersc.gov/cfs/m888/dcamps/hamlib/hamlib_snippets.py or https://github.com/Azulene-Labs/hamlib_functions". GitHub API for `Azulene-Labs/hamlib_functions`: license Apache-2.0, Python, 8 stars, not archived, default branch `main`. `git ls-remote` HEAD is `b8d847e96c70cfc1dacbbae89551e57c055a3c38`; the last commit was on 2025-03-30T00:17:59Z with message "test push".

---

## Appendix: list of unavailable / unverified items (summary)
- QuantumEvo's TMLR acceptance: OpenReview returned 403 (ChallengeRequired); cannot be verified.
- Building the cirkit/revkit bundled with QuantumEvo: not tested.
- Zhang–Li–Ying divide-and-conquer pebbling (TCAD 2025): no arXiv version and no code; its effect numbers are only second-hand paraphrases.
- Unqomp's arXiv id: unavailable (search returned no results).
- OLSQ2 arXiv version: not found. The IEEE Xplore page returned 202; content not obtained.
- Actual builds of caterpillar / mockturtle: not tested.
- tweedledum 1.2.0 (GitHub master, nanobind version): unreleased and not tested.
- QUBIKOS per-architecture data: only in Figure 4, as an image; cannot be read as a table.
- Gleinig & Hoefler (DAC 2021): no arXiv version; original not read.
- MDPI HTML page for Jang et al. 2021: returned 403; used the PDF instead.
- Several S-box papers had only their titles confirmed, numbers not read: ePrint 2024/381, 2025/1494, 2023/146, 2023/018, 2022/683.
- Fetched files (all in `scratchpad/recon_BCDE/`):
  - `qe_tables16_21.txt`: QuantumEvo full per-function results.
  - `sbox/`, `pdf6/`: PDFs and their text for S-boxes and state preparation.
  - `qiskit_252/`, `qmap_3100/`, `qe_repo/`, `qclib_repo/`: shallow clones.
