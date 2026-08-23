"""backend/app/ai/exceptions.py

Exception hierarchy for the CaseClock AI subsystem.
Provides lightweight, domain-specific exceptions for QuickML client operations,
prompt rendering, intent extraction, tool execution, and validation.
"""

from __future__ import annotations


class AIError(Exception):
    pass
    """Base exception for all AI subsystem errors in CaseClock."""

    def __init__(self, message: str = "An error occurred in the AI subsystem.") -> None:
        super().__init__(message)
        


# ── QuickML Infrastructure Exceptions ─────────────────────────────────────────

class QuickMLError(AIError):
    """Base exception for QuickML client and API operations."""

    def __init__(self, message: str = "QuickML provider operation failed.") -> None:
        super().__init__(message)


class QuickMLAuthError(QuickMLError):
    """Raised when QuickML authentication or OAuth token acquisition fails."""

    def __init__(self, message: str = "QuickML authentication failed.") -> None:
        super().__init__(message)


class QuickMLConfigurationError(QuickMLAuthError):
    """Raised when server-side QuickML/OAuth configuration is incomplete."""

    def __init__(self, message: str = "QuickML provider is not configured.") -> None:
        super().__init__(message)


class QuickMLConnectionError(QuickMLError):
    """Raised when network connection to QuickML endpoint fails."""

    def __init__(self, message: str = "Failed to connect to QuickML API endpoint.") -> None:
        super().__init__(message)


class QuickMLTimeoutError(QuickMLError):
    """Raised when a QuickML API request times out."""

    def __init__(self, message: str = "QuickML API request timed out.") -> None:
        super().__init__(message)


class QuickMLRateLimitError(QuickMLError):
    """Raised when QuickML API rate limit (HTTP 429) is exceeded."""

    def __init__(self, message: str = "QuickML API rate limit exceeded.") -> None:
        super().__init__(message)


class QuickMLResponseError(QuickMLError):
    """Raised when QuickML API returns an unexpected HTTP status or payload."""

    def __init__(
        self,
        message: str = "QuickML API returned an unexpected response.",
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


# ── Application Layer Exceptions ──────────────────────────────────────────────

class PromptError(AIError):
    """Raised when prompt template loading, rendering, or formatting fails."""

    def __init__(self, message: str = "Prompt template operation failed.") -> None:
        super().__init__(message)


class IntentExtractionError(AIError):
    """Raised when intent extraction or JSON schema validation fails."""

    def __init__(self, message: str = "Failed to extract structured intent.") -> None:
        super().__init__(message)


class ToolExecutionError(AIError):
    """Raised when a deterministic tool execution fails."""

    def __init__(
        self,
        message: str = "Tool execution failed.",
        tool_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.tool_name = tool_name


class MissingEntityError(ToolExecutionError):
    """Raised when an intent requires a mandatory entity that was not provided."""

    def __init__(
        self,
        message: str = "A required entity for this intent was missing.",
        entity_type: str = "case_id",
        intent_name: str | None = None,
    ) -> None:
        super().__init__(message, tool_name=intent_name)
        self.entity_type = entity_type
        self.intent_name = intent_name



class AIValidationError(AIError):
    """Raised when AI subsystem request/response validation fails."""

    def __init__(self, message: str = "Validation error in AI payload.") -> None:
        super().__init__(message)
