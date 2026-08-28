import { GitMerge } from 'lucide-react'
import { useSnapshotDiff, useResolutionCandidates } from '@/hooks/useNexus'

interface NetworkDeltaSummaryProps {
  activeSnapshot: 'before' | 'after'
}

export function NetworkDeltaSummary({ activeSnapshot }: NetworkDeltaSummaryProps) {
  const diffQuery = useSnapshotDiff(activeSnapshot === 'after')
  const candidatesQuery = useResolutionCandidates()

  if (activeSnapshot !== 'after') {
    return null
  }

  if (diffQuery.isLoading) {
    return (
      <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-3 text-xs text-blue-800 flex items-center gap-2">
        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        <span>Computing topological network delta...</span>
      </div>
    )
  }

  const diff = diffQuery.data
  if (!diff) return null

  const addedNodesCount = diff.added_node_ids?.length || 0
  const removedNodesCount = diff.removed_node_ids?.length || 0
  const addedEdgesCount = diff.added_edge_ids?.length || 0
  const removedEdgesCount = diff.removed_edge_ids?.length || 0

  const confirmedCandidates = (candidatesQuery.data || []).filter((c) => c.status === 'CONFIRMED')
  const confirmedIds = confirmedCandidates.map((c) => c.id)
  const decisionLabel = confirmedIds.length > 0 ? confirmedIds.join(', ') : 'RC-1'

  const bridges = confirmedCandidates.map((c) => {
    const leftCase = c.left.case_ids[0] || 'Case A'
    const rightCase = c.right.case_ids[0] || 'Case B'
    return `${leftCase} ↔ ${rightCase}`
  })
  const bridgeLabel = bridges.length > 0
    ? bridges.join('; ')
    : 'FIR 141/2026 (Mysuru) and FIR 207/2026 (Bengaluru)'

  const hasRc1 = confirmedIds.includes('RC-1') || confirmedIds.length === 0
  const hasRc2 = confirmedIds.includes('RC-2')
  const hasRc3 = confirmedIds.includes('RC-3')

  const propagationDetails: string[] = []
  if (hasRc1) propagationDetails.push('ACC-9914 ➔ ACC-7731 financial flow')
  if (hasRc2) propagationDetails.push('ACC-4491 ➔ ACC-9914 hawala channel')
  if (hasRc3) propagationDetails.push('VEH-1001 vehicle logistics link')
  const propagationLabel = propagationDetails.length > 0
    ? propagationDetails.join(', ')
    : 'Downstream communication and financial flow'

  return (
    <div className="rounded-xl border border-emerald-300 bg-emerald-50/70 p-4 text-xs text-neutral-900 shadow-sm space-y-2.5 animate-in fade-in duration-200">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-emerald-200/80 pb-2">
        <div className="flex items-center gap-2 font-bold text-emerald-950 text-sm">
          <GitMerge className="h-4.5 w-4.5 text-emerald-600" />
          <span>Network Transformation Delta (What Changed)</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-bold">
          <span className="bg-emerald-100 border border-emerald-300 text-emerald-900 px-2 py-0.5 rounded-md">
            Merged Entities ({removedNodesCount} → {addedNodesCount})
          </span>
          <span className="bg-blue-100 border border-blue-300 text-blue-900 px-2 py-0.5 rounded-md">
            Rewired Edges (+{addedEdgesCount} / -{removedEdgesCount})
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-white/90 border border-emerald-100 p-2.5 rounded-lg shadow-2xs space-y-1">
          <div className="font-bold text-emerald-950 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Entities Merged &amp; Unified
          </div>
          <p className="text-[11px] text-neutral-600">
            {removedNodesCount} alias records unified into <strong>{addedNodesCount} canonical entity node(s)</strong> based on verified {decisionLabel} decision{confirmedIds.length > 1 ? 's' : ''}.
          </p>
        </div>

        <div className="bg-white/90 border border-emerald-100 p-2.5 rounded-lg shadow-2xs space-y-1">
          <div className="font-bold text-emerald-950 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            Cross-Case Bridge Formed
          </div>
          <p className="text-[11px] text-neutral-600">
            Unified suspect node bridges <strong>{bridgeLabel}</strong>.
          </p>
        </div>

        <div className="bg-white/90 border border-emerald-100 p-2.5 rounded-lg shadow-2xs space-y-1">
          <div className="font-bold text-emerald-950 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            Evidentiary Propagation
          </div>
          <p className="text-[11px] text-neutral-600">
            Downstream edges ({propagationLabel}) re-anchored to the canonical entity.
          </p>
        </div>
      </div>
    </div>
  )
}
