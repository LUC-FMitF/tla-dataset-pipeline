"""Unified orchestrator for iterative TLA+ prompt execution."""

import json
from typing import Any, Optional, cast

from langchain_core.messages import HumanMessage

from tladata.logging import get_logger
from tladata.parsing.prompt_loader import PromptLoader
from tladata.parsing.providers import create_llm


class PromptOrchestrator:
    """Orchestrates execution of iterative TLA+ prompts with injected templates.

    This class manages a sequence of prompts (V1, V2, V3) that progressively
    refine TLA+ specification analysis. Prompts are loaded as dependencies,
    keeping the orchestrator modular and configuration-agnostic.
    """

    VALID_STAGES = {"v1", "v2", "v3"}

    def __init__(
        self,
        model_spec: str = "gpt-4",
        api_key: Optional[str] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            model_spec: Provider-qualified model string (default: gpt-4)
            api_key: API key for providers that require one
            prompt_loader: PromptLoader instance. If None, creates default loader.
        """
        self.model_spec = model_spec
        self.api_key = api_key
        self._llm: Any | None = None
        self.prompt_loader = prompt_loader or PromptLoader()
        self.logger = get_logger(self.__class__.__name__)

    def _get_llm(self) -> Any:
        """Create the chat model lazily so the module can be imported without langchain."""
        if self._llm is None:
            self._llm = create_llm(self.model_spec, self.api_key)
        return self._llm

    def run_stage(
        self,
        stage: str,
        tla_content: str,
        previous_result: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute a single prompt stage.

        Args:
            stage: Pipeline stage ('v1', 'v2', or 'v3')
            tla_content: TLA+ specification content
            previous_result: Result from previous stage (required for v2, v3)

        Returns:
            Parsed result as dictionary

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If LLM call fails
        """
        if stage not in self.VALID_STAGES:
            raise ValueError(f"Invalid stage: {stage}. Must be one of {self.VALID_STAGES}")

        self._validate_tla_content(tla_content)

        # V2 and V3 require previous result
        if stage in {"v2", "v3"} and previous_result is None:
            raise ValueError(f"Stage {stage} requires previous_result from prior stage")

        self.logger.info(f"Running stage {stage.upper()}")

        try:
            if stage == "v1":
                return self._run_v1(tla_content)
            elif stage == "v2":
                v1_result = previous_result
                assert v1_result is not None
                return self._run_v2(tla_content, v1_result)
            else:  # v3
                v2_result = previous_result
                assert v2_result is not None
                return self._run_v3(tla_content, v2_result)
        except Exception as e:
            self.logger.error(f"Stage {stage.upper()} failed: {e}")
            raise RuntimeError(f"Stage {stage.upper()} execution failed: {e}") from e

    def _run_v1(self, tla_content: str) -> dict[str, Any]:
        """Execute V1 (initial extraction) stage.

        Args:
            tla_content: TLA+ specification content

        Returns:
            V1 extraction result
        """
        prompt_text = self.prompt_loader.load_v1_prompt()

        # Construct message: prompt + TLA+ file content
        full_message = (
            f"{prompt_text}\n\n---\n\nHere is the TLA+ file:\n\n```tla\n{tla_content}\n```"
        )

        # Use HumanMessage directly to avoid template parsing
        messages = [HumanMessage(content=full_message)]
        response = self._get_llm().invoke(messages)
        result = self._parse_json_response(response.content)

        self.logger.info("V1 extraction completed successfully")
        return result

    def _run_v2(self, tla_content: str, v1_result: dict[str, Any]) -> dict[str, Any]:
        """Execute V2 (verification and refinement) stage.

        Args:
            tla_content: TLA+ specification content
            v1_result: Result from V1 stage

        Returns:
            V2 refined result
        """
        prompt_text = self.prompt_loader.load_v2_prompt()

        # Construct message: prompt + TLA+ file + V1 result
        v1_json = json.dumps(v1_result, indent=2)
        full_message = f"{prompt_text}\n\n---\n\nOriginal TLA+ file:\n\n```tla\n{tla_content}\n```\n\nV1 JSON extraction:\n\n```json\n{v1_json}\n```"

        # Use HumanMessage directly to avoid template parsing
        messages = [HumanMessage(content=full_message)]
        response = self._get_llm().invoke(messages)
        result = self._parse_json_response(response.content)

        # Extract changelog if present
        if "CHANGE LOG" in response.content:
            changelog_idx = response.content.find("CHANGE LOG")
            result["_changelog"] = response.content[changelog_idx:]

        self.logger.info("V2 verification completed successfully")
        return result

    def _run_v3(self, tla_content: str, v2_result: dict[str, Any]) -> dict[str, Any]:
        """Execute V3 (fine-grained division) stage.

        Args:
            tla_content: TLA+ specification content
            v2_result: Result from V2 stage

        Returns:
            V3 augmented result
        """
        prompt_text = self.prompt_loader.load_v3_prompt()

        # Construct message: prompt + TLA+ file + V2 result
        v2_json = json.dumps(v2_result, indent=2)
        full_message = f"{prompt_text}\n\n---\n\nOriginal TLA+ file:\n\n```tla\n{tla_content}\n```\n\nV2 JSON from verification:\n\n```json\n{v2_json}\n```"

        # Use HumanMessage directly to avoid template parsing
        messages = [HumanMessage(content=full_message)]
        response = self._get_llm().invoke(messages)
        result = self._parse_json_response(response.content)

        self.logger.info("V3 fine-grained division completed successfully")
        return result

    def _sanitize_json_string(self, json_str: str) -> str:
        """Sanitize JSON string by escaping unescaped control characters.

        Args:
            json_str: Raw JSON string that may contain unescaped control chars

        Returns:
            Sanitized JSON string with properly escaped control characters
        """
        # Replace literal control characters with their escaped versions
        # Process the string character by character, handling strings properly
        result = []
        in_string = False
        escape_next = False
        i = 0

        while i < len(json_str):
            char = json_str[i]

            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue

            if char == "\\" and in_string:
                result.append(char)
                escape_next = True
                i += 1
                continue

            if char == '"' and not escape_next:
                result.append(char)
                in_string = not in_string
                i += 1
                continue

            # Inside strings, escape control characters
            if in_string:
                if char == "\n":
                    result.append("\\n")
                elif char == "\r":
                    result.append("\\r")
                elif char == "\t":
                    result.append("\\t")
                elif char == "\b":
                    result.append("\\b")
                elif char == "\f":
                    result.append("\\f")
                elif ord(char) < 32:  # Other control characters
                    result.append(f"\\u{ord(char):04x}")
                else:
                    result.append(char)
            else:
                result.append(char)

            i += 1

        return "".join(result)

    def _parse_json_response(self, response_text: str) -> dict[str, Any]:
        """Parse JSON from LLM response.

        Args:
            response_text: Raw response text from LLM

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If response doesn't contain valid JSON
        """
        try:
            # Extract JSON from response (may have surrounding text)
            json_start = response_text.find("{")

            if json_start == -1:
                # No JSON found - log the actual response for debugging
                self.logger.error(f"LLM response (first 500 chars): {response_text[:500]}")
                raise ValueError("No JSON object found in response")

            # Find the end of the first complete JSON object by counting braces
            brace_count = 0
            json_end = json_start
            in_string = False
            escape_next = False

            for i in range(json_start, len(response_text)):
                char = response_text[i]

                # Handle escape sequences in strings
                if escape_next:
                    escape_next = False
                    continue

                if char == "\\" and in_string:
                    escape_next = True
                    continue

                # Toggle string state on unescaped quotes
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                # Only count braces outside of strings
                if not in_string:
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

            if brace_count != 0:
                self.logger.error(
                    f"Unmatched braces in JSON. LLM response (first 500 chars): {response_text[:500]}"
                )
                raise ValueError("Unmatched braces in JSON object")

            json_str = response_text[json_start:json_end]

            # Sanitize control characters before parsing
            json_str = self._sanitize_json_string(json_str)

            return cast(dict[str, Any], json.loads(json_str))
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from LLM response: {e}")
            self.logger.error(
                f"Extracted JSON attempt (first 500 chars): {json_str[:500] if 'json_str' in locals() else 'N/A'}"
            )
            raise ValueError(f"Invalid JSON in LLM response: {e}") from e

    def _validate_tla_content(self, content: str) -> None:
        """Validate TLA+ content.

        Args:
            content: Content to validate

        Raises:
            ValueError: If content is empty
        """
        if not content or not content.strip():
            raise ValueError("TLA+ content cannot be empty")
