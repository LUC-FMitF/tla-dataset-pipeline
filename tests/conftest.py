"""Pytest configuration and shared fixtures."""

import json
import tempfile
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from tladata.config import (
    DiscoveryLimits,
    ExtractionLimits,
    GitHubAPILimits,
    LimitsConfig,
    UploadLimits,
    ValidationLimits,
)
from tladata.contracts.types import RepositoryDiscovery, RepoMetadata
from tladata.discovery.github_client import GithubClient


# ============================================================================
# Config Fixtures
# ============================================================================


@pytest.fixture
def github_api_limits() -> GitHubAPILimits:
    """Create GitHub API limits for testing."""
    return GitHubAPILimits(
        request_timeout=10,
        max_retries=2,
        retry_delay=1,
    )


@pytest.fixture
def discovery_limits() -> DiscoveryLimits:
    """Create discovery limits for testing."""
    return DiscoveryLimits(
        max_repositories=100,
        max_results_per_query=30,
        call_delay=0.1,
    )


@pytest.fixture
def extraction_limits() -> ExtractionLimits:
    """Create extraction limits for testing."""
    return ExtractionLimits(
        file_download_timeout=30,
        max_file_size=10_000_000,  # 10 MB
        max_files_per_repo=50,
    )


@pytest.fixture
def upload_limits() -> UploadLimits:
    """Create upload limits for testing."""
    return UploadLimits(
        batch_size=100,
    )


@pytest.fixture
def validation_limits() -> ValidationLimits:
    """Create validation limits for testing."""
    return ValidationLimits(
        max_validation_errors=10,
    )


@pytest.fixture
def test_config(
    github_api_limits: GitHubAPILimits,
    discovery_limits: DiscoveryLimits,
    extraction_limits: ExtractionLimits,
    upload_limits: UploadLimits,
    validation_limits: ValidationLimits,
) -> LimitsConfig:
    """Create a test LimitsConfig with all limits."""
    return LimitsConfig(
        github_api=github_api_limits,
        discovery=discovery_limits,
        extraction=extraction_limits,
        upload=upload_limits,
        validation=validation_limits,
    )


# ============================================================================
# GitHub Client Fixtures
# ============================================================================


@pytest.fixture
def mock_github_client(github_api_limits: GitHubAPILimits) -> GithubClient:
    """Create a mock GitHub client for testing."""
    with patch.object(GithubClient, "get") as mock_get:
        client = GithubClient("test-token", github_api_limits)
        client.get = mock_get  # type: ignore[assignment]
        return client


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_repo_metadata() -> RepoMetadata:
    """Create sample repository metadata."""
    return {
        "repo": "torvalds/linux",
        "description": "Linux kernel repository",
        "stars": 150000,
        "default_branch": "master",
        "url": "https://github.com/torvalds/linux",
    }


@pytest.fixture
def sample_repository_discovery() -> RepositoryDiscovery:
    """Create sample repository discovery record."""
    return {
        "repo": "tlaplus/Examples",
        "url": "https://github.com/tlaplus/Examples",
        "description": "TLA+ Examples",
        "stars": 500,
        "default_branch": "master",
        "sha": "abc123def456",
    }


@pytest.fixture
def sample_manifest_record() -> dict[str, Any]:
    """Create a sample manifest record."""
    return {
        "repo": "tlaplus/Examples",
        "url": "https://github.com/tlaplus/Examples",
        "description": "TLA+ Examples",
        "stars": 500,
        "default_branch": "master",
        "sha": "abc123def456",
    }


@pytest.fixture
def temp_manifest_file(
    tmp_path: Path, sample_manifest_record: dict[str, Any]
) -> Generator[str, None, None]:
    """Create a temporary manifest JSONL file with sample data."""
    manifest_file = tmp_path / "test_manifest.jsonl"
    
    with open(manifest_file, "w") as f:
        for i in range(5):
            record = {**sample_manifest_record, "repo": f"repo-{i}"}
            f.write(json.dumps(record) + "\n")
    
    yield str(manifest_file)


@pytest.fixture
def temp_schema_file(tmp_path: Path) -> Generator[str, None, None]:
    """Create a temporary JSON schema file."""
    schema_file = tmp_path / "test_schema.json"
    
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "url": {"type": "string"},
            "description": {"type": "string"},
            "stars": {"type": "integer"},
            "default_branch": {"type": "string"},
            "sha": {"type": "string"},
        },
        "required": ["repo", "url", "sha"],
    }
    
    with open(schema_file, "w") as f:
        json.dump(schema, f)
    
    yield str(schema_file)


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Generator[str, None, None]:
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    yield str(output_dir)


# ============================================================================
# Mock Response Fixtures
# ============================================================================


@pytest.fixture
def mock_github_search_response() -> dict[str, Any]:
    """Create a mock GitHub search API response."""
    return {
        "total_count": 2,
        "incomplete_results": False,
        "items": [
            {
                "id": 1,
                "name": "Examples",
                "full_name": "tlaplus/Examples",
                "owner": {
                    "login": "tlaplus",
                    "id": 1,
                },
                "html_url": "https://github.com/tlaplus/Examples",
                "description": "TLA+ Examples",
                "stargazers_count": 500,
                "default_branch": "master",
            },
            {
                "id": 2,
                "name": "tla-dataset",
                "full_name": "tla-project/tla-dataset",
                "owner": {
                    "login": "tla-project",
                    "id": 2,
                },
                "html_url": "https://github.com/tla-project/tla-dataset",
                "description": "TLA+ Dataset",
                "stargazers_count": 100,
                "default_branch": "main",
            },
        ],
    }


@pytest.fixture
def mock_github_commit_response() -> dict[str, Any]:
    """Create a mock GitHub commit API response."""
    return {
        "sha": "abc123def456",
        "url": "https://api.github.com/repos/tlaplus/Examples/commits/abc123def456",
        "html_url": "https://github.com/tlaplus/Examples/commit/abc123def456",
        "commit": {
            "author": {
                "name": "Test Author",
                "email": "test@example.com",
                "date": "2024-01-01T00:00:00Z",
            },
            "message": "Test commit",
        },
    }


@pytest.fixture
def mock_github_tree_response() -> dict[str, Any]:
    """Create a mock GitHub tree API response."""
    return {
        "sha": "abc123def456",
        "url": "https://api.github.com/repos/tlaplus/Examples/git/trees/abc123def456",
        "tree": [
            {
                "path": "Foo.tla",
                "mode": "100644",
                "type": "blob",
                "sha": "blob1",
                "url": "https://api.github.com/repos/tlaplus/Examples/git/blobs/blob1",
            },
            {
                "path": "Bar.cfg",
                "mode": "100644",
                "type": "blob",
                "sha": "blob2",
                "url": "https://api.github.com/repos/tlaplus/Examples/git/blobs/blob2",
            },
            {
                "path": "README.md",
                "mode": "100644",
                "type": "blob",
                "sha": "blob3",
                "url": "https://api.github.com/repos/tlaplus/Examples/git/blobs/blob3",
            },
        ],
        "truncated": False,
    }
