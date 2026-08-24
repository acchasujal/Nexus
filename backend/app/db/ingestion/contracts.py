"""Pydantic contracts shared by CSV ingestion adapters."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from backend.app.core.graph.edges import GraphEdge
from backend.app.core.graph.entities import GraphEntityBase, SourceRecord
from backend.app.core.graph.enums import ResolutionStatus


class SourceType(str, Enum):
    """Supported synthetic ingestion sources."""

    FIR = "FIR"
    CDR = "CDR"
    BANK_TXN = "BANK_TXN"
    INTEL_REPORT = "INTEL_REPORT"


class IssueSeverity(str, Enum):
    """Severity assigned to a row-level parse issue."""

    WARNING = "WARNING"
    ERROR = "ERROR"


class ParseIssue(BaseModel):
    """Describes a problem found while parsing one source row."""

    source_type: SourceType
    file_name: str
    row_number: int = Field(ge=1)
    record_id: str
    field_name: str
    code: str
    message: str
    severity: IssueSeverity


class EntityReviewCandidate(BaseModel):
    """Records an explainable candidate match for an incoming entity."""

    incoming_record_id: str
    candidate_node_id: str
    status: ResolutionStatus
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_fields: list[str] = Field(default_factory=list)
    conflicting_fields: list[str] = Field(default_factory=list)
    reason: str = ""
    source_record_ids: list[str] = Field(default_factory=list)
    auto_link_allowed: bool = False
    requires_human_review: bool = True


class IngestionSummary(BaseModel):
    """Counts produced while processing one ingestion batch."""

    received_count: int = 0
    accepted_count: int = 0
    duplicate_count: int = 0
    rejected_count: int = 0
    warning_count: int = 0
    source_record_count: int = 0
    node_created_count: int = 0
    node_reused_count: int = 0
    relationship_created_count: int = 0
    review_required_count: int = 0


class ParsedSourceBundle(BaseModel):
    """Result of parsing source rows, ready for mapping."""

    batch_id: str
    source_type: SourceType
    file_name: str
    source_records: list[SourceRecord] = Field(default_factory=list)
    claims: list[Any] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    issues: list[ParseIssue] = Field(default_factory=list)
    summary: IngestionSummary = Field(default_factory=IngestionSummary)


class IngestionBundle(BaseModel):
    """Complete, database-independent result of one CSV ingestion batch."""

    batch_id: str
    source_type: SourceType
    file_name: str
    source_records: list[SourceRecord] = Field(default_factory=list)
    nodes: list[GraphEntityBase] = Field(default_factory=list)
    relationships: list[GraphEdge] = Field(default_factory=list)
    review_candidates: list[EntityReviewCandidate] = Field(default_factory=list)
    issues: list[ParseIssue] = Field(default_factory=list)
    summary: IngestionSummary = Field(default_factory=IngestionSummary)
