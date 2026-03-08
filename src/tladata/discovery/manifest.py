import json
from collections.abc import Iterable
from typing import Any


def merge_records(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    if existing["repo"] != new["repo"]:
        raise ValueError(f"Repo mismatch: {existing['repo']} != {new['repo']}")

    existing["query_hits"].extend(new["query_hits"])
    return existing


def write_jsonl(path: str, records: Iterable[dict[str, Any]]) -> None:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
