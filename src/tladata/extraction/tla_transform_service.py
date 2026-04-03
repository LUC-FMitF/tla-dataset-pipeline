"""TLA+ transformation service for batch processing extracted files."""

import json
from pathlib import Path
from typing import Any

from tladata.extraction.extraction_manifest import load_extraction_manifest
from tladata.transform.json import TlaTransformer


class TlaTransformationService:
    """Service for transforming extracted TLA+ files into feature-annotated JSON."""

    def __init__(self, base_paths: list[str] | None = None):
        """
        Initialize transformation service.

        Args:
            base_paths: Optional list of base paths for file search (local only)
        """
        self.transformer = TlaTransformer(base_paths or [])

    def transform_from_local_extraction(
        self,
        extraction_manifest: str,
        extracted_files_root: str,
        output_fine: str,
        output_coarse: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Transform extracted TLA+ files from local extraction manifest.

        This is the PRIMARY transformation method for the pipeline.
        It takes the extraction manifest (created after FileExtractor) and transforms
        all extracted files into labeled feature datasets.

        Args:
            extraction_manifest: Path to extraction_manifest.jsonl (created by generate_extraction_manifest)
            extracted_files_root: Root directory containing extracted files (e.g., data/raw)
            output_fine: Output path for fine-grained features JSON
            output_coarse: Output path for coarse-grained features JSON

        Returns:
            Tuple of (fine_records, coarse_records)

        Example:
            service = TlaTransformationService()
            service.transform_from_local_extraction(
                extraction_manifest="manifests/extraction/extraction_manifest.jsonl",
                extracted_files_root="data/raw",
                output_fine="data/processed/tla-components-fine.json",
                output_coarse="data/processed/tla-components-coarse.json"
            )
        """
        extracted_root = Path(extracted_files_root)
        if not extracted_root.exists():
            raise ValueError(f"Extracted files root not found: {extracted_files_root}")

        specs = []
        total_files = 0
        errors = []

        # Process each repository in extraction manifest
        for repo_record in load_extraction_manifest(extraction_manifest):
            repo = repo_record["repo"]
            repo_dir = extracted_root / repo

            if not repo_dir.exists():
                errors.append(f"Repository directory not found: {repo_dir}")
                continue

            # Process each .tla file in this repo
            for tla_file_info in repo_record.get("tla_files", []):
                tla_rel_path = tla_file_info["path"]
                tla_full_path = repo_dir / tla_rel_path

                if not tla_full_path.exists():
                    errors.append(f"TLA file not found: {tla_full_path}")
                    continue

                # Try to find corresponding .cfg file
                cfg_path = tla_full_path.with_suffix(".cfg")
                cfg_full_path = None
                if cfg_path.exists():
                    cfg_full_path = cfg_path

                # Also check for .cfg files listed in manifest
                cfg_full_path = None
                for cfg_info in repo_record.get("cfg_files", []):
                    cfg_rel_path = cfg_info["path"]
                    potential_cfg = repo_dir / cfg_rel_path
                    if potential_cfg.exists() and (
                        potential_cfg.name == tla_file_info["path"].replace(".tla", ".cfg")
                        or cfg_rel_path.replace(".cfg", "") == tla_rel_path.replace(".tla", "")
                    ):
                        cfg_full_path = potential_cfg
                        break

                # Create spec entry for this file
                spec = {
                    "repo": repo,
                    "model": tla_full_path.stem,
                    "file_path": tla_rel_path,
                    "tla_clean": str(tla_full_path),
                    "tla_original": str(tla_full_path),
                    "cfg": str(cfg_full_path) if cfg_full_path else None,
                }
                specs.append(spec)
                total_files += 1

        print(f"Loaded {total_files} TLA+ files from {len(specs)} specifications")
        if errors:
            print("Warnings during extraction manifest processing:")
            for error in errors[:10]:
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")

        # Transform all specs
        print(f"Transforming {len(specs)} specifications...")
        fine_out, coarse_out = self.transformer.transform(
            specs,
            output_fine=output_fine,
            output_coarse=output_coarse,
            base_paths=[str(extracted_root)],
        )

        # Create transformation manifest linking specs to source repos
        self._create_transformation_manifest(
            fine_out, "data/processed/transformation_manifest.jsonl"
        )

        print(
            f"Transformation complete: {len(fine_out)} fine-grained, {len(coarse_out)} coarse-grained records"
        )
        print(f"Fine-grained output:  {output_fine}")
        print(f"Coarse-grained output: {output_coarse}")

        return fine_out, coarse_out

    def _create_transformation_manifest(
        self, records: list[dict[str, Any]], output_path: str
    ) -> None:
        """Create transformation manifest linking specs to source repos."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                manifest_record = {
                    "id": record["id"],
                    "specification": record["Specification"],
                    "repo": record.get("repo", "unknown"),
                }
                f.write(json.dumps(manifest_record) + "\n")
        print(f"Transformation manifest: {output_path}")

    # Legacy methods for backward compatibility
    def transform_from_directory(
        self,
        tla_dir: str,
        output_fine: str,
        output_coarse: str,
        recursive: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Transform all TLA+ files in a directory (legacy method).

        DEPRECATED: Use transform_from_local_extraction() with extraction manifest instead.
        This method is kept for backward compatibility.

        Args:
            tla_dir: Directory containing extracted TLA+ files
            output_fine: Output path for fine-grained features JSON
            output_coarse: Output path for coarse-grained features JSON
            recursive: Whether to search recursively for .tla files

        Returns:
            Tuple of (fine_records, coarse_records)
        """
        tla_dir_path = Path(tla_dir)
        if not tla_dir_path.exists():
            raise ValueError(f"Directory not found: {tla_dir}")

        # Find all TLA files
        pattern = "**/*.tla" if recursive else "*.tla"
        tla_files = list(tla_dir_path.glob(pattern))

        if not tla_files:
            print(f"Warning: No .tla files found in {tla_dir}")

        print(f"Found {len(tla_files)} TLA+ files to process")

        # Build spec entries from files
        specs = []
        for idx, tla_file in enumerate(tla_files):
            spec_name = tla_file.stem
            cfg_file = tla_file.with_suffix(".cfg")

            spec = {
                "model": str(spec_name),
                "tla_clean": str(tla_file),
                "tla_original": str(tla_file),
                "cfg": str(cfg_file) if cfg_file.exists() else None,
            }
            specs.append(spec)

        print(f"Processing {len(specs)} specifications...")
        fine_out, coarse_out = self.transformer.transform(
            specs,
            output_fine=output_fine,
            output_coarse=output_coarse,
            base_paths=[str(tla_dir_path)],
        )

        print(
            f"Transformation complete: {len(fine_out)} fine-grained, {len(coarse_out)} coarse-grained records"
        )
        print(f"Fine-grained output:  {output_fine}")
        print(f"Coarse-grained output: {output_coarse}")

        return fine_out, coarse_out

    def transform_from_manifest(
        self,
        manifest_jsonl: str,
        output_fine: str,
        output_coarse: str,
        base_paths: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Transform specs defined in a custom manifest (legacy method).

        DEPRECATED: Use transform_from_local_extraction() instead.
        This method is kept for backward compatibility.

        Args:
            manifest_jsonl: Path to JSONL file with spec entries
            output_fine: Output path for fine-grained features JSON
            output_coarse: Output path for coarse-grained features JSON
            base_paths: Optional list of base paths for file search

        Returns:
            Tuple of (fine_records, coarse_records)
        """
        manifest_path = Path(manifest_jsonl)
        if not manifest_path.exists():
            raise ValueError(f"Manifest not found: {manifest_jsonl}")

        # Load specs from manifest
        specs = []
        with open(manifest_jsonl) as f:
            for line in f:
                if line.strip():
                    specs.append(json.loads(line))

        print(f"Loaded {len(specs)} specifications from manifest: {manifest_jsonl}")

        # Add base path if not provided
        if not base_paths:
            base_paths = [str(manifest_path.parent)]

        print(f"Processing {len(specs)} specifications with base paths: {base_paths}")
        fine_out, coarse_out = self.transformer.transform(
            specs, output_fine=output_fine, output_coarse=output_coarse, base_paths=base_paths
        )

        print(
            f"Transformation complete: {len(fine_out)} fine-grained, {len(coarse_out)} coarse-grained records"
        )
        print(f"Fine-grained output:  {output_fine}")
        print(f"Coarse-grained output: {output_coarse}")

        return fine_out, coarse_out
