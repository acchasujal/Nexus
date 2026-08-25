/**
 * frontend/src/components/nexus/GlobalNetworkCanvas.tsx
 *
 * Global Network Explorer canvas with entity-type layer toggles, case focus,
 * legend, selected-node neighborhood, bridge/community badges, before/after
 * delta highlighting, Louvain community ring colors, and straight color-coded edges.
 */
import { useMemo, useState } from 'react'
import {
  ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider,
  type Node, type Edge, MarkerType, EdgeLabelRenderer, BaseEdge, getStraightPath, type EdgeProps,
} from '@xyflow/react'
import {
  User, Briefcase, Phone, Landmark, Link2, BadgeCheck, Users,
} from 'lucide-react'
import type { NexusNetworkResponse, SnapshotDiffResponse } from '@shared/contracts/api'
import '@xyflow/react/dist/style.css'

interface GlobalNetworkCanvasProps {
  graph: NexusNetworkResponse
  diff?: SnapshotDiffResponse | null
  highlightDelta?: boolean
  onEdgeSelect: (edgeId: string) => void
  onNodeSelect?: (nodeId: string) => void
}

const NODE_STYLE: Record<string, { icon: typeof User; ring: string; chip: string }> = {
  Person: { icon: User, ring: 'border-sky-500', chip: 'text-sky-900 bg-sky-50 border border-sky-200' },
  Case: { icon: Briefcase, ring: 'border-rose-500', chip: 'text-rose-900 bg-rose-50 border border-rose-200' },
  Phone: { icon: Phone, ring: 'border-amber-500', chip: 'text-amber-900 bg-amber-50 border border-amber-200' },
  Account: { icon: Landmark, ring: 'border-violet-500', chip: 'text-violet-900 bg-violet-50 border border-violet-200' },
}

const COMMUNITY_COLORS: Record<string, string> = {
  'COMMUNITY-C1': 'ring-violet-500',
  'COMMUNITY-C2': 'ring-emerald-500',
  'COMMUNITY-C3': 'ring-amber-500',
  'COMMUNITY-C4': 'ring-pink-500',
}

const EDGE_COLORS: Record<string, { stroke: string; labelBg: string; text: string }> = {
  ACCUSED_IN: { stroke: '#e11d48', labelBg: '#fff1f2', text: '#9f1239' },
  CO_ACCUSED_IN: { stroke: '#f43f5e', labelBg: '#fff1f2', text: '#9f1239' },
  VICTIM_IN: { stroke: '#0284c7', labelBg: '#f0f9ff', text: '#0369a1' },
  USES_PHONE: { stroke: '#d97706', labelBg: '#fffbeb', text: '#b45309' },
  OWNS_ACCOUNT: { stroke: '#7c3aed', labelBg: '#f5f3ff', text: '#6d28d9' },
  TRANSFERRED_TO: { stroke: '#059669', labelBg: '#ecfdf5', text: '#047857' },
  COMMUNICATED_WITH: { stroke: '#ea580c', labelBg: '#fff7ed', text: '#c2410c' },
  CONNECTS_CASES: { stroke: '#2563eb', labelBg: '#eff6ff', text: '#1d4ed8' },
}

function EntityNode({ data, id }: { data: Record<string, unknown>; id: string }) {
  const cfg = NODE_STYLE[String(data.entityType)] ?? NODE_STYLE.Person
  const Icon = cfg.icon
  const badges = (data.badges as string[] | undefined) ?? []
  const isDelta = Boolean(data.isDelta)
  const isDimmed = Boolean(data.isDimmed)
  const communityBadge = badges.find((b) => b.startsWith('COMMUNITY-'))
  const communityRing = communityBadge ? COMMUNITY_COLORS[communityBadge] ?? 'ring-neutral-400' : ''
  return (
    <div
      data-testid={`node-${id}`}
      className={`relative z-20 w-[185px] rounded-xl border-2 bg-white px-3 py-2 text-center shadow-md transition-all duration-200 ${
        cfg.ring
      } ${isDelta ? 'ring-3 ring-emerald-500 ring-offset-2 ring-offset-white' : ''} ${
        communityRing && !isDelta ? `ring-2 ring-offset-1 ring-offset-white ${communityRing}` : ''
      } ${
        isDimmed ? 'opacity-25' : 'hover:shadow-lg'
      }`}
    >
      {/* Top handles */}
      <Handle type="target" position={Position.Top} id="top-left" style={{ left: '25%' }} className="!opacity-0" />
      <Handle type="target" position={Position.Top} id="top-center" style={{ left: '50%' }} className="!opacity-0" />
      <Handle type="target" position={Position.Top} id="top-right" style={{ left: '75%' }} className="!opacity-0" />

      {/* Side handles */}
      <Handle type="target" position={Position.Left} id="left" className="!opacity-0" />
      <Handle type="target" position={Position.Right} id="right" className="!opacity-0" />

      {/* Bottom handles */}
      <Handle type="target" position={Position.Bottom} id="bottom-left" style={{ left: '25%' }} className="!opacity-0" />
      <Handle type="target" position={Position.Bottom} id="bottom-center" style={{ left: '50%' }} className="!opacity-0" />
      <Handle type="target" position={Position.Bottom} id="bottom-right" style={{ left: '75%' }} className="!opacity-0" />

      <div className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${cfg.chip}`}>
        <Icon className="h-3 w-3" /> {String(data.entityType)}
      </div>
      <div className="mt-1 truncate text-xs font-bold text-neutral-900" title={String(data.label)}>
        {String(data.label)}
      </div>
      {badges.length > 0 && (
        <div className="mt-1 flex flex-wrap justify-center gap-1">
          {badges.map((b) => (
            <span
              key={b}
              className="inline-flex items-center gap-0.5 rounded bg-blue-50 border border-blue-200 px-1.5 py-px text-[8px] font-bold text-blue-800"
              title={b === 'CROSS_CASE_BRIDGE' ? 'Connects two or more case components' : `Community ${b}`}
            >
              {b === 'CROSS_CASE_BRIDGE' ? <Link2 className="h-2.5 w-2.5" /> : <Users className="h-2.5 w-2.5" />}
              {b === 'CROSS_CASE_BRIDGE' ? 'BRIDGE' : b.replace('COMMUNITY-', 'C-')}
            </span>
          ))}
        </div>
      )}
      <div className="mt-0.5 font-mono text-[8px] text-neutral-500">{id}</div>

      {/* Source handles */}
      <Handle type="source" position={Position.Top} id="s-top-left" style={{ left: '25%' }} className="!opacity-0" />
      <Handle type="source" position={Position.Top} id="s-top-center" style={{ left: '50%' }} className="!opacity-0" />
      <Handle type="source" position={Position.Top} id="s-top-right" style={{ left: '75%' }} className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} id="s-bottom-left" style={{ left: '25%' }} className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} id="s-bottom-center" style={{ left: '50%' }} className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} id="s-bottom-right" style={{ left: '75%' }} className="!opacity-0" />
      <Handle type="source" position={Position.Left} id="s-left" className="!opacity-0" />
      <Handle type="source" position={Position.Right} id="s-right" className="!opacity-0" />
    </div>
  )
}

function NexusStraightEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  style,
  markerEnd,
  data,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  })

  const label = String(data?.label ?? '')
  const colorCfg = (data?.colorCfg as { stroke: string; labelBg: string; text: string }) ?? {
    stroke: '#64748b',
    labelBg: '#f8fafc',
    text: '#334155',
  }
  const isDerived = Boolean(data?.isDerived)

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: colorCfg.stroke,
          strokeWidth: 2,
          strokeDasharray: isDerived ? '5,4' : undefined,
        }}
        markerEnd={markerEnd}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
              zIndex: 25,
              backgroundColor: colorCfg.labelBg,
              borderColor: colorCfg.stroke,
              color: colorCfg.text,
            }}
            className="select-none rounded border px-2 py-0.5 text-[9px] font-bold shadow-xs whitespace-nowrap transition-transform hover:scale-105 cursor-pointer"
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}

const nodeTypes = { nexusEntity: EntityNode }
const edgeTypes = { nexusStraight: NexusStraightEdge }

// Clean non-overlapping spatial coordinates for standard investigation snapshots
const PRESET_COORDINATES: Record<string, { x: number; y: number }> = {
  // Before snapshot — Mysuru Cluster (Left)
  'ACC-7731': { x: 60, y: 50 },
  'PH-A': { x: 300, y: 50 },
  'P-MEENA': { x: 60, y: 220 },
  'P-RAFIQ-K': { x: 300, y: 220 },
  'CASE-141': { x: 180, y: 400 },

  // Before snapshot — Bengaluru Cluster (Right)
  'PH-B': { x: 660, y: 50 },
  'ACC-9914': { x: 900, y: 50 },
  'P-RAFIQ-A': { x: 660, y: 220 },
  'P-DEEPAK': { x: 900, y: 220 },
  'CASE-207': { x: 780, y: 400 },

  // After snapshot — Unified Bridge Entities (Center)
  'PH-UNIFIED': { x: 480, y: 50 },
  'P-RAFIQ': { x: 480, y: 220 },
}

function layout(graph: NexusNetworkResponse) {
  const positions = new Map<string, { x: number; y: number }>()

  // 1. Assign known preset coordinates if present
  graph.nodes.forEach((n) => {
    if (PRESET_COORDINATES[n.id]) {
      positions.set(n.id, { ...PRESET_COORDINATES[n.id] })
    }
  })

  // 2. Generic fallback layout for dynamic or unlisted nodes
  const unplaced = graph.nodes.filter((n) => !positions.has(n.id))
  if (unplaced.length > 0) {
    unplaced.forEach((n, idx) => {
      const tier = n.entity_type === 'Case' ? 400 : n.entity_type === 'Person' ? 220 : 50
      positions.set(n.id, { x: 1100 + (idx % 3) * 230, y: tier })
    })
  }

  return positions
}

function getOptimalHandles(
  edgeType: string,
  sourcePos?: { x: number; y: number },
  targetPos?: { x: number; y: number },
) {
  if (!sourcePos || !targetPos) return { sourceHandle: 's-bottom-center', targetHandle: 'top-center' }

  if (edgeType === 'TRANSFERRED_TO') {
    return { sourceHandle: 's-left', targetHandle: 'right' }
  }
  if (edgeType === 'COMMUNICATED_WITH' || edgeType === 'CONNECTS_CASES') {
    return sourcePos.x < targetPos.x
      ? { sourceHandle: 's-right', targetHandle: 'left' }
      : { sourceHandle: 's-left', targetHandle: 'right' }
  }
  if (edgeType === 'ACCUSED_IN') {
    return sourcePos.x > targetPos.x
      ? { sourceHandle: 's-bottom-left', targetHandle: 'top-right' }
      : { sourceHandle: 's-bottom-right', targetHandle: 'top-left' }
  }
  if (edgeType === 'VICTIM_IN') {
    return { sourceHandle: 's-bottom-right', targetHandle: 'top-left' }
  }
  if (edgeType === 'CO_ACCUSED_IN') {
    return { sourceHandle: 's-bottom-left', targetHandle: 'top-right' }
  }
  if (edgeType === 'OWNS_ACCOUNT') {
    return sourcePos.x > targetPos.x
      ? { sourceHandle: 's-top-left', targetHandle: 'bottom-right' }
      : { sourceHandle: 's-top-right', targetHandle: 'bottom-left' }
  }
  if (edgeType === 'USES_PHONE') {
    return { sourceHandle: 's-top-center', targetHandle: 'bottom-center' }
  }

  const dx = targetPos.x - sourcePos.x
  const dy = targetPos.y - sourcePos.y
  if (Math.abs(dy) >= Math.abs(dx)) {
    if (dy > 0) {
      return {
        sourceHandle: dx > 40 ? 's-bottom-right' : dx < -40 ? 's-bottom-left' : 's-bottom-center',
        targetHandle: dx > 40 ? 'top-left' : dx < -40 ? 'top-right' : 'top-center',
      }
    } else {
      return {
        sourceHandle: dx > 40 ? 's-top-right' : dx < -40 ? 's-top-left' : 's-top-center',
        targetHandle: dx > 40 ? 'bottom-left' : dx < -40 ? 'bottom-right' : 'bottom-center',
      }
    }
  }
  return {
    sourceHandle: dx > 0 ? 's-right' : 's-left',
    targetHandle: dx > 0 ? 'left' : 'right',
  }
}

function CanvasInner({ graph, diff, highlightDelta, onEdgeSelect, onNodeSelect }: GlobalNetworkCanvasProps) {
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())
  const [caseFilter, setCaseFilter] = useState<string>('ALL')
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  const positions = useMemo(() => layout(graph), [graph])
  const addedNodes = useMemo(() => new Set(diff?.added_node_ids ?? []), [diff])
  const addedEdges = useMemo(() => new Set(diff?.added_edge_ids ?? []), [diff])

  const caseOptions = useMemo(() => {
    const ids = new Set<string>()
    graph.nodes.forEach((n) => n.case_ids.forEach((c) => ids.add(c)))
    return ['ALL', ...[...ids].sort()]
  }, [graph])

  const toggleType = (t: string) =>
    setHiddenTypes((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })

  const visibleNodes = useMemo(
    () => graph.nodes.filter((n) => !hiddenTypes.has(n.entity_type) && (caseFilter === 'ALL' || n.case_ids.includes(caseFilter))),
    [graph, hiddenTypes, caseFilter],
  )

  const visibleIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes])

  const neighborhood = useMemo(() => {
    if (!selectedNode) return null
    const set = new Set<string>([selectedNode])
    graph.edges.forEach((e) => {
      if (e.source_id === selectedNode) set.add(e.target_id)
      if (e.target_id === selectedNode) set.add(e.source_id)
    })
    return set
  }, [selectedNode, graph.edges])

  const flowNodes = useMemo<Node[]>(
    () => visibleNodes.map((n) => ({
      id: n.id,
      type: 'nexusEntity',
      position: positions.get(n.id) ?? { x: 0, y: 0 },
      data: {
        label: n.label,
        entityType: n.entity_type,
        badges: n.badges,
        isDelta: highlightDelta && addedNodes.has(n.id),
        isDimmed: neighborhood ? !neighborhood.has(n.id) : false,
      },
      draggable: true,
    })),
    [visibleNodes, positions, highlightDelta, addedNodes, neighborhood],
  )

  const flowEdges = useMemo<Edge[]>(
    () => graph.edges
      .filter((e) => visibleIds.has(e.source_id) && visibleIds.has(e.target_id))
      .map((e) => {
        const isAdded = highlightDelta && addedEdges.has(e.id)
        const inNeighborhood = neighborhood ? e.source_id === selectedNode || e.target_id === selectedNode : true
        const colorCfg = EDGE_COLORS[e.edge_type] ?? { stroke: '#64748b', labelBg: '#f8fafc', text: '#334155' }
        const strokeColor = isAdded ? '#059669' : inNeighborhood ? colorCfg.stroke : '#cbd5e1'

        const handles = getOptimalHandles(
          e.edge_type,
          positions.get(e.source_id),
          positions.get(e.target_id),
        )

        return {
          id: e.id,
          source: e.source_id,
          target: e.target_id,
          sourceHandle: handles.sourceHandle,
          targetHandle: handles.targetHandle,
          type: 'nexusStraight',
          data: {
            label: e.edge_type.replaceAll('_', ' '),
            colorCfg: {
              stroke: strokeColor,
              labelBg: inNeighborhood ? colorCfg.labelBg : '#f1f5f9',
              text: inNeighborhood ? colorCfg.text : '#64748b',
            },
            isDerived: e.derivation_class === 'DERIVED',
            isAnimated: isAdded || e.edge_type === 'CONNECTS_CASES' || e.edge_type === 'TRANSFERRED_TO',
          },
          animated: isAdded || e.edge_type === 'CONNECTS_CASES' || e.edge_type === 'TRANSFERRED_TO',
          markerEnd: { type: MarkerType.ArrowClosed, color: strokeColor, width: 13, height: 13 },
        }
      }),
    [graph.edges, visibleIds, highlightDelta, addedEdges, neighborhood, selectedNode, positions],
  )

  const [showLegendMobile, setShowLegendMobile] = useState(false)
  const typeOptions = [...new Set(graph.nodes.map((n) => n.entity_type))]

  return (
    <div className="relative h-[480px] sm:h-[540px] md:h-[600px] w-full overflow-hidden rounded-xl border border-neutral-200 bg-slate-50 shadow-sm">
      {/* Top Filter Bar */}
      <div className="absolute left-2 sm:left-3 top-2 sm:top-3 z-10 flex flex-wrap items-center gap-1.5 sm:gap-2 rounded-lg border border-neutral-200 bg-white/95 backdrop-blur px-2.5 sm:px-3 py-1.5 sm:py-2 text-xs shadow-md max-w-[calc(100%-16px)] sm:max-w-none">
        <span className="font-bold uppercase tracking-wider text-neutral-600 text-[10px] sm:text-xs">Layers</span>
        {typeOptions.map((t) => (
          <button
            key={t}
            onClick={() => toggleType(t)}
            aria-pressed={!hiddenTypes.has(t)}
            className={`rounded-md border px-2 sm:px-2.5 py-0.5 sm:py-1 text-[11px] sm:text-xs font-semibold transition-colors ${
              hiddenTypes.has(t)
                ? 'border-neutral-200 bg-neutral-100 text-neutral-400'
                : `${NODE_STYLE[t]?.ring ?? 'border-neutral-300'} bg-white text-neutral-900 shadow-xs`
            }`}
          >
            {t}
          </button>
        ))}
        <span className="mx-0.5 sm:mx-1 h-3 sm:h-4 w-px bg-neutral-200" />
        <label htmlFor="case-focus" className="font-bold uppercase tracking-wider text-neutral-600 text-[10px] sm:text-xs">Focus</label>
        <select
          id="case-focus"
          value={caseFilter}
          onChange={(e) => setCaseFilter(e.target.value)}
          className="rounded-md border border-neutral-300 bg-white px-2 py-0.5 sm:py-1 text-[11px] sm:text-xs text-neutral-900 focus:border-blue-500 focus:outline-none shadow-xs"
        >
          {caseOptions.map((c) => (
            <option key={c} value={c}>{c === 'ALL' ? 'All' : c}</option>
          ))}
        </select>
      </div>

      {/* Edge & Node Legend — Collapsible on mobile */}
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
            <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-sky-500" /> Person</div>
            <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-rose-500" /> Case / FIR</div>
            <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber-500" /> Phone</div>
            <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-violet-500" /> Account</div>
          </div>
          <div className="border-t border-neutral-200 pt-1 mt-1 font-bold text-neutral-800 uppercase tracking-wider text-[9px]">Relationships</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1">
            <div className="flex items-center gap-1.5"><span className="h-1 w-3 rounded bg-rose-600" /> Accused</div>
            <div className="flex items-center gap-1.5"><span className="h-1 w-3 rounded bg-emerald-600" /> Bank Wire</div>
            <div className="flex items-center gap-1.5"><span className="h-1 w-3 rounded bg-amber-600" /> CDR Phone</div>
            <div className="flex items-center gap-1.5"><span className="h-1 w-3 rounded bg-violet-600" /> Owner</div>
            <div className="flex items-center gap-1.5"><span className="h-1 w-3 rounded bg-blue-600" /> Bridge</div>
            <div className="flex items-center gap-1.5"><BadgeCheck className="h-2.5 w-2.5 text-blue-600" /> BRIDGE</div>
          </div>
        </div>
      </div>

      {highlightDelta && (
        <div className="absolute right-2 sm:right-3 top-2 sm:top-3 z-10 rounded-lg border border-emerald-200 bg-emerald-50 px-2 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-[11px] font-bold text-emerald-900 shadow-md">
          {addedNodes.size} nodes / {addedEdges.size} links unified
        </div>
      )}

      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={(_, node) => {
          setSelectedNode(node.id)
          onNodeSelect?.(node.id)
        }}
        onEdgeClick={(_, edge) => onEdgeSelect(edge.id)}
        onPaneClick={() => setSelectedNode(null)}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.3}
        className="bg-slate-50"
        aria-label={`Investigation network with ${visibleNodes.length} entities`}
      >
        <Background color="#cbd5e1" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}

export function GlobalNetworkCanvas(props: GlobalNetworkCanvasProps) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  )
}
