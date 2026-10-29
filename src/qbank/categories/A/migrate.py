"""A v1.0 -> v1.1: the instance built from MQT QECC's construct_bb_code(90) (l and m swapped,
distance <= 2) leaves the bb_published family.

    A.css_zero.bb_published.mqt90  ->  A.css_zero.bb_mqt_n90_d2.mqt90   (family bb_mqt_n90_d2)

Only names change: the public record and its content hash, the split (test_in) and every other instance are unchanged,
so baseline results (cached by hash) stay valid; records and best_known are re-aggregated under the new id. The v1.0
manifest is archived (splits/archive/A.v1.0.0.json) and the history is written to splits/versions.json. A fresh
`qbank generate A` produces the v1.1 names directly (categories/A/generate.py); this migration only converts an
existing v1.0 data directory.
"""
from __future__ import annotations

import json

from ...core.canon import dump_json, file_sha256
from ...core.instance import data_root, inst_dir
from ...core.splits import build_manifest, frozen_path, load_manifest, new_version, split_path, write_manifest

OLD, NEW, NEW_FAMILY = "A.css_zero.bb_published.mqt90", "A.css_zero.bb_mqt_n90_d2.mqt90", "bb_mqt_n90_d2"
REASON = ("Instance A.css_zero.bb_published.mqt90 renamed to A.css_zero.bb_mqt_n90_d2.mqt90 and its family from bb_published to bb_mqt_n90_d2: it comes from construct_bb_code(90) of MQT QECC 2.0.0, which swaps l and m; its distance is <= 2 and it is not the [[90,8,10]] code of Bravyi et al. (that one is bravyi90). Content hash, split and all other instances unchanged")


def migrate_v1_1(log=print) -> dict:
    d = inst_dir("A")
    old_p, new_p = d / "private" / f"{OLD}.json", d / "private" / f"{NEW}.json"
    if new_p.exists() and not old_p.exists():
        log("[migrate A] already at v1.1")
        return {"status": "already migrated"}
    man_old = split_path("A")
    frozen = next((l.split()[-1] for l in frozen_path().read_text().splitlines() if l.split()[1:2] == ["A.json"]), None)
    new_version("A", "1.1.0", REASON, superseded_sha256=file_sha256(man_old), superseded_version="1.0.0",
                superseded_frozen=frozen)
    # private record
    rec = json.loads(old_p.read_text(encoding="utf-8"))
    rec["id"], rec["family"] = NEW, NEW_FAMILY
    dump_json(rec, new_p)
    old_p.unlink()
    # every A record now belongs to data version 1.1.0 (as a fresh build would stamp them)
    for p in sorted((d / "private").glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if r.get("qbank_version") != "1.1.0":
            r["qbank_version"] = "1.1.0"
            dump_json(r, p)
    # index
    idx_p = d / "index.jsonl"
    rows = [json.loads(l) for l in idx_p.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        if r["id"] == OLD:
            r["id"], r["family"] = NEW, NEW_FAMILY
    rows.sort(key=lambda r: r["id"])
    idx_p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    # manifest (rebuilt from the index so that counts per family are right)
    from .build import SPLIT_RULES
    man = load_manifest("A")
    split_of = {e["id"]: s for s, es in man["splits"].items() for e in es}
    split_of[NEW] = split_of.pop(OLD)
    fam = {r["id"]: (r["family"], r.get("size_bin")) for r in rows}
    assign = [(split_of[i], i, e["hash"], *fam[i]) for s, es in man["splits"].items() for e in es
              for i in [NEW if e["id"] == OLD else e["id"]]]
    new_man = build_manifest("A", assign, SPLIT_RULES)
    write_manifest("A", new_man)
    # published values: same instance, new id
    pub_p = data_root() / "published" / "A.jsonl"
    if pub_p.exists():
        pub_p.write_text(pub_p.read_text(encoding="utf-8").replace(f'"{OLD}"', f'"{NEW}"'), encoding="utf-8")
    log(f"[migrate A] {OLD} -> {NEW}; manifest rebuilt ({sum(new_man['totals'].values())} instances)")
    return {"status": "migrated", "totals": new_man["totals"]}
