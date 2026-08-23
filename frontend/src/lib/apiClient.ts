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
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
  let fullUrl = path.startsWith('http') ? path : `${baseUrl}${path}`
  const savedRole = localStorage.getItem('nexus_role') || localStorage.getItem('caseclock_role') || 'INVESTIGATOR'
  const token = localStorage.getItem('nexus_token')

  const method = (options?.method || 'GET').toUpperCase()
  const isMutating = method !== 'GET' && method !== 'HEAD'

  if (!isMutating && !fullUrl.includes('role=')) {
    const separator = fullUrl.includes('?') ? '&' : '?'
    fullUrl = `${fullUrl}${separator}role=${encodeURIComponent(savedRole)}`
  }

  const headers: Record<string, string> = {
    ...(isMutating ? { 'Content-Type': 'application/json', 'X-Role': savedRole } : {}),
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
    const query = new URLSearchParams(params as any).toString()
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
  getCommunities: () => apiFetch<any[]>('/api/v1/communities'),
  getBridges: () => apiFetch<any[]>('/api/v1/influence/bridges'),
  getInfluenceRankings: () => apiFetch<any[]>('/api/v1/influence/rankings'),

  // Patterns
  getRepeatOffenders: () => apiFetch<any[]>('/api/v1/patterns/repeat-offenders'),
  getSharedClusters: () => apiFetch<any[]>('/api/v1/patterns/shared-clusters'),

  // Timeline & Evidence
  getTimeline: (caseId?: string) => {
    return apiFetch<any[]>(`/api/v1/timeline${caseId ? `?case_id=${caseId}` : ''}`)
  },

  // Copilot
  queryCopilot: (req: CopilotQueryRequest) => {
    return apiFetch<CopilotQueryResponse>('/api/v1/copilot/query', {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },

  // Audit
  getAuditLogs: (limit = 50) => apiFetch<any[]>(`/api/v1/audit?limit=${limit}`),
}
