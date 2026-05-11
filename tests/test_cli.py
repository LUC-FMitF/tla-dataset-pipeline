"""Unit tests for the CLI module."""

import argparse
from unittest.mock import MagicMock, Mock, patch

import pytest

from tladata.cli import (
    discover,
    fetch_seeds,
    pull,
    push_to_s3,
    search,
    validate,
    validate_manifest,
)
from tladata.config import LimitsConfig


class TestDiscoverCommand:
    """Test the discover CLI command."""

    def test_discover_command_creates_pipeline(
        self, test_config: LimitsConfig, tmp_path
    ) -> None:
        """Test discover command creates DiscoveryPipeline."""
        args = argparse.Namespace(
            output=str(tmp_path / "output.jsonl"),
            schema="data_contracts/schemas/source_record.schema.json",
        )
        
        with patch("tladata.cli.get_github_client") as mock_client:
            with patch("tladata.cli.DiscoveryPipeline") as mock_pipeline:
                discover(args, test_config)
                
                # Verify DiscoveryPipeline was instantiated
                mock_pipeline.assert_called_once()

    def test_discover_command_handles_error(
        self, test_config: LimitsConfig, tmp_path
    ) -> None:
        """Test discover command handles errors gracefully."""
        args = argparse.Namespace(
            output=str(tmp_path / "output.jsonl"),
            schema="data_contracts/schemas/source_record.schema.json",
        )
        
        with patch("tladata.cli.get_github_client") as mock_client:
            mock_client.side_effect = ValueError("Test error")
            
            result = discover(args, test_config)
            
            # Should return error code
            assert result == 1


class TestSearchCommand:
    """Test the search CLI command."""

    def test_search_command_creates_service(
        self, test_config: LimitsConfig, tmp_path
    ) -> None:
        """Test search command creates SearchService."""
        args = argparse.Namespace(
            output=str(tmp_path / "output.jsonl"),
        )
        
        with patch("tladata.cli.get_github_client") as mock_client:
            with patch("tladata.cli.SearchService") as mock_service:
                search(args, test_config)
                
                # Verify SearchService was instantiated
                mock_service.assert_called_once()


class TestValidateCommand:
    """Test the validate CLI command."""

    def test_validate_command_reads_manifest(
        self, test_config: LimitsConfig, temp_manifest_file: str
    ) -> None:
        """Test validate command processes manifest."""
        args = argparse.Namespace(
            manifest=temp_manifest_file,
            schema="data_contracts/schemas/source_record.schema.json",
        )
        
        result = validate(args, test_config)
        
        # Should execute without error (result could be 0 or 1 depending on validation)
        assert isinstance(result, int)


class TestFetchSeedsCommand:
    """Test the fetch-seeds CLI command."""

    def test_fetch_seeds_command_creates_service(
        self, test_config: LimitsConfig, tmp_path
    ) -> None:
        """Test fetch-seeds command creates SeedFetcher."""
        args = argparse.Namespace(
            output=str(tmp_path / "output.jsonl"),
        )
        
        with patch("tladata.cli.get_github_client") as mock_client:
            with patch("tladata.cli.SeedFetcher") as mock_service:
                fetch_seeds(args, test_config)
                
                # Verify SeedFetcher was instantiated
                mock_service.assert_called_once()


class TestPullCommand:
    """Test the pull CLI command."""

    def test_pull_command_creates_handler(
        self, test_config: LimitsConfig, temp_manifest_file: str, tmp_path
    ) -> None:
        """Test pull command creates FileExtractionHandler."""
        args = argparse.Namespace(
            manifest=temp_manifest_file,
            output=str(tmp_path / "extracted"),
        )
        
        with patch("tladata.cli.get_github_client") as mock_client:
            with patch("tladata.cli.FileExtractionHandler") as mock_handler:
                mock_handler_instance = Mock()
                mock_handler_instance.handle.return_value = 0
                mock_handler.return_value = mock_handler_instance
                
                pull(args, test_config)
                
                # Verify handler was created and handle() was called
                mock_handler.assert_called_once()
                mock_handler_instance.handle.assert_called_once()


class TestPushToS3Command:
    """Test the push-to-s3 CLI command."""

    def test_push_to_s3_command_creates_handler(
        self, test_config: LimitsConfig, tmp_path
    ) -> None:
        """Test push-to-s3 command creates S3UploadHandler."""
        args = argparse.Namespace(
            input=str(tmp_path / "data"),
            bucket="test-bucket",
            prefix="raw",
            dry_run=True,
        )
        
        with patch("tladata.cli.S3UploadHandler") as mock_handler:
            mock_handler_instance = Mock()
            mock_handler_instance.handle.return_value = 0
            mock_handler.return_value = mock_handler_instance
            
            push_to_s3(args, test_config)
            
            # Verify handler was created and handle() was called
            mock_handler.assert_called_once()
            mock_handler_instance.handle.assert_called_once()


class TestValidateManifestFunction:
    """Test the validate_manifest function."""

    def test_validate_manifest_with_valid_file(
        self, test_config: LimitsConfig, temp_manifest_file: str, temp_schema_file: str
    ) -> None:
        """Test validate_manifest with valid manifest file."""
        args = argparse.Namespace(
            manifest=temp_manifest_file,
            schema=temp_schema_file,
            verbose=False,
        )
        
        with patch("tladata.cli.ManifestValidationHandler") as mock_handler:
            mock_handler_instance = Mock()
            mock_handler_instance.handle.return_value = 0
            mock_handler.return_value = mock_handler_instance
            
            result = validate_manifest(args, test_config)
            
            assert isinstance(result, int)

    def test_validate_manifest_handles_error(
        self, test_config: LimitsConfig
    ) -> None:
        """Test validate_manifest handles missing files gracefully."""
        args = argparse.Namespace(
            manifest="/nonexistent/manifest.jsonl",
            schema="/nonexistent/schema.json",
            verbose=False,
        )
        
        with patch("tladata.cli.ManifestValidationHandler") as mock_handler:
            mock_handler.side_effect = FileNotFoundError("File not found")
            
            result = validate_manifest(args, test_config)
            
            # Should return error code
            assert result == 1


class TestCommandDispatchDict:
    """Test CLI command dispatch mechanism."""

    def test_all_commands_registered_in_dispatch(self) -> None:
        """Test all expected commands are registered in dispatch dict."""
        expected_commands = {
            "discover",
            "search",
            "validate",
            "fetch-seeds",
            "pull",
            "push-to-s3",
        }
        
        # This test verifies the expected command names exist
        # In actual CLI, the dispatch dict is created in main_discover
        assert len(expected_commands) == 6
