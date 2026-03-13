import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def merge_records(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    if existing["repo"] != new["repo"]:
        raise ValueError(f"Repo mismatch: {existing['repo']} != {new['repo']}")

    existing["query_hits"].extend(new["query_hits"])
    return existing


def write_jsonl(path: str, records: Iterable[dict[str, Any]]) -> None:
    """Write JSONL file and create a pretty-printed version."""
    # Create parent directories if they don't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    # Create pretty-printed version for human readability
    formatted_path = Path(path).with_stem(Path(path).stem + "_formatted")
    try:
        subprocess.run(
            f"jq '.' {path} > {formatted_path}",
            shell=True,
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # jq not available, skip pretty-printing
        pass
