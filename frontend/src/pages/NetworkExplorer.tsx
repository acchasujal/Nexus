import { useState, useMemo, useEffect } from 'react'
import {
  Network,
  RotateCcw,
  Route,
  ShieldQuestion,
  ArrowRightLeft,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Briefcase,
} from 'lucide-react'
import { useNexusNetwork, useSnapshotDiff, useNexusPath, useEntityNetwork, useCaseNetworkData, useBatchNetwork, useResolutionCandidates } from '@/hooks/useNexus'
import { GlobalNetworkCanvas } from '@/components/nexus/GlobalNetworkCanvas'
import { EvidenceDrawer } from '@/components/nexus/EvidenceDrawer'
import { EntityDetailsDrawer } from '@/components/nexus/EntityDetailsDrawer'
import { DerivationBadge } from '@/components/nexus/DerivationBadge'
import { PathfinderEntitySelector } from '@/components/nexus/PathfinderEntitySelector'
import { NetworkDeltaSummary } from '@/components/nexus/NetworkDeltaSummary'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { PageHeader } from '@/components/ui/PageHeader'
import { Link, useSearchParams } from 'react-router-dom'
import type {
  NetworkGraphResponse,
  NexusNetworkResponse,
  NexusPathResponse,
  NexusGraphNode,
  NexusGraphEdge,
} from '@shared/contracts/api'

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

function mergeNetworkGraphs(
  graphs: (NetworkGraphResponse | undefined | null)[],
  pathData?: NexusPathResponse | null,
  snapshotId: string = 'ACTIVE-INVESTIGATION'
): NexusNetworkResponse | null {
  const validGraphs = graphs.filter((g): g is NetworkGraphResponse => Boolean(g && (g.nodes?.length || 0) > 0))
  if (validGraphs.length === 0 && (!pathData || !pathData.found || pathData.node_ids.length === 0)) {
    return null
  }

  const nodesMap = new Map<string, NexusGraphNode>()
  const edgesMap = new Map<string, NexusGraphEdge>()

  for (const g of validGraphs) {
    const nexusG = toNexusGraph(g, snapshotId)
    for (const node of nexusG.nodes) {
      if (!nodesMap.has(node.id)) {
        nodesMap.set(node.id, node)
      }
    }
    for (const edge of nexusG.edges) {
      if (!edgesMap.has(edge.id)) {
        edgesMap.set(edge.id, edge)
      }
    }
  }

  // If path traversal returned nodes/edges, ensure they are present in the canvas
  if (pathData && pathData.found) {
    for (const nid of pathData.node_ids) {
      if (!nodesMap.has(nid)) {
        nodesMap.set(nid, {
          id: nid,
          entity_type: 'Person',
          label: nid,
          case_ids: [],
          properties: {},
        })
      }
    }
    for (let i = 0; i < pathData.node_ids.length - 1; i++) {
      const u = pathData.node_ids[i]
      const v = pathData.node_ids[i + 1]
      const edgeId = pathData.edge_ids[i] || `edge-${u}-${v}`
      if (!edgesMap.has(edgeId)) {
        edgesMap.set(edgeId, {
          id: edgeId,
          source_id: u,
          target_id: v,
          edge_type: 'CONNECTED_TO',
          weight: 1.0,
          confidence: 1.0,
          derivation_class: 'FACT',
          recorded_at: new Date().toISOString(),
          case_ids: [],
          properties: {},
        })
      }
    }
  }

  const allNodes = Array.from(nodesMap.values())
  const allEdges = Array.from(edgesMap.values())

  return {
    snapshot_id: snapshotId,
    state: 'before',
    nodes: allNodes,
    edges: allEdges,
    total_nodes: allNodes.length,
    total_edges: allEdges.length,
  }
}

export default function NetworkExplorer() {
  const [searchParams, setSearchParams] = useSearchParams()
  const caseIdParam = searchParams.get('case_id')
  const targetCaseIdParam = searchParams.get('target_case_id')
  const nodeIdParam = searchParams.get('node_id')
  const batchIdParam = searchParams.get('batch_id')
  const snapshotParam = searchParams.get('snapshot')
  const focusParam = searchParams.get('focus')
  const caseFocusParam = searchParams.get('case_focus')
  
  const drawerParam = searchParams.get('drawer') === 'true'
  const [replay, setReplay] = useState<ReplayState>(snapshotParam === 'after' ? 'after' : 'before')
  const [edgeId, setEdgeId] = useState<string | null>(null)
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(drawerParam ? nodeIdParam : null)
  const validFocusModes = ['ALL', '1HOP', '2HOP', 'CROSS_CASE'] as const
  type FocusMode = (typeof validFocusModes)[number]
  const parsedFocus = focusParam?.toUpperCase().replace('-', '')
  const initialFocus = validFocusModes.includes(parsedFocus as FocusMode) ? parsedFocus as FocusMode : 'ALL'
  const [densityMode, setDensityMode] = useState<FocusMode>(initialFocus)

  const updateNetworkUrl = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null) next.delete(key)
      else next.set(key, value)
    })
    setSearchParams(next)
  }

  // URL changes from Back/Forward or external navigation are the only state sync direction.
  useEffect(() => {
    setReplay(snapshotParam === 'after' ? 'after' : 'before')
    const nextFocus = focusParam?.toUpperCase().replace('-', '')
    setDensityMode(validFocusModes.includes(nextFocus as FocusMode) ? nextFocus as FocusMode : 'ALL')
    if (drawerParam) {
      setSelectedEntityId(nodeIdParam)
    } else {
      setSelectedEntityId(null)
    }
  }, [snapshotParam, focusParam, nodeIdParam, drawerParam])

  const batchNetwork = useBatchNetwork(batchIdParam, Boolean(batchIdParam))
  const candidatesQuery = useResolutionCandidates()

  const candidatePresets = useMemo(() => {
    return (candidatesQuery.data || []).map((c) => {
      const leftCase = c.left.case_ids?.[0]
      const rightCase = c.right.case_ids?.[0]
      if (leftCase && rightCase && leftCase !== rightCase) {
        const leftName = leftCase.replace(/^CASE-/, 'FIR-')
        const rightName = rightCase.replace(/^CASE-/, 'FIR-')
        return {
          id: c.id,
          label: `🌟 ${leftName} ↔ ${rightName}`,
          src: leftCase,
          tgt: rightCase,
        }
      }
      return {
        id: c.id,
        label: `🔍 ${c.left.label || c.left.node_id} ↔ ${c.right.label || c.right.node_id}`,
        src: c.left.node_id,
        tgt: c.right.node_id,
      }
    })
  }, [candidatesQuery.data])

  // ── Dynamic Pathfinder & Exploration State ──────────────────────────────────
  const [showPathfinder, setShowPathfinder] = useState(false)
  const [sourceId, setSourceId] = useState(caseIdParam || nodeIdParam || '')
  const [targetId, setTargetId] = useState('')
  const [maxHops, setMaxHops] = useState(6)

  // Pre-fill from query params if requested
  useEffect(() => {
    if (caseIdParam) {
      setSourceId(caseIdParam)
      if (targetCaseIdParam) {
        setTargetId(targetCaseIdParam)
        setShowPathfinder(true)
      }
    } else if (nodeIdParam) {
      setSourceId(nodeIdParam)
      setShowPathfinder(true)
    }
  }, [caseIdParam, targetCaseIdParam, nodeIdParam])

  // Context classification
  const isEntityScoped = Boolean(nodeIdParam)
  const isCaseScoped = Boolean(caseIdParam)

  const effectiveSourceId = sourceId || nodeIdParam || ''
  const effectiveTargetId = targetId || ''
  
  // If no params are provided, we show the global network
  const isGlobalNetwork = !isCaseScoped && !isEntityScoped && !batchIdParam && !effectiveSourceId && !effectiveTargetId
  
  const isCaseId = (id?: string | null) => Boolean(id && (id.toUpperCase().startsWith('CASE') || id.toUpperCase().startsWith('FIR')))
  const isCasePath = Boolean(sourceId && targetId && isCaseId(sourceId) && isCaseId(targetId))
  const isEntityPath = Boolean((effectiveSourceId && !isCaseId(effectiveSourceId)) || (effectiveTargetId && !isCaseId(effectiveTargetId)))

  // Use the unified cross-case network for global view, snapshot diff replays, or case views when not exploring specific non-case entities
  const useUnifiedNetwork = !isEntityPath && (isGlobalNetwork || Boolean(snapshotParam) || Boolean(isCaseScoped && !isEntityScoped) || isCasePath)

  const hasSelection = Boolean(isGlobalNetwork || batchIdParam || useUnifiedNetwork || isCaseScoped || isEntityScoped || effectiveSourceId || effectiveTargetId)

  // Network queries
  const sourceEntityQuery = useEntityNetwork(
    effectiveSourceId,
    2,
    Boolean(!useUnifiedNetwork && effectiveSourceId && !isCaseId(effectiveSourceId))
  )
  const targetEntityQuery = useEntityNetwork(
    effectiveTargetId,
    2,
    Boolean(!useUnifiedNetwork && effectiveTargetId && effectiveTargetId !== effectiveSourceId && !isCaseId(effectiveTargetId))
  )
  const caseQuery = useCaseNetworkData(
    caseIdParam,
    2,
    Boolean(isCaseScoped && !useUnifiedNetwork)
  )
  const demoQuery = useNexusNetwork(
    replay,
    useUnifiedNetwork
  )
  const diff = useSnapshotDiff(replay === 'after' && useUnifiedNetwork && demoQuery.data?.state === 'after')

  const pathQuery = useNexusPath(sourceId, targetId, maxHops, showPathfinder && Boolean(sourceId && targetId))

  const activeQuery = useUnifiedNetwork
    ? demoQuery
    : isCaseScoped && !isEntityScoped
    ? caseQuery
    : sourceEntityQuery

  const graph: NexusNetworkResponse | null = useMemo(() => {
    if (batchIdParam) {
      return batchNetwork.data ?? null
    }
    if (useUnifiedNetwork) {
      return demoQuery.data ?? null
    }
    if (isCaseScoped && !isEntityScoped) {
      if (!caseQuery.data || caseQuery.data.total_nodes === 0) return null
      return toNexusGraph(caseQuery.data, `CASE-${caseIdParam}`)
    }
    if (effectiveSourceId || effectiveTargetId) {
      return mergeNetworkGraphs(
        [sourceEntityQuery.data, targetEntityQuery.data],
        pathQuery.data,
        effectiveSourceId ? `ENTITY-${effectiveSourceId}` : 'PATHFINDER-GRAPH'
      )
    }
    return null
  }, [
    useUnifiedNetwork,
    isGlobalNetwork,
    demoQuery.data,
    isCaseScoped,
    isEntityScoped,
    caseIdParam,
    caseQuery.data,
    effectiveSourceId,
    effectiveTargetId,
    sourceEntityQuery.data,
    targetEntityQuery.data,
    pathQuery.data,
    batchIdParam,
    batchNetwork.data,
  ])

  const afterUnavailable = useUnifiedNetwork && replay === 'after' && demoQuery.error

  // Lookups for labels and edges
  const nodesById = useMemo(() => {
    if (!graph?.nodes) return new Map()
    return new Map(graph.nodes.map((n) => [n.id, n]))
  }, [graph?.nodes])

  const edgesById = useMemo(() => {
    if (!graph?.edges) return new Map()
    return new Map(graph.edges.map((e) => [e.id, e]))
  }, [graph?.edges])

  /** Apply density/investigator mode filter to reduce graph clutter */
  const filteredGraph = useMemo(() => {
    if (!graph || densityMode === 'ALL') return graph
    const anchorId = effectiveSourceId || nodeIdParam || caseIdParam || ''
    if (densityMode === 'CROSS_CASE') {
      // Keep only nodes that appear in more than one case_ids entry
      const crossCaseNodes = new Set(
        graph.nodes.filter((n) => n.case_ids && n.case_ids.length > 1).map((n) => n.id)
      )
      const edges = graph.edges.filter(
        (e) => crossCaseNodes.has(e.source_id) && crossCaseNodes.has(e.target_id)
      )
      const nodeIds = new Set([...edges.map((e) => e.source_id), ...edges.map((e) => e.target_id)])
      return { ...graph, nodes: graph.nodes.filter((n) => nodeIds.has(n.id)), edges, total_nodes: nodeIds.size, total_edges: edges.length }
    }
    if (densityMode === '1HOP' && anchorId) {
      const directEdges = graph.edges.filter((e) => e.source_id === anchorId || e.target_id === anchorId)
      const nodeIds = new Set([anchorId, ...directEdges.map((e) => e.source_id), ...directEdges.map((e) => e.target_id)])
      return { ...graph, nodes: graph.nodes.filter((n) => nodeIds.has(n.id)), edges: directEdges, total_nodes: nodeIds.size, total_edges: directEdges.length }
    }
    if (densityMode === '2HOP' && anchorId) {
      const hop1Edges = graph.edges.filter((e) => e.source_id === anchorId || e.target_id === anchorId)
      const hop1Ids = new Set([anchorId, ...hop1Edges.map((e) => e.source_id), ...hop1Edges.map((e) => e.target_id)])
      const hop2Edges = graph.edges.filter((e) => hop1Ids.has(e.source_id) || hop1Ids.has(e.target_id))
      const nodeIds = new Set([...hop1Ids, ...hop2Edges.map((e) => e.source_id), ...hop2Edges.map((e) => e.target_id)])
      return { ...graph, nodes: graph.nodes.filter((n) => nodeIds.has(n.id)), edges: hop2Edges, total_nodes: nodeIds.size, total_edges: hop2Edges.length }
    }
    return graph
  }, [graph, densityMode, effectiveSourceId, nodeIdParam, caseIdParam])

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
  }

  return (
    <div className="space-y-5 max-w-7xl mx-auto w-full">
      {/* Header & Controls */}
      <PageHeader
        icon={Network}
        title="Global Network Explorer"
        subtitle="Multi-jurisdictional criminal network topology. Discover entity bridges, flow paths, and evidentiary provenance."
        actions={
          <>
            <button
              onClick={() => setShowPathfinder((v) => !v)}
              className={`inline-flex items-center gap-1.5 sm:gap-2 rounded-lg border px-3 py-1.5 sm:py-2 text-xs sm:text-sm font-semibold transition-all shadow-xs cursor-pointer ${
                showPathfinder
                  ? 'border-blue-600 bg-blue-50 text-blue-800 ring-2 ring-blue-500/20'
                  : 'border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50 hover:text-neutral-900'
              }`}
              aria-expanded={showPathfinder}
            >
              <Route className="h-4 w-4 text-blue-600" />
              Investigative Pathfinder
            </button>
            <div
              role="group"
              aria-label="Network snapshot replay"
              className="flex items-center rounded-lg border border-neutral-200 bg-neutral-100/80 p-0.5 sm:p-1 text-xs sm:text-sm font-semibold shadow-2xs"
            >
              <button
                onClick={() => {
                  setReplay('before')
                  updateNetworkUrl({ snapshot: 'before' })
                }}
                aria-pressed={replay === 'before'}
                className={`rounded-md px-2.5 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm transition-colors cursor-pointer ${
                  replay === 'before'
                    ? 'bg-white text-neutral-900 shadow-xs font-bold'
                    : 'text-neutral-600 hover:text-neutral-900'
                }`}
              >
                Before resolution
              </button>
              <button
                onClick={() => {
                  setReplay('after')
                  updateNetworkUrl({ snapshot: 'after' })
                }}
                aria-pressed={replay === 'after'}
                disabled={demoQuery.isLoading && !demoQuery.data}
                className={`rounded-md px-2.5 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm transition-colors disabled:opacity-40 cursor-pointer ${
                  replay === 'after'
                    ? 'bg-emerald-600 text-white shadow-xs font-bold'
                    : 'text-neutral-600 hover:text-neutral-900'
                }`}
              >
                After resolution
              </button>
            </div>
          </>
        }
      />

      {/* ── Network Delta (What Changed) Component ───────────────────────────── */}
      <NetworkDeltaSummary activeSnapshot={replay} />

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
              {candidatePresets
                .filter((p) => !(p.src === 'CASE-141' && p.tgt === 'CASE-207'))
                .map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => applyPreset(preset.src, preset.tgt, 6)}
                    className="rounded-md border border-blue-200 bg-white px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50 transition-colors shadow-2xs"
                  >
                    {preset.label}
                  </button>
                ))}
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

      {hasSelection && activeQuery.isLoading && <LoadingSkeleton layout="detail" />}
      {hasSelection && activeQuery.isError && useUnifiedNetwork && !afterUnavailable && (
        <ErrorState message="Failed to load the investigation network." onRetry={() => void activeQuery.refetch()} />
      )}

      {hasSelection && !useUnifiedNetwork && !activeQuery.isLoading && !graph && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900 shadow-sm space-y-2">
          <div className="flex items-center gap-2 font-bold text-base text-amber-950">
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
            No graph relationships found for {isCaseScoped ? 'case' : 'entity'}: <span className="font-mono">{effectiveSourceId || caseIdParam || 'selected entity'}</span>
          </div>
          <p className="text-amber-800">
            No recorded relationships or multi-hop connections are available for this selection in the active intelligence repository.
          </p>
        </div>
      )}

      {!hasSelection && (
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
              Snapshot <code className="text-neutral-900 font-semibold">{filteredGraph?.snapshot_id ?? graph.snapshot_id}</code> · {filteredGraph?.total_nodes ?? graph.total_nodes} nodes · {filteredGraph?.total_edges ?? graph.total_edges} links
            </span>
            <div className="flex items-center gap-1.5" role="group" aria-label="Graph density filter">
              {(
                [['ALL', 'All Nodes'], ['1HOP', '1-Hop'], ['2HOP', '2-Hop'], ['CROSS_CASE', 'Cross-Case']] as const
              ).map(([mode, label]) => (
                <button
                  key={mode}
                  onClick={() => {
                    setDensityMode(mode)
                    updateNetworkUrl({ focus: mode === 'ALL' ? 'all' : mode.toLowerCase() })
                  }}
                  title={mode === 'CROSS_CASE' ? 'Show only nodes shared across multiple cases' : mode === '1HOP' ? 'Show direct neighbours of the anchor node' : mode === '2HOP' ? 'Show up to 2-hop neighbours' : 'Show full graph'}
                  className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold border transition-colors ${
                    densityMode === mode
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-neutral-700 border-neutral-300 hover:bg-neutral-50'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
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
            graph={filteredGraph ?? graph}
            diff={replay === 'after' ? diff.data ?? null : null}
            highlightDelta={replay === 'after'}
            initialCaseFilter={caseIdParam}
            caseFocus={caseFocusParam}
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
            onOpenDetails={(nId) => {
              setSelectedEntityId(nId)
              updateNetworkUrl({ node_id: nId, drawer: 'true' })
            }}
            onCaseFocusChange={(caseId) => updateNetworkUrl({ case_focus: caseId })}
          />
        </>
      )}

      <EvidenceDrawer relationshipId={edgeId} onClose={() => setEdgeId(null)} />
      <EntityDetailsDrawer
        entityId={selectedEntityId}
        onClose={() => {
          setSelectedEntityId(null)
          updateNetworkUrl({ node_id: null, drawer: null })
        }}
        onFocusEntity={(nId) => {
          setSourceId(nId)
          setShowPathfinder(true)
        }}
      />
    </div>
  )
}
