"""Base class for discovery services."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from tladata.logging import get_logger

if TYPE_CHECKING:
    from tladata.config import DiscoveryLimits
    from tladata.discovery.github_client import GithubClient


class DiscoveryService(ABC):
    """Abstract base class for discovery services.

    Provides common initialization and logging for all discovery operations.
    Subclasses should implement run() to define specific discovery behavior.
    """

    def __init__(
        self,
        client: "GithubClient",
        output_path: str,
        limits: "DiscoveryLimits",
    ) -> None:
        """Initialize the discovery service.

        Args:
            client: GitHub API client
            output_path: Path where discovered data will be written
            limits: Discovery configuration limits
        """
        self.client = client
        self.output_path = output_path
        self.limits = limits
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def run(self) -> None:
        """Execute the discovery operation.

        Subclasses must implement this to define specific discovery behavior.
        """
        pass
