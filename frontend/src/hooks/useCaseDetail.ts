import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'
import type { CaseDetailResponse } from '@shared/contracts/api'

export function useCaseDetail(caseId: string | undefined) {
  return useQuery<CaseDetailResponse>({
    queryKey: ['case', caseId],
    queryFn: () => apiFetch<CaseDetailResponse>(`/api/v1/investigations/${caseId}`),
    enabled: Boolean(caseId),
  })
}
