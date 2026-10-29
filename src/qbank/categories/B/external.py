"""Category B external test instances (test_ood) and the probe set.

External sources (fetched by data/v1/external/fetch_B.sh into .cache/external, pinned + sha256-checked):
  SATLIB uniform random 3-SAT uf20-91 / uf50-218 / uuf50-218 (no licence statement: instances are
    flagged redistributable=false)
  EPFL combinational benchmarks @ 82d8cc69 (MIT): ctrl, cavlc, int2float, dec, router
  AES S-box: computed from its definition (FIPS-197: inverse in GF(2^8) mod x^8+x^4+x^3+x+1, then the affine map with 0x63)
Probe: small single-output functions; lower bound on the Toffoli/AND count = max(deg(f) - 1, 0) (algebraic degree via the
ANF; any X/CX/Toffoli-type circuit computing y xor f(x) with t AND-type gates has multiplicative complexity <= t, and
MC(f) >= deg(f) - 1). The report states where the best baseline attains this bound (then it is optimal).
"""
from __future__ import annotations

import io
import tarfile
from pathlib import Path

import numpy as np

from ...core.aig import AIG
from ...core.canon import file_sha256
from ...core.instance import PKG_ROOT
from ...core.seeds import rng_for, split_seed
from . import functions as F
from .generate import Planned, make_instance, size_bin

EXT = PKG_ROOT / ".cache" / "external"
SATLIB = {  # archive -> sha256 recorded in Phase 0 (phase0/recon/recon_datasets.md §7)
    "uf20-91.tar.gz": "be2835295e8500bb28f0314eba70bd0deaff1250b187260f7b6d0772bdf111a5",
    "uf50-218.tar.gz": "a40862e52dfdce78620b037254579a02dbda8182d2879433658a4c15cb00327c",
    "uuf50-218.tar.gz": "24cc9f492673e0f975fecc56b3a4d8ac21c385cc46205d83b7491a787f43e13d",
}
EPFL_COMMIT = "82d8cc6910419298e713a46644ed59fd3df53038"
EPFL = ["random_control/ctrl.aig", "random_control/cavlc.aig", "random_control/int2float.aig", "random_control/dec.aig",
        "random_control/router.aig"]


def parse_dimacs(text: str):
    nv, clauses, cur = None, [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in "c%":
            if line.startswith("%"):
                break          # SATLIB files end with a non-standard "%\n0\n" trailer
            continue
        if line.startswith("p"):
            nv = int(line.split()[2])
            continue
        for tok in line.split():
            v = int(tok)
            if v == 0:
                if cur:
                    clauses.append(cur)
                cur = []
            else:
                cur.append(v)
    return nv, clauses


def _satlib_members(archive: str) -> list[tuple[str, str]]:
    p = EXT / "satlib" / archive
    if file_sha256(p) != SATLIB[archive]:
        raise RuntimeError(f"checksum mismatch for {archive}")
    out = []
    with tarfile.open(p) as tf:
        for m in sorted(tf.getmembers(), key=lambda m: m.name):
            if m.isfile() and m.name.endswith(".cnf"):
                out.append((m.name.split("/")[-1], tf.extractfile(m).read().decode()))
    return out


def aig_from_truth_tables(tt: np.ndarray, n: int, names_in=None, names_out=None) -> AIG:
    """Shannon (mux-tree) construction with structural hashing; callers normally ABC-optimise afterwards."""
    g = AIG(n, input_names=names_in or [f"x{i}" for i in range(n)])
    memo = {}

    def build(bits: tuple, var: int):
        if all(b == 0 for b in bits):
            return 0
        if all(b == 1 for b in bits):
            return 1
        key = (bits, var)
        if key in memo:
            return memo[key]
        half = len(bits) // 2
        # bits indexed by x; variable `var` is the top remaining (most significant of the slice)
        lo, hi = build(bits[:half], var - 1), build(bits[half:], var - 1)
        x = g.input_lit(var - 1)
        r = g.OR(g.AND(x ^ 1, lo), g.AND(x, hi))
        memo[key] = r
        return r
    for j, row in enumerate(tt):
        g.add_output(build(tuple(int(b) for b in row), n), (names_out or [])[j] if names_out else f"y{j}")
    return g.cleanup()


def aes_sbox() -> list[int]:
    def mul(a, b):
        r = 0
        while b:
            if b & 1:
                r ^= a
            a = ((a << 1) ^ 0x11B) if a & 0x80 else (a << 1)
            b >>= 1
        return r
    inv = [0] * 256
    for x in range(1, 256):
        for y in range(1, 256):
            if mul(x, y) == 1:
                inv[x] = y
                break
    s = []
    for x in range(256):
        b = inv[x]
        o = 0
        for i in range(8):
            bit = ((b >> i) ^ (b >> ((i + 4) % 8)) ^ (b >> ((i + 5) % 8)) ^ (b >> ((i + 6) % 8)) ^ (b >> ((i + 7) % 8)) ^ (0x63 >> i)) & 1
            o |= bit << i
        s.append(o)
    return s


def generate_external(log=print) -> list[Planned]:
    from ...baselines.tools_b import abc_optimize
    P = []
    j = 0
    # satisfiable formulas only: an unsatisfiable formula (uuf*) is the constant-0 function, whose oracle is the empty
    # circuit (v1.0 contained 12 uuf50 instances; removed in v1.1)
    for archive, take, kind in (("uf20-91.tar.gz", 30, "phase"), ("uf50-218.tar.gz", 24, "phase")):
        for name, text in _satlib_members(archive)[:take]:
            nv, clauses = parse_dimacs(text)
            aig = F.cnf_to_aig(nv, clauses)
            src = {"kind": "external", "name": "SATLIB " + archive, "version": "SATLIB 1.4.4",
                   "ref": "https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html", "license": "none stated",
                   "file": name, "archive_sha256": SATLIB[archive]}
            fam = "satlib"
            P.append(Planned("test_ood", make_instance(f"B.phase.satlib.{name[:-4]}", aig, kind, fam, {"file": name}, src,
                                                       {"redistributable": False, "satisfiable": archive.startswith("uf"),
                                                        "size_bin": size_bin(nv)})))
            j += 1
    log(f"[B external] SATLIB {j}")
    for rel in EPFL:
        p = EXT / "epfl" / rel
        aig = AIG.from_aiger(p.read_bytes())
        src = {"kind": "external", "name": "EPFL combinational benchmark suite", "version": EPFL_COMMIT,
               "ref": "https://github.com/lsils/benchmarks", "license": "MIT", "file": rel, "sha256": file_sha256(p)}
        nm = Path(rel).stem
        P.append(Planned("test_ood", make_instance(f"B.bitflip.epfl.{nm}", aig, "bitflip", "epfl", {"file": rel}, src,
                                                   {"redistributable": True, "size_bin": size_bin(aig.num_inputs)})))
    log(f"[B external] EPFL {len(EPFL)}")
    sb = aes_sbox()
    tt = np.array([[(sb[x] >> j) & 1 for x in range(256)] for j in range(8)], dtype=np.uint8)
    aig = abc_optimize(aig_from_truth_tables(tt, 8, [f"x{i}" for i in range(8)], [f"s{j}" for j in range(8)]))
    src = {"kind": "definition", "name": "AES S-box", "version": "FIPS-197",
           "ref": "computed from the definition (GF(2^8) inverse + affine map 0x63)", "license": "public definition"}
    P.append(Planned("test_ood", make_instance("B.bitflip.sbox.aes", aig, "bitflip", "sbox", {"sbox": "AES"}, src,
                                               {"redistributable": True, "size_bin": size_bin(8)})))
    log("[B external] AES S-box")
    P += generate_structural_ood(log)
    return P


# ------------------------------------------------------------------ v1.2: more structural test_ood
CTU = EXT / "ctu"
CTU_ARCHIVES = {"ISCAS.7z": "398f9c8c59e14f342f2257284a96273a6cde0b0a7b064d22966b4e6aed4a3b47",
                "LGSynth91.7z": "949e95bd0285eb203a5d97a6ace79cef35d3da35ac89fd63bbece31fd6b0580a"}
# Selection rules (evaluated once on the archives, the resulting lists are fixed here and re-checked at build time):
#  combinational, 5 <= inputs <= 64, the ABC-optimised AIG contains at least one XOR pattern (MC-relevant structure),
#  not XOR-only (multiplicative complexity 0), not a copy of another selected circuit.
#  ISCAS-85: c17, c432 have no XOR; c1355 computes the same function as c499 (ABC `cec -n`: equivalent);
#            c2670, c5315, c7552 have more than 64 inputs.
#  LGSynth'91 (multi-level BLIF set): the C* files are the ISCAS-85 circuits again; parity is XOR-only; b1 has 3 inputs;
#            the remaining combinational circuits without an XOR pattern are not selected.
#  EPFL (other circuits with <= 64 inputs): sin, log2, square -- no constructive baseline verifiable (SAT miter > 600 s);
#            all others have more than 64 inputs.
ISCAS85 = ["c499", "c880", "c1908", "c3540", "c6288"]
LGSYNTH91 = ["9symml", "alu2", "alu4", "c8", "cm162a", "cm82a", "cm85a", "cordic", "count", "f51m", "lal", "my_adder",
             "pcle", "pcler8", "pm1", "sct", "t481", "term1", "ttt2", "z4ml"]


def abc_read(path: Path) -> AIG:
    """Netlist (.bench / .blif) -> AIG via ABC (read; strash), input/output names kept."""
    import os
    import subprocess
    import tempfile
    from ...baselines.tools_b import ABC
    with tempfile.TemporaryDirectory() as d:
        q = os.path.join(d, "out.aig")
        r = subprocess.run([ABC, "-c", f"read {path}; strash; write_aiger -s {q}"], capture_output=True, text=True,
                           timeout=120, cwd=d)
        if r.returncode != 0 or not os.path.exists(q):
            raise RuntimeError(f"ABC could not read {path.name}: {r.stdout[-300:]}")
        return AIG.from_aiger(open(q, "rb").read())


def has_xor_structure(aig: AIG) -> tuple[bool, bool]:
    """(contains an XOR pattern, is XOR-only) on the ABC-optimised AIG."""
    from ...baselines.tools_b import abc_optimize
    from ...core.xag import from_aig
    opt = abc_optimize(aig)
    x = from_aig(opt)
    return len(opt.ands) > x.num_ands, x.num_ands == 0


def generate_structural_ood(log=print) -> list[Planned]:
    from . import sboxes as SB
    from .generate import EXCLUDED
    P = []
    for nm, bits, load, rfc, desc in SB.SBOXES:
        sb = load()
        tt = np.array([[(sb[x] >> j) & 1 for x in range(1 << bits)] for j in range(bits)], dtype=np.uint8)
        from ...baselines.tools_b import abc_optimize
        aig = abc_optimize(aig_from_truth_tables(tt, bits, [f"x{i}" for i in range(bits)], [f"s{j}" for j in range(bits)]))
        src = {"kind": "external", "name": desc, "version": f"RFC {rfc}", "ref": SB.RFC_URL.format(n=rfc),
               "license": "IETF RFC (table values of a published standard)", "sha256": SB.RFC_SHA256[rfc]}
        P.append(Planned("test_ood", make_instance(f"B.bitflip.sbox.{nm}", aig, "bitflip", "sbox", {"sbox": desc}, src,
                                                   {"redistributable": True, "size_bin": size_bin(bits)})))
    log(f"[B external] cipher S-boxes {len(SB.SBOXES)}")
    for arch in CTU_ARCHIVES:
        got = file_sha256(CTU / arch)
        if got != CTU_ARCHIVES[arch]:
            raise RuntimeError(f"{arch}: sha256 {got} != pinned {CTU_ARCHIVES[arch]}")
    for fam, names, sub, archive, ext in (("iscas85", ISCAS85, CTU / "ISCAS" / "bench", "ISCAS.7z", "bench"),
                                          ("mcnc", LGSYNTH91, CTU / "LGSynth91" / "LGSynth91" / "blif", "LGSynth91.7z", "blif")):
        k = 0
        for nm in names:
            path = sub / f"{nm}.{ext}"
            aig = abc_read(path)
            xor, xor_only = has_xor_structure(aig)
            if not (5 <= aig.num_inputs <= 64 and xor and not xor_only):
                raise RuntimeError(f"{fam}/{nm} no longer satisfies the selection rule")
            src = {"kind": "external", "name": "ISCAS-85" if fam == "iscas85" else "MCNC LGSynth'91",
                   "version": f"CTU benchmark collection {archive}", "ref": "https://ddd.fit.cvut.cz/www/prj/Benchmarks/",
                   "license": "none stated", "file": f"{nm}.{ext}", "archive_sha256": CTU_ARCHIVES[archive]}
            try:
                inst = make_instance(f"B.bitflip.{fam}.{nm}", aig, "bitflip", fam, {"file": f"{nm}.{ext}"}, src,
                                     {"redistributable": False, "size_bin": size_bin(aig.num_inputs)})
            except RuntimeError as e:             # no constructive baseline verifiable: not admitted (logged)
                EXCLUDED.append({"family": fam, "file": f"{nm}.{ext}", "split": "test_ood", "reason": str(e)})
                log(f"[B external] {fam}/{nm} excluded: {e}")
                continue
            P.append(Planned("test_ood", inst))
            k += 1
        log(f"[B external] {fam} {k}")
    return P


def anf_degree(row: np.ndarray, n: int) -> int:
    a = row.astype(np.uint8).copy()
    for i in range(n):          # Moebius transform
        step = 1 << i
        for x in range(1 << n):
            if x & step:
                a[x] ^= a[x ^ step]
    return max((bin(x).count("1") for x in range(1 << n) if a[x]), default=0)


def generate_probe(log=print) -> list[Planned]:
    P = []
    for n in (3, 4, 5, 6):
        for j in range(5):
            seed = split_seed("probe", 100 * n + j)
            rng = rng_for("B.probe", n, seed)
            row = rng.integers(0, 2, size=1 << n).astype(np.uint8)
            if row.sum() in (0, 1 << n):
                row[0] ^= 1
            from ...baselines.tools_b import abc_optimize
            aig = abc_optimize(aig_from_truth_tables(row[None, :], n))
            deg = anf_degree(row, n)
            src = {"kind": "generator", "name": "random_small_function", "version": "1", "ref": "", "license": "qbank"}
            P.append(Planned("probe", make_instance(f"B.bitflip.probe.n{n}.s{seed}", aig, "bitflip", "probe_small",
                                                    {"n": n, "seed": seed}, src,
                                                    {"size_bin": "probe", "anf_degree": deg,
                                                     "toffoli_lower_bound": max(deg - 1, 0),
                                                     "lower_bound_reason": "Toffoli/AND count >= multiplicative complexity >= deg(f) - 1"})))
    log(f"[B probe] {len(P)}")
    return P
