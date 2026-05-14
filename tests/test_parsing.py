"""Tests for TLA+ parsing module."""

import json
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from tladata.parsing import (
    PromptLoader,
    PromptOrchestrator,
    PromptPipeline,
    PromptResultWriter,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def api_key() -> str:
    """Provide test API key."""
    return "sk-test-key-123"


@pytest.fixture
def temp_output_dir() -> Generator[str, None, None]:
    """Create temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_tla_content() -> str:
    """Provide sample TLA+ content."""
    return """---- MODULE Example ----
EXTENDS Naturals, FiniteSets

CONSTANT N, T

VARIABLE pc, x

vars == <<pc, x>>

Init == pc = "init" /\\ x = 0

Next == pc' = "done" /\\ x' = x + 1

Spec == Init /\\ [][Next]_vars

TypeOK == pc \\in {"init", "done"} /\\ x \\in Nat

===="""


@pytest.fixture
def sample_v1_result() -> dict:
    """Provide sample V1 result."""
    return {
        "id": None,
        "Specification": "Test specification",
        "ModuleName": "Example",
        "ExtendsModules": ["Naturals", "FiniteSets"],
        "InstanceModules": [],
        "InstanceSubstitutions": [],
        "ConstantNames": ["N", "T"],
        "VariableNames": ["pc", "x"],
        "AssumptionNames": [],
        "TheoremNames": [],
        "OperatorDefNames": ["vars", "Init", "Next", "Spec", "TypeOK"],
        "ActionDefNames": ["Next"],
        "RecursiveOperatorNames": [],
        "LocalOperatorNames": [],
        "LetInNames": [],
        "LambdaParams": [],
        "Implication": ["=>"],
        "Negation": [],
        "BooleanConstants": [],
        "Quantifiers": [],
        "EqualityOps": ["="],
        "MembershipOps": ["\\in"],
        "IfThenElse": [],
        "CaseExpr": [],
        "SetEnumeration": [],
        "SetOperators": [],
        "FiniteSetOps": [],
        "FunctionConstructor": [],
        "FunctionApplication": [],
        "FunctionOverride": [],
        "RecordConstructor": [],
        "RecordAccess": [],
        "TupleConstructor": ["<< pc, x >>"],
        "SequenceOps": [],
        "ArithmeticOps": ["+"],
        "ComparisonOps": [],
        "RangeExpr": [],
        "ChoiceExpr": [],
        "StringLiterals": ["init", "done"],
        "ArithmeticModules": ["Naturals"],
        "DataStructureModules": ["FiniteSets"],
        "ToolingModules": [],
        "PrimedVariables": ["pc", "x"],
        "UnchangedExprs": ["UNCHANGED vars"],
        "EnabledExprs": [],
        "TemporalSubscript": ["[][Next]_vars"],
        "AlwaysOp": ["[][Next]_vars"],
        "EventuallyOp": [],
        "LeadsToOp": [],
        "GuaranteesOp": [],
        "ActionComposition": [],
        "FairnessConditions": [],
        "ProofHints": [],
        "ProofCommands": [],
        "ProofStructureSteps": [],
        "AssumeProveBlocks": [],
        "PlusCalAlgorithm": [],
        "PlusCalProcesses": [],
        "ModelValues": [],
        "OperatorOverrides": [],
        "SymmetrySet": [],
        "StateConstraint": [],
        "ActionConstraint": [],
        "ViewExpr": [],
        "ComplexityTier": "basic",
    }


# ============================================================================
# PromptResultWriter Tests
# ============================================================================


class TestPromptResultWriter:
    """Tests for PromptResultWriter."""

    def test_init_creates_directory(self, temp_output_dir: str) -> None:
        """Test that init creates output directory."""
        PromptResultWriter(temp_output_dir)
        assert Path(temp_output_dir).exists()

    def test_init_fails_with_empty_dir(self) -> None:
        """Test that init fails with empty directory."""
        with pytest.raises(ValueError, match="Output directory cannot be empty"):
            PromptResultWriter("")

    def test_save_v1_result(self, temp_output_dir: str, sample_v1_result: dict) -> None:
        """Test saving V1 result."""
        writer = PromptResultWriter(temp_output_dir)
        path = writer.save_v1_result("test.tla", sample_v1_result)

        assert path.exists()
        assert path.name == "test_v1.json"

    def test_save_v2_result(self, temp_output_dir: str, sample_v1_result: dict) -> None:
        """Test saving V2 result."""
        writer = PromptResultWriter(temp_output_dir)
        path = writer.save_v2_result("test.tla", sample_v1_result)

        assert path.exists()
        assert path.name == "test_v2.json"

    def test_save_v3_result(self, temp_output_dir: str, sample_v1_result: dict) -> None:
        """Test saving V3 result."""
        writer = PromptResultWriter(temp_output_dir)
        path = writer.save_v3_result("test.tla", sample_v1_result)

        assert path.exists()
        assert path.name == "test_v3.json"

    def test_load_v1_result(self, temp_output_dir: str, sample_v1_result: dict) -> None:
        """Test loading V1 result."""
        writer = PromptResultWriter(temp_output_dir)
        writer.save_v1_result("test.tla", sample_v1_result)

        loaded = writer.load_v1_result("test.tla")
        assert loaded["ModuleName"] == sample_v1_result["ModuleName"]

    def test_v1_result_exists(self, temp_output_dir: str, sample_v1_result: dict) -> None:
        """Test checking if V1 result exists."""
        writer = PromptResultWriter(temp_output_dir)

        assert not writer.v1_result_exists("test.tla")
        writer.save_v1_result("test.tla", sample_v1_result)
        assert writer.v1_result_exists("test.tla")

    def test_save_invalid_result(self, temp_output_dir: str) -> None:
        """Test that saving invalid result raises error."""
        writer = PromptResultWriter(temp_output_dir)

        with pytest.raises(ValueError, match="Result must be a dictionary"):
            writer.save_v1_result("test.tla", "not a dict")

    def test_load_nonexistent_result(self, temp_output_dir: str) -> None:
        """Test that loading nonexistent result raises error."""
        writer = PromptResultWriter(temp_output_dir)

        with pytest.raises(FileNotFoundError):
            writer.load_v1_result("nonexistent.tla")


# ============================================================================
# PromptOrchestrator Tests
# ============================================================================


class TestPromptOrchestrator:
    """Tests for PromptOrchestrator."""

    def test_init_with_valid_key(self, api_key: str) -> None:
        """Test initialization with valid API key."""
        orchestrator = PromptOrchestrator(api_key)
        assert orchestrator.api_key == api_key
        assert orchestrator.model_name == "gpt-4"

    def test_init_with_empty_key(self) -> None:
        """Test that init fails with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            PromptOrchestrator("")

    def test_init_with_custom_prompt_loader(self, api_key: str, temp_output_dir: str) -> None:
        """Test initialization with custom prompt loader."""
        loader = PromptLoader(temp_output_dir)
        orchestrator = PromptOrchestrator(api_key, prompt_loader=loader)
        assert orchestrator.prompt_loader is loader

    def test_validate_tla_content(self, api_key: str, sample_tla_content: str) -> None:
        """Test TLA+ content validation."""
        orchestrator = PromptOrchestrator(api_key)

        # Should not raise
        orchestrator._validate_tla_content(sample_tla_content)

        # Should raise on empty
        with pytest.raises(ValueError, match=r"TLA\+ content cannot be empty"):
            orchestrator._validate_tla_content("")

    def test_invalid_stage(self, api_key: str, sample_tla_content: str) -> None:
        """Test that invalid stage raises error."""
        orchestrator = PromptOrchestrator(api_key)

        with pytest.raises(ValueError, match="Invalid stage"):
            orchestrator.run_stage("v4", sample_tla_content)

    def test_v2_requires_previous_result(self, api_key: str, sample_tla_content: str) -> None:
        """Test that V2 requires V1 result."""
        orchestrator = PromptOrchestrator(api_key)

        with pytest.raises(ValueError, match="requires previous_result"):
            orchestrator.run_stage("v2", sample_tla_content, None)

    def test_v3_requires_previous_result(self, api_key: str, sample_tla_content: str) -> None:
        """Test that V3 requires V2 result."""
        orchestrator = PromptOrchestrator(api_key)

        with pytest.raises(ValueError, match="requires previous_result"):
            orchestrator.run_stage("v3", sample_tla_content, None)

    def test_parse_json_response_with_trailing_text(self, api_key: str) -> None:
        """Test that JSON parsing handles LLM responses with trailing text (like changelogs).
        
        This tests the fix for the "Extra data" error that occurred when LLM responses
        included content after the JSON object (e.g., CHANGE LOG sections).
        """
        orchestrator = PromptOrchestrator(api_key)
        
        # Simulate an LLM response with JSON followed by a changelog
        json_content = {"id": "test", "specification": "x := 0", "variables": ["x"]}
        response_text = f"""{json.dumps(json_content)}

CHANGE LOG:
- Fixed parsing logic
- Improved error handling
- Added validation"""
        
        # Should extract just the JSON without the changelog
        result = orchestrator._parse_json_response(response_text)
        assert result == json_content

    def test_parse_json_response_with_nested_objects(self, api_key: str) -> None:
        """Test JSON parsing with nested objects and arrays."""
        orchestrator = PromptOrchestrator(api_key)
        
        json_content = {
            "id": "test",
            "nested": {"key": "value", "array": [1, 2, 3]},
            "specs": [{"name": "spec1"}, {"name": "spec2"}]
        }
        response_text = f"Here is the JSON:\n{json.dumps(json_content)}\n\nAdditional notes follow."
        
        result = orchestrator._parse_json_response(response_text)
        assert result == json_content

    def test_parse_json_response_with_escaped_strings(self, api_key: str) -> None:
        """Test JSON parsing handles escaped quotes in strings correctly."""
        orchestrator = PromptOrchestrator(api_key)
        
        json_content = {
            "id": "test",
            "text": 'This has "escaped" quotes and a brace } inside',
            "formula": "x = {1, 2, 3}"
        }
        response_text = json.dumps(json_content) + "\n\nExtra text with } braces"
        
        result = orchestrator._parse_json_response(response_text)
        assert result == json_content
        assert "escaped" in result["text"]
        assert "}" in result["formula"]

    def test_parse_json_with_unescaped_control_characters(self, api_key: str) -> None:
        """Test JSON parsing handles unescaped control characters in LLM response.
        
        This tests the fix for "Invalid control character" errors that occur when
        LLM responses contain literal newlines/tabs in JSON strings instead of
        properly escaped ones.
        """
        orchestrator = PromptOrchestrator(api_key)
        
        # Simulate a JSON with literal control characters (as LLM would produce)
        json_content = {"id": "test", "text": "Line 1\nLine 2\tTabbed"}
        response_text = '{"id": "test", "text": "Line 1\nLine 2\tTabbed"}\n\nExtra notes'
        
        # Should successfully parse after sanitizing control characters
        result = orchestrator._parse_json_response(response_text)
        assert result == json_content
        assert result["text"] == "Line 1\nLine 2\tTabbed"

    def test_sanitize_json_string_basic(self, api_key: str) -> None:
        """Test _sanitize_json_string with basic control characters."""
        orchestrator = PromptOrchestrator(api_key)
        
        # JSON with literal newline and tab inside string
        dirty_json = '{"text": "line1\nline2\ttab"}'
        clean_json = orchestrator._sanitize_json_string(dirty_json)
        
        # Should be able to parse after sanitization
        result = json.loads(clean_json)
        assert result["text"] == "line1\nline2\ttab"

    def test_sanitize_json_preserves_escaped_sequences(self, api_key: str) -> None:
        """Test that sanitization doesn't double-escape already escaped sequences."""
        orchestrator = PromptOrchestrator(api_key)
        
        # JSON with already-escaped sequences
        already_escaped = '{"text": "line1\\nline2\\ttab"}'
        sanitized = orchestrator._sanitize_json_string(already_escaped)
        
        # Should preserve the escaping
        result = json.loads(sanitized)
        assert result["text"] == "line1\nline2\ttab"

    def test_sanitize_json_with_carriage_returns(self, api_key: str) -> None:
        """Test sanitization of carriage return characters."""
        orchestrator = PromptOrchestrator(api_key)
        
        # JSON with literal carriage return
        dirty_json = '{"text": "line1\rline2"}'
        clean_json = orchestrator._sanitize_json_string(dirty_json)
        
        result = json.loads(clean_json)
        assert result["text"] == "line1\rline2"


# ============================================================================
# PromptLoader Tests
# ============================================================================


class TestPromptLoader:
    """Tests for PromptLoader."""

    def test_init_with_default_dir(self) -> None:
        """Test initialization with default directory."""
        loader = PromptLoader()
        # Should not raise - uses package default
        assert loader.prompts_dir.exists()

    def test_init_with_invalid_dir(self) -> None:
        """Test that init fails with nonexistent directory."""
        with pytest.raises(ValueError, match="Prompts directory not found"):
            PromptLoader("/nonexistent/path")

    def test_list_available_prompts(self) -> None:
        """Test listing available prompts."""
        loader = PromptLoader()
        prompts = loader.list_available_prompts()
        # Should have at least the default prompts
        assert len(prompts) > 0

    def test_clear_cache(self) -> None:
        """Test clearing the cache."""
        loader = PromptLoader()
        loader._cache["test"] = "content"
        loader.clear_cache()
        assert len(loader._cache) == 0


# ============================================================================
# PromptPipeline Tests
# ============================================================================


class TestPromptPipeline:
    """Tests for PromptPipeline."""

    def test_init_with_valid_params(self, api_key: str, temp_output_dir: str) -> None:
        """Test pipeline initialization."""
        pipeline = PromptPipeline(api_key, temp_output_dir)
        assert pipeline.api_key == api_key
        assert pipeline.model_name == "gpt-4"

    def test_init_fails_with_empty_key(self, temp_output_dir: str) -> None:
        """Test that init fails with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            PromptPipeline("", temp_output_dir)

    def test_init_fails_with_empty_output_dir(self, api_key: str) -> None:
        """Test that init fails with empty output dir."""
        with pytest.raises(ValueError, match="Output directory cannot be empty"):
            PromptPipeline(api_key, "")

    def test_run_full_pipeline_nonexistent_file(self, api_key: str, temp_output_dir: str) -> None:
        """Test that pipeline fails with nonexistent file."""
        pipeline = PromptPipeline(api_key, temp_output_dir)

        with pytest.raises(FileNotFoundError):
            pipeline.run_full_pipeline("nonexistent.tla")


# ============================================================================
# ParsingHandler Tests
# ============================================================================


class TestParsingHandler:
    """Tests for ParsingHandler."""

    def test_handler_import(self) -> None:
        """Test that ParsingHandler can be imported."""
        from tladata.parsing.parsing_handler import ParsingHandler

        handler = ParsingHandler()
        assert handler is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for the parsing module."""

    def test_result_writer_roundtrip(self, temp_output_dir: str, sample_v1_result: dict) -> None:
        """Test saving and loading results."""
        writer = PromptResultWriter(temp_output_dir)

        # Save
        writer.save_v1_result("test.tla", sample_v1_result)
        writer.save_v2_result("test.tla", sample_v1_result)
        writer.save_v3_result("test.tla", sample_v1_result)

        # Load and verify
        v1 = writer.load_v1_result("test.tla")
        v2 = writer.load_v2_result("test.tla")
        v3 = writer.load_v3_result("test.tla")

        assert v1["ModuleName"] == sample_v1_result["ModuleName"]
        assert v2["ModuleName"] == sample_v1_result["ModuleName"]
        assert v3["ModuleName"] == sample_v1_result["ModuleName"]

    def test_multiple_files(self, temp_output_dir: str, sample_v1_result: dict) -> None:
        """Test handling multiple files."""
        writer = PromptResultWriter(temp_output_dir)

        # Save results for multiple files
        for i in range(3):
            filename = f"spec{i}.tla"
            result = sample_v1_result.copy()
            result["ModuleName"] = f"Module{i}"
            writer.save_v1_result(filename, result)

        # Verify all files exist
        assert writer.v1_result_exists("spec0.tla")
        assert writer.v1_result_exists("spec1.tla")
        assert writer.v1_result_exists("spec2.tla")
