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
