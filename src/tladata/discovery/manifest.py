from typing import Any, Dict, Iterable
import json


def merge_records(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    if existing["repo"] != new["repo"]:
        raise ValueError(
            f"Repo mismatch: {existing['repo']} != {new['repo']}"
        )

    existing["query_hits"].extend(new["query_hits"])
    return existing


def write_jsonl(path: str, records: Iterable[Dict[str, Any]]) -> None:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
