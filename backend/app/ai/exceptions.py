"""backend/app/ai/exceptions.py

Exception hierarchy for the NEXUS AI subsystem.
Provides lightweight, domain-specific exceptions for AI operations,
prompt rendering, intent extraction, tool execution, and validation.
"""

from __future__ import annotations


class AIError(Exception):
    """Base exception for all AI subsystem errors in NEXUS."""

    def __init__(self, message: str = "An error occurred in the AI subsystem.") -> None:
        super().__init__(message)


class PromptError(AIError):
    """Base exception for prompt-related errors."""

    def __init__(self, message: str = "A prompt error occurred.") -> None:
        super().__init__(message)


class PromptRenderError(PromptError):
    """Raised when a prompt template cannot be rendered."""

    def __init__(self, template_name: str, message: str = "Failed to render prompt template.") -> None:
        self.template_name = template_name
        super().__init__(f"[{template_name}] {message}")


class IntentExtractionError(AIError):
    """Raised when structured intent cannot be extracted from user utterance."""

    def __init__(self, message: str = "Failed to extract intent from user query.") -> None:
        super().__init__(message)


class EntityResolutionError(AIError):
    """Raised when entity resolution fails during extraction or linking."""

    def __init__(self, message: str = "Entity resolution failed.") -> None:
        super().__init__(message)
