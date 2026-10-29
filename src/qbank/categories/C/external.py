"""Category-C external sources (test_ood and probe).

QUEKO     (BSD-3-Clause, redistributable)  UCLA-VAST/QUEKO-benchmark @ 2ee23a12; x/cx circuits built from a hidden
          mapping so that a zero-SWAP routing exists; meta/*_solution.csv gives that mapping. Only BNTF + BSS (which ship
          solutions) are used; the witness routing is rebuilt and checked by qbank (-> optimal/C.jsonl).
QUBIKOS   (no licence) ping-shuo-hao/qubikos @ 442a9948; CX circuits
          with an optimal SWAP count known by construction (arXiv:2502.08839); no witness in the repository.
MQT Bench (MIT) mqt.bench 2.3.0 generators for families not used in train (INDEP level), rewritten to qbank's logical
          routing basis with Qiskit (optimization_level 1, fixed seed); measurements and barriers removed.
HamLib    (no licence on the portal) condensedmatter/tfim and heisenberg (dataset v1.1) lattice
          Hamiltonians; one first-order Trotter step with one commuting block per Pauli type.
"""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import numpy as np

from ...core.circuit import Circuit
from ...core.instance import PKG_ROOT
from ...core.seeds import rng_for
from . import generate as G

EXT = PKG_ROOT / ".cache" / "external"
QUEKO_COMMIT = "2ee23a12aff894f1861d3d49eb14d09d9f9956bd"
QUBIKOS_COMMIT = "442a994884a6a5fd37725f59b8b42c90fd1be387"
QUEKO_DIR = EXT / "queko" / f"QUEKO-benchmark-{QUEKO_COMMIT}"
QUBIKOS_DIR = EXT / "qubikos" / f"qubikos-{QUBIKOS_COMMIT}"
HAMLIB_DIR = EXT / "hamlib"
LOGICAL_BASIS = ["h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "rz", "rx", "ry", "cx", "cz", "rzz", "rxx", "ryy"]
QUEKO_DEVICE = {16: "Aspen-4", 20: "Tokyo", 53: "Rochester", 54: "Sycamore"}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def queko_devices() -> dict:
    tree = ast.parse((QUEKO_DIR / "CONNECTION.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "INDEX_CONNECTION_LIST":
            return {k: sorted(tuple(sorted(e)) for e in v) for k, v in ast.literal_eval(node.value).items()}
    raise RuntimeError("INDEX_CONNECTION_LIST not found")


def device_by_name(name: str) -> tuple[str, int, list]:
    """Unseen (QUEKO) device graphs, usable for other external circuits."""
    es = queko_devices()[name]
    N = 1 + max(max(e) for e in es)
    return f"{name} (QUEKO CONNECTION.py)", N, [list(e) for e in es]


_GATE = re.compile(r"^\s*([a-z0-9_]+)\s*(\(([^)]*)\))?\s+(.+?);\s*$")


def parse_simple_qasm2(text: str) -> Circuit:
    """Tolerant reader for the flat x/cx/cz/h/... QASM 2 files of QUEKO and QUBIKOS (QUBIKOS writes `qreg[16];`)."""
    n = None
    gates = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("//", "OPENQASM", "include", "creg", "barrier", "measure")):
            continue
        if s.startswith("qreg"):
            n = int(re.search(r"\[(\d+)\]", s).group(1))
            continue
        m = _GATE.match(s)
        if not m:
            raise ValueError(f"cannot parse QASM line {s!r}")
        g, params, args = m.group(1), m.group(3), m.group(4)
        qs = [int(x) for x in re.findall(r"\[(\d+)\]", args)]
        ps = [float(eval(x, {"pi": np.pi})) for x in params.split(",")] if params else []
        if g not in LOGICAL_BASIS:
            raise ValueError(f"gate {g} outside the logical routing basis")
        gates.append((g, qs, ps))
    c = Circuit(n)
    for g, qs, ps in gates:
        c.append(g, qs, ps)
    return c


def _src(kind, name, version, ref, licence, redistributable, extra=None):
    d = {"kind": kind, "name": name, "version": version, "ref": ref, "license": licence, "redistributable": redistributable}
    if extra:
        d.update(extra)
    return d


# ------------------------------------------------------------------ QUEKO
def queko_files() -> list[Path]:
    out = []
    for sub in ("BNTF", "BSS"):
        out += sorted((QUEKO_DIR / sub).glob("*.qasm"))
    return out


def queko_solution(stem: str) -> list[int]:
    txt = (QUEKO_DIR / "meta" / f"{stem}_solution.csv").read_text().split()
    return [int(x) for x in txt]


def queko_witness(c: Circuit, layout: list[int], N: int) -> Circuit:
    w = Circuit(N)
    for g, qs, ps in c.gates:
        w.append(g, [layout[q] for q in qs], ps)
    return w


def make_queko(path: Path, split: str):
    from ..A.generate import Planned
    c = parse_simple_qasm2(path.read_text())
    stem = path.stem
    m = re.match(r"(\d+)QBT_(\d+)CYC_([A-Z]+)_(\d+)", stem)
    nq, cyc, dens, serial = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
    dev = QUEKO_DEVICE[nq]
    dname, N, es = device_by_name(dev)
    sol = queko_solution(stem)
    src = _src("external", "QUEKO", QUEKO_COMMIT, "arXiv:2002.09783; github.com/UCLA-VAST/QUEKO-benchmark", "BSD-3-Clause", True,
               {"file": f"{path.parent.name}/{path.name}", "sha256": _sha(path)})
    inst = G.make_instance(f"C.queko.{stem}", c, None, dname, N, es, "queko", {"n": c.n, "set": path.parent.name,
                           "optimal_depth_cycles": cyc, "density": dens, "serial": serial}, src,
                           {"size_bin": G.size_bin(c.n), "known_optimal": {"swaps": 0, "witness_initial_layout": sol,
                            "depth_cycles": cyc, "source": "QUEKO construction (zero-SWAP mapping, meta/*_solution.csv)"}})
    return Planned(split, inst)


# ------------------------------------------------------------------ QUBIKOS
def qubikos_coupling(dev_dir: Path) -> list[list[int]]:
    f = next(p for p in dev_dir.iterdir() if p.suffix == ".txt")
    t = f.read_text()
    lst = ast.literal_eval(t[t.index("["): t.rindex("]") + 1])
    return sorted([sorted(map(int, e)) for e in lst])


def make_qubikos(path: Path, split: str):
    from ..A.generate import Planned
    c = parse_simple_qasm2(path.read_text())
    es = qubikos_coupling(path.parent)
    N = max(c.n, 1 + max(max(e) for e in es))
    m = re.match(r"(.+?)_(\d+)_(\d+)_(\d+)$", path.stem)
    dev, opt, n2q, idx = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    src = _src("external", "QUBIKOS", QUBIKOS_COMMIT, "arXiv:2502.08839; github.com/ping-shuo-hao/qubikos", "none (all rights reserved)",
               False, {"file": f"examples/{path.parent.name}/{path.name}", "sha256": _sha(path)})
    inst = G.make_instance(f"C.qubikos.{path.stem}", c, None, f"{dev} (QUBIKOS coupling file)", N, es, "qubikos",
                           {"n": c.n, "device": dev, "two_qubit_gates": n2q, "serial": idx}, src,
                           {"size_bin": G.size_bin(c.n), "redistributable": False,
                            "known_optimal": {"swaps": opt, "source": "QUBIKOS construction (arXiv:2502.08839); no witness shipped",
                                              "verified_by_qbank": False}})
    return Planned(split, inst)


# ------------------------------------------------------------------ MQT Bench
MQTBENCH = [  # (benchmark, sizes)
    ("ghz", (40, 100)), ("graphstate", (24, 60)), ("qft", (16, 40)), ("qftentangled", (20, 48)), ("wstate", (30, 80)),
    ("qpeexact", (16, 32)), ("qpeinexact", (18, 36)), ("vqe_su2", (20, 50)), ("vqe_real_amp", (24, 64)),
    ("vqe_two_local", (16, 40)), ("qnn", (20, 50)), ("dj", (30, 80)), ("bv", (40, 100)), ("ae", (12, 24)),
    ("cdkm_ripple_carry_adder", (20, 40)), ("draper_qft_adder", (16, 32)), ("modular_adder", (16, 32)),
    ("bmw_quark_cardinality", (16, 40)), ("grover", (8, 10)), ("full_adder", (18, 34)),
]


def mqtbench_circuit(name: str, n: int) -> Circuit:
    from mqt.bench import BenchmarkLevel, get_benchmark
    from qiskit import QuantumCircuit, transpile
    if name == "graphstate":
        # mqt.bench's graphstate draws its random regular graph with seed=None (different on every call): call the
        # generator directly with a fixed derived seed so that the instance is reproducible
        from mqt.bench.benchmarks.graphstate import create_circuit
        from ...core.seeds import derive_int
        qc = create_circuit(n, degree=2, seed=derive_int("C-mqtbench-graphstate", n) % (2 ** 31))
    else:
        qc = get_benchmark(name, BenchmarkLevel.INDEP, n)
    clean = QuantumCircuit(qc.num_qubits)
    for ins in qc.data:
        if ins.operation.name in ("measure", "barrier"):
            continue
        clean.append(ins.operation, [clean.qubits[qc.find_bit(q).index] for q in ins.qubits])
    t = transpile(clean, basis_gates=LOGICAL_BASIS, optimization_level=1, seed_transpiler=0)
    c = Circuit(t.num_qubits)
    for ins in t.data:
        g = ins.operation.name
        if g in ("barrier", "id", "delay"):
            continue
        c.append(g, [t.find_bit(q).index for q in ins.qubits], [float(x) for x in ins.operation.params])
    return c


def _ood_device(n: int, rng) -> tuple[str, int, list]:
    """An unseen QUEKO device when one fits without wasting more than 3x the qubits, else heavy-hex or grid."""
    opts = [("Tokyo", 20), ("Rochester", 53), ("Sycamore", 54)]
    fit = [d for d, sz in opts if n <= sz <= max(3 * n, 20)]
    cands = [("queko", d) for d in fit[:1]] + [("hh", None), ("grid", None)]
    kind, d = cands[int(rng.integers(len(cands)))]
    if kind == "queko":
        return device_by_name(d)
    if kind == "hh":
        return G.heavy_hex_device(n)
    return G.device("grid", n, rng)


def make_mqtbench(name: str, n: int, split: str):
    import importlib.metadata as md
    from ..A.generate import Planned
    c = mqtbench_circuit(name, n)
    rng = rng_for("C-ext", "mqtbench", name, n)
    dname, N, es = _ood_device(c.n, rng)
    src = _src("external", "MQT Bench", md.version("mqt.bench"), "github.com/munich-quantum-toolkit/bench (PyPI mqt.bench)", "MIT", True,
               {"benchmark": name, "level": "INDEP", "rewrite": f"qiskit {md.version('qiskit')} transpile(basis={LOGICAL_BASIS}, "
                                                              f"optimization_level=1, seed_transpiler=0); measure/barrier removed"})
    inst = G.make_instance(f"C.mqtbench.{name}.n{c.n}", c, None, dname, N, es, "mqtbench", {"n": c.n, "benchmark": name}, src,
                           {"size_bin": G.size_bin(c.n)})
    return Planned(split, inst)


# ------------------------------------------------------------------ HamLib
HAMLIB_FILES = {"tfim": ("tfim.zip", "841f2139213b08ee03125fa196d77cf090293aaa69993391fc1e02b0a9968eee"),
                "heis": ("heis.zip", "d6df869372b09c3d9d38d0671bcdd919cd8992861d4f6777054eb94a3380e00e")}
_TERM = re.compile(r"\(?\s*([-+0-9.e]+)\s*\)?\s*\[([^\]]*)\]")


def hamlib_terms(model: str, key: str) -> tuple[int, list]:
    import h5py
    f = h5py.File(HAMLIB_DIR / f"{model}.hdf5", "r")
    ds = f[key]
    n = int(ds.attrs["nqubits"])
    txt = ds[()].decode() if isinstance(ds[()], bytes) else str(ds[()])
    terms = []
    for coef, ops in _TERM.findall(txt):
        ops = ops.split()
        if ops:
            terms.append((float(coef), [(o[0], int(o[1:])) for o in ops]))
    return n, terms


def hamlib_circuit(n: int, terms: list) -> tuple[Circuit, list, dict]:
    """One Trotter step; two-qubit terms grouped by Pauli type (XX, YY, ZZ: each group commutes), then 1-local fields."""
    groups = {"XX": [], "YY": [], "ZZ": []}
    fields = {"X": [], "Y": [], "Z": []}
    coeffs = set()
    for coef, ops in terms:
        if len(ops) == 2 and ops[0][0] == ops[1][0]:
            groups[ops[0][0] * 2].append(tuple(sorted((ops[0][1], ops[1][1]))))
            coeffs.add(("2q", coef))
        elif len(ops) == 1:
            fields[ops[0][0]].append(ops[0][1])
            coeffs.add(("1q", coef))
        else:
            raise ValueError(f"unsupported HamLib term {ops}")
    c = Circuit(n)
    blocks = []
    b = 0
    for P in ("XX", "YY", "ZZ"):
        if groups[P]:
            for u, v in sorted(set(groups[P])):
                c.append("r" + P.lower(), [u, v], [f"J_{P.lower()}"])
                blocks.append(b)
            b += 1
    for P in ("X", "Y", "Z"):
        for q in sorted(set(fields[P])):
            c.append("r" + P.lower(), [q], ["h"])
            blocks.append(b)
    return c, blocks, {"coefficients": sorted(coeffs)}


HAMLIB_PICK = [  # (model, lattice prefix): lattices not used by any training family
    ("tfim", "graph-2D-triag-pbc"), ("tfim", "graph-2D-triag-nonpbc"), ("tfim", "graph-2D-hex-pbc"), ("tfim", "graph-2D-hex-nonpbc"),
    ("tfim", "graph-3D-grid-pbc"), ("tfim", "graph-3D-grid-nonpbc"), ("tfim", "graph-2D-grid-pbc"), ("tfim", "graph-1D-grid-pbc"),
    ("heis", "graph-2D-triag-pbc"), ("heis", "graph-2D-triag-nonpbc"), ("heis", "graph-2D-hex-pbc"), ("heis", "graph-3D-grid-pbc"),
    ("heis", "graph-3D-grid-nonpbc"), ("heis", "graph-2D-grid-pbc"), ("heis", "graph-2D-grid-nonpbc"),
]


def hamlib_keys(model: str, prefix: str, lo: int = 9, hi: int = 156) -> list[tuple[str, int]]:
    import csv
    fn = {"tfim": "condensedmatter_tfim.csv", "heis": "condensedmatter_heisenberg.csv"}[model]
    out = {}
    with open(HAMLIB_DIR / fn) as fh:
        for row in csv.DictReader(fh):
            key = row["Dataset"].lstrip("/")
            if not key.startswith(prefix + "-qubitnodes"):
                continue
            n = int(row["nqubits"])
            if lo <= n <= hi:
                lattice = re.sub(r"_h-[^_]*$", "", key)
                # one field value per lattice: prefer h-1 (tfim) / the first listed (heis)
                if lattice not in out or key.endswith("_h-1"):
                    out[lattice] = (key, n)
    return sorted(out.values(), key=lambda x: (x[1], x[0]))


def make_hamlib(model: str, key: str, split: str):
    from ..A.generate import Planned
    n, terms = hamlib_terms(model, key)
    c, blocks, meta = hamlib_circuit(n, terms)
    rng = rng_for("C-ext", "hamlib", model, key)
    dname, N, es = _ood_device(n, rng)
    fname, zsha = HAMLIB_FILES[model]
    src = _src("external", "HamLib", "v1.1", "arXiv:2306.13126; portal.nersc.gov/cfs/m888/dcamps/hamlib/", "none (portal states no licence)",
               False, {"file": f"condensedmatter/{'tfim' if model == 'tfim' else 'heisenberg'}/{fname}", "zip_sha256": zsha, "dataset": key})
    inst = G.make_instance(f"C.hamlib.{model}.{key}", c, blocks, dname, N, es, "hamlib", {"n": n, "model": model, "lattice": key},
                           src, {"size_bin": G.size_bin(n), "redistributable": False, **meta})
    return Planned(split, inst)


# ------------------------------------------------------------------ assembly
def _pick(items, k, tag):
    order = sorted(items, key=lambda x: hashlib.sha256(f"{tag}|{x}".encode()).hexdigest())
    return order[:k], order[k:]


def generate_external(log=print) -> list:
    P = []
    files = queko_files()
    # probe: 60 QUEKO instances with the smallest depths (5-15 cycles) on the 16- and 54-qubit devices; test_ood: 300 others
    small = [f for f in files if re.match(r"(16|54)QBT_(05|10|15)CYC", f.stem)]
    probe, _ = _pick([str(f) for f in small], 60, "queko-probe")
    rest = [str(f) for f in files if str(f) not in set(probe)]
    ood, _ = _pick(rest, 300, "queko-ood")
    P += [make_queko(Path(f), "probe") for f in sorted(probe)]
    P += [make_queko(Path(f), "test_ood") for f in sorted(ood)]
    log(f"[C ext] QUEKO: probe {len(probe)}, test_ood {len(ood)}")
    qb = sorted((QUBIKOS_DIR / "examples").glob("*/*.qasm"))
    P += [make_qubikos(f, "test_ood") for f in qb]
    log(f"[C ext] QUBIKOS: test_ood {len(qb)}")
    k = 0
    for name, sizes in MQTBENCH:
        for n in sizes:
            try:
                P.append(make_mqtbench(name, n, "test_ood"))
                k += 1
            except Exception as e:
                log(f"[C ext] MQT Bench {name} n={n} skipped: {type(e).__name__}: {e}")
    log(f"[C ext] MQT Bench: test_ood {k}")
    k = 0
    for model, prefix in HAMLIB_PICK:
        keys = hamlib_keys(model, prefix)
        if not keys:
            continue
        idx = np.linspace(0, len(keys) - 1, min(4, len(keys))).round().astype(int)
        for i in sorted(set(idx.tolist())):
            P.append(make_hamlib(model, keys[i][0], "test_ood"))
            k += 1
    log(f"[C ext] HamLib: test_ood {k}")
    return P
