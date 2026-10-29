"""DATASHEETs for categories B-D: data/v1/<C>/DATASHEET.md. Tables are computed from data/v1 files;
the prose documents contracts, checkers, limits, sources and known limitations (all stated in the code as well)."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date

from ..core.instance import data_root, load_index
from ..core.splits import load_manifest

DOC = {
"B": {
 "version": "1.3.0",
 "title": "Category B (classical-function oracle compilation)",
 "task": [
  "- **oracle_bitflip_clean**: |x⟩|y⟩|0_anc⟩ → |x⟩|y ⊕ f(x)⟩|0_anc⟩; the phase must be exactly +1 for every input (including relative phases; nothing beyond a global phase is allowed); ancillas must return to |0⟩.",
  "- **oracle_phase_clean** (single output): |x⟩|0_anc⟩ → (−1)^{f(x)} |x⟩|0_anc⟩.",
  "- **Gate set**: x, cx, ccx, ccz, rccx, rc3x, swap, z, s, sdg, t, tdg, cz; the t_mbu track additionally allows `mbu` (X-basis measurement + classically controlled diagonal correction).",
  "- **`mbu` rule**: the classically controlled correction of an `mbu` may not act on the measured qubit; such a circuit is rejected before any simulation (negative test in `tests/test_b_contracts.py`). None of the 226,854 `mbu` gates of the stored baseline circuits acts on its measured qubit.",
  "- **Tracks**: tof@bmin, tof@1.5bmin (qubit budget = the minimum width b_min of the verified constructive baselines, and 1.5 times it), tof@inf (Toffoli/AND count), t_mbu@inf (T count, measurement-based uncomputation allowed), cx@inf (CX count, fixed decomposition: ccx = 6 CX), and the Toffoli side track tof_clifford@inf (contract version 2: Clifford + Toffoli-type gates, no `mbu`, cost = Toffoli count).",
  "- **Main track**: the task packs and the paper use `t_mbu@inf` as B's main track; the tool-share table of this bank's report uses `tof@inf` as \"main track\", and the report gives the full results of every track.",
  "- **Contract versions**: the tof_clifford@inf track exists on the 63 parametrised structural instances (compare.lt_const, compare.interval, arith.threshold, arith.mul_bit), whose public records carry contract version 2; the public records of the other 466 instances carry contract version 1 and have no such track.",
  "- **Cost definitions**: Toffoli count (ccx/ccz/rccx count 1, rc3x counts 2); T count (ccx 7, ccz 7, rccx 4, rc3x 8, fixed after decomposition per the Qiskit 2.5.2 definitions); CX count (ccx 6, rccx 3, rc3x 6, swap 3)."],
 "check": [
  "- Before any simulation the checker validates the circuit width and the number of qubits and parameters of every gate; an exception inside the checker is recorded as `error` (never a pass).",
  "- Input + output registers ≤ 22 qubits: bit-parallel exhaustive simulation (uint64, phases kept as mod-8 bit planes), RCCX/RC3X via monomial tables, exact comparison including phases.",
  "- Above 22 qubits: SAT equivalence miter (CaDiCaL 1.9.5, run in a subprocess, 600 s hard limit); when the circuit contains non-±1 phases (S/T/RCCX/RC3X) no symbolic phase check is possible and the result is \"unverified\".",
  "- Negative controls in `tests/test_b_contracts.py` (wrong phase, ancilla not cleaned, gate outside the gate set, over budget).",
  "- **Optimum reference for probe**: the multiplicative complexity MC(f) (minimum number of AND gates, XOR free) is computed exactly with SAT. Every reversible circuit with t Toffoli-type gates corresponds to an XAG with t AND gates, so Toffoli count ≥ MC(f); compiling an MC-optimal XAG into an oracle uses at most 2·MC(f) − 1 Toffolis (verified circuits stored in `optimal/B.jsonl`). The optimum is therefore bracketed in [MC, 2·MC − 1]. SAT solving is slow for 6-input functions; when it does not finish, the lower bound is the proven part (no less than deg − 1)."],
 "limits": [
  "- The verification limit determines the sizes: for arith/prod_parity at w ≥ 11 (23-qubit registers) the SAT miter exceeds 600 s, so test_in only goes up to w = 10.",
  "- Instances that no constructive baseline can verify exactly are not included (`excluded_unverifiable` in `build_report.json`).",
  "- Constant functions (e.g. triangle-free graphs, unsatisfiable formulas) correspond to empty circuits and are not included; unsatisfiable 3-SAT draws are rejected and redrawn (`draws_until_satisfiable`); constant functions are detected semantically (SAT), so unsatisfiable SATLIB formulas are not included.",
  "- Deduplication is up to NP equivalence (input permutation + input negation, both requiring only free X gates): all eq_const of the same width are mutually equivalent; Sudokus with a unique solution, SATLIB formulas with a single model and random 3-SAT are all \"point functions\", equivalent to eq_const. These cross-split duplicates are removed (deterministic families cannot be refilled), so eq_const effectively has a single problem per width, and the SATLIB test_ood instances are reduced accordingly.",
  "- QuantumEvo needs system dependencies such as Boost and was not built (recorded as unavailable); RevLib has no license and is not included.",
  "- **XAG baseline** (the approach of Meuli et al., ICCAD 2019, reimplemented in this benchmark): XOR uses only CNOTs, one Toffoli per AND gate; ≤ 5 inputs use an MC-optimal XAG from SAT, 6 inputs use \"optimal Shannon decomposition + exact 5-input subfunctions\", larger functions use structural XOR extraction after ABC optimization.",
  "- **\"Solve first, then compile\" baseline**: all solutions are found with SAT, then multi-controlled gates are built from the prefix tree of the solution set.",
  "- **Solution-sparse instances** are decided by the fraction of solutions (see the report), listed separately and not used for the main conclusions.",
  "- **XAG MC cut rewriting (mockturtle xag_minmc_resynthesis)**: mockturtle's (lsils/mockturtle @ d9e02495, MIT) multiplicative-complexity-oriented cut rewriting: `cut_rewriting_with_compatibility_graph` + minimum-MC database (≤ 5 inputs use mockturtle's bundled library, 6 inputs use the AND-optimal circuits of the 6-variable affine classes from NIST usnistgov/Circuits, converted to mockturtle format via kitty's spectral canonical form and each re-simulated and checked) + `mc_cost`; build script `env/build_minmc.sh`. Differences from the original implementation: exact spectral canonicalization of cut functions has a step limit (10⁴ steps during rewriting, 10⁸ steps for whole functions; cuts over the limit are not rewritten; the database lacks 6 classes whose canonicalization exceeds 10⁸ steps); networks with ≤ 6 inputs are additionally resynthesized by a whole-function database lookup, keeping whichever has fewer AND gates; cut_limit is mockturtle's default 25, and if cut rewriting at this commit triggers the topo_view assertion (a cycle appears), it is rerun with 12 (deterministic).",
  "- **Deterministic SAT budgets**: XAG + MC and pebbling SAT use SAT conflict limits (exact MC: 50k conflicts per k; pebbling: 1M conflicts per call to find the first feasible schedule, then at most 10 bisection tightening calls of 100k conflicts each), so results do not depend on wall-clock time and machine load, and they are included in the 20-record reproducibility sample; the only thing that varies with load is whether the run finishes within 60 s.",
  "- **Structural test_ood** includes three external sources (block-cipher S-boxes from RFCs, ISCAS-85, MCNC LGSynth'91), reported per source.",
  "- **Parametrised structural instances**: 63 single-output bit-flip oracles with 8-21 inputs (compare.lt_const 17, compare.interval 15, arith.threshold 16, arith.mul_bit 15; 49 in train, 14 in val). Each satisfies the strict structural rule min(#solutions, 2^n − #solutions) ≥ 2^(n/2) (exact count by enumeration), uses every input, has an NPN signature different from all other instances and from each other, and has a constructive circuit verified by the checker. Every tool was run on them (2646 jobs: 1701 pass, 876 not applicable, 69 timeout, 0 fail).",
  "- **Task-pack reference values**: for the 262 instances used by the task packs (199 other instances + the 63 parametrised structural instances) the reference circuits are verified with the current checker, cheapest first, and the first that passes gives the reference value.",
  "- **Reference values of the Toffoli side track**: tof_clifford@inf has no tool runs of its own. During aggregation (`_reuse_tof_clifford` in `aggregate.py`) the verified circuits of the instance's other tracks are verified under the `tof_clifford@inf` contract in order of Toffoli count, and the first that passes is best_known (tool name suffix `[circuit reused, re-verified on tof_clifford@inf]`). All 63 parametrised structural instances have a reference value on this track, identical to the task-pack verification.",
  "- The circuits of XAG MC cut rewriting differ strongly in structure from the original AIG, which makes the SAT miter harder above 22 qubits: on 14 large structural instances (11 simon3, majority n41/n51, mcnc my_adder) it cannot decide within 600 s; these are recorded as unverified (not counted as correct), and best_known on these instances comes from other tools; on majority n63 the tool does not finish within 60 s (timeout).",
  "- The affine class of probe s40602 (6 inputs) is one of the 6 classes missing from the database, so XAG MC cut rewriting cannot resynthesize it by whole-function lookup (13 AND gates); best_known is 12 Toffolis (XAG + MC), short of the ≤ 11 target. The optimum file contains a verified circuit with 11 Toffolis (6 AND gates), but it comes from a long-running upper-bound computation, not from the 60 s baseline."],
 "sources": "SATLIB uf20/uf50 (no license statement; uuf50 not used); EPFL combinational benchmarks @ 82d8cc69 (MIT); the AES S-box is constructed from the FIPS-197 definition; the S-box tables of Camellia, ARIA, CLEFIA, Kuznyechik and Magma are taken from the original texts of RFC 3713 / 5794 / 6114 / 7801 / 8891 (pinned by sha256, self-checked when parsed: permutation, the example values in the RFC, and the inverse table); ISCAS-85 and MCNC LGSynth'91 are taken from the benchmark collection of the Czech Technical University (the original CBL/MCNC hosts are no longer reachable; no license statement); mockturtle @ d9e02495 (MIT) and the NIST 6-variable AND-optimal circuits @ b7678d67 (the repository has no LICENSE; `env/build_minmc.sh` builds the database and checks its sha256). See `data/v1/external/fetch_B.sh` and `SOURCES_B.json`.",
},
"C": {
 "version": "1.1.0",
 "title": "Category C (routing and commuting-gate scheduling)",
 "task": [
  "- **routing_equiv**: output a routed circuit on n_physical qubits (only explicit SWAPs, no bridges) and an initial layout initial_layout[l] (the physical qubit holding logical qubit l, chosen by the method). Every two-qubit gate (including SWAPs) must lie on an edge of the coupling graph; after replaying the mapping, the circuit must be a topological reordering of the input circuit's gate DAG (gate names, parameters and qubit order identical gate by gate).",
  "- **routing_commuting**: as above, but gates within the same commuting block (`blocks` in public) may be reordered arbitrarily; between blocks the order is kept on each qubit.",
  "- **Tracks**: swaps (number of inserted SWAPs, main); depth2q (two-qubit gate depth, a SWAP counts as 3 layers); swaps_commuting (QAOA/Trotter/HamLib only, block partition given).",
  "- Input circuits contain no swap gates (swap is reserved for routing); logical gate set: h, x, y, z, s, sdg, t, tdg, sx, rz, rx, ry, cx, cz, rzz, rxx, ryy; parameters may be symbolic (name strings)."],
 "check": [
  "- Main checker: mapping replay (`qbank/contracts/routing.py`), polynomial time, no size limit.",
  "- For n_physical ≤ 16 on the routing_equiv track, MQT QCEC is used as an independent second check (symbolic parameters replaced by random values; the routing permutation is undone with SWAPs before comparing); disagreement between the two is judged \"checker disagreement\".",
  "- Negative controls in `tests/test_c_contracts.py`: missing SWAP, wrong parameter, DAG order violation, reordering across blocks, invalid initial layout."],
 "limits": [
  "- The deduplication invariant (Weisfeiler-Lehman hash) cannot distinguish regular graphs: random regular QAOA graphs of the same size in different splits are conservatively treated as duplicates (5 were actually removed and refilled).",
  "- pytket and MQT QMAP cannot take this benchmark's gates directly (symbolic parameters, rxx/ryy): they route a \"placeholder circuit\" (same interaction structure; two-qubit gates → cx/rzz, single-qubit gates → rz, leading ry labels mark the initial position of each logical qubit), which is then replayed along the DAG to substitute the original gates back.",
  "- Qiskit 2.5's Commuting2qGateRouter misreads the layout when there are several commuting blocks (`_make_op_layers` and `_position_in_cmap` use opposite directions), so from the second block on gates may land on non-adjacent qubits; this benchmark calls it block by block and tracks the permutation itself. It applies only to devices with a simple path covering all logical qubits (on heavy-hex and random sparse graphs it is often \"unsupported\").",
  "- OLSQ2 (UCLA-VAST @ 0d7066f4, patched for Qiskit 2) is a small-scale baseline (≤ 16 logical qubits, ≤ 80 gates, transition mode, SWAP objective): its SWAP count is minimal only within its time-step range and is not taken as a proven optimum. The small-scale known optima come only from QUEKO (zero-SWAP witness) and QUBIKOS (constructed values, not independently verified).",
  "- In the qiskit-ibm-runtime version used, FakeCairoV2 has only 26 mutually connected qubits (1 isolated qubit): device selection requires the largest connected component to be ≥ the number of logical qubits, otherwise the next device tier is used.",
  "- MQT Bench's graphstate generator sets no random seed by default; this benchmark calls its create_circuit directly with a derived seed for reproducibility (covered by the full-rebuild test in `tests/test_cde_data.py`).",
  "- **test_ood is reported per source**: 300 of the 555 are QUEKO, with known optimum 0 SWAPs; the baselines already reach the optimum on most of them, so they serve mainly as a correctness check and should not be merged into a geometric-mean score; the real room for improvement is on QUBIKOS (median ratio of best baseline to constructed optimum about 15x)."],
 "sources": "QUEKO @ 2ee23a12 (BSD-3, redistributable); QUBIKOS @ 442a9948 (no license); MQT Bench 2.3.0 (MIT, INDEP level, families not used in training); HamLib v1.1 condensedmatter/tfim, heisenberg (no license on the portal). See `data/v1/external/fetch_C.sh`.",
},
"D": {
 "version": "1.0.0",
 "title": "Category D (non-Clifford state preparation)",
 "task": [
  "- **state_exact**: prepare the target state from |0…0⟩ with fidelity |⟨target|ψ⟩|² ≥ 1 − 1e−9; the comparison includes relative phases, a global phase is allowed; no ancillas allowed.",
  "- **state_approx**: fidelity ≥ 0.99, a separate track (cx@F0.99), not compared with the exact tracks.",
  "- **Tracks**: cx (CX count, all-to-all, main); depth2q@line (two-qubit gate depth under linear connectivity; an output map is allowed: qubit q of the state is carried by physical qubit output_map[q], since the input is |0…0⟩); cx@F0.99 (dense and sparse families).",
  "- **Gate set**: any single-qubit gate (h, x, y, z, s, sdg, t, tdg, sx, sxdg, rx, ry, rz, p, u) + cx, cz; parameters must be numeric.",
  "- public gives only n and the list of target amplitudes (little-endian, global phase fixed), no family name and no construction hints."],
 "check": [
  "- Main checker: an independent sparse state-vector simulation (int64 keys for n ≤ 62, Python integer keys beyond), executed in a \"support-aware\" equivalent topological order: a fused single-qubit segment runs right after the preceding two-qubit gate if it does not enlarge the support, otherwise it is postponed until just before the next two-qubit gate; this changes only the intermediate support, not the final state.",
  "- More than 2^22 intermediate nonzero entries (2^18 for n > 62) is judged \"unverified\"; for n ≤ 16 qiskit Statevector is used as a second check, and disagreement is judged \"checker disagreement\".",
  "- Negative controls in `tests/test_d_contracts.py`: angle perturbation, relative phase, ancilla, gate set, non-line edge."],
 "limits": [
  "- Dicke k = 1 is the W state, so the dicke family uses k = 2 in train/val/test_in and W is a separate family; k ≥ 3 goes only to test_ood, with C(n, k) ≤ 4096.",
  "- Dense methods (Qiskit StatePreparation, qclib LowRank/SVD/UCGE) are used only for n ≤ 14; BQSKit only for n ≤ 4 (O3 compilation at n = 5 took more than 500 s in measurements), run in a separate process group and killed when time is up.",
  "- qclib MergeInitialize is big-endian (bit-reversed keys); PivotInitialize raises an error under Qiskit 2.5.2 and is not used; CVO-QRAM and similar introduce ancillas and do not fit the ancilla-free contract.",
  "- Qiskit 2.5.2's StatePreparation produces wrong states for a few highly sparse 13-14-qubit vectors (fidelities 0.57, 0.25, 0.002 computed with Qiskit's own Statevector, and results differ between runs; another vector triggers \"Input matrix is not unitary\"). This is an upstream numerical issue, not the adapter; the checker judges these as fail, as observed.",
  "- Known optima: the n = 2 probes need 1 CX (proof in `qbank/optimal/bde_optimal.py`); n = 3 has only the lower bound 2 and the published upper bound 3 (Znidaric, Giraud & Georgeot, PRA 77, 032320 (2008)); for the other instances the proven lower bounds come only from robust certificates (`certificate` of each entry in `data/v1/optimal/D.jsonl`: n − 1 when the two-qubit correlation graph is connected, or half the number of single qubits proven to be mixed, rounded up); \"all single-qubit marginals are mixed\" alone does not imply n − 1 (e.g. two Bell pairs need only 2 CX), and an n − 1 that a certificate cannot confirm is only an unproven reference (kind `unproven_bound`: a numerical reference, never used for \"distance to optimum\").",
  "- **Known-optimum file** `data/v1/optimal/D.jsonl`: every record carries a `certificate`; a lower bound marked proven comes only from a robust certificate that holds for every state within the contract tolerance. Contents: 520 proven lower bounds, 18 unproven references, 10 proven optima, 41 upper bounds, 41 numerical optima. The D lower bounds of task pack v2 equal this file record by record."],
 "sources": "Everything is generated by this benchmark's generators from the definitions (no external data).",
},
}


def make_datasheet(cat: str, log=print) -> str:
    d = DOC[cat]
    man = load_manifest(cat)
    idx = {r["id"]: r for r in load_index(cat)}
    split_of = {e["id"]: s for s, es in man["splits"].items() for e in es}
    fam_split = defaultdict(Counter)
    fam_n = defaultdict(list)
    for iid, r in idx.items():
        fam_split[r["family"]][split_of[iid]] += 1
        if r.get("n") is not None:
            fam_n[r["family"]].append(r["n"])
    rep_p = data_root() / "instances" / cat / "build_report.json"
    rep = json.loads(rep_p.read_text()) if rep_p.exists() else {}
    L = [f"# Datasheet: qbank v1 · {d['title']}\n", f"Generated: {date.today().isoformat()} (by `qbank report {cat}` from `data/v1/`).\n",
         "## 1. Task and contract\n", *d["task"], "", "## 2. Checking method and size limits\n", *d["check"], "",
         "## 3. Families and split sizes\n", "| Family | n range | train | val | test_in | test_ood | probe |\n|---|---|---|---|---|---|---|"]
    for fam in sorted(fam_split):
        c = fam_split[fam]
        ns = fam_n.get(fam)
        rng = f"{min(ns)}-{max(ns)}" if ns else "-"
        L.append(f"| {fam} | {rng} | {c['train']} | {c['val']} | {c['test_in']} | {c['test_ood']} | {c['probe']} |")
    L.append("\nTotal: " + ", ".join(f"{s} {man['totals'][s]}" for s in man["totals"]) + f"; {sum(man['totals'].values())} instances in all.")
    L.append(f"\nSplit rules: {man['rules'].split(' | ')[0]}\n")     # the manifest's appended version notes live in versions.json
    L.append(f"Equivalent variants: {rep.get('variants', '-')} (3 per test instance, in the same split as the original, `data/v1/variants/{cat}/`).")
    if rep.get("dropped"):
        L.append(f"Cross-split deduplication removed {len(rep['dropped'])} (all refilled with new seeds from the same split or recorded); see `data/v1/instances/{cat}/build_report.json`.")
    L += ["", "## 4. Known limitations and implementation adjustments\n", *d["limits"], "", "## 5. Sources and licenses\n", d["sources"], "",
          "## 6. Baseline definitions\n",
          "- Each (instance, tool, track) gets 60 s of single-core wall-clock time; randomized/iterative tools are rerun with different seeds within the budget and the best result is kept; results delivered after the budget are recorded as timeouts; output checking has a separate 600 s window that does not count toward the tool budget.",
          "- The machine is an Apple M3 Max (12 performance cores + 4 efficiency cores). When baselines run 10-16 single-core jobs in parallel, the OS schedules some jobs on efficiency cores, where the same 60 s wall-clock budget corresponds to less compute, so the effective compute per record is not perfectly uniform (each record stores hardware information). This mainly affects tools that improve over time (rustiq, LightSABRE, OLSQ2, etc.) and has no effect on deterministic tools (category B's pebbling SAT and XAG use conflict limits and are deterministic).",
          "- Records of some baselines carry `concurrency` measured at run time (number of concurrency slots, number of jobs running at start, 1-minute load); the others carry `concurrency_estimate`, computed during aggregation (the number of simultaneously running jobs reconstructed from the start/end times of all cached records, 1 s resolution, excluding other processes). For the final evaluation, `qbank rebaseline <C> --split test --tools <time-limited tools>` reruns the time-limited baselines on test instances at fixed concurrency (default = number of performance cores); results are stored separately and best_known is not changed.",
          "- All baseline outputs are verified by this benchmark's checkers and their costs recomputed by `qbank.core.costs`; \"unverified\" never counts as correct.",
          "- best_known = min(verified baselines, published values whose semantics and budget both match), with the source stated; known optima/lower bounds in `data/v1/optimal/" + cat + ".jsonl`.", "",
          "## 7. Reproduction\n", f"```\nbash env/bootstrap_env.sh\nqbank generate {cat} && qbank baselines {cat} && qbank optimal {cat} && qbank aggregate {cat} && qbank report {cat}\n```"]
    p = data_root() / cat / "DATASHEET.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return str(p)
