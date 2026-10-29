"""Export pack for evolution experiments: only train + val, and only public parts go to candidates.

<out>/candidate_view/<split>/<hash>.json   public view (what candidates may read)
<out>/harness/best_known.jsonl              train/val best_known (fitness side only, never shown to candidates)
<out>/harness/tracks.json                   track -> contract/metric
<out>/MANIFEST.json                         counts + sha256 of every file
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..core.canon import dump_json, file_sha256, hash_hex
from ..core.instance import data_root, load_public
from ..core.splits import load_manifest

EXPORT_SPLITS = ("train", "val")
PRIVATE_KEYS = {"id", "family", "source", "params", "private", "contracts"}


def export_pack(category: str, out: Path, subset: str | None = None) -> dict:
    """subset: optional named subset (qbank.eval.subsets), decided from private fields; the pack stays public-only."""
    from ..core.instance import load_private
    from .subsets import predicate
    keep = predicate(category, subset)
    if out.exists():
        shutil.rmtree(out)
    man = load_manifest(category)
    from .api import evaluation_exclusions
    drop = evaluation_exclusions(category)      # 10-29: the later copy of a task listed under two names
    ids = set()
    counts = {}
    for split in EXPORT_SPLITS:
        entries = [e for e in man["splits"][split] if e["id"] not in drop]
        if keep is not None:
            entries = [e for e in entries if keep(load_private(category, e["id"])["private"])]
        counts[split] = len(entries)
        for e in entries:
            pub = load_public(category, e["hash"])
            leaked = PRIVATE_KEYS & set(pub)
            if leaked:
                raise RuntimeError(f"public record of {e['id']} contains private keys {leaked}")
            dump_json(pub, out / "candidate_view" / split / f"{hash_hex(e['hash'])}.json")
            ids.add(e["id"])
    bk = data_root() / "baselines" / category / "best_known.jsonl"
    rows = []
    if bk.exists():
        for line in bk.read_text().splitlines():
            r = json.loads(line)
            if r["instance_id"] in ids:
                rows.append({"hash": r["hash"], "track": r["track"], "value": r["value"], "source_kind": r.get("source_kind")})
    (out / "harness").mkdir(parents=True, exist_ok=True)
    (out / "harness" / "best_known.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    files = sorted(p for p in out.rglob("*") if p.is_file())
    manifest = {"category": category, "subset": subset, "splits": counts, "excluded_duplicates": sorted(drop),
                "note": "candidate_view: public only; harness: fitness side only",
                "files": {str(p.relative_to(out)): file_sha256(p) for p in files}}
    dump_json(manifest, out / "MANIFEST.json")
    return {"category": category, "subset": subset, "splits": counts, "files": len(files)}
