"""Seed ranges per split (disjoint by construction) and deterministic seed derivation."""
from __future__ import annotations

import hashlib

import numpy as np

from .canon import canonical_json

SPLIT_BASE = {"train": 0, "val": 10_000, "test_in": 20_000, "test_ood": 30_000, "probe": 40_000}
SPLITS = ("train", "val", "test_in", "test_ood", "probe")


def split_seed(split: str, i: int) -> int:
    if not 0 <= i < 10_000:
        raise ValueError("seed index out of range")
    return SPLIT_BASE[split] + i


def split_of_seed(seed: int) -> str:
    for s in reversed(SPLITS):
        if seed >= SPLIT_BASE[s]:
            return s
    raise ValueError(seed)


def derive_int(*parts) -> int:
    """64-bit integer derived from (family, params, seed, ...) via SHA-256 of their canonical JSON."""
    h = hashlib.sha256(canonical_json(list(parts))).digest()
    return int.from_bytes(h[:8], "big")


def rng_for(*parts) -> np.random.Generator:
    return np.random.default_rng(derive_int(*parts))
