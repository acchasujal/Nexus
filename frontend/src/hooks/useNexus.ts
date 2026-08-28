/**
 * frontend/src/hooks/useNexus.ts
 *
 * React Query hooks for the frozen NEXUS prototype contract (/api/v1/nexus/*).
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import type { NexusLeadDecisionRequest, ResolutionDecisionRequest } from '@shared/contracts/api'

export function useResolutionCandidates() {
  return useQuery({
    queryKey: ['nexus', 'candidates'],
    queryFn: () => apiClient.getResolutionCandidates(),
  })
}

export function useDecideCandidate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, req }: { id: string; req: ResolutionDecisionRequest }) =>
      apiClient.decideResolutionCandidate(id, req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['nexus'] })
    },
  })
}

export function useNexusNetwork(snapshot: 'before' | 'after', enabled: boolean = true) {
  return useQuery({
    queryKey: ['nexus', 'network', snapshot],
    queryFn: () => apiClient.getNexusNetwork({ snapshot }),
    enabled,
    retry: false,
  })
}

export function useSnapshotDiff(enabled: boolean) {
  return useQuery({
    queryKey: ['nexus', 'diff'],
    queryFn: () => apiClient.getSnapshotDiff(),
    enabled,
    retry: false,
  })
}

export function useEntityNetwork(entityId: string | null, depth: number = 2, enabled: boolean = true) {
  return useQuery({
    queryKey: ['entities', 'network', entityId, depth],
    queryFn: () => apiClient.getEntityNetwork(entityId!, depth),
    enabled: Boolean(enabled && entityId && entityId.trim() !== ''),
    retry: false,
  })
}

export function useCaseNetworkData(caseId: string | null, depth: number = 2, enabled: boolean = true) {
  return useQuery({
    queryKey: ['cases', 'network', caseId, depth],
    queryFn: () => apiClient.getCaseNetwork(caseId!, depth),
    enabled: Boolean(enabled && caseId && caseId.trim() !== ''),
    retry: false,
  })
}

export function useEdgeEvidence(relationshipId: string | null) {
  return useQuery({
    queryKey: ['nexus', 'evidence', relationshipId],
    queryFn: () => apiClient.getEdgeEvidence(relationshipId!),
    enabled: Boolean(relationshipId),
    retry: false,
  })
}

export function useNexusPath(sourceId: string | null, targetId: string | null, maxDepth: number = 6, enabled: boolean = true) {
  return useQuery({
    queryKey: ['nexus', 'path', sourceId, targetId, maxDepth],
    queryFn: () => apiClient.findNexusPath(sourceId!, targetId!, maxDepth),
    enabled: Boolean(enabled && sourceId && targetId && sourceId.trim() !== '' && targetId.trim() !== ''),
    retry: false,
  })
}

export function useLeads() {
  return useQuery({
    queryKey: ['nexus', 'leads'],
    queryFn: () => apiClient.getLeads(),
  })
}

export function useDecideLead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, req }: { id: string; req: NexusLeadDecisionRequest }) =>
      apiClient.decideLead(id, req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['nexus'] })
    },
  })
}

export function useNexusCopilot(query: string | null) {
  return useQuery({
    queryKey: ['nexus', 'copilot', query],
    queryFn: () => apiClient.queryNexusCopilot(query!),
    enabled: Boolean(query),
  })
}

export function useNexusSearch(query: string) {
  return useQuery({
    queryKey: ['nexus', 'search', query],
    queryFn: () => apiClient.nexusSearch(query),
    enabled: query.trim().length >= 2,
  })
}

export function useResetDemo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiClient.resetDemo(),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['nexus'] })
    },
  })
}

export function useScanLeads() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiClient.scanLeads(),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['nexus', 'leads'] })
    },
  })
}
