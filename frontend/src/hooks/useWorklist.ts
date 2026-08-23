import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { apiFetch } from '@/lib/apiClient'
import type { CaseSummaryResponse } from '@shared/contracts/api'

export function useWorklist() {
  const { role } = useAuth()

  return useQuery<CaseSummaryResponse[]>({
    queryKey: ['worklist', role],
    queryFn: () => apiFetch<CaseSummaryResponse[]>(`/worklist?role=${role ?? 'IO'}`),
    staleTime: 0,
  })
}
