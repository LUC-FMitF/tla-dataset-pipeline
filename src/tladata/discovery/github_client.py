"""GitHub API client with retry logic and rate limit handling."""

from typing import TYPE_CHECKING, Any, cast

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tladata.logging import get_logger

if TYPE_CHECKING:
    from tladata.config import GitHubAPILimits


logger = get_logger(__name__)


class GithubClient:
    """Simple wrapper around the GitHub API using requests.
    
    Handles authentication, provides GET request method with retry logic,
    and respects GitHub API rate limits and timeouts.
    """

    def __init__(self, token: str, limits: "GitHubAPILimits") -> None:
        """Initialize GitHub client.
        
        Args:
            token: GitHub personal access token
            limits: GitHub API configuration limits
        """
        self.base_url: str = "https://api.github.com"
        self.headers: dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        self.request_timeout = limits.request_timeout
        self.max_retries = limits.max_retries
        self.retry_delay = limits.retry_delay

        # Create session with connection pooling and retry adapter
        self.session = requests.Session()
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=limits.max_retries - 1,  # urllib3 Retry total excludes the initial request
            backoff_factor=1,  # 1 * 2^attempt for exponential backoff
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
            allowed_methods=["GET"],  # Only retry GET requests
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get(
        self, path: str, params: dict[str, Any] | None = None, timeout: int | None = None
    ) -> dict[str, Any]:
        """Get from GitHub API with retry logic and timeouts.

        Args:
            path: API endpoint path
            params: Query parameters
            timeout: Custom timeout in seconds (uses default if not specified)
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            RuntimeError: If max retries exceeded
        """
        url = f"{self.base_url}{path}"
        request_timeout = timeout if timeout is not None else self.request_timeout

        try:
            resp = self.session.get(
                url, headers=self.headers, params=params, timeout=request_timeout
            )
            resp.raise_for_status()
            return cast(dict[str, Any], resp.json())
        except requests.exceptions.RequestException as e:
            # Log the error and raise with proper context
            logger.error(f"GitHub API request failed after retries: {e}")
            raise RuntimeError(f"GitHub API request failed: {e}") from e
