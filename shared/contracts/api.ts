/**
 * shared/contracts/api.ts
 *
 * Authoritative TypeScript API contract types for NEXUS Criminal Intelligence Platform.
 * Kept in sync with shared/contracts/api.py.
 */

export const CANONICAL_DATASET_VERSION = 'NCRB_CALIBRATED:v1'
export const CANONICAL_SNAPSHOT_BASELINE = 'snap-baseline-v1'
export const CANONICAL_SNAPSHOT_CURRENT = 'snap-current'

export type UserRole = 'INVESTIGATOR' | 'ANALYST' | 'SUPERVISOR' | 'ADMIN' | 'IO' | 'SHO' | 'SP'

export type ResolutionStatus = 'MATCHED' | 'PROBABLE_MATCH' | 'REVIEW_REQUIRED' | 'NOT_MATCHED'

export type EntityType = 
  | 'Person'
  | 'Case'
  | 'Phone'
  | 'Vehicle'
  | 'Location'
  | 'Organization'
  | 'Device'
  | 'Account'
  | 'Transaction'
  | 'Event'
  | 'IntelligenceReport'
  | 'Evidence'

export interface EvidenceProvenanceContract {
  source_type: string
  source_id: string
  timestamp: string
  extracted_fact: string
  derivation_method: string
  confidence: number
  file_hash?: string
}

export type ClockStatus = 'green' | 'amber' | 'red' | 'overdue' | string

export interface ClockResponse {
  id: string
  case_id: string
  clock_type: string
  start_date: string
  deadline_date: string
  days_remaining: number
  status: ClockStatus
  bnss_reference?: string
}

export interface EscalationResponse {
  id: string
  case_id: string
  triggered_at: string
  reason: string
  routed_to_rank: string
  routed_to_officer_id: string
  resolved: boolean
}

export interface DependencyResponse {
  id: string
  case_id: string
  name: string
  status: 'pending' | 'resolved' | string
  days_stale: number
  assigned_to: string
}

export type DependencyStatus = 'pending' | 'resolved' | string

export interface ChatResponse {
  query?: string
  message?: string
  answer?: string
  response?: string
  conversation_id?: string
  intent?: Record<string, any> | string
  citations?: GroundedCitation[]
  [key: string]: any
}


export interface EvidenceItemResponse {
  id: string
  evidence_number: string
  case_id: string
  evidence_type: string
  description: string
  collected_at: string
  storage_location?: string
  provenance: EvidenceProvenanceContract
}

export type DocumentSourceType =
  | 'FIR_DOCUMENT'
  | 'POLICE_REPORT'
  | 'INTELLIGENCE_DOCUMENT'
  | 'OTHER_DOCUMENT'

export type ExtractionStatus = 'SUCCESS' | 'FAILED' | 'EMPTY'

export interface DocumentExtractionMetadata {
  page_count: number
  character_count: number
  word_count: number
  extraction_method: string
  error_message?: string | null
}

export interface DocumentResponse {
  document_id: string
  original_filename: string
  source_type: string
  mime_type: string
  content_hash: string
  uploaded_by: string
  uploaded_at: string
  case_id?: string | null
  extraction_status: ExtractionStatus
  extraction_metadata: DocumentExtractionMetadata
  provenance: EvidenceProvenanceContract
}

export interface DocumentTextResponse {
  document_id: string
  content_hash: string
  extracted_text: string
  extraction_status: ExtractionStatus
  extraction_metadata: DocumentExtractionMetadata
}

export type CandidateEntityType =
  | 'PERSON'
  | 'PHONE'
  | 'ACCOUNT'
  | 'VEHICLE'
  | 'LOCATION'
  | 'ORGANIZATION'
  | 'DEVICE'
  | 'DATE_TIME'
  | 'EVENT'

export type CandidateResolutionStatus = 'UNRESOLVED' | 'REVIEW_REQUIRED' | 'NO_MATCH_FOUND'

export interface SourceSpan {
  start: number
  end: number
  page?: number | null
}

export interface CandidateProvenance {
  document_id: string
  document_sha256: string
  page?: number | null
  source_text_hash: string
  case_id?: string | null
}

export interface ResolutionCandidateMatch {
  canonical_entity_id: string
  canonical_name: string
  entity_type: string
  match_score: number
  match_reasons: string[]
}

export interface CandidateEntity {
  candidate_id: string
  entity_type: CandidateEntityType | string
  surface_text: string
  normalized_value: string
  confidence: number
  source_document_id: string
  case_id?: string | null
  source_span: SourceSpan
  evidence_text: string
  extraction_method: 'DETERMINISTIC' | 'LLM_ASSISTED' | string
  provenance: CandidateProvenance
  resolution_status: CandidateResolutionStatus
  resolution_candidates: ResolutionCandidateMatch[]
  status?: string | null
  resulting_graph_id?: string | null
}

export interface CandidateRelationship {
  candidate_relationship_id: string
  source_candidate_id: string
  target_candidate_id: string
  source_text: string
  target_text: string
  relationship_type: string
  confidence: number
  evidence_text: string
  source_document_id: string
  case_id?: string | null
  source_span?: SourceSpan | null
  provenance: CandidateProvenance
  status: 'CANDIDATE' | 'ACCEPTED' | 'REJECTED' | string
  resulting_edge_id?: string | null
}

export interface DocumentExtractionResult {
  document_id: string
  case_id?: string | null
  content_hash: string
  extraction_run_id: string
  extracted_at: string
  candidate_entities: CandidateEntity[]
  candidate_relationships: CandidateRelationship[]
  entity_count: number
  relationship_count: number
  status: string
  extraction_notes: string[]
}

// ── Investigator Confirmation & Graph Promotion (P1-C) ─────────────────────

export type CandidateDecisionAction =
  | 'ACCEPT_EXISTING'
  | 'ACCEPT_NEW'
  | 'ACCEPT_RELATIONSHIP'
  | 'REJECT'

export type CandidateDecisionStatus =
  | 'PENDING'
  | 'ACCEPTED_EXISTING_ENTITY'
  | 'ACCEPTED_NEW_ENTITY'
  | 'ACCEPTED_RELATIONSHIP'
  | 'REJECTED'

export interface AcceptExistingEntityRequest {
  target_canonical_id: string
  case_id?: string | null
  notes?: string | null
}

export interface AcceptNewEntityRequest {
  entity_type: string
  canonical_name: string
  case_id?: string | null
  properties?: Record<string, unknown>
  notes?: string | null
}

export interface AcceptRelationshipRequest {
  source_canonical_id: string
  target_canonical_id: string
  relationship_type: string
  case_id?: string | null
  properties?: Record<string, unknown>
  notes?: string | null
}

export interface RejectCandidateRequest {
  reason: string
  notes?: string | null
}

export interface CandidateDecisionResponse {
  decision_id: string
  candidate_id: string
  candidate_type: 'ENTITY' | 'RELATIONSHIP' | string
  action: CandidateDecisionAction | string
  status: CandidateDecisionStatus | string
  decided_by: string
  decided_at: string
  target_id?: string | null
  resulting_graph_id?: string | null
  reason?: string | null
  notes?: string | null
  audit_event_id?: string | null
  propagation_status?: string | null
  propagation_snapshot_id?: string | null
}

export type NodePresenceType =
  | 'DIRECT_CASE'
  | 'INTELLIGENCE_EXPANSION'
  | 'CDR_CONNECTION'
  | 'CROSS_CASE'
  | 'EVIDENCE'
  | 'OTHER'

export interface NodeContextResponse {
  presence_type: NodePresenceType
  reason: string
  source_ids: string[]
  relationship_types: string[]
  distance_from_case: number
  path: string[]
  readable_path?: string
}

export interface GraphNodeResponse {
  id: string
  entity_type: string
  label: string
  properties: Record<string, any>
  degree: number
  confidence: number
  context?: NodeContextResponse
}

export interface GraphEdgeResponse {
  id: string
  source_id: string
  target_id: string
  edge_type: string
  weight: number
  provenance: EvidenceProvenanceContract
  properties: Record<string, any>
}

export interface NetworkGraphResponse {
  nodes: GraphNodeResponse[]
  edges: GraphEdgeResponse[]
  total_nodes: number
  total_edges: number
  case_id?: string
  depth?: number
}

export interface EntityResolutionQuery {
  full_name?: string
  phone_number?: string
  vehicle_number?: string
  address_text?: string
  national_id?: string
  aliases?: string[]
  confidence_threshold?: number
  candidate_limit?: number
}

export interface EntityResolutionMatchResponse {
  matched_node_id: string
  confidence: number
  status: ResolutionStatus
  matched_fields: string[]
  reason: string
  evidence_breakdown: Record<string, number>
  properties: Record<string, any>
  search_relevance?: number
  resolution_state?: string
  evidence_families?: string[]
  supporting_factors?: string[]
  conflicting_factors?: string[]
  independent_sources?: number
  explanation?: string
}

export interface EntityResolutionResponse {
  query: Record<string, any>
  matches: EntityResolutionMatchResponse[]
  total_matches: number
}

export interface CommunityResponse {
  community_id: string
  size: number
  member_ids: string[]
  dominant_entity_type: string
  top_influencer_id: string
  reason: string
}

export interface BridgeNodeResponse {
  node_id: string
  entity_type: string
  label: string
  connected_components_count: number
  betweenness_score: number
  reason: string
}

export interface InfluenceRankingResponse {
  node_id: string
  label: string
  entity_type: string
  degree_centrality: number
  betweenness_centrality: number
  rank: number
}

export interface RepeatOffenderResponse {
  person_id: string
  person_name: string
  case_ids: string[]
  case_count: number
  reason: string
}

export interface SharedClusterResponse {
  cluster_id: string
  cluster_type: string
  person_ids: string[]
  case_ids: string[]
  reason: string
}

export type TimelineEventCategory =
  | 'CASE_REGISTRATION'
  | 'EVIDENCE_DOCUMENT'
  | 'COMMUNICATION'
  | 'FINANCIAL_TRANSACTION'
  | 'SURVEILLANCE_SIGHTING'
  | 'INVESTIGATOR_ACTION'
  | 'GRAPH_CHANGE'
  | 'INTELLIGENCE_SIGNAL'
  | 'EVIDENCE_ASSESSMENT'
  | 'VERIFICATION_WORKFLOW'
  | 'CROSS_CASE_ROUTE'

export interface TimelineEventResponse {
  id: string
  event_type: string
  timestamp: string
  description: string
  participant_ids: string[]
  location_id?: string
  case_id?: string
  category?: TimelineEventCategory
  occurred_at?: string
  recorded_at?: string
  title?: string
  edge_ids?: string[]
  source_type?: string
  source_id?: string
  locator?: string
  actor_id?: string
  actor_role?: UserRole
  intelligence_event_id?: string
  evidence_refs?: string[]
  snapshot_id?: string
  route_id?: string
  task_id?: string
  assessment_id?: string
  properties?: Record<string, unknown>
}

export interface TimelineQueryResponse {
  events: TimelineEventResponse[]
  total_count: number
  case_id?: string
  entity_id?: string
  limit: number
  offset: number
  has_more: boolean
}


export interface InvestigationSummaryResponse {
  id: string
  fir_number: string
  title?: string
  station_name: string
  district?: string
  offence_category: string
  status?: string
  updated_at?: string
  accused_count?: number
  evidence_count?: number
  priority_rank?: number
  clock?: ClockResponse
  unresolved_dependency_count?: number
  risk_rank?: number
}

export interface InvestigationDetailResponse {
  id: string
  fir_number: string
  title?: string
  station_name: string
  district?: string
  offence_category: string
  incident_date?: string
  status?: string
  summary?: string
  sections?: string[]
  accused?: Record<string, any>[]
  victims?: Record<string, any>[]
  evidence?: EvidenceItemResponse[]
  updated_at?: string
  clocks?: ClockResponse[]
  dependencies?: DependencyResponse[]
}

export type CaseDetailResponse = InvestigationDetailResponse


export interface GroundedCitation {
  source_type: string
  source_id: string
  fact: string
  confidence: number
}

export interface CaseCollectionItem {
  case_id: string
  fir_number: string
  title: string
  offence_category: string
  district: string
  station_name: string
  status: string
  updated_at?: string
  summary?: string
}

export interface CopilotQueryRequest {
  query: string
  case_id?: string
  investigation_id?: string
  session_id?: string
  /** Entity-centric query parameters (used by Copilot structured dispatch) */
  entity_id?: string
  max_hops?: number
  is_resolved?: boolean
}

export interface CopilotQueryResponse {
  query: string
  intent: string
  answer: string
  is_refusal: boolean
  refusal_reason?: string
  grounded_citations: GroundedCitation[]
  suggested_actions: string[]
  graph_context?: NetworkGraphResponse
  evidence_ids?: string[]
  reasoning_path?: string[]
  case_id?: string
  collection_results?: CaseCollectionItem[]
  total_count?: number
  query_type?: string
}

export interface AuditLogEntry {
  id: string
  user_id: string
  user_role: string
  action: string
  entity_type?: string
  entity_id?: string
  details: Record<string, any>
  timestamp: string
}

export interface AuthLoginRequest {
  username: string
  password?: string
  role?: UserRole
}

export interface AuthTokenResponse {
  access_token: string
  token_type: string
  user_id: string
  role: UserRole
  expires_in: number
}

// ── Entity Profile ─────────────────────────────────────────────────────────────

/** Full profile of a graph entity, including evidence and centrality data. */
export interface EntityProfileResponse {
  entity_id: string
  entity_type: string
  label: string
  properties: Record<string, any>
  aliases: string[]
  degree: number
  community_id?: string
  betweenness_score?: number
  evidence_items: EvidenceItemResponse[]
}

// ── Evidence Verification (BE-04) ──────────────────────────────────────────

/** SHA-256 hash chain verification result for Section 63 BSA 2023 compliance. */
export interface EvidenceVerificationResponse {
  evidence_hashes: Record<string, string>  // evidence_id -> sha256
  chain_hash: string
  verified_at: string
  verification_status: 'VERIFIED' | 'INCOMPLETE'
}

export interface EvidenceVerifyRequest {
  evidence_ids: string[]
  path_node_ids: string[]
}

// ── BSA Dossier Export (BE-05) ───────────────────────────────────────────────

/** Request body for POST /export/dossier (Section 63 BSA 2023 workflow). */
export interface DossierExportRequest {
  case_id: string
  include_network: boolean
  include_evidence: boolean
  include_hash_chain: boolean
}

export interface DossierExportResponse {
  case_id: string
  sha256_hash: string
  generated_at: string
  page_count: number
  file_size_bytes: number
}

export interface NexusDossierRequest {
  case_id?: string
  lead_id?: string
  evidence_ids?: string[]
  include_network?: boolean
  include_evidence?: boolean
  include_hash_chain?: boolean
}

export interface NexusDossierResponse {
  dossier_id: string
  case_id?: string
  case_ids: string[]
  lead_id?: string
  pdf_sha256: string
  chain_hash: string
  evidence_ids: string[]
  evidence_hashes: Record<string, string>
  generated_at: string
  page_count: number
  file_size_bytes: number
  download_url: string
}

export interface EvidenceIntegrityCheckResult {
  evidence_id: string
  expected_hash: string
  computed_hash: string
  verified: boolean
  verification_timestamp?: string
  failure_reason?: string
}

export interface EvidenceBatchVerifyRequest {
  evidence_ids?: string[]
  dossier_id?: string
}

export interface EvidenceBatchVerifyResponse {
  results: EvidenceIntegrityCheckResult[]
  overall_verified: boolean
  chain_hash: string
  verified_at: string
}

export interface NexusDossierVerificationResponse {
  dossier_id: string
  expected_hash: string
  computed_hash: string
  verified: boolean
  verification_timestamp: string
}


// ── File Ingestion ─────────────────────────────────────────────────────────────

/** Multi-source ingestion request body for POST /ingest. */
export interface IngestRequest {
  source_type: 'CDR' | 'BANK_TXN' | 'FIR' | 'INTEL_REPORT' | 'SURVEILLANCE_REPORT'
  file_name: string
  records: Record<string, any>[]
}

export interface IngestResponse {
  ingested_count: number
  skipped_count: number
  error_count: number
  audit_event_id: string
}

// ── NEXUS Prototype Contract Types ──────────────────────────────────────────

export interface NexusSourceRecord {
  id: string
  batch_id: string
  source_type: string
  locator: string
  raw_excerpt: string
  case_ids?: string[]
  hash_algorithm?: string
  content_hash?: string
  hash_version?: string
  hashed_at?: string
  occurred_at: string
}

export interface NexusGraphNode {
  id: string
  entity_type: string
  label: string
  case_ids: string[]
  badges?: string[]
  properties: Record<string, any>
}

export interface NexusGraphEdge {
  id: string
  source_id: string
  target_id: string
  edge_type: string
  weight: number
  confidence: number
  derivation_class: 'FACT' | 'DERIVED' | 'HYPOTHESIS'
  recorded_at: string
  case_ids: string[]
  properties: Record<string, any>
}

export interface NexusNetworkResponse {
  snapshot_id: string
  state: 'before' | 'after' | string
  nodes: NexusGraphNode[]
  edges: NexusGraphEdge[]
  total_nodes: number
  total_edges: number
  dataset_version?: string
}

export interface SnapshotDiffResponse {
  before_snapshot_id: string
  after_snapshot_id: string
  added_node_ids: string[]
  removed_node_ids: string[]
  changed_node_ids: string[]
  added_edge_ids: string[]
  removed_edge_ids: string[]
  changed_edge_ids: string[]
  dataset_version?: string
}

export interface ResolutionCandidateRecord {
  node_id: string
  entity_type: string
  label: string
  case_ids: string[]
  properties: Record<string, any>
  source_records: NexusSourceRecord[]
}

export interface ResolutionCandidate {
  id: string
  score: number
  status: 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'DEFERRED'
  left: ResolutionCandidateRecord
  right: ResolutionCandidateRecord
  reasons: { field: string; detail: string; weight: number }[]
  conflicts: { field: string; left_value: string; right_value: string }[]
  decided_at?: string
  decided_by?: string
}

export interface ResolutionDecisionRequest {
  decision: 'CONFIRM' | 'REJECT' | 'DEFER'
  decided_by: string
  note?: string
}

export interface ResolutionDecisionResponse {
  candidate_id: string
  status: string
  affected_node_ids: string[]
  new_snapshot_id?: string
}

export interface NexusEdgeEvidenceResponse {
  relationship_id: string
  edge_type: string
  source_label: string
  target_label: string
  derivation_class: 'FACT' | 'DERIVED' | 'HYPOTHESIS'
  confidence: number
  recorded_at: string
  source_records: NexusSourceRecord[]
  derivation_chain: { step: number; rule: string; inputs: string[] }[]
}

export interface NexusPathResponse {
  found: boolean
  source_id: string
  target_id: string
  node_ids: string[]
  edge_ids: string[]
  hops: number
  explanation: string
  evidence_ids: string[]
}

export interface NexusLead {
  id: string
  title: string
  rule_id: string
  explanation: string
  severity: string
  review_priority?: 'HIGH' | 'MEDIUM' | 'LOW'
  priority_factors?: Record<string, string>
  why_prioritized?: string[]
  derivation_class: 'FACT' | 'DERIVED' | 'HYPOTHESIS'
  case_ids: string[]
  entity_ids?: string[]
  status: 'NEW' | 'ACCEPTED' | 'REJECTED'
  path: { node_ids: string[]; edge_ids: string[] }
  evidence_ids: string[]
  citations?: GroundedCitation[]
  reasoning_path?: string[]
  created_at: string
  generation_mode?: 'REAL_LLM' | 'MOCK_LLM_TEST' | 'DETERMINISTIC_FALLBACK'
  lead_type?: string
  decided_at?: string
  decided_by?: string
  decision_note?: string
}

export interface NexusLeadDecisionRequest {
  decision: 'ACCEPT' | 'REJECT'
  decided_by: string
  note?: string
}

export interface NexusCopilotResponse {
  query: string
  answer: string
  is_refusal: boolean
  refusal_reason?: string
  evidence_ids: string[]
  reasoning_path: string[]
  intent?: string
  grounded_citations?: GroundedCitation[]
  suggested_actions?: string[]
  graph_context?: NetworkGraphResponse
  case_id?: string
  collection_results?: CaseCollectionItem[]
}

export interface NexusSearchResponse {
  query: string
  cases: { id: string; fir_number: string; title: string; score: number }[]
  entities: { id: string; label: string; entity_type: string; case_ids: string[]; score: number; subtext?: string }[]
}


// ── Real Ingestion API ────────────────────────────────────────────────────────

export type BatchStatus = 'COMPLETED' | 'COMPLETED_WITH_WARNINGS' | 'FAILED'

export interface IngestionFileSummary {
  received: number
  accepted: number
  rejected: number
  duplicates: number
  conflicts: number
  warnings: number
  source_records: number
  nodes_created: number
  nodes_reused: number
  relationships_created: number
  review_required: number
}

export interface IngestionFileResult {
  source_type: string
  file_name: string
  size_bytes: number
  summary: IngestionFileSummary
}

export interface IngestionParseIssue {
  source_type: string
  file_name: string
  row_number?: number
  record_id?: string
  field?: string
  code: string
  message: string
  severity: string
}

export interface IngestionBatchResponse {
  batch_id: string
  status: BatchStatus
  files_processed: IngestionFileResult[]
  summary: IngestionFileSummary
  parse_issues: IngestionParseIssue[]
  review_candidates: Record<string, any>[]
  graph_updated: boolean
}

export interface NexusIngestResponse {
  status: string
  batch_id: string
  files_processed: string[]
  received_rows: number
  accepted_rows: number
  rejected_rows: number
  duplicates: number
  conflicts: number
  warnings: number
  nodes_extracted: number
  relations_formed: number
  source_records: number
  review_required: number
  provenance_completeness: number
  graph_ready: boolean
}

// ── Hotspot Intelligence & Repeat Offender Radar ─────────────────────────────

export interface DominantCategoryItem {
  category: string
  count: number
  percentage: number
}

export interface DistrictHotspotIntelligence {
  district: string
  case_count: number
  baseline_cases: number
  concentration_multiplier: number
  dominant_categories: DominantCategoryItem[]
  cross_case_links_count: number
  repeat_offender_overlap_count: number
  repeat_offender_ids: string[]
  repeat_offender_names: string[]
  evidence_backed: boolean
  evidence_ids: string[]
  alert_level: 'RED' | 'AMBER' | 'GREEN'
  summary_reason: string
}

export interface HotspotCaseItem {
  case_id: string
  fir_number: string
  title: string
  date: string
  crime_head: string
  police_station: string
  sections: string[]
  accused_count: number
}

export interface HotspotEntityItem {
  entity_id: string
  name: string
  entity_type: string
  case_count: number
  role: string
}

export interface HotspotDrilldownResponse {
  district: string
  case_count: number
  baseline_cases: number
  concentration_multiplier: number
  cases: HotspotCaseItem[]
  entities: HotspotEntityItem[]
  repeat_offenders: Record<string, any>[]
  cross_case_links: Record<string, any>[]
  evidence_ids: string[]
  evidence: Record<string, any>[]
}

export interface SharedNetworkEntity {
  entity_id: string
  label: string
  entity_type: string
  shared_reason: string
}

export interface RecentCaseInfo {
  case_id: string
  fir_number: string
  date: string
  district: string
  crime_head: string
}

export interface RepeatOffenderRadarItem {
  person_id: string
  canonical_name: string
  aliases: string[]
  resolved_person_ids: string[]
  case_count: number
  case_ids: string[]
  fir_numbers: string[]
  districts: string[]
  district_count: number
  shared_network_entities_count: number
  shared_network_entities: SharedNetworkEntity[]
  shared_phone_identifiers: string[]
  most_recent_case?: RecentCaseInfo | null
  evidence_ids: string[]
  why_surfaced: string
  compliance_status: string
}

export interface BridgingOffenderDetail {
  person_id: string
  name: string
  home_district: string
  external_districts: string[]
  case_ids: string[]
  case_count: number
}

export interface ConnectedDistrictInfo {
  district: string
  bridging_offenders: string[]
  case_count: number
}

export interface CombinedBridgeSignal {
  signal_id: string
  primary_district: string
  primary_district_cases: number
  repeat_offender_count: number
  connected_districts: ConnectedDistrictInfo[]
  cross_district_bridge_detected: boolean
  bridging_offender_details: BridgingOffenderDetail[]
  evidence_ids: string[]
  alert_title: string
  explanation: string
}

// ── P0 Proactive Network Change Intelligence Contracts ────────────────────────

export type EpistemicState = 'SUPPORTS' | 'CONFLICTS' | 'MISSING' | 'INFERRED' | 'VERIFIED'

export type ReviewPriority = 'CRITICAL_REVIEW' | 'PRIORITY_REVIEW' | 'ROUTINE_REVIEW'

export type ForecastTarget = 
  | 'JURISDICTION_SHIFT'
  | 'COMMUNICATION_PATTERN_SHIFT'
  | 'FINANCIAL_ROUTE_TRANSITION'
  | 'IDENTIFIER_DRIFT'
  | 'NETWORK_RESTRUCTURING'

export interface EvidenceAssessmentItem {
  claim_id: string
  target_relationship_id: string
  evidence_ref: string
  state: EpistemicState
  rationale: string
  source_quality: number
  freshness_days: number
}

export interface ForecastItem {
  forecast_id: string
  pulse_id: string
  target_state: ForecastTarget
  time_window: [string, string]
  support_level: number
  uncertainty: number
  action_window: string
  suggested_verification: string
  abstained: boolean
  abstention_reason?: string | null
}

export interface VerificationActionItem {
  verification_id: string
  target_claim: string
  missing_evidence_type: string
  recommended_action: string
  responsible_role: UserRole
  status: string
  result?: string | null
}

export interface NetworkPulseItem {
  pulse_id: string
  change_ids: string[]
  signal_headline: string
  review_priority: ReviewPriority
  time_window: [string, string]
  evidence_refs: string[]
  support_level: number
  uncertainty: number
  action_window: string
  abstained: boolean
  generated_at: string
  assessment: EvidenceAssessmentItem[]
  forecast?: ForecastItem | null
  verification_plan: VerificationActionItem[]
  affected_entities: string[]
  affected_cases: string[]
}

export interface GraphSnapshotSummary {
  snapshot_id: string
  case_scope?: string | null
  created_at: string
  node_count: number
  edge_count: number
  version: string
  dataset_version?: string
}

export interface NetworkDiffResponse {
  before_snapshot_id: string
  after_snapshot_id: string
  added_nodes: string[]
  removed_nodes: string[]
  added_relationships: string[]
  removed_relationships: string[]
  modified_node_count: number
  modified_relationship_count: number
  pulses: NetworkPulseItem[]
  summary: Record<string, any>
  dataset_version?: string
}

export interface IntelligenceKPIs {
  active_pulses_count: number
  critical_pulses_count: number
  evidence_percent: number
  supported_claims: number
  total_claims: number
  affected_cases_count: number
  added_nodes: number
  added_edges: number
  total_changes: number
}

export interface IntelligenceBootstrapResponse {
  dataset_version: string
  snapshot_id: string
  baseline_snapshot_id: string
  kpis: IntelligenceKPIs
  primary_pulse?: NetworkPulseItem | null
  primary_diff?: NetworkDiffResponse | null
  affected_cases: string[]
  generated_at: string
}

export interface InvestigationContext {
  case_id?: string
  target_case_id?: string
  entity_id?: string
  evidence_id?: string
  change_id?: string
  relationship_id?: string
  snapshot_id?: string
  feature_type?: string
  focus?: '1hop' | '2hop' | 'crosscase' | 'community'
  drawer?: 'entity' | 'relationship' | 'evidence'
}

export type EpistemicDeltaState = 'OBSERVED' | 'DERIVED' | 'PROPOSED' | 'CONFIRMED'

export interface NetworkDeltaNode {
  node_id: string
  entity_type: string
  label: string
  epistemic_state: EpistemicDeltaState
  properties?: Record<string, any>
}

export interface NetworkDeltaRelationship {
  relationship_id: string
  source_id: string
  target_id: string
  edge_type: string
  epistemic_state: EpistemicDeltaState
  confidence: number
  evidence_refs: string[]
  properties?: Record<string, any>
}

export interface NetworkDelta {
  delta_id: string
  before_snapshot_id: string
  after_snapshot_id: string
  dataset_version: string
  status: EpistemicDeltaState
  triggering_evidence: string[]
  added_nodes: NetworkDeltaNode[]
  removed_node_ids: string[]
  added_relationships: NetworkDeltaRelationship[]
  removed_relationship_ids: string[]
  proposed_interpretation: string
  rationale: string
}

// ── P1-A Cross-Jurisdiction Intelligence Pulse Routing Contracts ─────────────

export type PulseDeliveryStatus = 
  | 'DISPATCHED'
  | 'DELIVERED'
  | 'ACKNOWLEDGED'
  | 'ACTIONED'
  | 'REJECTED'

export type PulseSecurityClassification = 
  | 'RESTRICTED'
  | 'CONFIDENTIAL'
  | 'SECRET'

export interface IntelligencePulsePacket {
  packet_id: string
  origin_case_id: string
  origin_district: string
  origin_officer_id: string
  target_case_id: string
  target_district: string
  target_role: UserRole
  headline: string
  summary: string
  shared_entities: string[]
  evidence_refs: string[]
  packet_hash: string
  security_classification: PulseSecurityClassification
  dispatched_at: string
  delivery_status: PulseDeliveryStatus
  acknowledged_at?: string | null
  acknowledged_by?: string | null
  acknowledgment_note?: string | null
}

export interface CreateIntelligencePulseRequest {
  origin_case_id: string
  target_case_id: string
  target_district: string
  headline: string
  summary: string
  shared_entities?: string[]
  evidence_refs?: string[]
  security_classification?: PulseSecurityClassification
}

export interface AcknowledgePulseRequest {
  decision: 'ACKNOWLEDGE' | 'ACTION' | 'REJECT'
  note?: string | null
}

// ── A14 Affected Investigation Routing Contracts ─────────────────────────────

export interface AffectedInvestigationRoute {
  route_id: string
  origin_case_id: string
  origin_district: string
  target_case_id: string
  target_district: string
  trigger_event_id?: string | null
  source_snapshot_id: string
  target_snapshot_id: string
  diff_summary: Record<string, number>
  intersecting_entity_ids: string[]
  intersecting_edge_ids: string[]
  routing_reason: string
  evidence_refs: string[]
  route_hash: string
  status: PulseDeliveryStatus
  dispatched_at: string
  acknowledged_at?: string | null
  acknowledged_by?: string | null
  acknowledgment_note?: string | null
}

export interface AcknowledgeRouteRequest {
  decision: 'ACKNOWLEDGE' | 'ACTION' | 'REJECT'
  note?: string | null
}

export interface EvaluateRoutingRequest {
  origin_case_id?: string | null
  source_snapshot_id?: string | null
  target_snapshot_id?: string | null
  trigger_event_id?: string | null
  changed_entity_ids?: string[]
  changed_edge_ids?: string[]
}

export interface RouteQueryResponse {
  total: number
  routes: AffectedInvestigationRoute[]
}

// ── P1-C Network Adaptation Engine Contracts ─────────────────────────────────

export type NetworkAdaptationType = 
  | 'INTERMEDIARY_REPLACEMENT'
  | 'BRIDGE_SUBSTITUTION'
  | 'FINANCIAL_REROUTING'
  | 'COMMUNITY_RECONNECTION'

export type AdaptationReviewStatus = 
  | 'DETECTED'
  | 'CONFIRMED'
  | 'DISMISSED'
  | 'MONITORING'

export interface NetworkAdaptationEvent {
  adaptation_id: string
  adaptation_type: NetworkAdaptationType
  primary_entity_id: string
  primary_entity_name: string
  secondary_entity_id: string
  secondary_entity_name: string
  substitute_intermediary_id?: string | null
  substitute_intermediary_name?: string | null
  previous_path: string[]
  new_path: string[]
  detected_at: string
  time_lag_days?: number | null
  structural_significance: number
  corroborating_context: string
  evidence_refs: string[]
  derivation_class: string
  review_status: AdaptationReviewStatus
  investigator_note?: string | null
  decided_at?: string | null
  decided_by?: string | null
}

export interface DecideNetworkAdaptationRequest {
  status: AdaptationReviewStatus
  note?: string | null
}

// ── P1-D Digital Shadow (SOCMINT Governance) Contracts ───────────────────────

export type DigitalShadowPlatform = 
  | 'TELEGRAM'
  | 'WHATSAPP'
  | 'DARKWEB_FORUM'
  | 'SOCIAL_MEDIA'
  | 'PAYMENT_GATEWAY'
  | 'MARKETPLACE'

export type DigitalShadowLifecycle = 
  | 'OBSERVED'
  | 'CANDIDATE_LINK'
  | 'CORROBORATED'
  | 'INVESTIGATOR_CONFIRMED'
  | 'DISMISSED'

export interface DigitalShadowCorroboration {
  corroboration_id: string
  person_id: string
  person_name: string
  platform: DigitalShadowPlatform
  digital_identifier: string
  corroborating_physical_id: string
  corroborating_physical_type: string
  confidence_score: number
  lifecycle_state: DigitalShadowLifecycle
  observation_context: string
  source_url_or_channel: string
  evidence_refs: string[]
  derivation_class: string
  first_observed_at: string
  last_verified_at?: string | null
  investigator_note?: string | null
  decided_at?: string | null
  decided_by?: string | null
}

export interface DecideDigitalShadowRequest {
  lifecycle_state: DigitalShadowLifecycle
  note?: string | null
}

// ── P2 Case DNA Explainable Structural Similarity Contracts ──────────────────

export interface CaseDNA {
  case_pair: string[]
  case_a_title: string
  case_b_title: string
  overall_similarity: number
  structure_similarity: number
  communication_similarity: number
  financial_similarity: number
  location_similarity: number
  temporal_similarity: number
  shared_entities: string[]
  explanation: string
  evidence_refs: string[]
  derivation_class: string
  dataset_version?: string
  snapshot_id?: string
}

export interface CaseDNAMatchResponse {
  target_case_id: string
  similar_cases: CaseDNA[]
  average_similarity: number
  highest_similarity: number
  top_shared_entities: string[]
  dataset_version?: string
}

// ── A3 IntelligenceEvent Unified Domain Contract ─────────────────────────────

export type IntelligenceEventType =
  | 'DOCUMENT_INGESTED'
  | 'DOCUMENT_EXTRACTED'
  | 'ENTITY_OBSERVED'
  | 'RELATIONSHIP_OBSERVED'
  | 'NETWORK_CHANGE_DETECTED'
  | 'SNAPSHOT_CREATED'
  | 'SIGNAL_GENERATED'
  | 'EVIDENCE_ASSESSED'
  | 'VERIFICATION_REQUIRED'
  | 'VERIFICATION_TASK_CREATED'
  | 'VERIFICATION_COMPLETED'
  | 'ENTITY_RESOLUTION_DECIDED'
  | 'INVESTIGATOR_DECISION'

export interface IntelligenceEvent {
  event_id: string
  event_type: IntelligenceEventType
  event_version: string
  event_timestamp: string
  case_id: string
  fir_id?: string | null
  source_id?: string | null
  evidence_refs: string[]
  snapshot_id?: string | null
  related_entity_ids: string[]
  related_edge_ids: string[]
  source_type: string
  actor_id: string
  actor_role?: UserRole | null
  observed_at?: string | null
  ingested_at: string
  processed_at?: string | null
  correlation_id?: string | null
  causation_id?: string | null
  title: string
  description: string
  payload: Record<string, unknown>
  integrity_hash?: string | null
}

export interface CreateIntelligenceEventRequest {
  event_type: IntelligenceEventType
  case_id: string
  fir_id?: string | null
  source_id?: string | null
  evidence_refs?: string[]
  snapshot_id?: string | null
  related_entity_ids?: string[]
  related_edge_ids?: string[]
  source_type?: string
  actor_id?: string | null
  actor_role?: UserRole | null
  observed_at?: string | null
  correlation_id?: string | null
  causation_id?: string | null
  title?: string
  description?: string
  payload?: Record<string, unknown>
}

export interface IntelligenceEventListResponse {
  events: IntelligenceEvent[]
  total_count: number
  case_id?: string | null
  limit: number
  offset: number
}

// ── A7 Persistent Verification Tasks Domain Contracts ────────────────────────

export type VerificationTaskStatus =
  | 'CREATED'
  | 'ASSIGNED'
  | 'REQUESTED'
  | 'RECEIVED'
  | 'UNDER_REVIEW'
  | 'VERIFIED'
  | 'DISMISSED'

export type VerificationTaskDecision = 'VERIFIED' | 'DISMISSED'

export interface TaskTransitionHistoryItem {
  from_status: VerificationTaskStatus
  to_status: VerificationTaskStatus
  actor_id: string
  timestamp: string
  rationale?: string | null
}

export interface VerificationTask {
  task_id: string
  case_id: string
  created_at: string
  updated_at: string
  originating_event_id?: string | null
  originating_pulse_id?: string | null
  target_claim: string
  reason: string
  requested_evidence_type: string
  verification_action: string
  expected_outcome?: string | null
  evidence_gap?: string | null
  assigned_officer_id?: string | null
  assigned_role?: UserRole | null
  assigned_at?: string | null
  status: VerificationTaskStatus
  history: TaskTransitionHistoryItem[]
  requested_evidence_ids: string[]
  received_evidence_ids: string[]
  supporting_evidence_ids: string[]
  conflicting_evidence_ids: string[]
  decision?: VerificationTaskDecision | null
  decision_rationale?: string | null
  deciding_actor?: string | null
  decided_at?: string | null
}

export interface CreateVerificationTaskRequest {
  case_id: string
  target_claim: string
  reason: string
  requested_evidence_type: string
  verification_action: string
  expected_outcome?: string | null
  evidence_gap?: string | null
  originating_event_id?: string | null
  originating_pulse_id?: string | null
  assigned_officer_id?: string | null
  assigned_role?: UserRole | null
}

export interface AssignVerificationTaskRequest {
  assigned_officer_id: string
  assigned_role?: UserRole | null
  rationale?: string | null
}

export interface TransitionVerificationTaskRequest {
  target_status: VerificationTaskStatus
  rationale?: string | null
}

export interface AttachEvidenceRequest {
  evidence_id: string
  relationship_type?: string
  notes?: string | null
}

export interface DecideVerificationTaskRequest {
  decision: VerificationTaskDecision
  rationale: string
}

export interface VerificationTaskListResponse {
  tasks: VerificationTask[]
  total_count: number
  case_id?: string | null
  status?: VerificationTaskStatus | null
  assignee?: string | null
  limit: number
  offset: number
}

// ── A5 Evidence Assessment Domain Contracts ────────────────────────────────────

export type AssessmentBasis =
  | 'DIRECT'
  | 'CORROBORATING'
  | 'CONFLICTING'
  | 'MISSING'
  | 'INFERRED'

export interface AssessmentRevisionHistoryItem {
  revision_number: number
  from_state: EpistemicState
  to_state: EpistemicState
  actor_id: string
  timestamp: string
  rationale: string
  evidence_ids: string[]
}

export interface EvidenceAssessment {
  assessment_id: string
  case_id: string
  created_at: string
  updated_at: string
  claim: string
  claim_type: string
  target_entity_id?: string | null
  target_edge_id?: string | null
  target_event_id?: string | null
  intelligence_event_id?: string | null
  verification_task_id?: string | null
  state: EpistemicState
  rationale: string
  assessment_basis: AssessmentBasis
  evidence_ids: string[]
  supporting_evidence_ids: string[]
  conflicting_evidence_ids: string[]
  missing_evidence_types: string[]
  source_ids: string[]
  source_types: string[]
  observed_at?: string | null
  ingested_at: string
  provenance_refs: string[]
  history: AssessmentRevisionHistoryItem[]
}

export interface CreateEvidenceAssessmentRequest {
  case_id: string
  claim: string
  claim_type?: string
  state: EpistemicState
  rationale: string
  assessment_basis?: AssessmentBasis
  target_entity_id?: string | null
  target_edge_id?: string | null
  target_event_id?: string | null
  intelligence_event_id?: string | null
  verification_task_id?: string | null
  evidence_ids?: string[]
  supporting_evidence_ids?: string[]
  conflicting_evidence_ids?: string[]
  missing_evidence_types?: string[]
}

export interface ReviseEvidenceAssessmentRequest {
  state: EpistemicState
  rationale: string
  assessment_basis?: AssessmentBasis | null
  additional_evidence_ids?: string[]
  supporting_evidence_ids?: string[] | null
  conflicting_evidence_ids?: string[] | null
  missing_evidence_types?: string[] | null
}

export interface EvidenceAssessmentListResponse {
  assessments: EvidenceAssessment[]
  total_count: number
  case_id?: string | null
  state?: EpistemicState | null
  limit: number
  offset: number
}








