"""Add instances to a category as a new data version without touching existing instances (10-28, A 1.2.0 / B 1.3.0).

apply_extension writes ONLY the new instances' public / private files, merges their rows into index.jsonl (same line
format as instance.write_instances), archives the current frozen manifest (splits.new_version), writes the new
manifest = old manifest + new entries (build_manifest: same ordering and counts as a full build) and freezes it.
Existing instance files, hashes and split assignments are not rewritten; a full rebuild (categories/<C>/build.py,
which calls the same extension) yields the same manifest.
"""
from __future__ import annotations

import json

from .canon import dump_json, hash_hex
from .instance import inst_dir, load_index
from .splits import build_manifest, freeze, load_manifest, new_version, write_manifest


def apply_extension(category: str, planned, report: dict, version: str, old_version: str, old_frozen: str,
                    reason: str, rules_note: str, log=print) -> dict:
    d = inst_dir(category)
    idx = load_index(category)
    old_ids = {r["id"] for r in idx}
    old_hashes = {r["hash"] for r in idx}
    for p in planned:
        if p.inst.id in old_ids or p.inst.hash in old_hashes:
            raise ValueError(f"{p.inst.id}: id or content hash exists already")
        if p.split not in ("train", "val"):
            raise ValueError(f"{p.inst.id}: new instances go to train / val only, not {p.split}")
    for p in planned:
        p.inst.qbank_version = version
        dump_json(p.inst.public_record(), d / "public" / f"{hash_hex(p.inst.hash)}.json")
        dump_json(p.inst.private_record(), d / "private" / f"{p.inst.id}.json")
    rows = idx + [{"id": p.inst.id, "hash": p.inst.hash, "family": p.inst.family, "task": p.inst.task,
                   "size_bin": p.inst.private.get("size_bin"), "n": p.inst.public.get("n", p.inst.public.get("n_logical"))}
                  for p in planned]
    lines = [json.dumps(r, sort_keys=True) for r in sorted(rows, key=lambda r: r["id"])]
    (d / "index.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    old = load_manifest(category)
    fam = {r["id"]: (r["family"], r.get("size_bin")) for r in rows}
    assign = [(sp, e["id"], e["hash"], *fam[e["id"]]) for sp, es in old["splits"].items() for e in es]
    assign += [(p.split, p.inst.id, p.inst.hash, p.inst.family, p.inst.private.get("size_bin")) for p in planned]
    new_version(category, version, reason, superseded_version=old_version, superseded_frozen=old_frozen)
    man = build_manifest(category, assign, old["rules"] + " | " + rules_note)
    for sp, es in old["splits"].items():          # the old entries are kept exactly
        keep = {e["id"]: e["hash"] for e in man["splits"][sp]}
        assert all(keep.get(e["id"]) == e["hash"] for e in es), f"{category} {sp}: an existing entry changed"
    write_manifest(category, man)
    h = freeze(category)
    report = {**report, "manifest_sha256": h, "totals": man["totals"]}
    dump_json(report, d / f"extension_v{version}.json")
    log(f"[extend {category}] {len(planned)} new instances; version {version}; totals {man['totals']}; frozen {h[:16]}")
    return report
