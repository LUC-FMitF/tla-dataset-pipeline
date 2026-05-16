"""Command-line interface for tladata."""

import argparse
import os
import sys
from typing import TYPE_CHECKING

from tladata import __version__, configure_logging, get_logger
from tladata.config import LimitsConfig, load_env
from tladata.contracts.manifest_validator import ManifestValidationHandler
from tladata.discovery.github_client import GithubClient
from tladata.discovery.pipeline import (
    DiscoveryPipeline,
    ManifestValidator,
    SearchService,
    SeedFetcher,
)
from tladata.extraction.file_extraction_handler import FileExtractionHandler
from tladata.extraction.s3_upload_handler import S3UploadHandler
from tladata.parsing.parsing_handler import ParsingHandler

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def get_github_client(config: LimitsConfig) -> GithubClient:
    """Get authenticated GitHub client.

    Args:
        config: Application configuration with GitHub API limits

    Returns:
        Authenticated GitHub client

    Raises:
        ValueError: If GITHUB_TOKEN environment variable is not set
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    return GithubClient(token, config.github_api)


# Discovery subcommands


def discover(args: argparse.Namespace, config: LimitsConfig) -> int:
    """Run full discovery pipeline: seeds + search + write + validate."""
    try:
        client = get_github_client(config)
        pipeline = DiscoveryPipeline(client, args.output, args.schema, config.discovery)
        pipeline.run()
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


def search(args: argparse.Namespace, config: LimitsConfig) -> int:
    """Run search queries and write results."""
    try:
        client = get_github_client(config)
        service = SearchService(client, args.output, config.discovery)
        service.run()
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


def validate(args: argparse.Namespace, config: LimitsConfig) -> int:
    """Validate an existing manifest against a schema."""
    try:
        validator = ManifestValidator(args.manifest, args.schema)
        validator.validate()
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


def fetch_seeds(args: argparse.Namespace, config: LimitsConfig) -> int:
    """Fetch metadata for seeded repositories only."""
    try:
        client = get_github_client(config)
        fetcher = SeedFetcher(client, args.output, config.discovery)
        fetcher.run()
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


def validate_manifest(args: argparse.Namespace, config: LimitsConfig) -> int:
    """Validate a JSONL manifest file against a JSON schema."""
    try:
        handler = ManifestValidationHandler(config)
        return handler.handle(args)
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


# Extraction subcommands


def pull(args: argparse.Namespace, config: LimitsConfig) -> int:
    """Extract .tla, .cfg, and .tlaps files from discovered repositories."""
    try:
        client = get_github_client(config)
        handler = FileExtractionHandler(config, client)
        return handler.handle(args)
    except ValueError as e:
        logger.error(f"Error: {e}")
        return 1


def parse(args: argparse.Namespace, config: LimitsConfig) -> int:
    handler = ParsingHandler()
    return handler.handle(args)


def push_to_s3(args: argparse.Namespace, config: LimitsConfig) -> int:
    """Push extracted files to AWS S3."""
    handler = S3UploadHandler(config)
    return handler.handle(args)


# Main entry points


def main_discover() -> int:
    """Main entry point for discovery commands."""
    load_env()  # Load .env file if it exists (local development only)
    configure_logging(verbose=False)  # Setup logging infrastructure

    # Load configuration
    config = LimitsConfig.load()

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

    # parse
    parse_parser = subparsers.add_parser(
        "parse",
        help="Run LLM-based parsing on TLA+ files",
    )
    parse_parser.add_argument(
        "input",
        help="Path to a TLA+ file or directory of TLA+ files",
    )
    parse_parser.add_argument(
        "--output",
        default="data/parsed",
        help="Output directory for results (default: data/parsed)",
    )
    parse_parser.add_argument(
        "--model",
        default="gpt-4",
        help="Model spec: provider:model or bare model name (default: gpt-4). "
             "Examples: ollama:llama3, openai:gpt-4o, huggingface:mistralai/Mistral-7B-Instruct-v0.2",
    )
    parse_parser.add_argument(
        "--version",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Pipeline version to run (default: 3)",
    )
    parse_parser.add_argument(
        "--no-skip",
        dest="skip_existing",
        action="store_false",
        help="Re-process files even if results already exist",
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
    push_parser.add_argument(
        "--manifest-bucket",
        help="S3 bucket for manifest files (uses --bucket if not specified)",
    )
    push_parser.add_argument(
        "--manifest-prefix",
        help="S3 prefix/folder for manifests (default: manifests/sources)",
    )

    args = parser.parse_args()

    # Default to discover if no command specified
    if not args.command:
        args.command = "discover"

    # Command dispatch table
    _handlers = {
        "discover": discover,
        "search": search,
        "validate": validate,
        "fetch-seeds": fetch_seeds,
        "pull": pull,
        "parse": parse,
        "push-to-s3": push_to_s3,
    }

    handler = _handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args, config)


def main_validate() -> int:
    """Main entry point for manifest validation."""
    load_env()  # Load .env file if it exists (local development only)
    configure_logging(verbose=False)  # Setup logging infrastructure

    # Load configuration
    config = LimitsConfig.load()

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
    return validate_manifest(args, config)


if __name__ == "__main__":
    sys.exit(main_discover())
