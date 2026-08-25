/**
 * frontend/src/components/NetworkAnalysisPanel.tsx
 *
 * Case Network Analysis Panel powered by D3.js Force-Directed Graph Engine.
 * Features:
 * - Dynamic D3 physics simulation with automatic multi-port spacing
 * - Comprehensive Inspector for Node Attributes & Relationship Evidence
 * - High-contrast entity cards with entity icons & case badges
 * - Table / Graph view toggle, Fullscreen view, and Print/Dossier export
 */
import { useState, useMemo, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useCaseNetwork, type NetworkNode } from '@/hooks/useCaseNetwork'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { D3NetworkGraph, type D3GraphNode, type D3GraphEdge } from '@/components/nexus/D3NetworkGraph'
import { EvidenceDrawer } from '@/components/nexus/EvidenceDrawer'
import { 
  Network, 
  Link as LinkIcon, 
  Layers, 
  Table2, 
  Share2, 
  Minimize2,
  Maximize, 
  Eye, 
  EyeOff, 
  Printer, 
  BookOpen,
  FileText,
  Move,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react'

interface NetworkAnalysisPanelProps {
  caseId: string
  selectedEntityId?: string | null
  onEntitySelect?: (id: string | null) => void
}

type ViewMode = 'graph' | 'table'

// Shorten long IDs (e.g. 8d5e...9cc1)
function shortenId(id: string): string {
  if (id && id.length > 12 && id.includes('-')) {
    return `${id.substring(0, 4)}...${id.substring(id.length - 4)}`
  }
  return id
}

// Safe node label extractor
function getNodeLabel(node?: NetworkNode | null): string {
  return node?.data?.label || node?.label || node?.id || ''
}

const LAYER_CONFIG: Record<string, { label: string; ring: string }> = {
  person: { label: 'Person', ring: 'border-sky-400 text-sky-900' },
  case: { label: 'Case', ring: 'border-rose-400 text-rose-900' },
  phone: { label: 'Phone', ring: 'border-amber-400 text-amber-900' },
  account: { label: 'Account', ring: 'border-violet-400 text-violet-900' },
  evidence: { label: 'Evidence', ring: 'border-teal-400 text-teal-900' },
  section: { label: 'Section', ring: 'border-indigo-400 text-indigo-900' },
  law: { label: 'Law', ring: 'border-indigo-400 text-indigo-900' },
}

export function NetworkAnalysisPanel({
  caseId,
  selectedEntityId,
  onEntitySelect,
}: NetworkAnalysisPanelProps) {
  const { data: graphData, isLoading, error, refetch } = useCaseNetwork(caseId)
  const [viewMode, setViewMode] = useState<ViewMode>('graph')
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [evidenceDrawerEdgeId, setEvidenceDrawerEdgeId] = useState<string | null>(null)
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())
  const [showInspector, setShowInspector] = useState(true)
  const [showLegend, setShowLegend] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isPrinting, setIsPrinting] = useState(false)
  const [layoutDensity, setLayoutDensity] = useState<'compact' | 'normal' | 'spacious' | 'extra-spacious'>('normal')
  const containerRef = useRef<HTMLDivElement>(null)

  const toggleFullscreen = () => {
    if (!containerRef.current) return
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => setIsFullscreen(true))
      setIsFullscreen(true)
    } else {
      document.exitFullscreen().catch(() => setIsFullscreen(false))
      setIsFullscreen(false)
    }
  }

  const handlePrint = () => {
    setIsPrinting(true)
    setTimeout(() => {
      window.print()
      setIsPrinting(false)
    }, 100)
  }

  const toggleType = (type: string) => {
    setHiddenTypes((prev) => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }

  const typeOptions = useMemo(() => {
    if (!graphData) return []
    return [...new Set(graphData.nodes.map((n) => n.type))]
  }, [graphData])

  const visibleNodes = useMemo(() => {
    if (!graphData) return []
    return graphData.nodes.filter((n) => !hiddenTypes.has(n.type))
  }, [graphData, hiddenTypes])

  const visibleIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes])

  // Transform nodes for D3
  const d3Nodes = useMemo<D3GraphNode[]>(() => {
    return visibleNodes.map((n) => ({
      id: n.id,
      label: getNodeLabel(n),
      name: getNodeLabel(n),
      entity_type: n.type,
      type: n.type,
      properties: n.properties,
      timestamp: (n.properties?.timestamp || n.properties?.occurred_at || n.properties?.created_at || n.properties?.date || (n.data as Record<string, unknown>)?.occurred_at) as string,
      badges: (n.properties?.badges as string[]) || [],
    }))
  }, [visibleNodes])

  // Transform edges for D3
  const d3Edges = useMemo<D3GraphEdge[]>(() => {
    if (!graphData) return []
    return graphData.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        edge_type: e.edge_type,
        label: e.label,
        reason: e.reason,
        derivation_class: e.derivation_class,
        confidence: e.confidence,
        provenance: e.provenance,
        properties: e.properties,
        timestamp: ((e as Record<string, unknown>).timestamp || (e.properties as Record<string, unknown>)?.recorded_at || (e.properties as Record<string, unknown>)?.occurred_at || (e.provenance as Record<string, unknown>)?.occurred_at) as string,
        call_count: (e as Record<string, unknown>).call_count,
        channel: (e as Record<string, unknown>).channel,
      }))
  }, [graphData, visibleIds])

  const [internalEntityId, setInternalEntityId] = useState<string | null>(null)
  const activeEntityId = selectedEntityId !== undefined && selectedEntityId !== null ? selectedEntityId : internalEntityId

  // Active Inspector selection
  const defaultCaseNode = useMemo<NetworkNode | null>(() => {
    if (!graphData) return null
    return graphData.nodes.find(n => n.type === 'case') || graphData.nodes[0]
  }, [graphData])

  const inspectTarget = useMemo<NetworkNode | null>(() => {
    if (!graphData) return null
    if (activeEntityId) {
      return graphData.nodes.find(n => n.id === activeEntityId) ?? null
    }
    return defaultCaseNode
  }, [graphData, activeEntityId, defaultCaseNode])

  const selectedEdge = useMemo(() => {
    if (!graphData || !selectedEdgeId) return null
    return graphData.edges.find(e => e.id === selectedEdgeId) ?? null
  }, [graphData, selectedEdgeId])

  const edgeSourceNode = useMemo(() => {
    if (!graphData || !selectedEdge) return null
    return graphData.nodes.find(n => n.id === selectedEdge.source) ?? null
  }, [graphData, selectedEdge])

  const edgeTargetNode = useMemo(() => {
    if (!graphData || !selectedEdge) return null
    return graphData.nodes.find(n => n.id === selectedEdge.target) ?? null
  }, [graphData, selectedEdge])

  // Connections for inspector
  const connections = useMemo(() => {
    const activeId = activeEntityId || defaultCaseNode?.id
    if (!graphData || !activeId) return []

    const items: { node: NetworkNode; relation: string }[] = []
    graphData.edges.forEach((edge) => {
      if (edge.source === activeId) {
        const target = graphData.nodes.find(n => n.id === edge.target)
        if (target) items.push({ node: target, relation: edge.label })
      } else if (edge.target === activeId) {
        const source = graphData.nodes.find(n => n.id === edge.source)
        if (source) items.push({ node: source, relation: edge.label })
      }
    })
    return items
  }, [graphData, activeEntityId, defaultCaseNode])

  if (isLoading) return <LoadingSkeleton layout="detail" />
  if (error) return <ErrorState message="Failed to load case investigation graph." onRetry={refetch} />
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="py-12 border border-dashed border-neutral-300 rounded-radius-md bg-neutral-50 text-center">
        <Network className="mx-auto h-12 w-12 text-neutral-400 mb-4" aria-hidden="true" />
        <h3 className="text-h2 font-semibold text-neutral-700">No graph data available</h3>
      </div>
    )
  }

  const graphDescription = `Investigation network containing ${graphData.nodes.length} entities and ${graphData.edges.length} relationships.`

  return (
    <div className={`relative w-full ${isFullscreen ? 'fixed inset-0 z-50 bg-white p-4 h-screen w-screen flex flex-col overflow-hidden' : 'space-y-4'}`} ref={containerRef}>
      {/* Printable Paper Overlay */}
      {isPrinting && (
        <div className="hidden print:block absolute inset-0 bg-white text-black p-8 font-serif z-50">
          <div className="border-b-2 border-black pb-4 mb-6">
            <h1 className="text-2xl font-bold uppercase tracking-wide">NEXUS Criminal Intelligence Network Board</h1>
            <div className="grid grid-cols-2 gap-4 text-xs mt-2 font-mono">
              <div><strong>CASE ID:</strong> {caseId}</div>
              <div><strong>DATE GENERATED:</strong> {new Date().toLocaleDateString()}</div>
              <div><strong>OFFICER ROLE:</strong> Investigator</div>
              <div><strong>INTELLIGENCE SYSTEM:</strong> NEXUS Intelligence Graph</div>
            </div>
          </div>
          <div className="space-y-4">
            <h2 className="text-lg font-bold underline">Investigation Target Nodes</h2>
            <table className="w-full text-xs border-collapse border border-black">
              <thead>
                <tr className="bg-neutral-100">
                  <th className="border border-black p-2">Entity ID</th>
                  <th className="border border-black p-2">Label</th>
                  <th className="border border-black p-2">Type</th>
                </tr>
              </thead>
              <tbody>
                {graphData.nodes.map(n => (
                  <tr key={n.id}>
                    <td className="border border-black p-2 font-mono">{n.id}</td>
                    <td className="border border-black p-2 font-bold">{getNodeLabel(n)}</td>
                    <td className="border border-black p-2 capitalize">{n.type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* View Mode Toggle & Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div className="flex items-center gap-3">
          <p className="text-small text-neutral-600">{graphDescription}</p>
          <Link
            to="/network"
            className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-md hover:bg-blue-100 transition-colors shadow-2xs"
            title="View this case in Global Multi-Case Network Explorer"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            <span>Open in Global Explorer</span>
          </Link>
        </div>

        <div
          className="flex items-center rounded-radius-md bg-neutral-100 p-1 text-caption font-semibold"
          role="group"
          aria-label="Network view mode"
        >
          <button
            onClick={() => setViewMode('graph')}
            aria-pressed={viewMode === 'graph'}
            className={`inline-flex min-h-9 items-center gap-1.5 rounded-radius-sm px-3 py-1 transition-all duration-fast ${
              viewMode === 'graph'
                ? 'bg-neutral-50 shadow-sm text-neutral-900 font-bold'
                : 'text-neutral-500 hover:text-neutral-800'
            }`}
          >
            <Share2 className="h-3.5 w-3.5" aria-hidden="true" />
            Graph
          </button>
          <button
            onClick={() => setViewMode('table')}
            aria-pressed={viewMode === 'table'}
            className={`inline-flex min-h-9 items-center gap-1.5 rounded-radius-sm px-3 py-1 transition-all duration-fast ${
              viewMode === 'table'
                ? 'bg-neutral-50 shadow-sm text-neutral-900 font-bold'
                : 'text-neutral-500 hover:text-neutral-800'
            }`}
          >
            <Table2 className="h-3.5 w-3.5" aria-hidden="true" />
            Table
          </button>
        </div>
      </div>

      {/* Table view */}
      {viewMode === 'table' && (
        <div className="space-y-4 print:hidden">
          <section aria-labelledby="network-nodes-heading">
            <h3 id="network-nodes-heading" className="text-h2 font-semibold text-neutral-800 mb-3">
              Network Entities ({visibleNodes.length})
            </h3>
            <div className="w-full overflow-x-auto rounded-radius-md border border-neutral-200 bg-neutral-50">
              <table className="w-full border-collapse text-left text-small text-neutral-800" aria-label="Case network entities">
                <thead className="border-b border-neutral-200 bg-neutral-100">
                  <tr>
                    <th scope="col" className="px-4 py-3 font-semibold uppercase tracking-wider">Entity</th>
                    <th scope="col" className="px-4 py-3 font-semibold uppercase tracking-wider">Type</th>
                    <th scope="col" className="px-4 py-3 font-semibold uppercase tracking-wider">ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {visibleNodes.map((node) => (
                    <tr 
                      key={node.id} 
                      onClick={() => {
                        setInternalEntityId(node.id)
                        onEntitySelect?.(node.id)
                        setSelectedEdgeId(null)
                      }}
                      className={`hover:bg-neutral-100/50 cursor-pointer ${activeEntityId === node.id ? 'bg-rose-50/40 font-bold' : ''}`}
                    >
                      <td className="px-4 py-2 font-medium text-neutral-900">{getNodeLabel(node)}</td>
                      <td className="px-4 py-2 capitalize text-neutral-600">{node.type}</td>
                      <td className="px-4 py-2 font-mono text-neutral-500">{shortenId(node.id)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* Graph Canvas Workspace */}
      {viewMode === 'graph' && (
        <div className={`grid grid-cols-1 gap-4 ${isFullscreen ? 'flex-1 min-h-0 h-[calc(100vh-100px)]' : 'h-[600px]'} transition-all ${showInspector ? 'lg:grid-cols-4' : 'lg:grid-cols-1'}`}>
          {/* D3 Graph View (Left 75% or Full) */}
          <div className="lg:col-span-3 rounded-radius-md border border-neutral-200 bg-neutral-50 h-full relative flex flex-col min-w-0">
            
            {/* Top-Left Layer Filter Bar (Matches GlobalNetworkCanvas) */}
            {typeOptions.length > 0 && (
              <div className="absolute left-3 top-3 z-20 flex flex-wrap items-center gap-1.5 rounded-lg border border-neutral-200 bg-white/95 backdrop-blur-sm px-2.5 py-1.5 text-xs shadow-sm max-w-[calc(100%-220px)] overflow-x-auto">
                <span className="font-bold uppercase tracking-wider text-neutral-600 text-[10px] flex items-center gap-1 mr-1">
                  <Layers className="h-3 w-3 text-blue-600" /> Layers
                </span>
                {typeOptions.map((t) => {
                  const isHidden = hiddenTypes.has(t)
                  const cfg = LAYER_CONFIG[t.toLowerCase()]
                  return (
                    <button
                      key={t}
                      onClick={() => toggleType(t)}
                      aria-pressed={!isHidden}
                      className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold transition-colors capitalize ${
                        isHidden
                          ? 'border-neutral-200 bg-neutral-100 text-neutral-400'
                          : `${cfg?.ring ?? 'border-neutral-300 text-neutral-900'} bg-white shadow-2xs font-bold`
                      }`}
                    >
                      {cfg?.label ?? t}
                    </button>
                  )
                })}
              </div>
            )}

            {/* Top-Right Toolbar Controls */}
            <div className="absolute top-3 right-3 z-20 flex items-center gap-1 bg-white/95 backdrop-blur-sm p-1 rounded-radius-md border border-neutral-200 shadow-sm">
              <button 
                onClick={() => {
                  setLayoutDensity(prev => prev === 'spacious' ? 'extra-spacious' : prev === 'extra-spacious' ? 'compact' : prev === 'compact' ? 'normal' : 'spacious')
                }} 
                className={`p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none flex items-center gap-1 px-2 text-[11px] font-semibold transition-colors ${layoutDensity !== 'normal' ? 'text-blue-700 bg-blue-50/90 font-bold' : ''}`} 
                title={`Spacing: ${layoutDensity} (Click to expand or compact physics forces)`}
              >
                <Move className="h-3.5 w-3.5" />
                <span className="capitalize">{layoutDensity}</span>
              </button>

              <div className="w-px bg-neutral-200 mx-0.5 h-4" />

              <button onClick={toggleFullscreen} className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none" title="Fullscreen toggle">
                {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
              </button>
              <button onClick={handlePrint} className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none" title="Print/Export Investigation Board">
                <Printer className="h-4 w-4" />
              </button>
              <button onClick={() => setShowLegend(prev => !prev)} className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none" title="Toggle Legend">
                <BookOpen className="h-4 w-4" />
              </button>
              <button onClick={() => setShowInspector(prev => !prev)} className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none" title="Toggle Inspector">
                {showInspector ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {/* D3 Force Directed Graph Engine */}
            <D3NetworkGraph
              nodes={d3Nodes}
              edges={d3Edges}
              selectedNodeId={activeEntityId}
              selectedEdgeId={selectedEdgeId}
              onNodeSelect={(nodeId) => {
                setInternalEntityId(nodeId)
                onEntitySelect?.(nodeId)
                setSelectedEdgeId(null)
              }}
              onEdgeSelect={(edgeId) => {
                setSelectedEdgeId(edgeId)
                setInternalEntityId(null)
                onEntitySelect?.(null)
              }}
              densityMode={layoutDensity}
              enableTemporalScrubber={true}
              className="flex-grow min-h-0"
            />

            {/* Legend overlay */}
            {showLegend && (
              <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm px-3.5 py-2.5 rounded-lg border border-neutral-200 text-caption text-neutral-700 shadow-md z-10 space-y-2 max-w-xs animate-in fade-in zoom-in-95 duration-150">
                <div>
                  <div className="font-bold text-neutral-900 uppercase tracking-wider text-[9px] mb-1">Entity Categories & Shapes</div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px]">
                    <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-rose-500 inline-block" /> Case (Square)</div>
                    <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-sky-500 inline-block" /> Person (Circle)</div>
                    <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-amber-500 inline-block rotate-45" /> Phone (Triangle)</div>
                    <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-violet-500 inline-block rounded-xs" /> Account (Hexagon)</div>
                    <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-teal-500 inline-block" /> Evidence (Cross)</div>
                    <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-indigo-500 inline-block" /> Law (Star)</div>
                  </div>
                </div>
                <div className="border-t border-neutral-200 pt-1.5">
                  <div className="font-bold text-neutral-900 uppercase tracking-wider text-[9px] mb-1">Relationships</div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px]">
                    <div className="flex items-center gap-1.5"><span className="h-1 w-3 rounded bg-rose-600" /> Accused</div>
                    <div className="flex items-center gap-1.5"><span className="h-1 w-3 rounded bg-emerald-600" /> Bank Wire</div>
                    <div className="flex items-center gap-1.5"><span className="h-1 w-3 rounded bg-amber-600" /> CDR Call</div>
                    <div className="flex items-center gap-1.5"><span className="h-1 w-3 rounded bg-blue-600" /> Bridge</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Inspector Panel (25%) */}
          {showInspector && selectedEdgeId && selectedEdge && (
            <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 overflow-y-auto flex flex-col h-full shadow-xs">
              <div className="border-b border-neutral-200 pb-3 flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-900 border border-amber-300 px-1.5 py-0.5 rounded-radius-sm">
                    Relationship Reason & Evidence
                  </span>
                  <h3 className="text-h2 font-bold text-neutral-900 mt-2">
                    {selectedEdge.label?.replaceAll('_', ' ')}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedEdgeId(null)}
                  className="text-neutral-400 hover:text-neutral-700 p-1 rounded-radius-sm hover:bg-neutral-200 text-xs font-bold"
                  title="Close Inspector"
                >
                  ✕
                </button>
              </div>

              <div className="mt-4 space-y-4">
                {/* Connected Endpoints */}
                <div>
                  <h4 className="text-caption font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
                    <LinkIcon className="h-4 w-4" aria-hidden="true" /> Connected Entities
                  </h4>
                  <div className="mt-2 space-y-2">
                    <div className="p-2.5 bg-white border border-neutral-200 rounded-radius-sm">
                      <div className="text-[9px] font-bold text-neutral-400 uppercase">From (Source)</div>
                      <div className="font-bold text-neutral-900 text-small">{getNodeLabel(edgeSourceNode)}</div>
                      <div className="text-[8px] font-mono text-neutral-500">{selectedEdge.source}</div>
                    </div>
                    <div className="p-2.5 bg-white border border-neutral-200 rounded-radius-sm">
                      <div className="text-[9px] font-bold text-neutral-400 uppercase">To (Target)</div>
                      <div className="font-bold text-neutral-900 text-small">{getNodeLabel(edgeTargetNode)}</div>
                      <div className="text-[8px] font-mono text-neutral-500">{selectedEdge.target}</div>
                    </div>
                  </div>
                </div>

                {/* Reason why they are connected */}
                <div>
                  <h4 className="text-caption font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
                    <FileText className="h-4 w-4 text-status-info" aria-hidden="true" /> Reason for Connection
                  </h4>
                  <div className="mt-2 p-3 bg-blue-50/90 border border-blue-200 rounded-radius-sm text-neutral-900 text-small leading-relaxed font-semibold">
                    {selectedEdge.reason || 'Direct investigative relationship between entities.'}
                  </div>
                </div>

                {/* Evidentiary Provenance */}
                <div>
                  <h4 className="text-caption font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="h-4 w-4" aria-hidden="true" /> Evidentiary Provenance
                  </h4>
                  <dl className="mt-2 text-small space-y-1 text-neutral-700 bg-neutral-100 p-3 rounded-radius-sm">
                    {selectedEdge.provenance?.source_type && (
                      <div className="flex justify-between">
                        <dt className="text-neutral-500">Source Type</dt>
                        <dd className="font-bold text-blue-900">{String(selectedEdge.provenance.source_type)}</dd>
                      </div>
                    )}
                    {selectedEdge.provenance?.source_id && (
                      <div className="flex justify-between">
                        <dt className="text-neutral-500">Source Record ID</dt>
                        <dd className="font-mono text-[10px]">{String(selectedEdge.provenance.source_id)}</dd>
                      </div>
                    )}
                    {selectedEdge.provenance?.derivation_method && (
                      <div className="flex justify-between">
                        <dt className="text-neutral-500">Derivation</dt>
                        <dd className="font-semibold text-neutral-800">{String(selectedEdge.provenance.derivation_method)}</dd>
                      </div>
                    )}
                    {(selectedEdge as Record<string, unknown>).call_count !== undefined && (
                      <div className="flex justify-between">
                        <dt className="text-neutral-500">Call Count</dt>
                        <dd className="font-bold text-amber-800">{String((selectedEdge as Record<string, unknown>).call_count)} Calls</dd>
                      </div>
                    )}
                    {(selectedEdge as Record<string, unknown>).channel && (
                      <div className="flex justify-between">
                        <dt className="text-neutral-500">Channel</dt>
                        <dd className="capitalize">{String((selectedEdge as Record<string, unknown>).channel).replace('_', ' ')}</dd>
                      </div>
                    )}
                  </dl>
                </div>

                {/* Open Full Evidence Drawer Button */}
                <button
                  onClick={() => setEvidenceDrawerEdgeId(selectedEdge.id)}
                  className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-colors"
                >
                  <ShieldCheck className="h-4 w-4" />
                  <span>Inspect Full Evidence Chain</span>
                </button>
              </div>
            </div>
          )}

          {showInspector && inspectTarget && !selectedEdgeId && (
            <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 overflow-y-auto flex flex-col h-full shadow-xs">
              <div className="border-b border-neutral-200 pb-3">
                <span className="text-[10px] font-bold text-status-info uppercase tracking-wider bg-neutral-200/55 px-1.5 py-0.5 rounded-radius-sm">
                  {selectedEntityId ? `${inspectTarget.type} entity` : 'Active Context Case'}
                </span>
                <h3 className="text-h2 font-bold text-neutral-900 mt-2">
                  {getNodeLabel(inspectTarget)}
                </h3>
              </div>

              <div className="mt-4 space-y-4">
                <div>
                  <h4 className="text-caption font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="h-4 w-4" aria-hidden="true" /> Attributes
                  </h4>
                  <dl className="mt-2 text-small space-y-1 text-neutral-700 bg-neutral-100 p-3 rounded-radius-sm">
                    <div className="flex justify-between">
                      <dt className="text-neutral-500">ID Reference</dt>
                      <dd className="font-mono">{shortenId(inspectTarget.id)}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-neutral-500">Node Class</dt>
                      <dd className="capitalize font-semibold">{inspectTarget.type}</dd>
                    </div>
                  </dl>
                </div>

                <div>
                  <h4 className="text-caption font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
                    <LinkIcon className="h-4 w-4" aria-hidden="true" /> Connected Relationships ({connections.length})
                  </h4>
                  {connections.length === 0 ? (
                    <p className="text-small text-neutral-500 mt-2">No active connections found.</p>
                  ) : (
                    <ul className="mt-2 space-y-2 max-h-[180px] overflow-y-auto pr-1">
                      {connections.map(({ node, relation }) => (
                        <li
                          key={node.id}
                          className="text-small p-2 bg-white border border-neutral-200 rounded-radius-sm flex flex-col"
                        >
                          <span className="font-semibold text-neutral-800">{getNodeLabel(node)}</span>
                          <span className="text-caption text-neutral-500 mt-0.5">
                            Relationship: <code className="bg-neutral-100 px-1 rounded text-caption">{relation}</code>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Slide-over Evidence Drawer with full evidentiary provenance */}
      <EvidenceDrawer
        relationshipId={evidenceDrawerEdgeId}
        onClose={() => setEvidenceDrawerEdgeId(null)}
      />
    </div>
  )
}
export default NetworkAnalysisPanel
