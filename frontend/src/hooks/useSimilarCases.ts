import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'

export interface SimilarCaseMatch {
  case_id: string
  score: number
  reasons: string[]
  properties: Record<string, unknown>
}

export interface SimilarCasesResponse {
  case_id: string
  top_k: number
  min_score: number
  matches: SimilarCaseMatch[]
  match_count: number
}

export function useSimilarCases(caseId?: string) {
  return useQuery<SimilarCasesResponse>({
    queryKey: ['similar-cases', caseId],
    queryFn: () => apiFetch<SimilarCasesResponse>(`/api/v1/graph/cases/${caseId}/similar`),
    enabled: Boolean(caseId),
    staleTime: 0,
  })
}
