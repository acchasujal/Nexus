/**
 * frontend/src/lib/apiClient.ts
 *
 * Centralized API client for NEXUS Criminal Intelligence Platform.
 */

import type {
  CopilotQueryRequest,
  CopilotQueryResponse,
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
  ResolutionDecisionRequest,
  ResolutionDecisionResponse,
  SnapshotDiffResponse,
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

export const apiClient = {
  // Investigations
  getInvestigations: (params?: { district?: string; category?: string; status?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString()
    return apiFetch<InvestigationSummaryResponse[]>(`/api/v1/investigations${query ? `?${query}` : ''}`)
  },
  getInvestigationDetail: (caseId: string) => {
    return apiFetch<InvestigationDetailResponse>(`/api/v1/investigations/${caseId}`)
  },

  // Network Explorer
  getCaseNetwork: (caseId: string, depth = 2) => {
    return apiFetch<NetworkGraphResponse>(`/api/v1/network/cases/${caseId}?depth=${depth}`)
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
  getAuditLogs: (limit = 50) => apiFetch<Record<string, unknown>[]>(`/api/v1/audit?limit=${limit}`),

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

  // ── NEXUS prototype endpoints (frozen M4 contract) ──────────────────────
  nexusIngest: (files: { fir?: File, cdr?: File, bank?: File, intelligence?: File }) => {
    const formData = new FormData()
    if (files.fir) formData.append('fir', files.fir)
    if (files.cdr) formData.append('cdr', files.cdr)
    if (files.bank) formData.append('bank', files.bank)
    if (files.intelligence) formData.append('intelligence', files.intelligence)
    
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
    entity_types?: string[]
    case_ids?: string[]
  }) => {
    const query = new URLSearchParams()
    if (params?.snapshot) query.set('snapshot', params.snapshot)
    if (params?.entity_types?.length) query.set('entity_types', params.entity_types.join(','))
    if (params?.case_ids?.length) query.set('case_ids', params.case_ids.join(','))
    const qs = query.toString()
    return apiFetch<NexusNetworkResponse>(`/api/v1/nexus/network${qs ? `?${qs}` : ''}`)
  },
  getSnapshotDiff: () => apiFetch<SnapshotDiffResponse>('/api/v1/nexus/network/diff'),
  getEdgeEvidence: (relationshipId: string) => {
    return apiFetch<NexusEdgeEvidenceResponse>(`/api/v1/nexus/relationships/${relationshipId}/evidence`)
  },
  findNexusPath: (sourceId: string, targetId: string, maxDepth = 6) => {
    return apiFetch<NexusPathResponse>(`/api/v1/nexus/path?source=${encodeURIComponent(sourceId)}&target=${encodeURIComponent(targetId)}&max_depth=${maxDepth}`)
  },
  getLeads: () => apiFetch<NexusLead[]>('/api/v1/nexus/leads'),
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
  resetDemo: () => apiFetch<{ status: string }>('/api/v1/nexus/demo/reset', { method: 'POST' }),
}
