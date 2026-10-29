"""Build category D: generate -> dedup across splits -> write instances -> variants -> split manifest."""
from __future__ import annotations

import itertools
import json
import math
import time
from collections import defaultdict

import numpy as np

from ...core.canon import content_hash, dump_json, hash_hex
from ...core.instance import data_root, write_instances
from ...core.seeds import rng_for
from ...core.splits import build_manifest, write_manifest
from . import generate as G

SPLIT_RULES = ("D v1: dicke k=2 (n=4-24 -> train, val n in {6,11,16,21}; n=25-40 -> test_in; k>=3, C(n,k)<=4096 -> "
               "test_ood); w (n=4-32 -> train, val n in {7,13,19,25,31}; n in {33,...,128} -> test_in); dense Haar-random "
               "(n=3-8: 16 train / 5 val seeds per n; n=9,10 -> test_in); sparse random support (S 8-14, M 15-22, L 23-30 "
               "qubits, 2-64 nonzeros: 36 train / 12 val / 4 test_in per bin; XL 31-40 qubits, up to 128 nonzeros -> "
               "test_in); test_ood = structured supports (simplex, first-order Reed-Muller, Hamming codewords, fixed "
               "weight) + Dicke k>=3; probe = dense n=2,3. Seed ranges disjoint per split.")


def invariants(inst) -> tuple:
    """Invariant under qubit permutation, single-qubit X flips and per-basis-state phases fixed by local Z rotations is
    hard to state exactly; we use (n, nonzero count, sorted multiset of |amplitude|^2 rounded, weight histogram)."""
    pub = inst.public
    a = sorted(round(re * re + im * im, 9) for _, re, im in pub["amplitudes"])
    return (pub["n"], len(a), tuple(a[:64]), tuple(a[-64:]))


def find_cross_split_duplicates(planned) -> list[dict]:
    groups = defaultdict(list)
    for p in planned:
        groups[invariants(p.inst)].append(p)
    out = []
    for inv, ps in groups.items():
        for x, y in itertools.combinations(ps, 2):
            if x.split != y.split:
                out.append({"a": x.inst.id, "b": y.inst.id, "splits": [x.split, y.split],
                            "verdict": "identical" if x.inst.hash == y.inst.hash else "equal invariants (treated as duplicate)"})
    return out


def local_variant(pub: dict, kind: str, rng) -> tuple[dict, dict]:
    """Equivalent targets under free single-qubit gates: qubit relabelling, X flips, and Z-phase rotations."""
    n = pub["n"]
    perm = rng.permutation(n).tolist() if "perm" in kind else list(range(n))
    flips = int(sum(1 << q for q in range(n) if rng.random() < 0.5)) if "flip" in kind else 0
    phases = rng.uniform(0, 2 * math.pi, n).tolist() if "phase" in kind else [0.0] * n
    amp = {}
    for k, re, im in pub["amplitudes"]:
        x = int(k)
        y = 0
        for q in range(n):
            if (x >> q) & 1:
                y |= 1 << perm[q]
        y ^= flips
        ph = sum(phases[q] for q in range(n) if (y >> q) & 1)
        amp[y] = complex(re, im) * complex(math.cos(ph), math.sin(ph))
    pub2 = json.loads(json.dumps(pub))
    pub2["amplitudes"] = G.amplitudes_to_public(amp)
    return pub2, {"qubit_perm": perm, "x_flips": str(flips), "z_phases": phases}


def write_variants(planned) -> int:
    root = data_root() / "variants" / "D"
    if root.exists():
        import shutil
        shutil.rmtree(root)
    count = 0
    for p in planned:
        if p.split not in ("test_in", "test_ood"):
            continue
        rng = rng_for("D-variants", p.inst.hash)
        for i, kind in enumerate(("perm", "perm+flip", "perm+flip+phase"), start=1):
            pub2, tr = local_variant(p.inst.public, kind, rng)
            canon = {"n": pub2["n"], "amplitudes": G.canon_amplitudes(pub2["amplitudes"]), "tracks": G.canon_tracks(pub2["tracks"])}
            v = {"variant_of": p.inst.hash, "variant_id": f"{p.inst.hash}#v{i}", "kind": kind, "split": p.split,
                 "transform": tr, "public": pub2, "hash": content_hash("D", "state_prep", canon),
                 "note": "equivalent under free single-qubit gates (relabelling, X, Z rotations): same optimal cx_count"}
            dump_json(v, root / hash_hex(p.inst.hash) / f"v{i}.json")
            count += 1
    return count


def build(log=print) -> dict:
    t = time.time()
    planned = G.generate_all(log=log)
    dups = find_cross_split_duplicates(planned)
    order = {"train": 0, "val": 1, "test_in": 2, "test_ood": 3, "probe": 4}
    split_of = {p.inst.id: p.split for p in planned}
    drop = {max((d["a"], d["b"]), key=lambda i: order[split_of[i]]) for d in dups}
    refills = []
    if drop:
        dropped = [p for p in planned if p.inst.id in drop]
        planned = [p for p in planned if p.inst.id not in drop]
        for old in dropped:
            new = None
            if old.regen is not None:
                for attempt in range(1, 10):
                    cand = G.regenerate(old, attempt)
                    if not any(invariants(p.inst) == invariants(cand.inst) and p.split != cand.split for p in planned):
                        new = cand
                        break
            if new:
                planned.append(new)
            refills.append({"dropped": old.inst.id, "replacement": new.inst.id if new else None})
        log(f"[build D] dropped {len(drop)} cross-split duplicates, refilled {sum(1 for r in refills if r['replacement'])}")
    write_instances("D", [p.inst for p in planned])
    nvar = write_variants(planned)
    man = build_manifest("D", [(p.split, p.inst.id, p.inst.hash, p.inst.family, p.inst.private.get("size_bin")) for p in planned],
                         SPLIT_RULES)
    write_manifest("D", man)
    rep = {"n_instances": len(planned), "cross_split_pairs": dups, "dropped": sorted(drop), "refills": refills,
           "variants": nvar, "totals": man["totals"], "seconds": round(time.time() - t)}
    dump_json(rep, data_root() / "instances" / "D" / "build_report.json")
    return rep
