import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { apiFetch } from '@/lib/apiClient'
import type { InvestigationSummaryResponse } from '@shared/contracts/api'

export function useWorklist() {
  const { role } = useAuth()

  return useQuery<InvestigationSummaryResponse[]>({
    queryKey: ['worklist', role],
    queryFn: () => apiFetch<InvestigationSummaryResponse[]>(`/worklist?role=${role ?? 'IO'}`),
    staleTime: 0,
  })
}
