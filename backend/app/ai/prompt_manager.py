"""backend/app/ai/prompt_manager.py

PromptManager is the single source of truth for prompt templates,
JSON schemas, and prompt versioning within the NEXUS AI subsystem.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from backend.app.ai.exceptions import PromptError

# ── Prompt Type Enumeration ───────────────────────────────────────────────────

class PromptType(StrEnum):
    """Enumeration of versioned prompt templates.
    
    Maps logical prompt categories to their corresponding versioned filenames
    without file extensions.
    """

    SYSTEM = "system_prompt_v1"
    INTENT = "intent_prompt_v1"
    SYNTHESIS = "synthesis_prompt_v1"


# ── Prompt Manager Implementation ─────────────────────────────────────────────

class PromptManager:
    """Manages loading, caching, and rendering of prompt templates and JSON schemas."""

    def __init__(self, prompts_dir: Path | str | None = None) -> None:
        """Initialize PromptManager with target directory and private caches.
        
        Args:
            prompts_dir: Optional custom path to prompts directory. Defaults to
                         `backend/app/ai/prompts`.
        """
        if prompts_dir is not None:
            self._prompts_dir = Path(prompts_dir).resolve()
        else:
            self._prompts_dir = (Path(__file__).resolve().parent / "prompts").resolve()

        self._schemas_dir = self._prompts_dir / "schemas"
        self._prompt_cache: dict[str, str] = {}
        self._schema_cache: dict[str, dict[str, Any]] = {}

    def get_prompt(self, prompt_type: PromptType | str) -> str:
        """Retrieves raw prompt template text by prompt type or filename.
        
        Args:
            prompt_type: PromptType enum member or filename string (e.g. 'system_prompt_v1').
            
        Returns:
            Raw string content of the prompt template.
            
        Raises:
            PromptError: If the prompt template file is missing or unreadable.
        """
        key = self._normalize_prompt_key(prompt_type)

        if key in self._prompt_cache:
            return self._prompt_cache[key]

        file_path = self._prompts_dir / f"{key}.txt"

        try:
            content = file_path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise PromptError(f"Prompt template '{key}.txt' not found at '{file_path}'.") from e
        except Exception as e:
            raise PromptError(f"Failed to read prompt template '{key}.txt': {e}") from e

        self._prompt_cache[key] = content
        return content

    def render(self, prompt_type: PromptType | str, **context: Any) -> str:
        """Loads prompt template and formats placeholders with context variables.
        
        Args:
            prompt_type: PromptType enum member or filename string.
            **context: Dynamic context key-value pairs to inject into template placeholders.
            
        Returns:
            Formatted rendered prompt string.
            
        Raises:
            PromptError: If the template is missing, context variables are missing,
                         or rendering fails.
        """
        template = self.get_prompt(prompt_type)

        try:
            return template.format(**context)
        except KeyError as e:
            raise PromptError(
                f"Missing required context key {e} when rendering prompt '{prompt_type}'."
            ) from e
        except (ValueError, IndexError) as e:
            raise PromptError(
                f"Format error rendering prompt '{prompt_type}': {e}"
            ) from e
        except Exception as e:
            raise PromptError(
                f"Unexpected error rendering prompt '{prompt_type}': {e}"
            ) from e

    def get_schema(self, schema_name: str) -> dict[str, Any]:
        """Loads and parses a JSON schema from disk into a Python dictionary.
        
        Args:
            schema_name: Schema filename with or without '.json' extension (e.g. 'intent_schema').
            
        Returns:
            Parsed JSON schema dictionary.
            
        Raises:
            PromptError: If schema file is missing, unreadable, or invalid JSON.
        """
        key = self._normalize_schema_key(schema_name)

        if key in self._schema_cache:
            return self._schema_cache[key]

        schema_path = self._schemas_dir / f"{key}.json"

        try:
            raw_text = schema_path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
        except FileNotFoundError as e:
            raise PromptError(f"JSON schema '{key}.json' not found at '{schema_path}'.") from e
        except json.JSONDecodeError as e:
            raise PromptError(f"Invalid JSON content in schema '{key}.json': {e}") from e
        except Exception as e:
            raise PromptError(f"Failed to load JSON schema '{key}.json': {e}") from e

        if not isinstance(data, dict):
            raise PromptError(
                f"JSON schema '{key}.json' must contain a top-level JSON object."
            ) 

        self._schema_cache[key] = data
        return data

    @staticmethod
    def _normalize_prompt_key(prompt_type: PromptType | str) -> str:
        """Normalizes prompt type or string into a clean filename key without extension."""
        if isinstance(prompt_type, PromptType):
            key = prompt_type.value
        else:
            key = str(prompt_type)
        if key.endswith(".txt"):
            key = key[:-4]
        return key

    @staticmethod
    def _normalize_schema_key(schema_name: str) -> str:
        """Normalizes schema name string into a clean filename key without extension."""
        key = str(schema_name)
        if key.endswith(".json"):
            key = key[:-5]
        return key
