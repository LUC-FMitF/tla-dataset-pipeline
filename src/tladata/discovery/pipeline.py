"""Orchestration layer for discovery operations."""

from typing import TYPE_CHECKING, Any

from tladata.contracts.validate import validate_jsonl
from tladata.discovery.base_service import DiscoveryService
from tladata.discovery.github_client import GithubClient
from tladata.discovery.github_search import (
    fetch_repo_metadata,
    search_repositories,
)
from tladata.discovery.manifest import merge_records, write_jsonl
from tladata.logging import get_logger
from tladata.utils.load_seeds import load_queries, load_seed_repos

if TYPE_CHECKING:
    from tladata.config import DiscoveryLimits


logger = get_logger(__name__)


class DiscoveryPipeline(DiscoveryService):
    """Full discovery pipeline: seeds + search + write + validate."""

    def __init__(
        self,
        client: GithubClient,
        output_path: str,
        schema_path: str,
        limits: "DiscoveryLimits",
    ) -> None:
        """Initialize the discovery pipeline.

        Args:
            client: GitHub API client
            output_path: Output path for discovered repositories
            schema_path: Path to validation schema
            limits: Discovery configuration limits
        """
        super().__init__(client, output_path, limits)
        self.schema_path = schema_path

    def run(self) -> None:
        """Execute the full discovery pipeline."""
        seeds = load_seed_repos()
        queries = load_queries()

        discovered = self._fetch_seeds(seeds)
        discovered = self._run_searches(queries, discovered)

        write_jsonl(self.output_path, discovered.values())
        self.logger.info(f"Manifest written to: {self.output_path}")

        self._validate()

    def _fetch_seeds(self, seeds: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch metadata for seeded repositories."""
        discovered: dict[str, dict[str, Any]] = {}
        for repo in seeds:
            if len(discovered) >= self.limits.max_repositories:
                self.logger.info(f"Reached max repositories limit ({self.limits.max_repositories})")
                break
            discovered[repo] = fetch_repo_metadata(self.client, repo, source="seed")
        return discovered

    def _run_searches(
        self, queries: list[str], discovered: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Run search queries and merge results."""
        for query in queries:
            if len(discovered) >= self.limits.max_repositories:
                self.logger.info(
                    f"Reached max repositories limit ({self.limits.max_repositories}), stopping search"
                )
                break

            repos = search_repositories(self.client, query)

            # Limit results per query
            repos_to_process = repos[: self.limits.max_results_per_query]
            if len(repos) > self.limits.max_results_per_query:
                self.logger.info(
                    f"Limiting search results for query '{query}' to {self.limits.max_results_per_query} (found {len(repos)})"
                )

            for repo_dict in repos_to_process:
                if len(discovered) >= self.limits.max_repositories:
                    self.logger.info(
                        f"Reached max repositories limit ({self.limits.max_repositories})"
                    )
                    break

                repo_name = str(repo_dict.get("full_name", ""))
                new_metadata = fetch_repo_metadata(self.client, repo_name, source=f"query:{query}")
                if repo_name in discovered:
                    discovered[repo_name] = merge_records(discovered[repo_name], new_metadata)
                else:
                    discovered[repo_name] = new_metadata
        return discovered

    def _validate(self) -> None:
        """Validate the output manifest."""
        success, errors = validate_jsonl(self.output_path, self.schema_path)
        if success:
            self.logger.info(f"Validation passed against: {self.schema_path}")
        else:
            raise RuntimeError("Validation failed:\n" + "\n".join(errors))


class SearchService(DiscoveryService):
    """Search-only service."""

    def run(self) -> None:
        """Execute search queries and write results."""
        queries = load_queries()
        discovered: dict[str, dict[str, Any]] = {}

        for query in queries:
            if len(discovered) >= self.limits.max_repositories:
                self.logger.info(
                    f"Reached max repositories limit ({self.limits.max_repositories}), stopping search"
                )
                break

            repos = search_repositories(self.client, query)

            # Limit results per query
            repos_to_process = repos[: self.limits.max_results_per_query]
            if len(repos) > self.limits.max_results_per_query:
                self.logger.info(
                    f"Limiting search results for query '{query}' to {self.limits.max_results_per_query} (found {len(repos)})"
                )

            for repo_dict in repos_to_process:
                if len(discovered) >= self.limits.max_repositories:
                    self.logger.info(
                        f"Reached max repositories limit ({self.limits.max_repositories})"
                    )
                    break

                repo_name = str(repo_dict.get("full_name", ""))
                new_metadata = fetch_repo_metadata(self.client, repo_name, source=f"query:{query}")
                if repo_name in discovered:
                    discovered[repo_name] = merge_records(discovered[repo_name], new_metadata)
                else:
                    discovered[repo_name] = new_metadata

        write_jsonl(self.output_path, discovered.values())
        self.logger.info(f"Search results written to: {self.output_path}")


class SeedFetcher(DiscoveryService):
    """Fetches metadata for seeded repositories only."""

    def run(self) -> None:
        """Fetch seeded repos and write results."""
        seeds = load_seed_repos()
        discovered: dict[str, dict[str, Any]] = {}

        for repo in seeds:
            discovered[repo] = fetch_repo_metadata(self.client, repo, source="seed")

        write_jsonl(self.output_path, discovered.values())
        self.logger.info(f"Seed repos metadata written to: {self.output_path}")


class ManifestValidator:
    """Validates manifests against schemas."""

    def __init__(self, manifest_path: str, schema_path: str) -> None:
        """Initialize the manifest validator.

        Args:
            manifest_path: Path to JSONL manifest file
            schema_path: Path to JSON schema file
        """
        self.manifest_path = manifest_path
        self.schema_path = schema_path
        self.logger = get_logger(self.__class__.__name__)

    def validate(self) -> None:
        """Validate the manifest."""
        success, errors = validate_jsonl(self.manifest_path, self.schema_path)
        if success:
            self.logger.info(f"Validation passed: {self.manifest_path} against {self.schema_path}")
        else:
            raise RuntimeError("Validation failed:\n" + "\n".join(errors))
