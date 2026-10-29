"""Build category A end to end: generate -> verify -> dedup -> write instances -> variants -> split manifest.

    qbank generate A      (CLI wrapper)
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict

import numpy as np

from ...core import gf2
from ...core.canon import content_hash, dump_json, hash_hex
from ...core.instance import data_root, write_instances
from ...core.pauli import PauliRows, mul_into, rref as pauli_rref
from ...core.seeds import rng_for
from ...core.splits import build_manifest, write_manifest
from . import generate as G
from .instances import GATE_SET_PUBLIC

SPLIT_RULES = ("A v1: T families -> train/val/test_in (random families: >=12 seeds per (family,size bin) in train, "
               "4 in val; test_in = XL bin + 2 new seeds per train bin; parametric families by parameter); "
               "O families + sporadic + composites (no T component) -> test_ood; probe = small instances with known "
               "optimum/bound. Seed ranges disjoint per split (core/seeds.py).")


# ------------------------------------------------------------------ duplicate detection
def _low_weight_counts(k_basis: np.ndarray, max_w: int = 3) -> tuple[int, ...]:
    """Number of weight-1..max_w vectors in ker(k_basis) (i.e. in the row space whose dual basis is k_basis)."""
    n = k_basis.shape[1]
    cols = [int.from_bytes(np.packbits(k_basis[:, j]).tobytes(), "big") for j in range(n)]
    by = defaultdict(list)
    for j, v in enumerate(cols):
        by[v].append(j)
    c1 = len(by.get(0, []))
    c2 = sum(len(v) * (len(v) - 1) // 2 for v in by.values())
    c3 = 0
    if max_w >= 3:
        for a in range(n):
            for b in range(a + 1, n):
                c3 += sum(1 for c in by.get(cols[a] ^ cols[b], []) if c > b)
    return (c1, c2, c3)


def invariants(inst) -> tuple:
    pub = inst.public
    n = pub["n"]
    if pub["task"] == "css_logical_zero":
        hx = gf2.from_sparse_rows(pub["hx"], n)
        hz = gf2.from_sparse_rows(pub["hz"], n)
        rx, rz = gf2.rank(hx), gf2.rank(hz)
        dist = (inst.private.get("code", {}).get("verification", {}) or {}).get("distance", {}) or {}
        # rowspace(Hx) = ker(nullspace(Hx)); count its low-weight vectors (basis- and permutation-invariant)
        wx = _low_weight_counts(gf2.nullspace(hx)) if n <= 450 else None
        wz = _low_weight_counts(gf2.nullspace(hz)) if n <= 450 else None
        return ("css", n, rx, rz, dist.get("dX"), dist.get("dZ"), wx, wz)
    st = PauliRows.from_strings(pub["stabilizers"], n)
    weights = tuple(sorted(int(w) for w in (st.x | st.z).sum(axis=1)))
    return ("stab", n, weights if n <= 4 else None, len(pub.get("code_stabilizers", [])))


def _iso_worker(args, q):
    a_pub, b_pub = args
    import networkx as nx
    def graph(pub):
        g = nx.Graph()
        for qb in range(pub["n"]):
            g.add_node(("q", qb), t="q")
        for kind in ("hx", "hz"):
            for i, row in enumerate(pub.get(kind, [])):
                g.add_node((kind, i), t=kind)
                for qb in row:
                    g.add_edge((kind, i), ("q", qb))
        return g
    q.put(bool(nx.vf2pp_is_isomorphic(graph(a_pub), graph(b_pub), node_label="t")))


def tanner_isomorphic(a, b, timeout: float = 20.0) -> bool | None:
    """Tanner-graph isomorphism (VF2++) in a subprocess with a time limit; None = undecided."""
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    q = ctx.Queue()
    p = ctx.Process(target=_iso_worker, args=((a.public, b.public), q))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.kill(); p.join()
        return None
    return q.get() if not q.empty() else None


def _same_rowspaces(a, b) -> bool:
    n = a.public["n"]
    return all(gf2.rowspace_equal(gf2.from_sparse_rows(a.public[k], n), gf2.from_sparse_rows(b.public[k], n)) for k in ("hx", "hz"))


def _pair_verdict(x, y, inv) -> dict:
    rec = {"a": x.inst.id, "b": y.inst.id, "splits": [x.split, y.split]}
    if x.inst.hash == y.inst.hash:
        rec["verdict"], rec["duplicate"] = "identical_hash", True
    elif inv[0] == "css" and _same_rowspaces(x.inst, y.inst):
        rec["verdict"], rec["duplicate"] = "identical code (row spaces equal)", True
    elif inv[0] == "css" and inv[1] <= 60:
        iso = tanner_isomorphic(x.inst, y.inst)
        rec["verdict"] = {True: "equivalent (Tanner graphs isomorphic)", False: "not equivalent (Tanner graphs not isomorphic)",
                          None: "undecided within 20 s (treated as duplicate)"}[iso]
        rec["duplicate"] = iso is not False
    elif inv[0] == "css":
        rec["verdict"], rec["duplicate"] = "invariants equal, n > 60 (treated as duplicate)", True
    else:
        rec["verdict"], rec["duplicate"] = "stabilizer states with equal invariants but different hashes (distinct states)", False
    return rec


def find_suspected_duplicates(planned) -> list[dict]:
    """Pairs in DIFFERENT splits whose invariants agree, with an exact verdict where one can be reached."""
    groups = defaultdict(list)
    for p in planned:
        groups[invariants(p.inst)].append(p)
    out = []
    for inv, ps in groups.items():
        if len(ps) < 2:
            continue
        for x, y in itertools.combinations(ps, 2):
            if x.split == y.split:
                continue
            out.append(_pair_verdict(x, y, inv))
    return out


# ------------------------------------------------------------------ variants (same split as the original)
def _perm_rows(rows, perm):
    return sorted(sorted(int(perm[q]) for q in r) for r in rows)


def css_variant(inst, kind: str, rng: np.random.Generator) -> dict:
    pub = json.loads(json.dumps(inst.public))
    n = pub["n"]
    transform = {}
    hx = gf2.from_sparse_rows(pub["hx"], n)
    hz = gf2.from_sparse_rows(pub["hz"], n)
    if kind in ("basis", "relabel+basis"):
        hx = ((gf2.random_invertible(hx.shape[0], rng).astype(np.int64) @ hx) % 2).astype(np.uint8)
        hz = ((gf2.random_invertible(hz.shape[0], rng).astype(np.int64) @ hz) % 2).astype(np.uint8)
        transform["basis_change"] = True
    if kind in ("relabel", "relabel+basis"):
        perm = rng.permutation(n)
        hx2 = np.zeros_like(hx); hz2 = np.zeros_like(hz)
        hx2[:, perm] = hx; hz2[:, perm] = hz
        hx, hz = hx2, hz2
        transform["perm"] = perm.tolist()        # original qubit q -> variant qubit perm[q]
    pub["hx"] = gf2.sparse_rows(hx)
    pub["hz"] = gf2.sparse_rows(hz)
    canon = {"n": n, "hx_rref": gf2.sparse_rows(gf2.rref(hx)[0]), "hz_rref": gf2.sparse_rows(gf2.rref(hz)[0]),
             "gate_set": GATE_SET_PUBLIC, "tracks": pub["tracks"]}
    return {"variant_of": inst.hash, "kind": kind, "transform": transform, "public": pub,
            "hash": content_hash("A", pub["task"], canon)}


def _pauli_basis_change(rows: PauliRows, m: np.ndarray) -> PauliRows:
    out_x, out_z, out_r = [], [], []
    for i in range(m.shape[0]):
        acc = PauliRows(np.zeros((1, rows.n), np.uint8), np.zeros((1, rows.n), np.uint8), np.zeros(1, np.uint8))
        for j in np.flatnonzero(m[i]):
            mul_into(acc, np.array([0]), rows.x[j], rows.z[j], rows.r[j])
        out_x.append(acc.x[0]); out_z.append(acc.z[0]); out_r.append(acc.r[0])
    return PauliRows(np.array(out_x), np.array(out_z), np.array(out_r, np.uint8))


def stab_variant(inst, kind: str, rng: np.random.Generator) -> dict:
    pub = json.loads(json.dumps(inst.public))
    n = pub["n"]
    transform = {}
    keys = ["stabilizers"] + (["code_stabilizers"] if "code_stabilizers" in pub else [])
    rows = {k: PauliRows.from_strings(pub[k], n) for k in keys}
    if kind in ("basis", "relabel+basis"):
        rows = {k: _pauli_basis_change(v, gf2.random_invertible(v.m, rng)) for k, v in rows.items()}
        transform["basis_change"] = True
    if kind in ("relabel", "relabel+basis"):
        perm = rng.permutation(n)
        rows = {k: v.relabel(perm) for k, v in rows.items()}
        transform["perm"] = perm.tolist()
    for k, v in rows.items():
        pub[k] = v.to_strings()
    canon = {"n": n, "stab_rref": pauli_rref(rows["stabilizers"])[0].to_strings(), "gate_set": GATE_SET_PUBLIC,
             "tracks": pub["tracks"]}
    if "code_stabilizers" in rows:
        canon["code_stab_rref"] = pauli_rref(rows["code_stabilizers"])[0].to_strings()
    return {"variant_of": inst.hash, "kind": kind, "transform": transform, "public": pub,
            "hash": content_hash("A", pub["task"], canon)}


def write_variants(planned) -> int:
    root = data_root() / "variants" / "A"
    if root.exists():
        import shutil
        shutil.rmtree(root)
    count = 0
    for p in planned:
        if p.split not in ("test_in", "test_ood"):
            continue
        rng = rng_for("A-variants", p.inst.hash)
        for i, kind in enumerate(("relabel", "basis", "relabel+basis"), start=1):
            v = css_variant(p.inst, kind, rng) if p.inst.task == "css_logical_zero" else stab_variant(p.inst, kind, rng)
            v["variant_id"] = f"{p.inst.hash}#v{i}"
            v["split"] = p.split
            dump_json(v, root / hash_hex(p.inst.hash) / f"v{i}.json")
            count += 1
    return count


def load_exclusions(path=None) -> list[dict]:
    p = path or (data_root() / "exclusions" / "exclude.json")
    if not p.exists():
        return []
    return [e for e in json.loads(p.read_text())["entries"] if e.get("category", "A") == "A"]


def matches_exclusion(inst, entry) -> bool:
    """Exact hash, identical code (row spaces), or permutation-equivalent (equal invariants + Tanner isomorphism, n <= 60)."""
    from .instances import css_instance, stab_instance
    from . import codes as C
    if entry["type"] == "hash":
        return inst.hash == entry["hash"]
    if entry["type"] == "css_code":
        if inst.task != "css_logical_zero" or inst.public["n"] != entry["n"]:
            return False
        n = entry["n"]
        code = C.CodeSpec("excluded", "excluded", {}, n, True, gf2.from_sparse_rows(entry["hx"], n), gf2.from_sparse_rows(entry["hz"], n))
        ex = css_instance("excluded", code, "excluded", {}, {}, {}, graphs=True)
        if ex.hash == inst.hash or _same_rowspaces(ex, inst):
            return True
        if invariants(ex) == invariants(inst) and n <= 60:
            return bool(tanner_isomorphic(ex, inst))
        return invariants(ex) == invariants(inst)   # conservative: equal invariants on a large code count as a match
    if entry["type"] == "stabilizer_state":
        if inst.task != "stabilizer_state" or inst.public["n"] != entry["n"]:
            return False
        ex = stab_instance("excluded", PauliRows.from_strings(entry["stabilizers"], entry["n"]), "excluded", {}, {}, {},
                           graphs="line_2q" in inst.public["tracks"])
        return ex.hash == inst.hash
    raise ValueError(f"unknown exclusion type {entry['type']}")


def apply_exclusions(planned, entries, log=print):
    kept, dropped = [], []
    for p in planned:
        if p.split in ("test_in", "test_ood") and any(matches_exclusion(p.inst, e) for e in entries):
            dropped.append(p.inst.id)
            continue
        kept.append(p)
    if dropped:
        log(f"[build A] exclusion list removed {len(dropped)} test instances: {dropped}")
    return kept, dropped


def build(include_756: bool = True, log=print) -> dict:
    import time
    t = time.time()
    planned = G.generate_all(include_756=include_756)
    log(f"[build A] generated + verified {len(planned)} instances in {time.time() - t:.0f}s")
    t = time.time()
    dups = find_suspected_duplicates(planned)
    log(f"[build A] duplicate scan in {time.time() - t:.0f}s: {len(dups)} cross-split pairs with equal invariants, "
        f"{sum(d['duplicate'] for d in dups)} treated as duplicates")
    order = {"train": 0, "val": 1, "test_in": 2, "test_ood": 3, "probe": 4}
    split_of = {p.inst.id: p.split for p in planned}
    drop = set()
    for d in dups:
        if d["duplicate"]:
            drop.add(max((d["a"], d["b"]), key=lambda i: order[split_of[i]]))
    refills = []
    if drop:
        log(f"[build A] dropping {len(drop)} instances that duplicate an instance of an earlier split: {sorted(drop)}")
        dropped_p = [p for p in planned if p.inst.id in drop]
        planned = [p for p in planned if p.inst.id not in drop]
        inv_of = {p.inst.id: invariants(p.inst) for p in planned}
        for old in dropped_p:
            if old.regen is None:
                continue
            for attempt in range(1, 10):
                new = G.regenerate(old, attempt)
                inv = invariants(new.inst)
                clash = [p for p in planned if inv_of[p.inst.id] == inv and p.split != new.split and _pair_verdict(p, new, inv)["duplicate"]]
                clash += [p for p in planned if p.inst.hash == new.inst.hash]
                if not clash:
                    planned.append(new)
                    inv_of[new.inst.id] = inv
                    refills.append({"dropped": old.inst.id, "replacement": new.inst.id, "attempts": attempt})
                    break
            else:
                refills.append({"dropped": old.inst.id, "replacement": None, "attempts": 9})
        log(f"[build A] refilled {sum(1 for r in refills if r['replacement'])}/{len(dropped_p)} dropped slots with fresh seeds")
    planned, excluded = apply_exclusions(planned, load_exclusions(), log)
    cross = [d for d in dups if d["splits"][0] != d["splits"][1]]
    remaining = [d for d in find_suspected_duplicates(planned) if d["duplicate"]]
    report = {"n_instances": len(planned), "suspected_duplicates": dups, "dropped_as_duplicates": sorted(drop), "refills": refills,
              "cross_split_duplicates": remaining, "excluded": excluded}
    if remaining:
        raise RuntimeError(f"cross-split duplicates remain: {remaining}")
    from . import extend_v12          # data version 1.2.0 (10-28): named codes for the task packs, train / val only
    ext, ext_report = extend_v12.extension([p.inst for p in planned], log)
    planned += ext
    write_instances("A", [p.inst for p in planned])
    dump_json(ext_report, data_root() / "instances" / "A" / f"extension_v{extend_v12.VERSION}.json")
    report["variants"] = write_variants(planned)
    man = build_manifest("A", [(p.split, p.inst.id, p.inst.hash, p.inst.family, p.inst.private.get("size_bin")) for p in planned],
                         SPLIT_RULES + " | " + extend_v12.RULES_NOTE)
    write_manifest("A", man)
    report["totals"] = man["totals"]
    dump_json(report, data_root() / "instances" / "A" / "build_report.json")
    return report
