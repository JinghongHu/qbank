"""Canonical JSON and content hashing.

hash = "sha256:" + SHA256(b"qbank-v1\\n" + canonical_json({"category", "task", "canon"}))
canonical_json: sorted keys, separators (",", ":"), UTF-8, no NaN/inf. Binary floats must not appear in hashed
content: encode reals with float.hex() (see fhex) or as rational strings.
"""
from __future__ import annotations

import hashlib
import json

PREFIX = b"qbank-v1\n"


def _check_no_float(obj, path="$"):
    if isinstance(obj, float):
        raise TypeError(f"binary float in hashed content at {path}; use fhex()")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"non-string key at {path}")
            _check_no_float(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _check_no_float(v, f"{path}[{i}]")


def canonical_json(obj, allow_float: bool = False) -> bytes:
    if not allow_float:
        _check_no_float(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(category: str, task: str, canon) -> str:
    return "sha256:" + sha256_hex(PREFIX + canonical_json({"category": category, "task": task, "canon": canon}))


def hash_hex(h: str) -> str:
    return h.split(":", 1)[1] if h.startswith("sha256:") else h


def fhex(x: float) -> str:
    return float(x).hex()


def dump_json(obj, path, allow_float: bool = True) -> None:
    """Deterministic pretty JSON for stored files (sorted keys, trailing newline)."""
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n"
    p.write_text(text, encoding="utf-8")


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
