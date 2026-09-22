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

export function useNexusNetwork(
  params: 'before' | 'after' | Parameters<typeof apiClient.getNexusNetwork>[0],
  enabled: boolean = true
) {
  const queryParams = typeof params === 'string' ? { snapshot: params } : params
  return useQuery({
    queryKey: ['nexus', 'network', queryParams],
    queryFn: () => apiClient.getNexusNetwork(queryParams),
    enabled,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useBatchNetwork(batchId: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ['nexus', 'batchNetwork', batchId],
    queryFn: () => apiClient.getBatchNetwork(batchId!),
    enabled: Boolean(enabled && batchId),
    retry: false,
  })
}

export function useSnapshotDiff(enabled: boolean) {
  return useQuery({
    queryKey: ['nexus', 'diff'],
    queryFn: () => apiClient.getSnapshotDiff(),
    enabled,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useEntityNetwork(entityId: string | null, depth: number = 2, enabled: boolean = true) {
  return useQuery({
    queryKey: ['entities', 'network', entityId, depth],
    queryFn: () => apiClient.getEntityNetwork(entityId!, depth),
    enabled: Boolean(enabled && entityId && entityId.trim() !== ''),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCaseNetworkData(caseId: string | null, depth: number = 1, enabled: boolean = true) {
  return useQuery({
    queryKey: ['cases', 'network', caseId, depth],
    queryFn: () => apiClient.getCaseNetwork(caseId!, depth),
    enabled: Boolean(enabled && caseId && caseId.trim() !== ''),
    retry: false,
    staleTime: 5 * 60 * 1000,
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
    staleTime: 30 * 1000,
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

// ── Intelligence Hub Hooks ──────────────────────────────────────────────────

export function useIntelligenceHotspots(enabled: boolean = true) {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'hotspots'],
    queryFn: () => apiClient.getIntelligenceHotspots(),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useHotspotDrilldown(district: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'hotspots', district],
    queryFn: () => apiClient.getHotspotDrilldown(district!),
    enabled: Boolean(enabled && district && district.trim() !== ''),
    staleTime: 5 * 60 * 1000,
  })
}

export function useRepeatOffenderRadar(minCases: number = 2, topK: number = 50, enabled: boolean = true) {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'offenders', minCases, topK],
    queryFn: () => apiClient.getRepeatOffenderRadar(minCases, topK),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCombinedBridgeSignals(enabled: boolean = true) {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'combined'],
    queryFn: () => apiClient.getCombinedBridgeSignals(),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

// ── P0 Proactive Network Change Intelligence Hooks ────────────────────────────

export function useSnapshots(caseScope?: string) {
  return useQuery({
    queryKey: ['nexus', 'snapshots', caseScope],
    queryFn: () => apiClient.getSnapshots(caseScope),
    staleTime: 5 * 60 * 1000,
  })
}

export function useProactiveDiff(before = 'snap-baseline-v1', after = 'snap-current', enabled = true) {
  return useQuery({
    queryKey: ['nexus', 'proactive-diff', before, after],
    queryFn: () => apiClient.getProactiveDiff(before, after),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useNetworkPulses(priority?: string, caseId?: string) {
  return useQuery({
    queryKey: ['nexus', 'pulses', priority, caseId],
    queryFn: () => apiClient.getPulses(priority, caseId),
    staleTime: 2 * 60 * 1000,
  })
}

export function useIntelligenceBootstrap() {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'bootstrap'],
    queryFn: () => apiClient.getIntelligenceBootstrap(),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  })
}

// ── P1-A Cross-Jurisdiction Intelligence Pulse Dissemination Hooks ───────────

export function useIntelligencePulseInbox(caseId?: string, district?: string) {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'pulses', 'inbox', caseId, district],
    queryFn: () => apiClient.getIntelligencePulseInbox(caseId, district),
  })
}

export function useDispatchIntelligencePulse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: import('@shared/contracts/api').CreateIntelligencePulseRequest) =>
      apiClient.dispatchIntelligencePulse(req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['nexus', 'intelligence', 'pulses'] })
    },
  })
}

export function useAcknowledgeIntelligencePulse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ packetId, req }: { packetId: string; req: import('@shared/contracts/api').AcknowledgePulseRequest }) =>
      apiClient.acknowledgeIntelligencePulse(packetId, req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['nexus', 'intelligence', 'pulses'] })
    },
  })
}

// ── P1-B Identity Drift Radar Hooks ───────────────────────────────────────────

export function useIdentityDrifts(personId?: string, driftType?: string, status?: string) {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'identity-drift', personId, driftType, status],
    queryFn: () => apiClient.getIdentityDrifts(personId, driftType, status),
    staleTime: 5 * 60 * 1000,
  })
}

export function useDecideIdentityDrift() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ driftId, req }: { driftId: string; req: import('@shared/contracts/api').DecideIdentityDriftRequest }) =>
      apiClient.decideIdentityDrift(driftId, req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['nexus', 'intelligence', 'identity-drift'] })
    },
  })
}

export function useIdentityDriftSummary() {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'identity-drift', 'summary'],
    queryFn: () => apiClient.getIdentityDriftSummary(),
    staleTime: 5 * 60 * 1000,
  })
}

// ── P1-C Network Adaptation Radar Hooks ─────────────────────────────────────

export function useNetworkAdaptations(adaptationType?: string, status?: string) {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'network-adaptation', adaptationType, status],
    queryFn: () => apiClient.getNetworkAdaptations(adaptationType, status),
    staleTime: 5 * 60 * 1000,
  })
}

export function useDecideNetworkAdaptation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ adaptationId, req }: { adaptationId: string; req: import('@shared/contracts/api').DecideNetworkAdaptationRequest }) =>
      apiClient.decideNetworkAdaptation(adaptationId, req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['nexus', 'intelligence', 'network-adaptation'] })
    },
  })
}

export function useNetworkAdaptationSummary() {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'network-adaptation', 'summary'],
    queryFn: () => apiClient.getNetworkAdaptationSummary(),
    staleTime: 5 * 60 * 1000,
  })
}

// ── P1-D Digital Shadow (SOCMINT Governance) Hooks ──────────────────────────

export function useDigitalShadows(personId?: string, platform?: string, lifecycleState?: string) {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'digital-shadow', personId, platform, lifecycleState],
    queryFn: () => apiClient.getDigitalShadows(personId, platform, lifecycleState),
    staleTime: 5 * 60 * 1000,
  })
}

export function useDecideDigitalShadow() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ corroborationId, req }: { corroborationId: string; req: import('@shared/contracts/api').DecideDigitalShadowRequest }) =>
      apiClient.decideDigitalShadow(corroborationId, req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['nexus', 'intelligence', 'digital-shadow'] })
    },
  })
}

export function useDigitalShadowSummary() {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'digital-shadow', 'summary'],
    queryFn: () => apiClient.getDigitalShadowSummary(),
    staleTime: 5 * 60 * 1000,
  })
}

// ── P2 Case DNA Explainable Structural Similarity Hooks ─────────────────────

export function useCaseDNA(caseId?: string, topK?: number) {
  return useQuery({
    queryKey: ['nexus', 'intelligence', 'case-dna', caseId, topK],
    queryFn: () => (caseId ? apiClient.getCaseDNA(caseId, topK) : Promise.resolve(null)),
    enabled: Boolean(caseId),
    staleTime: 5 * 60 * 1000,
  })
}



