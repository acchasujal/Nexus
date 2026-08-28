/**
 * frontend/src/lib/mocks/nexusHandlers.ts
 *
 * MSW handlers for the frozen M4 NEXUS prototype contract (/api/v1/nexus/*).
 */
import { http, HttpResponse, delay } from 'msw'
import type { ResolutionCandidate } from '@shared/contracts/api'
import {
  AFTER_EDGES, AFTER_NODES, BEFORE_EDGES, BEFORE_NODES, BRIDGE_LEAD,
  CANDIDATE_RC1, CANDIDATE_RC2, CANDIDATE_RC3, SNAPSHOT_DIFF, allSourceRecords, evidenceFor,
} from './nexusFixture'

interface NexusDemoState {
  candidates: ResolutionCandidate[]
  lead: typeof BRIDGE_LEAD
  decisionCount: number
}

const freshState = (): NexusDemoState => ({
  candidates: [
    structuredClone(CANDIDATE_RC1),
    structuredClone(CANDIDATE_RC2),
    structuredClone(CANDIDATE_RC3),
  ],
  lead: structuredClone(BRIDGE_LEAD),
  decisionCount: 0,
})

export const nexusState: { current: NexusDemoState } = { current: freshState() }

const isResolved = () => nexusState.current.candidates.some(c => c.status === 'CONFIRMED')

const networkFor = (snapshot: 'before' | 'after') => {
  const resolved = isResolved()
  const useAfter = snapshot === 'after' && resolved
  return {
    snapshot_id: useAfter ? SNAPSHOT_DIFF.after_snapshot_id : SNAPSHOT_DIFF.before_snapshot_id,
    state: useAfter ? ('after' as const) : ('before' as const),
    nodes: useAfter ? AFTER_NODES : BEFORE_NODES,
    edges: useAfter ? AFTER_EDGES : BEFORE_EDGES,
    total_nodes: (useAfter ? AFTER_NODES : BEFORE_NODES).length,
    total_edges: (useAfter ? AFTER_EDGES : BEFORE_EDGES).length,
  }
}

const isTest = typeof process !== 'undefined' && process.env.NODE_ENV === 'test'
const simDelay = async (ms: number) => {
  if (!isTest) await delay(ms)
}

export const nexusHandlers = [
  http.post(/\/api\/v1\/nexus\/ingest/, async () => {
    await simDelay(400)
    nexusState.current = freshState()
    return HttpResponse.json({
      batch_id: 'BATCH-2026-08-24',
      source_type: 'GOLDEN_FUSION',
      ingested_count: 3,
      extraction_summary: { persons: 6, phones: 3, accounts: 2, events: 1, relationships: 10 },
      snapshot_id: SNAPSHOT_DIFF.before_snapshot_id,
    })
  }),

  http.post(/\/api\/v1\/nexus\/demo\/reset/, async () => {
    nexusState.current = freshState()
    return HttpResponse.json({ status: 'reset' })
  }),

  http.get(/\/api\/v1\/nexus\/resolution\/candidates/, async () => {
    await simDelay(200)
    return HttpResponse.json(nexusState.current.candidates)
  }),

  http.post(/\/api\/v1\/nexus\/resolution\/([^/]+)\/decision/, async ({ params, request }) => {
    await simDelay(350)
    const id = params[0] as string
    const candidate = nexusState.current.candidates.find(c => c.id === id)
    if (!candidate) {
      return new HttpResponse(null, { status: 404, statusText: 'Candidate not found' })
    }
    const body = (await request.json()) as { decision: 'CONFIRM' | 'REJECT' | 'DEFER'; decided_by?: string }
    candidate.status =
      body.decision === 'CONFIRM' ? 'CONFIRMED' : body.decision === 'REJECT' ? 'REJECTED' : 'DEFERRED'
    candidate.decided_at = new Date().toISOString()
    candidate.decided_by = body.decided_by ?? 'Investigating Officer'
    nexusState.current.decisionCount += 1
    return HttpResponse.json({
      candidate_id: candidate.id,
      status: candidate.status,
      affected_node_ids: body.decision === 'CONFIRM' ? SNAPSHOT_DIFF.added_node_ids : [],
      new_snapshot_id: body.decision === 'CONFIRM' ? SNAPSHOT_DIFF.after_snapshot_id : undefined,
    })
  }),

  http.get(/\/api\/v1\/nexus\/network\/diff/, async () => {
    await simDelay(200)
    if (!isResolved()) {
      return HttpResponse.json(
        { detail: 'No diff available yet — confirm a resolution candidate first.' },
        { status: 409 },
      )
    }
    return HttpResponse.json(SNAPSHOT_DIFF)
  }),

  http.get(/\/api\/v1\/nexus\/network/, async ({ request }) => {
    await simDelay(250)
    const url = new URL(request.url)
    const snapshot = (url.searchParams.get('snapshot') ?? 'before') as 'before' | 'after'
    if (snapshot === 'after' && !isResolved()) {
      return HttpResponse.json(
        { detail: 'The "after" snapshot only exists after a resolution is confirmed.' },
        { status: 409 },
      )
    }
    return HttpResponse.json(networkFor(snapshot))
  }),

  http.get(/\/api\/v1\/nexus\/relationships\/([^/]+)\/evidence/, async ({ params }) => {
    await simDelay(150)
    const id = params[0] as string
    const evidence = evidenceFor(String(id))
    if (!evidence) {
      return HttpResponse.json(
        { detail: `Evidence chain for relationship ${String(id)} is unavailable in this snapshot.` },
        { status: 404 },
      )
    }
    return HttpResponse.json(evidence)
  }),

  http.get(/\/api\/v1\/nexus\/path/, async ({ request }) => {
    await simDelay(200)
    const url = new URL(request.url)
    const source = (url.searchParams.get('source') ?? '').trim()
    const target = (url.searchParams.get('target') ?? '').trim()
    const maxDepth = Number.parseInt(url.searchParams.get('max_depth') || '6', 10)

    if (!source || !target) {
      return HttpResponse.json({
        found: false,
        source_id: source,
        target_id: target,
        node_ids: [],
        edge_ids: [],
        hops: 0,
        explanation: 'Source and target entity identifiers are required.',
        evidence_ids: [],
      })
    }

    if (source === target) {
      return HttpResponse.json({
        found: false,
        source_id: source,
        target_id: target,
        node_ids: [source],
        edge_ids: [],
        hops: 0,
        explanation: `Source and target entities are identical ('${source}').`,
        evidence_ids: [],
      })
    }

    const net = networkFor(isResolved() ? 'after' : 'before')
    const nodesById = new Map(net.nodes.map((n) => [n.id, n]))

    const findNode = (val: string) => {
      if (nodesById.has(val)) return nodesById.get(val)
      const low = val.toLowerCase()
      for (const n of net.nodes) {
        if (n.id.toLowerCase() === low || n.label.toLowerCase() === low) return n
      }
      return null
    }

    const srcNode = findNode(source)
    const tgtNode = findNode(target)

    if (!srcNode) {
      return HttpResponse.json({
        found: false,
        source_id: source,
        target_id: target,
        node_ids: [],
        edge_ids: [],
        hops: 0,
        explanation: `Source entity '${source}' was not found in the active graph snapshot.`,
        evidence_ids: [],
      })
    }

    if (!tgtNode) {
      return HttpResponse.json({
        found: false,
        source_id: source,
        target_id: target,
        node_ids: [],
        edge_ids: [],
        hops: 0,
        explanation: `Target entity '${target}' was not found in the active graph snapshot.`,
        evidence_ids: [],
      })
    }

    // Golden path special explanation
    if (isResolved() && ((srcNode.id === 'CASE-141' && tgtNode.id === 'CASE-207') || (srcNode.id === 'CASE-207' && tgtNode.id === 'CASE-141'))) {
      return HttpResponse.json({
        found: true,
        source_id: srcNode.id,
        target_id: tgtNode.id,
        node_ids: ['CASE-141', 'P-RAFIQ', 'CASE-207'],
        edge_ids: ['E-ACCUSE-141', 'E-ACCUSE-207'],
        hops: 2,
        explanation:
          'FIR 141/2026 and FIR 207/2026 are connected through the confirmed entity ' +
          '"Rafiq Khan / Rafiq Ahmed" (candidate RC-1), accused in both cases and reachable on phone +91 98450 11223 in both CDR pulls.',
        evidence_ids: ['SRC-FIR-141', 'SRC-FIR-207', 'SRC-CDR-A12', 'SRC-CDR-B31'],
      })
    }

    // Bidirectional Adjacency
    const adj = new Map<string, { to: string; edgeId: string; edgeType: string; evs: string[] }[]>()
    for (const e of net.edges) {
      const evList = (Array.isArray(e.properties?.evidence_ids) ? e.properties.evidence_ids : []) as string[]
      if (!adj.has(e.source_id)) adj.set(e.source_id, [])
      if (!adj.has(e.target_id)) adj.set(e.target_id, [])
      adj.get(e.source_id)!.push({ to: e.target_id, edgeId: e.id, edgeType: e.edge_type, evs: evList })
      adj.get(e.target_id)!.push({ to: e.source_id, edgeId: e.id, edgeType: e.edge_type, evs: evList })
    }

    // BFS
    const queue: { curr: string; pathNodes: string[]; pathEdges: string[]; pathEvs: string[] }[] = [
      { curr: srcNode.id, pathNodes: [srcNode.id], pathEdges: [], pathEvs: [] },
    ]
    const visited = new Set<string>([srcNode.id])
    let foundPath: { pathNodes: string[]; pathEdges: string[]; pathEvs: string[] } | null = null

    while (queue.length > 0) {
      const { curr, pathNodes, pathEdges, pathEvs } = queue.shift()!
      if (pathNodes.length - 1 >= maxDepth) continue

      for (const { to, edgeId, evs } of adj.get(curr) || []) {
        if (visited.has(to)) continue
        const nextNodes = [...pathNodes, to]
        const nextEdges = [...pathEdges, edgeId]
        const nextEvs = [...pathEvs, ...evs]

        if (to === tgtNode.id) {
          foundPath = { pathNodes: nextNodes, pathEdges: nextEdges, pathEvs: nextEvs }
          break
        }

        visited.add(to)
        queue.push({ curr: to, pathNodes: nextNodes, pathEdges: nextEdges, pathEvs: nextEvs })
      }
      if (foundPath) break
    }

    if (foundPath) {
      const hops = foundPath.pathNodes.length - 1
      const labels = foundPath.pathNodes.map((id) => nodesById.get(id)?.label || id)
      return HttpResponse.json({
        found: true,
        source_id: srcNode.id,
        target_id: tgtNode.id,
        node_ids: foundPath.pathNodes,
        edge_ids: foundPath.pathEdges,
        hops,
        explanation: `Discovered ${hops}-hop evidence connection: ${labels.join(' ➔ ')}.`,
        evidence_ids: [...new Set(foundPath.pathEvs)],
      })
    }

    return HttpResponse.json({
      found: false,
      source_id: srcNode.id,
      target_id: tgtNode.id,
      node_ids: [],
      edge_ids: [],
      hops: 0,
      explanation: isResolved()
        ? `No connection found between '${srcNode.label}' and '${tgtNode.label}' within ${maxDepth} hops in the current snapshot.`
        : 'No connection exists in the current snapshot. Confirm pending entity resolutions to reveal hidden links.',
      evidence_ids: [],
    })
  }),

  http.get(/\/api\/v1\/nexus\/leads/, async () => {
    await simDelay(200)
    return HttpResponse.json(isResolved() ? [nexusState.current.lead] : [])
  }),

  http.post(/\/api\/v1\/nexus\/leads\/([^/]+)\/decision/, async ({ params, request }) => {
    await simDelay(300)
    const id = params[0] as string
    if (id !== nexusState.current.lead.id) {
      return new HttpResponse(null, { status: 404, statusText: 'Lead not found' })
    }
    const body = (await request.json()) as { decision: 'ACCEPT' | 'REJECT'; decided_by?: string; note?: string }
    nexusState.current.lead.status = body.decision === 'ACCEPT' ? 'ACCEPTED' : 'REJECTED'
    nexusState.current.lead.decided_at = new Date().toISOString()
    nexusState.current.lead.decided_by = body.decided_by ?? 'Investigating Officer'
    nexusState.current.lead.decision_note = body.note
    return HttpResponse.json(nexusState.current.lead)
  }),

  http.post(/\/api\/v1\/nexus\/copilot\/query/, async ({ request }) => {
    await simDelay(500)
    const body = (await request.json()) as { query: string }
    const q = (body.query ?? '').toLowerCase()
    if (/(guilt|guilty|criminal|mastermind|convict|punish)/.test(q)) {
      return HttpResponse.json({
        query: body.query,
        answer: 'I cannot infer guilt, innocence, or risk of reoffending. These are matters of judicial determination.',
        is_refusal: true,
        refusal_reason: 'Deterministic refusal gate: predictive guilt scoring is prohibited.',
        evidence_ids: [],
        reasoning_path: [],
        suggested_actions: ['View confirmed phone call logs', 'Examine bank transfer chains'],
        grounded_citations: [],
      })
    }
    if (/(connect|link|bridge|relat)/.test(q)) {
      return HttpResponse.json({
        query: body.query,
        answer: isResolved()
          ? 'FIR 141/2026 and FIR 207/2026 connect through the confirmed alias "Rafiq Khan / Rafiq Ahmed": ' +
            'same phone +91 98450 11223 in both CDR pulls, same father\'s name in both FIRs, and repeated transfers ' +
            'from ACC-9914 (Deepak Rao) into ACC-7731 held by Rafiq.'
          : 'No connection is currently visible. There is one pending entity-resolution candidate (RC-1) that, if confirmed, may link the two cases.',
        is_refusal: false,
        evidence_ids: isResolved()
          ? ['SRC-FIR-141', 'SRC-FIR-207', 'SRC-CDR-A12', 'SRC-CDR-B31', 'SRC-TXN-55']
          : ['SRC-FIR-141', 'SRC-FIR-207'],
        reasoning_path: isResolved()
          ? [
              'Entity resolution RC-1 CONFIRMED → person unified (P-RAFIQ)',
              'P-RAFIQ —ACCUSED_IN→ CASE-141 and CASE-207',
              'ACC-9914 —TRANSFERRED_TO→ ACC-7731 (2 transactions)',
            ]
          : ['Resolution candidate RC-1 status: PENDING'],
        grounded_citations: [
          { source_type: 'FIR', source_id: 'SRC-FIR-141', fact: 'FIR 141/2026 record', confidence: 1.0 },
          { source_type: 'FIR', source_id: 'SRC-FIR-207', fact: 'FIR 207/2026 record', confidence: 1.0 },
        ],
        suggested_actions: ['Expand 2-hop neighborhood', 'Inspect telephone call logs'],
      })
    }
    if (/(608|case-0031|arms trafficking)/.test(q) || (/(tell me about|summarize)/.test(q) && /(fir|case)/.test(q))) {
      return HttpResponse.json({
        query: body.query,
        answer:
          'CASE BRIEF: FIR-2026-608\n' +
          '────────────────────────────────────────────────\n' +
          'Offence / Title: Illegal Arms Trafficking (Investigation into Illegal Arms Trafficking at Belagavi)\n' +
          'Jurisdiction: Koramangala PS, Belagavi\n' +
          'Status: OPEN\n\n' +
          'Summary:\nCase registered regarding suspected illegal arms trafficking involving syndicates in Belagavi.\n\n' +
          'Accused / Suspects (2):\n• Rahul Chauhan — Phone: 9846361787, Vehicle: KA-20-IH-2976, ID: ID-661894\n• Vijay Khan — Phone: 9876543210\n\n' +
          'Indexed Evidence (1):\n• EV-2026-7955 (CDR_RECORD): Evidentiary material seized for FIR-2026-608',
        is_refusal: false,
        evidence_ids: ['EV-2026-7955', 'SRC-FIR-FIR-2026-608'],
        reasoning_path: [
          'Case index match: FIR-2026-608 (case-0031)',
          'Jurisdiction: Koramangala PS, Belagavi',
          'Person Rahul Chauhan registered as accused in FIR-2026-608',
        ],
        grounded_citations: [
          { source_type: 'PERSON', source_id: 'person-0060', fact: 'Accused in FIR-2026-608: Rahul Chauhan', confidence: 1.0 },
          { source_type: 'EVIDENCE', source_id: 'EV-2026-7955', fact: 'Evidence EV-2026-7955 (CDR_RECORD) logged under FIR-2026-608', confidence: 1.0 },
          { source_type: 'FIR', source_id: 'FIR-2026-608', fact: 'FIR registered at Koramangala PS, Belagavi', confidence: 1.0 },
        ],
        suggested_actions: ['Open Case Details', 'View Case Network', 'Inspect Accused', 'View Timeline', 'View Evidence'],
        case_id: 'case-0031',
      })
    }
    return HttpResponse.json({
      query: body.query,
      answer: 'This query was parsed against the investigation graph. Ask "How are the two cases connected?" for the grounded connection explanation.',
      is_refusal: false,
      evidence_ids: [],
      reasoning_path: ['Intent: general_info — no specific graph claim to ground'],
      grounded_citations: [],
      suggested_actions: ['Ask about suspect connections', 'Trace financial flows'],
    })
  }),

  http.get(/\/api\/v1\/nexus\/search/, async ({ request }) => {
    await simDelay(150)
    const url = new URL(request.url)
    const q = (url.searchParams.get('q') ?? '').trim()
    const qLower = q.toLowerCase()
    if (!q) return HttpResponse.json({ query: '', cases: [], entities: [] })
    const normQ = qLower.replace(/[^\w]/g, '')
    const nodes = isResolved() ? AFTER_NODES : BEFORE_NODES

    const matchesNode = (n: (typeof nodes)[0]) => {
      if (n.label.toLowerCase().includes(qLower)) return true
      if (Object.values(n.properties).some((v) => String(v).toLowerCase().includes(qLower))) return true
      if (normQ && normQ.length >= 2) {
        if (n.label.toLowerCase().replace(/[^\w]/g, '').includes(normQ)) return true
        if (Object.values(n.properties).some((v) => String(v).toLowerCase().replace(/[^\w]/g, '').includes(normQ))) return true
      }
      return false
    }

    const buildSubtext = (n: (typeof nodes)[0]) => {
      const props = n.properties || {}
      const etype = n.entity_type
      const caseInfo = n.case_ids?.length ? ` • FIR: ${n.case_ids.join(', ')}` : ''
      if (etype === 'Phone') {
        const num = props.number || props.phone || n.label
        return `Phone: ${num}${props.seen_in ? ` (${props.seen_in})` : ''}${caseInfo}`
      }
      if (etype === 'Account') {
        const parts = [props.holder ? `Holder: ${props.holder}` : null, props.bank].filter(Boolean)
        return `${parts.length ? parts.join(' • ') : 'Bank Account'}${caseInfo}`
      }
      if (etype === 'Person') {
        const parts = [props.role, props.phone ? `Phone: ${props.phone}` : null].filter(Boolean)
        return `${parts.length ? parts.join(' • ') : 'Person'}${caseInfo}`
      }
      if (etype === 'Vehicle') {
        const parts = [props.registration ? `Reg: ${props.registration}` : null, props.owner ? `Owner: ${props.owner}` : null].filter(Boolean)
        return `${parts.length ? parts.join(' • ') : 'Vehicle'}${caseInfo}`
      }
      return (props.description || props.role || etype) + caseInfo
    }

    const cases = nodes
      .filter((n) => n.entity_type === 'Case' && matchesNode(n))
      .map((n) => ({ id: n.id, fir_number: String(n.properties.fir_number ?? ''), title: n.label, score: 1 }))

    const entities = nodes
      .filter((n) => n.entity_type !== 'Case' && matchesNode(n))
      .map((n) => ({
        id: n.id,
        label: n.label,
        entity_type: n.entity_type,
        case_ids: n.case_ids,
        score: 1,
        subtext: buildSubtext(n),
      }))

    return HttpResponse.json({ query: q, cases, entities })
  }),

  http.get(/\/api\/v1\/nexus\/sources\/([^/]+)/, async ({ params }) => {
    const id = params[0] as string
    const record = allSourceRecords[String(id)]
    if (!record) return new HttpResponse(null, { status: 404, statusText: 'Source record not found' })
    return HttpResponse.json(record)
  }),

  http.get(/\/api\/v1\/investigations\/([^/]+)/, async ({ params }) => {
    const id = String(params[0])
    return HttpResponse.json({
      id,
      fir_number: id === 'CASE-207' ? 'FIR 207/2026' : `FIR ${id}`,
      title: id === 'CASE-207' ? 'FIR 207/2026: Cyber Financial Layering' : `Investigation ${id}`,
      station_name: 'Cyber Crime PS, Bengaluru',
      district: 'Bengaluru',
      offence_category: 'Cyber Financial Fraud',
      incident_date: '2026-03-02T14:15:00Z',
      status: 'UNDER_INVESTIGATION',
      summary: 'Cross-district investigation tracking mule bank networks and forged credentials.',
      sections: ['Section 66D IT Act', 'Section 318(4) BNS'],
      accused: [
        {
          id: 'P-DEEPAK',
          name: 'Deepak Khan',
          full_name: 'Deepak Khan',
          phone_number: '9884045292',
          phone: '9884045292',
          vehicle_number: 'KA-46-NR-1158',
          vehicle: 'KA-46-NR-1158',
          address_text: 'MG Road, Bengaluru',
        },
        {
          id: 'P-RAFIQ-A',
          name: 'Rafiq Ahmed',
          full_name: 'Rafiq Ahmed',
          phone_number: '+91 98450 11223',
          phone: '+91 98450 11223',
        },
      ],
      victims: [],
      evidence: [],
      updated_at: '2026-08-24T10:00:00Z',
    })
  }),

  http.post(/\/api\/v1\/entity-resolution\/resolve/, async ({ request }) => {
    const body = (await request.json()) as any
    return HttpResponse.json({
      query: body,
      matches: [],
      total_matches: 0,
    })
  }),
]
