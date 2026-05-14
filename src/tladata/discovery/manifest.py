import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from tladata.logging import get_logger

logger = get_logger(__name__)


def merge_records(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge two repository metadata records, combining query_hits.

    Args:
        existing: Existing repository metadata
        new: New repository metadata to merge

    Returns:
        Merged metadata record

    Raises:
        ValueError: If repositories don't match
    """
    if existing["repo"] != new["repo"]:
        raise ValueError(f"Repo mismatch: {existing['repo']} != {new['repo']}")

    existing["query_hits"].extend(new["query_hits"])
    return existing


def write_jsonl(path: str, records: Iterable[dict[str, Any]]) -> None:
    """Write JSONL file and create a pretty-printed version.

    Args:
        path: Output path for JSONL file
        records: Iterable of records to write
    """
    # Create parent directories if they don't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    # Create pretty-printed version for human readability
    formatted_path = Path(path).with_stem(Path(path).stem + "_formatted")
    try:
        with open(path) as f:
            data = [json.loads(line) for line in f if line.strip()]

        with open(formatted_path, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)

        logger.debug(f"Created formatted version: {formatted_path}")
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Could not create formatted version: {e}")
