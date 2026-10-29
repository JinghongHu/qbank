"""Prompt isolation: LLM task descriptions must not name test instances or held-out families/parameters.
Per category: a list of held-out family / source names (FORBIDDEN_TERMS) plus every test_in / test_ood instance id
(and, for codes, their [[n,k]] parameters)."""
from __future__ import annotations

import re

# held-out families (O), sporadic/published test codes and their common names (case-insensitive substrings)
FORBIDDEN_TERMS_A = [
    "hypergraph product", "hgp", "many-hypercube", "many hypercube", "hypercube", "iceberg", "c4/c6", "c4c6", "carbon",
    "shor", "golay", "toric", "unrotated", "planar code", "bacon", "five-qubit", "5-qubit", "perfect code", "gottesman",
    "symplectic double", "concatenat", "lifted product", "gross code", "gross", "bravyi", "shyps",
]


# held-out (test_ood) sources and families of categories B-E
FORBIDDEN_TERMS = {
    "A": FORBIDDEN_TERMS_A,
    "B": ["satlib", "uf20", "uf50", "uuf50", "epfl", "int2float", "cavlc", "s-box", "sbox", "aes", "rijndael"],
    "C": ["queko", "qubikos", "mqt bench", "mqtbench", "hamlib", "sycamore", "rochester", "aspen", "tokyo",
          "triangular lattice", "hexagonal lattice", "3d grid", "heisenberg lattice"],
    "D": ["reed-muller", "reed muller", "simplex code", "hamming code", "codeword", "fixed-weight", "fixed weight",
          "dicke state with k >= 3", "k>=3"],
}


def forbidden_patterns(category: str) -> list[tuple[str, re.Pattern]]:
    from .instance import load_index, load_private
    from .splits import load_manifest
    pats = [(t, re.compile(re.escape(t), re.I)) for t in FORBIDDEN_TERMS.get(category, [])]
    man = load_manifest(category)
    for split in ("test_in", "test_ood"):
        for e in man["splits"][split]:
            pats.append((e["id"], re.compile(re.escape(e["id"]))))
            priv = load_private(category, e["id"])
            code = priv["private"].get("code")
            if code:
                n, k = code["n"], code["k"]
                pats.append((f"[[{n},{k},...]]", re.compile(rf"\[\[\s*{n}\s*,\s*{k}\s*[,\]]")))
    return pats


def lint(category: str, text: str) -> list[dict]:
    hits = []
    for label, pat in forbidden_patterns(category):
        for m in pat.finditer(text):
            hits.append({"term": label, "at": m.start(), "context": text[max(0, m.start() - 30): m.end() + 30]})
    return hits
