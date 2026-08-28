import { useState, useMemo, useEffect } from 'react'
import {
  Network,
  RotateCcw,
  Route,
  ShieldQuestion,
  ArrowRightLeft,
  Search,
  Sparkles,
  Layers,
  CheckCircle2,
  AlertCircle,
  X,
  ExternalLink,
  ChevronRight,
  Briefcase,
} from 'lucide-react'
import { useNexusNetwork, useSnapshotDiff, useNexusPath, useEntityNetwork, useCaseNetworkData } from '@/hooks/useNexus'
import { GlobalNetworkCanvas } from '@/components/nexus/GlobalNetworkCanvas'
import { EvidenceDrawer } from '@/components/nexus/EvidenceDrawer'
import { DerivationBadge } from '@/components/nexus/DerivationBadge'
import { PathfinderEntitySelector } from '@/components/nexus/PathfinderEntitySelector'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { Link, useSearchParams } from 'react-router-dom'
import type { NetworkGraphResponse, NexusNetworkResponse } from '@shared/contracts/api'

type ReplayState = 'before' | 'after'

function toNexusGraph(res: NetworkGraphResponse, snapshotId: string): NexusNetworkResponse {
  return {
    snapshot_id: snapshotId,
    state: 'before',
    nodes: (res.nodes || []).map((n) => {
      const props = (n.properties || {}) as Record<string, unknown>
      const cIds: string[] = props.case_id
        ? [String(props.case_id)]
        : Array.isArray(props.case_ids)
        ? props.case_ids.map(String)
        : []
      return {
        id: n.id,
        entity_type: n.entity_type || 'Entity',
        label: n.label || String(props.full_name || props.fir_number || n.id),
        case_ids: cIds,
        properties: props,
      }
    }),
    edges: (res.edges || []).map((e) => {
      const props = (e.properties || {}) as Record<string, unknown>
      const cIds: string[] = props.case_id
        ? [String(props.case_id)]
        : Array.isArray(props.case_ids)
        ? props.case_ids.map(String)
        : []
      return {
        id: e.id,
        source_id: e.source_id,
        target_id: e.target_id,
        edge_type: e.edge_type,
        weight: typeof e.weight === 'number' ? e.weight : 1.0,
        confidence: typeof e.provenance?.confidence === 'number' ? e.provenance.confidence : 1.0,
        derivation_class: (e.provenance?.derivation_method === 'DIRECT' ? 'FACT' : 'DERIVED') as 'FACT' | 'DERIVED',
        recorded_at: e.provenance?.timestamp || new Date().toISOString(),
        case_ids: cIds,
        properties: props,
      }
    }),
    total_nodes: res.total_nodes ?? res.nodes?.length ?? 0,
    total_edges: res.total_edges ?? res.edges?.length ?? 0,
  }
}

export default function NetworkExplorer() {
  const [searchParams] = useSearchParams()
  const caseIdParam = searchParams.get('case_id')
  const nodeIdParam = searchParams.get('node_id')
  const [replay, setReplay] = useState<ReplayState>('before')
  const [edgeId, setEdgeId] = useState<string | null>(null)

  // ── Dynamic Pathfinder & Exploration State ──────────────────────────────────
  const [showPathfinder, setShowPathfinder] = useState(false)
  const [sourceId, setSourceId] = useState(caseIdParam || nodeIdParam || '')
  const [targetId, setTargetId] = useState('')
  const [maxHops, setMaxHops] = useState(6)
  const [isExploring, setIsExploring] = useState(Boolean(caseIdParam || nodeIdParam))

  // Pre-fill from query params if requested
  useEffect(() => {
    if (caseIdParam) {
      setSourceId(caseIdParam)
      setShowPathfinder(true)
      setIsExploring(true)
    } else if (nodeIdParam) {
      setSourceId(nodeIdParam)
      setShowPathfinder(true)
      setIsExploring(true)
    }
  }, [caseIdParam, nodeIdParam])

  // Context classification
  const isEntityScoped = Boolean(nodeIdParam)
  const isCaseScoped = Boolean(caseIdParam)
  const isDemoCase = isCaseScoped && (caseIdParam === 'CASE-141' || caseIdParam === 'CASE-207')
  const hasActiveGraph = Boolean(caseIdParam || nodeIdParam || isExploring || (sourceId && targetId))

  // Network queries
  const entityQuery = useEntityNetwork(nodeIdParam, 2, isEntityScoped)
  const caseQuery = useCaseNetworkData(caseIdParam, 2, isCaseScoped && !isDemoCase)
  const demoQuery = useNexusNetwork(replay, (isCaseScoped && isDemoCase) || (!isEntityScoped && !isCaseScoped && hasActiveGraph))
  const diff = useSnapshotDiff(replay === 'after' && demoQuery.data?.state === 'after')

  const activeQuery = isEntityScoped ? entityQuery : (isCaseScoped && !isDemoCase ? caseQuery : demoQuery)

  const graph: NexusNetworkResponse | null = useMemo(() => {
    if (isEntityScoped) {
      if (!entityQuery.data || entityQuery.data.total_nodes === 0) return null
      return toNexusGraph(entityQuery.data, `ENTITY-${nodeIdParam}`)
    }
    if (isCaseScoped && !isDemoCase) {
      if (!caseQuery.data || caseQuery.data.total_nodes === 0) return null
      return toNexusGraph(caseQuery.data, `CASE-${caseIdParam}`)
    }
    if (hasActiveGraph && demoQuery.data) {
      return demoQuery.data
    }
    return null
  }, [isEntityScoped, isCaseScoped, isDemoCase, nodeIdParam, caseIdParam, entityQuery.data, caseQuery.data, demoQuery.data, hasActiveGraph])

  const pathQuery = useNexusPath(sourceId, targetId, maxHops, showPathfinder && Boolean(sourceId && targetId))

  const afterUnavailable = !isEntityScoped && !isCaseScoped && replay === 'after' && demoQuery.error

  // Lookups for labels and edges
  const nodesById = useMemo(() => {
    if (!graph?.nodes) return new Map()
    return new Map(graph.nodes.map((n) => [n.id, n]))
  }, [graph?.nodes])

  const edgesById = useMemo(() => {
    if (!graph?.edges) return new Map()
    return new Map(graph.edges.map((e) => [e.id, e]))
  }, [graph?.edges])

  // Handler to swap source & target
  const handleSwap = () => {
    const temp = sourceId
    setSourceId(targetId)
    setTargetId(temp)
  }

  // Quick preset apply
  const applyPreset = (src: string, tgt: string, hops = 6) => {
    setSourceId(src)
    setTargetId(tgt)
    setMaxHops(hops)
    setShowPathfinder(true)
    setIsExploring(true)
  }

  return (
    <div className="space-y-5">
      {/* Header & Controls */}
      <div className="flex flex-col justify-between gap-4 border-b border-neutral-200 pb-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="flex items-center gap-2.5 text-2xl font-bold text-neutral-900">
            <Network className="h-6 w-6 text-blue-600" /> Global Network Explorer
          </h1>
          <p className="mt-1 text-sm text-neutral-600">
            Multi-jurisdictional criminal network topology. Discover entity bridges, flow paths, and evidentiary provenance.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <button
            onClick={() => setShowPathfinder((v) => !v)}
            className={`inline-flex items-center gap-1.5 sm:gap-2 rounded-lg border px-3 py-1.5 sm:py-2 text-xs sm:text-sm font-semibold transition-all shadow-xs ${
              showPathfinder
                ? 'border-blue-600 bg-blue-50 text-blue-800 ring-2 ring-blue-500/20'
                : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50 hover:text-neutral-900'
            }`}
            aria-expanded={showPathfinder}
          >
            <Route className="h-4 w-4 text-blue-600" />
            Investigative Pathfinder
          </button>
          <div
            role="group"
            aria-label="Network snapshot replay"
            className="flex items-center rounded-lg border border-neutral-300 bg-neutral-100 p-0.5 sm:p-1 text-xs sm:text-sm font-semibold shadow-inner"
          >
            <button
              onClick={() => {
                setReplay('before')
                setIsExploring(true)
              }}
              aria-pressed={replay === 'before'}
              className={`rounded-md px-2.5 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm transition-colors ${
                replay === 'before'
                  ? 'bg-white text-neutral-900 shadow-sm font-bold'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              Before resolution
            </button>
            <button
              onClick={() => {
                setReplay('after')
                setIsExploring(true)
              }}
              aria-pressed={replay === 'after'}
              disabled={demoQuery.isLoading && !demoQuery.data}
              className={`rounded-md px-2.5 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm transition-colors disabled:opacity-40 ${
                replay === 'after'
                  ? 'bg-emerald-600 text-white shadow-sm font-bold'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              After resolution
            </button>
          </div>
        </div>
      </div>

      {/* ── Interactive Investigative Pathfinder Bar ────────────────────────────── */}
      {showPathfinder && (
        <div className="rounded-2xl border border-blue-200 bg-linear-to-b from-blue-50/70 to-white p-4 sm:p-5 text-sm shadow-md transition-all">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-blue-100 pb-3">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
                <Route className="h-4 w-4" />
              </span>
              <div>
                <h3 className="font-bold text-neutral-900 text-sm sm:text-base">
                  Interactive Graph Pathfinder
                </h3>
                <p className="text-xs text-neutral-500">
                  Deterministic shortest-path traversal across multi-jurisdictional evidence entities
                </p>
              </div>
            </div>

            {/* Presets */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-bold text-neutral-500 uppercase tracking-wider mr-1">
                Presets:
              </span>
              <button
                onClick={() => applyPreset('CASE-141', 'CASE-207', 6)}
                className="rounded-md border border-blue-200 bg-white px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50 transition-colors shadow-2xs"
              >
                🌟 FIR-141 ↔ FIR-207
              </button>
              <button
                onClick={() => applyPreset('P-DEEPAK', 'P-RAFIQ-K', 6)}
                className="rounded-md border border-neutral-200 bg-white px-2 py-1 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 transition-colors shadow-2xs"
              >
                💳 Deepak ↔ Rafiq
              </button>
              <button
                onClick={() => applyPreset('P-DEEPAK', 'CASE-141', 6)}
                className="rounded-md border border-neutral-200 bg-white px-2 py-1 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 transition-colors shadow-2xs"
              >
                📱 Deepak ↔ FIR-141
              </button>
            </div>
          </div>

          {/* Form Selectors */}
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-12 sm:items-end">
            {/* Source Entity Selector */}
            <div className="sm:col-span-4">
              <PathfinderEntitySelector
                label="Source Entity / Case"
                dotColor="blue"
                selectedId={sourceId}
                onSelect={setSourceId}
                activeGraphNodes={graph?.nodes}
                testId="pathfinder-source-select"
              />
            </div>

            {/* Swap Button */}
            <div className="flex justify-center sm:col-span-1 pb-1">
              <button
                onClick={handleSwap}
                title="Swap source and target"
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-600 hover:border-blue-500 hover:text-blue-600 hover:bg-blue-50 transition-all shadow-xs"
              >
                <ArrowRightLeft className="h-4 w-4" />
              </button>
            </div>

            {/* Target Entity Selector */}
            <div className="sm:col-span-4">
              <PathfinderEntitySelector
                label="Target Entity / Case"
                dotColor="rose"
                selectedId={targetId}
                onSelect={setTargetId}
                activeGraphNodes={graph?.nodes}
                testId="pathfinder-target-select"
              />
            </div>

            {/* Max Hops Slider */}
            <div className="sm:col-span-3 pb-1">
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-bold text-neutral-700">Max Search Depth</label>
                <span className="text-xs font-bold text-blue-700">{maxHops} Hops</span>
              </div>
              <input
                type="range"
                min={1}
                max={10}
                value={maxHops}
                onChange={(e) => setMaxHops(Number(e.target.value))}
                className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            </div>
          </div>

          {/* Pathfinder Results Presentation */}
          <div className="mt-4 border-t border-blue-100 pt-3">
            {pathQuery.isLoading && (
              <div className="flex items-center gap-2 text-xs text-blue-800 py-2">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
                <span>Running BFS graph traversal across evidence relationships…</span>
              </div>
            )}

            {pathQuery.data && (
              pathQuery.data.found ? (
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800 border border-emerald-200">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Connected in {pathQuery.data.hops} {pathQuery.data.hops === 1 ? 'Hop' : 'Hops'}
                      </span>
                      <span className="text-xs text-neutral-500">
                        ({pathQuery.data.node_ids.length} entities, {pathQuery.data.edge_ids.length} verified relationships)
                      </span>
                    </div>
                    <span className="text-[11px] text-blue-600 font-semibold">
                      💡 Click any relationship in the path to inspect underlying evidence
                    </span>
                  </div>

                  {/* Narrative explanation */}
                  <p className="text-xs sm:text-sm text-neutral-800 font-medium leading-relaxed bg-white/80 p-3 rounded-lg border border-blue-100 shadow-2xs">
                    {pathQuery.data.explanation}
                  </p>

                  {/* Step-by-Step Breadcrumb Chain */}
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                      Investigative Chain Steps:
                    </span>
                    <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto py-1">
                      {pathQuery.data.node_ids.map((nId, idx) => {
                        const nodeObj = nodesById.get(nId)
                        const edgeObj = idx < pathQuery.data.edge_ids.length ? edgesById.get(pathQuery.data.edge_ids[idx]) : null
                        const edgeIdVal = pathQuery.data.edge_ids[idx]

                        return (
                          <div key={nId} className="flex items-center gap-1.5">
                            {/* Node Chip */}
                            <div
                              className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-bold shadow-2xs ${
                                idx === 0
                                  ? 'bg-blue-50 border-blue-300 text-blue-900'
                                  : idx === pathQuery.data.node_ids.length - 1
                                  ? 'bg-rose-50 border-rose-300 text-rose-900'
                                  : 'bg-white border-neutral-300 text-neutral-800'
                              }`}
                            >
                              <span className="text-[10px] font-mono text-neutral-400">#{idx + 1}</span>
                              <span>{nodeObj?.label || nId}</span>
                              <span className="rounded bg-neutral-100 px-1 py-0.2 text-[9px] font-mono text-neutral-500 uppercase">
                                {nodeObj?.entity_type || 'Node'}
                              </span>
                            </div>

                            {/* Edge connector if not last */}
                            {edgeObj && (
                              <button
                                onClick={() => setEdgeId(edgeIdVal)}
                                title={`Click to view evidence for: ${edgeObj.edge_type}`}
                                className="group flex items-center gap-1 rounded-md bg-blue-100/70 hover:bg-blue-200/90 border border-blue-200 px-2 py-0.8 text-[11px] font-semibold text-blue-900 transition-colors shadow-2xs"
                              >
                                <span className="group-hover:underline">
                                  {String(edgeObj.label || edgeObj.edge_type || '').replaceAll('_', ' ')}
                                </span>
                                <ExternalLink className="h-3 w-3 text-blue-600 group-hover:scale-110 transition-transform" />
                              </button>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Evidence Citations */}
                  {pathQuery.data.evidence_ids.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-[11px] text-neutral-500 font-bold uppercase tracking-wider mr-1">
                        Supporting Evidence:
                      </span>
                      {pathQuery.data.evidence_ids.map((id) => (
                        <code
                          key={id}
                          className="rounded bg-amber-50 px-2 py-0.5 text-[11px] font-mono text-amber-900 border border-amber-200 shadow-2xs"
                        >
                          {id}
                        </code>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-lg bg-amber-50/80 border border-amber-200 p-3 text-xs text-amber-900 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold">
                    <ShieldQuestion className="h-4 w-4 text-amber-600" />
                    No Direct or Indirect Connection Found
                  </div>
                  <p className="text-amber-800 leading-relaxed">
                    {pathQuery.data.explanation}
                  </p>
                  {replay === 'before' && (
                    <p className="text-[11px] text-amber-700 pt-1 font-medium">
                      💡 Tip: Switch to <strong>After resolution</strong> to reveal links unified by entity resolution decisions.
                    </p>
                  )}
                </div>
              )
            )}
          </div>
        </div>
      )}

      {hasActiveGraph && activeQuery.isLoading && <LoadingSkeleton layout="detail" />}
      {hasActiveGraph && activeQuery.isError && !isEntityScoped && !isCaseScoped && !afterUnavailable && (
        <ErrorState message="Failed to load the investigation network." onRetry={() => void activeQuery.refetch()} />
      )}

      {isEntityScoped && !activeQuery.isLoading && (activeQuery.isError || !entityQuery.data || entityQuery.data.total_nodes === 0) && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900 shadow-sm space-y-2">
          <div className="flex items-center gap-2 font-bold text-base text-amber-950">
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
            No graph relationships found for entity: <span className="font-mono">{nodeIdParam}</span>
          </div>
          <p className="text-amber-800">
            No recorded relationships or multi-hop connections are available for this entity in the active intelligence repository.
          </p>
        </div>
      )}

      {isCaseScoped && !isDemoCase && !activeQuery.isLoading && (activeQuery.isError || !caseQuery.data || caseQuery.data.total_nodes === 0) && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900 shadow-sm space-y-2">
          <div className="flex items-center gap-2 font-bold text-base text-amber-950">
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
            No graph relationships found for case: <span className="font-mono">{caseIdParam}</span>
          </div>
          <p className="text-amber-800">
            No recorded relationships or multi-hop connections are available for this case in the active intelligence repository.
          </p>
        </div>
      )}

      {!hasActiveGraph && (
        <div className="rounded-2xl border border-dashed border-neutral-300 bg-white/80 p-10 sm:p-14 text-center space-y-4 shadow-2xs">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 border border-blue-200 shadow-xs">
            <Network className="h-6 w-6" />
          </div>
          <div className="max-w-md mx-auto space-y-1.5">
            <h3 className="text-base sm:text-lg font-bold text-neutral-900">No investigation selected</h3>
            <p className="text-xs sm:text-sm text-neutral-600 leading-relaxed">
              Select entities or open a case to explore its network.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Link
              to="/worklist"
              className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-300 bg-white px-3.5 py-2 text-xs font-bold text-neutral-800 hover:bg-neutral-50 transition-colors shadow-xs"
            >
              <Briefcase className="h-3.5 w-3.5 text-neutral-600" />
              Open Investigations Worklist
            </Link>
            <button
              onClick={() => setShowPathfinder(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 hover:bg-blue-100 px-3.5 py-2 text-xs font-bold text-blue-700 transition-colors shadow-2xs"
            >
              <Route className="h-3.5 w-3.5" />
              Open Pathfinder
            </button>
            <button
              onClick={() => {
                applyPreset('CASE-141', 'CASE-207', 6)
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 px-3.5 py-2 text-xs font-bold text-white transition-colors shadow-sm"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Load Demo Case (FIR-141 ↔ FIR-207)
            </button>
          </div>
        </div>
      )}

      {afterUnavailable && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900 shadow-sm">
          <p className="font-semibold">The "After resolution" snapshot does not exist yet.</p>
          <p className="mt-1 text-amber-800">
            Confirm the pending entity match first — the merged network is generated from that decision.{' '}
            <Link to="/fusion" className="font-bold underline hover:text-amber-950 text-blue-700">
              Open Entity Fusion
            </Link>
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
          <GlobalNetworkCanvas
            graph={graph}
            diff={replay === 'after' ? diff.data ?? null : null}
            highlightDelta={replay === 'after'}
            initialCaseFilter={caseIdParam}
            initialNodeId={nodeIdParam}
            pathNodeIds={showPathfinder && pathQuery.data?.found ? pathQuery.data.node_ids : null}
            pathEdgeIds={showPathfinder && pathQuery.data?.found ? pathQuery.data.edge_ids : null}
            onSetSource={(id) => {
              setSourceId(id)
              setShowPathfinder(true)
            }}
            onSetTarget={(id) => {
              setTargetId(id)
              setShowPathfinder(true)
            }}
            onEdgeSelect={setEdgeId}
          />
        </>
      )}

      <EvidenceDrawer relationshipId={edgeId} onClose={() => setEdgeId(null)} />
    </div>
  )
}
