"""backend/app/ai/schemas.py

Provider-agnostic data models and contracts for the CaseClock AI subsystem.
Defines typed request, response, intent, tool, and conversation schemas
compatible with Pydantic v2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field
from typing import Literal


# ── Domain & Extraction Entities ──────────────────────────────────────────────

class Entity(BaseModel):
    """Extracted domain entity or parameter from user input."""

    type: str = Field(
        ...,
        description="Category or key identifier for the entity (e.g. 'case_id', 'zone', 'officer_name').",
    )
    value: Any = Field(
        ...,
        description="Extracted value corresponding to the entity.",
    )


class Intent(BaseModel):
    """Structured intent representation extracted by an NLU provider."""

    name: str = Field(
        ...,
        description="Name of the extracted intent (e.g. 'FIND_SIMILAR_CASES', 'GET_HOTSPOTS').",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional confidence score between 0.0 and 1.0.",
    )
    entities: list[Entity] = Field(
        default_factory=list,
        description="List of entities extracted alongside the intent.",
    )


# ── Messaging & Conversation ──────────────────────────────────────────────────

class ChatMessage(BaseModel):
    """A single turn or message within a chat conversation."""

    role: Literal[
        "system",
        "user",
        "assistant",
        "tool",
    ] = Field(
        ...,
        description="Role of the message author: 'system', 'user', 'assistant', or 'tool'.",
    )
    content: str = Field(
        ...,
        description="Text content of the message.",
    )
    name: str | None = Field(
        default=None,
        description="Optional name of the sender or tool.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the message was created.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value metadata attached to this message.",
    )


class ConversationContext(BaseModel):
    """Encapsulates session history, user context, and metadata."""

    conversation_id: str = Field(
        ...,
        description="Unique identifier for the active conversation session.",
    )
    user_id: str | None = Field(
        default=None,
        description="Optional identifier of the user.",
    )
    case_id: str | None = Field(
        default=None,
        description="Optional active case ID for legal context.",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Ordered message history for this conversation session.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Session-wide metadata and dynamic context flags.",
    )


# ── Tool Calling & Function Execution ──────────────────────────────────────────

class ToolCall(BaseModel):
    """Represents a request from an LLM provider to execute a tool/function."""

    name: str = Field(
        ...,
        description="Target function or tool name to execute.",
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments for the tool execution.",
    )
    call_id: str | None = Field(
        default=None,
        description="Optional identifier linking this call to a response.",
    )


class ToolResult(BaseModel):
    """Represents the output of a deterministic tool execution."""

    name: str = Field(
        ...,
        description="Name of the tool that was executed.",
    )
    result: Any = Field(
        default=None,
        description="Payload or return data produced by the tool execution.",
    )
    tool_call_id: str | None = Field(
        default=None,
        description="ID matching the originating ToolCall.",
    )
    error: str | None = Field(
        default=None,
        description="Error description if the tool execution failed.",
    )


# ── Provider-Agnostic LLM Interfaces ─────────────────────────────────────────

class UsageMetadata(BaseModel):
    """Token consumption statistics for an LLM request."""

    prompt_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of tokens in the input prompt.",
    )
    completion_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of tokens in the generated completion.",
    )
    total_tokens: int = Field(
        default=0,
        ge=0,
        description="Total tokens consumed by the operation.",
    )


class LLMRequest(BaseModel):
    """Provider-agnostic inference request."""
    thinking: bool = Field(
        default=False,
        description="Whether to enable provider reasoning/thinking mode.",
    )
    messages: list[ChatMessage] = Field(
        ...,
        description="List of chat messages representing conversation history and prompts.",
    )
    model: str | None = Field(
        default=None,
        description="Optional model identifier override.",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for text generation.",
        
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of completion tokens to generate.",
    )
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional native tool/function definitions available to the LLM.",
    )
    response_format: str | dict[str, Any] | None = Field(
        default=None,
        description="Desired output format (e.g. 'json' or JSON Schema).",
    )
    extra_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific pass-through arguments.",
    )


class LLMResponse(BaseModel):
    """Provider-agnostic inference response."""

    content: str | None = Field(
        default=None,
        description="Generated text response from the LLM provider.",
    )
    tool_calls: list[ToolCall] = Field(
        default_factory=list,
        description="List of tool execution requests generated by the model.",
    )
    usage: UsageMetadata | None = Field(
        default=None,
        description="Token consumption metadata.",
    )
    finish_reason: str | None = Field(
        default=None,
        description="Termination reason (e.g. 'stop', 'tool_calls', 'length').",
    )
    raw_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw unparsed metadata returned by the provider.",
    )


# ── Presentation Layer Contracts ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    """API payload received at POST /chat."""

    message: str = Field(
        ...,
        description="User's natural language input prompt.",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Optional existing conversation session identifier.",
    )
    case_id: str | None = Field(
        default=None,
        description="Optional legal case ID context.",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior conversation history turns.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Client-side metadata attached to the request.",
    )


class ChatResponse(BaseModel):
    """API response returned from POST /chat."""

    message: str = Field(
        ...,
        description="Final assistant response message formatted for the user.",
    )
    conversation_id: str = Field(
        ...,
        description="Active conversation session identifier.",
    )
    intent: Intent | None = Field(
        default=None,
        description="Identified user intent backing the execution.",
    )
    entities: list[Entity] = Field(
        default_factory=list,
        description="Extracted entities used in domain execution.",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Structured deterministic graph or domain payload.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metrics and metadata (e.g. latency, model used).",
    )
