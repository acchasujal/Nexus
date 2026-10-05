/**
 * frontend/src/lib/apiClient.ts
 *
 * Centralized API client for NEXUS Criminal Intelligence Platform.
 */

import type {
  AcceptExistingEntityRequest,
  AcceptNewEntityRequest,
  AcceptRelationshipRequest,
  CandidateDecisionResponse,
  CandidateEntity,
  CopilotQueryRequest,
  CopilotQueryResponse,
  DocumentExtractionResult,
  DocumentResponse,
  DocumentTextResponse,
  EntityResolutionQuery,
  EntityResolutionResponse,
  InvestigationDetailResponse,
  InvestigationSummaryResponse,
  NetworkGraphResponse,
  NexusCopilotResponse,
  NexusEdgeEvidenceResponse,
  NexusIngestResponse,
  IngestionBatchResponse,
  NexusLead,
  NexusLeadDecisionRequest,
  NexusNetworkResponse,
  NexusPathResponse,
  NexusSearchResponse,
  ResolutionCandidate,
  ResolutionCandidateMatch,
  ResolutionDecisionRequest,
  RejectCandidateRequest,
  EvidenceIntegrityCheckResult,
  ResolutionDecisionResponse,
  SnapshotDiffResponse,
  EvidenceBatchVerifyResponse,
  NexusDossierRequest,
  NexusDossierResponse,
  NexusDossierVerificationResponse,
  DistrictHotspotIntelligence,
  HotspotDrilldownResponse,
  RepeatOffenderRadarItem,
  CombinedBridgeSignal,
  NexusSourceRecord,
  EntityProfileResponse,
  AuditLogEntry,
  AuthLoginRequest,
  AuthTokenResponse,
} from '@shared/contracts/api'

export class ApiError extends Error {
  readonly status: number
  readonly statusText: string

  constructor(status: number, statusText: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
  }
}

const INTELLIGENCE_REQUEST_TIMEOUT_MS = 20_000

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const origin = typeof window !== 'undefined' && window.location?.origin && window.location.origin !== 'null'
    ? window.location.origin
    : 'http://localhost'
  const rawBase = (import.meta.env.VITE_API_BASE_URL || origin).trim()
  const baseUrl = rawBase.endsWith('/') ? rawBase.slice(0, -1) : rawBase
  let savedRole = 'INVESTIGATOR'
  let token: string | null = null
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      savedRole = window.localStorage.getItem('nexus_role') || 'INVESTIGATOR'
      token = window.localStorage.getItem('nexus_token')
    }
  } catch {
    // ignore in node test environment
  }

  const method = (options?.method || 'GET').toUpperCase()
  const isMutating = method !== 'GET' && method !== 'HEAD'

  let fullUrl = `${baseUrl}${path}`
  if (!isMutating && !fullUrl.includes('role=')) {
    const separator = fullUrl.includes('?') ? '&' : '?'
    fullUrl = `${fullUrl}${separator}role=${encodeURIComponent(savedRole)}`
  }

  const isFormData = options?.body instanceof FormData

  const headers: Record<string, string> = {
    ...(
      isMutating && !isFormData
        ? { 'Content-Type': 'application/json' }
        : {}
    ),
    ...(isMutating ? { 'X-Role': savedRole } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options?.headers as Record<string, string> | undefined),
  }

  const response = await fetch(fullUrl, {
    ...options,
    signal: options?.signal ?? (!isMutating ? AbortSignal.timeout(INTELLIGENCE_REQUEST_TIMEOUT_MS) : undefined),
    headers,
  })

  if (!response.ok) {
    let message: string
    try {
      const body = await response.json() as { detail?: string; message?: string }
      message = body.detail ?? body.message ?? response.statusText
    } catch {
      message = response.statusText
    }
    if ((response.status === 401 || response.status === 403) && typeof window !== 'undefined' && window.localStorage) {
      if (message.toLowerCase().includes('token')) {
        window.localStorage.removeItem('nexus_token')
      }
    }
    throw new ApiError(response.status, response.statusText, message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

async function apiFetchBlob(path: string): Promise<Blob> {
  const origin = typeof window !== 'undefined' && window.location?.origin && window.location.origin !== 'null' ? window.location.origin : 'http://localhost'
  const rawBase = (import.meta.env.VITE_API_BASE_URL || origin).trim()
  const baseUrl = rawBase.endsWith('/') ? rawBase.slice(0, -1) : rawBase
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('nexus_token') : null
  const role = typeof window !== 'undefined' ? window.localStorage.getItem('nexus_role') || 'INVESTIGATOR' : 'INVESTIGATOR'
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), 'X-Role': role },
  })
  if (!response.ok) {
    let message = response.statusText || 'Dossier download failed'
    try {
      const body = await response.json() as { detail?: string; message?: string }
      message = body.detail ?? body.message ?? message
    } catch {
      // The response may be a non-JSON proxy or server error body.
    }
    throw new ApiError(response.status, response.statusText, message)
  }
  return response.blob()
}

export const apiClient = {
  // Authentication
  login: (req: AuthLoginRequest) => {
    return apiFetch<AuthTokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(req),
      signal: AbortSignal.timeout(INTELLIGENCE_REQUEST_TIMEOUT_MS),
    })
  },

  // Investigations
  getInvestigations: (params?: { district?: string; category?: string; status?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString()
    return apiFetch<InvestigationSummaryResponse[]>(`/api/v1/investigations${query ? `?${query}` : ''}`)
  },
  getInvestigationDetail: (caseId: string) => {
    return apiFetch<InvestigationDetailResponse>(`/api/v1/investigations/${caseId}`)
  },

  // Network Explorer
  getCaseNetwork: (caseId: string, depth = 1) => {
    return apiFetch<NetworkGraphResponse>(`/api/v1/network/cases/${encodeURIComponent(caseId)}?depth=${depth}`)
  },
  getEntityProfile: (entityId: string) => {
    return apiFetch<EntityProfileResponse>(`/api/v1/entities/${encodeURIComponent(entityId)}`)
  },
  getEntityNetwork: (entityId: string, depth = 2) => {
    return apiFetch<NetworkGraphResponse>(`/api/v1/entities/${encodeURIComponent(entityId)}/network?depth=${depth}`)
  },

  // Entity Resolution
  resolveEntities: (query: EntityResolutionQuery) => {
    return apiFetch<EntityResolutionResponse>('/api/v1/entity-resolution/resolve', {
      method: 'POST',
      body: JSON.stringify(query),
    })
  },

  // Communities & Centrality
  getCommunities: () => apiFetch<Record<string, unknown>[]>('/api/v1/communities'),
  getBridges: () => apiFetch<Record<string, unknown>[]>('/api/v1/influence/bridges'),
  getInfluenceRankings: () => apiFetch<Record<string, unknown>[]>('/api/v1/influence/rankings'),

  // Patterns
  getRepeatOffenders: () => apiFetch<Record<string, unknown>[]>('/api/v1/patterns/repeat-offenders'),
  getSharedClusters: () => apiFetch<Record<string, unknown>[]>('/api/v1/patterns/shared-clusters'),

  // Timeline & Evidence
  getTimeline: (caseId?: string) => {
    return apiFetch<Record<string, unknown>[]>(`/api/v1/timeline${caseId ? `?case_id=${caseId}` : ''}`)
  },

  // Copilot
  queryCopilot: (req: CopilotQueryRequest) => {
    return apiFetch<CopilotQueryResponse>('/api/v1/copilot/query', {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },

  // Audit
  getAuditLogs: (limit = 50) => apiFetch<AuditLogEntry[]>(`/api/v1/audit?limit=${limit}`),
  verifyAuditEvent: (eventId: string) =>
    apiFetch<{
      event_id: string
      verified: boolean
      stored_hash: string | null
      computed_hash: string
      reason: string
      previous_hash: string | null
    }>(`/api/v1/audit/${encodeURIComponent(eventId)}/verify`),

  // Blockchain Anchors (Phase 4)
  listAuditAnchors: () =>
    apiFetch<Array<{
      anchor_id: string
      batch_start: string
      batch_end: string
      event_count: number
      root_hash: string
      anchored_at: string
      creator_participant: string
      block_index: number
      block_hash: string
      ledger_id: string
    }>>('/api/v1/audit/anchors'),

  createAuditAnchor: (limit = 50) =>
    apiFetch<{
      anchor_id: string
      batch_start: string
      batch_end: string
      event_count: number
      root_hash: string
      anchored_at: string
      creator_participant: string
      ledger_id: string
    }>(`/api/v1/audit/anchors?limit=${limit}`, {
      method: 'POST',
    }),

  verifyAuditAnchor: (anchorId: string) =>
    apiFetch<{
      verified: boolean
      anchor_id: string
      root_hash: string
      block_index: number | null
      block_hash: string | null
      ledger_id: string
      reason: string
      chain_valid: boolean
      anchored_event_count: number
    }>(`/api/v1/audit/anchors/${encodeURIComponent(anchorId)}/verify`),

  getAuditEventProof: (eventId: string, anchorId?: string) =>
    apiFetch<{
      verified: boolean
      event_id: string
      event_hash: string
      anchor_id: string
      block_index: number
      block_hash: string
      root_hash: string
      leaf_index: number
      total_leaves: number
      proof: Array<{ sibling_hash: string; direction: string }>
      ledger_id: string
      participant: string
      anchored_at: string
      event_type?: string
      actor_id?: string
      timestamp?: string
    }>(`/api/v1/audit/${encodeURIComponent(eventId)}/proof${anchorId ? `?anchor_id=${encodeURIComponent(anchorId)}` : ''}`),


  // Ingestion
  ingestFiles: (files: { fir?: File, cdr?: File, bank?: File, intelligence?: File }) => {
    const formData = new FormData()
    if (files.fir) formData.append('fir', files.fir)
    if (files.cdr) formData.append('cdr', files.cdr)
    if (files.bank) formData.append('bank', files.bank)
    if (files.intelligence) formData.append('intelligence', files.intelligence)
    
    return apiFetch<IngestionBatchResponse>('/api/v1/ingest', {
      method: 'POST',
      body: formData,
    })
  },

  // ── Document Ingestion (P1-A) ───────────────────────────────────────────
  uploadDocument: (file: File, sourceType: string = 'OTHER_DOCUMENT', caseId?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_type', sourceType)
    if (caseId && caseId.trim()) {
      formData.append('case_id', caseId.trim())
    }
    return apiFetch<DocumentResponse>('/api/v1/documents', {
      method: 'POST',
      body: formData,
    })
  },
  getDocument: (documentId: string) => {
    return apiFetch<DocumentResponse>(`/api/v1/documents/${documentId}`)
  },
  getDocumentText: (documentId: string) => {
    return apiFetch<DocumentTextResponse>(`/api/v1/documents/${documentId}/text`)
  },
  listDocuments: (caseId?: string) => {
    const query = caseId ? `?case_id=${encodeURIComponent(caseId)}` : ''
    return apiFetch<DocumentResponse[]>(`/api/v1/documents${query}`)
  },

  // ── Candidate Intelligence & Entity Extraction (P1-B) ───────────────────
  extractDocumentCandidates: (documentId: string, forceReextract: boolean = false) => {
    const query = forceReextract ? '?force_reextract=true' : ''
    return apiFetch<DocumentExtractionResult>(`/api/v1/documents/${encodeURIComponent(documentId)}/extract${query}`, {
      method: 'POST',
    })
  },
  getDocumentCandidates: (documentId: string) => {
    return apiFetch<DocumentExtractionResult>(`/api/v1/documents/${encodeURIComponent(documentId)}/candidates`)
  },
  getCandidateEntity: (candidateId: string) => {
    return apiFetch<CandidateEntity>(`/api/v1/candidates/${encodeURIComponent(candidateId)}`)
  },
  getCandidateResolution: (candidateId: string) => {
    return apiFetch<ResolutionCandidateMatch[]>(`/api/v1/candidates/${encodeURIComponent(candidateId)}/resolution`)
  },

  // ── Candidate Promotion & Graph Mutation (P1-C) ─────────────────────────
  acceptExistingEntity: (candidateId: string, req: AcceptExistingEntityRequest) => {
    return apiFetch<CandidateDecisionResponse>(`/api/v1/candidates/${encodeURIComponent(candidateId)}/accept-entity`, {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },
  acceptNewEntity: (candidateId: string, req: AcceptNewEntityRequest) => {
    return apiFetch<CandidateDecisionResponse>(`/api/v1/candidates/${encodeURIComponent(candidateId)}/accept-new`, {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },
  rejectCandidateEntity: (candidateId: string, req: RejectCandidateRequest) => {
    return apiFetch<CandidateDecisionResponse>(`/api/v1/candidates/${encodeURIComponent(candidateId)}/reject`, {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },
  acceptCandidateRelationship: (relationshipId: string, req: AcceptRelationshipRequest) => {
    return apiFetch<CandidateDecisionResponse>(`/api/v1/candidate-relationships/${encodeURIComponent(relationshipId)}/accept`, {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },
  rejectCandidateRelationship: (relationshipId: string, req: RejectCandidateRequest) => {
    return apiFetch<CandidateDecisionResponse>(`/api/v1/candidate-relationships/${encodeURIComponent(relationshipId)}/reject`, {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },
  getCandidateDecisions: (candidateId: string) => {
    return apiFetch<CandidateDecisionResponse[]>(`/api/v1/candidates/${encodeURIComponent(candidateId)}/decisions`)
  },

  // ── NEXUS prototype endpoints (frozen M4 contract) ──────────────────────
  nexusIngest: (files: { fir?: File, cdr?: File, bank?: File, intelligence?: File, surveillance?: File }) => {
    const formData = new FormData()
    if (files.fir) formData.append('fir', files.fir)
    if (files.cdr) formData.append('cdr', files.cdr)
    if (files.bank) formData.append('bank', files.bank)
    if (files.intelligence) formData.append('intelligence', files.intelligence)
    if (files.surveillance) formData.append('surveillance', files.surveillance)
    
    return apiFetch<NexusIngestResponse>('/api/v1/nexus/ingest', {
      method: 'POST',
      body: formData,
    })
  },
  getBatchNetwork: (batchId: string) => {
    return apiFetch<NexusNetworkResponse>(`/api/v1/nexus/batches/${batchId}/network`)
  },
  getResolutionCandidates: () => {
    return apiFetch<ResolutionCandidate[]>('/api/v1/nexus/resolution/candidates')
  },
  decideResolutionCandidate: (id: string, req: ResolutionDecisionRequest) => {
    return apiFetch<ResolutionDecisionResponse>(`/api/v1/nexus/resolution/${id}/decision`, {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },
  getNexusNetwork: (params?: {
    snapshot?: 'before' | 'after'
    snapshot_id?: string
    case_id?: string
    target_case_id?: string
    entity_id?: string
    node_id?: string
    focus?: string
    entity_types?: string[]
    case_ids?: string[]
  }) => {
    const query = new URLSearchParams()
    if (params?.snapshot) query.set('snapshot', params.snapshot)
    if (params?.snapshot_id) query.set('snapshot_id', params.snapshot_id)
    if (params?.case_id) query.set('case_id', params.case_id)
    if (params?.target_case_id) query.set('target_case_id', params.target_case_id)
    if (params?.entity_id) query.set('entity_id', params.entity_id)
    if (params?.node_id) query.set('node_id', params.node_id)
    if (params?.focus) query.set('focus', params.focus)
    if (params?.entity_types?.length) query.set('entity_types', params.entity_types.join(','))
    if (params?.case_ids?.length) query.set('case_ids', params.case_ids.join(','))
    const qs = query.toString()
    return apiFetch<NexusNetworkResponse>(`/api/v1/nexus/network${qs ? `?${qs}` : ''}`)
  },
  getSnapshotDiff: () => apiFetch<SnapshotDiffResponse>('/api/v1/nexus/network/diff'),
  getEdgeEvidence: (relationshipId: string) => {
    return apiFetch<NexusEdgeEvidenceResponse>(`/api/v1/nexus/relationships/${relationshipId}/evidence`)
  },
  verifySourceRecord: (sourceId: string) => {
    return apiFetch<EvidenceIntegrityCheckResult>(`/api/v1/nexus/sources/${sourceId}/verify`, { method: 'POST' })
  },
  findNexusPath: (sourceId: string, targetId: string, maxDepth = 6) => {
    return apiFetch<NexusPathResponse>(`/api/v1/nexus/path?source=${encodeURIComponent(sourceId)}&target=${encodeURIComponent(targetId)}&max_depth=${maxDepth}`)
  },
  getLeads: () => apiFetch<NexusLead[]>('/api/v1/nexus/leads'),
  scanLeads: () => apiFetch<NexusLead[]>('/api/v1/nexus/leads/scan', { method: 'POST' }),
  decideLead: (id: string, req: NexusLeadDecisionRequest) => {
    return apiFetch<NexusLead>(`/api/v1/nexus/leads/${id}/decision`, {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },
  queryNexusCopilot: (query: string, entityIdOrOptions?: string | { entityId?: string; caseId?: string }) => {
    const entityId = typeof entityIdOrOptions === 'string' ? entityIdOrOptions : entityIdOrOptions?.entityId
    const caseId = typeof entityIdOrOptions === 'object' ? entityIdOrOptions?.caseId : undefined
    return apiFetch<NexusCopilotResponse>('/api/v1/nexus/copilot/query', {
      method: 'POST',
      body: JSON.stringify({ query, entity_id: entityId, case_id: caseId }),
    })
  },
  nexusSearch: (q: string) => {
    return apiFetch<NexusSearchResponse>(`/api/v1/nexus/search?q=${encodeURIComponent(q)}`)
  },
  getSourceRecord: (sourceId: string) => {
    return apiFetch<NexusSourceRecord>(`/api/v1/nexus/sources/${encodeURIComponent(sourceId)}`)
  },
  resetDemo: () => apiFetch<{ status: string }>('/api/v1/nexus/demo/reset', { method: 'POST' }),
  generateEvidenceDossier: (request: NexusDossierRequest) => apiFetch<NexusDossierResponse>('/api/v1/nexus/evidence/dossier', {
    method: 'POST',
    body: JSON.stringify(request),
  }),
  downloadEvidenceDossier: (dossierId: string) => apiFetchBlob(`/api/v1/nexus/evidence/dossier/${encodeURIComponent(dossierId)}/download`),
  verifyEvidence: (request: { evidence_ids: string[]; dossier_id?: string }) => apiFetch<EvidenceBatchVerifyResponse>('/api/v1/nexus/evidence/verify', {
    method: 'POST',
    body: JSON.stringify(request),
  }),
  verifyEvidenceDossier: (dossierId: string) => apiFetch<NexusDossierVerificationResponse>(`/api/v1/nexus/evidence/dossier/${encodeURIComponent(dossierId)}/verify`, { method: 'POST' }),

  // ── Intelligence Hub Methods ──────────────────────────────────────────────
  getIntelligenceHotspots: () => apiFetch<DistrictHotspotIntelligence[]>('/api/v1/nexus/intelligence/hotspots'),
  getHotspotDrilldown: (district: string) => apiFetch<HotspotDrilldownResponse>(`/api/v1/nexus/intelligence/hotspots/${encodeURIComponent(district)}`),
  getRepeatOffenderRadar: (minCases = 2, topK = 50) => apiFetch<RepeatOffenderRadarItem[]>(`/api/v1/nexus/intelligence/offenders?min_cases=${minCases}&top_k=${topK}`),
  getOffenderRadarProfile: (personId: string) => apiFetch<RepeatOffenderRadarItem>(`/api/v1/nexus/intelligence/offenders/${encodeURIComponent(personId)}`),
  getCombinedBridgeSignals: () => apiFetch<CombinedBridgeSignal[]>('/api/v1/nexus/intelligence/combined'),

  // ── P0 Proactive Network Change Intelligence Methods ──────────────────────
  getSnapshots: (caseScope?: string) => 
    apiFetch<import('@shared/contracts/api').GraphSnapshotSummary[]>(
      caseScope ? `/api/v1/nexus/snapshots?case_scope=${encodeURIComponent(caseScope)}` : '/api/v1/nexus/snapshots'
    ),
  getProactiveDiff: (before = 'snap-baseline-v1', after = 'snap-current') =>
    apiFetch<import('@shared/contracts/api').NetworkDiffResponse>(
      `/api/v1/nexus/diff?before=${encodeURIComponent(before)}&after=${encodeURIComponent(after)}`
    ),
  getPulses: (priority?: string, caseId?: string) => {
    const params = new URLSearchParams()
    if (priority) params.append('priority', priority)
    if (caseId) params.append('case_id', caseId)
    const qs = params.toString()
    return apiFetch<import('@shared/contracts/api').NetworkPulseItem[]>(
      qs ? `/api/v1/nexus/pulses?${qs}` : '/api/v1/nexus/pulses',
      { signal: AbortSignal.timeout(INTELLIGENCE_REQUEST_TIMEOUT_MS) },
    )
  },
  getIntelligenceBootstrap: () =>
    apiFetch<import('@shared/contracts/api').IntelligenceBootstrapResponse>(
      '/api/v1/nexus/intelligence/bootstrap',
      { signal: AbortSignal.timeout(INTELLIGENCE_REQUEST_TIMEOUT_MS) },
    ),

  // ── P1-A Cross-Jurisdiction Intelligence Pulse Dissemination Methods ─────
  getIntelligencePulseInbox: (caseId?: string, district?: string) => {
    const params = new URLSearchParams()
    if (caseId) params.append('case_id', caseId)
    if (district) params.append('district', district)
    const qs = params.toString()
    return apiFetch<import('@shared/contracts/api').IntelligencePulsePacket[]>(
      qs ? `/api/v1/nexus/intelligence/pulses/inbox?${qs}` : '/api/v1/nexus/intelligence/pulses/inbox'
    )
  },
  dispatchIntelligencePulse: (req: import('@shared/contracts/api').CreateIntelligencePulseRequest) =>
    apiFetch<import('@shared/contracts/api').IntelligencePulsePacket>('/api/v1/nexus/intelligence/pulses/dispatch', {
      method: 'POST',
      body: JSON.stringify(req),
    }),
  acknowledgeIntelligencePulse: (packetId: string, req: import('@shared/contracts/api').AcknowledgePulseRequest) =>
    apiFetch<import('@shared/contracts/api').IntelligencePulsePacket>(
      `/api/v1/nexus/intelligence/pulses/${encodeURIComponent(packetId)}/acknowledge`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    ),

  // ── P1-B Identity Drift Radar Methods ──────────────────────────────────────
  getIdentityDrifts: (personId?: string, driftType?: string, status?: string) => {
    const params = new URLSearchParams()
    if (personId) params.append('person_id', personId)
    if (driftType) params.append('drift_type', driftType)
    if (status) params.append('status', status)
    const qs = params.toString()
    return apiFetch<import('@shared/contracts/api').IdentityDriftEvent[]>(
      qs ? `/api/v1/nexus/intelligence/identity-drift?${qs}` : '/api/v1/nexus/intelligence/identity-drift'
    )
  },
  decideIdentityDrift: (driftId: string, req: import('@shared/contracts/api').DecideIdentityDriftRequest) =>
    apiFetch<import('@shared/contracts/api').IdentityDriftEvent>(
      `/api/v1/nexus/intelligence/identity-drift/${encodeURIComponent(driftId)}/decide`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    ),
  getIdentityDriftSummary: () =>
    apiFetch<Record<string, any>>('/api/v1/nexus/intelligence/identity-drift/summary'),

  // ── P1-C Network Adaptation Radar Methods ──────────────────────────────────
  getNetworkAdaptations: (adaptationType?: string, status?: string) => {
    const params = new URLSearchParams()
    if (adaptationType) params.append('adaptation_type', adaptationType)
    if (status) params.append('status', status)
    const qs = params.toString()
    return apiFetch<import('@shared/contracts/api').NetworkAdaptationEvent[]>(
      qs ? `/api/v1/nexus/intelligence/network-adaptation?${qs}` : '/api/v1/nexus/intelligence/network-adaptation'
    )
  },
  decideNetworkAdaptation: (adaptationId: string, req: import('@shared/contracts/api').DecideNetworkAdaptationRequest) =>
    apiFetch<import('@shared/contracts/api').NetworkAdaptationEvent>(
      `/api/v1/nexus/intelligence/network-adaptation/${encodeURIComponent(adaptationId)}/decide`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    ),
  getNetworkAdaptationSummary: () =>
    apiFetch<Record<string, any>>('/api/v1/nexus/intelligence/network-adaptation/summary'),

  // ── P1-D Digital Shadow (SOCMINT Governance) Methods ───────────────────────
  getDigitalShadows: (personId?: string, platform?: string, lifecycleState?: string) => {
    const params = new URLSearchParams()
    if (personId) params.append('person_id', personId)
    if (platform) params.append('platform', platform)
    if (lifecycleState) params.append('lifecycle_state', lifecycleState)
    const qs = params.toString()
    return apiFetch<import('@shared/contracts/api').DigitalShadowCorroboration[]>(
      qs ? `/api/v1/nexus/intelligence/digital-shadow?${qs}` : '/api/v1/nexus/intelligence/digital-shadow'
    )
  },
  decideDigitalShadow: (corroborationId: string, req: import('@shared/contracts/api').DecideDigitalShadowRequest) =>
    apiFetch<import('@shared/contracts/api').DigitalShadowCorroboration>(
      `/api/v1/nexus/intelligence/digital-shadow/${encodeURIComponent(corroborationId)}/decide`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    ),
  getDigitalShadowSummary: () =>
    apiFetch<Record<string, any>>('/api/v1/nexus/intelligence/digital-shadow/summary'),

  // ── P2 Case DNA Explainable Structural Similarity Methods ─────────────────
  getCaseDNA: (caseId: string, topK?: number) => {
    const params = new URLSearchParams()
    if (topK) params.append('top_k', String(topK))
    const qs = params.toString()
    return apiFetch<import('@shared/contracts/api').CaseDNAMatchResponse>(
      qs ? `/api/v1/nexus/intelligence/case-dna/${encodeURIComponent(caseId)}?${qs}` : `/api/v1/nexus/intelligence/case-dna/${encodeURIComponent(caseId)}`
    )
  },
}




