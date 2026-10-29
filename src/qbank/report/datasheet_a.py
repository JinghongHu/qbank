"""DATASHEET for category A: data/v1/A/DATASHEET.md. Tables are computed from data/v1 files."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date

from ..core.instance import data_root, load_index, load_private
from ..core.splits import load_manifest

FAMILY_DOC = {
    "rand_stab": ("T", "Random full-rank stabilizer state: `qiskit.quantum_info.random_clifford(n, seed)` applied to |0^n⟩, seed derived from (family, n, in-split seed) via SHA-256", "stabilizer_state"),
    "bb_rand": ("T", "Bivariate bicycle code with random polynomials (Bravyi convention: x=S_l⊗I_m, y=I_l⊗S_m; A = x^a + y^b + y^c, B = y^d + x^e + x^f), requires k ≥ 2; excludes the (l,m) of all published BB codes (including swapped)", "css_logical_zero"),
    "gb_rand": ("T", "Random generalized bicycle code: A, B are random cyclic polynomials of weight 3-4 over Z_l, requires k ≥ 2", "css_logical_zero"),
    "css_rand": ("T", "General random CSS code without sparsity requirement: random full-rank Hx, Hz a random full-rank subspace of ker(Hx), k ∈ [1, n/8]", "css_logical_zero"),
    "rot_surface": ("T", "Rotated surface code [[d²,1,d]], d = 3-11 (own construction, including even d)", "css_logical_zero"),
    "color_666": ("T", "Triangular 6.6.6 color code (lattice from mqt.qecc 2.0.0, parameters independently verified by this benchmark)", "css_logical_zero"),
    "color_488": ("T", "Triangular 4.8.8 color code (as above; d=3 is identical to Steane and is an alias, not generated separately)", "css_logical_zero"),
    "qhamming": ("T", "Quantum Hamming code CSS(H_r, H_r) = [[2^r−1, 2^r−1−2r, 3]]", "css_logical_zero"),
    "qrm": ("T", "Punctured quantum Reed-Muller code [[2^m−1, 1, 3]] (X checks: coordinate functions; Z checks: monomials of degree 1..m−2)", "css_logical_zero"),
    "bb_published": ("T", "Published BB codes: 72/90/108/144/288/360/756 from Table 3 of Bravyi et al. (Nature 2024, arXiv:2308.07915v2), built from the polynomials in the table", "css_logical_zero"),
    "bb_mqt_n90_d2": ("T", "construct_bb_code(90) of MQT QECC 2.0.0: ℓ and m are passed swapped, the resulting code has k = 8 and distance ≤ 2, not Bravyi's [[90,8,10]]", "css_logical_zero"),
    "hgp_rand": ("O", "Hypergraph product of random biregular classical LDPC codes (shapes such as (2,3)/(2,4)/(3,4)/(3,6))", "css_logical_zero"),
    "many_hypercube": ("O", "many-hypercube code [[6^L,4^L,2^L]], L = 2, 3 (Goto, arXiv:2403.16054; construction from mqt.qecc)", "css_logical_zero"),
    "shor_concat": ("O", "Shor-type [[a·b,1,min(a,b)]], a ≤ b ∈ {3,5,7,9,11}", "css_logical_zero"),
    "iceberg": ("O", "Iceberg code [[2m,2m−2,2]] (|0_L⟩ is the GHZ state, optimum n−1)", "css_logical_zero"),
    "unrot_surface": ("O", "Unrotated surface code = hypergraph product of repetition codes, d ∈ {3,5,7,9,11}", "css_logical_zero"),
    "toric": ("O", "toric code = hypergraph product of cyclic repetition codes, d ∈ {3,4,5,6}", "css_logical_zero"),
    "sporadic": ("O", "Sporadic codes: Golay, Carbon (mqt.qecc code library), [[30,6,5]], Gottesman [[8,3,3]] (non-CSS), [[15,3,5]] (non-CSS), [[5,1,3]] (non-CSS)", "css_logical_zero / stabilizer_state"),
    "composite": ("O", "Concatenated codes rebuilt by StabilizerBench's rules (outer∘inner, inner k=1, n<200), neither component belongs to T; composite = true", "css_logical_zero / stabilizer_state"),
}


def make_datasheet(log=print) -> str:
    man = load_manifest("A")
    idx = {r["id"]: r for r in load_index("A")}
    split_of = {e["id"]: s for s, es in man["splits"].items() for e in es}
    fam_split = defaultdict(Counter)
    fam_n = defaultdict(list)
    dist_methods = Counter()
    for iid, r in idx.items():
        fam_split[r["family"]][split_of[iid]] += 1
        fam_n[r["family"]].append(r["n"])
        if r["task"] == "css_logical_zero" or iid.startswith("A.stab.sporadic") or iid.startswith("A.stab.composite"):
            v = load_private("A", iid)["private"].get("code", {}).get("verification", {}).get("distance", {})
            dist_methods[(v or {}).get("method", "n/a").split(":")[0]] += 1
    L = []
    a = L.append
    a("# Datasheet: qbank v1 · Category A (stabilizer state / code state preparation)\n")
    a(f"Generated: {date.today().isoformat()} (by `qbank report A` from `data/v1/`; all tables are computed).\n")
    a("## 1. Task and contract\n")
    a("- **css_logical_zero** (main): prepare the |0…0⟩_L of a CSS code from |0…0⟩, i.e. the state stabilized (eigenvalue +1) by all X checks and all Z-type operators commuting with them; it is determined by rowspace(Hx) alone and does not depend on the choice of logical operators.")
    a("- **stabilizer_state**: prepare a given full-rank signed stabilizer state (random stabilizer states; for non-CSS codes, the |0…0⟩_L defined by the published logical Z basis).")
    a("- **codespace_state** (secondary track): any output in the code space is accepted, the logical state is unconstrained (StabilizerBench's definition).")
    a("- **Gate set**: h, s, sdg, x, y, z, sx, sxdg, cx, cz, cy, swap. Any other gate (e.g. SPP, SQRT_XX, iSWAP, CXSWAP), measurement, reset or extra qubit is rejected.")
    a("- **Cost**: two-qubit gate count (cx = cz = cy = 1, swap = 3), recomputed by `qbank.core.costs`; tool self-reports are not trusted.")
    a("- **Tracks**: `a2a_2q` (all-to-all); `line_2q` and `grid_2q` (two-qubit gates only on graph edges, the output map from code qubits to physical qubits chosen by the method); `codespace_a2a_2q`.")
    a("- **Output maps**: every track accepts an answer with an output map (code qubit → physical qubit). On the all-to-all tracks this does not make the task easier: the initial state is \\|0…0⟩, so renaming the qubits of the whole circuit gives an answer without a map and with the same gates; on the line and grid tracks the map is the layout chosen by the method.\n")
    a("## 2. Checking method and size limits\n")
    a("- Two independent checkers must agree, otherwise the result is \"checker disagreement\" (treated as an error): (1) stim `TableauSimulator.peek_observable_expectation`; (2) `qbank.core.pauli`, a GF(2) symplectic propagation with a signed group-membership test that does not depend on a simulation library. It is cross-checked against stim on more than 4400 random cases with zero differences (`tests/test_core.py`).")
    a("- **Signs**: the checkers distinguish signs. Single-qubit Pauli corrections are free and are appended to the circuit by an explicit normalization step (recorded in the `pauli_correction` field); checking and counting both apply to the corrected circuit.")
    a("- **Negative controls** (`tests/test_a_contracts.py`): wrong sign (without correction) → rejected; states in the code space other than \\|0_L⟩, such as \\|+_L⟩ → rejected under css_logical_zero; gates outside the gate set, extra qubits, two-qubit gates not on the graph → rejected.")
    a("  **Note**: \\|1_L⟩ = X̄\\|0_L⟩ differs from \\|0_L⟩ only in signs, and X̄ is a product of single-qubit Paulis, so the normalization step corrects it to \\|0_L⟩. This is a direct consequence of the rule \"single-qubit Pauli corrections are free\".")
    a("- **Size limit**: the stabilizer check runs in polynomial time and all instances (n ≤ 756) can be checked exactly; there are no \"unverified\" category A instances.\n")
    a("## 3. Sources and licenses\n")
    a("- Generator families: generated by this benchmark's code (same license as qbank).")
    a("- External code or data used (all pinned to fixed versions, see `data/v1/external/SOURCES_A.json` and `fetch_A.sh`):")
    a("  - mqt.qecc 2.0.0 (PyPI, MIT): lattices of the color codes and many-hypercube codes, Golay, Carbon and misc code files;")
    a("  - MQT QECC repository @ accd7be9 (MIT): circuits released with arXiv:2605.15266 and arXiv:2408.11894, used only as baselines;")
    a("  - QECirc @ 4dd18796 (data CC BY-SA 4.0): used only as a source of baseline circuits, **not distributed with the benchmark**;")
    a("  - StabilizerBench @ 93208e34 (no license): only the composition rules are borrowed and reimplemented by us, no data is copied; only checksums of the data files are recorded.\n")
    a("## 4. Families, parameters and split sizes\n")
    a("| Family | T/O | Construction | Task | n range | train | val | test_in | test_ood | probe |\n|---|---|---|---|---|---|---|---|---|---|")
    for fam in sorted(fam_split, key=lambda f: (FAMILY_DOC.get(f, ("?",))[0], f)):
        to, desc, task = FAMILY_DOC.get(fam, ("?", fam, "?"))
        c = fam_split[fam]
        a(f"| {fam} | {to} | {desc} | {task} | {min(fam_n[fam])}-{max(fam_n[fam])} | {c['train']} | {c['val']} | {c['test_in']} | {c['test_ood']} | {c['probe']} |")
    a(f"\nTotal: " + ", ".join(f"{s} {man['totals'][s]}" for s in man["totals"]) + f"; {sum(man['totals'].values())} instances in all.")
    a("The named codes color_666 d11 (n = 91) and d13 (127), color_488 d11 (71) and d13 (97), QRM(2,6) (`qrm.m6r2`, 63) and QRM(2,7) (`qrm.m7r2`, 127) lie within the training size range of their families: d13 and QRM(2,7) are in train, d11 and QRM(2,6) in val (so that the test set of task pack v2 contains named codes within the training size range).")
    a("In addition, 3 equivalent variants are generated for each test instance (qubit relabeling, change of generator basis, and both), stored in `data/v1/variants/A/`, in the same split as the original.\n")
    a("## 5. Code verification\n")
    a("For every code n, k and commutativity are recomputed (all generators commute for every instance); the distance is computed exactly when feasible (vectorized meet-in-the-middle enumeration when the kernel dimension is ≤ 26), otherwise a search for low-weight logical operators (weight ≤ 4) gives a lower bound. Counts by method:\n")
    a("| Distance method | Instances |\n|---|---|")
    for m, c in sorted(dist_methods.items()):
        a(f"| {m} | {c} |")
    a("\nDistances of the named codes color_666 / color_488 d11 and d13, `qrm.m6r2` and `qrm.m7r2` (all k = 1): the X distance of `qrm.m6r2` is exactly 15; the others are proven ≥ 5 by the low-weight search (the same level as the d9 codes; the correctness of an A task does not depend on the distance). The formula distance of the QRM codes is stored only in the private `reported` field and is not treated as a verified result.")
    a("\nIssues in libraries and external data relevant to the benchmark, and how they are handled:")
    a("- **The two BB90 codes.** mqt.qecc 2.0.0's `construct_bb_code(90)` calls `_cyclic_code_check_matrix(m, l, …)` with ℓ = 15 and m = 3 swapped "
      "(checked in the source) and produces a different code: k = 8, but there are weight-2 logical operators (e.g. an X type acting on qubits (0, 15)), so the distance is ≤ 2. StabilizerBench's BB90, "
      "QECirc's `90-8-10` and the row labeled [[90,8,10]] in Table 2 of arXiv:2605.15266 all use this code. In this benchmark it is the family `bb_mqt_n90_d2`, instance `A.css_zero.bb_mqt_n90_d2.mqt90` (test_in), "
      "the distance-≤ 2 code produced by MQT QECC's `construct_bb_code(90)`, not Bravyi's [[90,8,10]]. "
      "The 134 in the literature is the two-qubit gate count on this d ≤ 2 code, and the \"published value\" counts only toward this instance's best_known; **it is not a record on [[90,8,10]]**.")
    a("- Bravyi et al.'s [[90,8,10]] (Nature 2024, Table 3: ℓ = 15, m = 3, A = x⁹ + y + y², B = 1 + x² + x⁷) is `A.css_zero.bb_published.bravyi90` in the benchmark "
      "(test_in, all baselines run). Checks: k = n − rank Hx − rank Hz = 8; exhaustive enumeration of all vectors of weight 1 and 2 finds no logical operator "
      "(a Z type in ker Hx but not in the row space of Hz, or vice versa for X type), so the distance is ≥ 3; d = 10 is taken from the paper, and this benchmark's low-weight search (weight ≤ 4) found no logical operator.")
    a("- mqt.qecc `construct_bb_code(108/144)` equals Bravyi's codes up to the permutation \"block swap + in-block transpose\" (proven by computation), so the 108/144 numbers and released circuits of arXiv:2605.15266 can be used for this benchmark's instances after relabeling.")
    a("- mqt.qecc `CSSCode.from_file` misreads the non-CSS 8_3_3 as a different CSS code; this benchmark reads it with a generic loader.")
    a("- QECirc circuits do not always use the same qubit numbering as the `original_matrices` they reference; each imported circuit is mapped to the benchmark instance whose target state it actually prepares (checked circuit by circuit).\n")
    a("## 6. Splits and deduplication\n")
    a("- Seed ranges are disjoint between splits (train 0-9,999, val 10,000-, test_in 20,000-, test_ood 30,000-, probe 40,000-); the actual seeds are derived via SHA-256.")
    a("- Deduplication applies only to pairs of instances in different splits: first compare content hashes; then compare invariants (n, rank, exact dX/dZ, the number of vectors of weight 1-3 in the row space); when invariants coincide, n ≤ 60 uses VF2++ to decide Tanner-graph isomorphism (20 s limit, undecided pairs treated as duplicates), and n > 60 compares row spaces, treating even differing ones conservatively as duplicates.")
    a("- Duplicates are removed from the later split and refilled with new seeds from the same split. **Observed**: small BB codes (n = 36) are often truly equivalent under different seeds (isomorphism proven). Details in `data/v1/instances/A/build_report.json`.")
    a("- Exclusion list: `data/v1/exclusions/exclude.json`, empty; matching works as in deduplication (tested with permuted equivalent forms in `tests/test_a_data.py`).")
    a("- **One task under two names**: the quantum Hamming code CSS(H_r, H_r) and the punctured QRM(1, r) have the same Hx, so their \\|0_L⟩ is the same state. Comparing the main-track target (signed stabilizer group in canonical form) of every A instance gives 4 groups: qhamming.r4 / qrm.m4 (both train), qhamming.r5 (val) / qrm.m5 (train), qhamming.r6 (test_in) / qrm.m6 (val), qhamming.r7 / qrm.m7 (both test_in). The splits keep both instances; evaluations leave out the instances listed under `exclude_from_evaluation` in `data/v1/splits/semantic_duplicates_A.json` (across splits the copy in the later split; within one split the pair counts once). `load_split()` and `qbank export` do this by default. Check script: `python -m qbank.categories.A.semantic_duplicates`. The check compares identical targets under the same qubit labels; equivalence up to relabelling is handled by the permutation-invariant duplicate check above. Task pack v2 contains none of the excluded copies.\n")
    a("## 7. Baselines and best_known definitions\n")
    a("- Each (instance, tool, track) gets 60 s of single-core wall-clock time: deterministic tools run once; rustiq (with the seed patch) is rerun with different seeds within the budget and the best result is kept. Connectivity tracks use \"synthesis tool + LightSABRE routing (fixed seed, output after routing and before optimization)\", plus Qiskit's native LNN synthesis. Output checking has a separate 600 s limit that does not count toward the tool budget.")
    a("- Statuses: pass, fail, tool error, unsupported, timeout, crash, unverified, unavailable. The heuristic mode of MQT QMAP crashes every time (SIGSEGV), recorded as observed.")
    a("- Externally released circuits (circuits released by MQT QECC, QECirc) are each verified by this benchmark's checkers and recounted under these definitions, then recorded as baselines (`published:*`, `qecirc:*`). Encoder circuits are also counted, with a note, if they satisfy css_logical_zero after setting the logical inputs to \\|0⟩.")
    a("- Published values (`data/v1/published/A.jsonl`) carry the paper, arXiv number, table number, original value and access date. They count toward best_known only when the metric semantics and the code are identical; values without released circuits are marked \"reported value only\".")
    a("- best_known = min(verified baselines, eligible published values), with the source stated.\n")
    a("## 8. Known optima (probe)\n")
    a("- `cnot_model_optimum`: obtained with MQT QECC `exact.synthesize_isometry_exact` (CSS_STATE, gate-count objective, z3), counted as proven only when the solver reports `proven_optimal`; it is an **upper bound** on the optimum over general Clifford circuits, so \"the gap of the baselines to it\" is a lower bound on the true gap.")
    a("- `clifford_completion_upper_bound`: the optimum found by QMAP SAT (two-qubit gate objective) for **one particular** Clifford completion of the target state, feasible only for n ≤ 3 in measurements. It is not the state-preparation optimum: e.g. on rand_stab n3 s40308 QMAP gives 3 while stim/rustiq/pytket give 1. It is therefore only an upper bound, not counted as a proven optimum.")
    a("- `lower_bound_attained`: Iceberg (GHZ) needs at least n−1 two-qubit gates, and this is attainable.\n")
    a("## 9. Known limitations\n")
    a("- c4c6 (Knill C4/C6, L ≥ 3) is not included: the logical-operator convention of C6 could not be verified from primary sources.")
    a("- The M bin of bb_rand in val has only 1 instance (target 4): under conservative deduplication, all 9 refill draws had the same code invariants as train codes.")
    a("- For code pairs with n > 60 and identical invariants, no exact test of permutation equivalence is done; they are all conservatively treated as duplicates.")
    a("- The true optimum of general Clifford states was not obtained (QMAP SAT gives only the optimum of one completion, an upper bound); the CNOT-model optimum is limited by SAT size (n ≤ 9-12 in measurements).")
    a("- On small codes existing tools often already reach the best literature values; the training signal comes mainly from medium and large instances.")
    a("- \"Proven optimum\" holds only in the CNOT model (|0⟩/|+⟩ initialization + CNOTs only) and is only an upper bound for general Clifford circuits; the report always calls it \"CNOT-model optimum\".")
    a("- color_666 d9, color_488 d9, qrm.m7 and qhamming r7 in test_in are not larger than the largest training code of their family (color d13 and QRM(2,7) are in train), so for these families they are not size-extrapolation instances (they are different codes; no leak).")
    a("- The quantum Hamming and QRM(1, r) families share four targets (see section 6); evaluations exclude the copies listed in `data/v1/splits/semantic_duplicates_A.json` by default.")
    a("- toric and unrot_surface in test_ood are close relatives of rot_surface in training (all surface-code families), so OOD results should be reported per family (see the \"test_ood by source/family\" table in the report).")
    a("- The machine is an Apple M3 Max (12 performance cores + 4 efficiency cores). When baselines run 10-16 single-core jobs in parallel, the OS schedules some jobs on efficiency cores, where the same 60 s wall-clock budget corresponds to less compute, so the effective compute per record is not perfectly uniform (each record stores hardware information). This mainly affects tools that improve over time (rustiq, SABRE, pebbling SAT, etc.) and has no effect on deterministic tools.")
    a("- The 60 s budget underestimates some tools: rustiq needs 65-70 s on large codes such as BB108 and is recorded as a timeout at 60 s; the quality-time curve (0.1x/1x/10x budget) is in the report.")
    a("- The \\|0_L⟩ of non-CSS codes depends on the logical Z basis published by this benchmark (given in `stabilizers` in public).\n")
    a("## 10. Reproduction\n")
    a("```\nbash env/bootstrap_env.sh           # environment (official PyPI, hash-locked, rustiq seed patch, ABC)\nbash data/v1/external/fetch_A.sh    # external sources (fixed commits)\nqbank generate A && qbank import A && qbank baselines A && qbank optimal A && qbank aggregate A && qbank report A\n```")
    text = "\n".join(L) + "\n"
    p = data_root() / "A" / "DATASHEET.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return str(p)
