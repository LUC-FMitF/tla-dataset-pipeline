"""Unit tests for the GitHub client module."""

from unittest.mock import Mock, patch

import pytest
import requests

from tladata.config import GitHubAPILimits
from tladata.discovery.github_client import GithubClient


class TestGithubClient:
    """Test GithubClient initialization and methods."""

    def test_github_client_initialization(
        self, github_api_limits: GitHubAPILimits
    ) -> None:
        """Test GithubClient initializes with correct attributes."""
        client = GithubClient("test-token", github_api_limits)

        assert client.base_url == "https://api.github.com"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test-token"
        assert client.request_timeout == github_api_limits.request_timeout
        assert client.max_retries == github_api_limits.max_retries
        assert client.session is not None

    def test_github_client_has_session(
        self, github_api_limits: GitHubAPILimits
    ) -> None:
        """Test GithubClient has requests.Session with retry adapter."""
        client = GithubClient("test-token", github_api_limits)

        assert hasattr(client, "session")
        assert isinstance(client.session, requests.Session)
        assert "https://" in client.session.adapters
        assert "http://" in client.session.adapters

    def test_github_client_get_success(
        self, github_api_limits: GitHubAPILimits
    ) -> None:
        """Test successful GitHub API GET request."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"test": "data"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            client = GithubClient("test-token", github_api_limits)
            result = client.get("/repos/test/repo")

            assert result == {"test": "data"}
            mock_get.assert_called_once()

    def test_github_client_get_with_params(
        self, github_api_limits: GitHubAPILimits
    ) -> None:
        """Test GitHub API GET request with query parameters."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"items": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            client = GithubClient("test-token", github_api_limits)
            params = {"q": "language:tlaplus", "per_page": 30}
            result = client.get("/search/repositories", params=params)

            assert result == {"items": []}
            # Verify params were passed
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["params"] == params

    def test_github_client_get_with_custom_timeout(
        self, github_api_limits: GitHubAPILimits
    ) -> None:
        """Test GitHub API GET request with custom timeout."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"test": "data"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            client = GithubClient("test-token", github_api_limits)
            result = client.get("/repos/test/repo", timeout=60)

            assert result == {"test": "data"}
            # Verify custom timeout was used
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["timeout"] == 60

    def test_github_client_get_uses_default_timeout(
        self, github_api_limits: GitHubAPILimits
    ) -> None:
        """Test GitHub API GET request uses default timeout when not specified."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"test": "data"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            client = GithubClient("test-token", github_api_limits)
            result = client.get("/repos/test/repo")

            assert result == {"test": "data"}
            # Verify default timeout was used
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["timeout"] == github_api_limits.request_timeout

    def test_github_client_get_request_exception(
        self, github_api_limits: GitHubAPILimits
    ) -> None:
        """Test GitHub API GET request handles request exceptions."""
        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

            client = GithubClient("test-token", github_api_limits)

            with pytest.raises(RuntimeError, match="GitHub API request failed"):
                client.get("/repos/test/repo")

    def test_github_client_get_http_error(
        self, github_api_limits: GitHubAPILimits
    ) -> None:
        """Test GitHub API GET request handles HTTP errors."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "404 Not Found"
            )
            mock_get.return_value = mock_response

            client = GithubClient("test-token", github_api_limits)

            with pytest.raises(RuntimeError, match="GitHub API request failed"):
                client.get("/repos/test/repo")

    def test_github_client_headers_set_correctly(
        self, github_api_limits: GitHubAPILimits
    ) -> None:
        """Test GitHub client headers include proper Accept header."""
        client = GithubClient("test-token", github_api_limits)

        assert client.headers["Accept"] == "application/vnd.github+json"
        assert client.headers["Authorization"] == "Bearer test-token"
