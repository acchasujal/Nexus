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

export const isResolved = () => nexusState.current.candidates.some(c => c.status === 'CONFIRMED')

const CANDIDATE_DELTAS: Record<string, {
  beforeNodeIds: string[]
  afterNodeIds: string[]
  beforeEdgeIds: string[]
  afterEdgeIds: string[]
}> = {
  'RC-1': {
    beforeNodeIds: ['P-RAFIQ-K', 'P-RAFIQ-A', 'PH-A', 'PH-B'],
    afterNodeIds: ['P-RAFIQ', 'PH-UNIFIED'],
    beforeEdgeIds: ['E-USEPH-A', 'E-USEPH-B'],
    afterEdgeIds: ['E-USEPH-1', 'E-USEPH-2', 'E-COMM-DK', 'E-BRIDGE'],
  },
  'RC-2': {
    beforeNodeIds: ['P-VIKRAM-S', 'P-BIKRAM-S'],
    afterNodeIds: ['P-VIKRAM'],
    beforeEdgeIds: ['E-ACCUSE-305', 'E-ACCUSE-412', 'E-OWN-4491'],
    afterEdgeIds: ['E-ACCUSE-305-A', 'E-ACCUSE-412-A', 'E-OWN-4491-A', 'E-BRIDGE-2'],
  },
  'RC-3': {
    beforeNodeIds: ['P-SUNIEL-S', 'P-SUNIL-S'],
    afterNodeIds: ['P-SUNIEL'],
    beforeEdgeIds: ['E-ACCUSE-501', 'E-ACCUSE-502', 'E-VEH-501', 'E-VEH-502'],
    afterEdgeIds: ['E-ACCUSE-501-A', 'E-ACCUSE-502-A', 'E-VEH-UNIFIED', 'E-BRIDGE-3'],
  },
}

export function getDynamicDiff(): SnapshotDiffResponse {
  const confirmed = nexusState.current.candidates.filter(c => c.status === 'CONFIRMED')
  const addedNodes: string[] = []
  const removedNodes: string[] = []
  const addedEdges: string[] = []
  const removedEdges: string[] = []

  for (const c of confirmed) {
    const delta = CANDIDATE_DELTAS[c.id]
    if (delta) {
      addedNodes.push(...delta.afterNodeIds)
      removedNodes.push(...delta.beforeNodeIds)
      addedEdges.push(...delta.afterEdgeIds)
      removedEdges.push(...delta.beforeEdgeIds)
    }
  }

  if (confirmed.length === 0) {
    return SNAPSHOT_DIFF
  }

  return {
    before_snapshot_id: 'SNAP-BEFORE-001',
    after_snapshot_id: `SNAP-AFTER-${confirmed.map(c => c.id).join('-')}`,
    added_node_ids: Array.from(new Set(addedNodes)),
    removed_node_ids: Array.from(new Set(removedNodes)),
    changed_node_ids: [],
    added_edge_ids: Array.from(new Set(addedEdges)),
    removed_edge_ids: Array.from(new Set(removedEdges)),
    changed_edge_ids: [],
  }
}

const networkFor = (snapshot: 'before' | 'after') => {
  const resolved = isResolved()
  const useAfter = snapshot === 'after' && resolved

  if (!useAfter) {
    return {
      snapshot_id: SNAPSHOT_DIFF.before_snapshot_id,
      state: 'before' as const,
      nodes: BEFORE_NODES,
      edges: BEFORE_EDGES,
      total_nodes: BEFORE_NODES.length,
      total_edges: BEFORE_EDGES.length,
    }
  }

  const diff = getDynamicDiff()
  const removedNodeSet = new Set(diff.removed_node_ids)
  const removedEdgeSet = new Set(diff.removed_edge_ids)
  const addedNodeSet = new Set(diff.added_node_ids)
  const addedEdgeSet = new Set(diff.added_edge_ids)

  // Start with before nodes, remove merged nodes, and add unified nodes
  const nodes = [
    ...BEFORE_NODES.filter(n => !removedNodeSet.has(n.id)),
    ...AFTER_NODES.filter(n => addedNodeSet.has(n.id)),
  ]

  // For edges: remove old edges, and include relevant after edges
  const edges = [
    ...BEFORE_EDGES.filter(e => !removedEdgeSet.has(e.id)),
    ...AFTER_EDGES.filter(e => addedEdgeSet.has(e.id)),
  ]

  // Also rewire edges for confirmed candidates (e.g. E-ACCUSE-141 to P-RAFIQ)
  const isRc1Confirmed = nexusState.current.candidates.find(c => c.id === 'RC-1')?.status === 'CONFIRMED'
  if (isRc1Confirmed) {
    for (let i = 0; i < edges.length; i++) {
      if (edges[i].id === 'E-ACCUSE-141' || edges[i].id === 'E-OWN-7731') {
        edges[i] = { ...edges[i], source_id: 'P-RAFIQ' }
      }
      if (edges[i].id === 'E-ACCUSE-207') {
        edges[i] = { ...edges[i], source_id: 'P-RAFIQ' }
      }
    }
  }

  return {
    snapshot_id: diff.after_snapshot_id,
    state: 'after' as const,
    nodes,
    edges,
    total_nodes: nodes.length,
    total_edges: edges.length,
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
    const diff = getDynamicDiff()
    return HttpResponse.json({
      candidate_id: candidate.id,
      status: candidate.status,
      affected_node_ids: body.decision === 'CONFIRM' ? (CANDIDATE_DELTAS[id]?.afterNodeIds ?? diff.added_node_ids) : [],
      new_snapshot_id: body.decision === 'CONFIRM' ? diff.after_snapshot_id : undefined,
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
    return HttpResponse.json(getDynamicDiff())
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

    // Dynamic mock path for Sunil Shetty <-> Sunil Gupta
    if (
      (source === 'person-0040' && target === 'person-0037') ||
      (source === 'person-0037' && target === 'person-0040')
    ) {
      const srcId = source
      const tgtId = target
      const isForward = srcId === 'person-0040'
      const nodes = isForward ? ['person-0040', 'person-0037'] : ['person-0037', 'person-0040']
      const labels = isForward ? ['Sunil Shetty', 'Sunil Gupta'] : ['Sunil Gupta', 'Sunil Shetty']
      return HttpResponse.json({
        found: true,
        source_id: srcId,
        target_id: tgtId,
        node_ids: nodes,
        edge_ids: ['e-40-37'],
        hops: 1,
        explanation: `Discovered 1-hop evidence connection: ${labels.join(' ➔ ')}.`,
        evidence_ids: ['EV-2026-4037'],
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
      const isCandidateConfirmed = nexusState.current.candidates.find(c => c.id === 'RC-1')?.status === 'CONFIRMED'
      if (isCandidateConfirmed) {
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
    }

    if (isResolved() && ((srcNode.id === 'CASE-305' && tgtNode.id === 'CASE-412') || (srcNode.id === 'CASE-412' && tgtNode.id === 'CASE-305'))) {
      const isCandidateConfirmed = nexusState.current.candidates.find(c => c.id === 'RC-2')?.status === 'CONFIRMED'
      if (isCandidateConfirmed) {
        return HttpResponse.json({
          found: true,
          source_id: srcNode.id,
          target_id: tgtNode.id,
          node_ids: ['CASE-305', 'P-VIKRAM', 'CASE-412'],
          edge_ids: ['E-ACCUSE-305-A', 'E-ACCUSE-412-A'],
          hops: 2,
          explanation:
            'FIR 305/2026 (Cyber Fraud) and FIR 412/2026 (Hawala Syndicate) are connected through the confirmed entity ' +
            '"Vikram Sharma / Bikram Sarma" (candidate RC-2), sharing Aadhaar suffix XXXX-XXXX-4491 and mobile +91 98450 77310 across Bengaluru jurisdictions.',
          evidence_ids: ['SRC-FIR-305', 'SRC-FIR-412'],
        })
      }
    }

    if (isResolved() && ((srcNode.id === 'CASE-501' && tgtNode.id === 'CASE-502') || (srcNode.id === 'CASE-502' && tgtNode.id === 'CASE-501'))) {
      const isCandidateConfirmed = nexusState.current.candidates.find(c => c.id === 'RC-3')?.status === 'CONFIRMED'
      if (isCandidateConfirmed) {
        return HttpResponse.json({
          found: true,
          source_id: srcNode.id,
          target_id: tgtNode.id,
          node_ids: ['CASE-501', 'P-SUNIEL', 'CASE-502'],
          edge_ids: ['E-ACCUSE-501-A', 'E-ACCUSE-502-A'],
          hops: 2,
          explanation:
            'FIR 501/2026 (Narcotics Ring) and FIR 502/2026 (Extortion & Logistics) are connected through the confirmed entity ' +
            '"Suniel Shetty / Sunil Shetty" (candidate RC-3), matching vehicle registration KA-01-AB-1001 and father name R. Shetty across both seizure reports.',
          evidence_ids: ['SRC-FIR-501', 'SRC-FIR-502'],
        })
      }
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

    const buildSubtext = (n: { entity_type: string; label: string; properties?: Record<string, unknown>; case_ids?: string[] }) => {
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

    const additionalMockNodes = [
      {
        id: 'person-0073',
        entity_type: 'Person',
        label: 'Vinod Sharma',
        case_ids: ['case-0049'],
        properties: { full_name: 'Vinod Sharma', role: 'Hawala Courier', district: 'Bengaluru' },
      },
      {
        id: 'person-0051',
        entity_type: 'Person',
        label: 'Ramesh Hegde',
        case_ids: ['case-0001', 'case-0049'],
        properties: { full_name: 'Ramesh Hegde', role: 'The Broker', district: 'Bengaluru' },
      },
      {
        id: 'person-0011',
        entity_type: 'Person',
        label: 'Praveen Iyer',
        case_ids: ['case-0001'],
        properties: { full_name: 'Praveen Iyer', role: 'Syndicate Lead', district: 'Mangaluru' },
      },
      {
        id: 'case-0001',
        entity_type: 'Case',
        label: 'FIR-2026-101 — Narcotics Trafficking',
        case_ids: ['case-0001'],
        properties: { fir_number: 'FIR-2026-101', title: 'Narcotics Trafficking & Money Laundering' },
      },
      {
        id: 'person-0040',
        entity_type: 'Person',
        label: 'Sunil Shetty',
        case_ids: ['case-0040'],
        properties: { full_name: 'Sunil Shetty', role: 'Suspect', district: 'Bengaluru' },
      },
      {
        id: 'person-0037',
        entity_type: 'Person',
        label: 'Sunil Gupta',
        case_ids: ['case-0040'],
        properties: { full_name: 'Sunil Gupta', role: 'Associate', district: 'Bengaluru' },
      },
      {
        id: 'case-0049',
        entity_type: 'Case',
        label: 'FIR-2026-984 — Extortion',
        case_ids: ['case-0049'],
        properties: { fir_number: 'FIR-2026-984', title: 'Extortion & Hawala Transport' },
      },
    ]

    const allCandidateNodes = [...nodes, ...additionalMockNodes]

    const matchesCandidate = (n: (typeof allCandidateNodes)[0]) => {
      if (n.label.toLowerCase().includes(qLower)) return true
      if (Object.values(n.properties).some((v) => String(v).toLowerCase().includes(qLower))) return true
      if (normQ && normQ.length >= 2) {
        if (n.label.toLowerCase().replace(/[^\w]/g, '').includes(normQ)) return true
        if (Object.values(n.properties).some((v) => String(v).toLowerCase().replace(/[^\w]/g, '').includes(normQ))) return true
      }
      return false
    }

    const cases = allCandidateNodes
      .filter((n) => n.entity_type === 'Case' && matchesCandidate(n))
      .map((n) => ({ id: n.id, fir_number: String(n.properties.fir_number ?? ''), title: n.label, score: 1 }))

    const entities = allCandidateNodes
      .filter((n) => n.entity_type !== 'Case' && matchesCandidate(n))
      .map((n) => ({
        id: n.id,
        label: n.label,
        entity_type: n.entity_type,
        case_ids: n.case_ids,
        score: 1,
        subtext: buildSubtext(n as any),
      }))

    return HttpResponse.json({ query: q, cases, entities })
  }),

  http.get(/\/api\/v1\/nexus\/sources\/([^/]+)/, async ({ request }) => {
    const match = new URL(request.url).pathname.match(/\/api\/v1\/nexus\/sources\/([^/]+)/)
    const id = match ? decodeURIComponent(match[1]) : ''
    const record = allSourceRecords[id]
    if (!record) return new HttpResponse(null, { status: 404, statusText: 'Source record not found' })
    return HttpResponse.json(record)
  }),

  http.get(/\/api\/v1\/entities\/([^/]+)\/network/, async ({ request }) => {
    const match = new URL(request.url).pathname.match(/\/api\/v1\/entities\/([^/]+)\/network/)
    const id = match ? decodeURIComponent(match[1]) : ''
    if (id === 'empty-entity' || id === 'non-existent') {
      return HttpResponse.json({ nodes: [], edges: [], total_nodes: 0, total_edges: 0 })
    }
    if (id === 'person-0073') {
      return HttpResponse.json({
        nodes: [
          {
            id: 'person-0073',
            entity_type: 'Person',
            label: 'Vinod Sharma',
            properties: { full_name: 'Vinod Sharma', role: 'Hawala Courier', district: 'Bengaluru', case_id: 'case-0049' },
            degree: 2,
            confidence: 1.0,
          },
          {
            id: 'phone-0073',
            entity_type: 'Phone',
            label: '+91 98450 77889',
            properties: { phone_number: '+91 98450 77889', subscriber: 'Vinod Sharma', case_id: 'case-0049' },
            degree: 1,
            confidence: 1.0,
          },
          {
            id: 'case-0049',
            entity_type: 'Case',
            label: 'FIR-2026-984 — Extortion',
            properties: { fir_number: 'FIR-2026-984', title: 'Extortion & Hawala Transport' },
            degree: 1,
            confidence: 1.0,
          },
        ],
        edges: [
          {
            id: 'e-vinod-phone',
            source_id: 'person-0073',
            target_id: 'phone-0073',
            edge_type: 'USES_PHONE',
            weight: 1.0,
            provenance: {
              source_type: 'CDR',
              source_id: 'CDR-2026-073',
              timestamp: '2026-03-01T10:00:00Z',
              extracted_fact: 'Subscribed phone in Vinod Sharma name',
              derivation_method: 'DIRECT',
              confidence: 1.0,
            },
            properties: { case_id: 'case-0049' },
          },
          {
            id: 'e-vinod-case',
            source_id: 'person-0073',
            target_id: 'case-0049',
            edge_type: 'ACCUSED_IN',
            weight: 1.0,
            provenance: {
              source_type: 'FIR',
              source_id: 'FIR-2026-984',
              timestamp: '2026-03-02T12:00:00Z',
              extracted_fact: 'Named accused in FIR 2026/984',
              derivation_method: 'DIRECT',
              confidence: 1.0,
            },
            properties: { case_id: 'case-0049' },
          },
        ],
        total_nodes: 3,
        total_edges: 2,
      })
    }
    if (id === 'person-0040' || id === 'person-0037') {
      return HttpResponse.json({
        nodes: [
          {
            id: 'person-0040',
            entity_type: 'Person',
            label: 'Sunil Shetty',
            properties: { full_name: 'Sunil Shetty', role: 'Suspect', district: 'Bengaluru' },
            degree: 1,
            confidence: 1.0,
          },
          {
            id: 'person-0037',
            entity_type: 'Person',
            label: 'Sunil Gupta',
            properties: { full_name: 'Sunil Gupta', role: 'Associate', district: 'Bengaluru' },
            degree: 1,
            confidence: 1.0,
          },
        ],
        edges: [
          {
            id: 'e-40-37',
            source_id: 'person-0040',
            target_id: 'person-0037',
            edge_type: 'CONNECTED_TO',
            weight: 1.0,
            provenance: {
              source_type: 'INTEL_REPORT',
              source_id: 'INTEL-2026-4037',
              timestamp: '2026-03-01T10:00:00Z',
              extracted_fact: 'Direct financial connection between Sunil Shetty and Sunil Gupta',
              derivation_method: 'DIRECT',
              confidence: 1.0,
            },
            properties: {},
          },
        ],
        total_nodes: 2,
        total_edges: 1,
      })
    }

    // Default mock neighborhood for other entities
    return HttpResponse.json({
      nodes: [
        {
          id,
          entity_type: 'Person',
          label: id,
          properties: { id },
          degree: 1,
          confidence: 1.0,
        },
      ],
      edges: [],
      total_nodes: 1,
      total_edges: 0,
    })
  }),

  http.get(/\/api\/v1\/network\/cases\/([^/]+)/, async ({ request }) => {
    const match = new URL(request.url).pathname.match(/\/api\/v1\/network\/cases\/([^/]+)/)
    const id = match ? decodeURIComponent(match[1]) : ''
    return HttpResponse.json({
      nodes: [
        {
          id,
          entity_type: 'Case',
          label: `Case ${id}`,
          properties: { fir_number: id },
          degree: 1,
          confidence: 1.0,
        },
      ],
      edges: [],
      total_nodes: 1,
      total_edges: 0,
    })
  }),

  http.get(/\/api\/v1\/cases\/([^/]+)\/network/, async ({ request }) => {
    const match = new URL(request.url).pathname.match(/\/api\/v1\/cases\/([^/]+)\/network/)
    const id = match ? decodeURIComponent(match[1]) : ''
    return HttpResponse.json({
      nodes: [
        {
          id,
          entity_type: 'Case',
          label: `Case ${id}`,
          properties: { fir_number: id },
          degree: 1,
          confidence: 1.0,
        },
      ],
      edges: [],
      total_nodes: 1,
      total_edges: 0,
    })
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
    const name = String(body.full_name || body.name || '').toLowerCase()
    const phone = String(body.phone_number || body.phone || '')
    const vehicle = String(body.vehicle_number || body.vehicle || '')
    const address = String(body.address_text || body.address || '')

    const matches: any[] = []

    if (name || phone || vehicle || address) {
      const matchName = body.full_name || 'Vikram Sharma (Alias: Ramesh Hegde)'
      matches.push({
        matched_node_id: 'person-0040',
        confidence: 0.94,
        status: 'MATCHED',
        matched_fields: ['full_name', 'phone_number', 'jurisdiction'],
        reason: `Deterministic match on MSISDN +91 98201 22334 and phonetic double-metaphone alignment for "${matchName}".`,
        evidence_breakdown: {
          name_similarity: 0.92,
          phone_match: 1.0,
          graph_proximity: 0.9,
        },
        properties: {
          full_name: matchName,
          aliases: ['Ramesh Hegde', 'Vikky', 'S. Kumar'],
          phone_number: phone || '+91 98201 22334',
          role: 'Kingpin / Primary Coordinator',
          district: 'Mumbai Central',
          case_count: 3,
        },
      })

      if (name.includes('vikram') || name.includes('sunil') || name.includes('deepak')) {
        matches.push({
          matched_node_id: 'person-0037',
          confidence: 0.78,
          status: 'PROBABLE_MATCH',
          matched_fields: ['alias', 'co_accused_nexus', 'financial_mule'],
          reason: 'Secondary alias match with shared financial mule accounts across FIR-141 and FIR-207.',
          evidence_breakdown: {
            name_similarity: 0.75,
            financial_nexus: 0.82,
          },
          properties: {
            full_name: 'Sunil Gupta',
            aliases: ['Vikram Bhai', 'SG'],
            phone_number: '+91 98111 55667',
            role: 'Financial Mule Operator',
            district: 'New Delhi',
            case_count: 2,
          },
        })
      }
    }

    return HttpResponse.json({
      query: body,
      matches,
      total_matches: matches.length,
    })
  }),

  // Intelligence Hub Hotspots
  http.get(/\/api\/v1\/nexus\/intelligence\/hotspots(\?.*)?$/, () => {
    return HttpResponse.json([
      {
        district: 'Mumbai Central',
        case_count: 87,
        baseline_cases: 25.6,
        concentration_multiplier: 3.4,
        dominant_categories: [
          { category: 'Narcotics', count: 39, percentage: 44.8 },
          { category: 'Robbery', count: 28, percentage: 32.2 },
          { category: 'Cyber', count: 20, percentage: 23.0 },
        ],
        cross_case_links_count: 14,
        repeat_offender_overlap_count: 6,
        repeat_offender_ids: ['person-0040', 'person-0037'],
        repeat_offender_names: ['Ramesh Hegde', 'Sunil Gupta'],
        evidence_backed: true,
        evidence_ids: ['EVD-FIR-141', 'EVD-CDR-01'],
        alert_level: 'RED',
        summary_reason: 'District Mumbai Central has 87 cases (3.4x baseline) with 6 repeat offenders.',
      },
      {
        district: 'Pune City',
        case_count: 32,
        baseline_cases: 25.6,
        concentration_multiplier: 1.2,
        dominant_categories: [
          { category: 'Financial Fraud', count: 18, percentage: 56.2 },
          { category: 'Extortion', count: 14, percentage: 43.8 },
        ],
        cross_case_links_count: 5,
        repeat_offender_overlap_count: 2,
        repeat_offender_ids: ['person-0040'],
        repeat_offender_names: ['Ramesh Hegde'],
        evidence_backed: true,
        evidence_ids: ['EVD-FIR-207'],
        alert_level: 'AMBER',
        summary_reason: 'District Pune City has 32 cases (1.2x baseline) with 2 repeat offenders.',
      },
    ])
  }),

  // Intelligence Hub Drilldown
  http.get(/\/api\/v1\/nexus\/intelligence\/hotspots\/([^/?]+)/, ({ params }) => {
    const district = decodeURIComponent(String(params[0])) || 'Mumbai Central'
    return HttpResponse.json({
      district,
      case_count: 87,
      baseline_cases: 25.6,
      concentration_multiplier: 3.4,
      cases: [
        {
          case_id: 'case-0141',
          fir_number: 'FIR-2026-141',
          title: 'Narcotics distribution syndicate',
          date: '2026-02-04T10:00:00Z',
          crime_head: 'Narcotics',
          police_station: 'Mumbai Central Police Station',
          sections: ['Section 21 NDPS', 'Section 120B IPC'],
          accused_count: 4,
        },
        {
          case_id: 'case-0142',
          fir_number: 'FIR-2026-142',
          title: 'Armed jewelry robbery',
          date: '2026-02-12T14:30:00Z',
          crime_head: 'Robbery',
          police_station: 'Crime Branch Mumbai',
          sections: ['Section 392 IPC', 'Section 397 IPC'],
          accused_count: 3,
        },
      ],
      entities: [
        {
          entity_id: 'person-0040',
          name: 'Ramesh Hegde',
          entity_type: 'Person',
          case_count: 7,
          role: 'ACCUSED_IN',
        },
        {
          entity_id: 'person-0037',
          name: 'Sunil Gupta',
          entity_type: 'Person',
          case_count: 3,
          role: 'ACCUSED_IN',
        },
      ],
      repeat_offenders: [
        {
          person_id: 'person-0040',
          canonical_name: 'Ramesh Hegde',
          aliases: ['Ramesh H.', 'R. Hegde'],
          case_count: 7,
          districts: ['Mumbai Central', 'Pune City', 'Thane'],
          fir_numbers: ['FIR-2026-141', 'FIR-2026-142', 'FIR-2026-207'],
          why_surfaced: 'Deterministic repeat-case + entity-resolution evidence.',
        },
      ],
      cross_case_links: [
        {
          source_id: 'person-0040',
          target_id: 'case-0142',
          edge_type: 'ACCUSED_IN',
          case_ids: ['case-0141', 'case-0142'],
        },
      ],
      evidence_ids: ['EVD-FIR-141', 'EVD-CDR-01'],
      evidence: [
        {
          evidence_id: 'EVD-FIR-141',
          source_type: 'FIR_RECORD',
          description: 'Original FIR record for Case 141',
          case_id: 'case-0141',
        },
      ],
    })
  }),

  // Intelligence Hub Repeat Offenders Radar
  http.get(/\/api\/v1\/nexus\/intelligence\/offenders(\?.*)?$/, () => {
    return HttpResponse.json([
      {
        person_id: 'person-0040',
        canonical_name: 'Ramesh Hegde',
        aliases: ['Ramesh H.', 'R. Hegde'],
        resolved_person_ids: ['person-0040', 'person-0040-alias'],
        case_count: 7,
        case_ids: ['case-0141', 'case-0142', 'case-0207'],
        fir_numbers: ['FIR-2026-141', 'FIR-2026-142', 'FIR-2026-207'],
        districts: ['Mumbai Central', 'Pune City', 'Thane'],
        district_count: 3,
        shared_network_entities_count: 4,
        shared_network_entities: [
          {
            entity_id: 'person-0037',
            label: 'Sunil Gupta',
            entity_type: 'Person',
            shared_reason: 'Co-accused in case-0141',
          },
        ],
        shared_phone_identifiers: ['+91 98200 11223', '+91 98200 99887'],
        most_recent_case: {
          case_id: 'case-0142',
          fir_number: 'FIR-2026-142',
          date: '2026-02-12T14:30:00Z',
          district: 'Mumbai Central',
          crime_head: 'Robbery',
        },
        evidence_ids: ['EVD-FIR-141', 'EVD-CDR-01'],
        why_surfaced: 'Deterministic repeat-case + entity-resolution evidence.',
        compliance_status: 'Investigative lead — not a finding of guilt.',
      },
    ])
  }),

  // Intelligence Hub Combined Bridges
  http.get(/\/api\/v1\/nexus\/intelligence\/combined(\?.*)?$/, () => {
    return HttpResponse.json([
      {
        signal_id: 'sig-bridge-mumbai-central',
        primary_district: 'Mumbai Central',
        primary_district_cases: 87,
        repeat_offender_count: 6,
        connected_districts: [
          {
            district: 'Pune City',
            bridging_offenders: ['Ramesh Hegde'],
            case_count: 32,
          },
        ],
        cross_district_bridge_detected: true,
        bridging_offender_details: [
          {
            person_id: 'person-0040',
            name: 'Ramesh Hegde',
            home_district: 'Mumbai Central',
            external_districts: ['Pune City', 'Thane'],
            case_ids: ['case-0141', 'case-0207'],
            case_count: 7,
          },
        ],
        evidence_ids: ['EVD-FIR-141', 'EVD-CDR-01'],
        alert_title: 'RED FLAG — Cross-District Criminal Network Bridge',
        explanation: 'Crime hotspot: District Mumbai Central (87 cases). 6 resolved repeat offenders are associated with this area. 1 of those offenders also connect to cases in Pune City. Cross-case bridge detected.',
      },
    ])
  }),
]


