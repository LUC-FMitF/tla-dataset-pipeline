"""Utilities for loading and managing TLA+ prompts."""

from pathlib import Path
from typing import Optional

from tladata.logging import get_logger


class PromptLoader:
    """Loads and manages TLA+ prompt templates from files.

    This class provides a modular way to load prompt files, supporting
    multiple versions (V1, V2, V3) and custom prompts.
    """

    def __init__(self, prompts_dir: Optional[str] = None) -> None:
        """Initialize the prompt loader.

        Args:
            prompts_dir: Directory containing prompt files. If None, uses
                        the default prompts directory in the package.

        Raises:
            ValueError: If the prompts directory doesn't exist
        """
        if prompts_dir is None:
            # Use default prompts directory in the package
            self.prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        if not self.prompts_dir.exists():
            raise ValueError(f"Prompts directory not found: {self.prompts_dir}")

        self.logger = get_logger(self.__class__.__name__)
        self._cache: dict[str, str] = {}

    def load_prompt(self, prompt_name: str) -> str:
        """Load a prompt template by name.

        Args:
            prompt_name: Name of the prompt (e.g., 'v1', 'v2', 'v3', 'prompt1', 'prompt2')

        Returns:
            The prompt template content

        Raises:
            FileNotFoundError: If the prompt file doesn't exist
            ValueError: If the prompt file is empty
        """
        # Check cache first
        if prompt_name in self._cache:
            self.logger.debug(f"Loaded prompt from cache: {prompt_name}")
            return self._cache[prompt_name]

        # Try multiple file naming conventions
        possible_names = [
            f"{prompt_name}.md",
            f"{prompt_name}.txt",
            f"prompt_{prompt_name}.md",
            f"prompt_{prompt_name}.txt",
        ]

        content = None
        for filename in possible_names:
            filepath = self.prompts_dir / filename
            if filepath.exists():
                try:
                    content = filepath.read_text()
                    break
                except OSError as e:
                    self.logger.warning(f"Failed to read {filepath}: {e}")
                    continue

        if content is None:
            raise FileNotFoundError(
                f"Prompt '{prompt_name}' not found in {self.prompts_dir}. "
                f"Tried: {', '.join(possible_names)}"
            )

        if not content.strip():
            raise ValueError(f"Prompt file is empty: {prompt_name}")

        # Cache the content
        self._cache[prompt_name] = content
        self.logger.info(f"Loaded prompt: {prompt_name}")

        return content

    def load_v1_prompt(self) -> str:
        """Load the V1 (initial extraction) prompt.

        Returns:
            The V1 prompt template
        """
        return self.load_prompt("prompt1")

    def load_v2_prompt(self) -> str:
        """Load the V2 (verification) prompt.

        Returns:
            The V2 prompt template
        """
        return self.load_prompt("prompt2")

    def load_v3_prompt(self) -> str:
        """Load the V3 (fine-grained division) prompt.

        Returns:
            The V3 prompt template
        """
        return self.load_prompt("prompt3")

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._cache.clear()
        self.logger.debug("Prompt cache cleared")

    def list_available_prompts(self) -> list[str]:
        """List all available prompt files.

        Returns:
            List of prompt file names without extensions
        """
        prompts = set()
        for file in self.prompts_dir.glob("*.md"):
            # Remove extension and common prefixes
            name = file.stem
            if name.startswith("prompt_"):
                name = name[7:]  # Remove "prompt_" prefix
            elif name.startswith("prompt"):
                name = name[6:]  # Remove "prompt" prefix
            prompts.add(name)

        return sorted(list(prompts))
