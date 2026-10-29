# qbank: a benchmark for quantum circuit optimisation

qbank is a bank of quantum circuit optimisation tasks with exact correctness checks. Each task asks for a circuit that
meets a precise contract (prepare a state, implement an oracle, route a circuit on a device graph, ...) at the lowest
possible cost (two-qubit gates, T gates, SWAPs, ...). Every instance comes with:

- an exact **contract checker**: a circuit counts only if the checker returns `pass`; "unverified" never counts;
- costs recomputed by the bank itself (`qbank.core.costs`), never taken from a tool's own report;
- **reference values** from classical tools run under a fixed budget (one core, 60 s), every output verified;
- **known optima or lower bounds** where they can be proven, each with its proof or certificate;
- a fixed place in **frozen splits** (train / val / test_in / test_ood / probe) and, for test instances, 3 equivalent
  variants (qubit relabelling, change of generators, both).

This is qbank v1. Per-category details: `data/v1/<C>/DATASHEET.md`; reports: `results/2026-10-29/`.

## Categories

| | Task | Main cost | Instances |
|---|---|---|---|
| A | prepare a stabilizer state or the logical \|0⟩ of a stabilizer code (rotated surface, color, Reed-Muller, Hamming, bivariate bicycle, generalised bicycle, random CSS, hypergraph-product, ... codes) on all-to-all, grid or line connectivity | two-qubit gates | 504 |
| B | compile a classical Boolean function into a bit-flip or phase oracle (arithmetic, comparisons, S-boxes, ISCAS/MCNC/EPFL circuits, SAT formulas, ...) | T count with measurement-based uncomputation (`t_mbu@inf`); Toffoli count; CX count; Toffoli count under a qubit budget | 529 |
| C | route a circuit (QAOA, Trotter, QUEKO, QUBIKOS, HamLib, MQT Bench) on a device coupling graph with a free initial layout; blocks of commuting gates may be reordered on the commuting track | inserted SWAPs | 1605 |
| D | prepare an arbitrary (complex-amplitude) target state from \|0...0⟩ without ancillas or measurements | CX count | 530 |

Splits (all frozen; `qbank split <C> --check` verifies them):

| | train | val | test_in | test_ood | probe | total |
|---|---|---|---|---|---|---|
| A | 206 | 69 | 105 | 90 | 34 | 504 |
| B | 254 | 75 | 88 | 92 | 20 | 529 |
| C | 540 | 180 | 270 | 555 | 60 | 1605 |
| D | 245 | 75 | 92 | 88 | 30 | 530 |
| total | 1245 | 399 | 555 | 825 | 144 | 3168 |

test_in holds new instances of the training families (partly within, partly beyond the training sizes); test_ood holds
families or sources never seen in training; probe holds small instances with known optima. Seed ranges of the splits are
disjoint, and equivalent variants stay in the split of their instance.

## Contracts in brief

- **A**: the circuit (Clifford gates: H, S, S†, X, Y, Z, √X, CX, CZ, CY, SWAP) must prepare exactly the target stabilizer group; free
  single-qubit Pauli corrections are applied by the checker; an optional output map (code qubit -> physical qubit) is
  accepted on every track (on all-to-all tracks it cannot lower the cost, since renaming the qubits of the whole circuit
  gives the same gates). Two independent checkers (stim and a GF(2) symplectic propagation) must agree.
- **B**: |x⟩|y⟩|0⟩ -> |x⟩|y ⊕ f(x)⟩|0⟩ (bit-flip) or (-1)^f(x)|x⟩|0⟩ (phase), every phase exactly +1, ancillas back to
  |0⟩. Exhaustive simulation up to 22 register bits, a SAT miter above. On `t_mbu@inf` the gate `mbu` (X-basis
  measurement with a classically controlled diagonal correction, which may not act on the measured qubit) is allowed.
- **C**: the routed circuit must equal the input circuit under the declared initial layout and the final permutation,
  using two-qubit gates only on coupling edges.
- **D**: fidelity with the target ≥ 1 - 1e-9; gate set: single-qubit gates, CX, CZ; no ancillas, no measurements.

## Reference values, optima and bounds

- Baselines: about 71 000 runs of 245 tool configurations (Qiskit, pytket, stim, rustiq, MQT QMAP/QECC, mockturtle,
  ABC, qclib, BQSKit, OLSQ2, SAT-based pebbling, ...), one core and 60 s each; `data/v1/baselines/<C>/records.jsonl` has every
  run (status, costs, times, hardware, concurrency).
- `best_known.jsonl`: the best verified baseline per (instance, track), plus a published value where its semantics
  match the contract; such a value is marked `source_kind: "published"` and its verified part is
  `best_baseline_value`. `score()` uses the verified value by default.
- `data/v1/optimal/<C>.jsonl`: proven optima, proven lower bounds (with proof or certificate), unproven numerical
  references (`unproven_bound`, `numerical_optimum`) and published upper bounds, each labelled with its kind. Category A's
  "optimal" values are optimal in the CNOT model (an upper bound for general Clifford circuits).
- For B's Toffoli side track `tof_clifford@inf` the reference is the cheapest verified circuit of the instance's other
  tracks that passes that track's contract.
- Reproducibility: `qbank repro <C>` re-runs 20 random baseline records; deterministic tools must reproduce gate by
  gate; qclib (category D), whose results depend on the platform's floating-point linear algebra, must pass the checker
  and its cost difference is recorded.

## Evaluation interface

`qbank.eval.api`, independent of any optimisation framework:

| Function | Purpose |
|---|---|
| `load_split(category, split, subset=None, include_duplicates=False)` | instances of one split (for the evaluator; includes private fields); `subset` filters on private fields, e.g. B's `"structural"` or `"solution_sparse"`; tasks listed under two names (`data/v1/splits/semantic_duplicates_A.json`) are left out unless `include_duplicates` |
| `public_view(instance)` | the only part a candidate program may see |
| `best_known(instance_id, track)` | the best_known record (value and source) |
| `verify(instance, circuit, track, ...)` | exact contract check (C also takes `initial_layout`; A and D may take an `output_map`) |
| `cost(circuit, metric)` | cost recomputed by the costs module |
| `score(instance, track, circuit, ...)` | verify + cost + ratio to the best verified baseline (a published value, if any, is listed separately) |

```python
from qbank.eval.api import load_split, public_view, verify, score
inst = load_split("D", "train")[0]
# category B, structural families only: load_split("B", "train", subset="structural")
view = public_view(inst)                      # give only this to the candidate program
circ = candidate(view)                        # returns a qbank.core.circuit.Circuit
v = verify(inst, circ, track="cx")            # only v.status == "pass" counts
print(score(inst, "cx", circ))                # value, reference value, ratio
```

## Commands

```
bash rebuild_all.sh                        # rebuild from scratch: environment -> external data -> all categories -> reports -> tests (tens of CPU hours, resumable)
.venv/bin/qbank generate <C>               # instances, variants and (unfrozen) splits
.venv/bin/qbank baselines <C> --workers 10 # baselines (one core, 60 s per instance x tool x track; cached in data/v1/cache/<C>/)
.venv/bin/qbank optimal <C>                # known optima / lower bounds
.venv/bin/qbank aggregate <C>              # baseline table and best_known
.venv/bin/qbank report <C> | all           # reports and datasheets
.venv/bin/qbank split <C> --freeze|--check # freeze / check the splits
.venv/bin/qbank export <C> --out DIR       # export pack for optimisation experiments (public part of train/val only)
.venv/bin/qbank prompt-lint <C> FILE       # check that a task description leaks no test instance or held-out family
.venv/bin/qbank curve <C>                  # quality-time curve: 0.1x / 10x budget re-runs on a stratified subset (not in best_known)
.venv/bin/qbank repro <C>                  # baseline reproducibility
.venv/bin/qbank rebaseline <C> --split test --tools T ...   # re-run time-limited baselines at a fixed concurrency, stored separately
bash env/build_minmc.sh                    # category B mockturtle XAG tool and 6-input database
```

## Layout

```
qbank/
  env/                 bootstrap_env.sh (isolated venv + Rust + rustiq + ABC), build_minmc.sh, minmc/, patches/
  requirements.lock.txt  pip-tools hash lock (official PyPI)
  src/qbank/
    core/              circuits, costs, content hashes, seeds, splits, instance store, GF(2)/Pauli/AIG/SAT tools
    contracts/         stabilizer (A), oracle (B), routing (C), state (D)
    categories/<C>/    generate.py, build.py, instances.py (verify dispatch), external.py, published.py
    baselines/         tools_<c>.py, job_<c>.py, runner.py, aggregate.py, repro.py, curve.py
    optimal/           a_optimal.py, c_optimal.py, bde_optimal.py
    eval/              api.py (evaluation interface), export.py (export packs)
    report/            reports and datasheets
  data/v1/
    instances/<C>/public/<hash>.json   what a candidate program may see (no id, family or source)
    instances/<C>/private/<id>.json    all other fields, including provenance and licence of external instances
    splits/                            frozen split manifests, FROZEN.sha256, semantic_duplicates_A.json
    baselines/<C>/                     records.jsonl, best_known.jsonl, curve.jsonl, repro.json
    optimal/, published/, external/    optima and bounds, published values, download scripts and checksums
    <C>/DATASHEET.md                   datasheet of each category
  results/2026-10-29/  REPORT.md (overview), REPORT_<C>.md, CSV tables
  tests/               negative controls of the contracts, data integrity, reproducibility
```

## Repository contents

The repository holds code, tests, documentation, reports, all instances and all reference values. Not included because
of their size (about 10 GB in total): the baseline circuits (`data/v1/baselines/<C>/circuits/`, `best_circuits/`, to
which the `circuit_path` fields of `best_known.jsonl` point), the run cache (`data/v1/cache/`) and the equivalent
variants (`data/v1/variants/`, rebuilt by `qbank generate`). Tests that need these files (baseline reproduction,
variants, full rebuilds) need the complete data.

288 instances are built from external data whose source states no licence (HamLib, QUBIKOS, SATLIB, ISCAS-85, MCNC;
list in `data/v1/UNLICENSED_SOURCES.tsv`).

## Principles

- An instance is a problem, not an answer; its content hash (SHA-256 with prefix `qbank-v1\n`) identifies the problem;
  public and private parts are stored separately.
- External code and data are pinned to official sources, commits and sha256 checksums.
- Splits are never edited once frozen; a change of instances is a new data version with its reason recorded.
