from typing import Any, Dict, List, Optional, cast
from datetime import datetime, timezone
import requests
import os

BASE_URL: str = "https://api.github.com"


def _headers() -> Dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def search_repositories(query: str, per_page: int = 50) -> List[Dict[str, Any]]:
    url = f"{BASE_URL}/search/repositories"
    params: Dict[str, Any] = {"q": query, "per_page": per_page}

    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    data = cast(Dict[str, Any], resp.json())

    return cast(List[Dict[str, Any]], data.get("items", []))


def fetch_repo_metadata(full_name: str, source: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/repos/{full_name}"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    repo = resp.json()

    default_branch = repo["default_branch"]

    # Get HEAD SHA
    branch_url = f"{BASE_URL}/repos/{full_name}/branches/{default_branch}"
    branch_resp = requests.get(branch_url, headers=_headers())
    branch_resp.raise_for_status()
    branch = branch_resp.json()

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
