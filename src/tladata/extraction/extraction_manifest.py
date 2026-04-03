"""Extract and track metadata about which TLA+ files were extracted from each repository."""

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any


def generate_extraction_manifest(
    extracted_files_root: str, output_manifest: str, verbose: bool = False
) -> dict[str, Any]:
    """
    Scan extracted files directory and generate manifest.

    Assumes structure: extracted_files_root/<repo>/<subdirs>/*.tla

    Args:
        extracted_files_root: Path to data/raw or equivalent
        output_manifest: Path to write extraction_manifest.jsonl
        verbose: Print details during processing

    Returns:
        Dictionary with extraction statistics
    """
    root_path = Path(extracted_files_root)

    if not root_path.exists():
        raise ValueError(f"Directory not found: {extracted_files_root}")

    manifest_records: list[dict[str, Any]] = []
    stats: dict[str, Any] = {"total_repos": 0, "total_files": 0, "errors": []}

    # repos are stored as <owner>/<name> directories
    for repo_dir in root_path.iterdir():
        if not repo_dir.is_dir():
            continue

        # Extract repo name from directory structure
        # e.g., if path is data/raw/tlaplus/tlaplus, repo = "tlaplus/tlaplus"
        # We need to reconstruct this from the directory name
        parts: list[str] = []
        current = repo_dir
        while current != root_path and current != root_path.parent:
            parts.insert(0, current.name)
            current = current.parent
        repo_name = "/".join(parts) if len(parts) >= 2 else repo_dir.name

        tla_files = []
        cfg_files = []
        other_files = []

        # Find all files in this repo
        for file_path in repo_dir.rglob("*"):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(repo_dir))
                file_info = {
                    "path": relative_path,
                    "size": file_path.stat().st_size,
                }

                if file_path.suffix == ".tla":
                    tla_files.append(file_info)
                elif file_path.suffix == ".cfg":
                    cfg_files.append(file_info)
                else:
                    other_files.append(file_info)

        if tla_files or cfg_files:
            record = {
                "repo": repo_name,
                "tla_files": tla_files,
                "cfg_files": cfg_files,
                "total_tla": len(tla_files),
                "total_cfg": len(cfg_files),
                "total_files": len(tla_files) + len(cfg_files),
            }

            manifest_records.append(record)
            stats["total_repos"] += 1
            stats["total_files"] += record["total_files"]

            if verbose:
                print(f"  {repo_name}: {len(tla_files)} .tla, {len(cfg_files)} .cfg")

    # Write manifest
    Path(output_manifest).parent.mkdir(parents=True, exist_ok=True)
    with open(output_manifest, "w", encoding="utf-8") as f:
        for record in manifest_records:
            f.write(json.dumps(record) + "\n")

    print(f"\nExtraction manifest: {output_manifest}")
    print(f"  Repositories: {stats['total_repos']}")
    print(f"  Total files: {stats['total_files']}")

    return stats


def load_extraction_manifest(manifest_path: str) -> Generator[dict[str, Any], None, None]:
    """Load and yield extraction manifest records."""
    with open(manifest_path) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def add_s3_paths_to_manifest(
    extraction_manifest: str,
    output_s3_manifest: str,
    s3_bucket: str,
    s3_prefix: str,
) -> None:
    """
    Convert extraction manifest to S3 manifest with s3:// URIs.

    Args:
        extraction_manifest: Input extraction_manifest.jsonl
        output_s3_manifest: Output S3 manifest with URI references
        s3_bucket: S3 bucket name
        s3_prefix: S3 prefix/folder where files were uploaded
    """
    s3_records = []
    base_uri = f"s3://{s3_bucket}/{s3_prefix}".rstrip("/")

    for record in load_extraction_manifest(extraction_manifest):
        repo = record["repo"]
        repo_prefix = f"{base_uri}/{repo}"

        s3_record = {
            "repo": repo,
            "s3_prefix": repo_prefix,
            "tla_files": [
                {"path": f["path"], "s3_uri": f"{repo_prefix}/{f['path']}"}
                for f in record["tla_files"]
            ],
            "cfg_files": [
                {"path": f["path"], "s3_uri": f"{repo_prefix}/{f['path']}"}
                for f in record["cfg_files"]
            ],
            "total_tla": record["total_tla"],
            "total_cfg": record["total_cfg"],
        }
        s3_records.append(s3_record)

    # Write S3 manifest
    Path(output_s3_manifest).parent.mkdir(parents=True, exist_ok=True)
    with open(output_s3_manifest, "w", encoding="utf-8") as f:
        for record in s3_records:
            f.write(json.dumps(record) + "\n")

    print(f"S3 manifest: {output_s3_manifest} ({len(s3_records)} repos)")
