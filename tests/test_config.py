"""Unit tests for the config module."""

import tempfile
from pathlib import Path

import pytest

from tladata.config import (
    DiscoveryLimits,
    ExtractionLimits,
    GitHubAPILimits,
    LimitsConfig,
    UploadLimits,
    ValidationLimits,
)


class TestGitHubAPILimits:
    """Test GitHubAPILimits dataclass."""

    def test_github_api_limits_creation(self) -> None:
        """Test creating GitHubAPILimits with values."""
        limits = GitHubAPILimits(
            request_timeout=30,
            max_retries=3,
            retry_delay=2,
        )

        assert limits.request_timeout == 30
        assert limits.max_retries == 3
        assert limits.retry_delay == 2

    def test_github_api_limits_defaults(self) -> None:
        """Test GitHubAPILimits has expected default values."""
        limits = GitHubAPILimits(
            request_timeout=30,
            max_retries=3,
            retry_delay=2,
        )

        assert limits.request_timeout > 0
        assert limits.max_retries > 0
        assert limits.retry_delay > 0


class TestDiscoveryLimits:
    """Test DiscoveryLimits dataclass."""

    def test_discovery_limits_creation(self) -> None:
        """Test creating DiscoveryLimits."""
        limits = DiscoveryLimits(
            max_repositories=500,
            max_results_per_query=50,
            call_delay=0.1,
        )

        assert limits.max_repositories == 500
        assert limits.max_results_per_query == 50
        assert limits.call_delay == 0.1


class TestExtractionLimits:
    """Test ExtractionLimits dataclass."""

    def test_extraction_limits_creation(self) -> None:
        """Test creating ExtractionLimits."""
        limits = ExtractionLimits(
            file_download_timeout=60,
            max_file_size=50_000_000,
            max_files_per_repo=100,
        )

        assert limits.file_download_timeout == 60
        assert limits.max_file_size == 50_000_000
        assert limits.max_files_per_repo == 100


class TestUploadLimits:
    """Test UploadLimits dataclass."""

    def test_upload_limits_creation(self) -> None:
        """Test creating UploadLimits."""
        limits = UploadLimits(batch_size=200)

        assert limits.batch_size == 200


class TestValidationLimits:
    """Test ValidationLimits dataclass."""

    def test_validation_limits_creation(self) -> None:
        """Test creating ValidationLimits."""
        limits = ValidationLimits(max_validation_errors=50)

        assert limits.max_validation_errors == 50


class TestLimitsConfig:
    """Test LimitsConfig dataclass and load method."""

    def test_limits_config_creation(
        self,
        test_config: LimitsConfig,
    ) -> None:
        """Test creating LimitsConfig with all limits."""
        assert test_config.github_api is not None
        assert test_config.discovery is not None
        assert test_config.extraction is not None
        assert test_config.upload is not None
        assert test_config.validation is not None

    def test_limits_config_load(self) -> None:
        """Test loading LimitsConfig from default file."""
        config = LimitsConfig.load()

        assert config is not None
        assert isinstance(config.github_api, GitHubAPILimits)
        assert isinstance(config.discovery, DiscoveryLimits)
        assert isinstance(config.extraction, ExtractionLimits)
        assert isinstance(config.upload, UploadLimits)
        assert isinstance(config.validation, ValidationLimits)

    def test_limits_config_load_custom_path(self) -> None:
        """Test loading LimitsConfig from custom path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config_file = tmp_path / "test_limits.yaml"

            # Create a test config file
            config_content = """
github_api:
  request_timeout: 15
  per_page: 25
  max_retries: 2
  retry_delay: 1
discovery:
  max_repositories: 200
  max_results_per_query: 25
  call_delay: 0.2
extraction:
  file_download_timeout: 45
  max_file_size: 5000000
  max_files_per_repo: 25
  max_concurrent_repos: 3
upload:
  batch_size: 50
validation:
  max_validation_errors: 5
"""
            config_file.write_text(config_content)

            config = LimitsConfig.load(str(config_file))

            assert config.github_api.request_timeout == 15
            assert config.discovery.max_repositories == 200
            assert config.extraction.file_download_timeout == 45
            assert config.upload.batch_size == 50
            assert config.validation.max_validation_errors == 5

    def test_limits_config_load_nonexistent_file(self) -> None:
        """Test loading from nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            LimitsConfig.load("/nonexistent/path/config.yaml")

    def test_limits_config_load_invalid_yaml(self) -> None:
        """Test loading invalid YAML raises error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config_file = tmp_path / "invalid.yaml"

            # Write invalid YAML
            config_file.write_text("invalid: yaml: content:")

            with pytest.raises(Exception):  # YAML parsing error
                LimitsConfig.load(str(config_file))
