import time
from typing import Any, Optional, cast

import requests

from tladata.utils.load_limits import load_limits

"""GithubClient is a simple wrapper around the GitHub API using requests. It handles authentication and provides a method for making GET requests to the API."""


class GithubClient:
    def __init__(self, token: str) -> None:
        self.base_url: str = "https://api.github.com"
        self.headers: dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        limits = load_limits()
        self.request_timeout = limits.get("github_api", "request_timeout", 30)
        self.max_retries = limits.get("github_api", "max_retries", 3)
        self.retry_delay = limits.get("github_api", "retry_delay", 1)

    def get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Get from GitHub API with retry logic and timeouts."""
        url = f"{self.base_url}{path}"

        last_error = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.get(
                    url, headers=self.headers, params=params, timeout=self.request_timeout
                )
                resp.raise_for_status()
                return cast(dict[str, Any], resp.json())
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)  # exponential backoff
                    print(f"Retry attempt {attempt + 1}/{self.max_retries} after {wait_time}s...")
                    time.sleep(wait_time)

        # If all retries failed, raise the last error
        raise last_error or requests.exceptions.RequestException("Max retries exceeded")
