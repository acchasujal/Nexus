/**
 * frontend/src/pages/NetworkExplorer.tsx
 *
 * Global Network Explorer with two-state Before/After replay:
 * - renders all cases/entities from the snapshot contract
 * - layer toggles, case focus, legend, bridge/community badges
 * - two-position control: Before resolution / After resolution
 * - highlights only the snapshot delta (added nodes/edges) in After mode
 * - click-any-link opens the Evidence Drawer
 */
import { useState } from 'react'
import { Network, RotateCcw, Route, ShieldQuestion, ArrowRightLeft } from 'lucide-react'
import { useNexusNetwork, useSnapshotDiff, useNexusPath } from '@/hooks/useNexus'
import { GlobalNetworkCanvas } from '@/components/nexus/GlobalNetworkCanvas'
import { EvidenceDrawer } from '@/components/nexus/EvidenceDrawer'
import { DerivationBadge } from '@/components/nexus/DerivationBadge'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { Link } from 'react-router-dom'

type ReplayState = 'before' | 'after'

export default function NetworkExplorer() {
  const [replay, setReplay] = useState<ReplayState>('before')
  const [edgeId, setEdgeId] = useState<string | null>(null)

  const before = useNexusNetwork('before', replay === 'before')
  const after = useNexusNetwork('after', replay === 'after')
  const diff = useSnapshotDiff(replay === 'after' && after.data?.state === 'after')

  const network = replay === 'before' ? before : after
  const graph = network.data

  const pathQuery = useNexusPath('CASE-141', 'CASE-207')
  const [showPath, setShowPath] = useState(false)

  const afterUnavailable = replay === 'after' && after.error

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 border-b border-neutral-200 pb-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="flex items-center gap-2.5 text-2xl font-bold text-neutral-900">
            <Network className="h-6 w-6 text-blue-600" /> Global Network Explorer
          </h1>
          <p className="mt-1 text-sm text-neutral-600">Every case and entity in the current snapshot. Click any link for its full evidence chain.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <button onClick={() => setShowPath((v) => !v)}
            className="inline-flex items-center gap-1.5 sm:gap-2 rounded-lg border border-neutral-300 bg-white px-2.5 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm font-semibold text-neutral-700 transition-colors hover:bg-neutral-50 hover:text-neutral-900 shadow-sm"
            aria-expanded={showPath}>
            <Route className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-blue-600" /> {showPath ? 'Hide' : 'Find'} case connection
          </button>
          <div role="group" aria-label="Network snapshot replay" className="flex items-center rounded-lg border border-neutral-300 bg-neutral-100 p-0.5 sm:p-1 text-xs sm:text-sm font-semibold shadow-inner">
            <button onClick={() => setReplay('before')} aria-pressed={replay === 'before'}
              className={`rounded-md px-2.5 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm transition-colors ${replay === 'before' ? 'bg-white text-neutral-900 shadow-sm font-bold' : 'text-neutral-600 hover:text-neutral-900'}`}>
              Before resolution
            </button>
            <button onClick={() => setReplay('after')} aria-pressed={replay === 'after'}
              disabled={after.isLoading && !after.data}
              className={`rounded-md px-2.5 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm transition-colors disabled:opacity-40 ${replay === 'after' ? 'bg-emerald-600 text-white shadow-sm font-bold' : 'text-neutral-600 hover:text-neutral-900'}`}>
              After resolution
            </button>
          </div>
        </div>
      </div>

      {showPath && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 text-sm shadow-sm">
          <div className="flex items-center gap-2 font-semibold text-neutral-900">
            <ArrowRightLeft className="h-4 w-4 text-blue-600" /> FIR 141/2026 ↔ FIR 207/2026
          </div>
          {pathQuery.isLoading && <p className="mt-2 text-neutral-600">Searching for an explainable connection…</p>}
          {pathQuery.data && (
            pathQuery.data.found ? (
              <div className="mt-2 space-y-2">
                <p className="text-neutral-800">{pathQuery.data.explanation}</p>
                <p className="font-mono text-xs text-neutral-600 font-medium">path: {pathQuery.data.node_ids.join(' → ')} ({pathQuery.data.hops} hops)</p>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs text-neutral-600 font-semibold">Evidence:</span>
                  {pathQuery.data.evidence_ids.map((id) => (
                    <code key={id} className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-mono text-amber-900 border border-amber-200">{id}</code>
                  ))}
                </div>
              </div>
            ) : (
              <p className="mt-2 flex items-center gap-2 text-neutral-700">
                <ShieldQuestion className="h-4 w-4 text-amber-600" /> {pathQuery.data.explanation}
              </p>
            )
          )}
        </div>
      )}

      {network.isLoading && <LoadingSkeleton layout="detail" />}
      {network.isError && !afterUnavailable && <ErrorState message="Failed to load the investigation network." onRetry={() => void network.refetch()} />}

      {afterUnavailable && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900 shadow-sm">
          <p className="font-semibold">The "After resolution" snapshot does not exist yet.</p>
          <p className="mt-1 text-amber-800">
            Confirm the pending entity match first — the merged network is generated from that decision.{' '}
            <Link to="/fusion" className="font-bold underline hover:text-amber-950 text-blue-700">Open Entity Fusion</Link>
          </p>
        </div>
      )}

      {graph && !afterUnavailable && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-xs text-neutral-600 font-medium">
            <span data-testid="snapshot-label">
              Snapshot <code className="text-neutral-900 font-semibold">{graph.snapshot_id}</code> · {graph.total_nodes} nodes · {graph.total_edges} links
            </span>
            {replay === 'after' && diff.data && (
              <span className="flex items-center gap-2">
                <DerivationBadge klass="DERIVED" size="xs" /> Only the delta from resolution is highlighted
              </span>
            )}
            {replay === 'before' && (
              <span className="flex items-center gap-1.5 text-neutral-600">
                <RotateCcw className="h-3 w-3" /> Two separate case components — no bridge visible
              </span>
            )}
          </div>
          <GlobalNetworkCanvas graph={graph} diff={replay === 'after' ? diff.data ?? null : null} highlightDelta={replay === 'after'} onEdgeSelect={setEdgeId} />
        </>
      )}

      <EvidenceDrawer relationshipId={edgeId} onClose={() => setEdgeId(null)} />
    </div>
  )
}
