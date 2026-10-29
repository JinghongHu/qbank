# Run: python -m qbank.categories.A.semantic_duplicates  (prints the groups as JSON; 2026-10-29)
"""Group every A instance by the exact target of its main track (a2a_2q): the canonical signed stabilizer group of the
target state (rref). Same key = same preparation task. Also the codespace track key (Hx, Hz row spaces)."""
import hashlib, json, sys, collections
from qbank.core.instance import load_index, load_public
from qbank.core.splits import load_manifest
from qbank.categories.A.instances import targets_for
from qbank.core.pauli import rref
man = load_manifest("A")
split = {e["id"]: s for s, es in man["splits"].items() for e in es}
groups = collections.defaultdict(list); cs = collections.defaultdict(list)
for row in load_index("A"):
    pub = load_public("A", row["hash"])
    for track, G in (("a2a_2q", groups), ("codespace_a2a_2q", cs)):
        if track not in pub["tracks"]:
            continue
        t = rref(targets_for(pub, pub["tracks"][track]["contract"]))[0]
        key = hashlib.sha256(b"".join(a.tobytes() for a in (t.x, t.z, t.r)) + str(pub["n"]).encode()).hexdigest()
        G[key].append(row["id"])
out = []
for name, G in (("a2a_2q", groups), ("codespace_a2a_2q", cs)):
    for k, ids in G.items():
        if len(ids) > 1:
            out.append({"track": name, "ids": sorted(ids), "splits": [split[i] for i in sorted(ids)],
                        "cross_split": len({split[i] for i in ids}) > 1})
print(json.dumps(out, indent=1))
