"""Upload files to AWS S3."""

from pathlib import Path
from typing import Any

try:
    import boto3  # type: ignore[import-not-found, import-untyped]

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


class S3Uploader:
    """Upload extracted TLA+ files to AWS S3."""

    def __init__(self, bucket: str, prefix: str = "raw", region: str = "us-east-2"):
        """
        Initialize S3 uploader.

        Args:
            bucket: S3 bucket name
            prefix: S3 prefix/folder within bucket
            region: AWS region
        """
        if not HAS_BOTO3:
            raise ImportError("boto3 is required for S3 upload. Install with: pip install boto3")

        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        self.s3_client = boto3.client("s3", region_name=region)  # type: ignore[attr-defined]

    def upload_directory(self, local_dir: str, dry_run: bool = False) -> dict[str, Any]:
        """
        Upload directory of extracted files to S3.

        Args:
            local_dir: Local directory containing extracted files
            dry_run: If True, only log what would be uploaded without uploading

        Returns:
            Dictionary with upload statistics
        """
        local_path = Path(local_dir)
        if not local_path.is_dir():
            raise ValueError(f"Directory not found: {local_dir}")

        stats: dict[str, Any] = {
            "total_files": 0,
            "uploaded_files": 0,
            "skipped_files": 0,
            "errors": [],
        }

        for file_path in local_path.rglob("*"):
            if file_path.is_file():
                stats["total_files"] += 1
                try:
                    self._upload_file(file_path, local_path, dry_run, stats)
                except Exception as e:
                    stats["errors"].append(str(e))
                    stats["skipped_files"] += 1

        return stats

    def _upload_file(
        self, file_path: Path, base_path: Path, dry_run: bool, stats: dict[str, Any]
    ) -> None:
        """Upload a single file to S3."""
        # Compute S3 key as prefix + relative path
        relative_path = file_path.relative_to(base_path)
        s3_key = f"{self.prefix}/{relative_path}".replace("\\", "/")

        if dry_run:
            print(f"[DRY RUN] Would upload: {file_path} -> s3://{self.bucket}/{s3_key}")
        else:
            print(f"Uploading: {relative_path} ...")
            self.s3_client.upload_file(str(file_path), self.bucket, s3_key)
            stats["uploaded_files"] += 1

    def upload_file(self, local_file: str, s3_key: str, dry_run: bool = False) -> None:
        """
        Upload single file to S3.

        Args:
            local_file: Path to local file
            s3_key: S3 key (without bucket name)
            dry_run: If True, only log without uploading
        """
        local_path = Path(local_file)
        if not local_path.is_file():
            raise ValueError(f"File not found: {local_file}")

        full_key = f"{self.prefix}/{s3_key}".lstrip("/")

        if dry_run:
            print(f"[DRY RUN] Would upload: {local_file} -> s3://{self.bucket}/{full_key}")
        else:
            print(f"Uploading: {local_file} -> s3://{self.bucket}/{full_key}")
            self.s3_client.upload_file(local_file, self.bucket, full_key)

    @staticmethod
    def get_s3_config_from_dvc(dvc_config_path: str) -> dict | None:
        """
        Parse S3 configuration from .dvc/config file.

        Returns:
            Dictionary with bucket, prefix, region if found, None otherwise
        """
        import configparser

        config = configparser.ConfigParser()
        config.read(dvc_config_path)

        if "remote" in config and "s3remote" in [
            s.split('"')[1] for s in config.sections() if s.startswith("'remote")
        ]:
            # Try alternate pattern
            for section in config.sections():
                if "remote" in section and "s3remote" in section:
                    url = config.get(section, "url", fallback=None)
                    if url and url.startswith("s3://"):
                        parts = url.replace("s3://", "").split("/", 1)
                        return {
                            "bucket": parts[0],
                            "prefix": parts[1] if len(parts) > 1 else "",
                            "region": config.get(section, "region", fallback="us-east-2"),
                        }
        return None
