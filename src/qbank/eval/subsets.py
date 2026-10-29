"""Named instance subsets for evolution experiments, e.g. fitness on B's structural families only.

A subset is decided from the instance's private record (harness side); exported packs still contain public parts only.
  B: structural       -- not solution-sparse (private solution_sparse is False; rule in categories/B/build.py)
     solution_sparse  -- n_solutions < 2^(n/2) for a single-output function
"""
from __future__ import annotations

SUBSETS = {
    "B": {"structural": lambda priv: not priv.get("solution_sparse", False),
          "solution_sparse": lambda priv: bool(priv.get("solution_sparse", False))},
}


def predicate(category: str, subset: str | None):
    if subset is None:
        return None
    try:
        return SUBSETS[category][subset]
    except KeyError:
        known = sorted(SUBSETS.get(category, {}))
        raise ValueError(f"unknown subset {subset!r} for category {category} (known: {known or 'none'})") from None
