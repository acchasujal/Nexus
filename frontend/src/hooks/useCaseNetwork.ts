import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'

export interface NetworkNode {
  id: string
  type: string
  label: string
  data: {
    label: string
    [key: string]: unknown
  }
  properties?: Record<string, unknown>
}

export interface NetworkEdge {
  id: string
  source: string
  target: string
  label: string
  edge_type?: string
  [key: string]: unknown
}

export interface NetworkResponse {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
}

export function useCaseNetwork(caseId?: string) {
  return useQuery<NetworkResponse>({
    queryKey: ['case-network', caseId],
    queryFn: async () => {
      const res = await apiFetch<Record<string, unknown>>(`/api/v1/network/cases/${caseId}`)
      const rawNodes = (res.nodes as Record<string, unknown>[] | undefined) ?? []
      const rawEdges = (res.edges as Record<string, unknown>[] | undefined) ?? []

      const nodes: NetworkNode[] = rawNodes.map((n) => {
        const props = (n.properties as Record<string, unknown>) || {}
        const rawLabel = String(n.label || (n.data as Record<string, unknown>)?.label || '')
        const looksLikeId = !rawLabel || rawLabel === n.id || rawLabel.startsWith('section-') || rawLabel.startsWith('evidence-') || rawLabel.startsWith('act-') || rawLabel.startsWith('intel-')
        const propLabel = String(
          props.section_number ||
          props.title ||
          props.full_name ||
          props.name ||
          props.fir_number ||
          props.evidence_number ||
          props.description ||
          ''
        )
        const nodeLabel = (looksLikeId && propLabel) ? propLabel : (rawLabel || propLabel || String(n.id))
        const nodeType = String(n.entity_type || n.type || 'entity').toLowerCase().replace(/[^a-z0-9]/g, '')
        return {
          id: String(n.id),
          type: nodeType,
          label: nodeLabel,
          data: {
            label: nodeLabel,
            ...(typeof n.data === 'object' && n.data ? (n.data as Record<string, unknown>) : {}),
            properties: props,
          },
          properties: props,
        }
      })

      const edges: NetworkEdge[] = rawEdges.map((e) => {
        const edgeLabel = String(e.edge_type || e.label || '')
        const source = String(e.source_id || e.source || '')
        const target = String(e.target_id || e.target || '')
        return {
          id: String(e.id || `${source}-${target}`),
          source,
          target,
          label: edgeLabel,
          edge_type: edgeLabel,
          ...(typeof e.properties === 'object' && e.properties ? (e.properties as Record<string, unknown>) : {}),
        }
      })

      return { nodes, edges }
    },
    enabled: Boolean(caseId),
    staleTime: 0,
  })
}
