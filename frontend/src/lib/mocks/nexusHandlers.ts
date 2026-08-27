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
    const source = url.searchParams.get('source') ?? ''
    const target = url.searchParams.get('target') ?? ''
    if (isResolved() && ((source === 'CASE-141' && target === 'CASE-207') || (source === 'CASE-207' && target === 'CASE-141'))) {
      return HttpResponse.json({
        found: true, source_id: source, target_id: target,
        node_ids: ['CASE-141', 'P-RAFIQ', 'CASE-207'],
        edge_ids: ['E-ACCUSE-141', 'E-ACCUSE-207'],
        hops: 2,
        explanation:
          'FIR 141/2026 and FIR 207/2026 are connected through the confirmed entity ' +
          '"Rafiq Khan / Rafiq Ahmed" (candidate RC-1), accused in both cases and reachable on phone +91 98450 11223 in both CDR pulls.',
        evidence_ids: ['SRC-FIR-141', 'SRC-FIR-207', 'SRC-CDR-A12', 'SRC-CDR-B31'],
      })
    }
    return HttpResponse.json({
      found: false, source_id: source, target_id: target,
      node_ids: [], edge_ids: [], hops: 0,
      explanation: isResolved()
        ? `No explainable connection between ${source} and ${target} in the current snapshot.`
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
      })
    }
    return HttpResponse.json({
      query: body.query,
      answer: 'This query was parsed against the investigation graph. Ask "How are the two cases connected?" for the grounded connection explanation.',
      is_refusal: false,
      evidence_ids: [],
      reasoning_path: ['Intent: general_info — no specific graph claim to ground'],
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
]
