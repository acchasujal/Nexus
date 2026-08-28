"""backend/app/ai/schemas.py

Provider-agnostic data models and contracts for the NEXUS AI subsystem.
Defines typed request, response, intent, tool, and conversation schemas
compatible with Pydantic v2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

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


# ── GraphRAG Context Engine Data Contracts ────────────────────────────────────

class EntityContext(BaseModel):
    """Compact representation of an entity node retrieved for GraphRAG context."""

    id: str = Field(..., description="Canonical node identifier in the NEXUS graph.")
    label: str = Field(..., description="Human-readable label or display name.")
    entity_type: str = Field(..., description="Category (e.g. Person, Case, Account, Phone, Vehicle).")
    properties: dict[str, Any] = Field(default_factory=dict, description="Salient entity attributes.")
    case_ids: list[str] = Field(default_factory=list, description="Associated investigation cases.")
    is_bridge: bool = Field(default=False, description="Whether this entity is a high-centrality cut-vertex bridge.")
    community_id: str | None = Field(default=None, description="Louvain community or syndicate cluster identifier.")
    evidence_ids: list[str] = Field(default_factory=list, description="Evidence items directly linking this entity.")


class RelationshipContext(BaseModel):
    """Compact representation of a graph relationship connecting two entities."""

    id: str = Field(..., description="Unique edge identifier.")
    source_id: str = Field(..., description="Source node ID.")
    source_label: str = Field(default="", description="Human-readable label of the source node.")
    target_id: str = Field(..., description="Target node ID.")
    target_label: str = Field(default="", description="Human-readable label of the target node.")
    relationship_type: str = Field(..., description="Semantic edge type (e.g. ACCUSED_IN, TRANSFERRED_TO, CALLED).")
    properties: dict[str, Any] = Field(default_factory=dict, description="Salient edge properties.")
    evidence_ids: list[str] = Field(default_factory=list, description="Backing evidence IDs for this relationship.")
    case_ids: list[str] = Field(default_factory=list, description="Case contexts where this relationship holds.")


class PathContext(BaseModel):
    """Represents a multi-hop traversal or chain connecting entities or cases."""

    source_id: str = Field(..., description="Origin node identifier.")
    target_id: str = Field(..., description="Destination node identifier.")
    hops: int = Field(..., description="Number of edges along the path.")
    nodes: list[str] = Field(default_factory=list, description="Ordered node IDs along the path.")
    node_labels: list[str] = Field(default_factory=list, description="Ordered node display labels along the path.")
    edges: list[str] = Field(default_factory=list, description="Ordered edge IDs along the path.")
    evidence_ids: list[str] = Field(default_factory=list, description="All supporting evidence IDs along the path.")
    reasoning_steps: list[str] = Field(default_factory=list, description="Human-readable step descriptions.")


class EvidenceContext(BaseModel):
    """Structured evidence item with forensic provenance and locators."""

    evidence_id: str = Field(..., description="Unique evidence ID.")
    source_type: str = Field(..., description="Source medium (e.g. FIR, CDR, BANK_STATEMENT, SEIZURE_REPORT).")
    source_id: str | None = Field(default=None, description="Underlying case or document source reference.")
    locator: str | None = Field(default=None, description="Forensic document coordinate (e.g. Page 4 Para 2).")
    description: str = Field(default="", description="Summary of the evidence item.")
    excerpt: str = Field(default="", description="Verbatim quote or excerpt from the official record.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Provenance confidence score.")
    extracted_fact: str = Field(default="", description="Deterministic fact statement derived from this item.")
    provenance: dict[str, Any] = Field(default_factory=dict, description="Complete forensic chain-of-custody provenance.")
    related_entity_ids: list[str] = Field(default_factory=list, description="Entities substantiated by this evidence.")
    related_relationship_ids: list[str] = Field(default_factory=list, description="Relationships substantiated by this evidence.")


class PatternContext(BaseModel):
    """Structured suspicious network pattern finding."""

    pattern_id: str = Field(..., description="Unique identifier for the detected pattern.")
    pattern_type: str = Field(..., description="Pattern rule (e.g. circular_repeated_financial_flow, shared_phone_device).")
    severity: str = Field(default="medium", description="Operational triage level (low, medium, high, critical).")
    description: str = Field(default="", description="Human-readable explanation of why this pattern was flagged.")
    participating_entity_ids: list[str] = Field(default_factory=list, description="Entities participating in the pattern.")
    evidence_ids: list[str] = Field(default_factory=list, description="Supporting evidence IDs for the pattern.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Structural statistics (e.g. cycle length, volume).")


class TimelineEventContext(BaseModel):
    """Chronological event record retrieved for temporal context."""

    event_id: str = Field(..., description="Unique event identifier.")
    timestamp: str | None = Field(default=None, description="ISO-8601 timestamp string.")
    event_type: str = Field(..., description="Type of event (e.g. FIR_FILED, TRANSACTION, CALL_BURST).")
    description: str = Field(..., description="Event description.")
    entity_ids: list[str] = Field(default_factory=list, description="Associated entities.")
    evidence_ids: list[str] = Field(default_factory=list, description="Backing evidence IDs.")


class RetrievalMetadata(BaseModel):
    """Execution telemetry for GraphRAG context building."""

    retrieval_strategy: str = Field(..., description="GraphRAG retrieval strategy (e.g. path_focused, case_scoped, financial_trace).")
    query_type: str = Field(..., description="Classified intent (e.g. cross_case_connection, financial_flow, pattern_investigation).")
    retrieved_nodes_count: int = Field(default=0, description="Total nodes retrieved before pruning.")
    retrieved_edges_count: int = Field(default=0, description="Total edges retrieved before pruning.")
    retrieved_evidence_count: int = Field(default=0, description="Total evidence items included.")
    retrieved_patterns_count: int = Field(default=0, description="Total pattern findings included.")
    duration_ms: float = Field(default=0.0, description="Context retrieval and ranking duration in milliseconds.")
    pruned_nodes_count: int = Field(default=0, description="Nodes pruned to meet max_nodes token budget.")
    pruned_edges_count: int = Field(default=0, description="Edges pruned to meet token budget.")
    is_resolved: bool = Field(default=True, description="Whether retrieval operated over resolved or unresolved graph state.")


class InvestigationContext(BaseModel):
    """Comprehensive, compact, evidence-grounded GraphRAG context for LLM ingestion."""

    query: str = Field(..., description="Original user prompt or investigation query.")
    case_ids: list[str] = Field(default_factory=list, description="Salient case identifiers.")
    entity_ids: list[str] = Field(default_factory=list, description="Salient entity identifiers.")
    entities: list[EntityContext] = Field(default_factory=list, description="Retrieved entity records.")
    relationships: list[RelationshipContext] = Field(default_factory=list, description="Retrieved relationship edges.")
    paths: list[PathContext] = Field(default_factory=list, description="Traversed multi-hop connection paths.")
    evidence: list[EvidenceContext] = Field(default_factory=list, description="Authoritative evidence records.")
    patterns: list[PatternContext] = Field(default_factory=list, description="Detected graph patterns.")
    timeline_events: list[TimelineEventContext] = Field(default_factory=list, description="Chronological timeline events.")
    reasoning_path: list[str] = Field(default_factory=list, description="Deterministic step-by-step reasoning lineage.")
    retrieval_metadata: RetrievalMetadata = Field(
        default_factory=lambda: RetrievalMetadata(retrieval_strategy="general", query_type="general"),
        description="Retrieval strategy and performance telemetry.",
    )

    def to_prompt_text(self) -> str:
        """Render the structured investigation context into a compact, markdown-formatted text block for LLM prompts."""
        lines: list[str] = []
        lines.append("=== NEXUS DETERMINISTIC INVESTIGATION CONTEXT ===")
        lines.append(f"Query: {self.query}")
        if self.case_ids:
            lines.append(f"Target Cases: {', '.join(self.case_ids)}")
        if self.entity_ids:
            lines.append(f"Target Entities: {', '.join(self.entity_ids)}")
        lines.append("")

        # 1. Traversal Paths
        if self.paths:
            lines.append("## Connection Paths (Deterministic BFS Traversals):")
            for i, p in enumerate(self.paths, 1):
                path_str = " ➔ ".join(p.node_labels or p.nodes)
                lines.append(f"{i}. {path_str} ({p.hops} hops)")
                if p.reasoning_steps:
                    for step in p.reasoning_steps:
                        lines.append(f"   - {step}")
                if p.evidence_ids:
                    lines.append(f"   Evidence Citations: {', '.join(p.evidence_ids)}")
            lines.append("")

        # 2. Key Entities
        if self.entities:
            lines.append("## Salient Entities:")
            for e in self.entities:
                bridge_tag = " [HIGH-CENTRALITY BRIDGE]" if e.is_bridge else ""
                comm_tag = f" [Cluster: {e.community_id}]" if e.community_id else ""
                props_summary = []
                for k, v in e.properties.items():
                    if k not in ("name", "label", "canonical_label", "full_name") and v:
                        props_summary.append(f"{k}={v}")
                props_str = f" ({', '.join(props_summary[:3])})" if props_summary else ""
                lines.append(f"- **{e.label}** ({e.entity_type}, ID: `{e.id}`){bridge_tag}{comm_tag}{props_str}")
            lines.append("")

        # 3. Verified Relationships
        if self.relationships:
            lines.append("## Verified Graph Relationships:")
            for r in self.relationships:
                ev_str = f" [Evidence: {', '.join(r.evidence_ids)}]" if r.evidence_ids else " [Uncited]"
                lines.append(f"- `{r.source_label or r.source_id}` ──[{r.relationship_type}]──> `{r.target_label or r.target_id}`{ev_str}")
            lines.append("")

        # 4. Detected Patterns
        if self.patterns:
            lines.append("## Detected Criminal Patterns & Structural Findings:")
            for pt in self.patterns:
                ev_str = f" (Evidence: {', '.join(pt.evidence_ids)})" if pt.evidence_ids else ""
                lines.append(f"- **[{pt.severity.upper()}] {pt.pattern_type}**: {pt.description}{ev_str}")
            lines.append("")

        # 5. Authoritative Evidence Lineage
        if self.evidence:
            lines.append("## Authoritative Forensic Evidence Records (Section 63 BSA 2023 Provenance):")
            for ev in self.evidence:
                loc_str = f" (Locator: {ev.locator})" if ev.locator else ""
                lines.append(f"- **[{ev.evidence_id}]** ({ev.source_type}){loc_str}: {ev.description or ev.extracted_fact}")
                if ev.excerpt:
                    lines.append(f"  *Verbatim Excerpt:* \"{ev.excerpt}\"")
            lines.append("")

        # 6. Timeline
        if self.timeline_events:
            lines.append("## Chronological Event Lineage:")
            for te in self.timeline_events:
                ts = f"[{te.timestamp}] " if te.timestamp else ""
                lines.append(f"- {ts}**{te.event_type}**: {te.description}")
            lines.append("")

        lines.append("==================================================")
        return "\n".join(lines)

