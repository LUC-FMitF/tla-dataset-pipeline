"""Command-line interface for tladata."""

import argparse
import os
import sys
from pathlib import Path
from typing import cast

from tladata import __version__
from tladata.contracts.validate import validate_jsonl
from tladata.discovery.github_client import GithubClient
from tladata.discovery.pipeline import (
    DiscoveryPipeline,
    ManifestValidator,
    SearchService,
    SeedFetcher,
)
from tladata.extraction.file_extractor import FileExtractor
from tladata.extraction.s3_uploader import S3Uploader
from tladata.utils.load_limits import load_limits


def get_github_client() -> GithubClient:
    """Get authenticated GitHub client."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    return GithubClient(token)


# Discovery subcommands


def discover(args: argparse.Namespace) -> int:
    """Run full discovery pipeline: seeds + search + write + validate."""
    try:
        client = get_github_client()
        pipeline = DiscoveryPipeline(client, args.output, args.schema)
        pipeline.run()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def search(args: argparse.Namespace) -> int:
    """Run search queries and write results."""
    try:
        client = get_github_client()
        service = SearchService(client, args.output)
        service.run()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def validate(args: argparse.Namespace) -> int:
    """Validate an existing manifest against a schema."""
    try:
        validator = ManifestValidator(args.manifest, args.schema)
        validator.validate()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def fetch_seeds(args: argparse.Namespace) -> int:
    """Fetch metadata for seeded repositories only."""
    try:
        client = get_github_client()
        fetcher = SeedFetcher(client, args.output)
        fetcher.run()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def validate_manifest(args: argparse.Namespace) -> int:
    """Validate a JSONL manifest file against a JSON schema."""
    # Convert to absolute paths if relative
    manifest_path = Path(args.manifest)
    schema_path = Path(args.schema)

    if not manifest_path.is_absolute():
        manifest_path = Path.cwd() / manifest_path
    if not schema_path.is_absolute():
        schema_path = Path.cwd() / schema_path

    print(f"Validating manifest: {manifest_path}")
    print(f"Schema: {schema_path}\n")

    success, errors = validate_jsonl(str(manifest_path), str(schema_path))

    if success:
        print("Validation passed!")
        return 0
    else:
        limits = load_limits()
        max_errors_display = limits.get("validation", "max_validation_errors", 50)

        print(f"Validation failed with {len(errors)} error(s):\n")
        if args.verbose or len(errors) <= max_errors_display:
            for error in errors:
                print(f"  {error}")
        else:
            # Show first N errors and summary
            for error in errors[:max_errors_display]:
                print(f"  {error}")
            print(f"\n  ... and {len(errors) - max_errors_display} more errors")
            print("\nRun with -v/--verbose to see all errors")

        return 1


# Extraction subcommands


def pull(args: argparse.Namespace) -> int:
    """Extract .tla, .cfg, and .tlaps files from discovered repositories."""
    try:
        client = get_github_client()
        extractor = FileExtractor(client)
        extractor.extract_files(args.manifest, args.output)
        print(f"\nFiles extracted to: {args.output}")
        return 0
    except Exception as e:
        print(f"Error during extraction: {e}", file=sys.stderr)
        return 1


def push_to_s3(args: argparse.Namespace) -> int:
    """Push extracted files to AWS S3."""
    try:
        # Try to get S3 config from DVC config
        dvc_config_path = Path(".dvc/config")
        s3_config = None

        if dvc_config_path.exists():
            s3_config = S3Uploader.get_s3_config_from_dvc(str(dvc_config_path))

        bucket = args.bucket or (s3_config.get("bucket") if s3_config else None)
        prefix = args.prefix or (s3_config.get("prefix") if s3_config else "raw")
        region = args.region or (s3_config.get("region") if s3_config else "us-east-2")

        if not bucket:
            raise ValueError(
                "Bucket not specified. Use --bucket or configure in .dvc/config"
            )

        uploader = S3Uploader(cast(str, bucket), cast(str, prefix), cast(str, region))
        stats = uploader.upload_directory(args.input, dry_run=args.dry_run)

        print("\nUpload Statistics:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Uploaded: {stats['uploaded_files']}")
        print(f"  Skipped: {stats['skipped_files']}")
        if stats["errors"]:
            print(f"  Errors: {len(stats['errors'])}")
            for error in stats["errors"][:5]:
                print(f"    - {error}")

        return 0
    except Exception as e:
        print(f"Error during S3 upload: {e}", file=sys.stderr)
        return 1


# Main entry points


def main_discover() -> int:
    """Main entry point for discovery commands."""
    parser = argparse.ArgumentParser(description="TLA Dataset Discovery Pipeline", prog="tladata")

    # Global arguments
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--output",
        default="manifests/sources/sources_latest.jsonl",
        help="Output path for JSONL manifest (default: manifests/sources/sources_latest.jsonl)",
    )
    parser.add_argument(
        "--schema",
        default="data_contracts/schemas/source_record.schema.json",
        help="Path to validation schema (default: data_contracts/schemas/source_record.schema.json)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # discover
    subparsers.add_parser(
        "discover",
        help="Run full discovery pipeline (seeds + search + write + validate)",
    )

    # search
    subparsers.add_parser(
        "search",
        help="Run search queries and write results",
    )

    # validate
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a manifest against a schema",
    )
    validate_parser.add_argument(
        "manifest",
        help="Path to manifest to validate",
    )

    # fetch-seeds
    subparsers.add_parser(
        "fetch-seeds",
        help="Fetch metadata for seeded repositories only",
    )

    # pull
    pull_parser = subparsers.add_parser(
        "pull",
        help="Extract .tla, .cfg, and .tlaps files from discovered repositories",
    )
    pull_parser.add_argument(
        "--manifest",
        default="manifests/sources/sources_latest.jsonl",
        help="Path to manifest file (default: manifests/sources/sources_latest.jsonl)",
    )
    pull_parser.add_argument(
        "--output",
        default="data/raw",
        help="Output directory for extracted files (default: data/raw)",
    )

    # push-to-s3
    push_parser = subparsers.add_parser(
        "push-to-s3",
        help="Push extracted files to AWS S3 storage",
    )
    push_parser.add_argument(
        "--input",
        default="data/raw",
        help="Input directory with files to push (default: data/raw)",
    )
    push_parser.add_argument(
        "--bucket",
        help="S3 bucket name (uses .dvc/config if not specified)",
    )
    push_parser.add_argument(
        "--prefix",
        help="S3 prefix/folder (default: raw)",
    )
    push_parser.add_argument(
        "--region",
        help="AWS region (default: us-east-2)",
    )
    push_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading",
    )

    args = parser.parse_args()

    # Default to discover if no command specified
    if not args.command:
        args.command = "discover"

    if args.command == "discover":
        return discover(args)
    elif args.command == "search":
        return search(args)
    elif args.command == "validate":
        return validate(args)
    elif args.command == "fetch-seeds":
        return fetch_seeds(args)
    elif args.command == "pull":
        return pull(args)
    elif args.command == "push-to-s3":
        return push_to_s3(args)
    else:
        parser.print_help()
        return 1


def main_validate() -> int:
    """Main entry point for manifest validation."""
    parser = argparse.ArgumentParser(
        description="Validate a JSONL manifest file against a JSON schema"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        default="manifests/sources/sources_latest.jsonl",
        help="Path to the JSONL manifest file (default: manifests/sources/sources_latest.jsonl)",
    )
    parser.add_argument(
        "--schema",
        default="data_contracts/schemas/source_record.schema.json",
        help="Path to the JSON schema file (default: data_contracts/schemas/source_record.schema.json)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print all validation errors (not just summary)",
    )

    args = parser.parse_args()
    return validate_manifest(args)


if __name__ == "__main__":
    sys.exit(main_discover())
