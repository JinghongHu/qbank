"""Instance record, storage layout and public view.

Layout (under data/v1/instances/<C>/):
  public/<hashhex>.json   {"hash": ..., **public}      -- the ONLY thing a candidate program may see
  private/<id>.json        all other fields + "public_hash"
  index.jsonl              one line per instance: id, hash, family, task, size_bin (sorted by id)
"""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .. import QBANK_VERSION
from .canon import dump_json, hash_hex

PKG_ROOT = Path(__file__).resolve().parents[3]          # .../qbank


def data_root() -> Path:
    return Path(os.environ.get("QBANK_DATA", PKG_ROOT / "data" / "v1"))


@dataclass
class Instance:
    id: str
    category: str
    task: str
    family: str
    source: dict
    params: dict
    public: dict
    private: dict
    contracts: list
    tracks: list
    hash: str
    qbank_version: str = QBANK_VERSION

    def private_record(self) -> dict:
        return {"id": self.id, "qbank_version": self.qbank_version, "category": self.category, "task": self.task,
                "family": self.family, "source": self.source, "params": self.params, "private": self.private,
                "contracts": self.contracts, "tracks": self.tracks, "hash": self.hash, "public_hash": self.hash}

    def public_record(self) -> dict:
        rec = copy.deepcopy(self.public)
        rec["hash"] = self.hash
        return rec

    @staticmethod
    def from_records(priv: dict, pub: dict) -> "Instance":
        pub = dict(pub)
        h = pub.pop("hash")
        if h != priv["hash"]:
            raise ValueError(f"public/private hash mismatch for {priv['id']}")
        return Instance(priv["id"], priv["category"], priv["task"], priv["family"], priv["source"], priv["params"],
                        pub, priv["private"], priv["contracts"], priv["tracks"], priv["hash"], priv["qbank_version"])


def inst_dir(category: str) -> Path:
    return data_root() / "instances" / category


def write_instances(category: str, instances: list[Instance], clean: bool = True) -> None:
    d = inst_dir(category)
    if clean and d.exists():
        import shutil
        shutil.rmtree(d)
    seen_hash: dict[str, str] = {}
    seen_id: set[str] = set()
    from .splits import DATA_VERSIONS
    for inst in instances:
        inst.qbank_version = DATA_VERSIONS.get(category, inst.qbank_version)
        if inst.id in seen_id:
            raise ValueError(f"duplicate id {inst.id}")
        if inst.hash in seen_hash:
            raise ValueError(f"duplicate content hash: {inst.id} and {seen_hash[inst.hash]}")
        seen_id.add(inst.id)
        seen_hash[inst.hash] = inst.id
        dump_json(inst.public_record(), d / "public" / f"{hash_hex(inst.hash)}.json")
        dump_json(inst.private_record(), d / "private" / f"{inst.id}.json")
    lines = [json.dumps({"id": i.id, "hash": i.hash, "family": i.family, "task": i.task,
                         "size_bin": i.private.get("size_bin"), "n": i.public.get("n", i.public.get("n_logical"))}, sort_keys=True)
             for i in sorted(instances, key=lambda x: x.id)]
    (d / "index.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_index(category: str) -> list[dict]:
    p = inst_dir(category) / "index.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_public(category: str, h: str) -> dict:
    return json.loads((inst_dir(category) / "public" / f"{hash_hex(h)}.json").read_text(encoding="utf-8"))


def load_private(category: str, iid: str) -> dict:
    return json.loads((inst_dir(category) / "private" / f"{iid}.json").read_text(encoding="utf-8"))


def load_instance(category: str, iid: str) -> Instance:
    priv = load_private(category, iid)
    return Instance.from_records(priv, load_public(category, priv["hash"]))


def iter_instances(category: str):
    for row in load_index(category):
        yield load_instance(category, row["id"])


def public_view(instance_or_public) -> dict:
    """What a candidate program may see: a deep copy of the public part (plus its opaque content hash)."""
    if isinstance(instance_or_public, Instance):
        return instance_or_public.public_record()
    rec = copy.deepcopy(instance_or_public)
    return rec
