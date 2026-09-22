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


# ── Canonical Constants ────────────────────────────────────────────────────────
CANONICAL_DATASET_VERSION: str = "NCRB_CALIBRATED:v1"
CANONICAL_SNAPSHOT_BASELINE: str = "snap-baseline-v1"
CANONICAL_SNAPSHOT_CURRENT: str = "snap-current"


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


# ── Unstructured Document Ingestion (P1-A) ──────────────────────────────────

class DocumentSourceType(str, Enum):
    FIR_DOCUMENT = "FIR_DOCUMENT"
    POLICE_REPORT = "POLICE_REPORT"
    INTELLIGENCE_DOCUMENT = "INTELLIGENCE_DOCUMENT"
    OTHER_DOCUMENT = "OTHER_DOCUMENT"


class ExtractionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EMPTY = "EMPTY"


class DocumentExtractionMetadata(BaseModel):
    page_count: int = 0
    character_count: int = 0
    word_count: int = 0
    extraction_method: str = "deterministic"
    error_message: str | None = None


class DocumentResponse(BaseModel):
    document_id: str
    original_filename: str
    source_type: str
    mime_type: str
    content_hash: str  # Deterministic SHA-256 tamper-evident fingerprint
    uploaded_by: str
    uploaded_at: datetime
    case_id: str | None = None
    extraction_status: ExtractionStatus
    extraction_metadata: DocumentExtractionMetadata = Field(default_factory=DocumentExtractionMetadata)
    provenance: EvidenceProvenanceContract = Field(default_factory=EvidenceProvenanceContract)


class DocumentTextResponse(BaseModel):
    document_id: str
    content_hash: str
    extracted_text: str
    extraction_status: ExtractionStatus
    extraction_metadata: DocumentExtractionMetadata = Field(default_factory=DocumentExtractionMetadata)


# ── Candidate Intelligence & Entity Extraction (P1-B) ────────────────────────

class CandidateEntityType(str, Enum):
    PERSON = "PERSON"
    PHONE = "PHONE"
    ACCOUNT = "ACCOUNT"
    VEHICLE = "VEHICLE"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    DEVICE = "DEVICE"
    DATE_TIME = "DATE_TIME"
    EVENT = "EVENT"


class CandidateResolutionStatus(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_MATCH_FOUND = "NO_MATCH_FOUND"


class SourceSpan(BaseModel):
    start: int
    end: int
    page: int | None = None


class CandidateProvenance(BaseModel):
    document_id: str
    document_sha256: str
    page: int | None = None
    source_text_hash: str
    case_id: str | None = None


class ResolutionCandidateMatch(BaseModel):
    canonical_entity_id: str
    canonical_name: str
    entity_type: str
    match_score: float
    match_reasons: list[str] = Field(default_factory=list)


class CandidateEntity(BaseModel):
    candidate_id: str
    entity_type: str
    surface_text: str
    normalized_value: str
    confidence: float
    source_document_id: str
    case_id: str | None = None
    source_span: SourceSpan
    evidence_text: str
    extraction_method: str = "DETERMINISTIC"  # DETERMINISTIC | LLM_ASSISTED
    provenance: CandidateProvenance
    resolution_status: CandidateResolutionStatus = CandidateResolutionStatus.UNRESOLVED
    resolution_candidates: list[ResolutionCandidateMatch] = Field(default_factory=list)
    status: str = "PENDING"  # PENDING | ACCEPTED_EXISTING_ENTITY | ACCEPTED_NEW_ENTITY | REJECTED
    resulting_graph_id: str | None = None


class CandidateRelationship(BaseModel):
    candidate_relationship_id: str
    source_candidate_id: str
    target_candidate_id: str
    source_text: str
    target_text: str
    relationship_type: str
    confidence: float
    evidence_text: str
    source_document_id: str
    case_id: str | None = None
    source_span: SourceSpan | None = None
    provenance: CandidateProvenance
    status: str = "CANDIDATE"  # CANDIDATE | ACCEPTED | REJECTED
    resulting_edge_id: str | None = None


class DocumentExtractionResult(BaseModel):
    document_id: str
    case_id: str | None = None
    content_hash: str
    extraction_run_id: str
    extracted_at: datetime = Field(default_factory=_utcnow)
    candidate_entities: list[CandidateEntity] = Field(default_factory=list)
    candidate_relationships: list[CandidateRelationship] = Field(default_factory=list)
    entity_count: int = 0
    relationship_count: int = 0
    status: str = "COMPLETED"
    extraction_notes: list[str] = Field(default_factory=list)


# ── Investigator Confirmation & Graph Promotion (P1-C) ─────────────────────

class CandidateDecisionAction(str, Enum):
    ACCEPT_EXISTING = "ACCEPT_EXISTING"
    ACCEPT_NEW = "ACCEPT_NEW"
    ACCEPT_RELATIONSHIP = "ACCEPT_RELATIONSHIP"
    REJECT = "REJECT"


class CandidateDecisionStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED_EXISTING_ENTITY = "ACCEPTED_EXISTING_ENTITY"
    ACCEPTED_NEW_ENTITY = "ACCEPTED_NEW_ENTITY"
    ACCEPTED_RELATIONSHIP = "ACCEPTED_RELATIONSHIP"
    REJECTED = "REJECTED"


class AcceptExistingEntityRequest(BaseModel):
    target_canonical_id: str
    case_id: str | None = None
    notes: str | None = None


class AcceptNewEntityRequest(BaseModel):
    entity_type: str
    canonical_name: str
    case_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class AcceptRelationshipRequest(BaseModel):
    source_canonical_id: str
    target_canonical_id: str
    relationship_type: str
    case_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class RejectCandidateRequest(BaseModel):
    reason: str
    notes: str | None = None


class CandidateDecisionResponse(BaseModel):
    decision_id: str
    candidate_id: str
    candidate_type: str  # ENTITY | RELATIONSHIP
    action: str  # ACCEPT_EXISTING | ACCEPT_NEW | ACCEPT_RELATIONSHIP | REJECT
    status: str
    decided_by: str  # officer user_id
    decided_at: datetime = Field(default_factory=_utcnow)
    target_id: str | None = None
    resulting_graph_id: str | None = None
    reason: str | None = None
    notes: str | None = None
    audit_event_id: str | None = None
    propagation_status: str | None = None
    propagation_snapshot_id: str | None = None


# ── Graph & Network ───────────────────────────────────────────────────────────

class NodePresenceType(str, Enum):
    DIRECT_CASE = "DIRECT_CASE"
    INTELLIGENCE_EXPANSION = "INTELLIGENCE_EXPANSION"
    CDR_CONNECTION = "CDR_CONNECTION"
    CROSS_CASE = "CROSS_CASE"
    EVIDENCE = "EVIDENCE"
    OTHER = "OTHER"


class NodeContextResponse(BaseModel):
    presence_type: NodePresenceType
    reason: str
    source_ids: list[str] = Field(default_factory=list)
    relationship_types: list[str] = Field(default_factory=list)
    distance_from_case: int = 0
    path: list[str] = Field(default_factory=list)
    readable_path: str = ""


class GraphNodeResponse(BaseModel):
    id: str
    entity_type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    degree: int = 0
    confidence: float = 1.0
    context: NodeContextResponse | None = None


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
    case_id: str | None = None
    depth: int | None = None


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
    search_relevance: float = 1.0
    resolution_state: str = "CANDIDATE_NAME_ONLY"
    evidence_families: list[str] = Field(default_factory=list)
    supporting_factors: list[str] = Field(default_factory=list)
    conflicting_factors: list[str] = Field(default_factory=list)
    independent_sources: int = 1
    explanation: str = ""


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


class TimelineEventCategory(str, Enum):
    CASE_REGISTRATION = "CASE_REGISTRATION"
    EVIDENCE_DOCUMENT = "EVIDENCE_DOCUMENT"
    COMMUNICATION = "COMMUNICATION"
    FINANCIAL_TRANSACTION = "FINANCIAL_TRANSACTION"
    SURVEILLANCE_SIGHTING = "SURVEILLANCE_SIGHTING"
    INVESTIGATOR_ACTION = "INVESTIGATOR_ACTION"
    GRAPH_CHANGE = "GRAPH_CHANGE"
    INTELLIGENCE_SIGNAL = "INTELLIGENCE_SIGNAL"
    EVIDENCE_ASSESSMENT = "EVIDENCE_ASSESSMENT"
    VERIFICATION_WORKFLOW = "VERIFICATION_WORKFLOW"
    CROSS_CASE_ROUTE = "CROSS_CASE_ROUTE"


class TimelineEventResponse(BaseModel):
    id: str
    event_type: str
    timestamp: datetime
    description: str
    participant_ids: list[str] = Field(default_factory=list)
    location_id: str | None = None
    case_id: str | None = None
    # Rich A15 extensions (backward-compatible with defaults)
    category: TimelineEventCategory | None = None
    occurred_at: datetime | None = None
    recorded_at: datetime | None = None
    title: str | None = None
    edge_ids: list[str] = Field(default_factory=list)
    source_type: str | None = None
    source_id: str | None = None
    locator: str | None = None
    actor_id: str | None = None
    actor_role: UserRole | None = None
    intelligence_event_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    snapshot_id: str | None = None
    route_id: str | None = None
    task_id: str | None = None
    assessment_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class TimelineQueryResponse(BaseModel):
    events: list[TimelineEventResponse]
    total_count: int
    case_id: str | None = None
    entity_id: str | None = None
    limit: int = 50
    offset: int = 0
    has_more: bool = False



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


class CaseCollectionItem(BaseModel):
    case_id: str
    fir_number: str
    title: str
    offence_category: str
    district: str
    station_name: str
    status: str
    updated_at: datetime | None = None
    summary: str | None = None


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
    collection_results: list[CaseCollectionItem] = Field(default_factory=list)
    total_count: int = 0
    query_type: str | None = None


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
    integrity_hash: str | None = None
    previous_hash: str | None = None


class AuthLoginRequest(BaseModel):
    username: str
    password: str | None = None
    role: UserRole | None = None


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
    source_type: str  # CDR | BANK_TXN | FIR | INTEL_REPORT | SURVEILLANCE_REPORT
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


# ── P0 Proactive Network Change Intelligence Contracts ────────────────────────

class EpistemicState(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONFLICTS = "CONFLICTS"
    MISSING = "MISSING"
    INFERRED = "INFERRED"
    VERIFIED = "VERIFIED"


class ReviewPriority(str, Enum):
    CRITICAL_REVIEW = "CRITICAL_REVIEW"
    PRIORITY_REVIEW = "PRIORITY_REVIEW"
    ROUTINE_REVIEW = "ROUTINE_REVIEW"


class ForecastTarget(str, Enum):
    JURISDICTION_SHIFT = "JURISDICTION_SHIFT"
    COMMUNICATION_PATTERN_SHIFT = "COMMUNICATION_PATTERN_SHIFT"
    FINANCIAL_ROUTE_TRANSITION = "FINANCIAL_ROUTE_TRANSITION"
    IDENTIFIER_DRIFT = "IDENTIFIER_DRIFT"
    NETWORK_RESTRUCTURING = "NETWORK_RESTRUCTURING"


class EvidenceAssessmentItem(BaseModel):
    claim_id: str
    target_relationship_id: str
    evidence_ref: str
    state: EpistemicState
    rationale: str
    source_quality: float = 1.0
    freshness_days: int = 0


class ForecastItem(BaseModel):
    forecast_id: str
    pulse_id: str
    target_state: ForecastTarget
    time_window: tuple[str, str] = ("", "")
    support_level: float = 0.0
    uncertainty: float = 0.0
    action_window: str = "Within 48 hours"
    suggested_verification: str = ""
    abstained: bool = False
    abstention_reason: str | None = None


class VerificationActionItem(BaseModel):
    verification_id: str
    target_claim: str
    missing_evidence_type: str
    recommended_action: str
    responsible_role: UserRole = UserRole.INVESTIGATOR
    status: str = "PENDING"
    result: str | None = None


class NetworkPulseItem(BaseModel):
    pulse_id: str
    change_ids: list[str] = Field(default_factory=list)
    signal_headline: str
    review_priority: ReviewPriority = ReviewPriority.PRIORITY_REVIEW
    time_window: tuple[str, str] = ("", "")
    evidence_refs: list[str] = Field(default_factory=list)
    support_level: float = 0.0
    uncertainty: float = 0.0
    action_window: str = "Immediate"
    abstained: bool = False
    generated_at: str = Field(default_factory=lambda: _utcnow().isoformat())
    assessment: list[EvidenceAssessmentItem] = Field(default_factory=list)
    forecast: ForecastItem | None = None
    verification_plan: list[VerificationActionItem] = Field(default_factory=list)
    affected_entities: list[str] = Field(default_factory=list)
    affected_cases: list[str] = Field(default_factory=list)


class GraphSnapshotSummary(BaseModel):
    snapshot_id: str
    case_scope: str | None = None
    created_at: str
    node_count: int
    edge_count: int
    version: str = "v1"
    dataset_version: str = CANONICAL_DATASET_VERSION


class NetworkDiffResponse(BaseModel):
    before_snapshot_id: str
    after_snapshot_id: str
    added_nodes: list[str] = Field(default_factory=list)
    removed_nodes: list[str] = Field(default_factory=list)
    added_relationships: list[str] = Field(default_factory=list)
    removed_relationships: list[str] = Field(default_factory=list)
    modified_node_count: int = 0
    modified_relationship_count: int = 0
    pulses: list[NetworkPulseItem] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    dataset_version: str = CANONICAL_DATASET_VERSION


class NexusGraphNode(BaseModel):
    id: str
    entity_type: str
    label: str
    case_ids: list[str] = Field(default_factory=list)
    badges: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class NexusGraphEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    edge_type: str
    weight: float = 1.0
    confidence: float = 1.0
    derivation_class: str = "FACT"  # FACT, DERIVED, HYPOTHESIS
    recorded_at: str = Field(default_factory=lambda: _utcnow().isoformat())
    case_ids: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class NexusNetworkResponse(BaseModel):
    snapshot_id: str
    state: str = "after"  # "before", "after", or snapshot ID
    nodes: list[NexusGraphNode] = Field(default_factory=list)
    edges: list[NexusGraphEdge] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    dataset_version: str = CANONICAL_DATASET_VERSION


class SnapshotDiffResponse(BaseModel):
    before_snapshot_id: str
    after_snapshot_id: str
    added_node_ids: list[str] = Field(default_factory=list)
    removed_node_ids: list[str] = Field(default_factory=list)
    changed_node_ids: list[str] = Field(default_factory=list)
    added_edge_ids: list[str] = Field(default_factory=list)
    removed_edge_ids: list[str] = Field(default_factory=list)
    changed_edge_ids: list[str] = Field(default_factory=list)
    dataset_version: str = CANONICAL_DATASET_VERSION


class IntelligenceKPIs(BaseModel):
    active_pulses_count: int = 0
    critical_pulses_count: int = 0
    evidence_percent: int = 100
    supported_claims: int = 0
    total_claims: int = 0
    affected_cases_count: int = 0
    added_nodes: int = 0
    added_edges: int = 0
    total_changes: int = 0


class IntelligenceBootstrapResponse(BaseModel):
    dataset_version: str = CANONICAL_DATASET_VERSION
    snapshot_id: str = CANONICAL_SNAPSHOT_CURRENT
    baseline_snapshot_id: str = CANONICAL_SNAPSHOT_BASELINE
    kpis: IntelligenceKPIs = Field(default_factory=IntelligenceKPIs)
    primary_pulse: NetworkPulseItem | None = None
    primary_diff: NetworkDiffResponse | None = None
    affected_cases: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: _utcnow().isoformat())


class InvestigationContext(BaseModel):
    case_id: str | None = None
    target_case_id: str | None = None
    entity_id: str | None = None
    evidence_id: str | None = None
    change_id: str | None = None
    relationship_id: str | None = None
    snapshot_id: str | None = None
    feature_type: str | None = None
    focus: str | None = None  # "1hop", "2hop", "crosscase", "community"
    drawer: str | None = None  # "entity", "relationship", "evidence"


# ── P1-A Cross-Jurisdiction Intelligence Pulse Routing Contracts ─────────────

class PulseDeliveryStatus(str, Enum):
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED = "ACTIONED"
    REJECTED = "REJECTED"


class PulseSecurityClassification(str, Enum):
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"


class IntelligencePulsePacket(BaseModel):
    packet_id: str
    origin_case_id: str
    origin_district: str
    origin_officer_id: str
    target_case_id: str
    target_district: str
    target_role: UserRole = UserRole.INVESTIGATOR
    headline: str
    summary: str
    shared_entities: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    packet_hash: str
    security_classification: PulseSecurityClassification = PulseSecurityClassification.RESTRICTED
    dispatched_at: str = Field(default_factory=lambda: _utcnow().isoformat())
    delivery_status: PulseDeliveryStatus = PulseDeliveryStatus.DISPATCHED
    acknowledged_at: str | None = None
    acknowledged_by: str | None = None
    acknowledgment_note: str | None = None


class CreateIntelligencePulseRequest(BaseModel):
    origin_case_id: str
    target_case_id: str
    target_district: str
    headline: str
    summary: str
    shared_entities: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    security_classification: PulseSecurityClassification = PulseSecurityClassification.RESTRICTED


class AcknowledgePulseRequest(BaseModel):
    decision: str  # ACKNOWLEDGE, ACTION, REJECT
    note: str | None = None


# ── A14 Affected Investigation Routing Contracts ─────────────────────────────

class AffectedInvestigationRoute(BaseModel):
    """
    Authoritative routing record directing criminal network change intelligence
    to deterministically affected investigations (A14).
    Grounded in verifiable evidence provenance and Section 63 BSA compliance,
    without predictive guilt or speculative prioritization.
    """
    route_id: str
    origin_case_id: str
    origin_district: str
    target_case_id: str
    target_district: str
    trigger_event_id: str | None = None
    source_snapshot_id: str
    target_snapshot_id: str
    diff_summary: dict[str, int] = Field(default_factory=dict)
    intersecting_entity_ids: list[str] = Field(default_factory=list)
    intersecting_edge_ids: list[str] = Field(default_factory=list)
    routing_reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    route_hash: str
    status: PulseDeliveryStatus = PulseDeliveryStatus.DISPATCHED
    dispatched_at: str = Field(default_factory=lambda: _utcnow().isoformat())
    acknowledged_at: str | None = None
    acknowledged_by: str | None = None
    acknowledgment_note: str | None = None


class AcknowledgeRouteRequest(BaseModel):
    decision: str  # ACKNOWLEDGE, ACTION, REJECT
    note: str | None = None


class EvaluateRoutingRequest(BaseModel):
    origin_case_id: str | None = None
    source_snapshot_id: str | None = None
    target_snapshot_id: str | None = None
    trigger_event_id: str | None = None
    changed_entity_ids: list[str] = Field(default_factory=list)
    changed_edge_ids: list[str] = Field(default_factory=list)


class RouteQueryResponse(BaseModel):
    total: int
    routes: list[AffectedInvestigationRoute] = Field(default_factory=list)


# ── P1-B Identity Drift Radar Contracts ───────────────────────────────────────

class IdentityDriftType(str, Enum):
    PHONE_TURNOVER = "PHONE_TURNOVER"
    DEVICE_HOP = "DEVICE_HOP"
    VEHICLE_DRIFT = "VEHICLE_DRIFT"
    ALIAS_EVOLUTION = "ALIAS_EVOLUTION"


class IdentityDriftStatus(str, Enum):
    DETECTED = "DETECTED"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    MONITORING = "MONITORING"


class IdentityDriftEvent(BaseModel):
    drift_id: str
    person_id: str
    person_name: str
    drift_type: IdentityDriftType
    previous_value: str
    new_value: str
    previous_seen_at: str | None = None
    new_seen_at: str | None = None
    time_window_days: int | None = None
    corroborating_context: str
    evidence_refs: list[str] = Field(default_factory=list)
    derivation_class: str = "DERIVED"
    human_status: IdentityDriftStatus = IdentityDriftStatus.DETECTED
    investigator_note: str | None = None
    decided_at: str | None = None
    decided_by: str | None = None


class DecideIdentityDriftRequest(BaseModel):
    status: IdentityDriftStatus
    note: str | None = None


# ── P1-C Network Adaptation Engine Contracts ─────────────────────────────────

class NetworkAdaptationType(str, Enum):
    INTERMEDIARY_REPLACEMENT = "INTERMEDIARY_REPLACEMENT"
    BRIDGE_SUBSTITUTION = "BRIDGE_SUBSTITUTION"
    FINANCIAL_REROUTING = "FINANCIAL_REROUTING"
    COMMUNITY_RECONNECTION = "COMMUNITY_RECONNECTION"


class AdaptationReviewStatus(str, Enum):
    DETECTED = "DETECTED"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    MONITORING = "MONITORING"


class NetworkAdaptationEvent(BaseModel):
    adaptation_id: str
    adaptation_type: NetworkAdaptationType
    primary_entity_id: str
    primary_entity_name: str
    secondary_entity_id: str
    secondary_entity_name: str
    substitute_intermediary_id: str | None = None
    substitute_intermediary_name: str | None = None
    previous_path: list[str] = Field(default_factory=list)
    new_path: list[str] = Field(default_factory=list)
    detected_at: str = Field(default_factory=lambda: _utcnow().isoformat())
    time_lag_days: int | None = None
    structural_significance: float = 0.85
    corroborating_context: str
    evidence_refs: list[str] = Field(default_factory=list)
    derivation_class: str = "DERIVED"
    review_status: AdaptationReviewStatus = AdaptationReviewStatus.DETECTED
    investigator_note: str | None = None
    decided_at: str | None = None
    decided_by: str | None = None


class DecideNetworkAdaptationRequest(BaseModel):
    status: AdaptationReviewStatus
    note: str | None = None


# ── P1-D Digital Shadow (SOCMINT Governance) Contracts ───────────────────────

class DigitalShadowPlatform(str, Enum):
    TELEGRAM = "TELEGRAM"
    WHATSAPP = "WHATSAPP"
    DARKWEB_FORUM = "DARKWEB_FORUM"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    PAYMENT_GATEWAY = "PAYMENT_GATEWAY"
    MARKETPLACE = "MARKETPLACE"


class DigitalShadowLifecycle(str, Enum):
    """Mandatory Section 63 BSA progression lifecycle for digital corroboration."""
    OBSERVED = "OBSERVED"
    CANDIDATE_LINK = "CANDIDATE_LINK"
    CORROBORATED = "CORROBORATED"
    INVESTIGATOR_CONFIRMED = "INVESTIGATOR_CONFIRMED"
    DISMISSED = "DISMISSED"


class DigitalShadowCorroboration(BaseModel):
    corroboration_id: str
    person_id: str
    person_name: str
    platform: DigitalShadowPlatform
    digital_identifier: str
    corroborating_physical_id: str  # Mandatory hard physical identifier (Phone, IMEI, Account, Bank)
    corroborating_physical_type: str  # Phone, Device, Account
    confidence_score: float = 0.85
    lifecycle_state: DigitalShadowLifecycle = DigitalShadowLifecycle.OBSERVED
    observation_context: str
    source_url_or_channel: str
    evidence_refs: list[str] = Field(default_factory=list)
    derivation_class: str = "DERIVED"
    first_observed_at: str = Field(default_factory=lambda: _utcnow().isoformat())
    last_verified_at: str | None = None
    investigator_note: str | None = None
    decided_at: str | None = None
    decided_by: str | None = None


class DecideDigitalShadowRequest(BaseModel):
    lifecycle_state: DigitalShadowLifecycle
    note: str | None = None


# ── P2 Case DNA Explainable Structural Similarity Contracts ──────────────────

class CaseDNA(BaseModel):
    case_pair: list[str]  # [case_a_id, case_b_id]
    case_a_title: str
    case_b_title: str
    overall_similarity: float
    structure_similarity: float      # Graph topology & modularity similarity
    communication_similarity: float  # CDR burst & frequency profile
    financial_similarity: float      # Peeling chain & transaction flow similarity
    location_similarity: float       # Geographic spatial overlap
    temporal_similarity: float       # Modus operandi timing match
    shared_entities: list[str] = Field(default_factory=list)
    explanation: str
    evidence_refs: list[str] = Field(default_factory=list)
    derivation_class: str = "DERIVED"
    dataset_version: str = CANONICAL_DATASET_VERSION
    snapshot_id: str = CANONICAL_SNAPSHOT_CURRENT


class CaseDNAMatchResponse(BaseModel):
    target_case_id: str
    similar_cases: list[CaseDNA] = Field(default_factory=list)
    average_similarity: float = 0.0
    highest_similarity: float = 0.0
    top_shared_entities: list[str] = Field(default_factory=list)
    dataset_version: str = CANONICAL_DATASET_VERSION


# ── A3 IntelligenceEvent Unified Domain Contract ─────────────────────────────

class IntelligenceEventType(str, Enum):
    DOCUMENT_INGESTED = "DOCUMENT_INGESTED"
    DOCUMENT_EXTRACTED = "DOCUMENT_EXTRACTED"
    ENTITY_OBSERVED = "ENTITY_OBSERVED"
    RELATIONSHIP_OBSERVED = "RELATIONSHIP_OBSERVED"
    NETWORK_CHANGE_DETECTED = "NETWORK_CHANGE_DETECTED"
    SNAPSHOT_CREATED = "SNAPSHOT_CREATED"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    EVIDENCE_ASSESSED = "EVIDENCE_ASSESSED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    VERIFICATION_TASK_CREATED = "VERIFICATION_TASK_CREATED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    ENTITY_RESOLUTION_DECIDED = "ENTITY_RESOLUTION_DECIDED"
    INVESTIGATOR_DECISION = "INVESTIGATOR_DECISION"


class IntelligenceEvent(BaseModel):
    """
    Authoritative domain event contract for the NEXUS criminal intelligence pipeline (A3).
    Represents atomic operational intelligence occurrences with tamper-evident SHA-256
    payload hashing and verifiable evidence provenance, strictly without predictive guilt scoring.
    """
    # Identity
    event_id: str
    event_type: IntelligenceEventType
    event_version: str = "1.0"
    event_timestamp: datetime = Field(default_factory=_utcnow)

    # Context
    case_id: str
    fir_id: str | None = None
    source_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    snapshot_id: str | None = None
    related_entity_ids: list[str] = Field(default_factory=list)
    related_edge_ids: list[str] = Field(default_factory=list)

    # Provenance
    source_type: str = "SYSTEM"
    actor_id: str = "SYSTEM"
    actor_role: UserRole | None = None
    observed_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=_utcnow)
    processed_at: datetime | None = None
    correlation_id: str | None = None
    causation_id: str | None = None

    # Semantics & Content
    title: str = ""
    description: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    integrity_hash: str | None = None


class CreateIntelligenceEventRequest(BaseModel):
    """Request contract to record an operational intelligence event."""
    event_type: IntelligenceEventType
    case_id: str
    fir_id: str | None = None
    source_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    snapshot_id: str | None = None
    related_entity_ids: list[str] = Field(default_factory=list)
    related_edge_ids: list[str] = Field(default_factory=list)
    source_type: str = "SYSTEM"
    actor_id: str | None = None
    actor_role: UserRole | None = None
    observed_at: datetime | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    title: str = ""
    description: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class IntelligenceEventListResponse(BaseModel):
    """Paginated collection of intelligence events."""
    events: list[IntelligenceEvent]
    total_count: int
    case_id: str | None = None
    limit: int = 50
    offset: int = 0


# ── A7 Persistent Verification Tasks Domain Contracts ────────────────────────

class VerificationTaskStatus(str, Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    REQUESTED = "REQUESTED"
    RECEIVED = "RECEIVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    DISMISSED = "DISMISSED"


class VerificationTaskDecision(str, Enum):
    VERIFIED = "VERIFIED"
    DISMISSED = "DISMISSED"


class TaskTransitionHistoryItem(BaseModel):
    from_status: VerificationTaskStatus
    to_status: VerificationTaskStatus
    actor_id: str
    timestamp: datetime = Field(default_factory=_utcnow)
    rationale: str | None = None


class VerificationTask(BaseModel):
    """
    Authoritative domain contract for persistent investigator verification tasks (A7).
    Bridges proactive intelligence recommendations and investigator evidence collection,
    strictly without predictive guilt scoring.
    """
    # Identity
    task_id: str
    case_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Origin
    originating_event_id: str | None = None
    originating_pulse_id: str | None = None
    target_claim: str
    reason: str

    # Verification requirement
    requested_evidence_type: str
    verification_action: str
    expected_outcome: str | None = None
    evidence_gap: str | None = None

    # Assignment
    assigned_officer_id: str | None = None
    assigned_role: UserRole | None = None
    assigned_at: datetime | None = None

    # Lifecycle
    status: VerificationTaskStatus = VerificationTaskStatus.CREATED
    history: list[TaskTransitionHistoryItem] = Field(default_factory=list)

    # Evidence linkage (references only)
    requested_evidence_ids: list[str] = Field(default_factory=list)
    received_evidence_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    conflicting_evidence_ids: list[str] = Field(default_factory=list)

    # Decision
    decision: VerificationTaskDecision | None = None
    decision_rationale: str | None = None
    deciding_actor: str | None = None
    decided_at: datetime | None = None


class CreateVerificationTaskRequest(BaseModel):
    """Request contract to instantiate a persistent verification task."""
    case_id: str
    target_claim: str
    reason: str
    requested_evidence_type: str
    verification_action: str
    expected_outcome: str | None = None
    evidence_gap: str | None = None
    originating_event_id: str | None = None
    originating_pulse_id: str | None = None
    assigned_officer_id: str | None = None
    assigned_role: UserRole | None = None


class AssignVerificationTaskRequest(BaseModel):
    """Request contract to assign/reassign a verification task."""
    assigned_officer_id: str
    assigned_role: UserRole | None = None
    rationale: str | None = None


class TransitionVerificationTaskRequest(BaseModel):
    """Request contract to advance task lifecycle state."""
    target_status: VerificationTaskStatus
    rationale: str | None = None


class AttachEvidenceRequest(BaseModel):
    """Request contract to link an authoritative evidence record to a verification task."""
    evidence_id: str
    relationship_type: str = "SUPPORTING"  # SUPPORTING, CONFLICTING, RECEIVED, REQUESTED
    notes: str | None = None


class DecideVerificationTaskRequest(BaseModel):
    """Request contract to record final verification outcome."""
    decision: VerificationTaskDecision
    rationale: str


class VerificationTaskListResponse(BaseModel):
    """Paginated collection of verification tasks."""
    tasks: list[VerificationTask]
    total_count: int
    case_id: str | None = None
    status: VerificationTaskStatus | None = None
    assignee: str | None = None
    limit: int = 50
    offset: int = 0


# ── A5 Evidence Assessment Domain Contracts ────────────────────────────────────

class AssessmentBasis(str, Enum):
    DIRECT = "DIRECT"
    CORROBORATING = "CORROBORATING"
    CONFLICTING = "CONFLICTING"
    MISSING = "MISSING"
    INFERRED = "INFERRED"


class AssessmentRevisionHistoryItem(BaseModel):
    revision_number: int
    from_state: EpistemicState
    to_state: EpistemicState
    actor_id: str
    timestamp: datetime = Field(default_factory=_utcnow)
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)


class EvidenceAssessment(BaseModel):
    """
    Authoritative evidence assessment domain entity (A5).
    Evaluates the relationship between evidence and claims/entities/edges/events
    without predictive guilt, risk, or confidence scoring.
    """
    # Identity
    assessment_id: str
    case_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Claim
    claim: str
    claim_type: str = "RELATIONSHIP"  # RELATIONSHIP, ENTITY_LINK, COMMUNICATION, FINANCIAL, EVENT_MEMBERSHIP
    target_entity_id: str | None = None
    target_edge_id: str | None = None
    target_event_id: str | None = None
    intelligence_event_id: str | None = None
    verification_task_id: str | None = None

    # Assessment
    state: EpistemicState
    rationale: str
    assessment_basis: AssessmentBasis = AssessmentBasis.DIRECT

    # Authoritative Evidence References
    evidence_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    conflicting_evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence_types: list[str] = Field(default_factory=list)

    # Provenance
    source_ids: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    observed_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=_utcnow)
    provenance_refs: list[str] = Field(default_factory=list)

    # History & Lifecycle
    history: list[AssessmentRevisionHistoryItem] = Field(default_factory=list)

    def to_pulse_item(self) -> EvidenceAssessmentItem:
        """Convert first-class EvidenceAssessment into a backward-compatible pulse item."""
        evidence_ref = self.evidence_ids[0] if self.evidence_ids else (self.target_edge_id or "none")
        return EvidenceAssessmentItem(
            claim_id=self.assessment_id,
            target_relationship_id=self.target_edge_id or self.target_entity_id or "none",
            evidence_ref=evidence_ref,
            state=self.state,
            rationale=self.rationale,
            source_quality=1.0 if self.state in (EpistemicState.SUPPORTS, EpistemicState.VERIFIED) else 0.5,
            freshness_days=0,
        )

    @classmethod
    def from_pulse_item(cls, item: EvidenceAssessmentItem, case_id: str = "") -> EvidenceAssessment:
        """Construct an EvidenceAssessment from an embedded pulse EvidenceAssessmentItem."""
        return cls(
            assessment_id=item.claim_id,
            case_id=case_id,
            claim=f"Assessment of {item.target_relationship_id}",
            claim_type="RELATIONSHIP",
            target_edge_id=item.target_relationship_id if item.target_relationship_id != "none" else None,
            evidence_ids=[item.evidence_ref] if item.evidence_ref != "none" else [],
            state=item.state,
            rationale=item.rationale,
            assessment_basis=AssessmentBasis.DIRECT if item.state == EpistemicState.SUPPORTS else AssessmentBasis.MISSING,
        )


class CreateEvidenceAssessmentRequest(BaseModel):
    """Request contract to assess a claim with evidence."""
    case_id: str
    claim: str
    claim_type: str = "RELATIONSHIP"
    state: EpistemicState
    rationale: str
    assessment_basis: AssessmentBasis = AssessmentBasis.DIRECT
    target_entity_id: str | None = None
    target_edge_id: str | None = None
    target_event_id: str | None = None
    intelligence_event_id: str | None = None
    verification_task_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    conflicting_evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence_types: list[str] = Field(default_factory=list)


class ReviseEvidenceAssessmentRequest(BaseModel):
    """Request contract to revise an existing assessment."""
    state: EpistemicState
    rationale: str
    assessment_basis: AssessmentBasis | None = None
    additional_evidence_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] | None = None
    conflicting_evidence_ids: list[str] | None = None
    missing_evidence_types: list[str] | None = None


class EvidenceAssessmentListResponse(BaseModel):
    """Paginated collection of evidence assessments."""
    assessments: list[EvidenceAssessment]
    total_count: int
    case_id: str | None = None
    state: EpistemicState | None = None
    limit: int = 50
    offset: int = 0





