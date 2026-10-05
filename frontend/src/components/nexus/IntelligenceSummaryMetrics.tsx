import { Activity, ShieldCheck, Briefcase, GitCompare } from 'lucide-react'
import { useIntelligenceBootstrap } from '@/hooks/useNexus'
import { MetricCard } from '@/components/ui/MetricCard'

export function IntelligenceSummaryMetrics() {
  const { data: bootstrap, isPending: isInitialLoading, isError: isBootstrapError } = useIntelligenceBootstrap()
  const kpis = bootstrap?.kpis
  const activePulsesCount = kpis?.active_pulses_count
  const criticalPulsesCount = kpis?.critical_pulses_count ?? 0
  const affectedCasesCount = kpis?.affected_cases_count
  const evidencePercent = kpis?.evidence_percent
  const displaySupportedClaims = kpis?.supported_claims
  const displayTotalClaims = kpis?.total_claims ?? 0
  const addedNodes = kpis?.added_nodes
  const addedEdges = kpis?.added_edges
  const totalChanges = kpis?.total_changes
  const isErrorState = isBootstrapError && !kpis

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        label="Active Pulses"
        value={isErrorState ? 'Unavailable' : (isInitialLoading ? '...' : (activePulsesCount ?? 'Unavailable'))}
        icon={Activity}
        badge={
          isErrorState
            ? { text: 'Sync Error', variant: 'danger' }
            : isInitialLoading ? { text: 'Connecting', variant: 'neutral' }
            : isBootstrapError ? { text: 'Stale', variant: 'neutral' }
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
            : isInitialLoading ? { text: 'Connecting', variant: 'neutral' }
            : isBootstrapError ? { text: 'Stale', variant: 'neutral' }
            : displayTotalClaims > 0
            ? { text: `${displaySupportedClaims}/${displayTotalClaims} verified claims`, variant: 'neutral' }
            : { text: 'Baseline verified', variant: 'success' }
        }
        tooltip="Proportion of verified claims with corroborating evidence references in active pulse scope"
      />

      <MetricCard
        label="Affected Investigations"
        value={isErrorState ? 'Unavailable' : (isInitialLoading ? '...' : (affectedCasesCount ?? 'Unavailable'))}
        icon={Briefcase}
        badge={{ text: isBootstrapError && kpis ? 'Stale' : 'Cross-Jurisdiction', variant: 'neutral' }}
        tooltip="Unique active police investigations intersecting with detected network changes"
      />

      <MetricCard
        label="Network Changes"
        value={isErrorState ? 'Unavailable' : (isInitialLoading ? '...' : `+${totalChanges}`)}
        icon={GitCompare}
        badge={{ text: isBootstrapError && kpis ? 'Stale' : kpis ? `+${addedNodes} nodes, +${addedEdges} edges` : (isInitialLoading ? 'Loading' : 'Unavailable'), variant: 'neutral' }}
        tooltip="Structural network delta between baseline snapshot and current intelligence window"
      />
    </div>
  )
}
