import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'

export interface NetworkNode {
  id: string
  type: string
  data: {
    label: string
    [key: string]: unknown
  }
  position: {
    x: number
    y: number
  }
}

export interface NetworkEdge {
  id: string
  source: string
  target: string
  label: string
  [key: string]: unknown
}

export interface NetworkResponse {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
}

export function useCaseNetwork(caseId?: string) {
  return useQuery<NetworkResponse>({
    queryKey: ['case-network', caseId],
    queryFn: () => apiFetch<NetworkResponse>(`/cases/${caseId}/network`),
    enabled: Boolean(caseId),
    staleTime: 0,
  })
}
