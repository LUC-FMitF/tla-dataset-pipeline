"""Handler for extracting files from repositories."""

from typing import TYPE_CHECKING

from tladata.cli_handler import CLIHandler
from tladata.config import LimitsConfig
from tladata.extraction.file_extractor import FileExtractor

if TYPE_CHECKING:
    import argparse

    from tladata.discovery.github_client import GithubClient


class FileExtractionHandler(CLIHandler):
    """Handle file extraction operations."""

    def __init__(self, config: LimitsConfig, client: "GithubClient") -> None:
        """Initialize the file extraction handler.

        Args:
            config: Application configuration with limits
            client: Authenticated GitHub client
        """
        super().__init__()
        self.config = config
        self.client = client

    def handle(self, args: "argparse.Namespace") -> int:
        """Extract .tla, .cfg, and .tlaps files from discovered repositories.

        Args:
            args: Arguments with manifest and output paths

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            self.logger.info("Starting file extraction")
            extractor = FileExtractor(self.client, self.config.extraction)
            extractor.extract_files(args.manifest, args.output)
            self.logger.info(f"Files extracted to: {args.output}")
            return 0
        except Exception as e:
            self.logger.error(f"Error during extraction: {e}")
            return 1
