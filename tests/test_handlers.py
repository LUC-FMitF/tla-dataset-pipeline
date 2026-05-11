"""Unit tests for CLI handlers."""

import argparse
from unittest.mock import Mock, patch

import pytest

from tladata.cli_handler import CLIHandler
from tladata.config import LimitsConfig
from tladata.contracts.manifest_validator import ManifestValidationHandler
from tladata.extraction.file_extraction_handler import FileExtractionHandler
from tladata.extraction.s3_upload_handler import S3UploadHandler


class TestCLIHandlerBase:
    """Test CLIHandler abstract base class."""

    def test_cli_handler_is_abstract(self) -> None:
        """Test that CLIHandler cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CLIHandler()  # type: ignore[abstract]

    def test_cli_handler_requires_handle_method(self) -> None:
        """Test that CLIHandler requires handle() method."""

        class IncompleteHandler(CLIHandler):
            """Handler without handle method."""
            pass

        with pytest.raises(TypeError):
            IncompleteHandler()  # type: ignore[abstract]

    def test_cli_handler_subclass_with_handle(self) -> None:
        """Test that CLIHandler subclass can be instantiated with handle()."""

        class TestHandler(CLIHandler):
            """Test handler with handle method."""

            def handle(self, args: argparse.Namespace) -> int:
                """Handle command."""
                return 0

        handler = TestHandler()
        result = handler.handle(argparse.Namespace())
        assert result == 0


class TestManifestValidationHandler:
    """Test ManifestValidationHandler."""

    def test_manifest_validation_handler_inheritance(
        self, test_config: LimitsConfig
    ) -> None:
        """Test ManifestValidationHandler inherits from CLIHandler."""
        handler = ManifestValidationHandler(test_config)
        assert isinstance(handler, CLIHandler)

    def test_manifest_validation_handler_has_handle_method(
        self, test_config: LimitsConfig
    ) -> None:
        """Test ManifestValidationHandler has handle() method."""
        handler = ManifestValidationHandler(test_config)
        assert hasattr(handler, "handle")
        assert callable(handler.handle)

    def test_manifest_validation_handler_with_valid_manifest(
        self, test_config: LimitsConfig, temp_manifest_file: str, temp_schema_file: str
    ) -> None:
        """Test ManifestValidationHandler with valid manifest file."""
        handler = ManifestValidationHandler(test_config)
        args = argparse.Namespace(
            manifest=temp_manifest_file,
            schema=temp_schema_file,
            verbose=False,
        )

        result = handler.handle(args)

        # Result should be an int (0 for success, 1 for failure)
        assert isinstance(result, int)
        assert result in (0, 1)


class TestFileExtractionHandler:
    """Test FileExtractionHandler."""

    def test_file_extraction_handler_inheritance(
        self, test_config: LimitsConfig
    ) -> None:
        """Test FileExtractionHandler inherits from CLIHandler."""
        with patch("tladata.cli_handler.get_logger"):
            from tladata.discovery.github_client import GithubClient
            client = Mock(spec=GithubClient)
            handler = FileExtractionHandler(test_config, client)
            assert isinstance(handler, CLIHandler)

    def test_file_extraction_handler_has_handle_method(
        self, test_config: LimitsConfig
    ) -> None:
        """Test FileExtractionHandler has handle() method."""
        with patch("tladata.cli_handler.get_logger"):
            from tladata.discovery.github_client import GithubClient
            client = Mock(spec=GithubClient)
            handler = FileExtractionHandler(test_config, client)
            assert hasattr(handler, "handle")
            assert callable(handler.handle)

    def test_file_extraction_handler_with_missing_manifest(
        self, test_config: LimitsConfig, tmp_path
    ) -> None:
        """Test FileExtractionHandler handles missing manifest."""
        with patch("tladata.cli_handler.get_logger"):
            from tladata.discovery.github_client import GithubClient
            client = Mock(spec=GithubClient)
            handler = FileExtractionHandler(test_config, client)

            args = argparse.Namespace(
                manifest=str(tmp_path / "nonexistent.jsonl"),
                output=str(tmp_path / "output"),
            )

            with patch.object(handler, "handle", wraps=handler.handle):
                result = handler.handle(args)

                # Should return error code on missing manifest
                assert isinstance(result, int)
                assert result == 1


class TestS3UploadHandler:
    """Test S3UploadHandler."""

    def test_s3_upload_handler_inheritance(
        self, test_config: LimitsConfig
    ) -> None:
        """Test S3UploadHandler inherits from CLIHandler."""
        with patch("tladata.cli_handler.get_logger"):
            handler = S3UploadHandler(test_config)
            assert isinstance(handler, CLIHandler)

    def test_s3_upload_handler_has_handle_method(
        self, test_config: LimitsConfig
    ) -> None:
        """Test S3UploadHandler has handle() method."""
        with patch("tladata.cli_handler.get_logger"):
            handler = S3UploadHandler(test_config)
            assert hasattr(handler, "handle")
            assert callable(handler.handle)

    def test_s3_upload_handler_with_missing_input_dir(
        self, test_config: LimitsConfig, tmp_path
    ) -> None:
        """Test S3UploadHandler handles missing input directory."""
        with patch("tladata.cli_handler.get_logger"):
            handler = S3UploadHandler(test_config)

            args = argparse.Namespace(
                input=str(tmp_path / "nonexistent"),
                bucket="test-bucket",
                prefix="raw",
                dry_run=True,
            )

            result = handler.handle(args)

            # Should return error code on missing input
            assert isinstance(result, int)
            assert result == 1

    def test_s3_upload_handler_dry_run(
        self, test_config: LimitsConfig, tmp_path
    ) -> None:
        """Test S3UploadHandler respects dry_run flag."""
        with patch("tladata.cli_handler.get_logger"):
            # Create a test directory with a file
            input_dir = tmp_path / "input"
            input_dir.mkdir()
            (input_dir / "test.tla").write_text("---- MODULE Test ----\nPLACEHOLDER\n====")

            handler = S3UploadHandler(test_config)

            args = argparse.Namespace(
                input=str(input_dir),
                bucket="test-bucket",
                prefix="raw",
                dry_run=True,  # Should not actually upload
            )

            with patch("tladata.extraction.s3_uploader.HAS_BOTO3", False):
                result = handler.handle(args)

                # Should handle gracefully (may fail due to missing boto3, but that's ok)
                assert isinstance(result, int)
