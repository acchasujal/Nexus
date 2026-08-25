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
        const rawProps = (typeof e.properties === 'object' && e.properties ? e.properties : {}) as Record<string, unknown>
        const rawProv = (typeof e.provenance === 'object' && e.provenance ? e.provenance : {}) as Record<string, unknown>
        
        let edgeLabel = String(e.edge_type || e.label || '')
        
        // Enrich generic CONNECTED_TO edges with specific telecommunication / interaction metadata
        if (edgeLabel === 'CONNECTED_TO' || edgeLabel === 'connected_to') {
          if (rawProps.channel === 'VOICE_CALL' || String(e.id).includes('call') || rawProv.source_type === 'CDR' || rawProv.derivation_method === 'CALL_RECORD') {
            const count = rawProps.call_count ? ` (${rawProps.call_count})` : ''
            edgeLabel = `CDR_CALLS${count}`
          } else if (rawProps.channel === 'SMS') {
            edgeLabel = 'SMS_CONTACT'
          } else if (rawProps.amount) {
            edgeLabel = `BANK_TXN`
          } else {
            edgeLabel = 'COMMUNICATED_WITH'
          }
        }

        // Generate human-readable reason why they are connected
        let reason = 'Evidentiary link in investigation'
        if (rawProv.extracted_fact) {
          reason = String(rawProv.extracted_fact)
        } else if (edgeLabel.includes('ACCUSED') || edgeLabel.includes('CO_ACCUSED')) {
          reason = rawProps.role ? String(rawProps.role) : 'Named as accused in case complaint'
        } else if (edgeLabel.includes('VICTIM')) {
          reason = 'Complainant / victim in FIR statement'
        } else if (edgeLabel.includes('CDR') || edgeLabel.includes('CALL') || edgeLabel.includes('PHONE') || edgeLabel.includes('COMMUNICAT')) {
          if (rawProps.call_count) {
            reason = `${rawProps.call_count} voice calls logged in CDR`
          } else if (rawProps.channel) {
            reason = `${String(rawProps.channel).replace('_', ' ')} logged in records`
          } else {
            reason = 'Telecommunication interaction logged'
          }
        } else if (edgeLabel.includes('TRANSFER') || edgeLabel.includes('TXN')) {
          if (rawProps.amount) {
            reason = `₹${Number(rawProps.amount).toLocaleString('en-IN')} fund transfer`
          } else {
            reason = 'Bank transaction link'
          }
        } else if (edgeLabel.includes('ACCOUNT') || edgeLabel.includes('OWNS')) {
          reason = rawProps.bank ? `${rawProps.bank} account holder` : 'Bank account holder link'
        } else if (edgeLabel.includes('SECTION') || edgeLabel.includes('VIOLATED') || edgeLabel.includes('GOVERNED')) {
          reason = 'Governing penal section in charge'
        } else if (edgeLabel.includes('DEPENDENCY') || edgeLabel.includes('CLOCK')) {
          reason = 'Investigative statutory deadline / blocker'
        }

        const source = String(e.source_id || e.source || '')
        const target = String(e.target_id || e.target || '')
        return {
          id: String(e.id || `${source}-${target}`),
          source,
          target,
          label: edgeLabel,
          edge_type: edgeLabel,
          reason,
          properties: rawProps,
          provenance: rawProv,
          ...rawProps,
        }
      })

      return { nodes, edges }
    },
    enabled: Boolean(caseId),
    staleTime: 0,
  })
}
