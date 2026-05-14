"""Pipeline orchestrator for iterative prompt execution."""

from pathlib import Path
from typing import Any

from tladata.logging import get_logger
from tladata.parsing.orchestrator import PromptOrchestrator
from tladata.parsing.prompt_loader import PromptLoader
from tladata.parsing.result_writer import PromptResultWriter


class PromptPipeline:
    """Orchestrates the complete V1 -> V2 -> V3 prompt pipeline.

    Manages the flow of data through successive prompt versions, handling
    result persistence and error recovery. Uses a modular PromptOrchestrator
    with injected prompts for flexibility.
    """

    def __init__(
        self,
        api_key: str,
        output_dir: str,
        model_name: str = "gpt-4",
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        """Initialize the prompt pipeline.

        Args:
            api_key: OpenAI API key for LLM access
            output_dir: Directory for saving results
            model_name: LLM model to use (default: gpt-4)
            prompt_loader: Optional PromptLoader for custom prompts

        Raises:
            ValueError: If api_key or output_dir is empty
        """
        if not api_key:
            raise ValueError("API key cannot be empty")
        if not output_dir:
            raise ValueError("Output directory cannot be empty")

        self.api_key = api_key
        self.model_name = model_name
        self.result_writer = PromptResultWriter(output_dir)
        self.logger = get_logger(self.__class__.__name__)

        # Initialize orchestrator with optional custom prompt loader
        self.orchestrator = PromptOrchestrator(api_key, model_name, prompt_loader)

    def run_full_pipeline(
        self,
        tla_file_path: str,
        skip_existing: bool = True,
    ) -> dict[str, Any]:
        """Execute the complete V1 -> V2 -> V3 pipeline.

        Args:
            tla_file_path: Path to the TLA+ file to process
            skip_existing: Skip processing if V3 result already exists (default: True)

        Returns:
            V3 result dictionary

        Raises:
            FileNotFoundError: If the TLA+ file doesn't exist
            RuntimeError: If any pipeline stage fails
        """
        tla_path = Path(tla_file_path)
        if not tla_path.exists():
            raise FileNotFoundError(f"TLA+ file not found: {tla_file_path}")

        filename = tla_path.name

        # Check if already completed
        if skip_existing and self.result_writer.v3_result_exists(filename):
            self.logger.info(f"V3 result already exists for {filename}, loading from cache")
            return self.result_writer.load_v3_result(filename)

        # Read TLA+ content
        tla_content = tla_path.read_text()
        self.logger.info(f"Processing {filename} through full pipeline")

        try:
            # V1: Initial extraction
            self.logger.info(f"Running V1 for {filename}")
            v1_result = self._run_v1_stage(filename, tla_content)

            # V2: Verification and refinement
            self.logger.info(f"Running V2 for {filename}")
            v2_result = self._run_v2_stage(filename, tla_content, v1_result)

            # V3: Fine-grained division
            self.logger.info(f"Running V3 for {filename}")
            v3_result = self._run_v3_stage(filename, tla_content, v2_result)

            self.logger.info(f"Pipeline completed successfully for {filename}")
            return v3_result

        except Exception as e:
            self.logger.error(f"Pipeline failed for {filename}: {e}")
            raise

    def run_v1_only(
        self,
        tla_file_path: str,
        skip_existing: bool = True,
    ) -> dict[str, Any]:
        """Run only V1 extraction stage.

        Args:
            tla_file_path: Path to the TLA+ file to process
            skip_existing: Skip if V1 result already exists (default: True)

        Returns:
            V1 result dictionary

        Raises:
            FileNotFoundError: If the TLA+ file doesn't exist
            RuntimeError: If V1 stage fails
        """
        tla_path = Path(tla_file_path)
        if not tla_path.exists():
            raise FileNotFoundError(f"TLA+ file not found: {tla_file_path}")

        filename = tla_path.name

        if skip_existing and self.result_writer.v1_result_exists(filename):
            self.logger.info(f"V1 result already exists for {filename}, loading from cache")
            return self.result_writer.load_v1_result(filename)

        tla_content = tla_path.read_text()
        self.logger.info(f"Running V1 for {filename}")

        return self._run_v1_stage(filename, tla_content)

    def run_v1_v2(
        self,
        tla_file_path: str,
        skip_existing: bool = True,
    ) -> dict[str, Any]:
        """Run V1 and V2 stages.

        Args:
            tla_file_path: Path to the TLA+ file to process
            skip_existing: Skip if V2 result already exists (default: True)

        Returns:
            V2 result dictionary

        Raises:
            FileNotFoundError: If the TLA+ file doesn't exist
            RuntimeError: If any pipeline stage fails
        """
        tla_path = Path(tla_file_path)
        if not tla_path.exists():
            raise FileNotFoundError(f"TLA+ file not found: {tla_file_path}")

        filename = tla_path.name

        if skip_existing and self.result_writer.v2_result_exists(filename):
            self.logger.info(f"V2 result already exists for {filename}, loading from cache")
            return self.result_writer.load_v2_result(filename)

        tla_content = tla_path.read_text()
        self.logger.info(f"Running V1 and V2 for {filename}")

        v1_result = self._run_v1_stage(filename, tla_content)
        v2_result = self._run_v2_stage(filename, tla_content, v1_result)

        return v2_result

    def _run_v1_stage(self, filename: str, tla_content: str) -> dict[str, Any]:
        """Execute V1 stage with error handling and result persistence.

        Args:
            filename: Base name of the TLA+ file
            tla_content: TLA+ file content

        Returns:
            V1 result dictionary

        Raises:
            RuntimeError: If V1 stage fails
        """
        try:
            v1_result = self.orchestrator.run_stage("v1", tla_content)
            self.result_writer.save_v1_result(filename, v1_result)
            return v1_result
        except Exception as e:
            self.logger.error(f"V1 stage failed for {filename}: {e}")
            raise RuntimeError(f"V1 stage failed: {e}") from e

    def _run_v2_stage(
        self,
        filename: str,
        tla_content: str,
        v1_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute V2 stage with error handling and result persistence.

        Args:
            filename: Base name of the TLA+ file
            tla_content: TLA+ file content
            v1_result: Result from V1 stage

        Returns:
            V2 result dictionary

        Raises:
            RuntimeError: If V2 stage fails
        """
        try:
            v2_result = self.orchestrator.run_stage("v2", tla_content, v1_result)
            self.result_writer.save_v2_result(filename, v2_result)
            return v2_result
        except Exception as e:
            self.logger.error(f"V2 stage failed for {filename}: {e}")
            raise RuntimeError(f"V2 stage failed: {e}") from e

    def _run_v3_stage(
        self,
        filename: str,
        tla_content: str,
        v2_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute V3 stage with error handling and result persistence.

        Args:
            filename: Base name of the TLA+ file
            tla_content: TLA+ file content
            v2_result: Result from V2 stage

        Returns:
            V3 result dictionary

        Raises:
            RuntimeError: If V3 stage fails
        """
        try:
            v3_result = self.orchestrator.run_stage("v3", tla_content, v2_result)
            self.result_writer.save_v3_result(filename, v3_result)
            return v3_result
        except Exception as e:
            self.logger.error(f"V3 stage failed for {filename}: {e}")
            raise RuntimeError(f"V3 stage failed: {e}") from e
