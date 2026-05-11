"""Configuration management for TLA dataset pipeline.

This module provides typed configuration classes using dataclasses and YAML loading,
replacing the legacy singleton pattern with dependency injection support.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def load_env() -> None:
    """Load environment variables from .env file if present."""
    try:
        from dotenv import load_dotenv

        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        # python-dotenv not installed (CI/CD environment) - this is expected
        pass


@dataclass
class GitHubAPILimits:
    """GitHub API configuration limits.
    
    Attributes:
        request_timeout: Request timeout in seconds
        per_page: Items per page in paginated requests
        max_retries: Maximum retry attempts on transient failures
        retry_delay: Delay in seconds between retries
    """

    request_timeout: int = 30
    per_page: int = 50
    max_retries: int = 3
    retry_delay: int = 1


@dataclass
class DiscoveryLimits:
    """Discovery operation configuration limits.
    
    Attributes:
        max_repositories: Maximum repositories to process
        max_results_per_query: Maximum results per search query
        call_delay: Delay between API calls in seconds
    """

    max_repositories: int = 5000
    max_results_per_query: int = 100
    call_delay: float = 0.1


@dataclass
class ExtractionLimits:
    """File extraction configuration limits.
    
    Attributes:
        file_download_timeout: Timeout per file download in seconds
        max_file_size: Maximum single file size in bytes
        max_files_per_repo: Maximum files to extract per repository
        max_concurrent_repos: Maximum concurrent repository extractions
    """

    file_download_timeout: int = 30
    max_file_size: int = 10485760  # 10 MB
    max_files_per_repo: int = 1000
    max_concurrent_repos: int = 5


@dataclass
class UploadLimits:
    """S3 upload configuration limits.
    
    Attributes:
        batch_size: Files per upload batch
        s3_timeout: S3 operation timeout in seconds
        max_concurrent_uploads: Maximum concurrent upload operations
    """

    batch_size: int = 100
    s3_timeout: int = 60
    max_concurrent_uploads: int = 10


@dataclass
class ValidationLimits:
    """Validation configuration limits.
    
    Attributes:
        max_validation_errors: Maximum errors to report during validation
    """

    max_validation_errors: int = 100


@dataclass
class LimitsConfig:
    """Complete configuration for the TLA dataset pipeline.
    
    This dataclass aggregates all limit/config sections and provides
    a single point of configuration access with full type safety.
    
    Attributes:
        github_api: GitHub API rate and timeout limits
        discovery: Repository discovery limits
        extraction: File extraction limits
        upload: S3 upload limits
        validation: Validation limits
    """

    github_api: GitHubAPILimits
    discovery: DiscoveryLimits
    extraction: ExtractionLimits
    upload: UploadLimits
    validation: ValidationLimits

    @classmethod
    def load(cls, path: str | None = None) -> "LimitsConfig":
        """Load configuration from YAML file.
        
        Args:
            path: Path to limits.yaml file. Defaults to config/runtime/limits.yaml
        
        Returns:
            Configured LimitsConfig instance
            
        Raises:
            FileNotFoundError: If config file not found
            yaml.YAMLError: If YAML parsing fails
        """
        if path is None:
            path = "config/runtime/limits.yaml"
        
        config_path = Path(path)
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        
        # Extract sections with defaults
        github_api_data = data.get("github_api", {})
        discovery_data = data.get("discovery", {})
        extraction_data = data.get("extraction", {})
        upload_data = data.get("upload", {})
        validation_data = data.get("validation", {})
        
        return cls(
            github_api=GitHubAPILimits(**github_api_data),
            discovery=DiscoveryLimits(**discovery_data),
            extraction=ExtractionLimits(**extraction_data),
            upload=UploadLimits(**upload_data),
            validation=ValidationLimits(**validation_data),
        )
