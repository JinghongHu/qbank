"""Evaluation interface for evolution experiments, independent of any evolution framework.

    from qbank.eval.api import load_split, public_view, best_known, verify, cost, score
    insts = load_split("A", "train")                  # list of Instance (harness side; contains private fields)
    insts = load_split("B", "train", subset="structural")   # optional subset filter (qbank.eval.subsets)
    view = public_view(insts[0])                      # the ONLY thing to hand to a candidate program
    circ, omap = my_candidate(view)                   # candidate returns a qbank Circuit (+ optional output map)
    v = verify(insts[0], circ, track="a2a_2q", output_map=omap)
    if v.status == "pass":
        score = cost(v.circuit, "two_qubit_gates") / best_known(insts[0].id, "a2a_2q")["value"]

Candidates must only ever receive public_view(...). Test splits are for the single final evaluation.
"""
from __future__ import annotations

import json
from functools import lru_cache

from ..core.circuit import Circuit
from ..core.costs import cost as _cost
from ..core.instance import Instance, data_root, load_instance
from ..core.instance import public_view as _public_view
from ..core.splits import load_split as _load_split


def evaluation_exclusions(category: str) -> set:
    """Instances to leave out of every evaluation (10-29): the later copy of a task that appears under two names
    (data/v1/splits/semantic_duplicates_<C>.json; A: quantum Hamming = punctured QRM(1, r))."""
    p = data_root() / "splits" / f"semantic_duplicates_{category}.json"
    if not p.exists():
        return set()
    return {i for g in json.loads(p.read_text(encoding="utf-8"))["groups"] for i in g["exclude_from_evaluation"]}


def load_split(category: str, split: str, subset: str | None = None, include_duplicates: bool = False) -> list[Instance]:
    """Instances of one split; `subset` (e.g. B: "structural" / "solution_sparse", see qbank.eval.subsets) filters by a
    private field of each instance. The instances of evaluation_exclusions() are left out unless include_duplicates."""
    from .subsets import predicate
    keep = predicate(category, subset)
    drop = set() if include_duplicates else evaluation_exclusions(category)
    insts = [load_instance(category, e["id"]) for e in _load_split(category, split) if e["id"] not in drop]
    return insts if keep is None else [i for i in insts if keep(i.private)]


def public_view(instance: Instance) -> dict:
    return _public_view(instance)


@lru_cache(maxsize=8)
def _best_table(category: str) -> dict:
    p = data_root() / "baselines" / category / "best_known.jsonl"
    out = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[(r["instance_id"], r["track"])] = r
    return out


def best_known(instance_id: str, track: str, category: str | None = None) -> dict | None:
    cat = category or instance_id.split(".", 1)[0]
    return _best_table(cat).get((instance_id, track))


def verify(instance: Instance, circuit: Circuit, track: str = "a2a_2q", output_map=None, *, initial_layout=None):
    """Exact contract check of a candidate answer (uses only instance.public). Per category the answer is:
      A  circuit (+ optional output_map on every track)  B  circuit
      C  routed circuit + initial_layout                 D  circuit (+ output_map on depth2q@line)
    Returns a verdict with .status in {pass, fail, unverified, checker_disagreement, error}; only "pass" counts."""
    cat = instance.category
    if cat == "A":
        from ..categories.A.instances import verify as v
        return v(instance.public, track, circuit, output_map)
    if cat == "B":
        from ..categories.B.instances import verify as v
        return v(instance.public, track, circuit, output_map)
    if cat == "C":
        from ..categories.C.instances import verify as v
        return v(instance.public, track, circuit, initial_layout)
    if cat == "D":
        from ..categories.D.instances import verify as v
        return v(instance.public, track, circuit, output_map)
    raise ValueError(f"unknown category {cat}")


def cost(circuit: Circuit, metric: str = "two_qubit_gates"):
    return _cost(circuit, metric)


def track_metric(instance: Instance, track: str) -> str:
    return instance.public["tracks"][track]["metric"]


def verified_reference(entry: dict | None):
    """The value of the best VERIFIED baseline of a best_known entry (10-29, Codex review): a best_known entry may be a
    published value that this bank has not verified (source_kind "published", verified False); its verified part is
    best_baseline_value."""
    if not entry:
        return None
    if entry.get("source_kind") == "baseline" and entry.get("verified", True):
        return entry.get("value")
    return entry.get("best_baseline_value")


def score(instance: Instance, track: str, circuit: Circuit, reference: str = "verified", **answer) -> dict:
    """verify + cost + comparison with a reference (lower is better on every qbank metric).
    reference="verified" (default): the best verified baseline (verified_reference); "best_known": best_known as stored,
    which may be an unverified published value (reported separately as `published` in either case)."""
    v = verify(instance, circuit, track, answer.pop("output_map", None), **answer)
    out = {"status": v.status, "reason": getattr(v, "reason", "")}
    if v.status != "pass":
        return out
    m = track_metric(instance, track)
    val = cost(circuit, m)
    bk = best_known(instance.id, track, instance.category)
    ref = verified_reference(bk) if reference == "verified" else (bk["value"] if bk else None)
    out.update(metric=m, value=val, reference=reference, reference_value=ref,
               best_known=bk["value"] if bk else None,
               published=(bk["value"] if bk and bk.get("source_kind") == "published" else None),
               ratio=(val / ref) if ref else None)
    return out
