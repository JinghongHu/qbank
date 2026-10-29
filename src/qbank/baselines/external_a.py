"""External category-A baseline circuits: released by papers/tools, re-verified and re-costed by qbank.

Sources (fetched by data/v1/external/fetch_A.sh at pinned commits into .cache/external/):
  * mqt-qecc  scripts/encoding_circuits/best_circuits/<n_k_d>/{zero,plus,encoder}_*.stim   (arXiv:2605.15266)
              scripts/ft_stateprep/eval/circuits/<code>/*non_ft*.stim                     (arXiv:2408.11894)
  * qecirc    data_yaml/circuits/*.yaml + .stim, code matrices in data_yaml/matrices/<original_matrices>.yaml
Each circuit is mapped onto a qbank instance (identity if the code matrices agree; the proven block-swap+transpose
permutation for MQT's BB108/144; Tanner-graph isomorphism otherwise), relabelled, verified with both checkers and
re-costed (swap = 3). Encoders count toward |0_L> only after fixing logical inputs to |0> (noted in the record).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

from ..core import gf2
from ..core.canon import file_sha256
from ..core.circuit import Circuit
from ..core.costs import costs
from ..core.instance import PKG_ROOT, load_index, load_public
from ..categories.A.instances import verify
from . import runner

EXT = PKG_ROOT / ".cache" / "external"
EXT_NS = "A-external"          # separate cache namespace (the baseline runner owns data/v1/cache/A/)
IMPORT_VERSION = "import-v2"   # v1 mapped QECirc circuits with the wrong matrix labelling (superseded)


def _commit(name: str) -> str:
    return (EXT / f"{name}.COMMIT").read_text().strip()


# ------------------------------------------------------------------ code <-> instance mapping
def _css_of_public(pub):
    n = pub["n"]
    return gf2.from_sparse_rows(pub["hx"], n), gf2.from_sparse_rows(pub["hz"], n)


def _tanner_mapping(hx_a, hz_a, hx_b, hz_b, max_n=130):
    """Permutation p with code_a[:, j] ~ code_b[:, p[j]] via isomorphism of Tanner graphs of the given generators."""
    import networkx as nx
    from networkx.algorithms import isomorphism as iso
    n = hx_a.shape[1]
    if n > max_n:
        return None

    def g(hx, hz):
        G = nx.Graph()
        for q in range(n):
            G.add_node(("q", q), t="q")
        for kind, H in (("x", hx), ("z", hz)):
            for i, row in enumerate(H):
                G.add_node((kind, i), t=kind, w=int(row.sum()))
                for q in np.flatnonzero(row):
                    G.add_edge((kind, i), ("q", int(q)))
        return G
    gm = iso.GraphMatcher(g(hx_a, hz_a), g(hx_b, hz_b), node_match=lambda a, b: a["t"] == b["t"] and a.get("w") == b.get("w"))
    if not gm.is_isomorphic():
        return None
    p = [None] * n
    for u, v in gm.mapping.items():
        if u[0] == "q":
            p[u[1]] = v[1]
    return p


def candidate_mappings(hx_e, hz_e, pub) -> list[tuple[str, list[int]]]:
    """Ways to map external qubit j -> instance qubit p[j]; each is kept only if it provably maps the external code
    onto the instance's code (row spaces of Hx and Hz equal after relabelling)."""
    n = pub["n"]
    if hx_e.shape[1] != n:
        return []
    hx_i, hz_i = _css_of_public(pub)
    cands = [("identity", list(range(n)))]
    if n in (108, 144):
        L = n // 2
        l, m = {108: (9, 6), 144: (12, 6)}[n]
        tr = [(i % m) * l + (i // m) for i in range(L)]
        perm = [tr[j] + L for j in range(L)] + [tr[j] for j in range(L)]   # Bravyi[:, j] == MQT[:, perm[j]]
        inv = [0] * n
        for j, pj in enumerate(perm):
            inv[pj] = j
        cands.append(("bb-blockswap-transpose", inv))
    # cheap necessary conditions for equivalence first
    if (gf2.rank(hx_e), gf2.rank(hz_e)) != (gf2.rank(hx_i), gf2.rank(hz_i)):
        return []
    out = []
    for name, p in cands:
        if _maps_code(hx_e, hz_e, hx_i, hz_i, p):
            out.append((name, p))
    if not out and n <= 60:
        p = _tanner_mapping_limited(hx_e, hz_e, hx_i, hz_i)
        if p is not None and _maps_code(hx_e, hz_e, hx_i, hz_i, p):
            out.append(("tanner-isomorphism", p))
    return out


def _tanner_worker(args, q):
    q.put(_tanner_mapping(*args))


def _tanner_mapping_limited(hx_e, hz_e, hx_i, hz_i, timeout: float = 20.0):
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    q = ctx.Queue()
    pr = ctx.Process(target=_tanner_worker, args=((hx_e, hz_e, hx_i, hz_i), q))
    pr.start()
    pr.join(timeout)
    if pr.is_alive():
        pr.kill(); pr.join()
        return None
    return q.get() if not q.empty() else None


def _maps_code(hx_e, hz_e, hx_i, hz_i, p) -> bool:
    n = hx_e.shape[1]
    px = np.zeros_like(hx_e); pz = np.zeros_like(hz_e)
    px[:, p] = hx_e
    pz[:, p] = hz_e
    return gf2.rowspace_equal(px, hx_i) and gf2.rowspace_equal(pz, hz_i)


# ------------------------------------------------------------------ source catalogues
MQT_BEST_DIRS = {  # dir -> (how to rebuild MQT's code for this directory)
    "15_1_3": ("named", "tetrahedral"), "15_7_3": ("hamming", 4), "17_1_5": ("488", 5), "19_1_5": ("666", 5),
    "23_1_7": ("named", "golay"), "30_6_5": ("misc", "30_6_5.txt"), "31_1_7": ("488", 7), "31_21_3": ("hamming", 5),
    "37_1_7": ("666", 7), "72_12_6": ("bb", 72), "90_8_10": ("bb", 90), "108_8_10": ("bb", 108), "144_12_12": ("bb", 144),
}
MQT_FT_DIRS = {"steane": ("named", "steane"), "shor": ("named", "shor"), "rotated_surface_d3": ("rot", 3),
               "rotated_surface_d5": ("rot", 5), "hamming": ("hamming", 4), "tetrahedral": ("named", "tetrahedral"),
               "carbon": ("named", "carbon"), "cc_4_8_8": ("488", 5), "cc_4_8_8_d7": ("488", 7), "cc_6_6_6": ("666", 5)}


def _mqt_code(spec):
    from mqt.qecc import CSSCode
    from mqt.qecc.codes import (HexagonalColorCode, RotatedSurfaceCode, SquareOctagonColorCode, construct_bb_code,
                                construct_quantum_hamming_code)
    from ..categories.A import codes as C
    kind, arg = spec
    if kind == "named":
        c = CSSCode.from_code_name(arg)
    elif kind == "hamming":
        c = construct_quantum_hamming_code(arg)
    elif kind == "488":
        c = SquareOctagonColorCode(distance=arg)
    elif kind == "666":
        c = HexagonalColorCode(distance=arg)
    elif kind == "bb":
        c = construct_bb_code(arg)
    elif kind == "rot":
        c = RotatedSurfaceCode(distance=arg)
    elif kind == "misc":
        cs = C.mqt_misc(arg)
        return cs.hx, cs.hz
    return gf2.as_gf2(c.Hx), gf2.as_gf2(c.Hz)


def _instances_by_n():
    by = {}
    for row in load_index("A"):
        pub = load_public("A", row["hash"])
        if pub["task"] != "css_logical_zero":
            continue
        by.setdefault(pub["n"], []).append((row, pub))
    return by


def _try_record(circ: Circuit, hx_e, hz_e, candidates, tool: str, version: str, config: dict, kind: str, log):
    """Map a |0_L> or |+_L> (kind) circuit onto matching instances; store one record per (instance, track)."""
    stored = 0
    for row, pub in candidates:
        maps = candidate_mappings(hx_e, hz_e, pub)
        tracks = ["a2a_2q", "codespace_a2a_2q"] if kind == "zero" else ["codespace_a2a_2q"]
        for track in tracks:
            verdict, used = None, None
            for mname, p in maps:
                v = verify(pub, track, circ.relabel(p))
                if v.status == "pass":
                    verdict, used = v, mname
                    break
            if not maps:
                continue  # different code (no mapping found): not this instance
            job = {"category": "A", "iid": row["id"], "hash": row["hash"], "track": track, "tool": tool,
                   "version": version, "config": {**config, "kind": kind}, "budget": None, "seed": None}
            job["cache_key"] = runner.cache_key(row["hash"], tool, version, job["config"], track)
            if job["cache_key"] in runner.load_cache_keys(EXT_NS, row["hash"]):
                continue
            if verdict is None:
                r = {"status": "fail", "reason": f"code matched ({[m for m, _ in maps]}) but circuit failed verification"}
            else:
                r = {"status": "pass", "costs": costs(verdict.circuit), "circuit": verdict.circuit.to_json(), "output_map": None,
                     "pauli_correction": verdict.pauli_correction, "meta": {"mapping": used}}
            runner._store({**job, "ns": EXT_NS}, r, 0.0, "external (not timed)")
            stored += 1
            log(f"  {tool} -> {row['id']} [{track}] {r['status']} {r.get('costs', {}).get('two_qubit_gates', '')}")
    return stored


def _orient(circ, hx, hz, kind):
    """The circuit's X/Z convention: (hx, hz) as given, or with the roles swapped (the circuit decides)."""
    if _prepares(circ, hx, hz, kind):
        return hx, hz, "as_given"
    if _prepares(circ, hz, hx, kind):
        return hz, hx, "xz_swapped"
    return hx, hz, None


def import_mqt(log=print) -> int:
    root = EXT / "mqt-qecc" / "scripts"
    ver = f"mqt-qecc@{_commit('mqt-qecc')};{IMPORT_VERSION}"
    by_n = _instances_by_n()
    total = 0
    for d, spec in MQT_BEST_DIRS.items():
        hx_e, hz_e = _mqt_code(spec)
        for f in sorted((root / "encoding_circuits" / "best_circuits" / d).glob("*.stim")):
            kind = "zero" if f.name.startswith("zero") else "plus" if f.name.startswith("plus") else "encoder"
            import stim
            sc = stim.Circuit(f.read_text())
            try:
                circ = Circuit.from_stim(sc, hx_e.shape[1]) if kind != "encoder" else Circuit.from_stim(sc, hx_e.shape[1])
            except ValueError as e:
                log(f"  skip {f.name}: {e}")
                continue
            note = "encoder with logical inputs fixed to |0> (counts toward |0_L>)" if kind == "encoder" else ""
            hx_e, hz_e, orient = _orient(circ, *_mqt_code(spec), "zero" if kind in ("zero", "encoder") else "plus")
            if orient is None:
                skipped.append({"file": f"best_circuits/{d}/{f.name}", "reason": "prepares the target state of neither X/Z orientation"})
                continue
            total += _try_record(circ, hx_e, hz_e, by_n.get(hx_e.shape[1], []), f"published:mqt-qecc/best_circuits/{d}/{f.name}",
                                 ver, {"source": "arXiv:2605.15266 (released circuits)", "file_sha256": file_sha256(f), "note": note},
                                 "zero" if kind in ("zero", "encoder") else "plus", log)
    for d, spec in MQT_FT_DIRS.items():
        hx_e, hz_e = _mqt_code(spec)
        for f in sorted((root / "ft_stateprep" / "eval" / "circuits" / d).glob("*non_ft*.stim")):
            import stim
            kind = "zero" if "zero" in f.name else "plus"
            try:
                circ = Circuit.from_stim(stim.Circuit(f.read_text()), hx_e.shape[1])
            except Exception as e:
                log(f"  skip {d}/{f.name}: {type(e).__name__}: {e}")
                continue
            hx_e, hz_e, orient = _orient(circ, *_mqt_code(spec), kind)
            if orient is None:
                skipped.append({"file": f"ft_stateprep/{d}/{f.name}", "reason": "prepares the target state of neither X/Z orientation"})
                continue
            total += _try_record(circ, hx_e, hz_e, by_n.get(hx_e.shape[1], []), f"published:mqt-qecc/ft_stateprep/{d}/{f.name}",
                                 ver, {"source": "arXiv:2408.11894 (released circuits)", "file_sha256": file_sha256(f)}, kind, log)
    return total


def _prepares(circ: Circuit, hx: np.ndarray, hz: np.ndarray, kind: str) -> bool:
    from ..contracts.stabilizer import targets_css_zero, verify_stabilizer_contract
    tg = targets_css_zero(hx) if kind == "zero" else targets_css_zero(hz)   # |+_L>: roles of X and Z swapped
    if kind == "plus":
        from ..core.pauli import PauliRows
        tg = PauliRows(tg.z.copy(), tg.x.copy(), tg.r.copy())
    return verify_stabilizer_contract(circ, tg, width=circ.n).status == "pass"


skipped: list = []


def import_qecirc(log=print) -> int:
    root = EXT / "qecirc" / "data_yaml"
    ver = f"qecirc-website@{_commit('qecirc')};{IMPORT_VERSION}"
    by_n = _instances_by_n()
    total = 0
    import stim
    for yf in sorted((root / "circuits").glob("*.yaml")):
        meta = yaml.safe_load(yf.read_text())
        tags = set(meta.get("tags") or [])
        if "state-preparation" not in tags or not ({"logical-state:zero", "logical-state:plus"} & tags):
            continue
        kind = "zero" if "logical-state:zero" in tags else "plus"
        n = meta.get("qubit_count")
        if n not in by_n:
            continue
        try:
            circ = Circuit.from_stim(stim.Circuit(yf.with_suffix(".stim").read_text()), n)
        except Exception:
            continue  # measurements / resets mid-circuit / flags: not a unitary n-qubit preparation
        # QECirc keeps two matrix sets (the circuit's original_matrices and the canonical code file); the stored
        # circuit is expressed in the labelling of only one of them: use the one it provably prepares the state for.
        sets = []
        mid = meta.get("original_matrices")
        if mid and (root / "matrices" / f"{mid}.yaml").exists():
            sets.append(("original_matrices", yaml.safe_load((root / "matrices" / f"{mid}.yaml").read_text())["h"]))
        slug = yf.name.split("--")[0]
        if (root / "codes" / f"{slug}.yaml").exists():
            sets.append((f"codes/{slug}", yaml.safe_load((root / "codes" / f"{slug}.yaml").read_text())["h"]))
        chosen = None
        for name, hmat in sets:
            h = np.array(hmat, dtype=np.uint8)
            if h.ndim != 2 or h.shape[1] != 2 * n:
                continue
            xpart, zpart = h[:, :n], h[:, n:]
            if (xpart.any(axis=1) & zpart.any(axis=1)).any():
                continue  # non-CSS
            hx_e, hz_e = xpart[xpart.any(axis=1)], zpart[zpart.any(axis=1)]
            if _prepares(circ, hx_e, hz_e, kind):
                chosen = (name, hx_e, hz_e)
                break
        if chosen is None:
            skipped.append({"qec_id": meta["qec_id"], "reason": "circuit prepares the target state of neither QECirc matrix set"})
            continue
        name, hx_e, hz_e = chosen
        total += _try_record(circ, hx_e, hz_e, by_n[n], f"qecirc:{meta['qec_id']}", ver,
                             {"source": meta.get("source", ""), "tool": meta.get("tool", ""), "name": meta.get("name", ""),
                              "matrices": name,
                              "file_sha256": file_sha256(yf.with_suffix(".stim")), "licence": "CC BY-SA 4.0"}, kind, log)
    return total
