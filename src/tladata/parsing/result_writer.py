"""Handles I/O operations for prompt results."""

import json
from pathlib import Path
from typing import Any

from tladata.logging import get_logger


class PromptResultWriter:
    """Manages reading and writing of TLA+ parsing results.

    Handles serialization/deserialization of prompt results to/from JSON files
    with proper error handling and directory management.
    """

    def __init__(self, output_dir: str) -> None:
        """Initialize the result writer.

        Args:
            output_dir: Base directory for storing results

        Raises:
            ValueError: If output_dir is empty or None
        """
        if not output_dir:
            raise ValueError("Output directory cannot be empty")

        self.output_dir = Path(output_dir)
        self.logger = get_logger(self.__class__.__name__)
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Output directory ensured: {self.output_dir}")

    def save_v1_result(self, tla_filename: str, result: dict[str, Any]) -> Path:
        """Save V1 prompt result to JSON file.

        Args:
            tla_filename: Base name of the TLA+ file (e.g., "myspec.tla")
            result: V1 result dictionary

        Returns:
            Path to saved file

        Raises:
            ValueError: If result is not a valid dictionary
            IOError: If file writing fails
        """
        if not isinstance(result, dict):
            raise ValueError(f"Result must be a dictionary, got {type(result)}")

        output_file = self._get_v1_path(tla_filename)
        self._write_json_file(output_file, result)
        return output_file

    def save_v2_result(self, tla_filename: str, result: dict[str, Any]) -> Path:
        """Save V2 prompt result to JSON file.

        Args:
            tla_filename: Base name of the TLA+ file
            result: V2 result dictionary

        Returns:
            Path to saved file

        Raises:
            ValueError: If result is not a valid dictionary
            IOError: If file writing fails
        """
        if not isinstance(result, dict):
            raise ValueError(f"Result must be a dictionary, got {type(result)}")

        output_file = self._get_v2_path(tla_filename)
        self._write_json_file(output_file, result)
        return output_file

    def save_v3_result(self, tla_filename: str, result: dict[str, Any]) -> Path:
        """Save V3 prompt result to JSON file.

        Args:
            tla_filename: Base name of the TLA+ file
            result: V3 result dictionary

        Returns:
            Path to saved file

        Raises:
            ValueError: If result is not a valid dictionary
            IOError: If file writing fails
        """
        if not isinstance(result, dict):
            raise ValueError(f"Result must be a dictionary, got {type(result)}")

        output_file = self._get_v3_path(tla_filename)
        self._write_json_file(output_file, result)
        return output_file

    def load_v1_result(self, tla_filename: str) -> dict[str, Any]:
        """Load V1 prompt result from JSON file.

        Args:
            tla_filename: Base name of the TLA+ file

        Returns:
            V1 result dictionary

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        return self._read_json_file(self._get_v1_path(tla_filename))

    def load_v2_result(self, tla_filename: str) -> dict[str, Any]:
        """Load V2 prompt result from JSON file.

        Args:
            tla_filename: Base name of the TLA+ file

        Returns:
            V2 result dictionary

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        return self._read_json_file(self._get_v2_path(tla_filename))

    def load_v3_result(self, tla_filename: str) -> dict[str, Any]:
        """Load V3 prompt result from JSON file.

        Args:
            tla_filename: Base name of the TLA+ file

        Returns:
            V3 result dictionary

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        return self._read_json_file(self._get_v3_path(tla_filename))

    def v1_result_exists(self, tla_filename: str) -> bool:
        """Check if V1 result exists for a TLA+ file.

        Args:
            tla_filename: Base name of the TLA+ file

        Returns:
            True if the file exists, False otherwise
        """
        return self._get_v1_path(tla_filename).exists()

    def v2_result_exists(self, tla_filename: str) -> bool:
        """Check if V2 result exists for a TLA+ file.

        Args:
            tla_filename: Base name of the TLA+ file

        Returns:
            True if the file exists, False otherwise
        """
        return self._get_v2_path(tla_filename).exists()

    def v3_result_exists(self, tla_filename: str) -> bool:
        """Check if V3 result exists for a TLA+ file.

        Args:
            tla_filename: Base name of the TLA+ file

        Returns:
            True if the file exists, False otherwise
        """
        return self._get_v3_path(tla_filename).exists()

    def _get_v1_path(self, tla_filename: str) -> Path:
        """Get the path for a V1 result file.

        Args:
            tla_filename: Base name of the TLA+ file

        Returns:
            Path object for the V1 result file
        """
        stem = Path(tla_filename).stem
        return self.output_dir / f"{stem}_v1.json"

    def _get_v2_path(self, tla_filename: str) -> Path:
        """Get the path for a V2 result file.

        Args:
            tla_filename: Base name of the TLA+ file

        Returns:
            Path object for the V2 result file
        """
        stem = Path(tla_filename).stem
        return self.output_dir / f"{stem}_v2.json"

    def _get_v3_path(self, tla_filename: str) -> Path:
        """Get the path for a V3 result file.

        Args:
            tla_filename: Base name of the TLA+ file

        Returns:
            Path object for the V3 result file
        """
        stem = Path(tla_filename).stem
        return self.output_dir / f"{stem}_v3.json"

    def _write_json_file(self, filepath: Path, data: dict[str, Any]) -> None:
        """Write data to a JSON file with proper formatting.

        Args:
            filepath: Path where the file should be written
            data: Dictionary to serialize

        Raises:
            IOError: If the file cannot be written
        """
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Result saved to {filepath}")
        except OSError as e:
            self.logger.error(f"Failed to write JSON file {filepath}: {e}")
            raise

    def _read_json_file(self, filepath: Path) -> dict[str, Any]:
        """Read data from a JSON file.

        Args:
            filepath: Path to the JSON file to read

        Returns:
            Dictionary loaded from JSON

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        try:
            with open(filepath) as f:
                data = json.load(f)
            self.logger.info(f"Result loaded from {filepath}")
            return data
        except FileNotFoundError:
            self.logger.error(f"Result file not found: {filepath}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in file {filepath}: {e}")
            raise
