"""Category C: routing and commuting-gate scheduling.

Public part: the logical circuit (QASM3 text + qbank JSON), the device coupling graph (edge list), and for the commuting
track the block annotation. Tracks:
  swaps           routing_equiv,     metric = inserted SWAP count (primary)
  depth2q         routing_equiv,     metric = two-qubit depth of the routed circuit (secondary; swap = 3 layers)
  swaps_commuting routing_commuting, metric = inserted SWAP count (QAOA / Trotter only; blocks given)
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np

from ...core.canon import content_hash
from ...core.circuit import Circuit
from ...core.instance import Instance
from ...core.seeds import rng_for, split_seed

SIZE_BINS = [("S", 8, 16), ("M", 17, 32), ("L", 33, 64), ("XL", 65, 156)]
GRAPH_KINDS = ("line", "ring", "grid", "heavy_hex", "random_sparse")


def size_bin(n: int) -> str:
    for b, lo, hi in SIZE_BINS:
        if lo <= n <= hi:
            return b
    return "XS" if n < 8 else "XXL"


# ------------------------------------------------------------------ device graphs
def _fake_backend_edges(name: str) -> tuple[int, list]:
    import qiskit_ibm_runtime.fake_provider as fp
    b = getattr(fp, name)()
    es = sorted({tuple(sorted(e)) for e in b.coupling_map.get_edges()})
    return b.num_qubits, [list(e) for e in es]


def heavy_hex_device(n: int) -> tuple[str, int, list]:
    from qiskit.transpiler import CouplingMap
    options = [("heavy_hex_d3", 19, None), ("ibm_falcon_27 (FakeCairoV2)", 27, "FakeCairoV2"), ("heavy_hex_d5", 57, None),
               ("heavy_hex_d7", 115, None), ("ibm_eagle_127 (FakeBrisbane)", 127, "FakeBrisbane"),
               ("ibm_heron_156 (FakeFez)", 156, "FakeFez")]
    for name, size, fake in options:
        if size >= n:
            if fake:
                try:
                    q, es = _fake_backend_edges(fake)
                except Exception:
                    continue
                G = nx.Graph()
                G.add_edges_from(map(tuple, es))
                if max((len(c) for c in nx.connected_components(G)), default=0) < n:
                    continue        # e.g. FakeCairoV2 has an isolated qubit: only 26 connected qubits
                return name, q, es
            d = {"heavy_hex_d3": 3, "heavy_hex_d5": 5, "heavy_hex_d7": 7}[name]
            cm = CouplingMap.from_heavy_hex(d)
            return name, cm.size(), [list(e) for e in sorted({tuple(sorted(e)) for e in cm.get_edges()})]
    raise ValueError(f"no heavy-hex device with >= {n} qubits")


def device(kind: str, n: int, rng) -> tuple[str, int, list]:
    if kind == "line":
        return f"line_{n}", n, [[i, i + 1] for i in range(n - 1)]
    if kind == "ring":
        return f"ring_{n}", n, [[i, i + 1] for i in range(n - 1)] + [[0, n - 1]]
    if kind == "grid":
        r = math.ceil(math.sqrt(n))
        c = math.ceil(n / r)
        es = []
        for i in range(r):
            for j in range(c):
                q = i * c + j
                if j + 1 < c:
                    es.append([q, q + 1])
                if i + 1 < r:
                    es.append([q, q + c])
        return f"grid_{r}x{c}", r * c, es
    if kind == "heavy_hex":
        return heavy_hex_device(n)
    if kind == "random_sparse":
        N = n + int(rng.integers(0, max(1, n // 8) + 1))
        tree = nx.random_labeled_tree(N, seed=int(rng.integers(2 ** 31)))
        es = {tuple(sorted(e)) for e in tree.edges}
        for _ in range(N // 3):
            a, b = rng.choice(N, 2, replace=False)
            es.add(tuple(sorted((int(a), int(b)))))
        return f"random_sparse_{N}", N, [list(e) for e in sorted(es)]
    raise ValueError(kind)


# ------------------------------------------------------------------ circuit families
def qaoa_circuit(n: int, rng) -> tuple[Circuit, list, dict]:
    kind = ["reg3", "reg4", "gnp"][int(rng.integers(3))]
    if kind.startswith("reg") and (n * int(kind[-1])) % 2 == 0 and n > int(kind[-1]):
        G = nx.random_regular_graph(int(kind[-1]), n, seed=int(rng.integers(2 ** 31)))
    else:
        kind = "gnp"
        G = nx.gnp_random_graph(n, min(1.0, 4.0 / n), seed=int(rng.integers(2 ** 31)))
    p = int(rng.integers(1, 4))
    c = Circuit(n)
    blocks = []
    for q in range(n):
        c.append("h", [q])
        blocks.append(0)
    b = 1
    for layer in range(p):
        for u, v in sorted(G.edges):
            c.append("rzz", [u, v], [f"gamma_{layer}"])
            blocks.append(b)
        b += 1
        for q in range(n):
            c.append("rx", [q], [f"beta_{layer}"])
            blocks.append(b)
        b += 1
    return c, blocks, {"graph": kind, "p": p, "edges": sorted(map(list, G.edges))}


def trotter_circuit(n: int, rng) -> tuple[Circuit, list, dict]:
    model = ["ising", "heisenberg"][int(rng.integers(2))]
    G = nx.gnp_random_graph(n, min(1.0, 3.0 / n), seed=int(rng.integers(2 ** 31)))
    c = Circuit(n)
    blocks = []
    b = 0
    terms = ["rzz"] if model == "ising" else ["rxx", "ryy", "rzz"]
    for t in terms:
        for u, v in sorted(G.edges):
            c.append(t, [u, v], [f"J_{t[1:]}"])
            blocks.append(b)
        b += 1
    for q in range(n):
        c.append("rx" if model == "ising" else "rz", [q], ["h"])
        blocks.append(b)
    return c, blocks, {"model": model, "edges": sorted(map(list, G.edges))}


def struct_random_circuit(n: int, rng) -> tuple[Circuit, None, dict]:
    """Random circuit on a controllable interaction graph: degree-limited random graph, gates drawn along its edges."""
    deg = int(rng.integers(2, 5))
    G = nx.random_regular_graph(deg, n, seed=int(rng.integers(2 ** 31))) if (n * deg) % 2 == 0 else \
        nx.gnp_random_graph(n, deg / n, seed=int(rng.integers(2 ** 31)))
    E = sorted(G.edges) or [(0, 1)]
    m = int(rng.integers(2 * n, 6 * n + 1))
    c = Circuit(n)
    for _ in range(m):
        if rng.random() < 0.3:
            c.append(str(rng.choice(["h", "t", "s", "sx"])), [int(rng.integers(n))])
        else:
            u, v = E[int(rng.integers(len(E)))]
            if rng.random() < 0.5:
                u, v = v, u
            c.append("cx", [u, v])
    return c, None, {"interaction_degree": deg, "two_qubit_gates": sum(1 for g in c.gates if len(g[1]) == 2)}


FAMILIES = {"qaoa": qaoa_circuit, "trotter": trotter_circuit, "struct_random": struct_random_circuit}


# ------------------------------------------------------------------ instance
def make_instance(iid, circ: Circuit, blocks, dev_name, n_phys, edges, family, params, source, private) -> Instance:
    tracks = {"swaps": {"contract": "routing_equiv", "metric": "swaps"},
              "depth2q": {"contract": "routing_equiv", "metric": "two_qubit_depth"}}
    if blocks is not None:
        tracks["swaps_commuting"] = {"contract": "routing_commuting", "metric": "swaps"}
    public = {"format": "qbank.public/1", "task": "routing", "n_logical": circ.n, "n_physical": n_phys,
              "circuit": circ.to_json(), "circuit_qasm3": _qasm3(circ), "coupling_edges": edges,
              "blocks": blocks, "tracks": tracks,
              "output": "routed circuit on n_physical qubits (explicit swap gates only) + initial_layout[l] = physical qubit of logical l"}
    canon = {"circuit": circ.to_json(), "edges": sorted(map(sorted, edges)), "n_physical": n_phys, "blocks": blocks, "tracks": tracks}
    h = content_hash("C", "routing", canon)
    priv = {**private, "device": dev_name, "size_bin": private.get("size_bin", size_bin(circ.n))}
    tl = [{"name": k, **v} for k, v in tracks.items()]
    return Instance(iid, "C", "routing", family, source, params, public, priv, sorted({v["contract"] for v in tracks.values()}), tl, h)


def _qasm3(c: Circuit) -> str:
    from qiskit import qasm3
    return qasm3.dumps(c.to_qiskit())


def gen(family: str, kind: str, split: str, bin_: str, i: int, n_range=None):
    from ..A.generate import Planned
    lo, hi = n_range or {b: (a, c) for b, a, c in SIZE_BINS}[bin_]
    seed = split_seed(split, i)
    rng = rng_for("C", family, kind, bin_, seed)
    n = int(rng.integers(lo, hi + 1))
    circ, blocks, meta = FAMILIES[family](n, rng)
    dev_name, n_phys, edges = device(kind, n, rng)
    src = {"kind": "generator", "name": f"{family}_on_{kind}", "version": "1", "ref": "", "license": "qbank"}
    inst = make_instance(f"C.{family}.{kind}.n{n}.s{seed}", circ, blocks, dev_name, n_phys, edges, family,
                         {"n": n, "seed": seed, "device_kind": kind, **{k: v for k, v in meta.items() if k != "edges"}}, src,
                         {"size_bin": bin_, "interaction_edges": meta.get("edges")})
    p = Planned(split, inst)
    p.regen = ("gen", (family, kind, split, bin_), i)
    return p


def generate_all(log=print) -> list:
    P = []
    for family in FAMILIES:
        for kind in GRAPH_KINDS:
            for bi, bin_ in enumerate(("S", "M", "L")):
                for sp, cnt in (("train", 12), ("val", 4), ("test_in", 2)):
                    for j in range(cnt):
                        P.append(gen(family, kind, sp, bin_, 1000 * bi + 100 * GRAPH_KINDS.index(kind) + j))
            for j in range(12):
                P.append(gen(family, kind, "test_in", "XL", 3000 + 100 * GRAPH_KINDS.index(kind) + j))
        log(f"[C] {family}: {sum(1 for p in P if p.inst.family == family)}")
    return P
