"""Build category B: generate -> dedup across splits -> write instances -> variants -> split manifest."""
from __future__ import annotations

import base64
import math
import itertools
import json
import time
from collections import defaultdict

import numpy as np

from ...core.aig import AIG
from ...core.canon import content_hash, dump_json, hash_hex
from ...core.instance import data_root, write_instances
from ...core.seeds import rng_for
from ...core.splits import build_manifest, write_manifest
from . import generate as G

SPLIT_RULES = ("B v1: T families (rand3sat, triangle, sudoku, simon3, compare, arith) -> train/val/test_in; random "
               "families: 12 train / 4 val seeds per size bin (S 6-12, M 13-18, L 19-24 inputs), test_in = XL (40-64 "
               "inputs) + 2 new seeds per train bin; deterministic functions by parameter (small -> train, L -> val, "
               "largest -> test_in); external sources (SATLIB, EPFL, S-boxes) -> test_ood; probe = small instances with a "
               "model-optimal value. Seed ranges disjoint per split.")


def invariants(inst) -> tuple:
    """Invariant under input permutation and input negation: n, m, per-output (weight, sorted cofactor-weight pairs)."""
    pub = inst.public
    aig = AIG.from_aiger(base64.b64decode(pub["aiger_b64"]))
    n = aig.num_inputs
    if n > 22:
        return ("big", n, len(aig.outputs), pub["task"])
    tt = aig.truth_tables()
    x = np.arange(1 << n)
    outs = []
    for row in tt:
        w = int(row.sum())
        cof = sorted(tuple(sorted((int(row[(x >> i) & 1 == 0].sum()), int(row[(x >> i) & 1 == 1].sum())))) for i in range(n))
        outs.append((w, tuple(cof)))
    return ("tt", n, len(aig.outputs), pub["task"], tuple(sorted(outs)))


def find_cross_split_duplicates(planned) -> list[dict]:
    groups = defaultdict(list)
    for p in planned:
        groups[invariants(p.inst)].append(p)
    out = []
    for inv, ps in groups.items():
        for x, y in itertools.combinations(ps, 2):
            if x.split == y.split:
                continue
            same = x.inst.hash == y.inst.hash
            if inv[0] == "big" and not same:
                continue       # > 22 inputs: invariants too weak to be meaningful; only exact identity is flagged
            out.append({"a": x.inst.id, "b": y.inst.id, "splits": [x.split, y.split],
                        "verdict": "identical function" if same else "equal NP-invariants (treated as duplicate)",
                        "duplicate": True})
    return out


# v1.2: "solution-sparse" is decided per instance from the fraction of satisfying inputs, not by family name.
# Rule: a single-output function with n inputs is solution-sparse
# iff n_solutions / 2^n < 2^(-n/2), i.e. n_solutions < 2^(n/2). Multi-output functions are never solution-sparse.
SPARSE_RULE = "single output and n_solutions < 2^(n/2)  (fraction n_solutions / 2^n < 2^(-n/2))"


def is_solution_sparse(n: int, n_solutions: int | None) -> bool:
    return n_solutions is not None and n_solutions * n_solutions < (1 << n)    # n_solutions < 2^(n/2), exact


def _sat_output(aig: AIG, j: int, value: int) -> bool:
    """Is output j equal to `value` for some input? (Tseitin CNF + CaDiCaL)"""
    from pysat.solvers import Solver
    I = aig.num_inputs
    cls = []
    for k, (a, b) in enumerate(aig.ands):
        v = I + 1 + k
        la = (a >> 1) * (-1 if a & 1 else 1)
        lb = (b >> 1) * (-1 if b & 1 else 1)
        cls += [[-v, la], [-v, lb], [v, -la, -lb]]
    o = aig.outputs[j]
    if (o >> 1) == 0:
        return bool(o & 1) == bool(value)
    lit = (o >> 1) * (-1 if o & 1 else 1)
    cls.append([lit if value else -lit])
    with Solver(name="cadical195", bootstrap_with=cls) as s:
        return bool(s.solve())


def is_constant(inst) -> bool:
    """Semantic check (v1.1): an output that never takes one of the two values is constant (e.g. an unsatisfiable
    formula); a function all of whose outputs are constant has the empty circuit as oracle."""
    aig = AIG.from_aiger(base64.b64decode(inst.public["aiger_b64"])).cleanup()
    return all(not _sat_output(aig, j, 1) or not _sat_output(aig, j, 0) for j in range(len(aig.outputs)))


def count_solutions(inst, cap: int = 1 << 16) -> tuple[int | None, str]:
    """Exact number of inputs with f(x) = 1 for a single-output function: exhaustive for n <= 22, otherwise an exact
    BDD model count (node limit), otherwise SAT enumeration with blocking clauses up to `cap` solutions.
    Returns (count or None, method)."""
    from ...baselines.tools_b import enumerate_solutions
    from ...core.modelcount import bdd_count
    aig = AIG.from_aiger(base64.b64decode(inst.public["aiger_b64"]))
    if len(aig.outputs) != 1:
        return None, "multi-output"
    if aig.num_inputs <= 22:
        return int(aig.truth_tables()[0].sum()), "exhaustive"
    c = bdd_count(aig)
    if c is not None:
        return c, "BDD model count"
    s = enumerate_solutions(aig, time.monotonic() + 120, cap=cap)
    return (None, f"unknown (more than {cap} solutions or enumeration timeout)") if s is None else (len(s), "SAT enumeration")


def drop_trivial_and_same_split(planned, log) -> tuple[list, list]:
    """Constant functions (e.g. a triangle-free graph) have the empty circuit as oracle: dropped. Identical functions
    within one split: the later one is dropped. Random families are refilled from new seeds of the same split."""
    out, seen, report = [], {}, []
    for p in planned:
        why = "constant function" if is_constant(p.inst) else ("same-split duplicate of " + seen[p.inst.hash]) \
            if p.inst.hash in seen else None
        if why is None:
            out.append(p)
            seen[p.inst.hash] = p.inst.id
            continue
        rep = None
        if p.regen is not None:
            for attempt in range(1, 20):
                new = G.regenerate(p, attempt)
                if not is_constant(new.inst) and new.inst.hash not in seen:
                    rep = new
                    break
        if rep is not None:
            out.append(rep)
            seen[rep.inst.hash] = rep.inst.id
        report.append({"dropped": p.inst.id, "reason": why, "replacement": rep.inst.id if rep else None})
    if report:
        log(f"[build B] dropped {len(report)} trivial / same-split duplicate instances, refilled "
            f"{sum(1 for r in report if r['replacement'])}")
    TRIVIAL.extend(report)
    return out, report


TRIVIAL: list = []


def permute_inputs(aig: AIG, perm: list[int], out_perm: list[int] | None = None) -> AIG:
    """New AIG with input i moved to position perm[i] (and output j to out_perm[j])."""
    n = aig.num_inputs
    names_in = list(aig.input_names) if aig.input_names else [None] * n
    g = AIG(n, input_names=[None] * n)
    for i in range(n):
        g.input_names[perm[i]] = names_in[i]
    lit = {0: 0}                                   # variable of the old AIG -> literal of the new AIG
    for i in range(n):
        lit[i + 1] = 2 * (perm[i] + 1)

    def m(l):
        return lit[l >> 1] ^ (l & 1)
    I = aig.num_inputs
    for j, (a, b) in enumerate(aig.ands):
        lit[I + 1 + j] = g.AND(m(a), m(b))          # strashing may return any literal (incl. complemented / constant)
    outs = [m(l) for l in aig.outputs]
    names = list(aig.output_names) if aig.output_names else [None] * len(outs)
    if out_perm is not None:
        o2, n2 = [None] * len(outs), [None] * len(outs)
        for j, pj in enumerate(out_perm):
            o2[pj], n2[pj] = outs[j], names[j]
        outs, names = o2, n2
    for l, nm in zip(outs, names):
        g.add_output(l, nm)
    return g.cleanup()


def write_variants(planned) -> int:
    root = data_root() / "variants" / "B"
    if root.exists():
        import shutil
        shutil.rmtree(root)
    count = 0
    for p in planned:
        if p.split not in ("test_in", "test_ood"):
            continue
        pub = p.inst.public
        aig = AIG.from_aiger(base64.b64decode(pub["aiger_b64"]))
        n, m = aig.num_inputs, len(aig.outputs)
        rng = rng_for("B-variants", p.inst.hash)
        specs = [("input_perm", rng.permutation(n).tolist(), None), ("input_perm", rng.permutation(n).tolist(), None),
                 ("input_perm+output_perm" if m > 1 else "input_perm", rng.permutation(n).tolist(),
                  rng.permutation(m).tolist() if m > 1 else None)]
        for i, (kind, perm, operm) in enumerate(specs, start=1):
            a2 = permute_inputs(aig, perm, operm)
            pub2 = json.loads(json.dumps(pub))
            pub2["aiger_b64"] = base64.b64encode(a2.to_aiger_binary()).decode()
            pub2["input_names"], pub2["output_names"] = a2.input_names, a2.output_names
            canon = {"function": G.function_canon(a2), "task": pub["task"], "tracks": pub["tracks"], "gate_set": pub["gate_set"]}
            v = {"variant_of": p.inst.hash, "variant_id": f"{p.inst.hash}#v{i}", "kind": kind, "split": p.split,
                 "transform": {"input_perm": perm, "output_perm": operm}, "public": pub2,
                 "hash": content_hash("B", pub["task"], canon)}
            dump_json(v, root / hash_hex(p.inst.hash) / f"v{i}.json")
            count += 1
    return count


def build(include_external: bool = True, log=print) -> dict:
    t = time.time()
    planned = G.generate_all(log=log)
    if include_external:
        from . import external
        planned += external.generate_external(log=log)
        planned += external.generate_probe(log=log)
    log(f"[build B] {len(planned)} instances in {time.time() - t:.0f}s")
    planned, trivial = drop_trivial_and_same_split(planned, log)
    dups = find_cross_split_duplicates(planned)
    order = {"train": 0, "val": 1, "test_in": 2, "test_ood": 3, "probe": 4}
    split_of = {p.inst.id: p.split for p in planned}
    drop = {max((d["a"], d["b"]), key=lambda i: order[split_of[i]]) for d in dups}
    refills = []
    if drop:
        dropped = [p for p in planned if p.inst.id in drop]
        planned = [p for p in planned if p.inst.id not in drop]
        inv_of = {p.inst.id: invariants(p.inst) for p in planned}
        for old in dropped:
            if old.regen is None:
                refills.append({"dropped": old.inst.id, "replacement": None})
                continue
            for attempt in range(1, 10):
                new = G.regenerate(old, attempt)
                inv = invariants(new.inst)
                if not any(inv_of[p.inst.id] == inv and p.split != new.split for p in planned) and \
                        not any(p.inst.hash == new.inst.hash for p in planned):
                    planned.append(new)
                    inv_of[new.inst.id] = inv
                    refills.append({"dropped": old.inst.id, "replacement": new.inst.id, "attempts": attempt})
                    break
            else:
                refills.append({"dropped": old.inst.id, "replacement": None})
        log(f"[build B] dropped {len(drop)} cross-split duplicates, refilled {sum(1 for r in refills if r['replacement'])}")
    unknown = []
    for p in planned:                           # solution-sparse instances are reported separately (v1.1; rule v1.2)
        c, how = count_solutions(p.inst)
        n_in = int(p.inst.public["n_inputs"]) if "n_inputs" in p.inst.public else \
            AIG.from_aiger(base64.b64decode(p.inst.public["aiger_b64"])).num_inputs
        p.inst.private["n_solutions"] = c
        p.inst.private["n_solutions_method"] = how
        p.inst.private["solution_fraction_log2"] = (round(math.log2(c) - n_in, 4) if c else None) if c is not None else None
        p.inst.private["solution_sparse"] = is_solution_sparse(n_in, c)
        if c is None and not how.startswith("multi"):
            unknown.append(p.inst.id)
    if unknown:
        log(f"[build B] solution count unknown (treated as not solution-sparse): {unknown}")
    from . import extend_v13          # data version 1.3.0 (10-28): parametrised structural sub-types, train / val only
    ext, ext_report = extend_v13.extension([p.inst for p in planned], log)
    planned += ext
    write_instances("B", [p.inst for p in planned])
    nvar = write_variants(planned)
    man = build_manifest("B", [(p.split, p.inst.id, p.inst.hash, p.inst.family, p.inst.private.get("size_bin")) for p in planned],
                         SPLIT_RULES + " | " + extend_v13.RULES_NOTE)
    write_manifest("B", man)
    rep = {"n_instances": len(planned), "cross_split_pairs": dups, "dropped": sorted(drop), "refills": refills,
           "variants": nvar, "totals": man["totals"], "excluded_unverifiable": list(G.EXCLUDED), "trivial_or_same_split_dropped": list(TRIVIAL),
           "solution_sparse_rule": SPARSE_RULE, "solution_count_unknown": unknown}
    dump_json(rep, data_root() / "instances" / "B" / "build_report.json")
    dump_json(ext_report, data_root() / "instances" / "B" / f"extension_v{extend_v13.VERSION}.json")
    return rep
