"""Validation handler for JSONL manifest files."""

from pathlib import Path
from typing import TYPE_CHECKING

from tladata.cli_handler import CLIHandler
from tladata.config import LimitsConfig
from tladata.contracts.validate import validate_jsonl

if TYPE_CHECKING:
    import argparse


class ManifestValidationHandler(CLIHandler):
    """Handle manifest validation with output formatting."""

    def __init__(self, config: LimitsConfig) -> None:
        """Initialize the manifest validation handler.

        Args:
            config: Application configuration with limits
        """
        super().__init__()
        self.config = config

    def handle(self, args: "argparse.Namespace") -> int:
        """Validate a JSONL manifest file against a JSON schema.

        Args:
            args: Arguments with manifest, schema, and verbose attributes

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        # Convert to absolute paths if relative
        manifest_path = Path(args.manifest)
        schema_path = Path(args.schema)

        if not manifest_path.is_absolute():
            manifest_path = Path.cwd() / manifest_path
        if not schema_path.is_absolute():
            schema_path = Path.cwd() / schema_path

        self.logger.info(f"Validating manifest: {manifest_path}")
        self.logger.info(f"Schema: {schema_path}")

        success, errors = validate_jsonl(str(manifest_path), str(schema_path))

        if success:
            self.logger.info("Validation passed!")
            return 0

        # Handle validation failures
        max_errors_display = self.config.validation.max_validation_errors

        self.logger.error(f"Validation failed with {len(errors)} error(s)")
        if args.verbose or len(errors) <= max_errors_display:
            for error in errors:
                self.logger.error(f"  {error}")
        else:
            # Show first N errors and summary
            for error in errors[:max_errors_display]:
                self.logger.error(f"  {error}")
            self.logger.error(f"\n  ... and {len(errors) - max_errors_display} more errors")
            self.logger.info("Run with -v/--verbose to see all errors")

        return 1
