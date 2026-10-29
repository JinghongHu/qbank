# qbank Phase-0 recon — Category A (CSS logical-|0…0⟩ state preparation, 2q-gate count)

- Access date for **every** source below: **2026-09-25** (all fetched in this session via curl / git / WebSearch; nothing recalled from memory).
- Scratch dir (all raw downloads, clones, scripts): `/private/tmp/claude-502/-Users-hjh-PycharmProjects-Qevovle/1f29f559-556e-45a5-8721-319594d33bc5/scratchpad/recon_A/`
- Local verification toolchain: scratch venv with `stim 1.16.0`, numpy, pyyaml, bs4 (arXiv HTML table extraction: `html_tables.py`), openpyxl.
- Convention used when *I* recount a circuit: CX/CZ = 1, SWAP = 3, any other Stim 2-qubit gate reported separately. **Numbers that I computed myself from repo/database files are labelled "[recomputed]"** and are not published numbers.

---

## 0. Critical findings (read first)

1. **MQT QECC `construct_bb_code(90)` does NOT build Bravyi's [[90,8,10]] code.** It passes `(15, 3)` as `(m, l_)` into a helper whose x/y orders are swapped relative to Bravyi's convention, so A = 1+y+y², B = 1+x+x² (after reduction). I built both codes and checked: same k = 8, but the MQT code has a **weight-2 Z-logical (qubits {45,60})** → d = 2; Bravyi's Table-3 code has no logical of weight ≤ 4 (consistent with d = 10). [recomputed; `bb_check.py`, `bb_check2.py`]. For n = 72 the MQT code is identical to Bravyi's (identical rowspaces, computed). For 108/144 the MQT matrices differ from Bravyi's as written, but by an algebraic argument (reordering the tensor factors maps MQT's x,y to Bravyi's y,x; for these symmetric polynomial pairs this just swaps A↔B, i.e. the left/right qubit blocks) they are the same code up to qubit permutation — argued, not computed; a low-weight search found no logical of weight ≤ 3 in QECirc's 108-8-10/144-12-12 either.
   - Consequences: (a) StabilizerBench's "BB Code n=90" (labelled d=10) is exactly the MQT code → actually d = 2. (b) QECirc code `90-8-10` ("Bivariate Bicycle Code", linked to arXiv:2605.15266) has weight-2 Z- and X-logicals → d = 2; QECirc separately hosts `90-8-10-autqec` ("Bivariate Bicycle Code (Bravyi Table 3)"), which has no logical of weight ≤ 3. (c) The `[[90,8,10]]` rows of arXiv:2605.15266 Tables 1–6 were produced on the MQT code: the released circuits `mqt-qecc/scripts/encoding_circuits/best_circuits/90_8_10/*.stim` stabilise the MQT check matrices and **not** Bravyi's (verified with stim). **So there is, as far as I found, no published |0_L⟩ count for the genuine Bravyi [[90,8,10]] code.**
2. **StabilizerBench (arXiv:2604.21287v1) is not a |0_L⟩ benchmark**: B1/B2 validity only checks that the output is a +1 eigenstate of the given stabilizer generators (codespace prep; logical state unconstrained). Its 2q metric counts only `CX/CZ/SWAP` target pairs (SWAP = 1) and treats every other Stim 2-qubit gate (SPP, SQRT_XX, CXSWAP, XCX, …) as 1-qubit ops; the repo's own B2 run logs contain "valid" circuits with 0 counted 2q gates (e.g. Steane via `SPP`/`SQRT_XX_DAG`). The BB-code baseline circuits are empty strings. The 168 "tensor-product" instances are actually **concatenations** in the released data. Details §1.
3. **QECirc** (arXiv:2609.20182 / qecirc.com) is the best machine-readable source of verified |0_L⟩/|+_L⟩ circuits: 968 circuits, bulk-downloadable from GitHub (`qecirc/qecirc-website`, data in `data_yaml/`, **data licence CC BY-SA 4.0**, code MIT) and via a JSON API. Its `two_qubit_gate_count` treats **SWAP as free** (CXSWAP counts 1) — must be recounted for our swap=3 rule. Per-code minima table §2.4.
4. Best published |0_L⟩ numbers found (all-to-all, unitary, non-FT): Steane 8, rot. surface d3 8 (SAT-optimal in CNOT-only model), Carbon 16, [[15,1,3]] 22, [[15,7,3]] 22, [[17,1,5]] 23, [[19,1,5]] 27, Golay **44** (QuSynth, arXiv:2603.17743), rot. surface d5 28, [[31,1,7]] 45, [[37,1,7]] 57, [[31,21,3]] 52, [[30,6,5]] 61, BB72 150, Gross **330** (arXiv:2605.15266), full table §9.
5. Held-out family candidates that reach n ≥ 100: **many-hypercube** (Goto, arXiv:2403.16054v3: [[6^L,4^L,2^L]], L=3 → [[216,64,8]] printed in the paper), Knill **C4/C6 (Carbon) family** (Goto quotes N=4·3^{L−1}, K=1 (or 2), D=2^L → n=108 at L=4, derived), **Iceberg** [[k+2,k,2]] (any even k, but |0̄⟩^{⊗k} is a GHZ state → trivial optimum). Details §8.

---

## 1. StabilizerBench — arXiv:2604.21287 + github.com/uw-math-ai/quantum-ai

### 1.1 Identity
| Field | Value (as fetched) |
|---|---|
| Title | "StabilizerBench: A Benchmark for AI-Assisted Quantum Error Correction Circuit Synthesis" |
| Authors | Andres Paz, Christian Tarta, Cordelia Yuqiao Li, Mayee Sun, Sarju Patel, Sylvie Lausier (Univ. of Washington) |
| arXiv | 2604.21287**v1** (only version), submitted Thu 23 Apr 2026; licence arXiv non-exclusive-distrib 1.0; PDF sha256 `6b7933f0…536f91` |
| Repo | https://github.com/uw-math-ai/quantum-ai (URL printed in the paper) |
| Repo HEAD | `93208e3468d2aa217dfe645bead0fb963cd8b279` ("rename script", 2026-09-11 08:51:07 −0700; matches `git ls-remote HEAD`) |
| Licence | **None.** No LICENSE file in the tree; GitHub API `license: null`, `/license` → 404. (→ all rights reserved by default; do not redistribute its data.) |

Inconsistency: arXiv abstract page says "192 stabilizer codes spanning **12** families"; the PDF abstract/introduction and the repo README say "**14** families"; Table I lists 6 families + "Other".

### 1.2 Code suite (paper §III-B, Table I) and what the data actually contains
Paper: "24 base codes spanning six families: rotated surface codes (d ∈ {3,5,7}), color codes (hexagonal and square-octagon, d ∈ {3,5,7}), Iceberg codes (m ∈ {2,3,4}), many-hypercube codes (ℓ ∈ {1,2}), bivariate bicycle (BB) codes (n ∈ {72,90}), and … Perfect 5-Qubit, Steane, Hamming, and Golay, Shor, Tetrahedral, Carbon, and 4-Qubit Detector codes." "The remaining 168 circuits are **tensor products** of pairs of base codes, constructed by taking the joint stabilizer group of two independent subsystems." Total generators K = 16,340.

Paper Table I (raw): Rotated Surface 3 codes, stabilizer range 8–48; Color (Hex+Sq-Oct) 6, 6–36; Iceberg 3, 2–2; Hypercube 2, 2–20; BB (LDPC) 2, 72–90; Other 8, 2–22; Total base 24, 2–90; Tensor products 168, 18–194; Total 192, 2–194.

File format: `data/benchmarks.json` (sha256 `883a1dd5…7c011`), a JSON list of 192 objects `{name, physical_qubits, logical_qubits, d, generators}`; generators are **Pauli strings** (e.g. `"XZZXI"`). Baselines are in `data/circuit_dataset.jsonl` (sha256 `240ee350…c7ee52`): 192 lines `{source_code, d, permutation, input_stabilizers, output_circuit}` with **Stim** circuit text. Codes were generated with `mqt.qecc` (`data/generate_code.py`).

The 24 base codes as stored (n, k, d from the JSON; #gens = number of generator strings; all but the 5-qubit code are given in CSS form) — plus **[recomputed]** baseline 2q count of the shipped B2 baseline (Stim `Tableau.to_circuit(method="elimination")`), using the repo's own `circuit_metric.py`:

| name (as in JSON) | [[n,k,d]] | #gens | baseline 2q [recomputed] (all CX) | baseline depth (repo metric) |
|---|---|---|---|---|
| Perfect 5-Qubit Code | [[5,1,3]] | 4 | 19 | 22 |
| Steane | [[7,1,3]] | 6 | 23 | 21 |
| Shor | [[9,1,3]] | 8 | 23 | 18 |
| Tetrahedral | [[15,1,3]] | 14 | 52 | 27 |
| Hamming | [[15,7,3]] | 8 | 65 | 29 |
| Carbon | [[12,2,4]] | 10 | 62 | 50 |
| Golay | [[23,1,7]] | 22 | 174 | 132 |
| BB Code n=72 | [[72,12,6]] | 72 (rank 60 → redundant) | **0 (empty baseline)** | 0 |
| BB Code n=90 | [[90,8,10]] (**actual d = 2**, see §0) | 90 (rank 82 → redundant) | **0 (empty baseline)** | 0 |
| Iceberg Code m=2 | [[4,2,2]] | 2 | 5 | 5 |
| Iceberg Code m=3 | [[6,4,2]] | 2 | 9 | 7 |
| Iceberg Code m=4 | [[8,6,2]] | 2 | 13 | 9 |
| Hypercube Code l=1 | [[6,4,2]] | 2 | 9 | 7 |
| Hypercube Code l=2 | [[36,16,4]] | 20 | 249 | 102 |
| Hex Color Code d=3 | [[7,1,3]] | 6 | 17 | 17 |
| Hex Color Code d=5 | [[19,1,5]] | 18 | 102 | 68 |
| Hex Color Code d=7 | [[37,1,7]] | 36 | 208 | 94 |
| Square Octagon Color Code d=3 | [[7,1,3]] | 6 | 19 | 13 |
| Square Octagon Color Code d=5 | [[17,1,5]] | 16 | 88 | 64 |
| Square Octagon Color Code d=7 | [[31,1,7]] | 30 | 192 | 106 |
| Rotated Surface Code d=3 | [[9,1,3]] | 8 | 19 | 15 |
| Rotated Surface Code d=5 | [[25,1,5]] | 24 | 104 | 59 |
| Rotated Surface Code d=7 | [[49,1,7]] | 48 | 257 | 129 |
| 4-Qubit Detector Code | [[4,2,2]] | 2 | 5 | 5 |

Observations [recomputed]:
- **BB baselines are empty**: `generate_naive_circuit` calls `stim.Tableau.from_stabilizers(..., allow_redundant=False)`, which fails on the redundant BB generator lists and the exception returns `""`. Only these 2 of 192 entries are empty.
- **Duplicates**: "Iceberg Code m=3" ≡ "Hypercube Code l=1" (identical stabilizer groups); "4-Qubit Detector Code" ≡ "Iceberg Code m=2" (identical); Hex d=3 and Sq-Oct d=3 have the same X-group weight enumerator as Steane (both are the [[7,1,3]] code up to qubit relabelling, not identical qubit order).
- **The 168 non-base instances are concatenations, not tensor products.** `data/generate_code.py::generate_concatenated_codes(outer, inner)` replaces each outer qubit by an inner (k=1) block; the JSON confirms this, e.g. `(Perfect 5-Qubit Code) * (Perfect 5-Qubit Code)` = [[25,1,9]], `(4-Qubit Detector Code) * (Rotated Surface Code d=7)` = [[196,2,14]]. Distance is set by formula `ceil(d_out/k_in)*d_in`, not computed. Outer codes used: all 24 base codes except BB and a few large ones; inner codes: 14 k=1 codes (5-qubit, Steane, Shor, Tetrahedral, Golay, Hex/SqOct color d=3,5,7, rot. surface d=3,5,7). 81 of 192 instances have n ≥ 100. `generate_code.py` also constructs Hypercube l=3 (n=216) but it is dropped by the `n < 200` filter.
- Note: MQT QECC HEAD's `CSSCode.from_code_name` supports only Steane/Tetrahedral/Shor/Golay/Carbon (no "Hamming"), so `generate_code.py` does not run unmodified against MQT HEAD; the committed JSON must have been produced with a different version/script state (it also contains the "4-Qubit Detector Code", which is commented out in the current script).

### 1.3 Task definitions (paper §III-D; repo)
- **B1 State-preparation**: input = k Pauli generators; output = Stim circuit on n qubits from |0⟩^⊗n; valid iff output is a +1 eigenstate of every generator (Stim tableau simulator, `tools/check_stabilizers.py`). → **codespace preparation; the logical state is NOT fixed** (for k ≥ 1 any codeword passes). The checker pads stabilizers with I to the circuit width, so extra ancilla qubits are not rejected.
- **B2 Circuit optimization**: input = baseline Stim circuit C_base (the Gaussian-elimination circuit above) + generators; valid iff all generators preserved; paper: strict improvement in lexicographic (G2Q, D) with "G2Q … total count of multi-qubit entangling gates (CX, CZ, SWAP, etc.)"; quality q_i = 0.75 Δ_G2Q + 0.25 Δ_D. Repo HEAD compares `(two_qubit_gates, volume, depth)` (3-tuple incl. "volume") in `tools/circuit_metric.py` / `B2/run.py`.
  - **Metric loophole [recomputed]**: `compute_metrics` expands only `CX/CZ/SWAP` into pairs (SWAP counted as 1); all other gates are expanded per qubit target and counted as one-qubit gates. Best "valid" B2 outputs in the repo's own run logs (`B2/data/**.json`) with that metric report **0 two-qubit gates** for Steane (gates SPP, SQRT_XX_DAG, …), Shor, Iceberg, Hex d=3, Rot. surface d=3 etc.
  - If I restrict to circuits whose only 2q gates are CX/CZ/SWAP (SWAP=3) and re-verify with stim, the best codespace-prep counts found in the repo's B2 logs [recomputed, **codespace only, not |0_L⟩**, not published]: 5-qubit 5; Steane 8; Shor 6; Tetrahedral 22; Hamming 18; Carbon 15; Golay 72; Iceberg m=2/3/4: 2/3/4; Hypercube l=1: 3, l=2: 59; Hex d=3/5/7: 8/34/164; SqOct d=3/5/7: 8/25/77; Rot. surface d=3/5/7: 8/28/60; 4-qubit detector 2; BB: none (no baseline).
- **B3 FT generation**: add flag qubits; FT score = fraction of dangerous single faults (weight > ⌊(d−1)/2⌋) flagged. Not relevant to our main track.
- **Per-code gate counts in the paper**: unavailable — the paper reports only aggregate capability/quality scores (Tables II–IV: e.g. B1 S_cap Claude 1 att/900 s = 10,772; B2 Claude 15 att/900 s S_cap 9,186, S_qual 2,911, mean G2Q↓ 66.4 %), no per-code gate-count table.

---

## 2. QECirc — arXiv:2609.20182 + qecirc.com

### 2.1 Identity
| Field | Value |
|---|---|
| Title | "QECirc: A Community-Driven, FAIR Library of Quantum Error Correction Circuits" |
| Authors | Ludwig Schmid, Tom Peham, Robert Wille (TUM; "on behalf of the QECirc contributors") |
| arXiv | 2609.20182**v1**; abs page: "[v1] Mon, 27 Jul 2026 18:00:01 UTC (7 KB)"; comment "2 pages extended abstract"; PDF sha256 `b88edeeb…ea91fba` |
| Site | https://qecirc.com (Astro site, "α"/alpha; README: "functionality, URLs, permalinks, and circuit data may change without notice") |
| Backing repo | https://github.com/qecirc/qecirc-website — HEAD `4dd1879657f5ae45129ca9fa5b16eaa56b553e42` (2026-09-20, "chore(deps) Update dependency js-yaml to v5.4.2 (#201)"; = `ls-remote` main) |
| Licences | Code: **MIT** (`LICENSE`, "Copyright (c) 2025 QECirc Contributors"; GitHub API `mit`). Data in `data_yaml/`: **CC BY-SA 4.0** (`LICENSE-DATA`). The website's /legal page (TUM Impressum, German) has generic "Nutzungsbedingungen" requiring consent for reuse of site material — conflicts with the repo licence; safest is to take data from GitHub under CC BY-SA 4.0 (ShareAlike: any redistributed derivative dataset must also be CC BY-SA). The paper says "openly licensed". |

### 2.2 What it hosts / metadata / formats (paper + repo)
- Paper: each circuit is attached to a code and a task: "encoding, logical Pauli-eigenstate preparation, fault-tolerant flag gadgets, or logical Clifford gates"; records "provenance (the generating tool and originating paper), computed metrics such as qubit count, depth, and two-qubit gate count, plus connectivity and device tags". Export "to Stim or OpenQASM" + Crumble/Quirk links. Ingestion "checks that encoders map the all-zero input into the code space and that state preparations satisfy every stabilizer and prepare the claimed logical basis state". Codes carry stabilizer (h) and logical check matrices, canonicalised.
- Repo data (HEAD above): `data_yaml/codes/*.yaml` (82 files: name, n, k, d, aliases, zoo_url, canonical_hash, `h` = (n−k)×2n symplectic [X|Z], `logical` = 2k×2n with top k X̄ rows, bottom k Z̄ rows for CSS; large ones stored sparse), `data_yaml/circuits/*.{yaml,stim,qasm,stim-annotated}` (968 each), `data_yaml/circuits/originals/`, `data_yaml/matrices/`, `papers/`, `tools/`. Circuit YAML fields: `qec_id, name, tool, source, notes, gate_count, two_qubit_gate_count, depth, qubit_count, quirk_url, tags, original_matrices`.
- Tags counts (all 968 circuits): ft 449, flag 439, state-preparation 395, logical-state:zero 313, gadget 294, non-ft 286, syndrome-extraction 155, encoding 86, logical-state:plus 70, connectivity:all-to-all 16, …
- **Metric semantics** (`scripts/add_circuit/circuit_validate.py`): `two_qubit_gate_count` = number of unitary two-qubit gate applications **excluding SWAP** ("A plain SWAP is a qubit relabeling — free AOD routing … NOT counted"); CXSWAP/ISWAP count 1. `depth` = **two-qubit (entangling) depth**, using the circuit's TICK layers if present, else greedy ASAP. `gate_count` = all non-SWAP unitary gates.
- Export formats: Stim, **OpenQASM 2.0** (the `qasm` body fetched for qec_id 88 starts `OPENQASM 2.0;`), stim-annotated (with R/M/DETECTOR/OBSERVABLE_INCLUDE).

### 2.3 Bulk access / API (verified live)
- `GET https://qecirc.com/api/circuits?ids=<comma list>` → JSON array `{qec_id, name, slug, code_name, code_slug, gate_count, two_qubit_gate_count, depth, qubit_count, tags}`; max 2000 ids per request (`X-Id-Limit: 2000`, `X-Truncated`). I fetched ids 1..2000 → 968 records, max qec_id 1298. **Saved raw**: `recon_A/qecirc/qecirc_api_circuits_ids1-2000.json`, **sha256 `07dd309f71863065b5750fc38a7197d2ea5a95686e9fc4286f7e7266eab5e118`** (headers in `qecirc/api_headers.txt`). All 968 `two_qubit_gate_count` values match the GitHub YAMLs (0 mismatches).
- `GET /api/circuits/<qec_id>/bodies` → `{"bodies":[{format:"stim"|"qasm"|"stim-annotated", body}]}` (tested on 88); `/api/circuits/<id>/originals`; `GET /api/codes/<slug>/matrices` → `{n,k,h,logical,…}`; `GET /api/download?code=<slug>` → zip of Stim files (tested `steane-code`: HTTP 200, application/zip, 20,208 B).
- Simplest bulk path: `git clone --depth 1 https://github.com/qecirc/qecirc-website` (all circuits + matrices).

### 2.4 |0_L⟩ / |+_L⟩ / encoder minima per code [recomputed from QECirc data, independently verified]
Method (`qecirc_analyze.py`; output `qecirc/qecirc_prep_enc_analysis.json`, table `qecirc/qecirc_min_table.txt`): for every circuit tagged `state-preparation` that is unitary (initial `R`/`RX` resets allowed) and acts on exactly n qubits, simulate with stim and check (i) every row of the code's `h` has deterministic ±1 expectation (sign-tolerant, as QECirc's own stored frames are arbitrary), (ii) all Z̄ (for |0_L⟩) or X̄ (for |+_L⟩) rows of `logical` are deterministic. "ours" = CX+CZ+3·SWAP (+other 2q). All listed minima pass (i)+(ii) except the non-CSS Gottesman code where my CSS-ordering assumption for `logical` doesn't apply.

| code_slug | name | [[n,k,d]] | min |0_L⟩ ours [QECirc 2q] (2q-depth; qec_id; tool) | min |+_L⟩ ours [QECirc] | min encoder ours [QECirc] |
|---|---|---|---|---|---|---|
| 4-2-2 | Iceberg | [[4,2,2]] | 5 [5] (4; 1145; qldpc naive tableau) | – | 14 [14] |
| five-qubit-code | 5-qubit | [[5,1,3]] | 6 [6] (4; 320; rlftqc) | – | 15 [6] (3 SWAPs) |
| 6-2-2 | "Iceberg Code" (as labelled) | [[6,2,2]] | 16 [16] (qldpc naive) | – | 22 [22] |
| steane-code | Steane | [[7,1,3]] | 8 [8] (3; 190; circuit-synth) | 8 [8] (3; 441; mqt-qecc) | 9 [9] |
| gottesman-8-3-3-code | Gottesman | [[8,3,3]] | 22 [10] (4 SWAPs; 174) | – | 23 [14] |
| 9-1-3 | Bacon-Shor | [[9,1,3]] | 22 [22] (qldpc naive) | – | 34 [34] |
| rotated-surface-code-d-3 | rot. surface | [[9,1,3]] | 8 [8] (3; 113; circuit-synth) | 8 [8] | 9 [9] |
| shor-code | Shor | [[9,1,3]] | 8 [8] (4; 92) | 6 [6] (2; 448) | 8 [8] |
| carbon-code | Carbon | [[12,2,4]] | 16 [16] (4; 100) | – | 18 [18] |
| unrotated-surface-code-d-3 | unrot. surface | [[13,1,3]] | 14 [14] (6; 1026; direct-zero-prep) | 14 [14] | 60 [60] |
| 15-7-3 | q. Hamming | [[15,7,3]] | 22 [22] (4; 105) | 22 [22] | 27 [27] |
| tetrahedral-code | tetrahedral | [[15,1,3]] | 22 [22] (4; 97) | 23 [23] | 24 [24] |
| 16-1-4-bacon-shor | Bacon-Shor | [[16,1,4]] | 46 [46] (qldpc naive) | – | 69 [69] |
| 16-2-4-toric | toric | [[16,2,4]] | 60 [60] (qldpc naive) | – | 74 [74] |
| 17-1-5 | 4.8.8 color | [[17,1,5]] | 23 [23] (4; 137) | 23 [23] | 24 [24] |
| 19-1-5 | 6.6.6 color | [[19,1,5]] | 27 [27] (4; 495) | 27 [27] | 28 [28] |
| 23-1-7 | Golay | [[23,1,7]] | 44 [44] (8; 108; circuit-synth) | 57 [57] | 47 [47] |
| rotated-surface-code-d-5 | rot. surface | [[25,1,5]] | 28 [28] (4; 117) | 28 [28] | 29 [29] |
| 30-6-5 | [[30,6,5]] | [[30,6,5]] | 62 [62] (9; 148) | 68 [68] | 82 [82] |
| 31-1-7 | 4.8.8 color | [[31,1,7]] | 45 [45] (7; 140) | 46 [46] | 46 [46] |
| 31-21-3 | q. Hamming | [[31,21,3]] | 52 [52] (5; 153) | 52 [52] | 82 [82] |
| 36-2-6 | toric | [[36,2,6]] | 177 [177] (qldpc naive) | – | 182 [182] |
| 37-1-7 | 6.6.6 color | [[37,1,7]] | 58 [58] (8; 144) | 59 [59] | 61 [61] |
| unrotated-surface-code-d-5 | unrot. surface | [[41,1,5]] | 52 [52] (12; 1030) | 52 [52] | – |
| 49-9-4 | SHYPS | [[49,9,4]] | 285 [285] (qldpc naive) | – | 294 [294] |
| rotated-surface-code-d-7 | rot. surface | [[49,1,7]] | 60 [60] (18; 1014) | 60 [60] | 345 [345] |
| 58-16-3 | HGP | [[58,16,3]] | 350 [350] (qldpc naive) | – | 382 [382] |
| 72-12-6 | BB | [[72,12,6]] | 150 [150] (9; 125) | 214 [214] | 221 [221] |
| rotated-surface-code-d-9 | rot. surface | [[81,1,9]] | 104 [104] (24; 1018) | 104 [104] | – |
| unrotated-surface-code-d-7 | unrot. surface | [[85,1,7]] | 114 [114] | 114 [114] | – |
| 90-8-10 | "BB" (**actually d=2**, §0) | [[90,8,10]] | 137 [137] (10; 156) | 147 [147] | 171 [171] |
| 108-8-10 | BB | [[108,8,10]] | 263 [263] (24; 160; circuit-synth) | 460 [460] | 516 [516] |
| rotated-surface-code-d-11 | rot. surface | [[121,1,11]] | 160 [160] (30; 1022) | 160 [160] | – |
| 144-12-12 | Gross | [[144,12,12]] | 395 [395] (35; 164; circuit-synth) | 330 [330] | 814 [814] |
| unrotated-surface-code-d-9 | unrot. surface | [[145,1,9]] | 200 [200] | 200 [200] | – |
| unrotated-surface-code-d-11 | unrot. surface | [[221,1,11]] | 310 [310] | 310 [310] | – |
| 241-121-3 | HGP | [[241,121,3]] | 2126 [2126] (qldpc naive) | – | 1911 [1911] |

Notes: the `direct-zero-prep` surface-code circuits match exactly the Colmenarez et al. formulas (§6.4). `qldpc` "tableau-0-preparation" circuits are naive (unoptimised) and should not be treated as competitive references. Codes with only FT preps (flags + measurements; not comparable): [[11,1,3]] 38, [[16,2,4]] 67, [[16,6,4]] 59 (mqt-qecc det-FT), [[20,2,6]] 145, [[47,1,11]] 1033, [[49,1,5]] 361 (|+⟩), [[49,1,9]] 408, [[71,1,11]] 829, [[95,1,7]] 1175 (|+⟩) (flag-at-origin), QECirc 2q counts.
QECirc has **no** many-hypercube, generalized-bicycle, or quantum-Reed–Muller-beyond-15 prep circuits; BB 288/360/756 and other qLDPC entries have syndrome-extraction only (full code list with task counts: `qecirc/qecirc_codes_list.txt`).

---

## 3. arXiv:2605.15266 — "Synthesis and Optimization of Encoding Circuits for Fault-Tolerant Quantum Computation"

- Authors: **Tom Peham, Matthew Steinberg, Robert Wille, Sascha Heußen**. v1 only (Thu 14 May 2026). "33 pages, 11 figures". PDF sha256 `c702ff5c…c8b3b8`. Tables read from arXiv HTML v1.
- Setting: greedy + rollout search over stabilizer tableaus (gate set {S,H,CX} for the formalism); SMT exact synthesis for small local isometries; codes: 2D/3D colour, quantum Hamming, Golay, [[30,6,5]] symplectic double (Kanomata–Goto), BB codes; non-CSS [[8,3,3]] Gottesman and [[15,3,5]]. Compared with Rustiq. "G = two-qubit gate count, D = circuit depth". All-to-all. Non-FT.
- Release: "all methods are openly available as part of the Munich Quantum Toolkit" (no separate URL in the paper). **Circuits are released** in `github.com/munich-quantum-toolkit/qecc` at `scripts/encoding_circuits/best_circuits/<n_k_d>/{encoder,zero,plus}_{optgates,optdepth}.stim` (MQT HEAD `accd7be9c93d6dc777ebfd9d36263250e5350746`, MIT). I recounted all 90 files: CX counts equal the table values; the CSS circuits use R/RX init + CX only; **the non-CSS circuits contain SWAPs that are not counted in G** (e.g. [[8,3,3]] zero_optgates: 11 CX + 5 SWAP → 26 under swap=3; [[15,3,5]] zero_optgates: 36 CX + 11 SWAP). I verified the BB zero circuits prepare |0⟩_L^{⊗k} (all Z operators in ker H_X have +1 expectation) of the *MQT* codes; for 90_8_10 this is the d=2 code (§0).
- QECirc hosts some of them (tool `circuit-synth` / `mqt-qecc`, source arXiv:2605.15266).

**Table 1 (raw): "Best depth-optimized circuits for each synthesis task." (G, D) — Encoder Ours | Encoder RustiQ | Zero Ours | Zero RustiQ | Plus Ours | Plus RustiQ**
| Code | Enc Ours | Enc RustiQ | Zero Ours | Zero RustiQ | Plus Ours | Plus RustiQ |
|---|---|---|---|---|---|---|
| [[8,3,3]] | 14,5 | 19,7 | 13,5 | 11,4 | 9,5 | 12,5 |
| [[15,1,3]] | 24,4 | 25,6 | 22,4 | 24,5 | 23,4 | 25,4 |
| [[15,3,5]] | 43,10 | 51,9 | 45,10 | 36,7 | 41,9 | 35,7 |
| [[15,7,3]] | 31,6 | 49,15 | 22,4 | 24,6 | 22,4 | 23,5 |
| [[17,1,5]] | 25,5 | 25,5 | 23,4 | 24,4 | 23,4 | 24,5 |
| [[19,1,5]] | 29,5 | 34,6 | 27,4 | 33,6 | 27,4 | 30,5 |
| [[23,1,7]] | 53,8 | 55,8 | 57,7 | 58,7 | 57,7 | 62,7 |
| [[30,6,5]] | 95,9 | 109,15 | 68,7 | 80,8 | 68,7 | 81,7 |
| [[31,1,7]] | 48,5 | 50,7 | 46,4 | 52,6 | 46,4 | 48,6 |
| [[31,21,3]] | 109,11 | 194,37 | 52,5 | 56,7 | 52,5 | 58,8 |
| [[37,1,7]] | 63,6 | 68,6 | 59,5 | 70,6 | 59,5 | 74,7 |
| [[72,12,6]] | 261,19 | 383,24 | 223,9 | 273,12 | 214,9 | 251,10 |
| [[90,8,10]] ⚠ | 183,12 | 242,14 | 147,8 | 178,8 | 147,8 | 180,8 |
| [[108,8,10]] | 667,24 | 634,23 | 548,15 | 597,16 | 460,14 | 592,16 |
| [[144,12,12]] | 1081,29 | 856,26 | 687,15 | 749,14 | 330,16 | 740,15 |

**Table 2 (raw): "Best gate-optimized circuits for each synthesis task."**
| Code | Enc Ours | Enc RustiQ | Zero Ours | Zero RustiQ | Plus Ours | Plus RustiQ |
|---|---|---|---|---|---|---|
| [[8,3,3]] | 12,8 | 15,10 | 11,8 | 10,7 | 9,5 | 9,5 |
| [[15,1,3]] | 24,5 | 24,9 | 22,5 | 22,12 | 23,5 | 23,9 |
| [[15,3,5]] | 36,11 | 35,16 | 36,13 | 28,8 | 31,12 | 27,13 |
| [[15,7,3]] | 28,7 | 46,23 | 22,5 | 22,7 | 22,5 | 23,13 |
| [[17,1,5]] | 25,5 | 24,7 | 23,4 | 25,7 | 23,4 | 24,9 |
| [[19,1,5]] | 29,6 | 32,10 | 27,4 | 30,15 | 27,4 | 30,11 |
| [[23,1,7]] | 49,10 | 54,32 | 45,10 | 52,24 | 45,10 | 50,24 |
| [[30,6,5]] | 82,13 | 84,29 | 61,11 | 71,28 | 62,11 | 71,27 |
| [[31,1,7]] | 47,6 | 53,16 | 45,5 | 51,20 | 45,5 | 52,15 |
| [[31,21,3]] | 94,18 | 153,45 | 52,8 | 52,13 | 52,8 | 55,35 |
| [[37,1,7]] | 60,8 | 69,21 | 57,6 | 68,27 | 57,6 | 66,17 |
| [[72,12,6]] | 239,40 | 273,48 | 150,14 | 202,61 | 150,15 | 214,73 |
| [[90,8,10]] ⚠ | 178,23 | 193,46 | 134,21 | 144,26 | 135,21 | 185,54 |
| [[108,8,10]] | 367,62 | 448,132 | 402,58 | 446,133 | 378,49 | 457,136 |
| [[144,12,12]] | 544,110 | 775,224 | 330,39 | 581,134 | 330,32 | 578,166 |

**Tables 3–6 (raw)** — rollout study. Columns: Greedy (G, D, t, ET) | Rollout 1 (G, ΔG%, D, ΔD%) | (t1,t2), ET | Rollout 2 (G, ΔG%, D, ΔD%).
- Table 3 (depth-optimized encoders): [[8,3,3]] 15,6,10,n | 14,6.7,5,16.7 | 10,2,y | 14,6.7,5,16.7 · [[15,1,3]] 24,4,10,y | 24,0,4,0 | 10,2,y | 24,0,4,0 · [[15,3,5]] 53,12,10,n | 45,15.1,10,16.7 | 40,20,y | 43,18.9,10,16.7 · [[15,7,3]] 36,9,30,n | 33,8.3,7,22.2 | 30,15,y | 31,13.9,6,33.3 · [[17,1,5]] 25,5,10,y | 25,0,5,0 | 10,2,y | 25,0,5,0 · [[19,1,5]] 29,6,10,n | 29,0,5,16.7 | 10,2,n | 29,0,5,16.7 · [[23,1,7]] 63,9,100,n | 53,15.9,8,11.1 | 50,25,y | 55,12.7,8,11.1 · [[30,6,5]] 99,13,100,n | 92,7.1,10,23.1 | 30,6,n | 95,4.0,9,30.8 · [[31,1,7]] 48,6,10,y | 48,0,6,0 | 50,25,y | 48,0,5,16.7 · [[31,21,3]] 127,23,10,n | 109,14.2,11,52.2 | 20,4,n | 112,11.8,12,47.8 · [[37,1,7]] 65,8,40,y | 63,3.1,7,12.5 | 30,6,n | 63,3.1,6,25.0 · [[72,12,6]] 274,33,50,n | 261,4.7,19,42.4 | 50,10,y | 268,2.2,20,39.4 · [[90,8,10]] 187,20,50,n | 183,2.1,12,40.0 | 10,2,n | 187,0.0,12,40.0 · [[108,8,10]] 750,30,100,y | 724,3.5,24,20.0 | 40,8,y | 667,11.1,24,20.0 · [[144,12,12]] 798,83,200,y | 1081,−35.5,29,65.1 | 20,10,y | 700,12.3,70,15.7
- Table 4 (gate-optimized encoders): [[8,3,3]] 13,7,10,n | 13,0.0,6,14.3 | 40,8,y | 12,7.7,8,−14.3 · [[15,1,3]] 24,10,20,n | 24,0,6,40.0 | 10,2,n | 24,0,5,50.0 · [[15,3,5]] 48,25,20,n | 39,18.8,12,52.0 | 30,6,n | 36,25.0,11,56.0 · [[15,7,3]] 35,18,20,n | 31,11.4,8,55.6 | 50,10,n | 28,20.0,7,61.1 · [[17,1,5]] 25,7,10,y | 25,0,7,0 | 10,5,n | 25,0,5,28.6 · [[19,1,5]] 30,13,30,y | 29,3.3,7,46.1 | 20,10,n | 29,3.3,6,53.9 · [[23,1,7]] 57,27,50,n | 50,12.3,13,51.9 | 40,8,n | 49,14.0,10,63.0 · [[30,6,5]] 101,29,200,n | 85,15.8,18,37.9 | 30,15,n | 82,18.8,13,55.2 · [[31,1,7]] 49,13,30,n | 47,4.1,8,38.5 | 20,10,n | 47,4.1,6,53.9 · [[31,21,3]] 125,47,200,n | 100,20.0,20,57.5 | 50,25,n | 94,24.8,18,61.7 · [[37,1,7]] 61,14,30,n | 61,0,10,28.6 | 20,4,n | 60,1.6,8,42.9 · [[72,12,6]] 262,88,40,n | 241,8.0,40,54.5 | 10,5,n | 239,8.8,40,54.5 · [[90,8,10]] 179,36,40,n | 179,0,24,33.3 | 20,4,n | 178,0.6,23,36.1 · [[108,8,10]] 625,107,50,n | 367,41.3,62,42.1 | 40,20,y | 371,40.6,97,9.3 · [[144,12,12]] 682,152,40,n | 544,20.2,110,27.6 | 20,4,y | 556,18.5,157,−3.3
- Table 5 (depth-optimized state prep; G,D of Greedy | Rollout1 | Rollout2) |0⟩_L^{⊗k} rows: [[8,3,3]] 15,6 | 13,5 | 13,5 · [[15,1,3]] 22,4 | 22,4 | 22,4 · [[15,3,5]] 57,16 | 45,10 | 43,11 · [[15,7,3]] 22,4 | 22,4 | 22,4 · [[17,1,5]] 23,4 | 23,4 | 23,4 · [[19,1,5]] 27,5 | 27,4 | 27,4 · [[23,1,7]] 63,9 | 54,8 | 57,7 · [[30,6,5]] 77,8 | 68,7 | 68,7 · [[31,1,7]] 46,5 | 46,5 | 46,4 · [[31,21,3]] 54,6 | 52,5 | 52,5 · [[37,1,7]] 60,5 | 60,5 | 59,5 · [[72,12,6]] 150,11 | 223,9 | 150,10 · [[90,8,10]] 151,10 | 147,8 | 148,8 · [[108,8,10]] 584,24 | 548,15 | 584,23 · [[144,12,12]] 330,17 | 687,15 | 330,17. |+⟩_L^{⊗k} rows: [[8,3,3]] 10,5|9,5|9,5 · [[15,1,3]] 23,5|24,4|23,4 · [[15,3,5]] 48,11|41,9|41,9 · [[15,7,3]] 22,4 ×3 · [[17,1,5]] 23,4 ×3 · [[19,1,5]] 27,5|27,4|27,4 · [[23,1,7]] 63,9|54,8|57,7 · [[30,6,5]] 78,8|68,7|69,7 · [[31,1,7]] 46,5|46,5|46,4 · [[31,21,3]] 54,6|52,5|52,5 · [[37,1,7]] 60,5|60,5|59,5 · [[72,12,6]] 150,11|214,9|150,10 · [[90,8,10]] 150,10|147,8|148,8 · [[108,8,10]] 508,21|460,14|508,20 · [[144,12,12]] 330,17|330,16|330,16.
- Table 6 (gate-optimized state prep) |0⟩_L^{⊗k}: [[8,3,3]] 13,11|13,6|11,8 · [[15,1,3]] 22,11|22,6|22,5 · [[15,3,5]] 54,31|39,12|36,13 · [[15,7,3]] 22,8|22,6|22,5 · [[17,1,5]] 23,7|23,5|23,4 · [[19,1,5]] 27,10|27,5|27,4 · [[23,1,7]] 51,22|46,13|45,10 · [[30,6,5]] 70,17|64,11|61,11 · [[31,1,7]] 46,13|45,6|45,5 · [[31,21,3]] 52,15|52,11|52,8 · [[37,1,7]] 58,13|57,8|57,6 · [[72,12,6]] 150,41|150,21|150,14 · [[90,8,10]] 141,23|134,22|134,21 · [[108,8,10]] 472,78|402,58|472,72 · [[144,12,12]] 330,63|330,39|330,48. |+⟩: [[8,3,3]] 9,6|9,5|9,5 · [[15,1,3]] 23,8|23,7|23,5 · [[15,3,5]] 47,21|34,13|31,12 · [[15,7,3]] 22,8|22,6|22,5 · [[17,1,5]] 23,7|23,5|23,4 · [[19,1,5]] 27,10|27,5|27,4 · [[23,1,7]] 51,22|46,13|45,10 · [[30,6,5]] 70,28|63,12|62,11 · [[31,1,7]] 46,13|45,6|45,5 · [[31,21,3]] 52,15|52,11|52,8 · [[37,1,7]] 58,13|57,8|57,6 · [[72,12,6]] 150,41|150,19|150,15 · [[90,8,10]] 141,52|136,46|135,21 · [[108,8,10]] 425,71|380,39|378,49 · [[144,12,12]] 330,66|330,32|330,38.
- Text claims (raw): "a 49-CNOT general-state encoder for the [[23,1,7]] Golay code, an 82-gate depth-13 encoder for the [[30,6,5]] symplectic double code, and a logical |0⟩^{⊗12} preparation circuit for the [[144,12,12]] bivariate bicycle (BB) code requiring 330 CNOT gates at a depth of 17"; "For the [[23,1,7]] Golay code, we find an encoder using only 45 CNOT gates, a reduction of 19% compared to Ref. [19] and 21% compared to Ref. [73]" (45 = the Zero column of Table 2, so "encoder" here means |0_L⟩ prep); [73] Paetznick–Reichardt "achieves 57 CNOT gates at depth 7"; [30,6,5]: Ref. [35] |+⟩ "67 CNOT gates at a depth of 11", ours "62 gates at a depth of 11 … 68 two-qubit gates at a depth of 7"; [[17,1,5]] encoder: "25 CNOT gates at depth 5, one CNOT more than the encoder from Ref. [10]"; HaPPY 12-qubit [[12,4,2]] encoder: 32 → **20 two-qubit gates at depth 10** (modular exact), vs 48 in Ref. [59]; full rollout 22 (depth 9) / 24 (depth 8).
- **Internal inconsistency**: text says "zero-state preparation circuits for the [[108,8,10]] and [[144,12,12]] … requiring **430** and 330 two-qubit gates", while Table 2 prints **402** for [[108,8,10]] Zero (the released `zero_optgates.stim` has 402 CX). Summary claims "improvements of up to 43% in two-qubit gate count and up to 70% in depth".

---

## 4. arXiv:2603.17743 — "Fast stabilizer state preparation via AI-optimized graph decimation"

- Authors: **Michael Doherty, Matteo Puviani, Jasmine Brewer, Gabriel Matos, David Amaro, Ben Criger, David T. Stephen** (Quantinuum). v1 only (Wed 18 Mar 2026), "25 pages, 22 figures". PDF sha256 `edc6d93d…7dd54f4`.
- Metric: "Two-qubit gate counts (TQGs) and two-qubit circuit depths (TQd)"; gates are CZ and CX (App. H: "if the ending Hadamard gates are pulled through to the beginning of the circuit, all two-qubit gates become CX gates"). Unitary, non-FT, from |0⟩^n. All-to-all. Target states: |0⟩_L (|+⟩_L for the Reed–Muller code).
- Release: **unavailable** — no code/data/GitHub link found in the paper text (grep for github/zenodo/availability returned nothing). Circuits for small codes are only drawn as figures (Figs. 15–22).
- Families of [[36,8,6]], [[40,20,6]] (non-CSS), [[42,12,5]], [[48,6,8]], [[64,12,8]], [[80,8,10]]: **not identified in the fetched text** (no "bicycle"/"hypergraph"/"LDPC" mention). [[144,12,12]] is cited to Bravyi et al.

**Table 1 (raw)** — columns: Code | Graph edges | Baseline (TQGs, TQd) | BeFS | Beam search | RL | QuSynth. Superscripts: 1 = Ref. [45] (Peham et al. PRX Quantum 6, 020330 = arXiv:2408.11894), 2 = Ref. [5] (Webster et al.), 3 = CZ-only graph-state prep with LC optimisation; a/b = random/min-degree tie-breakers; * = improved by post-hoc compilation; ‡ = decimation of an LC-optimised graph; "+1" = depth may be 1 higher (graph colouring).
| Code | edges | Baseline | BeFS | Beam | RL | QuSynth |
|---|---|---|---|---|---|---|
| [[9,1,3]] Surface | 10 | (8, 3)¹ | (8, 3)ᵃ | – | – | – |
| [[12,2,4]] Carbon | 21 | (16, 5)¹ | (16, 4)ᵃ | – | – | – |
| [[15,1,3]] Reed-Muller (|+⟩_L) | 32 | (23, 5)¹ | (23, 4)ᵃ | – | – | – |
| [[15,7,3]] Hamming | 28 | (22, 4)¹ | (22, 4)ᵃ | – | – | – |
| [[17,1,5]] Color | 32 | (23, 4)¹ | (23, 4)ᵃ | – | – | – |
| [[19,1,5]] Color | 41 | (27, 4)¹ | (27, 4)ᵃ | – | – | – |
| [[23,1,7]] Golay | 77 | (56, 17)² | (46, 9)ᵃ | (45, 7) | (45, 7) | **(44, 8)** |
| [[36,8,6]] | 158 | (124, 11+1)³ | (84, 13)ᵃ | (78, 10) | (81*, 12) | (77, 11) |
| [[40,20,6]] (non-CSS) | 396 | (284, 21+1)³ | (142, 22)ᵇ | (136, 31) | (132, 21) | (130, 24) |
| [[42,12,5]] | 193 | (131, 13+1)³ | (95, 16)ᵇ | (90, 22)ᵇ | (90, 11) | (90, 9) |
| [[48,6,8]] | 231 | (203, 15+1)³ | (121, 30)ᵇ | (117*, 18) | (117, 13) | (116, 15) |
| [[64,12,8]] | 462 | (298, 19+1)³ | (193, 32)ᵇ | (177*, 14) | (174, 16) | (170, 18) |
| + LC-optimization | 298 | | – | – | (165, 21)‡ | (161, 13)‡ |
| [[80,8,10]] | 524 | (446, 21+1)³ | (250, 30)ᵇ | (252, 22) | (251, 28) | (252, 13) |
| + LC-optimization | 446 | | – | – | (240, 31)‡ | (245, 21)‡ |
| [[144,12,12]] Gross | 2192 | (876, 37+1)³ | (482, 46)ᵇ | (427, 30) | (413, 28) | (426, 26) |
| + LC-optimization | 876 | | (429, 55)ᵇ,‡ | (381, 50)‡ | **(357, 18)‡** | (362, 21)‡ |
Text: Golay compared with Ref. [5] "56 two-qubit gates and circuit depth 17 (or alternatively the circuit from Ref. [51] with 57 two-qubit gates and depth 7)"; Gross code reduced "by a factor of 2.5 with respect to the result obtained from LC-optimization". Fig. 21: Golay |0⟩_L "44 two-qubit gates and two-qubit depth 8" (QuSynth); Fig. 22: [[36,8,6]] "77 two-qubit gates and total circuit depth 11". Caveat: which exact Gross-code check matrix they used cannot be verified (no data release).

---

## 5. Bravyi et al., "High-threshold and low-overhead fault-tolerant quantum memory" — arXiv:2308.07915

- Authors: Sergey Bravyi, Andrew W. Cross, Jay M. Gambetta, Dmitri Maslov, Patrick Rall, Theodore J. Yoder. Versions v1, **v2** (latest, Wed 21 Feb 2024); tables read from arXiv HTML v2; PDF v2 sha256 `dbcd5d77…fddbc`. (The Nature publication "Nature 627, 778–782 (2024)" is as cited by other papers; I did not fetch the Nature page.)
- **Table 3 (raw)**: "The codes have check matrices H^X=[A|B] and H^Z=[B^T|A^T] … x^ℓ=y^m=1 and xy=yx."

| [[n,k,d]] | Net Encoding Rate r | ℓ,m | A | B |
|---|---|---|---|---|
| [[72,12,6]] | 1/12 | 6,6 | x³+y+y² | y³+x+x² |
| [[90,8,10]] | 1/23 | 15,3 | x⁹+y+y² | 1+x²+x⁷ |
| [[108,8,10]] | 1/27 | 9,6 | x³+y+y² | y³+x+x² |
| [[144,12,12]] | 1/24 | 12,6 | x³+y+y² | y³+x+x² |
| [[288,12,18]] | 1/48 | 12,12 | x³+y²+y⁷ | y³+x+x² |
| [[360,12,≤24]] | 1/60 | 30,6 | x⁹+y+y² | y³+x²⁵+x²⁶ |
| [[756,16,≤34]] | 1/95 | 21,18 | x³+y¹⁰+y¹⁷ | y⁵+x³+x¹⁹ |

  Table 1 (raw) circuit-level: [[72,12,6]] r 1/12, d_circ ≤6, p0 0.0048, pL(1e-3) 7×10⁻⁵, pL(1e-4) 7×10⁻⁸; [[90,8,10]] 1/23, ≤8, 0.0053, 5×10⁻⁶, 4×10⁻¹⁰; [[108,8,10]] 1/27, ≤8, 0.0058, 3×10⁻⁶, 1×10⁻¹⁰; [[144,12,12]] 1/24, ≤10, 0.0065, 2×10⁻⁷, 8×10⁻¹³; [[288,12,18]] 1/48, ≤18, 0.0069, 2×10⁻¹², 1×10⁻²².
- I rebuilt the 72/90/108/144 codes from Table 3 (x = S_ℓ⊗I_m, y = I_ℓ⊗S_m): k = 12, 8, 8, 12 respectively; no logical of weight ≤ 4 for n = 90 [recomputed].
- Encoding / |0_L⟩ CNOT counts: **unavailable (none in the paper)** — logical initialisation is via a special initialisation + syndrome-measurement cycle (§"Logical initialization and measurements are discussed in Section 9"); the SM cycle is a depth-7 CNOT circuit with 6n·N_c CNOTs for N_c cycles. No unitary encoder counts.

---

## 6. Other published CSS |0_L⟩ / encoder gate counts

### 6.1 Peham, Schmid, Berent, Müller, Wille — "Automated Synthesis of Fault-Tolerant State Preparation Circuits for Quantum Error Correction Codes", arXiv:2408.11894 (v1–v3; read **v3**, 16 May 2025; PDF sha256 `1d45fbd4…e9481d5`). Code: "https://github.com/cda-tum/mqt-qecc" (now munich-quantum-toolkit/qecc).
- Semantics: the "State Preparation Circuit #CNOTs" columns are the **non-FT unitary preparation part** (CSS: init m qubits in |+⟩, rest |0⟩, then a **CNOT-only** circuit found by symbolic Gaussian elimination); "SAT" = optimal **within this CNOT-only model** (gate- or depth-optimal); the Verification columns are extra CNOTs/measurements for FT. RL column = Ref. [20] (Zen et al., arXiv:2402.17761).
- **Table 1 (optimising CNOT count), raw** — prep #CNOTs SAT/Heur/RL · prep depth SAT/Heur/RL · verif #CNOTs SAT/Heur/RL · #meas SAT/Heur/RL:
  - [[15,1,3]] Reed-Muller (tetrahedral) |0⟩_L: 22/22/22 · 4/4/7 · 3/3/3 · 1/1/1; |+⟩_L: 23/23/24 · 5/5/6 · 7/7/7 · 1/1/1
  - [[9,1,3]] Shor |0⟩_L: 8/8/8 · 5/6/5 · 3/3/3 · 1/1/1; |+⟩_L: 6/6/6 · 2/2/2 · 0/0/0 · 0/0/0
  - [[9,1,3]] Rotated Surface |0⟩_L: 8/8/8 · 5/6/3 · 3/4/3 · 1/1/1
  - [[15,7,3]] Hamming |0⟩_L^7: −/22/− · −/12/− · 6*/7/− · 2/2/−
  - [[17,1,5]] 2D Color |0⟩_L: −/23/25 · −/11/7 · 29*/32/− · 6*/5/−
  - [[19,1,5]] 2D Color |0⟩_L: −/27/− · −/8/− · 33*/38/− · 6*/6/−
  - [[25,1,5]] Rotated Surface |0⟩_L: −/28/− · −/13/− · 34*/34/− · 5*/5/−
- **Table 2 (optimising depth), raw**: [[15,1,3]] |0⟩ 22/22/22 · 4/4/7; |+⟩ 23/23/24 · 5/5/6 · [[9,1,3]] Shor |0⟩ 8/9/8 · 3/3/5; |+⟩ 6/6/6 · 2/2/2 · [[9,1,3]] Surface |0⟩ 8/8/8 · 3/3/3 · [[15,7,3]] |0⟩^7 **23**/22/− · 4/4/− · [[17,1,5]] −/23/25 · −/5/7 · [[19,1,5]] −/27/− · −/5/− · [[25,1,5]] −/28/− · −/5/−.
- Table 3 (generalized non-deterministic FT scheme, **FT totals incl. verification**, raw "#CNOTs, Depth | projective init worst/best"): [[15,1,3]] |0⟩ 25, 8 | 96/64; |+⟩ 42, 14 | 120/80 · [[9,1,3]] surface |0⟩ 11, 6 | 36/24 · [[12,2,4]] Carbon |0⟩^2 30, 16 | 120/90 · [[15,7,3]] |0⟩^7 28, 11 | 96/64 · [[17,1,5]] 71, 22 | 180/108 · [[19,1,5]] 120, 25 | 210/126 · [[25,1,5]] 127, 31 | 200/120.
- Released circuits (MQT repo `scripts/ft_stateprep/eval/circuits/<code>/*non_ft_{opt,heuristic}.stim`) [recomputed CX counts]: Steane zero opt 8, Shor zero opt 8 / plus opt 6, Carbon zero opt 16, Hamming zero opt 22, tetrahedral zero opt 22, rot. surface d3 zero opt 8, d5 heuristic 28, cc_4_8_8 (17q) 23, cc_4_8_8_d7 (31q) 46, cc_6_6_6 (19q) 27. (`rotated_surface_d3/zero_non_ft_heuristic.stim` fails to parse in stim: odd CX target count — data-quality issue.)

### 6.2 Webster, Koutsioumpas, Browne — "Heuristic and Optimal Synthesis of CNOT and Clifford Circuits", arXiv:2503.14660 (v1–v3; read **v3**, 7 Sep 2026; also Quantum 2026-09-21 per search result). Code: https://github.com/m-webster/CliffordOpt (HEAD `4663db0d38eb1a8bb40d8e91308a75c5a5a9d40c`; GitHub API licence: null → **no licence**).
- **Table 5 (raw)**: "Entangling two qubit gate count in |0⟩_L encoding circuit for the codes in [44]" (Ref. [44] = Zen et al. RL). Columns RLFQC | A* | Greedy | Pytket | Qiskit | Volanto | PyZX | Rustiq:
  [[5,1,3]] 6|6|6|7|8|7|10|12 · [[7,1,3]] Steane 8|8|8|10|11|12|9|22 · [[9,1,3]] Shor 8|8|8|10|10|11|9|11 · [[15,1,3]] Reed-Muller 22|22|22|31|32|37|24|55 · [[17,1,5]] Colour 37|31|33|43|43|42|42|52 · [[19,1,5]] Colour 49|45|49|61|61|70|67|151 · [[23,1,7]] Golay 61|**56**|69|96|97|118|138|237 · [[25,1,5]] Surface 54|54|53|72|72|61|71|84 · TOTAL 245|230|248|330|334|358|370|624.
- Text: "[[23,1,7]] … RL … 61 …; In [22] (Paetznick–Reichardt) … 57 CNOT gates …; Using our A* method, we found an encoding circuit using 56 entangling two qubit gates". Also: "Applying the A* algorithm to the same codes [SAT codes of refs 24, 31] gave circuits which match the optimal entangling gate counts."
- ⚠ Semantics caution: in the supplementary `paper_results/RL_SAT_encoding.xlsx` (downloaded, sha256 `c77e1420…798d0d24`), the `n` column for the [[17,1,5]], [[19,1,5]], [[25,1,5]] rows is 20, 23, 29 — i.e. the RL target states include extra (flag/ancilla) qubits, so these three rows are **likely not pure |0_L⟩ counts** (they are far above the 23/27/28 non-FT values elsewhere). I am not certain; treat them as not comparable.

### 6.3 Paetznick & Reichardt — "Fault-tolerant ancilla preparation and noise threshold lower bounds for the 23-qubit Golay code", arXiv:1106.2190 (read **v2**, 12 Apr 2013; PDF sha256 `cd0575eb…596db`)
- "Figure 4: An optimized circuit for preparing |0⟩ encoded in the Golay code uses **57 CNOT gates applied in seven rounds**." "…an encoding circuit with only 57 CNOT gates, 20 fewer than given by the Latin rectangle method" (→ 77). Steane: "A Latin rectangle-based encoding schedule … needs nine CNOT gates. An equivalent circuit requiring only eight CNOT gates is shown in Figure 5(b)." Unitary non-FT |0_L⟩ prep.

### 6.4 Colmenarez, Zen, Olle, Marquardt, Müller — "Unitary fault-tolerant encoding of Pauli states in surface codes", arXiv:2601.05113 (**v1**, 8 Jan 2026)
- **Table 1 (raw)** "Two-qubit gate count and circuit depth of the unitary encoding with ancilla (UEA) and without (UE) … for odd code distance d. Here we use t=⌊(d−1)/2⌋": Rot. UEA (5t+3)(d−1), depth 5(d−1), no meas · **Rot. UE (3t+1)(d−1), depth 3(d−1)** · Rot. ME 2d(d−1), 4, meas · UnRot. UEA (5d−2)(d−1), 5(d−1) · **UnRot. UE (3d−2)(d−1), 3(d−1)** · UnRot. ME 2(2d−1)(d−1), 4, meas.
- These are **distance-preserving (FT) unitary** encoders with geometrically local gates (UE assumes full connectivity inside a plaquette), so they are upper bounds for our all-to-all non-FT task. Evaluated [my arithmetic]: Rot. UE d=3/5/7/9/11 → 8/28/60/104/160; UnRot. UE → 14/52/114/200/310 — these equal QECirc's `direct-zero-prep` circuits exactly.
- Inconsistency: text says "for d=5 the unrotated surface the ME and UE encoding schemes need 72 and **44** gates", but the Table-1 formula gives (3·5−2)(5−1) = **52** (QECirc circuit has 52).

### 6.5 Kanomata & Goto — "Fault-tolerant quantum computing with a high-rate symplectic double code", arXiv:2509.15457 (v1, 18 Sep 2025)
- [[30,6,5]] CSS code (symplectic double of a [[15,3,5]] non-CSS code). "Figure 2: Plus-state encoder … with 108 CNOT gates. Figure 3: Plus-state encoder … with **67 CNOT gates**" (overlap method). (Depth 11 is quoted by arXiv:2605.15266; I did not find the depth number in the HTML text.) |+_L⟩ prep, non-FT.

### 6.6 Rodriguez et al. — "Experimental Demonstration of Logical Magic State Distillation", arXiv:2412.15165 (v1, 19 Dec 2024)
- "For the d=3 color code, the solution above gives the **9-gate, 3-layer encoding circuit**. For the [[17,1,5]] color code, the best solution we find has five layers and **24 CNOT/CZ gates**." These are **encoders** (arbitrary input state, logical input qubit), non-FT; neutral-atom hardware.

### 6.7 Paetznick et al. (Microsoft/Quantinuum) — "Demonstration of logical qubits and repeated error correction with better-than-physical error rates", arXiv:2404.02280 (read v3, 17 Nov 2024) — Carbon code
- Defines Carbon [[12,2,4]] = C4 concatenated into C6 (Knill), stabilizers in its Table 4. FT prep numbers (raw): "The resulting circuits for preparing |00⟩ require **19 qubits and 37 CNOTs**, whereas Knill's preparation requires 144 qubits and 216 CNOTs"; "Knill's C4 preparation circuit requires eight qubits and eight CNOTs, whereas fault tolerant preparation circuits with five qubits and five CNOTs are now known". These are **FT with verification ancillas**, not unitary n-qubit preps.

### 6.8 Other sources checked
- Zen et al., "Quantum Circuit Discovery for Fault-Tolerant Logical State Preparation with Reinforcement Learning", arXiv:2402.17761 (v2): counts are only in figures (no tables in the PDF text I extracted); numbers only available second-hand (RLFQC column in §6.2; RL column in §6.1). First-hand table: unavailable.
- Schmid et al., "Deterministic Fault-Tolerant State Preparation … Boolean Satisfiability", arXiv:2501.05527 (v1): Table I lists only **verification/correction** ancillas/CNOTs (e.g. Steane Σ 1 ANC / 3 CNOT), not the prep CNOT count — not directly usable.
- Higgott et al., "Optimal local unitary encoding circuits for the surface code", arXiv:2002.00362 (v5): depth-optimal local encoders; no gate-count table found in the HTML.
- Tsai & Puri, "A Unitary Encoder for Surface Codes", arXiv:2506.04084 (v1): depth-4 code-doubling circuit ("halves the gate count of the fastest encoder known previously"); no numeric gate-count table in the HTML (0 tables).
- **Generalized bicycle codes, optimised hypergraph-product codes, quantum Reed–Muller beyond [[15,1,3]], many-hypercube, Iceberg (numeric), Shor-type concatenations beyond [[9,1,3]]**: no published unitary |0_L⟩ 2q counts found in the sources fetched (unavailable from this session's search). Only QECirc's naive `qldpc` tableau circuits exist for HGP [[58,16,3]] (350) and [[241,121,3]] (2126).

---

## 7. MQT QECC code library (github.com/munich-quantum-toolkit/qecc)
- HEAD `accd7be9c93d6dc777ebfd9d36263250e5350746` (2026-09-25 19:19:17 +0000, "⬆️🩹 Update patch updates (#834)"; = ls-remote HEAD). **Licence MIT** ("Copyright (c) 2023 - 2026 Chair for Design Automation, TUM").
- `src/mqt/qecc/codes/instances/` (shipped data): `steane/`, `shor/`, `tetrahedral/`, `carbon/`, `golay/` (each `hx.npy`, `hz.npy`; README: [[7,1,3]], [[9,1,3]], [[15,1,3]], [[12,2,4]], [[23,1,7]]); `lifted_product/lp_l={16,21,30}_h{x,z}.npz` (sparse); `misc/8_3_3.txt` (Pauli strings), `misc/15_3_5.txt` (Python list), `misc/30_6_5.txt` (NumPy notation) readable by `CSSCode.from_file`.
- Constructions (`codes/__init__.py` exports): `construct_bb_code(n)` for n ∈ {72, 90, 108, 144, 288} (**n = 90 is wrong, d = 2**; see §0); `construct_iceberg_code(m)` → [[2m, 2m−2, 2]]; `construct_many_hypercube_code(level)` → [[6^l,4^l,2^l]] (docstring cites arXiv:2403.16054); `construct_quantum_hamming_code(r)` → [[2^r−1, 2^r−2r−1, 3]]; `HexagonalColorCode(d)`, `SquareOctagonColorCode(d)`, `RotatedSurfaceCode(d)`; `ConcatenatedCode`/`ConcatenatedCSSCode`; 3D/4D product codes in `hypergraph_product_code.py`.
- Released circuit data usable as references: `scripts/encoding_circuits/best_circuits/` (arXiv:2605.15266, 15 codes × 6 circuits, Stim), `scripts/ft_stateprep/eval/circuits/` (arXiv:2408.11894; steane, shor, rotated_surface_d3/d5, hamming, tetrahedral, carbon, cc_4_8_8, cc_4_8_8_d7, cc_6_6_6; Stim + QASM), `scripts/ft_stateprep/eval_det/circuits/` (QASM; incl. 11_1_3, 16_2_4, hypercube), `scripts/cat_states/circuits/`.

---

## 8. Held-out family candidates (set O) — defining papers and scaling

| Family | Defining paper (fetched) | Parameters as printed | n ≥ 100? | Published |0_L⟩ 2q counts |
|---|---|---|---|---|
| Many-hypercube | Goto, "Many-hypercube codes: High-rate quantum error-correcting codes for high-performance fault-tolerant quantum computing", arXiv:**2403.16054v3** (28 Aug 2024; sole author Hayato Goto; Sci. Adv. per search result) | "By concatenating it (L−1) times, we obtain the [[6^L,4^L,2^L]] code … level-L many-hypercube code"; "64 and 256 logical qubits are encoded into 216 and 1296 physical qubits … for the code distances of 8 and 16". Level-1 [[6,4,2]]: S_Z = Z1…Z6, S_X = X1…X6; Z_L1=Z1Z2, X_L1=X2X3; Z_L2=Z2Z3, X_L2=X1X2; Z_L3=Z4Z5, X_L3=X5X6; Z_L4=Z5Z6, X_L4=X4X5; "|0000⟩_L = (|000000⟩+|111111⟩)/√2" (GHZ). Fig. 1A zero-state encoder; Fig. 1B "arbitrary-state encoder by adding two CNOT gates". | **Yes**: L=3 → [[216,64,8]] (printed). L=4 → [[1296,256,16]]. | No numeric unitary counts found (FT encoders with ancillas/post-selection only). MQT `construct_many_hypercube_code(3)` builds n=216. |
| MHC variants | Goto, "Optimized Many-Hypercube Codes toward Lower Logical Error Rates and Earlier Realization", arXiv:2512.00561 (v4, 9 Mar 2026); Nakai & Goto, "Subsystem many-hypercube codes", arXiv:2510.04526 (v2) | "concatenated [[n,n−2,2]] quantum error-detecting codes (n is even)"; D_{6,4,4} = [[6,4,2]] at level 1 and [[4,2,2]] at levels 2, 3; mentions [[16,4,4]], [[24,8,4]], [[36,16,4]]. | Derived (my arithmetic from the concatenation rule n=∏nᵢ, k=∏(nᵢ−2), d=2^L): D_{6,4,4} = [[96,32,8]], D_{6,6,4} = [[144,32,8]] — **not printed in what I read; verify before use**. | none found |
| Carbon / C4-C6 | Paetznick et al., arXiv:2404.02280v3 (Carbon = C4 into C6, [[12,2,4]], stabilizers Table 4); scaling formula from Goto arXiv:2403.16054v3 | Goto: "The parameters of the C4/C6 scheme are given by N^(L)=4×3^{L−1}, K^(L)=1 (or 2), D^(L)=2^L". Carbon: "concatenation of C4 into C6 yields a [[12,2,4]] code". 2404.02280 §A.3: "In Knill's original proposal Carbon (C4/C6) was concatenated repeatedly with C6". | Derived from Goto's formula: L=3 → n=36, L=4 → n=**108** (K=1 or 2, D=16). Not verified by construction. | Carbon |0_L⟩^2: 16 (arXiv:2603.17743 BeFS (16,4); baseline (16,5) from arXiv:2408.11894). FT: 37 CNOT / 19 qubits (2404.02280). Larger levels: none. |
| Iceberg | Self, Benedetti, Amaro, "Protecting Expressive Circuits with a Quantum Error Detection Code", arXiv:**2211.06703** (v2, 26 Jul 2024; Nature Physics per search) | "[[k+2,k,2]] … An even number k of logical qubits are encoded into k+2 physical qubits"; X̄_i = X_i X_t, Z̄_i = Z_i Z_b; "this state is the GHZ state of the n physical qubits: |0̄⟩^{⊗[k]} = (|0⟩^{⊗n}+|1⟩^{⊗n})/√2". FT init uses one ancilla (Fig. 1c). | Yes for any even k ≥ 98 (trivially). | No numeric count printed; |0̄…0̄⟩ = GHZ_n, so the unitary optimum is n−1 two-qubit gates (standard GHZ fact — my inference, not a printed number). → useful only as a sanity-check family. |

Contamination note: StabilizerBench already contains Hypercube l=1,2, Iceberg m=2,3,4, Carbon and their concatenations (codespace task). QECirc contains Iceberg [[4,2,2]] and Carbon, but no many-hypercube code. The genuine Bravyi [[90,8,10]] has (per §0) no correct published |0_L⟩ count either.

---

## 9. Consolidated best-known unitary |0_L⟩ (non-FT, all-to-all) 2q counts found

(G = two-qubit gates as printed; D = depth as printed — metric differs per paper: 2408.11894/2605.15266 CNOT depth, 2603.17743 two-qubit depth; "SAT-opt" = optimal among CNOT-only circuits with |0⟩/|+⟩ inputs.)

| Code | [[n,k,d]] | best |0_L⟩ G (D) | source (table) | other printed values |
|---|---|---|---|---|---|
| Steane / 6.6.6 d3 | [[7,1,3]] | 8 | Webster 2503.14660v3 T5 (A*, Greedy, RLFQC); Paetznick–Reichardt 1106.2190v2 Fig. 5(b) | Latin rectangle 9; QECirc 8 (depth 3) |
| Rot. surface d3 | [[9,1,3]] | 8 (3) | 2408.11894v3 T1/T2 SAT-opt; 2603.17743v1 T1 BeFS (8,3) | Colmenarez UE formula 8 |
| Shor | [[9,1,3]] | 8 (3) | 2408.11894v3 T2 SAT | |+_L⟩ 6 (2) |
| Carbon | [[12,2,4]] | 16 (4) | 2603.17743v1 T1 BeFS | (16,5) from 2408.11894 per 2603.17743 |
| Tetrahedral / QRM | [[15,1,3]] | 22 (4) | 2408.11894v3 T1 SAT-opt; 2605.15266v1 T1 | |+_L⟩ 23 (SAT); 2603.17743 |+⟩ (23,4) |
| q. Hamming | [[15,7,3]] | 22 (4) | 2408.11894v3 T1/T2 heur; 2605.15266v1 T1; 2603.17743 T1 | SAT depth-opt 23 |
| 4.8.8 d5 | [[17,1,5]] | 23 (4) | 2605.15266v1 T1/T2; 2603.17743v1 T1; 2408.11894 heur | encoder 24 CNOT/CZ (2412.15165) |
| 6.6.6 d5 | [[19,1,5]] | 27 (4) | 2605.15266v1 T1/T2; 2603.17743v1 T1 | |
| Golay | [[23,1,7]] | **44 (8)** | 2603.17743v1 T1 QuSynth | 45 (7) beam/RL; 45 (10) 2605.15266 T2; 56 (A*, Webster T5); 57 in 7 rounds (1106.2190 Fig. 4); QECirc 44 |
| Rot. surface d5 | [[25,1,5]] | 28 | 2408.11894v3 T1 heur (depth 13) / T2 (depth 5) | Colmenarez UE 28 (FT, local) |
| Symplectic double | [[30,6,5]] | 61 (11) | 2605.15266v1 T2 | |+_L⟩ 62 (11); 67 (Kanomata–Goto) |
| 4.8.8 d7 | [[31,1,7]] | 45 (5) | 2605.15266v1 T2 | |
| q. Hamming | [[31,21,3]] | 52 (5) | 2605.15266v1 T1 | |
| 6.6.6 d7 | [[37,1,7]] | 57 (6) | 2605.15266v1 T2 | |
| unknown family | [[36,8,6]] | 77 (11) | 2603.17743v1 T1 QuSynth | |
| non-CSS | [[40,20,6]] | 130 (24) | 2603.17743v1 T1 | |
| unknown | [[42,12,5]] | 90 (9) | 2603.17743v1 T1 | |
| unknown | [[48,6,8]] | 116 (15) | 2603.17743v1 T1 | |
| Rot. surface d7 / d9 / d11 | [[49,1,7]] / [[81,1,9]] / [[121,1,11]] | 60 / 104 / 160 | Colmenarez 2601.05113v1 T1 formula (FT, local; upper bounds) | QECirc same |
| unknown | [[64,12,8]] | 161 (13) ‡ | 2603.17743v1 T1 | |
| BB | [[72,12,6]] | 150 (14) | 2605.15266v1 T2 | QECirc 150 (9) |
| unknown | [[80,8,10]] | 240 (31) ‡ | 2603.17743v1 T1 | |
| "BB" (MQT, d=2!) | [[90,8,10]]→[[90,8,2]] | 134 (21) | 2605.15266v1 T2 | not the Bravyi code |
| BB | [[108,8,10]] | 402 (58) (text: 430) | 2605.15266v1 T2 | QECirc circuit-synth 263 (id 160) [database value, not in paper] |
| Gross (BB) | [[144,12,12]] | **330 (39)**; 330 at depth 17 per text | 2605.15266v1 T2 / text | 357 (18) ‡ 2603.17743 RL; QECirc 395 |

---

## 10. Implications for qbank category A (recommendations)
1. **Build codes ourselves** from primary definitions and **verify k and d** (at least a low-weight-logical search) — do not import MQT `construct_bb_code(90)` or QECirc `90-8-10`. Use Bravyi Table 3 polynomials directly.
2. The task must specify the **logical basis** (which operators are Z̄) because |0…0⟩_L is basis-dependent for k > 1 (e.g. Iceberg/MHC GHZ structure). Verification = stim tableau: all X-stabilizers ±1-deterministic with the right sign convention, all Z-type operators in ker(H_X) (Z-stabilizers + Z̄) at +1.
3. **Whitelist gates** (e.g. {H, S, S†, X, Y, Z, CX, CZ, SWAP}); count SWAP = 3 and reject any other 2q gate, measurement, reset-after-use, or extra qubits. StabilizerBench shows agents will exploit SPP/SQRT_XX/CXSWAP if they aren't counted.
4. Reference scores: prefer the independently re-verifiable released circuits (MQT `best_circuits`, QECirc Stim) and re-count them under our metric; mark non-CSS SWAP-containing ones.
5. QECirc data is CC BY-SA 4.0 (ShareAlike); StabilizerBench and CliffordOpt have **no licence** → reference only, don't redistribute.
6. For held-out O with n ≥ 100: many-hypercube L=3 ([[216,64,8]]; no published unitary count found), C4/C6 level-4 (n=108, derived — must be constructed/verified), genuine Bravyi [[90,8,10]] and [[288,12,18]] (no correct/published |0_L⟩ counts found), large rotated/unrotated surface (but closed-form Colmenarez counts exist → contaminated), Iceberg (trivial GHZ optimum; sanity only).

---

## Appendix — files in scratch (`recon_A/`) and hashes
- arXiv PDFs (sha256): 2604.21287v1 `6b7933f0c9b4d4228b35a2db7c43527212dd4335c609aeff950bffd529536f91`; 2609.20182v1 `b88edeeb731cdda92a873af07aff18ffd9f85226cdbe5509f61742b36ea91fba`; 2605.15266v1 `c702ff5c69efc95c30a28277ec732f43e318308b471f8e32c5ea69be99f8c3b8`; 2603.17743v1 `edc6d93def25e4ece4b242938e87c78bf89cdb9ce64edd1690452aeff7dd54f4`; 2308.07915v2 `dbcd5d770033291eebb999c53105ebdb2e1dae0194b3ecc0369cb4d3ec9fddbc`; 2408.11894v3 `1d45fbd46d52ce105d9922edcb5c03f8e5fee058a9f9dfeb3fb920c4fe9481d5`; 1106.2190v2 `cd0575ebc3658400904fc99c9e4ec51ee9c536aa7db5a42e20e1eb66695596db`; 2403.16054v3 `1769bf53ed2cfdd9e35c0af71e57e25a5c9250323d9ffccd7f98a270bbd7d53d`; 2404.02280v3 `2d2197935fb3a2b269e679aa23dbee6e4fa6de809fcf529e8f310bd0059c2fdd`; 2211.06703v2 `6eba9288a346cf07105df593a3c7caaf68000fa2e9dba343a3550ae36cdd1ade`; 2402.17761v2 `955f36cbcc7cc61a54190da236a61cb1fd1556ab42a2ff7f6c10648ea74dae69`. arXiv HTML copies `html_*.html`, extracted tables `tables_*.txt`.
- QECirc API index: `qecirc/qecirc_api_circuits_ids1-2000.json` sha256 `07dd309f71863065b5750fc38a7197d2ea5a95686e9fc4286f7e7266eab5e118`; analysis `qecirc/qecirc_prep_enc_analysis.json`, `qecirc/qecirc_min_table.txt`, `qecirc/qecirc_codes_list.txt`.
- StabilizerBench data: `sb_repo/data/benchmarks.json` sha256 `883a1dd504cbd630ce227af777d7a7892b294fdacfb2395c8b2b8fe8f56c7011`; `sb_repo/data/circuit_dataset.jsonl` sha256 `240ee35008f0801ccf2e040e294625234ab19d074fb194d7d9f782827bc7ee52`.
- CliffordOpt `RL_SAT_encoding.xlsx` sha256 `c77e1420b61ebb267b6adf6fcbf2295ae01b8ec4339a07ab05420448798d0d24`.
- Clones (depth 1): `sb_repo/` @93208e34, `qecirc_repo/` @4dd18796, `mqt_qecc/` @accd7be9.
- Scripts: `qecirc_analyze.py`, `bb_check.py`, `bb_check2.py`, `mqt_best.py`, `mqt_best2.py`, `html_tables.py`.
