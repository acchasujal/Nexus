/**
 * frontend/src/components/nexus/D3NetworkGraph.tsx
 *
 * High-performance, physics-grounded D3.js Force-Directed Graph Engine.
 *
 * Features:
 * - Dynamic D3 Force Simulation (forceManyBody, forceLink, forceCollide, forceX/Y, forceCenter)
 * - Sleek circular nodes with semantic icons and clean pill labels
 * - Hidden edge labels by default — clicking any line reveals its label and relationship reason
 * - On-canvas interactive Node & Relationship Details Cards on selection
 * - Interactive Drag-and-Pin (d.fx, d.fy) to preserve investigator mental map
 * - Seamless Pan & Zoom with programmatic controls (Zoom In/Out, 100%, Fit View, Auto-Arrange)
 * - Semantic Entity Styling: Case (rose), Person (sky), Phone/CDR (amber), Account (violet), Evidence (teal), Law (indigo)
 * - Louvain Community Rings & Before/After Snapshot Delta Highlights
 * - Focus & Neighborhood Highlighting (dims unrelated entities)
 * - Temporal Timeline Scrubber (filters/animates entities & relationships across time)
 */
import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import * as d3 from 'd3'
import {
  ZoomIn, ZoomOut, Maximize2, RefreshCw,
  Sliders, Play, Pause, RotateCcw, X, Link as LinkIcon, Layers, FileText,
} from 'lucide-react'

export interface D3GraphNode extends d3.SimulationNodeDatum {
  id: string
  label?: string
  name?: string
  entity_type?: string
  type?: string
  case_ids?: string[]
  badges?: string[]
  properties?: Record<string, unknown>
  isDelta?: boolean
  timestamp?: string
  start?: string
  end?: string
  [key: string]: unknown
}

export interface D3GraphEdge extends d3.SimulationLinkDatum<D3GraphNode> {
  id: string
  source: string | D3GraphNode
  target: string | D3GraphNode
  edge_type?: string
  label?: string
  reason?: string
  derivation_class?: 'FACT' | 'DERIVED' | 'HYPOTHESIS'
  confidence?: number
  properties?: Record<string, unknown>
  provenance?: Record<string, unknown>
  timestamp?: string
  start?: string
  end?: string
  [key: string]: unknown
}

export interface D3NetworkGraphProps {
  nodes: D3GraphNode[]
  edges: D3GraphEdge[]
  selectedNodeId?: string | null
  selectedEdgeId?: string | null
  pathNodeIds?: string[] | null
  pathEdgeIds?: string[] | null
  selectedRegion?: string | null
  regionNodeIds?: Set<string> | null
  onNodeSelect?: (nodeId: string | null) => void
  onEdgeSelect?: (edgeId: string | null) => void
  onSetSource?: (nodeId: string, nodeLabel: string) => void
  onSetTarget?: (nodeId: string, nodeLabel: string) => void
  onOpenDetails?: (nodeId: string) => void
  onNodeDoubleClick?: (nodeId: string) => void
  highlightDelta?: boolean
  enableTemporalScrubber?: boolean
  height?: number | string
  className?: string
  densityMode?: 'compact' | 'normal' | 'spacious' | 'extra-spacious'
  customHeaderControls?: React.ReactNode
}

// ── Color Schemes & Styling ────────────────────────────────────────────────
const ENTITY_CONFIG: Record<string, { bg: string; stroke: string; text: string; chipBg: string; chipText: string; icon: string }> = {
  Case: { bg: '#fff1f2', stroke: '#e11d48', text: '#9f1239', chipBg: '#ffe4e6', chipText: '#be123c', icon: '📁' },
  case: { bg: '#fff1f2', stroke: '#e11d48', text: '#9f1239', chipBg: '#ffe4e6', chipText: '#be123c', icon: '📁' },
  Person: { bg: '#f0f9ff', stroke: '#0284c7', text: '#0369a1', chipBg: '#e0f2fe', chipText: '#0284c7', icon: '👤' },
  person: { bg: '#f0f9ff', stroke: '#0284c7', text: '#0369a1', chipBg: '#e0f2fe', chipText: '#0284c7', icon: '👤' },
  Phone: { bg: '#fffbeb', stroke: '#d97706', text: '#b45309', chipBg: '#fef3c7', chipText: '#d97706', icon: '📞' },
  phone: { bg: '#fffbeb', stroke: '#d97706', text: '#b45309', chipBg: '#fef3c7', chipText: '#d97706', icon: '📞' },
  Account: { bg: '#f5f3ff', stroke: '#7c3aed', text: '#6d28d9', chipBg: '#ede9fe', chipText: '#7c3aed', icon: '💳' },
  account: { bg: '#f5f3ff', stroke: '#7c3aed', text: '#6d28d9', chipBg: '#ede9fe', chipText: '#7c3aed', icon: '💳' },
  Evidence: { bg: '#f0fdfa', stroke: '#0d9488', text: '#115e59', chipBg: '#ccfbf1', chipText: '#0f766e', icon: '🔍' },
  evidence: { bg: '#f0fdfa', stroke: '#0d9488', text: '#115e59', chipBg: '#ccfbf1', chipText: '#0f766e', icon: '🔍' },
  Law: { bg: '#eef2ff', stroke: '#4f46e5', text: '#3730a3', chipBg: '#e0e7ff', chipText: '#4338ca', icon: '⚖️' },
  law: { bg: '#eef2ff', stroke: '#4f46e5', text: '#3730a3', chipBg: '#e0e7ff', chipText: '#4338ca', icon: '⚖️' },
  Section: { bg: '#eef2ff', stroke: '#4f46e5', text: '#3730a3', chipBg: '#e0e7ff', chipText: '#4338ca', icon: '⚖️' },
  section: { bg: '#eef2ff', stroke: '#4f46e5', text: '#3730a3', chipBg: '#e0e7ff', chipText: '#4338ca', icon: '⚖️' },
  Dependency: { bg: '#fff7ed', stroke: '#ea580c', text: '#c2410c', chipBg: '#ffedd5', chipText: '#ea580c', icon: '⏱️' },
  Officer: { bg: '#f8fafc', stroke: '#475569', text: '#1e293b', chipBg: '#f1f5f9', chipText: '#334155', icon: '🛡️' },
  Vehicle: { bg: '#f8fafc', stroke: '#64748b', text: '#334155', chipBg: '#f1f5f9', chipText: '#475569', icon: '🚗' },
  vehicle: { bg: '#f8fafc', stroke: '#64748b', text: '#334155', chipBg: '#f1f5f9', chipText: '#475569', icon: '🚗' },
}

// Entity type to D3 symbol type mapping
const ENTITY_SYMBOLS: Record<string, d3.SymbolType> = {
  Case: d3.symbolSquare,
  case: d3.symbolSquare,
  Person: d3.symbolCircle,
  person: d3.symbolCircle,
  Phone: d3.symbolTriangle,
  phone: d3.symbolTriangle,
  Evidence: d3.symbolCross,
  evidence: d3.symbolCross,
  Law: d3.symbolStar,
  law: d3.symbolStar,
  Section: d3.symbolStar,
  section: d3.symbolStar,
  Officer: d3.symbolWye,
  Dependency: d3.symbolWye,
  Vehicle: d3.symbolDiamond,
  vehicle: d3.symbolDiamond,
}

function getNodeSymbolPath(type: string, area: number): string {
  const raw = type.toLowerCase()
  // Account / Bank uses a distinct regular hexagon (not diamond)
  if (raw.includes('account') || raw.includes('bank')) {
    const r = Math.sqrt(area / (2 * Math.sqrt(3))) * 1.35
    const cos30 = 0.866025
    const sin30 = 0.5
    return `M 0,${-r} L ${r * cos30},${-r * sin30} L ${r * cos30},${r * sin30} L 0,${r} L ${-r * cos30},${r * sin30} L ${-r * cos30},${-r * sin30} Z`
  }

  const symType = ENTITY_SYMBOLS[type] ?? d3.symbolCircle
  return d3.symbol().type(symType).size(area)() ?? ''
}

const COMMUNITY_STROKES: Record<string, string> = {
  'COMMUNITY-C1': '#8b5cf6',
  'COMMUNITY-C2': '#10b981',
  'COMMUNITY-C3': '#f59e0b',
  'COMMUNITY-C4': '#ec4899',
}

export const EDGE_STROKES: Record<string, string> = {
  ACCUSED_IN: '#e11d48',
  CO_ACCUSED_IN: '#f43f5e',
  VICTIM_IN: '#0284c7',
  USES_PHONE: '#d97706',
  OWNS_ACCOUNT: '#7c3aed',
  TRANSFERRED_TO: '#059669',
  COMMUNICATED_WITH: '#ea580c',
  CONNECTS_CASES: '#2563eb',
  CDR_CALLS: '#d97706',
  BANK_TXN: '#059669',
  VIOLATED: '#4f46e5',
  GOVERNED: '#4f46e5',
}

export const D3NetworkGraph: React.FC<D3NetworkGraphProps> = ({
  nodes: rawNodes,
  edges: rawEdges,
  selectedNodeId,
  selectedEdgeId,
  pathNodeIds,
  pathEdgeIds,
  selectedRegion,
  regionNodeIds,
  onNodeSelect,
  onEdgeSelect,
  onSetSource,
  onSetTarget,
  onOpenDetails,
  onNodeDoubleClick,
  highlightDelta = false,
  enableTemporalScrubber = false,
  height = '100%',
  className = '',
  densityMode = 'normal',
  customHeaderControls,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const simulationRef = useRef<d3.Simulation<D3GraphNode, D3GraphEdge> | null>(null)
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const gRef = useRef<SVGGElement | null>(null)
  const nodeContainersRef = useRef<d3.Selection<SVGGElement, D3GraphNode, SVGGElement, unknown> | null>(null)
  const linkPathsRef = useRef<d3.Selection<SVGPathElement, D3GraphEdge, SVGGElement, unknown> | null>(null)
  const linkHitboxesRef = useRef<d3.Selection<SVGPathElement, D3GraphEdge, SVGGElement, unknown> | null>(null)
  const edgeBadgesRef = useRef<d3.Selection<SVGGElement, D3GraphEdge, SVGGElement, unknown> | null>(null)
  const focusRingsRef = useRef<d3.Selection<SVGPathElement, D3GraphNode, SVGGElement, unknown> | null>(null)

  // Internal selection state for immediate reactivity (controlled or uncontrolled)
  const [internalNodeId, setInternalNodeId] = useState<string | null>(null)
  const [internalEdgeId, setInternalEdgeId] = useState<string | null>(null)

  const activeNodeId = selectedNodeId !== undefined ? selectedNodeId : internalNodeId
  const activeEdgeId = selectedEdgeId !== undefined ? selectedEdgeId : internalEdgeId

  // Pathfinder active sets
  const pathNodeSet = useMemo(() => new Set(pathNodeIds ?? []), [pathNodeIds])
  const pathEdgeSet = useMemo(() => new Set(pathEdgeIds ?? []), [pathEdgeIds])
  const regionNodeSet = useMemo(() => regionNodeIds ?? new Set<string>(), [regionNodeIds])
  const isPathActive = pathNodeSet.size > 0
  const isRegionActive = Boolean(selectedRegion && selectedRegion !== 'ALL')

  const handleSelectNode = useCallback((nodeId: string | null) => {
    setInternalNodeId(nodeId)
    setInternalEdgeId(null)
    onNodeSelect?.(nodeId)
    onEdgeSelect?.(null)
  }, [onNodeSelect, onEdgeSelect])

  const handleSelectEdge = useCallback((edgeId: string | null) => {
    setInternalEdgeId(edgeId)
    setInternalNodeId(null)
    onEdgeSelect?.(edgeId)
    onNodeSelect?.(null)
  }, [onEdgeSelect, onNodeSelect])

  // Temporal Scrubber State
  const [isPlaying, setIsPlaying] = useState(false)
  const [timeIndex, setTimeIndex] = useState<number>(100)
  const [showScrubber, setShowScrubber] = useState(enableTemporalScrubber)

  const handleTogglePlay = useCallback(() => {
    if (!isPlaying) {
      if (timeIndex >= 100) {
        setTimeIndex(0)
      }
      setIsPlaying(true)
    } else {
      setIsPlaying(false)
    }
  }, [isPlaying, timeIndex])


  // Active Density Multiplier
  const densityScale = useMemo(() => {
    switch (densityMode) {
      case 'compact': return 0.8
      case 'spacious': return 1.25
      case 'extra-spacious': return 1.55
      default: return 1.0
    }
  }, [densityMode])

  // Compute parallel edge groups for curved rendering
  const parallelEdgeMeta = useMemo(() => {
    const pairGroups = new Map<string, D3GraphEdge[]>()

    rawEdges.forEach((edge) => {
      const src = typeof edge.source === 'object' ? (edge.source as D3GraphNode).id : edge.source
      const tgt = typeof edge.target === 'object' ? (edge.target as D3GraphNode).id : edge.target
      const key = [src, tgt].sort().join(':::')
      const list = pairGroups.get(key) || []
      list.push(edge)
      pairGroups.set(key, list)
    })

    const meta = new Map<string, { curvatureOffset: number; staggerT: number; totalParallel: number; index: number }>()

    pairGroups.forEach((group) => {
      const total = group.length
      group.forEach((edge, idx) => {
        const curvatureOffset = total > 1 ? (idx - (total - 1) / 2) * 36 : 0
        let staggerT = 0.5
        if (total === 2) staggerT = idx === 0 ? 0.38 : 0.62
        else if (total > 2) staggerT = 0.3 + (idx / (total - 1)) * 0.4

        meta.set(edge.id, { curvatureOffset, staggerT, totalParallel: total, index: idx })
      })
    })

    return meta
  }, [rawEdges])

  // Neighborhood map for dimming
  const neighborhood = useMemo(() => {
    if (!activeNodeId) return null
    const set = new Set<string>([activeNodeId])
    rawEdges.forEach((e) => {
      const s = typeof e.source === 'object' ? (e.source as D3GraphNode).id : e.source
      const t = typeof e.target === 'object' ? (e.target as D3GraphNode).id : e.target
      if (s === activeNodeId) set.add(t)
      if (t === activeNodeId) set.add(s)
    })
    return set
  }, [activeNodeId, rawEdges])

  // Active selected node details
  const activeSelectedNode = useMemo(() => {
    if (!activeNodeId) return null
    return rawNodes.find((n) => n.id === activeNodeId) ?? null
  }, [activeNodeId, rawNodes])

  // Active selected edge details
  const activeSelectedEdge = useMemo(() => {
    if (!activeEdgeId) return null
    return rawEdges.find((e) => e.id === activeEdgeId) ?? null
  }, [activeEdgeId, rawEdges])

  const edgeSourceNode = useMemo(() => {
    if (!activeSelectedEdge) return null
    const srcId = typeof activeSelectedEdge.source === 'object' ? (activeSelectedEdge.source as D3GraphNode).id : activeSelectedEdge.source
    return rawNodes.find((n) => n.id === srcId) ?? null
  }, [activeSelectedEdge, rawNodes])

  const edgeTargetNode = useMemo(() => {
    if (!activeSelectedEdge) return null
    const tgtId = typeof activeSelectedEdge.target === 'object' ? (activeSelectedEdge.target as D3GraphNode).id : activeSelectedEdge.target
    return rawNodes.find((n) => n.id === tgtId) ?? null
  }, [activeSelectedEdge, rawNodes])

  // Active node connections count
  const activeNodeConnections = useMemo(() => {
    if (!activeNodeId) return []
    return rawEdges.filter((e) => {
      const s = typeof e.source === 'object' ? (e.source as D3GraphNode).id : e.source
      const t = typeof e.target === 'object' ? (e.target as D3GraphNode).id : e.target
      return s === activeNodeId || t === activeNodeId
    })
  }, [activeNodeId, rawEdges])

  // Zoom & Viewport Action Helpers
  const zoomIn = useCallback(() => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current).transition().duration(250).call(zoomBehaviorRef.current.scaleBy, 1.25)
    }
  }, [])

  const zoomOut = useCallback(() => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current).transition().duration(250).call(zoomBehaviorRef.current.scaleBy, 0.8)
    }
  }, [])

  const zoom100 = useCallback(() => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current).transition().duration(250).call(zoomBehaviorRef.current.scaleTo, 1)
    }
  }, [])

  const fitView = useCallback(() => {
    if (!svgRef.current || !gRef.current || !zoomBehaviorRef.current || !containerRef.current) return
    const svg = d3.select(svgRef.current)
    const g = d3.select(gRef.current)

    const gNode = g.node() as SVGGElement
    if (!gNode || typeof gNode.getBBox !== 'function') return
    const bounds = gNode.getBBox()
    const fullWidth = containerRef.current.clientWidth || 900
    const fullHeight = containerRef.current.clientHeight || 580

    if (bounds.width === 0 || bounds.height === 0) return

    const midX = bounds.x + bounds.width / 2
    const midY = bounds.y + bounds.height / 2

    const scale = Math.min(
      Math.max(0.85 / Math.max(bounds.width / fullWidth, bounds.height / fullHeight), 0.25),
      1.4,
    )

    const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY]

    svg.transition().duration(450).call(
      zoomBehaviorRef.current.transform,
      d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale),
    )
  }, [])

  const zoomToNodeOrNeighborhood = useCallback((nodeId: string, animated = true) => {
    if (!svgRef.current || !zoomBehaviorRef.current || !containerRef.current) return
    const svg = d3.select(svgRef.current)
    const fullWidth = containerRef.current.clientWidth || 900
    const fullHeight = containerRef.current.clientHeight || 580

    // Find node and its neighbors in simulation data
    const simNodes = simulationRef.current?.nodes() || []
    const targetNode = simNodes.find((n) => n.id === nodeId)
    if (!targetNode || targetNode.x === undefined || targetNode.y === undefined) return

    // Find neighbor nodes
    const neighborIds = new Set<string>([nodeId])
    rawEdges.forEach((e) => {
      const s = typeof e.source === 'object' ? (e.source as D3GraphNode).id : e.source
      const t = typeof e.target === 'object' ? (e.target as D3GraphNode).id : e.target
      if (s === nodeId) neighborIds.add(t)
      if (t === nodeId) neighborIds.add(s)
    })

    const clusterNodes = simNodes.filter(
      (n) => neighborIds.has(n.id) && n.x !== undefined && n.y !== undefined
    )

    if (clusterNodes.length === 0) return

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
    clusterNodes.forEach((n) => {
      if (n.x! < minX) minX = n.x!
      if (n.x! > maxX) maxX = n.x!
      if (n.y! < minY) minY = n.y!
      if (n.y! > maxY) maxY = n.y!
    })

    const pad = 100
    minX -= pad
    maxX += pad
    minY -= pad
    maxY += pad

    const clusterWidth = Math.max(maxX - minX, 160)
    const clusterHeight = Math.max(maxY - minY, 160)
    const midX = (minX + maxX) / 2
    const midY = (minY + maxY) / 2

    const scale = Math.min(
      Math.max(0.85 / Math.max(clusterWidth / fullWidth, clusterHeight / fullHeight), 0.45),
      1.5,
    )

    const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY]

    if (animated) {
      svg.transition().duration(600).ease(d3.easeCubicOut).call(
        zoomBehaviorRef.current.transform,
        d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale),
      )
    } else {
      svg.call(
        zoomBehaviorRef.current.transform,
        d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale),
      )
    }
  }, [rawEdges])

  const reheatSimulation = useCallback(() => {
    if (simulationRef.current) {
      simulationRef.current.alpha(0.8).restart()
      setTimeout(() => {
        if (activeNodeId) zoomToNodeOrNeighborhood(activeNodeId)
        else fitView()
      }, 400)
    }
  }, [fitView, activeNodeId, zoomToNodeOrNeighborhood])

  // Playback timer for temporal scrubber
  useEffect(() => {
    let timer: NodeJS.Timeout
    if (isPlaying) {
      timer = setInterval(() => {
        setTimeIndex((prev) => {
          const next = prev + 2
          if (next >= 100) {
            setIsPlaying(false)
            return 100
          }
          return next
        })
      }, 250)
    }
    return () => clearInterval(timer)
  }, [isPlaying])

  const timeIndexRef = useRef(100)
  useEffect(() => { timeIndexRef.current = timeIndex }, [timeIndex])

  // Dedicated Effect: Smoothly zoom to selected node / cluster whenever activeNodeId changes
  useEffect(() => {
    if (activeNodeId && simulationRef.current) {
      const timer = setTimeout(() => {
        zoomToNodeOrNeighborhood(activeNodeId)
      }, 50)
      return () => clearTimeout(timer)
    }
    return undefined
  }, [activeNodeId, zoomToNodeOrNeighborhood])

  // Dedicated Effect: Live Selection & Highlighting (Runs instantly without tearing down simulation)
  useEffect(() => {
    if (!linkPathsRef.current || !nodeContainersRef.current) return

    // 1. Update edge paths & active highlight
    linkPathsRef.current
      .attr('stroke', (d) => {
        if (activeEdgeId === d.id) return '#e11d48'
        if (activeNodeId) {
          const src = typeof d.source === 'object' ? (d.source as D3GraphNode).id : d.source
          const tgt = typeof d.target === 'object' ? (d.target as D3GraphNode).id : d.target
          if (src === activeNodeId || tgt === activeNodeId) return '#0284c7'
        }
        const type = String(d.edge_type || d.label || '')
        return EDGE_STROKES[type] ?? '#94a3b8'
      })
      .attr('stroke-width', (d) => {
        if (activeEdgeId === d.id) return 4.0
        if (activeNodeId) {
          const src = typeof d.source === 'object' ? (d.source as D3GraphNode).id : d.source
          const tgt = typeof d.target === 'object' ? (d.target as D3GraphNode).id : d.target
          if (src === activeNodeId || tgt === activeNodeId) return 3.5
          if (neighborhood?.has(src) && neighborhood?.has(tgt)) return 2.5
        }
        return 2
      })
      .attr('opacity', (d) => {
        if (isRegionActive) {
          const src = typeof d.source === 'object' ? (d.source as D3GraphNode).id : d.source
          const tgt = typeof d.target === 'object' ? (d.target as D3GraphNode).id : d.target
          return regionNodeSet.has(src) || regionNodeSet.has(tgt) ? 1.0 : 0.12
        }
        if (!activeNodeId) return 0.85
        const src = typeof d.source === 'object' ? (d.source as D3GraphNode).id : d.source
        const tgt = typeof d.target === 'object' ? (d.target as D3GraphNode).id : d.target
        if (src === activeNodeId || tgt === activeNodeId) return 1.0
        if (neighborhood?.has(src) && neighborhood?.has(tgt)) return 0.8
        return 0.08
      })

    // 2. Update edge label badges (only visible when edge is selected)
    if (edgeBadgesRef.current) {
      edgeBadgesRef.current
        .style('display', (d) => (d.id === activeEdgeId ? 'block' : 'none'))
        .attr('opacity', (d) => (d.id === activeEdgeId ? 1.0 : 0.0))
        .select('rect')
        .attr('stroke', (d) => (activeEdgeId === d.id ? '#e11d48' : EDGE_STROKES[String(d.edge_type || d.label)] ?? '#cbd5e1'))
        .attr('stroke-width', (d) => (activeEdgeId === d.id ? 2.5 : 1))
    }

    // 3. Update focus rings & Louvain community indicators
    if (focusRingsRef.current) {
      focusRingsRef.current
        .attr('stroke', (d) => {
          if (activeNodeId === d.id) return '#0284c7'
          if (highlightDelta && d.isDelta) return '#10b981'
          const communityBadge = (d.badges || []).find((b) => b.startsWith('COMMUNITY-'))
          if (communityBadge && COMMUNITY_STROKES[communityBadge]) return COMMUNITY_STROKES[communityBadge]
          if (neighborhood?.has(d.id)) {
            const rawType = String(d.entity_type || d.type || 'Person')
            return (ENTITY_CONFIG[rawType] ?? ENTITY_CONFIG.Person).stroke
          }
          return 'none'
        })
        .attr('stroke-width', (d) => (activeNodeId === d.id || (highlightDelta && d.isDelta) ? 4.5 : neighborhood?.has(d.id) ? 3.0 : 2.0))
        .attr('opacity', (d) => {
          if (isRegionActive) return regionNodeSet.has(d.id) ? 1.0 : 0.2
          if (!activeNodeId) return 1.0
          if (activeNodeId === d.id) return 1.0
          return neighborhood?.has(d.id) ? 0.9 : 0.08
        })
    }

    // 4. Update node card elements & neighborhood dimming
    nodeContainersRef.current
      .select('path.node-circle')
      .attr('stroke-width', (d) => {
        const node = d as D3GraphNode
        if (node.id === activeNodeId) return 4.5
        if (neighborhood?.has(node.id)) return 3.0
        return 2
      })
      .attr('opacity', (d) => {
        const node = d as D3GraphNode
        if (isRegionActive) return regionNodeSet.has(node.id) ? 1.0 : 0.2
        if (!activeNodeId) return 1.0
        if (node.id === activeNodeId) return 1.0
        return neighborhood?.has(node.id) ? 1.0 : 0.12
      })
      .attr('filter', (d) => {
        const node = d as D3GraphNode
        if (node.id === activeNodeId) return 'drop-shadow(0 0 14px rgba(2,132,199,0.85))'
        if (neighborhood?.has(node.id)) return 'drop-shadow(0 2px 8px rgba(0,0,0,0.18))'
        return 'none'
      })

    nodeContainersRef.current
      .select('text')
      .attr('opacity', (d) => {
        const node = d as D3GraphNode
        if (isRegionActive) return regionNodeSet.has(node.id) ? 1.0 : 0.2
        if (!activeNodeId) return 1.0
        if (node.id === activeNodeId) return 1.0
        return neighborhood?.has(node.id) ? 1.0 : 0.15
      })

    nodeContainersRef.current
      .select('.node-label-group')
      .attr('opacity', (d) => {
        const node = d as D3GraphNode
        if (isRegionActive) return regionNodeSet.has(node.id) ? 1.0 : 0.2
        if (!activeNodeId) return 1.0
        if (node.id === activeNodeId) return 1.0
        return neighborhood?.has(node.id) ? 1.0 : 0.12
      })

  }, [activeNodeId, activeEdgeId, neighborhood, highlightDelta, isRegionActive, regionNodeSet])

  // Dedicated Effect: Live Timeline Scrubber Filtering
  useEffect(() => {
    if (!nodeContainersRef.current || !linkPathsRef.current) return

    // Extract all valid timestamps from nodes and edges
    const allTimestamps: number[] = []
    rawNodes.forEach((n) => {
      const ts = n.timestamp || n.start || (n.properties?.occurred_at as string) || (n.properties?.recorded_at as string) || (n.properties?.timestamp as string)
      if (ts) { const t = new Date(ts).getTime(); if (!isNaN(t)) allTimestamps.push(t) }
    })
    rawEdges.forEach((e) => {
      const ts = e.timestamp || e.start || (e.properties?.recorded_at as string) || (e.properties?.occurred_at as string) || (e.properties?.timestamp as string)
      if (ts) { const t = new Date(ts).getTime(); if (!isNaN(t)) allTimestamps.push(t) }
    })

    if (timeIndex >= 100) {
      nodeContainersRef.current.style('display', 'block')
      linkPathsRef.current.style('display', 'block')
      if (linkHitboxesRef.current) linkHitboxesRef.current.style('display', 'block')
      return
    }

    if (allTimestamps.length > 0) {
      const minTime = Math.min(...allTimestamps)
      const maxTime = Math.max(...allTimestamps)
      const cutoffTime = minTime + (maxTime - minTime) * (timeIndex / 100)

      const activeNodeIds = new Set<string>()
      nodeContainersRef.current.style('display', (d) => {
        const ts = d.timestamp || d.start || (d.properties?.occurred_at as string) || (d.properties?.recorded_at as string) || (d.properties?.timestamp as string)
        if (!ts) {
          activeNodeIds.add(d.id)
          return 'block'
        }
        const t = new Date(ts).getTime()
        const visible = isNaN(t) || t <= cutoffTime
        if (visible) activeNodeIds.add(d.id)
        return visible ? 'block' : 'none'
      })

      linkPathsRef.current.style('display', (d) => {
        const src = typeof d.source === 'object' ? (d.source as D3GraphNode).id : d.source
        const tgt = typeof d.target === 'object' ? (d.target as D3GraphNode).id : d.target
        if (!activeNodeIds.has(src) || !activeNodeIds.has(tgt)) return 'none'

        const ts = (d as D3GraphEdge).timestamp || (d as D3GraphEdge).start || ((d as D3GraphEdge).properties?.recorded_at as string)
        if (!ts) return 'block'
        const t = new Date(ts as string).getTime()
        return (!isNaN(t) && t > cutoffTime) ? 'none' : 'block'
      })

      if (linkHitboxesRef.current) {
        linkHitboxesRef.current.style('display', (d) => {
          const src = typeof d.source === 'object' ? (d.source as D3GraphNode).id : d.source
          const tgt = typeof d.target === 'object' ? (d.target as D3GraphNode).id : d.target
          return (activeNodeIds.has(src) && activeNodeIds.has(tgt)) ? 'block' : 'none'
        })
      }
    } else {
      // Sequence-based filtering (fallback when no timestamps exist)
      const totalNodes = rawNodes.length
      const cutoffIndex = Math.max(1, Math.ceil(totalNodes * (timeIndex / 100)))
      const activeNodeIds = new Set<string>()

      nodeContainersRef.current.style('display', (d, idx) => {
        const isCase = String(d.entity_type || d.type || '').toLowerCase().includes('case')
        const visible = isCase || idx < cutoffIndex
        if (visible) activeNodeIds.add(d.id)
        return visible ? 'block' : 'none'
      })

      linkPathsRef.current.style('display', (d) => {
        const src = typeof d.source === 'object' ? (d.source as D3GraphNode).id : d.source
        const tgt = typeof d.target === 'object' ? (d.target as D3GraphNode).id : d.target
        return (activeNodeIds.has(src) && activeNodeIds.has(tgt)) ? 'block' : 'none'
      })

      if (linkHitboxesRef.current) {
        linkHitboxesRef.current.style('display', (d) => {
          const src = typeof d.source === 'object' ? (d.source as D3GraphNode).id : d.source
          const tgt = typeof d.target === 'object' ? (d.target as D3GraphNode).id : d.target
          return (activeNodeIds.has(src) && activeNodeIds.has(tgt)) ? 'block' : 'none'
        })
      }
    }
  }, [timeIndex, rawNodes, rawEdges])

  // Initialize and update D3 Force Simulation (Only runs on data/density changes)
  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return

    const width = containerRef.current.clientWidth || 900
    const heightPx = containerRef.current.clientHeight || 580

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove() // Clean canvas

    // Setup zoom container
    const g = svg.append('g').attr('class', 'nexus-d3-canvas')
    gRef.current = g.node()

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.15, 3.5])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })

    zoomBehaviorRef.current = zoom
    svg.call(zoom).on('dblclick.zoom', null)

    // Markers for edge arrows
    const defs = svg.append('defs')
    const markerTypes = ['default', 'ACCUSED_IN', 'CO_ACCUSED_IN', 'VICTIM_IN', 'USES_PHONE', 'OWNS_ACCOUNT', 'TRANSFERRED_TO', 'COMMUNICATED_WITH', 'CONNECTS_CASES']
    
    markerTypes.forEach((type) => {
      const stroke = EDGE_STROKES[type] ?? '#94a3b8'
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 30)
        .attr('refY', 0)
        .attr('markerWidth', 6.5)
        .attr('markerHeight', 6.5)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', stroke)
    })

    // Clone data to preserve simulation state across updates
    const simNodes: D3GraphNode[] = rawNodes.map((d) => ({ ...d }))
    const nodeMap = new Map(simNodes.map((d) => [d.id, d]))

    const simEdges: D3GraphEdge[] = rawEdges
      .map((d) => {
        const s = typeof d.source === 'object' ? (d.source as D3GraphNode).id : d.source
        const t = typeof d.target === 'object' ? (d.target as D3GraphNode).id : d.target
        return {
          ...d,
          source: nodeMap.get(s) ?? s,
          target: nodeMap.get(t) ?? t,
        }
      })
      .filter((d) => typeof d.source === 'object' && typeof d.target === 'object')

    // Degree map for visual emphasis of well-connected nodes
    const degreeMap = new Map<string, number>()
    simEdges.forEach((e) => {
      const s = (e.source as D3GraphNode).id
      const t = (e.target as D3GraphNode).id
      degreeMap.set(s, (degreeMap.get(s) || 0) + 1)
      degreeMap.set(t, (degreeMap.get(t) || 0) + 1)
    })
    const maxDegree = Math.max(...Array.from(degreeMap.values()), 1)

    // Create D3 Force Simulation
    const simulation = d3.forceSimulation<D3GraphNode>(simNodes)
      .force(
        'link',
        d3.forceLink<D3GraphNode, D3GraphEdge>(simEdges)
          .id((d) => d.id)
          .distance((d) => {
            const edgeType = String(d.edge_type || d.label || '')
            if (edgeType.includes('ACCUSED') || edgeType.includes('VICTIM')) return 145 * densityScale
            if (edgeType.includes('PHONE') || edgeType.includes('ACCOUNT')) return 120 * densityScale
            return 130 * densityScale
          })
          .strength(0.7),
      )
      .force(
        'charge',
        d3.forceManyBody().strength((d) => {
          const typeStr = String((d as D3GraphNode).entity_type || (d as D3GraphNode).type || '').toLowerCase()
          if (typeStr.includes('case')) return -650 * densityScale
          return -320 * densityScale
        }),
      )
      .force('collide', d3.forceCollide().radius(50 * densityScale).iterations(3))
      .force('x', d3.forceX(width / 2).strength(0.06))
      .force('y', d3.forceY(heightPx / 2).strength(0.06))
      .force('center', d3.forceCenter(width / 2, heightPx / 2))

    simulationRef.current = simulation

    // Link Group
    const linkGroup = g.append('g').attr('class', 'links')

    // Hitbox Layer (Thick transparent clickable path for effortless clicking)
    const linkHitboxes = linkGroup.selectAll<SVGPathElement, D3GraphEdge>('path.edge-hitbox')
      .data(simEdges, (d) => d.id)
      .join('path')
      .attr('class', 'edge-hitbox cursor-pointer')
      .attr('fill', 'none')
      .attr('stroke', 'transparent')
      .attr('stroke-width', 28)
      .style('pointer-events', 'stroke')
      .on('click', (event, d) => {
        event.stopPropagation()
        handleSelectEdge(d.id)
      })

    linkHitboxesRef.current = linkHitboxes

    // Visible Edge Line
    const linkPaths = linkGroup.selectAll<SVGPathElement, D3GraphEdge>('path.edge-line')
      .data(simEdges, (d) => d.id)
      .join('path')
      .attr('class', 'edge-line cursor-pointer')
      .attr('fill', 'none')
      .attr('stroke', (d) => {
        if (isPathActive && pathEdgeSet.has(d.id)) return '#2563eb'
        if (activeEdgeId === d.id) return '#e11d48'
        const type = String(d.edge_type || d.label || '')
        return EDGE_STROKES[type] ?? '#94a3b8'
      })
      .attr('stroke-width', (d) => {
        if (isPathActive && pathEdgeSet.has(d.id)) return 3.5
        return activeEdgeId === d.id ? 3.5 : 2
      })
      .attr('stroke-dasharray', (d) => (d.derivation_class === 'DERIVED' || String(d.label).includes('DEPENDENCY') ? '5,4' : null))
      .attr('opacity', (d) => {
        if (isRegionActive) {
          const src = (d.source as D3GraphNode).id
          const tgt = (d.target as D3GraphNode).id
          return regionNodeSet.has(src) || regionNodeSet.has(tgt) ? 1.0 : 0.12
        }
        if (isPathActive) {
          return pathEdgeSet.has(d.id) ? 1.0 : 0.12
        }
        if (!activeNodeId) return 0.85
        const src = (d.source as D3GraphNode).id
        const tgt = (d.target as D3GraphNode).id
        return (src === activeNodeId || tgt === activeNodeId) ? 1.0 : 0.15
      })
      .attr('marker-end', (d) => {
        const type = String(d.edge_type || d.label || '')
        return `url(#arrow-${type in EDGE_STROKES ? type : 'default'})`
      })
      .on('mouseenter', function(_event, d) {
        if (d.id !== activeEdgeId) {
          d3.select(this).attr('stroke-width', 3).attr('stroke-opacity', 1)
        }
      })
      .on('mouseleave', function(_event, d) {
        if (d.id !== activeEdgeId) {
          d3.select(this).attr('stroke-width', 2).attr('stroke-opacity', 0.85)
        }
      })
      .on('click', (event, d) => {
        event.stopPropagation()
        handleSelectEdge(d.id)
      })

    linkPathsRef.current = linkPaths

    // Edge Label Group (SHOWN ON CLICKED LINE OR ON ACTIVE PATH)
    const edgeLabelGroup = g.append('g').attr('class', 'edge-labels')
    const edgeLabels = edgeLabelGroup.selectAll<SVGGElement, D3GraphEdge>('g.edge-badge')
      .data(simEdges, (d) => d.id)
      .join('g')
      .attr('class', 'edge-badge cursor-pointer select-none')
      .style('display', (d) => (d.id === activeEdgeId || (isPathActive && pathEdgeSet.has(d.id)) ? 'block' : 'none'))
      .attr('opacity', (d) => (d.id === activeEdgeId || (isPathActive && pathEdgeSet.has(d.id)) ? 1.0 : 0.0))
      .on('click', (event, d) => {
        event.stopPropagation()
        handleSelectEdge(d.id)
      })

    edgeBadgesRef.current = edgeLabels

    // Edge Badge Background Capsule
    edgeLabels.append('rect')
      .attr('rx', 10)
      .attr('ry', 10)
      .attr('fill', '#ffffff')
      .attr('stroke', (d) => {
        if (isPathActive && pathEdgeSet.has(d.id)) return '#2563eb'
        if (activeEdgeId === d.id) return '#e11d48'
        return EDGE_STROKES[String(d.edge_type || d.label)] ?? '#cbd5e1'
      })
      .attr('stroke-width', (d) => (activeEdgeId === d.id || (isPathActive && pathEdgeSet.has(d.id)) ? 2.5 : 1))
      .attr('filter', 'drop-shadow(0 2px 4px rgba(0,0,0,0.15))')
      .attr('filter', 'drop-shadow(0 2px 4px rgba(0,0,0,0.15))')

    // Edge Badge Text
    edgeLabels.append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', '8.5px')
      .attr('font-weight', '800')
      .attr('fill', '#0f172a')
      .text((d) => String(d.label || d.edge_type || '').replaceAll('_', ' '))

    // Measure and resize badge rects
    edgeLabels.each(function() {
      const textElem = d3.select(this).select('text').node() as SVGTextElement
      if (textElem && typeof textElem.getBBox === 'function') {
        const bbox = textElem.getBBox()
        const paddingX = 14
        const paddingY = 7
        d3.select(this).select('rect')
          .attr('x', bbox.x - paddingX / 2)
          .attr('y', bbox.y - paddingY / 2)
          .attr('width', Math.max(bbox.width + paddingX, 38))
          .attr('height', bbox.height + paddingY)
      } else if (textElem) {
        const textLen = (textElem.textContent || '').length
        const approxWidth = Math.max(textLen * 7 + 14, 38)
        d3.select(this).select('rect')
          .attr('x', -approxWidth / 2)
          .attr('y', -10)
          .attr('width', approxWidth)
          .attr('height', 20)
      }
    })

    // Drag behavior with Pinning
    const dragBehavior = d3.drag<SVGGElement, D3GraphNode>()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event) => {
        if (!event.active) simulation.alphaTarget(0)
      })

    // Node Group (Shape Nodes)
    const nodeGroup = g.append('g').attr('class', 'nodes')
    const nodeContainers = nodeGroup.selectAll<SVGGElement, D3GraphNode>('g.node-card')
      .data(simNodes, (d) => d.id)
      .join('g')
      .attr('class', 'node-card cursor-pointer select-none')
      .style('pointer-events', 'all')
      .call(dragBehavior)
      .on('click', (event, d) => {
        event.stopPropagation()
        handleSelectNode(d.id)
      })
      .on('dblclick', (event, d) => {
        event.stopPropagation()
        onNodeDoubleClick?.(d.id)
        d.fx = null
        d.fy = null
        simulation.alpha(0.3).restart()
      })

    nodeContainersRef.current = nodeContainers

    // 1. Outer Focus & Louvain Community Ring
    const focusRings = nodeContainers.append('path')
      .attr('class', 'focus-ring')
      .attr('d', (d) => {
        const rawType = String(d.entity_type || d.type || 'Person')
        const isCase = rawType.toLowerCase().includes('case')
        const degree = degreeMap.get(d.id) || 0
        const degreeScale = 1 + (degree / maxDegree) * 0.6
        const baseArea = isCase ? Math.PI * 31 * 31 : Math.PI * 27 * 27
        return getNodeSymbolPath(rawType, baseArea * degreeScale)
      })
      .attr('fill', 'none')
      .attr('stroke', (d) => {
        if (isPathActive && pathNodeSet.has(d.id)) return '#2563eb'
        if (activeNodeId === d.id) return '#0284c7'
        if (highlightDelta && d.isDelta) return '#10b981'
        const communityBadge = (d.badges || []).find((b) => b.startsWith('COMMUNITY-'))
        if (communityBadge && COMMUNITY_STROKES[communityBadge]) return COMMUNITY_STROKES[communityBadge]
        return 'none'
      })
      .attr('stroke-width', (d) => {
        if (isPathActive && pathNodeSet.has(d.id)) return 4
        return activeNodeId === d.id || (highlightDelta && d.isDelta) ? 3.5 : 2.5
      })
      .attr('stroke-dasharray', (d) => (highlightDelta && d.isDelta ? '4,3' : null))
      .attr('opacity', (d) => {
        if (isPathActive) {
          return pathNodeSet.has(d.id) ? 1.0 : 0.15
        }
        if (!activeNodeId) return 1.0
        return neighborhood?.has(d.id) ? 1.0 : 0.2
      })

    focusRingsRef.current = focusRings

    // 2. Inner Shape Body
    nodeContainers.append('path')
      .attr('class', 'node-circle')
      .attr('d', (d) => {
        const rawType = String(d.entity_type || d.type || 'Person')
        const isCase = rawType.toLowerCase().includes('case')
        const degree = degreeMap.get(d.id) || 0
        const degreeScale = 1 + (degree / maxDegree) * 0.6
        const baseArea = isCase ? Math.PI * 25 * 25 : Math.PI * 21 * 21
        return getNodeSymbolPath(rawType, baseArea * degreeScale)
      })
      .attr('fill', (d) => {
        const rawType = String(d.entity_type || d.type || 'Person')
        const cfg = ENTITY_CONFIG[rawType] ?? ENTITY_CONFIG.Person
        const degree = degreeMap.get(d.id) || 0
        const intensity = degree / maxDegree
        return String(d3.interpolate(cfg.bg, cfg.stroke)(Math.min(intensity * 0.6, 0.6)))
      })
      .attr('stroke', (d) => {
        if (isPathActive && pathNodeSet.has(d.id)) return '#2563eb'
        const rawType = String(d.entity_type || d.type || 'Person')
        const cfg = ENTITY_CONFIG[rawType] ?? ENTITY_CONFIG.Person
        return cfg.stroke
      })
      .attr('stroke-width', (d) => {
        if (isPathActive && pathNodeSet.has(d.id)) return 3.5
        return activeNodeId === d.id ? 3 : 2
      })
      .attr('filter', (d) => (isPathActive && pathNodeSet.has(d.id) ? 'drop-shadow(0 0 8px rgba(37,99,235,0.7))' : 'drop-shadow(0 2px 5px rgba(0,0,0,0.12))'))
      .attr('opacity', (d) => {
        if (isRegionActive) return regionNodeSet.has(d.id) ? 1.0 : 0.2
        if (isPathActive) {
          return pathNodeSet.has(d.id) ? 1.0 : 0.18
        }
        if (!activeNodeId) return 1.0
        return neighborhood?.has(d.id) ? 1.0 : 0.22
      })

    // 3. Center Icon
    nodeContainers.append('text')
      .attr('x', 0)
      .attr('y', 0)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('font-size', (d) => {
        const isCase = String(d.entity_type || d.type || '').toLowerCase().includes('case')
        return isCase ? '15px' : '13px'
      })
      .attr('opacity', (d) => {
        if (isPathActive) return pathNodeSet.has(d.id) ? 1.0 : 0.2
        return !activeNodeId || neighborhood?.has(d.id) ? 1.0 : 0.25
      })
      .text((d) => {
        const rawType = String(d.entity_type || d.type || 'Person')
        return (ENTITY_CONFIG[rawType] ?? ENTITY_CONFIG.Person).icon
      })

    // 4. Badge Dot (Top-Right of Circle)
    nodeContainers.filter((d) => Boolean((highlightDelta && d.isDelta) || (d.badges && d.badges.length > 0)))
      .append('circle')
      .attr('cx', 16)
      .attr('cy', -16)
      .attr('r', 6)
      .attr('fill', (d) => (highlightDelta && d.isDelta ? '#10b981' : '#3b82f6'))
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 1.5)

    // 5. Node Label (Positioned cleanly below circle)
    const labelGroup = nodeContainers.append('g')
      .attr('class', 'node-label-group')
      .attr('opacity', (d) => {
        if (isPathActive) return pathNodeSet.has(d.id) ? 1.0 : 0.2
        return !activeNodeId || neighborhood?.has(d.id) ? 1.0 : 0.25
      })

    // Background pill for text
    labelGroup.append('rect')
      .attr('class', 'node-label-bg')
      .attr('rx', 6)
      .attr('ry', 6)
      .attr('fill', '#ffffff')
      .attr('stroke', '#e2e8f0')
      .attr('stroke-width', 1)
      .attr('filter', 'drop-shadow(0 1px 2px rgba(0,0,0,0.06))')

    // Label Text
    labelGroup.append('text')
      .attr('class', 'node-label-text')
      .attr('x', 0)
      .attr('y', 33)
      .attr('text-anchor', 'middle')
      .attr('font-size', '9px')
      .attr('font-weight', '700')
      .attr('fill', '#0f172a')
      .text((d) => {
        const fullLabel = String(d.label || d.name || d.id)
        return fullLabel.length > 18 ? `${fullLabel.slice(0, 17)}…` : fullLabel
      })

    // Resize label pill rect to fit text
    labelGroup.each(function() {
      const textNode = d3.select(this).select('text').node() as SVGTextElement
      if (textNode && typeof textNode.getBBox === 'function') {
        const bbox = textNode.getBBox()
        const paddingX = 10
        const paddingY = 5
        d3.select(this).select('rect')
          .attr('x', bbox.x - paddingX / 2)
          .attr('y', bbox.y - paddingY / 2)
          .attr('width', Math.max(bbox.width + paddingX, 30))
          .attr('height', bbox.height + paddingY)
      } else if (textNode) {
        const textLen = (textNode.textContent || '').length
        const approxWidth = Math.max(textLen * 6 + 10, 30)
        d3.select(this).select('rect')
          .attr('x', -approxWidth / 2)
          .attr('y', 23)
          .attr('width', approxWidth)
          .attr('height', 16)
      }
    })

    // Simulation Tick Update (Physics Step)
    simulation.on('tick', () => {
      // 1. Update curved link paths and hitboxes
      const updateLinkD = (d: D3GraphEdge) => {
        const source = d.source as D3GraphNode
        const target = d.target as D3GraphNode
        if (source.x === undefined || source.y === undefined || target.x === undefined || target.y === undefined) return ''

        const meta = parallelEdgeMeta.get(d.id)
        const offset = meta?.curvatureOffset ?? 0

        if (offset === 0) {
          return `M ${source.x} ${source.y} L ${target.x} ${target.y}`
        }

        const dx = target.x - source.x
        const dy = target.y - source.y
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
        const nx = -dy / dist
        const ny = dx / dist

        const midX = (source.x + target.x) / 2 + nx * offset
        const midY = (source.y + target.y) / 2 + ny * offset

        return `M ${source.x} ${source.y} Q ${midX} ${midY} ${target.x} ${target.y}`
      }

      linkPaths.attr('d', updateLinkD)
      linkHitboxes.attr('d', updateLinkD)

      // 2. Update edge label badges (ONLY VISIBLE ON CLICKED / SELECTED LINE)
      edgeLabels
        .style('display', (d) => (d.id === activeEdgeId ? 'block' : 'none'))
        .attr('opacity', (d) => (d.id === activeEdgeId ? 1.0 : 0.0))
        .attr('transform', (d) => {
          const source = d.source as D3GraphNode
          const target = d.target as D3GraphNode
          if (source.x === undefined || source.y === undefined || target.x === undefined || target.y === undefined) return ''

          const meta = parallelEdgeMeta.get(d.id)
          const offset = meta?.curvatureOffset ?? 0
          const t = meta?.staggerT ?? 0.5

          if (offset === 0) {
            const lx = source.x + (target.x - source.x) * t
            const ly = source.y + (target.y - source.y) * t
            return `translate(${lx}, ${ly})`
          }

          const dx = target.x - source.x
          const dy = target.y - source.y
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
          const nx = -dy / dist
          const ny = dx / dist

          const midX = (source.x + target.x) / 2 + nx * offset
          const midY = (source.y + target.y) / 2 + ny * offset

          // Point along quadratic bezier at t
          const u = 1 - t
          const qx = u * u * source.x + 2 * u * t * midX + t * t * target.x
          const qy = u * u * source.y + 2 * u * t * midY + t * t * target.y

          return `translate(${qx}, ${qy})`
        })

      // 3. Update node positions
      nodeContainers.attr('transform', (d) => `translate(${d.x ?? 0}, ${d.y ?? 0})`)
    })

    // Auto-fit view or zoom to active node after initial stabilization
    const timer = setTimeout(() => {
      if (simNodes.length > 0 && svgRef.current && zoomBehaviorRef.current) {
        if (activeNodeId && simNodes.some((n) => n.id === activeNodeId)) {
          zoomToNodeOrNeighborhood(activeNodeId)
        } else {
          fitView()
        }
      }
    }, 450)

    return () => {
      clearTimeout(timer)
      simulation.stop()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- activeNodeId/activeEdgeId/highlightDelta/neighborhood are intentionally omitted; handled by the dedicated selection useEffect above to avoid full canvas teardown
  }, [rawNodes, rawEdges, parallelEdgeMeta, densityScale, fitView, handleSelectEdge, handleSelectNode, onNodeDoubleClick, zoomToNodeOrNeighborhood])

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full min-h-[450px] overflow-hidden bg-slate-50 border border-neutral-200 rounded-radius-md ${className}`}
      style={{ height }}
    >
      {/* Floating Focus & Neighborhood Indicator Pill */}
      {activeSelectedNode && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 bg-neutral-900/90 text-white backdrop-blur-md px-3.5 py-1.5 rounded-full shadow-lg border border-neutral-700 text-xs animate-in fade-in duration-200">
          <span className="flex h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
          <span className="font-semibold text-neutral-100 truncate max-w-[200px] sm:max-w-[280px]">
            Focused: <strong className="text-white font-bold">{activeSelectedNode.label || activeSelectedNode.name || activeSelectedNode.id}</strong> ({activeSelectedNode.entity_type || 'Entity'})
          </span>
          <span className="text-neutral-400">·</span>
          <span className="text-sky-300 font-medium whitespace-nowrap">{neighborhood ? neighborhood.size : 1} connected</span>
          <div className="flex items-center gap-1 ml-1 pl-2 border-l border-neutral-700">
            <button
              onClick={() => zoomToNodeOrNeighborhood(activeSelectedNode.id)}
              className="text-[11px] font-bold text-sky-400 hover:text-sky-300 px-1.5 py-0.5 rounded hover:bg-neutral-800 transition-colors cursor-pointer"
              title="Center and zoom on this cluster"
            >
              Zoom
            </button>
            <button
              onClick={() => {
                handleSelectNode(null)
                fitView()
              }}
              className="text-[11px] font-bold text-neutral-400 hover:text-white px-1 py-0.5 rounded hover:bg-neutral-800 transition-colors cursor-pointer"
              title="Clear focus (Show full network)"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Interactive Controls Overlay */}
      <div className="absolute top-3 left-3 z-20 flex flex-wrap items-center gap-1 bg-white/95 backdrop-blur-sm p-1 rounded-radius-md border border-neutral-200 shadow-sm">
        <button
          onClick={zoomIn}
          className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="h-4 w-4" />
        </button>
        <button
          onClick={zoomOut}
          className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="h-4 w-4" />
        </button>
        <button
          onClick={zoom100}
          className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 font-mono text-[11px] font-bold focus:outline-none transition-colors"
          title="100% Zoom"
        >
          100%
        </button>
        <button
          onClick={fitView}
          className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none transition-colors"
          title="Fit Canvas"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
        <button
          onClick={reheatSimulation}
          className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none transition-colors"
          title="Re-balance / Auto-Organize Layout"
        >
          <RefreshCw className="h-4 w-4" />
        </button>

        {enableTemporalScrubber && (
          <>
            <div className="w-px bg-neutral-200 mx-1 h-4" />
            <button
              onClick={() => setShowScrubber((prev) => !prev)}
              className={`p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none flex items-center gap-1 text-[11px] font-semibold transition-colors ${
                showScrubber ? 'text-blue-700 bg-blue-50/90 font-bold' : ''
              }`}
              title="Toggle Investigative Timeline Scrubber"
            >
              <Sliders className="h-3.5 w-3.5" />
              <span>Timeline Scrubber</span>
            </button>
          </>
        )}

        {customHeaderControls && (
          <>
            <div className="w-px bg-neutral-200 mx-1 h-4" />
            {customHeaderControls}
          </>
        )}
      </div>

      {/* Floating Node Details Card on Canvas */}
      {activeSelectedNode && (
        <div className="absolute top-14 sm:top-16 right-2 sm:right-3 z-30 w-72 max-w-[calc(100%-16px)] max-h-[calc(100%-68px)] overflow-y-auto max-sm:top-auto max-sm:bottom-3 max-sm:left-3 max-sm:right-3 max-sm:w-auto max-sm:max-h-[45vh] bg-white/95 backdrop-blur-md p-4 rounded-xl border border-neutral-200 shadow-xl animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-start justify-between border-b border-neutral-100 pb-2.5">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-sm shadow-xs">
                {(ENTITY_CONFIG[String(activeSelectedNode.entity_type || activeSelectedNode.type || 'Person')] ?? ENTITY_CONFIG.Person).icon}
              </div>
              <div>
                <span className="text-[9px] font-extrabold uppercase tracking-wider text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">
                  {String(activeSelectedNode.entity_type || activeSelectedNode.type || 'Entity')}
                </span>
                <h4 className="text-sm font-bold text-neutral-900 leading-snug mt-0.5" title={activeSelectedNode.label || activeSelectedNode.id}>
                  {activeSelectedNode.label || activeSelectedNode.id}
                </h4>
              </div>
            </div>
            <button
              onClick={() => handleSelectNode(null)}
              className="text-neutral-400 hover:text-neutral-700 p-1 rounded-md hover:bg-neutral-100 transition-colors"
              title="Close Detail Card"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="mt-3 space-y-2.5 text-xs text-neutral-700">
            <div className="flex justify-between items-center bg-neutral-50 px-2.5 py-1.5 rounded-lg border border-neutral-100">
              <span className="text-neutral-500 font-medium">Identifier</span>
              <code className="font-mono text-[10px] text-neutral-800 font-bold">{activeSelectedNode.id}</code>
            </div>

            <div className="flex justify-between items-center bg-neutral-50 px-2.5 py-1.5 rounded-lg border border-neutral-100">
              <span className="text-neutral-500 font-medium flex items-center gap-1">
                <LinkIcon className="h-3 w-3 text-blue-600" /> Connections
              </span>
              <span className="font-bold text-blue-800">{activeNodeConnections.length} Relationships</span>
            </div>

            {/* Dynamic Attributes */}
            {activeSelectedNode.properties && Object.keys(activeSelectedNode.properties).length > 0 && (
              <div className="space-y-1 pt-1">
                <div className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1">
                  <Layers className="h-3 w-3" /> Attributes
                </div>
                <div className="bg-neutral-50 p-2 rounded-lg border border-neutral-100 max-h-36 overflow-y-auto space-y-1 text-[11px]">
                  {Object.entries(activeSelectedNode.properties)
                    .filter(([k]) => !['evidence_ids', 'isDimmed', 'isDelta'].includes(k))
                    .map(([key, val]) => {
                      let formattedValue = ''
                      if (val !== null && val !== undefined) {
                        if (Array.isArray(val)) {
                          formattedValue = val.map(String).join(', ')
                        } else if (typeof val === 'object') {
                          try { formattedValue = JSON.stringify(val) } catch { formattedValue = '[Object]' }
                        } else {
                          formattedValue = String(val)
                        }
                      }
                      
                      return (
                        <div key={key} className="flex justify-between gap-2 border-b border-neutral-100/60 pb-0.5 last:border-none">
                          <span className="text-neutral-500 capitalize">{key.replaceAll('_', ' ')}:</span>
                          <span className="font-semibold text-neutral-900 truncate max-w-[140px]" title={formattedValue}>{formattedValue}</span>
                        </div>
                      )
                    })}
                </div>
              </div>
            )}

            {/* Quick Pathfinder Actions */}
            {(onSetSource || onSetTarget) && (
              <div className="pt-2 border-t border-neutral-100 flex gap-2">
                {onOpenDetails && (
                  <button
                    onClick={() => onOpenDetails(activeSelectedNode.id)}
                    className="flex-1 rounded-lg bg-emerald-50 border border-emerald-200 px-2 py-1.5 text-[10px] font-bold text-emerald-700 hover:bg-emerald-100 transition-colors shadow-2xs"
                    title="View full intelligence record"
                  >
                    📖 Full Record
                  </button>
                )}
                {onSetSource && (
                  <button
                    onClick={() => onSetSource(activeSelectedNode.id, String(activeSelectedNode.label || activeSelectedNode.id))}
                    className="flex-1 rounded-lg bg-blue-50 border border-blue-200 px-2 py-1.5 text-[10px] font-bold text-blue-700 hover:bg-blue-100 transition-colors shadow-2xs"
                  >
                    📍 Source
                  </button>
                )}
                {onSetTarget && (
                  <button
                    onClick={() => onSetTarget(activeSelectedNode.id, String(activeSelectedNode.label || activeSelectedNode.id))}
                    className="flex-1 rounded-lg bg-rose-50 border border-rose-200 px-2 py-1.5 text-[10px] font-bold text-rose-700 hover:bg-rose-100 transition-colors shadow-2xs"
                  >
                    🎯 Target
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating Relationship Details Card when line is clicked */}
      {activeSelectedEdge && !activeSelectedNode && (
        <div className="absolute top-14 sm:top-16 right-2 sm:right-3 z-30 w-72 max-w-[calc(100%-16px)] max-h-[calc(100%-68px)] overflow-y-auto max-sm:top-auto max-sm:bottom-3 max-sm:left-3 max-sm:right-3 max-sm:w-auto max-sm:max-h-[45vh] bg-white/95 backdrop-blur-md p-4 rounded-xl border border-neutral-200 shadow-xl animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-start justify-between border-b border-neutral-100 pb-2.5">
            <div>
              <span className="text-[9px] font-extrabold uppercase tracking-wider text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-100">
                Relationship
              </span>
              <h4 className="text-sm font-bold text-neutral-900 leading-snug mt-0.5">
                {String(activeSelectedEdge.label || activeSelectedEdge.edge_type || '').replaceAll('_', ' ')}
              </h4>
            </div>
            <button
              onClick={() => handleSelectEdge(null)}
              className="text-neutral-400 hover:text-neutral-700 p-1 rounded-md hover:bg-neutral-100 transition-colors"
              title="Close Relationship Card"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="mt-3 space-y-2.5 text-xs text-neutral-700">
            {/* Endpoints */}
            <div className="p-2 bg-neutral-50 rounded-lg border border-neutral-100 space-y-1 text-[11px]">
              <div className="flex justify-between">
                <span className="text-neutral-500 font-medium">From:</span>
                <span className="font-bold text-neutral-900 truncate max-w-[170px]">
                  {edgeSourceNode?.label || (typeof activeSelectedEdge.source === 'object' ? activeSelectedEdge.source.id : activeSelectedEdge.source)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-500 font-medium">To:</span>
                <span className="font-bold text-neutral-900 truncate max-w-[170px]">
                  {edgeTargetNode?.label || (typeof activeSelectedEdge.target === 'object' ? activeSelectedEdge.target.id : activeSelectedEdge.target)}
                </span>
              </div>
            </div>

            {/* Reason */}
            {activeSelectedEdge.reason && (
              <div>
                <div className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1 mb-1">
                  <FileText className="h-3 w-3 text-blue-600" /> Reason
                </div>
                <div className="p-2 bg-blue-50/80 border border-blue-100 rounded-lg text-blue-950 font-semibold text-[11px] leading-relaxed">
                  {activeSelectedEdge.reason}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Temporal Timeline Scrubber Toolbar */}
      {enableTemporalScrubber && showScrubber && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 w-[92%] max-w-lg bg-white/95 backdrop-blur-md px-4 py-2.5 rounded-xl border border-neutral-300 shadow-lg flex items-center gap-3">
          <button
            onClick={handleTogglePlay}
            aria-label={isPlaying ? 'Pause Timeline' : 'Play Timeline Evolution'}
            className="p-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors focus:outline-none"
            title={isPlaying ? 'Pause Timeline' : 'Play Timeline Evolution'}
          >
            {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          </button>
          <button
            onClick={() => {
              setTimeIndex(0)
              setIsPlaying(false)
            }}
            className="p-1.5 hover:bg-neutral-100 rounded-lg text-neutral-600 transition-colors focus:outline-none"
            title="Reset Timeline to Start"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>

          <div className="flex-1 flex flex-col gap-0.5">
            <div className="flex justify-between text-[9.5px] font-bold text-neutral-600">
              <span>Investigation Start</span>
              <span className="text-blue-700 font-mono">
                {timeIndex < 100 ? `${timeIndex}% Sequence Point` : 'All Grounded Evidence (100%)'}
              </span>
              <span>Latest Trace</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={timeIndex}
              onChange={(e) => {
                setTimeIndex(Number(e.target.value))
                setIsPlaying(false)
              }}
              className="w-full h-1.5 bg-neutral-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>
        </div>
      )}

      {/* SVG Canvas for D3 Rendering */}
      <svg
        ref={svgRef}
        className="w-full h-full cursor-default"
        onClick={() => {
          handleSelectNode(null)
          handleSelectEdge(null)
        }}
      />
    </div>
  )
}
export default D3NetworkGraph
