"""shared/contracts/api.py

Authoritative Python-side API contract types for the NEXUS Criminal Intelligence Platform.
Kept in sync with shared/contracts/api.ts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

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
    storage_location: str | None = None
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
    full_name: str | None = None
    phone_number: str | None = None
    vehicle_number: str | None = None
    address_text: str | None = None
    national_id: str | None = None
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
    location_id: str | None = None
    case_id: str | None = None


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
    incident_date: datetime | None = None
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
    case_id: str | None = None
    investigation_id: str | None = None
    session_id: str | None = None
    # Entity-centric query parameters (used by Copilot structured dispatch)
    entity_id: str | None = None
    max_hops: int = 2
    is_resolved: bool | None = None


class CopilotQueryResponse(BaseModel):
    query: str
    intent: str
    answer: str
    is_refusal: bool = False
    refusal_reason: str | None = None
    grounded_citations: list[GroundedCitation] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    graph_context: NetworkGraphResponse | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    reasoning_path: list[str] = Field(default_factory=list)
    case_id: str | None = None


# ── Audit & Auth ──────────────────────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    id: str
    user_id: str
    user_role: str
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)


class AuthLoginRequest(BaseModel):
    username: str
    password: str | None = None
    role: UserRole | None = UserRole.INVESTIGATOR


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: UserRole
    expires_in: int = 86400


# ── Entity Profile ────────────────────────────────────────────────────────────

class EntityProfileResponse(BaseModel):
    """Full profile of a graph entity, including evidence and centrality data."""
    entity_id: str
    entity_type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)
    degree: int = 0
    community_id: str | None = None
    betweenness_score: float | None = None
    evidence_items: list[EvidenceItemResponse] = Field(default_factory=list)


# ── Evidence Verification (BE-04) ─────────────────────────────────────────────

class EvidenceVerificationResponse(BaseModel):
    """SHA-256 hash chain verification result for Section 63 BSA 2023 compliance."""
    evidence_hashes: dict[str, str] = Field(default_factory=dict)  # evidence_id -> sha256
    chain_hash: str = ""
    verified_at: datetime = Field(default_factory=_utcnow)
    verification_status: str = "VERIFIED"  # VERIFIED | INCOMPLETE


class EvidenceVerifyRequest(BaseModel):
    """Request body for POST /evidence/verify."""
    evidence_ids: list[str] = Field(default_factory=list)
    path_node_ids: list[str] = Field(default_factory=list)


# ── BSA Dossier Export (BE-05) ────────────────────────────────────────────────

class DossierExportRequest(BaseModel):
    """Request body for POST /export/dossier (Section 63 BSA 2023 workflow)."""
    case_id: str
    include_network: bool = True
    include_evidence: bool = True
    include_hash_chain: bool = True


class DossierExportResponse(BaseModel):
    """Response from POST /export/dossier."""
    case_id: str
    sha256_hash: str
    generated_at: datetime = Field(default_factory=_utcnow)
    page_count: int = 0
    file_size_bytes: int = 0


class NexusDossierRequest(BaseModel):
    """Request for generating an evidence dossier from a case, lead, or evidence list."""
    case_id: str | None = None
    lead_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    include_network: bool = True
    include_evidence: bool = True
    include_hash_chain: bool = True


class NexusDossierResponse(BaseModel):
    """Metadata for a generated evidence dossier with SHA-256 signatures."""
    dossier_id: str
    case_id: str | None = None
    case_ids: list[str] = Field(default_factory=list)
    lead_id: str | None = None
    pdf_sha256: str
    chain_hash: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_hashes: dict[str, str] = Field(default_factory=dict)
    generated_at: str = ""
    page_count: int = 1
    file_size_bytes: int = 0
    download_url: str = ""


class EvidenceIntegrityCheckResult(BaseModel):
    """Integrity verification outcome for an individual evidence artifact."""
    evidence_id: str
    expected_hash: str
    computed_hash: str
    verified: bool
    verification_timestamp: str = ""
    failure_reason: str | None = None


class EvidenceBatchVerifyRequest(BaseModel):
    """Request for verifying the SHA-256 integrity of evidence items."""
    evidence_ids: list[str] = Field(default_factory=list)
    dossier_id: str | None = None


class EvidenceBatchVerifyResponse(BaseModel):
    """Batch integrity verification response for evidence artifacts and hash chains."""
    results: list[EvidenceIntegrityCheckResult] = Field(default_factory=list)
    overall_verified: bool = True
    chain_hash: str = ""
    verified_at: str = ""


class NexusDossierVerificationResponse(BaseModel):
    dossier_id: str
    expected_hash: str
    computed_hash: str
    verified: bool
    verification_timestamp: str



# ── File Ingestion ────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    """[DEPRECATED] Multi-source ingestion request body for POST /ingest."""
    source_type: str  # CDR | BANK_TXN | FIR | INTEL_REPORT
    file_name: str
    records: list[dict[str, Any]] = Field(default_factory=list)


class IngestResponse(BaseModel):
    """[DEPRECATED] Response from POST /ingest."""
    ingested_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    audit_event_id: str = ""


# ── Investigative Leads ───────────────────────────────────────────────────────

class NexusLeadPath(BaseModel):
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)


class NexusLead(BaseModel):
    id: str
    title: str
    rule_id: str
    explanation: str
    severity: str
    review_priority: str = "HIGH"  # HIGH | MEDIUM | LOW
    priority_factors: dict[str, str] = Field(default_factory=dict)
    why_prioritized: list[str] = Field(default_factory=list)
    derivation_class: str = "DERIVED"  # FACT | DERIVED | HYPOTHESIS
    case_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    status: str = "NEW"  # NEW | ACCEPTED | REJECTED
    path: NexusLeadPath = Field(default_factory=NexusLeadPath)
    evidence_ids: list[str] = Field(default_factory=list)
    citations: list[GroundedCitation] = Field(default_factory=list)
    reasoning_path: list[str] = Field(default_factory=list)
    created_at: str = ""
    generation_mode: str = "DETERMINISTIC_FALLBACK"  # REAL_LLM | MOCK_LLM_TEST | DETERMINISTIC_FALLBACK
    lead_type: str | None = None
    decided_at: str | None = None
    decided_by: str | None = None
    decision_note: str | None = None


class NexusLeadDecisionRequest(BaseModel):
    decision: str  # ACCEPT | REJECT
    decided_by: str = "Investigating Officer"
    note: str | None = None

# ── Real Ingestion API ────────────────────────────────────────────────────────

class BatchStatus(str, Enum):
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"


class IngestionFileSummary(BaseModel):
    received: int = 0
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    conflicts: int = 0
    warnings: int = 0
    source_records: int = 0
    nodes_created: int = 0
    nodes_reused: int = 0
    relationships_created: int = 0
    review_required: int = 0


class IngestionFileResult(BaseModel):
    source_type: str
    file_name: str
    size_bytes: int = 0
    summary: IngestionFileSummary = Field(default_factory=IngestionFileSummary)


class IngestionParseIssue(BaseModel):
    source_type: str
    file_name: str
    row_number: int | None = None
    record_id: str | None = None
    field: str | None = None
    code: str
    message: str
    severity: str


class IngestionBatchResponse(BaseModel):
    batch_id: str
    status: BatchStatus
    files_processed: list[IngestionFileResult] = Field(default_factory=list)
    summary: IngestionFileSummary = Field(default_factory=IngestionFileSummary)
    parse_issues: list[IngestionParseIssue] = Field(default_factory=list)
    review_candidates: list[dict[str, Any]] = Field(default_factory=list)
    graph_updated: bool = False


# ── Hotspot Intelligence & Repeat Offender Radar ─────────────────────────────

class DominantCategoryItem(BaseModel):
    category: str
    count: int
    percentage: float


class DistrictHotspotIntelligence(BaseModel):
    district: str
    case_count: int
    baseline_cases: float
    concentration_multiplier: float  # e.g., 3.4
    dominant_categories: list[DominantCategoryItem] = Field(default_factory=list)
    cross_case_links_count: int = 0
    repeat_offender_overlap_count: int = 0
    repeat_offender_ids: list[str] = Field(default_factory=list)
    repeat_offender_names: list[str] = Field(default_factory=list)
    evidence_backed: bool = True
    evidence_ids: list[str] = Field(default_factory=list)
    alert_level: str = "RED"  # RED | AMBER | GREEN
    summary_reason: str = ""


class HotspotCaseItem(BaseModel):
    case_id: str
    fir_number: str
    title: str = ""
    date: str = ""
    crime_head: str = ""
    police_station: str = ""
    sections: list[str] = Field(default_factory=list)
    accused_count: int = 0


class HotspotEntityItem(BaseModel):
    entity_id: str
    name: str
    entity_type: str = "Person"
    case_count: int = 0
    role: str = "Suspect"


class HotspotDrilldownResponse(BaseModel):
    district: str
    case_count: int
    baseline_cases: float
    concentration_multiplier: float
    cases: list[HotspotCaseItem] = Field(default_factory=list)
    entities: list[HotspotEntityItem] = Field(default_factory=list)
    repeat_offenders: list[dict[str, Any]] = Field(default_factory=list)
    cross_case_links: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class SharedNetworkEntity(BaseModel):
    entity_id: str
    label: str
    entity_type: str
    shared_reason: str


class RecentCaseInfo(BaseModel):
    case_id: str
    fir_number: str
    date: str = ""
    district: str = ""
    crime_head: str = ""


class RepeatOffenderRadarItem(BaseModel):
    person_id: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    resolved_person_ids: list[str] = Field(default_factory=list)
    case_count: int = 0
    case_ids: list[str] = Field(default_factory=list)
    fir_numbers: list[str] = Field(default_factory=list)
    districts: list[str] = Field(default_factory=list)
    district_count: int = 0
    shared_network_entities_count: int = 0
    shared_network_entities: list[SharedNetworkEntity] = Field(default_factory=list)
    shared_phone_identifiers: list[str] = Field(default_factory=list)
    most_recent_case: RecentCaseInfo | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    why_surfaced: str = "Deterministic repeat-case + entity-resolution evidence."
    compliance_status: str = "Investigative lead — not a finding of guilt."


class BridgingOffenderDetail(BaseModel):
    person_id: str
    name: str
    home_district: str
    external_districts: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    case_count: int = 0


class ConnectedDistrictInfo(BaseModel):
    district: str
    bridging_offenders: list[str] = Field(default_factory=list)
    case_count: int = 0


class CombinedBridgeSignal(BaseModel):
    signal_id: str
    primary_district: str
    primary_district_cases: int
    repeat_offender_count: int
    connected_districts: list[ConnectedDistrictInfo] = Field(default_factory=list)
    cross_district_bridge_detected: bool = False
    bridging_offender_details: list[BridgingOffenderDetail] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    alert_title: str = "RED FLAG — Cross-District Criminal Network Bridge"
    explanation: str = ""

