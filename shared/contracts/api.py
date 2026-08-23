"""shared/contracts/api.py

Authoritative Python-side API contract types for the NEXUS Criminal Intelligence Platform.
Kept in sync with shared/contracts/api.ts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    INVESTIGATOR = "INVESTIGATOR"
    ANALYST = "ANALYST"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"
    # Legacy aliases for backward compatibility
    IO = "IO"
    SHO = "SHO"
    SP = "SP"


class ResolutionStatus(str, Enum):
    MATCHED = "MATCHED"
    PROBABLE_MATCH = "PROBABLE_MATCH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_MATCHED = "NOT_MATCHED"


class EntityType(str, Enum):
    PERSON = "Person"
    CASE = "Case"
    PHONE = "Phone"
    VEHICLE = "Vehicle"
    LOCATION = "Location"
    ORGANIZATION = "Organization"
    DEVICE = "Device"
    ACCOUNT = "Account"
    TRANSACTION = "Transaction"
    EVENT = "Event"
    INTELLIGENCE_REPORT = "IntelligenceReport"
    EVIDENCE = "Evidence"


# ── Evidence & Provenance ──────────────────────────────────────────────────────

class EvidenceProvenanceContract(BaseModel):
    source_type: str = "DIRECT_RECORD"  # FIR, CDR, BANK_TXN, INTEL_REPORT
    source_id: str = ""
    timestamp: datetime = Field(default_factory=_utcnow)
    extracted_fact: str = ""
    derivation_method: str = "DIRECT"  # DIRECT, CO_OCCURRENCE, CALL_RECORD, FINANCIAL_LEDGER, ENTITY_RESOLUTION
    confidence: float = 1.0


class EvidenceItemResponse(BaseModel):
    id: str
    evidence_number: str
    case_id: str
    evidence_type: str
    description: str
    collected_at: datetime
    storage_location: Optional[str] = None
    provenance: EvidenceProvenanceContract = Field(default_factory=EvidenceProvenanceContract)


# ── Graph & Network ───────────────────────────────────────────────────────────

class GraphNodeResponse(BaseModel):
    id: str
    entity_type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    degree: int = 0
    confidence: float = 1.0


class GraphEdgeResponse(BaseModel):
    id: str
    source_id: str
    target_id: str
    edge_type: str
    weight: float = 1.0
    provenance: EvidenceProvenanceContract = Field(default_factory=EvidenceProvenanceContract)
    properties: dict[str, Any] = Field(default_factory=dict)


class NetworkGraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    total_nodes: int
    total_edges: int


# ── Entity Resolution ─────────────────────────────────────────────────────────

class EntityResolutionQuery(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    vehicle_number: Optional[str] = None
    address_text: Optional[str] = None
    national_id: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    confidence_threshold: float = 0.50
    candidate_limit: int = 10


class EntityResolutionMatchResponse(BaseModel):
    matched_node_id: str
    confidence: float
    status: ResolutionStatus
    matched_fields: list[str]
    reason: str
    evidence_breakdown: dict[str, float] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)


class EntityResolutionResponse(BaseModel):
    query: dict[str, Any]
    matches: list[EntityResolutionMatchResponse]
    total_matches: int


# ── Communities & Centrality ──────────────────────────────────────────────────

class CommunityResponse(BaseModel):
    community_id: str
    size: int
    member_ids: list[str]
    dominant_entity_type: str
    top_influencer_id: str
    reason: str


class BridgeNodeResponse(BaseModel):
    node_id: str
    entity_type: str
    label: str
    connected_components_count: int
    betweenness_score: float
    reason: str


class InfluenceRankingResponse(BaseModel):
    node_id: str
    label: str
    entity_type: str
    degree_centrality: float
    betweenness_centrality: float
    rank: int


# ── Patterns & Timeline ───────────────────────────────────────────────────────

class RepeatOffenderResponse(BaseModel):
    person_id: str
    person_name: str
    case_ids: list[str]
    case_count: int
    reason: str


class SharedClusterResponse(BaseModel):
    cluster_id: str
    cluster_type: str
    person_ids: list[str]
    case_ids: list[str]
    reason: str


class TimelineEventResponse(BaseModel):
    id: str
    event_type: str
    timestamp: datetime
    description: str
    participant_ids: list[str] = Field(default_factory=list)
    location_id: Optional[str] = None
    case_id: Optional[str] = None


# ── Case / Investigation ──────────────────────────────────────────────────────

class InvestigationSummaryResponse(BaseModel):
    id: str
    fir_number: str
    title: str
    station_name: str
    district: str
    offence_category: str
    status: str
    updated_at: datetime
    accused_count: int
    evidence_count: int
    priority_rank: int


class InvestigationDetailResponse(BaseModel):
    id: str
    fir_number: str
    title: str
    station_name: str
    district: str
    offence_category: str
    incident_date: Optional[datetime] = None
    status: str
    summary: str
    sections: list[str] = Field(default_factory=list)
    accused: list[dict[str, Any]] = Field(default_factory=list)
    victims: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceItemResponse] = Field(default_factory=list)
    updated_at: datetime


# ── Copilot & Intent ──────────────────────────────────────────────────────────

class GroundedCitation(BaseModel):
    source_type: str
    source_id: str
    fact: str
    confidence: float


class CopilotQueryRequest(BaseModel):
    query: str
    case_id: Optional[str] = None
    investigation_id: Optional[str] = None
    session_id: Optional[str] = None


class CopilotQueryResponse(BaseModel):
    query: str
    intent: str
    answer: str
    is_refusal: bool = False
    refusal_reason: Optional[str] = None
    grounded_citations: list[GroundedCitation] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    graph_context: Optional[NetworkGraphResponse] = None


# ── Audit & Auth ──────────────────────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    id: str
    user_id: str
    user_role: str
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)


class AuthLoginRequest(BaseModel):
    username: str
    password: Optional[str] = None
    role: Optional[UserRole] = UserRole.INVESTIGATOR


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: UserRole
    expires_in: int = 86400
