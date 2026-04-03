import time
from datetime import datetime, timezone
from typing import Any, cast

from tladata.discovery.github_client import GithubClient
from tladata.utils.load_limits import load_limits

"""This module contains functions for searching GitHub repositories and fetching their metadata using the GitHub API."""


def search_repositories(
    client: GithubClient, query: str, per_page: int | None = None
) -> list[dict[str, Any]]:
    """Search GitHub repositories with configured limits."""
    limits = load_limits()
    if per_page is None:
        per_page = limits.get("github_api", "per_page", 50)
    call_delay = limits.get("discovery", "call_delay", 0.1)

    params: dict[str, Any] = {"q": query, "per_page": per_page}
    time.sleep(call_delay)  # Rate limiting to avoid hitting API limits
    data = client.get("/search/repositories", params=params)
    return cast(list[dict[str, Any]], data.get("items", []))


def fetch_repo_metadata(client: GithubClient, full_name: str, source: str) -> dict[str, Any]:
    """Fetch repository metadata with rate limiting."""
    limits = load_limits()
    call_delay = limits.get("discovery", "call_delay", 0.1)

    time.sleep(call_delay)  # Rate limiting
    repo = client.get(f"/repos/{full_name}")
    default_branch = repo["default_branch"]

    time.sleep(call_delay)  # Rate limiting
    # Get HEAD SHA
    branch = client.get(f"/repos/{full_name}/branches/{default_branch}")
    sha = branch["commit"]["sha"]

    return {
        "repo": full_name,
        "html_url": repo["html_url"],
        "default_branch": default_branch,
        "sha": sha,
        "license_spdx": repo["license"]["spdx_id"] if repo["license"] else None,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "query_hits": [source],
    }
