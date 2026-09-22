import { Activity, ShieldCheck, Briefcase, GitCompare } from 'lucide-react'
import { useIntelligenceBootstrap, useNetworkPulses, useProactiveDiff } from '@/hooks/useNexus'
import { MetricCard } from '@/components/ui/MetricCard'

export function IntelligenceSummaryMetrics() {
  const { data: bootstrap, isLoading: isBootstrapLoading, isError: isBootstrapError } = useIntelligenceBootstrap()
  const { data: pulses = [], isLoading: isPulsesLoading } = useNetworkPulses()
  const { data: diff, isLoading: isDiffLoading } = useProactiveDiff()

  const kpis = bootstrap?.kpis

  // Fast-hydrate from bootstrap, update if pulses/diff return fresher data
  const hasLivePulses = pulses.length > 0
  const activePulsesCount = hasLivePulses ? pulses.length : (kpis?.active_pulses_count ?? 0)
  const criticalPulsesCount = hasLivePulses
    ? pulses.filter((p) => p.review_priority === 'CRITICAL_REVIEW').length
    : (kpis?.critical_pulses_count ?? 0)

  // Aggregate affected cases uniquely across all pulses
  const affectedCasesSet = new Set<string>()
  pulses.forEach((p) => {
    (p.affected_cases || []).forEach((c) => affectedCasesSet.add(c))
  })
  const affectedCasesCount = affectedCasesSet.size > 0
    ? affectedCasesSet.size
    : (kpis?.affected_cases_count ?? (bootstrap?.affected_cases?.length ?? 0))

  // Calculate evidence assessment counts
  let totalClaims = 0
  let supportedClaims = 0
  pulses.forEach((p) => {
    (p.assessment || []).forEach((a) => {
      totalClaims += 1
      if (a.state === 'SUPPORTS') supportedClaims += 1
    })
  })
  const evidencePercent = totalClaims > 0
    ? Math.round((supportedClaims / totalClaims) * 100)
    : (kpis?.evidence_percent ?? 100)
  const displaySupportedClaims = totalClaims > 0 ? supportedClaims : (kpis?.supported_claims ?? 0)
  const displayTotalClaims = totalClaims > 0 ? totalClaims : (kpis?.total_claims ?? 0)

  // Derive real network changes from proactive diff or bootstrap
  const addedNodes = diff?.added_nodes?.length ?? (kpis?.added_nodes ?? 0)
  const addedEdges = diff?.added_relationships?.length ?? (kpis?.added_edges ?? 0)
  const totalChanges = addedNodes + addedEdges

  const isInitialLoading = isBootstrapLoading && isPulsesLoading && isDiffLoading
  const isErrorState = isBootstrapError && !kpis && !hasLivePulses && !diff

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        label="Active Pulses"
        value={isErrorState ? 'Unavailable' : (isInitialLoading ? '...' : activePulsesCount)}
        icon={Activity}
        badge={
          isErrorState
            ? { text: 'Sync Error', variant: 'danger' }
            : criticalPulsesCount > 0
            ? { text: `${criticalPulsesCount} Critical Review`, variant: 'danger' }
            : { text: 'Queue Normal', variant: 'success' }
        }
        tooltip="Proactive network change intelligence pulses currently awaiting verification"
      />

      <MetricCard
        label="Evidence Status"
        value={isErrorState ? 'Unavailable' : (isInitialLoading ? '...' : `Evidence-linked: ${evidencePercent}%`)}
        icon={ShieldCheck}
        badge={
          isErrorState
            ? { text: 'Offline', variant: 'neutral' }
            : displayTotalClaims > 0
            ? { text: `${displaySupportedClaims}/${displayTotalClaims} verified claims`, variant: 'neutral' }
            : { text: 'Baseline verified', variant: 'success' }
        }
        tooltip="Proportion of verified claims with corroborating evidence references in active pulse scope"
      />

      <MetricCard
        label="Affected Investigations"
        value={isErrorState ? 'Unavailable' : (isInitialLoading ? '...' : affectedCasesCount)}
        icon={Briefcase}
        badge={{ text: 'Cross-Jurisdiction', variant: 'neutral' }}
        tooltip="Unique active police investigations intersecting with detected network changes"
      />

      <MetricCard
        label="Network Changes"
        value={isErrorState ? 'Unavailable' : (isInitialLoading ? '...' : `+${totalChanges}`)}
        icon={GitCompare}
        badge={{ text: `+${addedNodes} nodes, +${addedEdges} edges`, variant: 'neutral' }}
        tooltip="Structural network delta between baseline snapshot and current intelligence window"
      />
    </div>
  )
}
