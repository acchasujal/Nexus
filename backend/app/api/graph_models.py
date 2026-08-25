"""backend/app/api/graph_models.py

Pydantic v2 response models for all graph intelligence endpoints.
Provides structured contract validation and OpenAPI schema documentation
for graph routes.
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, Field

# ── Common Graph Shapes ────────────────────────────────────────────────────────

class NodeResponse(BaseModel):
    # Internal graph services use ``node_id``; the HTTP contract uses ``id``.
    # Accept both at the boundary so graph responses remain observationally
    # compatible while satisfying the documented API schema.
    id: str = Field(validation_alias=AliasChoices("id", "node_id"))
    entity_type: str
    properties: dict[str, Any]


class EdgeResponse(BaseModel):
    edge_type: str
    source_id: str
    target_id: str
    properties: dict[str, Any]


# ── Network & Traversal Responses ──────────────────────────────────────────────

class GraphNetworkResponse(BaseModel):
    root_id: str
    depth: int
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]
    node_count: int
    edge_count: int


class PersonNetworkResponse(BaseModel):
    root_id: str
    depth: int
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]


class CoAccusedItem(BaseModel):
    person_id: str
    shared_cases: list[NodeResponse]


class CoAccusedResponse(BaseModel):
    person_id: str
    co_accused: list[CoAccusedItem]
    co_accused_count: int


class PathsBetweenResponse(BaseModel):
    source_id: str
    target_id: str
    path_found: bool
    depth: int = 0
    nodes: list[NodeResponse] = []
    edges: list[EdgeResponse] = []


# ── Similarity Responses ───────────────────────────────────────────────────────

class SimilarCaseMatch(BaseModel):
    case_id: str
    score: float
    reasons: list[str]
    properties: dict[str, Any]


class SimilarCasesResponse(BaseModel):
    case_id: str
    top_k: int
    min_score: float
    matches: list[SimilarCaseMatch]
    match_count: int


class CaseCompareResponse(BaseModel):
    case_a_id: str
    case_b_id: str
    score: float
    reasons: list[str]


# ── Aggregation & Dashboard Responses ──────────────────────────────────────────

class CrimeSummaryResponse(BaseModel):
    total_cases: int
    by_stage: dict[str, int]
    by_category: dict[str, int]
    by_risk: dict[str, int]


class DimensionCountsResponse(BaseModel):
    dimension: str
    counts: dict[str, int]


class OfficerWorkloadItem(BaseModel):
    officer_id: str
    case_count: int


class OfficerWorkloadResponse(BaseModel):
    dimension: str
    workloads: list[OfficerWorkloadItem]
    total_officers: int


# ── Hotspots Responses ─────────────────────────────────────────────────────────

class HotspotsSummary(BaseModel):
    total_cases: int
    total_persons: int
    total_officers: int


class DistrictCrimeHotspot(BaseModel):
    district: str
    case_count: int
    crime_rate_index: float
    risk_level: str


class DistrictCrimeHotspotsResponse(BaseModel):
    category: str
    alert_level: str
    hotspots: list[DistrictCrimeHotspot]
    hotspot_count: int


class TemporalSpike(BaseModel):
    case_id: str
    fir_number: str
    reported_at: str
    spike_index: float
    details: str


class TemporalHotspotsResponse(BaseModel):
    category: str
    alert_level: str
    spikes: list[TemporalSpike]
    spike_count: int


class DependencyHotspot(BaseModel):
    case_id: str
    fir_number: str
    pending_count: int
    oldest_pending_days: int
    risk_level: str


class DependencyHotspotsResponse(BaseModel):
    category: str
    alert_level: str
    hotspots: list[DependencyHotspot]
    hotspot_count: int
    total_pending_dependencies: int


class WorkloadOfficer(BaseModel):
    officer_id: str
    officer_name: str
    case_count: int
    overload_index: float
    status: str


class WorkloadHotspotsResponse(BaseModel):
    category: str
    alert_level: str
    officers: list[WorkloadOfficer]
    officer_count: int


class RepeatOffenderItem(BaseModel):
    person_id: str
    case_count: int
    reason: str


class PhoneCluster(BaseModel):
    phone_number: str
    person_count: int
    person_ids: list[str]


class VehicleCluster(BaseModel):
    license_plate: str
    person_count: int
    person_ids: list[str]


class AddressCluster(BaseModel):
    address_text: str
    person_count: int
    person_ids: list[str]


class NetworkHotspotsResponse(BaseModel):
    category: str
    alert_level: str
    repeat_offenders: dict[str, Any]
    shared_phone_clusters: dict[str, Any]
    shared_vehicle_clusters: dict[str, Any]
    shared_address_clusters: dict[str, Any]
    total_network_flags: int


class DistrictHotspotsResponse(BaseModel):
    district: str
    temporal_spikes: list[dict[str, Any]]
    dependency_hotspots: list[dict[str, Any]]
    alert_summary: dict[str, int]


class MasterHotspotsResponse(BaseModel):
    generated_at: str
    summary: HotspotsSummary
    temporal: TemporalHotspotsResponse
    dependency: DependencyHotspotsResponse
    workload: WorkloadHotspotsResponse
    network: NetworkHotspotsResponse
    district: DistrictCrimeHotspotsResponse


# ── Offender Profile Responses ─────────────────────────────────────────────────

class RepeatOffenderDetail(BaseModel):
    person_id: str
    case_count: int
    case_ids: list[str]
    reason: str
    person: NodeResponse


class RepeatOffendersResponse(BaseModel):
    min_cases_threshold: int
    offender_count: int
    offenders: list[RepeatOffenderDetail]


class RepeatOffenderResolvedDetail(BaseModel):
    canonical_person_name: str
    person_ids: list[str]
    case_count: int
    case_ids: list[str]
    reason: str


class RepeatOffendersResolvedResponse(BaseModel):
    min_cases_threshold: int
    confidence_threshold: float
    offender_count: int
    offenders: list[RepeatOffenderResolvedDetail]


class SectionDiversity(BaseModel):
    unique_sections: list[str]
    count: int


class CrimeHeadDiversity(BaseModel):
    unique_crime_heads: list[str]
    count: int


class JurisdictionSpread(BaseModel):
    police_stations: list[str]
    districts: list[str]
    station_count: int
    district_count: int


class CoAccusedOffender(BaseModel):
    person_id: str
    shared_case_count: int


class OffenderProfileResponse(BaseModel):
    person_id: str
    person: NodeResponse
    accused_in_count: int
    case_ids: list[str]
    fir_numbers: list[str]
    section_diversity: SectionDiversity
    crime_head_diversity: CrimeHeadDiversity
    jurisdiction_spread: JurisdictionSpread
    co_accused_count: int
    co_accused: list[CoAccusedOffender]
    summary: str


# ── Graph Health Responses ─────────────────────────────────────────────────────

class GraphStatsResponse(BaseModel):
    node_count: int
    edge_count: int
    density: float
    average_degree: float
    node_counts_by_type: dict[str, int]
    edge_counts_by_type: dict[str, int]


class ConnectedComponentItem(BaseModel):
    size: int
    node_ids: list[str]


class ConnectedComponentsResponse(BaseModel):
    component_count: int
    components: list[ConnectedComponentItem]
    largest_component_size: int


class CentralNodeItem(BaseModel):
    node_id: str
    score: float
    node: NodeResponse


class CentralityResponse(BaseModel):
    metric: str
    top_nodes: list[CentralNodeItem]
