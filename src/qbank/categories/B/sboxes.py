"""Block-cipher S-boxes for B test_ood (v1.2), parsed from the official RFC texts (fetched by
data/v1/external/fetch_B.sh into .cache/external/rfc, sha256-pinned in RFC_SHA256).

Every table is checked while parsing: it must be a permutation, and where the RFC states an example value or an
inverse table, the parsed table must reproduce it (e.g. RFC 3713: SBOX1[0x3d] = 86; RFC 6114: S0[0xab] = 0x7e;
RFC 7801 and RFC 5794 give the inverse tables). No table value is typed in by hand.
"""
from __future__ import annotations

import re

from ...core.canon import file_sha256
from ...core.instance import PKG_ROOT

RFC_DIR = PKG_ROOT / ".cache" / "external" / "rfc"
RFC_URL = "https://www.rfc-editor.org/rfc/rfc{n}.txt"
RFC_SHA256 = {
    3713: "126cea1768aed9257fbdf52a4e1938eb15d79c8aacb83d14f60f1320d5b8770f",   # Camellia
    5794: "e83bdeb56937cb26fc4e3cd6c230ddfa971bc27056c5f202d55820af350cd89d",   # ARIA
    6114: "d62a3f085cd067c8bdc8b82b0064b097739926385aaad177590285773973a082",   # CLEFIA
    7801: "4e78cccae8ba582fa2e316aa8cbbb404ae0355d0a06b76d685482c0a0a842c69",   # GOST R 34.12-2015 Kuznyechik
    8891: "338f68b510190c36e0cdfd0077e2d93ef9e29a5e5665ef1c8b82e5564c6c0775",   # GOST R 34.12-2015 Magma
}


def _text(n: int) -> str:
    p = RFC_DIR / f"rfc{n}.txt"
    got = file_sha256(p)
    if got != RFC_SHA256[n]:
        raise RuntimeError(f"rfc{n}.txt: sha256 {got} != pinned {RFC_SHA256[n]}")
    # drop page breaks (footer, form feed, header) so tables split across pages parse as one block
    t = p.read_text(encoding="utf-8-sig")
    return re.sub(r"\n[^\n]*\[Page \d+\]\n\f?\n?RFC \d+[^\n]*\n", "\n", t)


def _grid(block: str, row_re: str, base: int) -> list[int]:
    """16 rows of 16 values after a row label matching row_re (group 1 = row index as hex)."""
    vals = {}
    for line in block.splitlines():
        m = re.match(row_re, line)
        if not m:
            continue
        toks = line[m.end():].split()
        if len(toks) != 16:
            raise ValueError(f"row {m.group(1)}: {len(toks)} values")
        r = int(m.group(1), 16)
        for c, t in enumerate(toks):
            vals[16 * r + c] = int(t, base)
    if sorted(vals) != list(range(256)):
        raise ValueError("incomplete 16x16 table")
    return [vals[i] for i in range(256)]


def _between(t: str, start: str, end: str) -> str:
    i = t.index(start)
    j = t.index(end, i + len(start))
    return t[i + len(start):j]


def _check_perm(s: list[int], bits: int, name: str) -> list[int]:
    if sorted(s) != list(range(1 << bits)):
        raise ValueError(f"{name}: not a permutation of {bits}-bit values")
    return s


def camellia_sbox1() -> list[int]:
    t = _text(3713)
    s = _grid(_between(t, "   SBOX1:\n", "2.4.2."), r"\s{3}([0-9a-f])0:", 10)
    if s[0x3D] != 86:                                    # "For example, SBOX1[0x3d] equals 86."
        raise ValueError("Camellia SBOX1 example check failed")
    return _check_perm(s, 8, "Camellia SBOX1")


def clefia_s(which: int) -> list[int]:
    t = _text(6114)
    start, end = ("Table 1: S-Box S0", "Table 2: S-Box S1") if which == 0 else ("Table 2: S-Box S1", "\n2.4.3")
    block = _between(t, start, end) if which == 0 else t[t.index(start):t.index(start) + 2000]
    s = _grid(block, r"\s{3}([0-9a-f])\.", 16)
    if which == 0 and s[0xAB] != 0x7E:                   # "if a value 0xab is input, 0x7e is output by S0"
        raise ValueError("CLEFIA S0 example check failed")
    return _check_perm(s, 8, f"CLEFIA S{which}")


def _int_list(block: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", block)]


def kuznyechik_pi() -> list[int]:
    t = _text(7801)
    pi = _int_list(_between(t, "    Pi' =\n", ")."))
    inv_block = t[t.index("Pi^(-1)' ="):]
    inv = _int_list(inv_block[inv_block.index("(", inv_block.index("=")) + 1:inv_block.index(").")])
    inv = inv[-256:] if len(inv) > 256 else inv
    if len(pi) != 256 or len(inv) != 256 or any(inv[pi[x]] != x for x in range(256)):
        raise ValueError("Kuznyechik Pi / Pi^(-1) consistency check failed")
    return _check_perm(pi, 8, "Kuznyechik Pi")


def aria_sb2() -> list[int]:
    t = _text(5794)
    sb2 = _grid(_between(t, "      SB2:\n", "      SB3:"), r"\s{7}([0-9a-f])0\s", 16)
    sb4 = _grid(_between(t, "      SB4:\n", "For example"), r"\s{7}([0-9a-f])0\s", 16)
    if sb4[0xEF] != 0xD3 or any(sb4[sb2[x]] != x for x in range(256)):   # RFC: SB4(0xef) = 0xd3; SB4 = SB2^-1
        raise ValueError("ARIA SB2 / SB4 consistency check failed")
    return _check_perm(sb2, 8, "ARIA SB2")


def magma_pi(i: int) -> list[int]:
    t = _text(8891)
    m = re.search(rf"Pi'_{i} = \(([^)]*)\);", t)
    s = [int(x) for x in m.group(1).split(",")]
    if len(s) != 16:
        raise ValueError(f"Magma Pi'_{i}: {len(s)} values")
    return _check_perm(s, 4, f"Magma Pi'_{i}")


# (instance suffix, bits, loader, RFC number, description)
SBOXES = [("camellia_s1", 8, camellia_sbox1, 3713, "Camellia SBOX1"),
          ("clefia_s0", 8, lambda: clefia_s(0), 6114, "CLEFIA S0"),
          ("clefia_s1", 8, lambda: clefia_s(1), 6114, "CLEFIA S1"),
          ("kuznyechik_pi", 8, kuznyechik_pi, 7801, "GOST R 34.12-2015 (Kuznyechik) Pi"),
          ("aria_sb2", 8, aria_sb2, 5794, "ARIA SB2")] + \
         [(f"magma_pi{i}", 4, (lambda i=i: magma_pi(i)), 8891, f"GOST R 34.12-2015 (Magma) Pi'_{i}") for i in range(8)]
