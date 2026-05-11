"""Discovery module with pipeline orchestration and services."""

from .base_service import DiscoveryService
from .github_client import GithubClient
from .github_search import fetch_repo_metadata, search_repositories
from .manifest import merge_records, write_jsonl
from .pipeline import DiscoveryPipeline, ManifestValidator, SearchService, SeedFetcher

__all__ = [
    "DiscoveryService",
    "DiscoveryPipeline",
    "SearchService",
    "SeedFetcher",
    "ManifestValidator",
    "GithubClient",
    "search_repositories",
    "fetch_repo_metadata",
    "write_jsonl",
    "merge_records",
]
