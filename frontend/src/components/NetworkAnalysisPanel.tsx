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
import { useCaseNetwork, type NetworkNode } from '@/hooks/useCaseNetwork'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { D3NetworkGraph, type D3GraphNode, type D3GraphEdge } from '@/components/nexus/D3NetworkGraph'
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
  Move
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

export function NetworkAnalysisPanel({
  caseId,
  selectedEntityId,
  onEntitySelect,
}: NetworkAnalysisPanelProps) {
  const { data: graphData, isLoading, error, refetch } = useCaseNetwork(caseId)
  const [viewMode, setViewMode] = useState<ViewMode>('graph')
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
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

  // Transform nodes for D3
  const d3Nodes = useMemo<D3GraphNode[]>(() => {
    if (!graphData) return []
    return graphData.nodes.map((n) => ({
      id: n.id,
      label: getNodeLabel(n),
      name: getNodeLabel(n),
      entity_type: n.type,
      type: n.type,
      properties: n.properties,
    }))
  }, [graphData])

  // Transform edges for D3
  const d3Edges = useMemo<D3GraphEdge[]>(() => {
    if (!graphData) return []
    return graphData.edges.map((e) => ({
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
      call_count: (e as Record<string, unknown>).call_count,
      channel: (e as Record<string, unknown>).channel,
    }))
  }, [graphData])

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
      <div className="flex items-center justify-between print:hidden">
        <p className="text-small text-neutral-600">{graphDescription}</p>
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
                ? 'bg-neutral-50 shadow-sm text-neutral-900'
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
                ? 'bg-neutral-50 shadow-sm text-neutral-900'
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
              Network Entities
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
                  {graphData.nodes.map((node) => (
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
            
            {/* Top Toolbar Controls */}
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
              <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm px-3 py-2 rounded-radius-sm border border-neutral-200 text-caption text-neutral-600 shadow-md z-10 space-y-1.5">
                <div className="font-bold text-neutral-900 uppercase tracking-wider text-[9px] mb-1">Entity Categories</div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px]">
                  <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-rose-500 mr-1.5" /> Case Record</div>
                  <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-sky-500 mr-1.5" /> Person Entity</div>
                  <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-amber-500 mr-1.5" /> CDR / Mobile</div>
                  <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-violet-500 mr-1.5" /> Bank Account</div>
                  <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-teal-500 mr-1.5" /> Evidence Log</div>
                  <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-indigo-500 mr-1.5" /> Penal Section</div>
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

                {/* Provenance & Source Metadata */}
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
    </div>
  )
}
export default NetworkAnalysisPanel
