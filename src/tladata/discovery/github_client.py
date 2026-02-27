from typing import Any, Dict, Optional, cast
import requests

"""GithubClient is a simple wrapper around the GitHub API using requests. It handles authentication and provides a method for making GET requests to the API."""

class GithubClient:
    def __init__(self, token: str) -> None:
        self.base_url: str = "https://api.github.com"
        self.headers: Dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())
