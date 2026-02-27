from typing import Any, Dict, List, cast
from datetime import datetime, timezone
from tladata.discovery.github_client import GithubClient

"""This module contains functions for searching GitHub repositories and fetching their metadata using the GitHub API."""

def search_repositories(
    client: GithubClient, query: str, per_page: int = 50
) -> List[Dict[str, Any]]:

    params: Dict[str, Any] = {"q": query, "per_page": per_page}
    data = client.get("/search/repositories", params=params)
    return cast(List[Dict[str, Any]], data.get("items", []))


def fetch_repo_metadata(client: GithubClient, full_name: str, source: str) -> Dict[str, Any]:

    repo = client.get(f"/repos/{full_name}")
    default_branch = repo["default_branch"]

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
        "query_hit": source,
    }
