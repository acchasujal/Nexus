import { useState, useMemo, useEffect, useRef } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider, useReactFlow, type Node, type Edge } from '@xyflow/react'
import { useCaseNetwork, type NetworkNode, type NetworkEdge } from '@/hooks/useCaseNetwork'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { 
  Info, 
  HelpCircle, 
  Network, 
  Link as LinkIcon, 
  User, 
  Layers, 
  Table2, 
  Share2, 
  Briefcase, 
  ShieldAlert, 
  Maximize2, 
  Minimize2,
  RefreshCw, 
  ZoomIn, 
  ZoomOut, 
  Maximize, 
  Eye, 
  EyeOff, 
  Printer, 
  Download,
  BookOpen
} from 'lucide-react'

// Import React Flow styles inline to scope them cleanly
import '@xyflow/react/dist/style.css'

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

// Custom node components to match Palantir Gotham design specifications
function CustomCaseNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-4 py-2.5 rounded-radius-md border shadow-md text-small text-center transition-opacity duration-fast min-w-[160px] bg-rose-50 border-rose-500 text-rose-900 font-semibold ${data.isDimmed ? 'opacity-25' : ''}`}>
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <div className="flex items-center justify-center gap-1.5 mb-1.5 text-[9px] uppercase tracking-wider text-rose-600 font-bold">
        <Briefcase className="h-3 w-3" /> Case
      </div>
      <div className="text-neutral-900 font-extrabold text-xs truncate max-w-[150px]">{data.label}</div>
      <div className="text-[9px] text-neutral-400 font-mono mt-1">Ref: {shortenId(id)}</div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  )
}

function CustomPersonNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3 py-2 rounded-radius-full border shadow-xs text-small text-center transition-opacity duration-fast min-w-[140px] bg-sky-50 border-sky-400 text-sky-800 font-medium ${data.isDimmed ? 'opacity-25' : ''}`}>
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <div className="flex items-center justify-center gap-1 mb-1 text-[9px] uppercase tracking-wider text-sky-500 font-bold">
        <User className="h-3 w-3" /> Person
      </div>
      <div className="text-neutral-800 font-semibold text-xs truncate max-w-[130px]">{data.label}</div>
      <div className="text-[8px] text-neutral-400 font-mono">Ref: {shortenId(id)}</div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  )
}

function CustomDependencyNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3 py-2 rounded-radius-md border shadow-xs text-small text-center transition-opacity duration-fast min-w-[150px] bg-amber-50 border-amber-400 text-amber-800 ${data.isDimmed ? 'opacity-25' : ''}`}>
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <div className="flex items-center justify-center gap-1 mb-1 text-[9px] uppercase tracking-wider text-amber-600 font-bold">
        <ShieldAlert className="h-3 w-3" /> Blocker
      </div>
      <div className="text-neutral-800 font-semibold text-xs truncate max-w-[140px]">{data.label}</div>
      <div className="text-[8px] text-neutral-400 font-mono mt-0.5">Ref: {shortenId(id)}</div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  )
}

function CustomNeutralNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3 py-2 rounded-radius-sm border border-neutral-300 bg-neutral-50 shadow-xs text-small text-center transition-opacity duration-fast min-w-[130px] text-neutral-700 ${data.isDimmed ? 'opacity-25' : ''}`}>
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <div className="text-neutral-900 font-medium text-xs truncate max-w-[125px]">{data.label}</div>
      <div className="text-[8px] text-neutral-400 font-mono">Ref: {shortenId(id)}</div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  )
}

const nodeTypes = {
  case: CustomCaseNode,
  person: CustomPersonNode,
  officer: CustomPersonNode,
  dependency: CustomDependencyNode,
  clock: CustomDependencyNode,
  evidence: CustomDependencyNode,
  unit: CustomNeutralNode,
  act: CustomNeutralNode,
  court: CustomNeutralNode,
  location: CustomNeutralNode,
  'crime-head': CustomNeutralNode,
  crime_sub_head: CustomNeutralNode,
  section: CustomNeutralNode,
}

// Wrapper to provide ReactFlow context
export function NetworkAnalysisPanel(props: NetworkAnalysisPanelProps) {
  return (
    <ReactFlowProvider>
      <NetworkAnalysisPanelContent {...props} />
    </ReactFlowProvider>
  )
}

function NetworkAnalysisPanelContent({ caseId, selectedEntityId, onEntitySelect }: NetworkAnalysisPanelProps) {
  const { data: graphData, isLoading, error, refetch } = useCaseNetwork(caseId)
  const { fitView, zoomIn, zoomOut, zoomTo, setCenter } = useReactFlow()

  // Fullscreen, view toggles & layout states
  const [viewMode, setViewMode] = useState<ViewMode>('graph')
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showLegend, setShowLegend] = useState(true)
  const [showInspector, setShowInspector] = useState(true)
  const [isPrinting, setIsPrinting] = useState(false)

  const containerRef = useRef<HTMLDivElement>(null)

  // Sync fullscreen state with ESC exits
  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFsChange)
    return () => document.removeEventListener('fullscreenchange', handleFsChange)
  }, [])

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen().catch(() => {
        setIsFullscreen(true)
      })
    } else {
      document.exitFullscreen()
    }
  }

  const handlePrint = () => {
    setIsPrinting(true)
    setTimeout(() => {
      window.print()
      setIsPrinting(false)
    }, 300)
  }

  // Grouping nodes by relation to Case for logical positioning (no-overlap layout)
  const flowNodes = useMemo<Node[]>(() => {
    if (!graphData) return []

    const caseNode = graphData.nodes.find(n => n.type === 'case')
    const primaryCaseId = caseNode ? caseNode.id : ''

    const victimIds = new Set<string>()
    const accusedIds = new Set<string>()
    const dependencyIds = new Set<string>()
    const evidenceIds = new Set<string>()
    const officerIds = new Set<string>()
    const lawIds = new Set<string>()

    graphData.edges.forEach(edge => {
      if (edge.source === primaryCaseId || edge.target === primaryCaseId) {
        const otherId = edge.source === primaryCaseId ? edge.target : edge.source
        if (edge.label === 'VICTIM_IN') victimIds.add(otherId)
        else if (edge.label === 'ACCUSED_IN') accusedIds.add(otherId)
        else if (edge.label === 'CASE_HAS_DEPENDENCY') dependencyIds.add(otherId)
        else if (edge.label.includes('EVIDENCE') || edge.label.includes('PRODUCED')) evidenceIds.add(otherId)
        else if (edge.label.includes('ASSIGNED') || edge.label.includes('INVESTIGATED')) officerIds.add(otherId)
        else if (edge.label.includes('SECTION') || edge.label.includes('VIOLATED') || edge.label.includes('GOVERNED')) lawIds.add(otherId)
      }
    })

    const victimsList = graphData.nodes.filter(n => victimIds.has(n.id))
    const accusedList = graphData.nodes.filter(n => accusedIds.has(n.id))
    const dependenciesList = graphData.nodes.filter(n => dependencyIds.has(n.id) || n.type === 'dependency' || n.type === 'clock')
    const evidenceList = graphData.nodes.filter(n => evidenceIds.has(n.id) || n.type === 'evidence')
    const officersList = graphData.nodes.filter(n => officerIds.has(n.id) || n.type === 'officer')
    const lawsList = graphData.nodes.filter(n => lawIds.has(n.id) || n.type === 'act' || n.type === 'section')
    const remainingList = graphData.nodes.filter(n => n.id !== primaryCaseId && !victimIds.has(n.id) && !accusedIds.has(n.id) && n.type !== 'dependency' && n.type !== 'clock' && n.type !== 'evidence' && n.type !== 'officer' && n.type !== 'act' && n.type !== 'section')

    const connectedIds = new Set<string>()
    const activeId = selectedEntityId
    if (activeId) {
      connectedIds.add(activeId)
      graphData.edges.forEach((edge) => {
        if (edge.source === activeId) connectedIds.add(edge.target)
        if (edge.target === activeId) connectedIds.add(edge.source)
      })
    }

    return graphData.nodes.map((node) => {
      const isDimmed = activeId ? !connectedIds.has(node.id) : false
      
      // Compute logical, non-overlapping coordinates in clean orthogonal clusters
      let x: number
      let y: number

      if (node.id === primaryCaseId) {
        x = 400
        y = 250
      } else if (victimIds.has(node.id)) {
        const idx = victimsList.findIndex(n => n.id === node.id)
        x = 400 + (idx - (victimsList.length - 1) / 2) * 220
        y = 60
      } else if (accusedIds.has(node.id)) {
        const idx = accusedList.findIndex(n => n.id === node.id)
        x = 750
        y = 250 + (idx - (accusedList.length - 1) / 2) * 110
      } else if (node.type === 'dependency' || node.type === 'clock' || dependencyIds.has(node.id)) {
        const idx = dependenciesList.findIndex(n => n.id === node.id)
        x = 640
        y = 420 + (idx - (dependenciesList.length - 1) / 2) * 110
      } else if (node.type === 'evidence' || evidenceIds.has(node.id)) {
        const idx = evidenceList.findIndex(n => n.id === node.id)
        x = 60
        y = 250 + (idx - (evidenceList.length - 1) / 2) * 110
      } else if (node.type === 'officer' || officerIds.has(node.id)) {
        const idx = officersList.findIndex(n => n.id === node.id)
        x = 180
        y = 420 + (idx - (officersList.length - 1) / 2) * 110
      } else if (node.type === 'act' || node.type === 'section' || lawIds.has(node.id)) {
        const idx = lawsList.findIndex(n => n.id === node.id)
        x = 150
        y = 100 + (idx - (lawsList.length - 1) / 2) * 90
      } else {
        const idx = remainingList.findIndex(n => n.id === node.id)
        x = 400
        y = 450 + (idx - (remainingList.length - 1) / 2) * 90
      }

      return {
        id: node.id,
        type: node.type,
        position: { x, y },
        data: { label: node.data.label, isDimmed },
        draggable: true,
      }
    })
  }, [graphData, selectedEntityId])

  // Center canvas on selected node dynamically
  useEffect(() => {
    if (selectedEntityId) {
      const matchedNode = flowNodes.find(n => n.id === selectedEntityId)
      if (matchedNode) {
        setCenter(matchedNode.position.x + 80, matchedNode.position.y + 40, { zoom: 1.35, duration: 450 })
      }
    }
  }, [selectedEntityId, flowNodes, setCenter])

  // Map backend edge structure to React Flow Edge objects
  const flowEdges = useMemo<Edge[]>(() => {
    if (!graphData) return []

    return graphData.edges.map((edge) => {
      const isDashed = edge.label === 'CASE_HAS_DEPENDENCY' || edge.label.startsWith('INFERRED_')
      const isConnected = selectedEntityId ? (edge.source === selectedEntityId || edge.target === selectedEntityId) : true
      
      const isSelected = selectedEdgeId === edge.id || (selectedEntityId && (edge.source === selectedEntityId || edge.target === selectedEntityId))
      const isHovered = hoveredEdgeId === edge.id
      const showLabel = isSelected || isHovered

      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: showLabel ? edge.label : undefined,
        labelStyle: { fill: '#333333', fontSize: 9, fontWeight: 700 },
        style: { 
          stroke: isSelected ? '#E11D48' : (isConnected ? '#4b5563' : '#e5e5e5'), 
          strokeWidth: isSelected ? 2.5 : (isConnected ? 1.5 : 1),
          strokeDasharray: isDashed ? '4,4' : undefined 
        },
        animated: isConnected && edge.label === 'CASE_HAS_DEPENDENCY',
      }
    })
  }, [graphData, selectedEntityId, selectedEdgeId, hoveredEdgeId])

  // Get active inspector selection
  const defaultCaseNode = useMemo<NetworkNode | null>(() => {
    if (!graphData) return null
    return graphData.nodes.find(n => n.type === 'case') || graphData.nodes[0]
  }, [graphData])

  const inspectTarget = useMemo<NetworkNode | null>(() => {
    if (!graphData) return null
    if (selectedEntityId) {
      return graphData.nodes.find(n => n.id === selectedEntityId) ?? null
    }
    return defaultCaseNode
  }, [graphData, selectedEntityId, defaultCaseNode])

  // Connections count for inspector
  const connections = useMemo(() => {
    const activeId = selectedEntityId || defaultCaseNode?.id
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
  }, [graphData, selectedEntityId, defaultCaseNode])

  const getRelationExplanation = (label: string) => {
    switch (label) {
      case 'ACCUSED_IN':
        return 'Entity is identified as a primary accused party listed in the FIR.'
      case 'VICTIM_IN':
        return 'Entity is identified as the victim / complainant listed in the FIR.'
      case 'CASE_HAS_DEPENDENCY':
        return 'Case has an outstanding evidentiary requirement blocking chargesheet progression.'
      default:
        return 'Entity is linked to this case file.'
    }
  }

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
    <div className="space-y-4 relative" ref={containerRef}>
      {/* Printable Paper Overlay (renders only when printing) */}
      {isPrinting && (
        <div className="hidden print:block absolute inset-0 bg-white text-black p-8 font-serif z-50">
          <div className="border-b-2 border-black pb-4 mb-6">
            <h1 className="text-2xl font-bold uppercase tracking-wide">CaseClock Statutory Investigation Board</h1>
            <div className="grid grid-cols-2 gap-4 text-xs mt-2 font-mono">
              <div><strong>CASE ID:</strong> {caseId}</div>
              <div><strong>DATE GENERATED:</strong> {new Date().toLocaleDateString()}</div>
              <div><strong>OFFICER ROLE:</strong> Investigating Officer (IO)</div>
              <div><strong>COMMISSIONED UNDER:</strong> BNSS Guidelines</div>
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
                    <td className="border border-black p-2 font-bold">{n.data.label}</td>
                    <td className="border border-black p-2 capitalize">{n.type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* View Mode Toggle */}
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
                      onClick={() => onEntitySelect?.(node.id)}
                      className={`hover:bg-neutral-100/50 cursor-pointer ${selectedEntityId === node.id ? 'bg-rose-50/40 font-bold' : ''}`}
                    >
                      <td className="px-4 py-2 font-medium text-neutral-900">{node.data.label}</td>
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
        <div className={`grid grid-cols-1 gap-6 h-[500px] transition-all ${showInspector ? 'lg:grid-cols-4' : 'lg:grid-cols-1'}`}>
          {/* React Flow View (Left 75% or Full) */}
          <div className="lg:col-span-3 rounded-radius-md border border-neutral-200 bg-neutral-50 h-full relative flex flex-col min-w-0">
            
            {/* Top Interactive Graph Toolbar */}
            <div className="absolute top-4 left-4 z-10 flex flex-wrap gap-1 bg-white/95 p-1 rounded-radius-md border border-neutral-200 shadow-sm">
              <button onClick={() => zoomIn({ duration: 250 })} className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none" title="Zoom In">
                <ZoomIn className="h-4 w-4" />
              </button>
              <button onClick={() => zoomOut({ duration: 250 })} className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none" title="Zoom Out">
                <ZoomOut className="h-4 w-4" />
              </button>
              <button onClick={() => zoomTo(1, { duration: 250 })} className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 font-mono text-caption focus:outline-none" title="100% Zoom">
                100%
              </button>
              <button onClick={() => fitView({ duration: 350 })} className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none" title="Fit Canvas">
                Fit
              </button>
              <button 
                onClick={() => {
                  onEntitySelect?.(null);
                  setSelectedEdgeId(null);
                  fitView({ duration: 350 });
                }} 
                className="p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none" 
                title="Reset Layout"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
              
              <div className="w-px bg-neutral-200 mx-1" />

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

            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              nodeTypes={nodeTypes}
              onNodeClick={(_, node) => {
                onEntitySelect?.(node.id)
                setSelectedEdgeId(null)
              }}
              onNodeDoubleClick={(_, node) => {
                setCenter(node.position.x + 80, node.position.y + 40, { zoom: 1.45, duration: 400 })
              }}
              onEdgeClick={(_, edge) => {
                setSelectedEdgeId(edge.id)
                onEntitySelect?.(null)
              }}
              onEdgeMouseEnter={(_, edge) => setHoveredEdgeId(edge.id)}
              onEdgeMouseLeave={() => setHoveredEdgeId(null)}
              onPaneClick={() => {
                onEntitySelect?.(null)
                setSelectedEdgeId(null)
              }}
              fitView
              aria-label={graphDescription}
              className="flex-grow min-h-0"
            >
              <Background color="#ccc" gap={16} />
              <Controls showInteractive={false} />
            </ReactFlow>

            {/* Dynamic Legend overlay */}
            {showLegend && (
              <div className="absolute bottom-4 left-4 bg-white/90 px-3 py-1.5 rounded-radius-sm border border-neutral-200 text-caption text-neutral-500 shadow-sm z-10 space-y-1">
                <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-rose-400 mr-1.5" aria-hidden="true" /> Case Record</div>
                <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-sky-400 mr-1.5" aria-hidden="true" /> Person Entity</div>
                <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-amber-400 mr-1.5" aria-hidden="true" /> Blocker / Clock</div>
                <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-neutral-400 mr-1.5" aria-hidden="true" /> Reference / Law</div>
              </div>
            )}
          </div>

          {/* Right Inspector Panel (25%) */}
          {showInspector && inspectTarget && !selectedEdgeId && (
            <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 overflow-y-auto flex flex-col h-full shadow-xs">
              <div className="border-b border-neutral-200 pb-3">
                <span className="text-[10px] font-bold text-status-info uppercase tracking-wider bg-neutral-200/55 px-1.5 py-0.5 rounded-radius-sm">
                  {selectedEntityId ? `${inspectTarget.type} entity` : 'Active Context Case'}
                </span>
                <h3 className="text-h2 font-bold text-neutral-900 mt-2">
                  {inspectTarget.data.label}
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
                          <span className="font-semibold text-neutral-800">{node.data.label}</span>
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
