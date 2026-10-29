"""Split manifests: data/v1/splits/<C>.json (+ FROZEN.sha256). Frozen manifests are read-only; changes need a new version."""
from __future__ import annotations

import json
import os
import stat
from collections import Counter
from datetime import date

from .canon import dump_json, file_sha256
from .instance import data_root
from .seeds import SPLITS


# data version per category (a frozen manifest may only change by publishing a new version; see new_version())
DATA_VERSIONS = {"A": "1.2.0", "B": "1.3.0", "C": "1.1.0", "D": "1.0.0"}   # A 1.2.0 / B 1.3.0: 10-28 (core/extend.py)


def versions_path():
    return data_root() / "splits" / "versions.json"


def version_history() -> dict:
    p = versions_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def new_version(category: str, version: str, reason: str, superseded_manifest=None, superseded_sha256: str | None = None,
                superseded_version: str = "1.0.0", superseded_frozen: str | None = None) -> None:
    """Archive the current (or the given superseded) manifest under splits/archive/<C>.v<old>.json, record the version
    history, and lift the freeze so that the new version can be built and frozen."""
    import shutil
    arch = data_root() / "splits" / "archive"
    arch.mkdir(parents=True, exist_ok=True)
    src = superseded_manifest or split_path(category)
    dst = arch / f"{category}.v{superseded_version}.json"
    shutil.copyfile(src, dst)
    os.chmod(dst, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    hist = version_history()
    h = hist.setdefault(category, [])
    rec = {"sha256": superseded_sha256 or file_sha256(dst), "frozen": superseded_frozen,
           "archived": f"splits/archive/{dst.name}", "superseded_by": version}
    old = next((e for e in h if e["version"] == superseded_version), None)
    if old is None:
        h.append({"version": superseded_version, **rec})
    elif not old.get("sha256"):
        old.update(rec)        # the entry that announced this version gets its archive record when it is superseded
    h.append({"version": version, "reason": reason, "created": date.today().isoformat()})
    dump_json(hist, versions_path())
    fp = frozen_path()
    if fp.exists():
        os.chmod(fp, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        keep = [l for l in fp.read_text().splitlines() if l.strip() and l.split()[1] != f"{category}.json"]
        fp.write_text("\n".join(sorted(keep)) + "\n")
    p = split_path(category)
    if p.exists():
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


def split_path(category: str):
    return data_root() / "splits" / f"{category}.json"


def frozen_path():
    return data_root() / "splits" / "FROZEN.sha256"


def build_manifest(category: str, assignments: list[tuple[str, str, str, str, str]], rules: str) -> dict:
    """assignments: (split, id, hash, family, size_bin)."""
    splits = {s: [] for s in SPLITS}
    counts = {s: Counter() for s in SPLITS}
    for sp, iid, h, fam, b in sorted(assignments, key=lambda a: (SPLITS.index(a[0]), a[1])):
        splits[sp].append({"id": iid, "hash": h})
        counts[sp][f"{fam}|{b}"] += 1
    hist = [e for e in version_history().get(category, []) if e.get("sha256")]
    return {"category": category, "qbank_version": DATA_VERSIONS.get(category, "1.0.0"),
            "supersedes": [{"version": e["version"], "sha256": e["sha256"], "archived": e["archived"]} for e in hist],
            "rules": rules, "splits": splits,
            "counts": {s: dict(sorted(c.items())) for s, c in counts.items()},
            "totals": {s: len(v) for s, v in splits.items()}}


def write_manifest(category: str, manifest: dict) -> None:
    p = split_path(category)
    if is_frozen(category):
        raise PermissionError(f"split manifest for {category} is frozen; publish a new version instead")
    dump_json(manifest, p)


def is_frozen(category: str) -> bool:
    fp = frozen_path()
    if not fp.exists():
        return False
    return any(line.split()[1] == f"{category}.json" for line in fp.read_text().splitlines() if line.strip())


def freeze(category: str) -> str:
    p = split_path(category)
    h = file_sha256(p)
    fp = frozen_path()
    lines = [l for l in (fp.read_text().splitlines() if fp.exists() else []) if l.strip() and l.split()[1] != f"{category}.json"]
    lines.append(f"{h} {category}.json  v{load_manifest(category).get('qbank_version', '1.0.0')} frozen {date.today().isoformat()}")
    if fp.exists():
        os.chmod(fp, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    fp.write_text("\n".join(sorted(lines)) + "\n")
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return h


def verify_frozen(category: str) -> bool:
    fp = frozen_path()
    for line in fp.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == f"{category}.json":
            return parts[0] == file_sha256(split_path(category))
    raise KeyError(f"{category} not frozen")


def load_manifest(category: str) -> dict:
    return json.loads(split_path(category).read_text(encoding="utf-8"))


def load_split(category: str, split: str) -> list[dict]:
    return load_manifest(category)["splits"][split]
