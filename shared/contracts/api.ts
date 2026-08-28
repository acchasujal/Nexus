/**
 * shared/contracts/api.ts
 *
 * Authoritative TypeScript API contract types for NEXUS Criminal Intelligence Platform.
 * Kept in sync with shared/contracts/api.py.
 */

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

export interface GraphNodeResponse {
  id: string
  entity_type: string
  label: string
  properties: Record<string, any>
  degree: number
  confidence: number
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

export interface TimelineEventResponse {
  id: string
  event_type: string
  timestamp: string
  description: string
  participant_ids: string[]
  location_id?: string
  case_id?: string
}

export interface InvestigationSummaryResponse {
  id: string
  fir_number: string
  title: string
  station_name: string
  district: string
  offence_category: string
  status: string
  updated_at: string
  accused_count: number
  evidence_count: number
  priority_rank: number
}

export interface InvestigationDetailResponse {
  id: string
  fir_number: string
  title: string
  station_name: string
  district: string
  offence_category: string
  incident_date?: string
  status: string
  summary: string
  sections: string[]
  accused: Record<string, any>[]
  victims: Record<string, any>[]
  evidence: EvidenceItemResponse[]
  updated_at: string
}

export interface GroundedCitation {
  source_type: string
  source_id: string
  fact: string
  confidence: number
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

/** Request body for POST /export/dossier (Section 63 BSA 2023). */
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

// ── File Ingestion ─────────────────────────────────────────────────────────────

/** Multi-source ingestion request body for POST /ingest. */
export interface IngestRequest {
  source_type: 'CDR' | 'BANK_TXN' | 'FIR' | 'INTEL_REPORT'
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
  state: 'before' | 'after'
  nodes: NexusGraphNode[]
  edges: NexusGraphEdge[]
  total_nodes: number
  total_edges: number
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
  derivation_class: 'FACT' | 'DERIVED' | 'HYPOTHESIS'
  case_ids: string[]
  status: 'NEW' | 'ACCEPTED' | 'REJECTED'
  path: { node_ids: string[]; edge_ids: string[] }
  evidence_ids: string[]
  created_at: string
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
}

export interface NexusSearchResponse {
  query: string
  cases: { id: string; fir_number: string; title: string; score: number }[]
  entities: { id: string; label: string; entity_type: string; case_ids: string[]; score: number; subtext?: string }[]
}

export interface NexusIngestResponse {
  batch_id: string
  source_type: string
  ingested_count: number
  extraction_summary: { persons: number; phones: number; accounts: number; events: number; relationships: number }
  snapshot_id: string
}
