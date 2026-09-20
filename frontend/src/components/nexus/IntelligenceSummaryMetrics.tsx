import { Activity, ShieldCheck, Briefcase, GitCompare } from 'lucide-react'
import { useNetworkPulses, useProactiveDiff } from '@/hooks/useNexus'
import { MetricCard } from '@/components/ui/MetricCard'

export function IntelligenceSummaryMetrics() {
  const { data: pulses = [], isLoading: isPulsesLoading } = useNetworkPulses()
  const { data: diff, isLoading: isDiffLoading } = useProactiveDiff()

  // Derive genuine values from active pulses
  const activePulsesCount = pulses.length
  const criticalPulsesCount = pulses.filter((p) => p.review_priority === 'CRITICAL_REVIEW').length

  // Aggregate affected cases uniquely across all pulses
  const affectedCasesSet = new Set<string>()
  pulses.forEach((p) => {
    (p.affected_cases || []).forEach((c) => affectedCasesSet.add(c))
  })
  const affectedCasesCount = affectedCasesSet.size

  // Calculate evidence assessment counts
  let totalClaims = 0
  let supportedClaims = 0
  pulses.forEach((p) => {
    (p.assessment || []).forEach((a) => {
      totalClaims += 1
      if (a.state === 'SUPPORTS') supportedClaims += 1
    })
  })
  const evidencePercent = totalClaims > 0 ? Math.round((supportedClaims / totalClaims) * 100) : 100

  // Derive real network changes from proactive diff
  const addedNodes = diff?.added_nodes?.length ?? 0
  const addedEdges = diff?.added_relationships?.length ?? 0
  const totalChanges = addedNodes + addedEdges

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        label="Active Pulses"
        value={isPulsesLoading ? '...' : activePulsesCount}
        icon={Activity}
        badge={
          criticalPulsesCount > 0
            ? { text: `${criticalPulsesCount} Critical Review`, variant: 'danger' }
            : { text: 'Queue Normal', variant: 'success' }
        }
        tooltip="Proactive network change intelligence pulses currently awaiting verification"
      />

      <MetricCard
        label="Evidence Status"
        value={isPulsesLoading ? '...' : `Evidence-linked: ${evidencePercent}%`}
        icon={ShieldCheck}
        badge={
          totalClaims > 0
            ? { text: `${supportedClaims}/${totalClaims} verified claims`, variant: 'neutral' }
            : { text: 'Baseline verified', variant: 'success' }
        }
        tooltip="Proportion of verified claims with corroborating evidence references in active pulse scope"
      />

      <MetricCard
        label="Affected Investigations"
        value={isPulsesLoading ? '...' : affectedCasesCount}
        icon={Briefcase}
        badge={{ text: 'Cross-Jurisdiction', variant: 'neutral' }}
        tooltip="Unique active police investigations intersecting with detected network changes"
      />

      <MetricCard
        label="Network Changes"
        value={isDiffLoading ? '...' : `+${totalChanges}`}
        icon={GitCompare}
        badge={{ text: `+${addedNodes} nodes, +${addedEdges} edges`, variant: 'neutral' }}
        tooltip="Structural network delta between baseline snapshot and current intelligence window"
      />
    </div>
  )
}
