"""Build category C: generate -> dedup across splits -> write instances -> variants -> split manifest."""
from __future__ import annotations

import itertools
import json
import time
from collections import Counter, defaultdict

import networkx as nx

from ...core.canon import dump_json, hash_hex
from ...core.circuit import Circuit
from ...core.instance import data_root, write_instances
from ...core.seeds import rng_for
from ...core.splits import build_manifest, write_manifest
from . import generate as G

SPLIT_RULES = ("C v1: 3 generator families (qaoa, trotter, struct_random) x 5 device kinds (line, ring, grid, heavy_hex, "
               "random_sparse); per (family, device kind): train 12 / val 4 / test_in 2 seeds per size bin S 8-16, M 17-32, "
               "L 33-64 logical qubits, plus 12 XL (65-156) in test_in; seed ranges disjoint per split. test_ood = external "
               "sources never used in train: QUEKO (300), QUBIKOS (160), MQT Bench families not used in "
               "train, HamLib lattice Hamiltonians; unseen devices (Aspen-4, Tokyo, Rochester, Sycamore). "
               "probe = 60 small QUEKO instances with a verified zero-SWAP witness.")


def invariants(inst) -> tuple:
    """Invariant under logical relabelling and device relabelling: sizes, gate-name multiset, degree sequences, device
    and interaction-graph WL hashes."""
    pub = inst.public
    c = Circuit.from_json(pub["circuit"])
    names = tuple(sorted(Counter(g for g, _, _ in c.gates).items()))
    I = nx.Graph()
    I.add_nodes_from(range(c.n))
    for g, qs, _ in c.gates:
        if len(qs) == 2:
            I.add_edge(*qs)
    D = nx.Graph()
    D.add_nodes_from(range(pub["n_physical"]))
    D.add_edges_from(map(tuple, pub["coupling_edges"]))
    return (c.n, pub["n_physical"], len(c.gates), names, nx.weisfeiler_lehman_graph_hash(I, iterations=3),
            nx.weisfeiler_lehman_graph_hash(D, iterations=3), pub["blocks"] is not None)


def find_cross_split_duplicates(planned) -> list[dict]:
    groups = defaultdict(list)
    for p in planned:
        groups[invariants(p.inst)].append(p)
    out = []
    for inv, ps in groups.items():
        for x, y in itertools.combinations(ps, 2):
            if x.split == y.split:
                continue
            out.append({"a": x.inst.id, "b": y.inst.id, "splits": [x.split, y.split],
                        "verdict": "identical" if x.inst.hash == y.inst.hash else "equal relabelling invariants (treated as duplicate)",
                        "duplicate": True})
    return out


def relabel(pub: dict, lperm: list[int], pperm: list[int]) -> dict:
    """Logical qubit l -> lperm[l]; physical qubit p -> pperm[p]. Blocks keep their gate order."""
    c = Circuit.from_json(pub["circuit"])
    c2 = Circuit(c.n)
    for g, qs, ps in c.gates:
        c2.append(g, [lperm[q] for q in qs], ps)
    pub2 = json.loads(json.dumps(pub))
    pub2["circuit"] = c2.to_json()
    pub2["circuit_qasm3"] = G._qasm3(c2)
    pub2["coupling_edges"] = sorted(sorted([pperm[a], pperm[b]]) for a, b in pub["coupling_edges"])
    return pub2


def write_variants(planned) -> int:
    from ...core.canon import content_hash
    root = data_root() / "variants" / "C"
    if root.exists():
        import shutil
        shutil.rmtree(root)
    count = 0
    for p in planned:
        if p.split not in ("test_in", "test_ood"):
            continue
        pub = p.inst.public
        n, N = pub["n_logical"], pub["n_physical"]
        rng = rng_for("C-variants", p.inst.hash)
        specs = [("logical_relabel", rng.permutation(n).tolist(), list(range(N))),
                 ("device_relabel", list(range(n)), rng.permutation(N).tolist()),
                 ("logical+device_relabel", rng.permutation(n).tolist(), rng.permutation(N).tolist())]
        for i, (kind, lp, pp) in enumerate(specs, start=1):
            pub2 = relabel(pub, lp, pp)
            canon = {"circuit": pub2["circuit"], "edges": pub2["coupling_edges"], "n_physical": N, "blocks": pub2["blocks"],
                     "tracks": pub2["tracks"]}
            v = {"variant_of": p.inst.hash, "variant_id": f"{p.inst.hash}#v{i}", "kind": kind, "split": p.split,
                 "transform": {"logical_perm": lp, "physical_perm": pp}, "public": pub2,
                 "hash": content_hash("C", "routing", canon)}
            dump_json(v, root / hash_hex(p.inst.hash) / f"v{i}.json")
            count += 1
    return count


def regenerate(p, attempt: int):
    name, args, i = p.regen
    return G.gen(*args, i + 100 * attempt)


def build(include_external: bool = True, log=print) -> dict:
    t = time.time()
    planned = G.generate_all(log=log)
    if include_external:
        from . import external
        planned += external.generate_external(log=log)
    log(f"[build C] {len(planned)} instances in {time.time() - t:.0f}s")
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
                new = regenerate(old, attempt)
                inv = invariants(new.inst)
                if not any(inv_of[p.inst.id] == inv and p.split != new.split for p in planned) and \
                        not any(p.inst.hash == new.inst.hash for p in planned):
                    planned.append(new)
                    inv_of[new.inst.id] = inv
                    refills.append({"dropped": old.inst.id, "replacement": new.inst.id, "attempts": attempt})
                    break
            else:
                refills.append({"dropped": old.inst.id, "replacement": None})
        log(f"[build C] dropped {len(drop)} cross-split duplicates, refilled {sum(1 for r in refills if r['replacement'])}")
    write_instances("C", [p.inst for p in planned])
    nvar = write_variants(planned)
    man = build_manifest("C", [(p.split, p.inst.id, p.inst.hash, p.inst.family, p.inst.private.get("size_bin")) for p in planned],
                         SPLIT_RULES)
    write_manifest("C", man)
    rep = {"n_instances": len(planned), "cross_split_pairs": dups, "dropped": sorted(drop), "refills": refills,
           "variants": nvar, "totals": man["totals"], "seconds": round(time.time() - t)}
    dump_json(rep, data_root() / "instances" / "C" / "build_report.json")
    return rep
