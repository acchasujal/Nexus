import { useState, useMemo, useEffect, useRef } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider, useReactFlow, type Node, type Edge } from '@xyflow/react'
import { useCaseNetwork, type NetworkNode } from '@/hooks/useCaseNetwork'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { 
  Network, 
  Link as LinkIcon, 
  User, 
  Layers, 
  Table2, 
  Share2, 
  Briefcase, 
  ShieldAlert, 
  Minimize2,
  RefreshCw, 
  ZoomIn, 
  ZoomOut, 
  Maximize, 
  Eye, 
  EyeOff, 
  Printer, 
  BookOpen,
  Phone,
  Landmark,
  FileText,
  Move
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

// Safe node label extractor
function getNodeLabel(node?: NetworkNode | null): string {
  return node?.data?.label || node?.label || node?.id || ''
}

// 4-Directional handles for clean cable management
function NodeHandles() {
  return (
    <>
      <Handle type="target" position={Position.Top} id="top" className="!w-2 !h-2 !bg-slate-400 !opacity-0" />
      <Handle type="source" position={Position.Bottom} id="bottom" className="!w-2 !h-2 !bg-slate-400 !opacity-0" />
      <Handle type="target" position={Position.Left} id="left" className="!w-2 !h-2 !bg-slate-400 !opacity-0" />
      <Handle type="source" position={Position.Right} id="right" className="!w-2 !h-2 !bg-slate-400 !opacity-0" />
    </>
  )
}

// Custom node components with high contrast and legible typography
function CustomCaseNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-4 py-2.5 rounded-xl border-2 shadow-md text-center transition-all duration-200 min-w-[170px] max-w-[230px] bg-rose-50 border-rose-500 text-rose-950 font-semibold ${data.isDimmed ? 'opacity-25' : 'hover:shadow-lg'}`}>
      <NodeHandles />
      <div className="flex items-center justify-center gap-1.5 mb-1 text-[9px] uppercase tracking-wider text-rose-700 font-bold">
        <Briefcase className="h-3 w-3" /> Case Record
      </div>
      <div className="text-neutral-950 font-extrabold text-xs leading-snug break-words px-1">{data.label}</div>
      <div className="text-[9px] text-rose-700/75 font-mono mt-0.5">Ref: {shortenId(id)}</div>
    </div>
  )
}

function CustomPersonNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3 py-2 rounded-xl border-2 shadow-sm text-center transition-all duration-200 min-w-[145px] max-w-[210px] bg-sky-50 border-sky-400 text-sky-950 font-medium ${data.isDimmed ? 'opacity-25' : 'hover:shadow-md'}`}>
      <NodeHandles />
      <div className="flex items-center justify-center gap-1 mb-0.5 text-[9px] uppercase tracking-wider text-sky-700 font-bold">
        <User className="h-3 w-3" /> Person
      </div>
      <div className="text-neutral-900 font-bold text-xs leading-snug break-words px-1">{data.label}</div>
      <div className="text-[8px] text-sky-700/70 font-mono">Ref: {shortenId(id)}</div>
    </div>
  )
}

function CustomDependencyNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3 py-2 rounded-xl border-2 shadow-sm text-center transition-all duration-200 min-w-[155px] max-w-[220px] bg-amber-50 border-amber-500 text-amber-950 ${data.isDimmed ? 'opacity-25' : 'hover:shadow-md'}`}>
      <NodeHandles />
      <div className="flex items-center justify-center gap-1 mb-0.5 text-[9px] uppercase tracking-wider text-amber-800 font-bold">
        <ShieldAlert className="h-3 w-3" /> Blocker / Clock
      </div>
      <div className="text-neutral-950 font-bold text-xs leading-snug break-words px-1">{data.label}</div>
      <div className="text-[8px] text-amber-800/75 font-mono mt-0.5">Ref: {shortenId(id)}</div>
    </div>
  )
}

function CustomLawNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3.5 py-2.5 rounded-xl border-2 shadow-sm text-center transition-all duration-200 min-w-[165px] max-w-[230px] bg-indigo-50 border-indigo-400 text-indigo-950 font-semibold ${data.isDimmed ? 'opacity-25' : 'hover:shadow-md'}`}>
      <NodeHandles />
      <div className="flex items-center justify-center gap-1 mb-0.5 text-[9px] uppercase tracking-wider text-indigo-700 font-bold">
        <BookOpen className="h-3.5 w-3.5" /> Law / Section
      </div>
      <div className="text-neutral-950 font-extrabold text-xs leading-snug break-words px-1">{data.label}</div>
      <div className="text-[8px] text-indigo-700/75 font-mono mt-0.5">Ref: {shortenId(id)}</div>
    </div>
  )
}

function CustomEvidenceNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3.5 py-2.5 rounded-xl border-2 shadow-sm text-center transition-all duration-200 min-w-[155px] max-w-[220px] bg-emerald-50 border-emerald-400 text-emerald-950 font-medium ${data.isDimmed ? 'opacity-25' : 'hover:shadow-md'}`}>
      <NodeHandles />
      <div className="flex items-center justify-center gap-1 mb-0.5 text-[9px] uppercase tracking-wider text-emerald-700 font-bold">
        <FileText className="h-3.5 w-3.5" /> Evidence / Report
      </div>
      <div className="text-neutral-900 font-bold text-xs leading-snug break-words px-1">{data.label}</div>
      <div className="text-[8px] text-emerald-700/75 font-mono mt-0.5">Ref: {shortenId(id)}</div>
    </div>
  )
}

function CustomPhoneNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3 py-2 rounded-xl border-2 shadow-sm text-center transition-all duration-200 min-w-[145px] max-w-[210px] bg-amber-50 border-amber-500 text-amber-950 font-medium ${data.isDimmed ? 'opacity-25' : 'hover:shadow-md'}`}>
      <NodeHandles />
      <div className="flex items-center justify-center gap-1 mb-0.5 text-[9px] uppercase tracking-wider text-amber-800 font-bold">
        <Phone className="h-3 w-3" /> Phone / CDR
      </div>
      <div className="text-neutral-900 font-bold text-xs leading-snug break-words px-1">{data.label}</div>
      <div className="text-[8px] text-amber-800/75 font-mono mt-0.5">Ref: {shortenId(id)}</div>
    </div>
  )
}

function CustomAccountNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3 py-2 rounded-xl border-2 shadow-sm text-center transition-all duration-200 min-w-[145px] max-w-[210px] bg-purple-50 border-purple-400 text-purple-950 font-medium ${data.isDimmed ? 'opacity-25' : 'hover:shadow-md'}`}>
      <NodeHandles />
      <div className="flex items-center justify-center gap-1 mb-0.5 text-[9px] uppercase tracking-wider text-purple-700 font-bold">
        <Landmark className="h-3 w-3" /> Account / TXN
      </div>
      <div className="text-neutral-900 font-bold text-xs leading-snug break-words px-1">{data.label}</div>
      <div className="text-[8px] text-purple-700/75 font-mono mt-0.5">Ref: {shortenId(id)}</div>
    </div>
  )
}

function CustomNeutralNode({ data, id }: { data: { label: string; isDimmed: boolean }; id: string }) {
  return (
    <div className={`px-3 py-2 rounded-xl border-2 border-slate-300 bg-slate-50 shadow-sm text-center transition-all duration-200 min-w-[135px] max-w-[200px] text-slate-800 ${data.isDimmed ? 'opacity-25' : 'hover:shadow-md'}`}>
      <NodeHandles />
      <div className="text-neutral-900 font-bold text-xs leading-snug break-words px-1">{data.label}</div>
      <div className="text-[8px] text-slate-500 font-mono">Ref: {shortenId(id)}</div>
    </div>
  )
}

const nodeTypes = {
  case: CustomCaseNode,
  person: CustomPersonNode,
  officer: CustomPersonNode,
  dependency: CustomDependencyNode,
  clock: CustomDependencyNode,
  evidence: CustomEvidenceNode,
  intelligencereport: CustomEvidenceNode,
  intelligence_report: CustomEvidenceNode,
  'intelligence-report': CustomEvidenceNode,
  intel: CustomEvidenceNode,
  report: CustomEvidenceNode,
  phone: CustomPhoneNode,
  account: CustomAccountNode,
  unit: CustomNeutralNode,
  act: CustomLawNode,
  section: CustomLawNode,
  court: CustomLawNode,
  location: CustomNeutralNode,
  crimehead: CustomLawNode,
  crimesubhead: CustomLawNode,
  'crime-head': CustomLawNode,
  crime_sub_head: CustomLawNode,
  default: CustomNeutralNode,
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
  const [layoutDensity, setLayoutDensity] = useState<'normal' | 'spacious' | 'extra-spacious'>('spacious')
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showLegend, setShowLegend] = useState(true)
  const [showInspector, setShowInspector] = useState(true)
  const [isPrinting, setIsPrinting] = useState(false)

  const containerRef = useRef<HTMLDivElement>(null)

  // Sync fullscreen state with ESC exits & trigger canvas re-fit
  useEffect(() => {
    const handleFsChange = () => {
      const fs = !!document.fullscreenElement
      setIsFullscreen(fs)
      setTimeout(() => {
        fitView({ duration: 300 })
      }, 150)
    }
    document.addEventListener('fullscreenchange', handleFsChange)
    return () => document.removeEventListener('fullscreenchange', handleFsChange)
  }, [fitView])

  // Re-fit canvas when user changes layout density
  useEffect(() => {
    const timer = setTimeout(() => {
      fitView({ duration: 350 })
    }, 100)
    return () => clearTimeout(timer)
  }, [layoutDensity, fitView])

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen().then(() => {
        setIsFullscreen(true)
        setTimeout(() => fitView({ duration: 300 }), 150)
      }).catch(() => {
        setIsFullscreen((prev) => !prev)
        setTimeout(() => fitView({ duration: 300 }), 150)
      })
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false)
        setTimeout(() => fitView({ duration: 300 }), 150)
      }).catch(() => {
        setIsFullscreen(false)
        setTimeout(() => fitView({ duration: 300 }), 150)
      })
    }
  }

  const handlePrint = () => {
    setIsPrinting(true)
    setTimeout(() => {
      window.print()
      setIsPrinting(false)
    }, 300)
  }

  // Grouping nodes by relation to Case with adaptive complexity scaling
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

    const isLawType = (n: NetworkNode) => ['act', 'section', 'court', 'crimehead', 'crimesubhead'].includes(n.type) || lawIds.has(n.id)
    const isEvidenceType = (n: NetworkNode) => ['evidence', 'intelligencereport', 'intelligence_report', 'intel', 'report'].includes(n.type) || evidenceIds.has(n.id)
    const isDependencyType = (n: NetworkNode) => ['dependency', 'clock', 'blocker'].includes(n.type) || dependencyIds.has(n.id)
    const isOfficerType = (n: NetworkNode) => ['officer', 'unit'].includes(n.type) || officerIds.has(n.id)
    const isPhoneOrAccount = (n: NetworkNode) => ['phone', 'account', 'bank', 'cdr', 'mobile'].includes(n.type)

    const victimsList = graphData.nodes.filter(n => victimIds.has(n.id))
    const accusedList = graphData.nodes.filter(n => accusedIds.has(n.id))
    const lawsList = graphData.nodes.filter(n => isLawType(n) && !accusedIds.has(n.id) && !victimIds.has(n.id))
    const evidenceList = graphData.nodes.filter(n => isEvidenceType(n) && !isLawType(n))
    const dependenciesList = graphData.nodes.filter(n => (isDependencyType(n) || isPhoneOrAccount(n)) && !accusedIds.has(n.id) && !victimIds.has(n.id))
    const officersList = graphData.nodes.filter(n => isOfficerType(n))
    const remainingList = graphData.nodes.filter(n => n.id !== primaryCaseId && !victimIds.has(n.id) && !accusedIds.has(n.id) && !isLawType(n) && !isEvidenceType(n) && !isDependencyType(n) && !isPhoneOrAccount(n) && !isOfficerType(n))

    const connectedIds = new Set<string>()
    const activeId = selectedEntityId
    if (activeId) {
      connectedIds.add(activeId)
      graphData.edges.forEach((edge) => {
        if (edge.source === activeId) connectedIds.add(edge.target)
        if (edge.target === activeId) connectedIds.add(edge.source)
      })
    }

    // Dynamic complexity scaling: expand distances automatically when graphs have more entities
    const totalNodes = graphData.nodes.length
    const autoScale = totalNodes > 14 ? 1.35 : totalNodes > 8 ? 1.15 : 1.0
    const userScale = layoutDensity === 'extra-spacious' ? 1.5 : layoutDensity === 'spacious' ? 1.25 : 0.95
    const scale = autoScale * userScale

    const colGap = Math.round(260 * scale)
    const rowGap = Math.round(145 * scale)
    const centerX = Math.round(620 * scale)
    const centerY = Math.round(320 * scale)

    return graphData.nodes.map((node) => {
      const isDimmed = activeId ? !connectedIds.has(node.id) : false
      
      // Compute logical, generous non-overlapping 2D coordinates
      let x: number
      let y: number

      if (node.id === primaryCaseId) {
        x = centerX
        y = centerY
      } else if (victimIds.has(node.id)) {
        const idx = victimsList.findIndex(n => n.id === node.id)
        x = centerX - Math.round((victimsList.length - 1) * 130) + idx * Math.round(260 * scale)
        y = Math.round(30 * scale)
      } else if (accusedIds.has(node.id)) {
        const idx = accusedList.findIndex(n => n.id === node.id)
        const col = idx % 2
        const row = Math.floor(idx / 2)
        x = centerX + Math.round(300 * scale) + col * colGap
        y = Math.round(30 * scale) + row * Math.round(rowGap * 0.9)
      } else if (isLawType(node)) {
        const idx = lawsList.findIndex(n => n.id === node.id)
        const col = idx % 2
        const row = Math.floor(idx / 2)
        x = 30 + col * colGap
        y = 30 + row * Math.round(rowGap * 0.85)
      } else if (isEvidenceType(node)) {
        const idx = evidenceList.findIndex(n => n.id === node.id)
        const col = idx % 2
        const row = Math.floor(idx / 2)
        x = 30 + col * colGap
        y = centerY + Math.round(40 * scale) + row * Math.round(rowGap * 0.85)
      } else if (isDependencyType(node) || isPhoneOrAccount(node)) {
        const idx = dependenciesList.findIndex(n => n.id === node.id)
        const col = idx % 2
        const row = Math.floor(idx / 2)
        x = centerX + Math.round(300 * scale) + col * colGap
        y = centerY + Math.round(180 * scale) + row * Math.round(rowGap * 0.9)
      } else if (isOfficerType(node)) {
        const idx = officersList.findIndex(n => n.id === node.id)
        const col = idx % 2
        const row = Math.floor(idx / 2)
        x = centerX - Math.round(140 * scale) + col * Math.round(colGap * 0.95)
        y = centerY + Math.round(260 * scale) + row * Math.round(rowGap * 0.85)
      } else {
        const idx = remainingList.findIndex(n => n.id === node.id)
        const col = idx % 2
        const row = Math.floor(idx / 2)
        x = centerX + Math.round(60 * scale) + col * colGap
        y = centerY + Math.round(260 * scale) + row * Math.round(rowGap * 0.85)
      }

      return {
        id: node.id,
        type: node.type,
        position: { x, y },
        data: { label: getNodeLabel(node), isDimmed },
        draggable: true,
      }
    })
  }, [graphData, selectedEntityId, layoutDensity])

  // Center canvas on selected node dynamically
  useEffect(() => {
    if (selectedEntityId) {
      const matchedNode = flowNodes.find(n => n.id === selectedEntityId)
      if (matchedNode) {
        setCenter(matchedNode.position.x + 80, matchedNode.position.y + 40, { zoom: 1.35, duration: 450 })
      }
    }
  }, [selectedEntityId, flowNodes, setCenter])

  // Map backend edge structure to React Flow Edge objects with smooth bending & always visible labels
  const flowEdges = useMemo<Edge[]>(() => {
    if (!graphData) return []

    return graphData.edges.map((edge) => {
      const isDashed = edge.label === 'CASE_HAS_DEPENDENCY' || edge.label.startsWith('INFERRED_')
      const isConnected = selectedEntityId ? (edge.source === selectedEntityId || edge.target === selectedEntityId) : true
      const isSelected = selectedEdgeId === edge.id || (selectedEntityId && (edge.source === selectedEntityId || edge.target === selectedEntityId))

      // Color coding for different edge types
      let baseColor = '#64748b'
      if (edge.label.includes('ACCUSED') || edge.label.includes('CO_ACCUSED')) baseColor = '#e11d48'
      else if (edge.label.includes('VICTIM')) baseColor = '#0284c7'
      else if (edge.label.includes('PHONE') || edge.label.includes('COMMUNICAT')) baseColor = '#d97706'
      else if (edge.label.includes('ACCOUNT') || edge.label.includes('OWNS')) baseColor = '#7c3aed'
      else if (edge.label.includes('TRANSFER') || edge.label.includes('TXN')) baseColor = '#059669'
      else if (edge.label.includes('DEPENDENCY')) baseColor = '#ea580c'
      else if (edge.label.includes('SECTION') || edge.label.includes('VIOLATED') || edge.label.includes('GOVERNED')) baseColor = '#4f46e5'

      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: 'smoothstep',
        label: edge.label ? edge.label.replaceAll('_', ' ') : undefined,
        labelStyle: { fill: '#0f172a', fontSize: 9.5, fontWeight: 700 },
        labelBgStyle: { fill: '#ffffff', stroke: baseColor, strokeWidth: 1.5, strokeOpacity: 0.95 },
        labelBgPadding: [6, 3] as [number, number],
        labelBgBorderRadius: 4,
        style: { 
          stroke: isSelected ? '#e11d48' : (isConnected ? baseColor : '#94a3b8'), 
          strokeWidth: isSelected ? 2.5 : (isConnected ? 2 : 1),
          strokeDasharray: isDashed ? '4,4' : undefined 
        },
        animated: isConnected && (edge.label === 'CASE_HAS_DEPENDENCY' || edge.label.includes('TRANSFER')),
      }
    })
  }, [graphData, selectedEntityId, selectedEdgeId])

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
      {/* Printable Paper Overlay (renders only when printing) */}
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
        <div className={`grid grid-cols-1 gap-4 ${isFullscreen ? 'flex-1 min-h-0 h-[calc(100vh-100px)]' : 'h-[580px]'} transition-all ${showInspector ? 'lg:grid-cols-4' : 'lg:grid-cols-1'}`}>
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

              <button 
                onClick={() => {
                  setLayoutDensity(prev => prev === 'spacious' ? 'extra-spacious' : prev === 'extra-spacious' ? 'normal' : 'spacious')
                }} 
                className={`p-1.5 hover:bg-neutral-100 rounded-radius-sm text-neutral-600 focus:outline-none flex items-center gap-1 px-2 text-[11px] font-semibold transition-colors ${layoutDensity !== 'normal' ? 'text-blue-700 bg-blue-50/90 font-bold' : ''}`} 
                title={`Spacing: ${layoutDensity} (Click to expand or tighten diagram)`}
              >
                <Move className="h-3.5 w-3.5" />
                <span>{layoutDensity === 'extra-spacious' ? 'Spacing: Extra Wide' : layoutDensity === 'spacious' ? 'Spacing: Expanded' : 'Spacing: Compact'}</span>
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
