/**
 * frontend/src/components/nexus/GlobalNetworkCanvas.tsx
 *
 * Global Network Explorer canvas powered by D3.js Force-Directed Graph Engine.
 * Features:
 * - Entity-type layer toggles & case focus filters
 * - Dynamic D3 physics simulation with drag-to-pin
 * - Louvain community rings, delta highlights, and parallel edge curvature
 * - Focus & neighborhood dimming on click
 * - Interactive legend and zoom controls
 */
import { useMemo, useState, useEffect } from 'react'
import {
  User, Briefcase, Phone, Landmark, BadgeCheck, Sparkles,
} from 'lucide-react'
import type { NexusNetworkResponse, SnapshotDiffResponse } from '@shared/contracts/api'
import { D3NetworkGraph, type D3GraphNode, type D3GraphEdge, EDGE_STROKES } from './D3NetworkGraph'

interface GlobalNetworkCanvasProps {
  graph: NexusNetworkResponse
  diff?: SnapshotDiffResponse | null
  highlightDelta?: boolean
  initialCaseFilter?: string | null
  caseFocus?: string | null
  initialNodeId?: string | null
  pathNodeIds?: string[] | null
  pathEdgeIds?: string[] | null
  onEdgeSelect: (edgeId: string) => void
  onNodeSelect?: (nodeId: string) => void
  onSetSource?: (nodeId: string, nodeLabel: string) => void
  onSetTarget?: (nodeId: string, nodeLabel: string) => void
  onOpenDetails?: (nodeId: string) => void
  onCaseFocusChange?: (caseId: string) => void
}

const NODE_STYLE: Record<string, { icon: typeof User; ring: string; chip: string; bg: string }> = {
  Person: { icon: User, ring: 'border-sky-500', chip: 'text-sky-900 bg-sky-50 border border-sky-200', bg: 'bg-sky-500' },
  Case: { icon: Briefcase, ring: 'border-rose-500', chip: 'text-rose-900 bg-rose-50 border border-rose-200', bg: 'bg-rose-500' },
  Phone: { icon: Phone, ring: 'border-amber-500', chip: 'text-amber-900 bg-amber-50 border border-amber-200', bg: 'bg-amber-500' },
  Account: { icon: Landmark, ring: 'border-violet-500', chip: 'text-violet-900 bg-violet-50 border border-violet-200', bg: 'bg-violet-500' },
}

export function GlobalNetworkCanvas({
  graph,
  diff,
  highlightDelta = false,
  caseFocus,
  initialNodeId,
  pathNodeIds,
  pathEdgeIds,
  onEdgeSelect,
  onNodeSelect,
  onSetSource,
  onSetTarget,
  onOpenDetails,
  onCaseFocusChange,
}: GlobalNetworkCanvasProps) {
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())
  const [selectedNode, setSelectedNode] = useState<string | null>(initialNodeId || null)
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null)
  const [showLegendMobile, setShowLegendMobile] = useState(false)

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (initialNodeId && graph?.nodes?.some((n) => n.id === initialNodeId)) {
      setSelectedNode(initialNodeId)
      onNodeSelect?.(initialNodeId)
    } else if (!initialNodeId) {
      setSelectedNode(null)
    }
  }, [initialNodeId, graph, onNodeSelect])
  /* eslint-enable react-hooks/set-state-in-effect */

  const addedNodes = useMemo(() => new Set(diff?.added_node_ids ?? []), [diff])
  const addedEdges = useMemo(() => new Set(diff?.added_edge_ids ?? []), [diff])

  const caseOptions = useMemo(() => {
    const ids = new Set<string>()
    graph.nodes.forEach((n) => n.case_ids.forEach((c) => ids.add(c)))
    return ['ALL', ...[...ids].sort()]
  }, [graph])

  // If the initial case filter from URL doesn't match any known case, fall back to ALL
  const resolvedInitialFilter = useMemo(() => {
    if (caseFocus?.toUpperCase() === 'ALL') return 'ALL'
    if (caseFocus) {
      const exactFocus = caseOptions.find((c) => c.toUpperCase() === caseFocus.toUpperCase())
      if (exactFocus) return exactFocus
      return 'ALL'
    }
    return 'ALL'
  }, [caseFocus, caseOptions])

  const [caseFilter, setCaseFilter] = useState<string>(resolvedInitialFilter)

  // Sync filter if resolved value changes (e.g. graph data loads after mount)
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const nextFilter = caseFocus?.toUpperCase() === 'ALL' ? 'ALL' : resolvedInitialFilter
    if (caseFilter !== nextFilter) {
      setCaseFilter(nextFilter)
    }
  }, [resolvedInitialFilter, caseFocus, caseFilter])
  /* eslint-enable react-hooks/set-state-in-effect */

  const toggleType = (t: string) =>
    setHiddenTypes((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })

  const visibleRawNodes = useMemo(
    () => graph.nodes.filter((n) => !hiddenTypes.has(n.entity_type) && (caseFilter === 'ALL' || n.case_ids.includes(caseFilter) || n.id === selectedNode)),
    [graph, hiddenTypes, caseFilter, selectedNode],
  )

  const visibleIds = useMemo(() => new Set(visibleRawNodes.map((n) => n.id)), [visibleRawNodes])

  // Transform nodes for D3
  const d3Nodes = useMemo<D3GraphNode[]>(() => {
    return visibleRawNodes.map((n) => ({
      id: n.id,
      label: n.label,
      name: n.label,
      entity_type: n.entity_type,
      type: n.entity_type,
      case_ids: n.case_ids,
      badges: n.badges,
      isDelta: highlightDelta && addedNodes.has(n.id),
      properties: n.properties,
    }))
  }, [visibleRawNodes, highlightDelta, addedNodes])

  // Transform edges for D3
  const d3Edges = useMemo<D3GraphEdge[]>(() => {
    return graph.edges
      .filter((e) => visibleIds.has(e.source_id) && visibleIds.has(e.target_id))
      .map((e) => ({
        id: e.id,
        source: e.source_id,
        target: e.target_id,
        edge_type: e.edge_type,
        label: e.edge_type.replaceAll('_', ' '),
        derivation_class: e.derivation_class,
        confidence: e.confidence,
        properties: e.properties,
        timestamp: e.recorded_at,
      }))
  }, [graph.edges, visibleIds])

  const typeOptions = [...new Set(graph.nodes.map((n) => n.entity_type))]
  const edgeTypeOptions = [...new Set(graph.edges.map((e) => e.edge_type))]

  return (
    <div className="relative h-[500px] sm:h-[560px] md:h-[620px] w-full overflow-hidden rounded-xl border border-neutral-200 bg-slate-50 shadow-sm flex flex-col">
      {/* Delta indicator */}
      {highlightDelta && (
        <div className="absolute right-2 sm:right-3 top-2 sm:top-3 z-10 rounded-lg border border-emerald-200 bg-emerald-50 px-2 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-[11px] font-bold text-emerald-900 shadow-md">
          {addedNodes.size} nodes / {addedEdges.size} links unified
        </div>
      )}

      {/* Edge & Node Legend */}
      <div className="absolute bottom-2 sm:bottom-3 left-2 sm:left-3 z-10">
        <button
          onClick={() => setShowLegendMobile(!showLegendMobile)}
          className="sm:hidden flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white/95 backdrop-blur px-2.5 py-1 text-[10px] font-bold text-neutral-700 shadow-md"
        >
          {showLegendMobile ? 'Hide Legend' : 'Show Legend'}
        </button>

        <div className={`${showLegendMobile ? 'block mt-1.5' : 'hidden'} sm:block space-y-1.5 rounded-lg border border-neutral-200 bg-white/95 backdrop-blur p-2.5 text-[10px] text-neutral-700 shadow-md max-w-xs`}>
          <div className="font-bold text-neutral-800 uppercase tracking-wider text-[9px] mb-1">Entities</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1">
            {typeOptions.map(t => {
              const style = NODE_STYLE[t] || { bg: 'bg-neutral-500' }
              return (
                <div key={t} className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${style.bg}`} /> {t === 'Case' ? 'Case / FIR' : t}
                </div>
              )
            })}
          </div>
          <div className="border-t border-neutral-200 pt-1 mt-1 font-bold text-neutral-800 uppercase tracking-wider text-[9px]">Relationships</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1">
            {edgeTypeOptions.map(t => (
              <div key={t} className="flex items-center gap-1.5">
                <span className="h-1 w-3 rounded" style={{ backgroundColor: EDGE_STROKES[t] || '#9ca3af' }} />
                {t.replaceAll('_', ' ')}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* D3 Force-Directed Canvas */}
      <D3NetworkGraph
        nodes={d3Nodes}
        edges={d3Edges}
        selectedNodeId={selectedNode}
        selectedEdgeId={selectedEdge}
        pathNodeIds={pathNodeIds}
        pathEdgeIds={pathEdgeIds}
        onSetSource={onSetSource}
        onSetTarget={onSetTarget}
        onOpenDetails={onOpenDetails}
        onNodeSelect={(nodeId) => {
          setSelectedNode(nodeId)
          if (nodeId) onNodeSelect?.(nodeId)
        }}
        onEdgeSelect={(edgeId) => {
          setSelectedEdge(edgeId)
          if (edgeId) onEdgeSelect(edgeId)
        }}
        highlightDelta={highlightDelta}
        enableTemporalScrubber={true}
        customHeaderControls={
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs">
            <span className="font-bold uppercase tracking-wider text-neutral-600 text-[10px] sm:text-xs shrink-0">Layers</span>
            {typeOptions.map((t) => (
              <button
                key={t}
                onClick={() => toggleType(t)}
                aria-pressed={!hiddenTypes.has(t)}
                className={`rounded-md border px-2 sm:px-2.5 py-0.5 text-[11px] sm:text-xs font-semibold transition-colors ${
                  hiddenTypes.has(t)
                    ? 'border-neutral-200 bg-neutral-100 text-neutral-400'
                    : `${NODE_STYLE[t]?.ring ?? 'border-neutral-300'} bg-white text-neutral-900 shadow-2xs`
                }`}
              >
                {t}
              </button>
            ))}
            <span className="mx-0.5 h-3 sm:h-4 w-px bg-neutral-200 shrink-0" />
            <label htmlFor="case-focus" className="font-bold uppercase tracking-wider text-neutral-600 text-[10px] sm:text-xs shrink-0">Focus</label>
            <select
              id="case-focus"
              value={caseFilter}
              onChange={(e) => {
                const nextFilter = e.target.value
                setCaseFilter(nextFilter)
                onCaseFocusChange?.(nextFilter)
              }}
              className="rounded-md border border-neutral-300 bg-white px-2 py-0.5 text-[11px] sm:text-xs text-neutral-900 focus:border-blue-500 focus:outline-none shadow-2xs"
            >
              {caseOptions.map((c) => (
                <option key={c} value={c}>{c === 'ALL' ? 'All' : c}</option>
              ))}
            </select>
          </div>
        }
        className="flex-1 min-h-0"
      />
    </div>
  )
}
export default GlobalNetworkCanvas
