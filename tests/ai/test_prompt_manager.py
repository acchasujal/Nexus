"""tests/ai/test_prompt_manager.py

Unit tests for backend.app.ai.prompt_manager.PromptManager.
Verifies prompt template loading, schema loading, template rendering,
caching behaviors, helper methods, and error handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.ai.exceptions import PromptError
from backend.app.ai.prompt_manager import PromptManager, PromptType

# ── Prompt Loading Tests ──────────────────────────────────────────────────────

def test_get_prompt_with_prompt_type_enum() -> None:
    # Arrange
    manager = PromptManager()

    # Act
    content = manager.get_prompt(PromptType.SYSTEM)

    # Assert
    assert isinstance(content, str)
    assert len(content.strip()) > 0


def test_get_prompt_with_filename_string() -> None:
    # Arrange
    manager = PromptManager()

    # Act
    content = manager.get_prompt("system_prompt_v1")

    # Assert
    assert isinstance(content, str)
    assert len(content.strip()) > 0


def test_get_prompt_with_txt_extension() -> None:
    # Arrange
    manager = PromptManager()

    # Act
    content = manager.get_prompt("system_prompt_v1.txt")

    # Assert
    assert isinstance(content, str)
    assert len(content.strip()) > 0


def test_get_prompt_cache_returns_identical_result() -> None:
    # Arrange
    manager = PromptManager()

    # Act
    first_load = manager.get_prompt(PromptType.SYSTEM)
    second_load = manager.get_prompt(PromptType.SYSTEM)

    # Assert
    assert first_load == second_load
    assert first_load is second_load


def test_get_prompt_caching_prevents_subsequent_disk_reads(tmp_path: Path) -> None:
    # Arrange
    prompt_file = tmp_path / "custom_prompt_v1.txt"
    prompt_file.write_text("Hello {name}", encoding="utf-8")
    manager = PromptManager(prompts_dir=tmp_path)

    # Act
    first = manager.get_prompt("custom_prompt_v1")
    
    # Overwrite the file on disk to verify second call uses cache instead of disk
    prompt_file.write_text("Modified content", encoding="utf-8")
    second = manager.get_prompt("custom_prompt_v1")

    # Assert
    assert first == "Hello {name}"
    assert second == "Hello {name}"


# ── Prompt Error Tests ────────────────────────────────────────────────────────

def test_get_prompt_missing_file_raises_prompt_error() -> None:
    # Arrange
    manager = PromptManager()

    # Act & Assert
    with pytest.raises(PromptError) as exc_info:
        manager.get_prompt("non_existent_prompt_v99")

    assert "not found" in str(exc_info.value).lower()


# ── Prompt Rendering Tests ───────────────────────────────────────────────────

def test_render_prompt_successfully(tmp_path: Path) -> None:
    # Arrange
    prompt_file = tmp_path / "greeting_prompt.txt"
    prompt_file.write_text("Hello {user_name}, welcome to {system}!", encoding="utf-8")
    manager = PromptManager(prompts_dir=tmp_path)

    # Act
    result = manager.render(
        "greeting_prompt",
        user_name="Officer Davis",
        system="NEXUS",
    )

    # Assert
    assert result == "Hello Officer Davis, welcome to NEXUS!"


def test_render_prompt_missing_placeholder_raises_prompt_error(tmp_path: Path) -> None:
    # Arrange
    prompt_file = tmp_path / "template_prompt.txt"
    prompt_file.write_text("Hello {user_name}, your case is {case_id}.", encoding="utf-8")
    manager = PromptManager(prompts_dir=tmp_path)

    # Act & Assert
    with pytest.raises(PromptError) as exc_info:
        manager.render("template_prompt", user_name="Officer Davis")

    assert "missing required context key" in str(exc_info.value).lower()


# ── Schema Loading Tests ──────────────────────────────────────────────────────

def test_get_schema_valid_schema() -> None:
    # Arrange
    manager = PromptManager()

    # Act
    schema = manager.get_schema("intent_schema")

    # Assert
    assert isinstance(schema, dict)
    assert schema.get("type") == "object"
    assert "properties" in schema


def test_get_schema_with_json_extension() -> None:
    # Arrange
    manager = PromptManager()

    # Act
    schema = manager.get_schema("intent_schema.json")

    # Assert
    assert isinstance(schema, dict)
    assert schema.get("type") == "object"


def test_get_schema_cache_returns_identical_result() -> None:
    # Arrange
    manager = PromptManager()

    # Act
    first_load = manager.get_schema("intent_schema")
    second_load = manager.get_schema("intent_schema")

    # Assert
    assert first_load == second_load
    assert first_load is second_load


def test_get_schema_caching_prevents_subsequent_disk_reads(tmp_path: Path) -> None:
    # Arrange
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    schema_file = schemas_dir / "custom_schema.json"
    schema_file.write_text('{"type": "object", "title": "First"}', encoding="utf-8")
    manager = PromptManager(prompts_dir=tmp_path)

    # Act
    first = manager.get_schema("custom_schema")

    # Overwrite file on disk to verify second call serves cached dictionary
    schema_file.write_text('{"type": "object", "title": "Second"}', encoding="utf-8")
    second = manager.get_schema("custom_schema")

    # Assert
    assert first == {"type": "object", "title": "First"}
    assert second == {"type": "object", "title": "First"}


# ── Schema Error Tests ────────────────────────────────────────────────────────

def test_get_schema_missing_file_raises_prompt_error() -> None:
    # Arrange
    manager = PromptManager()

    # Act & Assert
    with pytest.raises(PromptError) as exc_info:
        manager.get_schema("missing_schema_name")

    assert "not found" in str(exc_info.value).lower()


def test_get_schema_invalid_json_raises_prompt_error(tmp_path: Path) -> None:
    # Arrange
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    schema_file = schemas_dir / "broken_schema.json"
    schema_file.write_text('{"type": "object", missing_quotes: true}', encoding="utf-8")
    manager = PromptManager(prompts_dir=tmp_path)

    # Act & Assert
    with pytest.raises(PromptError) as exc_info:
        manager.get_schema("broken_schema")

    assert "invalid json content" in str(exc_info.value).lower()


def test_get_schema_top_level_list_raises_prompt_error(tmp_path: Path) -> None:
    # Arrange
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    schema_file = schemas_dir / "list_schema.json"
    schema_file.write_text('[{"type": "string"}]', encoding="utf-8")
    manager = PromptManager(prompts_dir=tmp_path)

    # Act & Assert
    with pytest.raises(PromptError) as exc_info:
        manager.get_schema("list_schema")

    assert "must contain a top-level json object" in str(exc_info.value).lower()


# ── Helper Method Tests ───────────────────────────────────────────────────────

def test_normalize_prompt_key() -> None:
    # Act & Assert
    assert PromptManager._normalize_prompt_key(PromptType.SYSTEM) == "system_prompt_v1"
    assert PromptManager._normalize_prompt_key("custom_prompt") == "custom_prompt"
    assert PromptManager._normalize_prompt_key("custom_prompt.txt") == "custom_prompt"


def test_normalize_schema_key() -> None:
    # Act & Assert
    assert PromptManager._normalize_schema_key("intent_schema") == "intent_schema"
    assert PromptManager._normalize_schema_key("intent_schema.json") == "intent_schema"
