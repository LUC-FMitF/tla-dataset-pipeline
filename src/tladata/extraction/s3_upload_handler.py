"""Handler for uploading extracted files to AWS S3."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

from tladata.cli_handler import CLIHandler
from tladata.config import LimitsConfig
from tladata.contracts.types import UploadStats
from tladata.extraction.s3_uploader import S3Uploader

if TYPE_CHECKING:
    import argparse


class S3UploadHandler(CLIHandler):
    """Handle S3 upload operations with configuration resolution."""

    def __init__(self, config: LimitsConfig) -> None:
        """Initialize the S3 upload handler.

        Args:
            config: Application configuration with limits
        """
        super().__init__()
        self.config = config

    def handle(self, args: "argparse.Namespace") -> int:
        """Upload extracted files to S3 with manifest files.

        Args:
            args: Arguments with input, bucket, prefix, region, dry_run, etc.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            self.logger.info("Starting S3 upload")

            # Try to get S3 config from DVC config
            dvc_config_path = Path(".dvc/config")
            s3_config = None

            if dvc_config_path.exists():
                s3_config = S3Uploader.get_s3_config_from_dvc(str(dvc_config_path))

            # Try multiple sources for bucket: args, DVC config, environment variable
            bucket = (
                args.bucket
                or (s3_config.get("bucket") if s3_config else None)
                or os.environ.get("S3_BUCKET")
            )
            prefix = args.prefix or (s3_config.get("prefix") if s3_config else "raw")
            region = args.region or (s3_config.get("region") if s3_config else "us-east-2")

            if not bucket:
                raise ValueError(
                    "Bucket not specified. Use --bucket, S3_BUCKET env var, or configure in .dvc/config"
                )

            uploader = S3Uploader(cast(str, bucket), cast(str, prefix), cast(str, region))

            # Upload extracted files from data/raw
            stats: UploadStats = uploader.upload_directory(args.input, dry_run=args.dry_run)

            # Also upload manifest files (possibly to different bucket/prefix)
            manifest_dir = Path("manifests/sources")
            if manifest_dir.exists():
                self.logger.info("Uploading manifests...")
                # Use separate bucket/prefix for manifests if specified
                manifest_bucket = args.manifest_bucket or bucket
                manifest_prefix = args.manifest_prefix or "manifests/sources"
                manifest_uploader = S3Uploader(
                    cast(str, manifest_bucket), cast(str, manifest_prefix), cast(str, region)
                )
                manifest_stats = manifest_uploader.upload_directory(
                    str(manifest_dir), dry_run=args.dry_run
                )
                # Combine statistics
                stats["total_files"] += manifest_stats["total_files"]
                stats["uploaded_files"] += manifest_stats["uploaded_files"]
                stats["skipped_files"] += manifest_stats["skipped_files"]
                stats["errors"].extend(manifest_stats["errors"])

            self._log_stats(stats)
            return 0
        except Exception as e:
            self.logger.error(f"Error during S3 upload: {e}")
            return 1

    def _log_stats(self, stats: UploadStats) -> None:
        """Log upload statistics.

        Args:
            stats: Upload statistics
        """
        self.logger.info("Upload Statistics:")
        self.logger.info(f"  Total files: {stats['total_files']}")
        self.logger.info(f"  Uploaded: {stats['uploaded_files']}")
        self.logger.info(f"  Skipped: {stats['skipped_files']}")
        if stats["errors"]:
            self.logger.error(f"  Errors: {len(stats['errors'])}")
            for error in stats["errors"][:5]:
                self.logger.error(f"    - {error}")
