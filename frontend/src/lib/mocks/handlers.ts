import { http, HttpResponse, delay } from 'msw'
import type { 
  CaseSummaryResponse, 
  CaseDetailResponse, 
  EscalationResponse, 
  CopilotQueryResponse,
  ChatResponse,
  DependencyResponse,
  DependencyStatus
} from '@shared/contracts/api'

// In-memory mock database state
let mockCases: CaseDetailResponse[] = [
  {
    id: "847",
    fir_number: "FIR 123/2026",
    station_name: "Mysuru Central",
    offence_category: "Murder (BNS Section 103)",
    clocks: [
      {
        id: "c_847_1",
        case_id: "847",
        clock_type: "default-bail",
        start_date: "2026-06-01T00:00:00Z",
        deadline_date: "2026-07-25T00:00:00Z",
        days_remaining: 9,
        status: "red",
        bnss_reference: "Section 187(3) BNSS [VERIFIED]"
      },
      {
        id: "c_847_2",
        case_id: "847",
        clock_type: "document-supply",
        start_date: "2026-07-01T00:00:00Z",
        deadline_date: "2026-07-15T00:00:00Z",
        days_remaining: -1,
        status: "overdue",
        bnss_reference: "Section 230 BNSS [VERIFIED]"
      }
    ],
    dependencies: [
      {
        id: "dep_847_1",
        case_id: "847",
        name: "FSL report",
        status: "pending",
        days_stale: 21,
        assigned_to: "Forensic Lab Bangalore"
      },
      {
        id: "dep_847_2",
        case_id: "847",
        name: "CDR analysis",
        status: "resolved",
        days_stale: 0,
        assigned_to: "Cyber Cell SP Office"
      }
    ]
  },
  {
    id: "902",
    fir_number: "FIR 45/2026",
    station_name: "Mysuru Central",
    offence_category: "Theft (BNS Section 303)",
    clocks: [
      {
        id: "c_902_1",
        case_id: "902",
        clock_type: "default-bail",
        start_date: "2026-06-15T00:00:00Z",
        deadline_date: "2026-08-14T00:00:00Z",
        days_remaining: 29,
        status: "amber",
        bnss_reference: "Section 187(3) BNSS [VERIFIED]"
      }
    ],
    dependencies: [
      {
        id: "dep_902_1",
        case_id: "902",
        name: "Witness Section 183 statement",
        status: "pending",
        days_stale: 5,
        assigned_to: "IO Sub-Inspector Patil"
      }
    ]
  }
]

const mockEscalations: EscalationResponse[] = [
  {
    id: "esc_1",
    case_id: "847",
    triggered_at: "2026-07-14T10:00:00Z",
    reason: "FSL report has been pending for 21 days, threatening 9-day chargesheet clock",
    routed_to_rank: "SHO",
    routed_to_officer_id: "off_sho_1",
    resolved: false
  }
]

// Generate 5000 case summaries dynamically for virtualization testing
const generate5000Worklist = (): CaseSummaryResponse[] => {
  const list: CaseSummaryResponse[] = []
  
  // Add our specific mock cases first so they are searchable
  mockCases.forEach((c) => {
    // Find primary clock (lowest days remaining, or overdue)
    const primaryClock = c.clocks.reduce((prev, curr) => {
      if (prev.status === 'overdue') return prev
      if (curr.status === 'overdue') return curr
      return curr.days_remaining < prev.days_remaining ? curr : prev
    })
    
    list.push({
      id: c.id,
      fir_number: c.fir_number,
      station_name: c.station_name,
      offence_category: c.offence_category,
      clock: primaryClock,
      unresolved_dependency_count: c.dependencies.filter(d => d.status !== 'resolved').length,
      risk_rank: c.id === "847" ? 1 : 2
    })
  })

  // Fill up to 5000 cases
  for (let i = 1; i <= 5000; i++) {
    const id = String(1000 + i)
    const daysRemaining = 12 + (i % 80)
    let status: 'green' | 'amber' | 'red' | 'overdue' = 'green'
    if (daysRemaining < 15) status = 'red'
    else if (daysRemaining < 30) status = 'amber'

    list.push({
      id,
      fir_number: `FIR ${45 + i}/2026`,
      station_name: i % 2 === 0 ? "Mysuru Central" : "Nanjangud Police Station",
      offence_category: i % 3 === 0 ? "Theft (BNS Section 303)" : "Assault (BNS Section 115)",
      clock: {
        id: `c_${id}`,
        case_id: id,
        clock_type: "default-bail",
        start_date: "2026-06-20T00:00:00Z",
        deadline_date: "2026-08-19T00:00:00Z",
        days_remaining: daysRemaining,
        status,
        bnss_reference: "Section 187(3) BNSS [VERIFIED]"
      },
      unresolved_dependency_count: i % 3,
      risk_rank: 5 + i
    })
  }

  return list
}

export const handlers = [
  // 1. GET /worklist & /api/v1/investigations
  http.get(/\/worklist|\/api\/v1\/investigations/, async () => {
    await delay(300) // Realistic latency simulation
    const allSummaries = generate5000Worklist()
    return HttpResponse.json(allSummaries)
  }),

  // 2. GET /cases/:id
  http.get(/\/cases\/([^/]+)/, async ({ params }) => {
    await delay(200)
    const id = params[0] as string
    const matchedCase = mockCases.find(c => c.id === id)
    
    if (!matchedCase) {
      return new HttpResponse(null, { status: 404, statusText: 'Case Not Found' })
    }
    
    return HttpResponse.json(matchedCase)
  }),

  // 3. GET /cases/:id/network
  http.get(/\/cases\/([^/]+)\/network/, async () => {
    await delay(250)
    // Return structured React Flow compatible graph nodes and edges
    return HttpResponse.json({
      nodes: [
        { id: '1', type: 'case', data: { label: 'FIR 123/2026 (Murder)' }, position: { x: 250, y: 50 } },
        { id: '2', type: 'person', data: { label: 'Ramesh Gowda (Accused)' }, position: { x: 100, y: 150 } },
        { id: '3', type: 'person', data: { label: 'Suresh Kumar (Victim)' }, position: { x: 400, y: 150 } },
        { id: '4', type: 'dependency', data: { label: 'FSL Report (Pending)' }, position: { x: 250, y: 250 } },
      ],
      edges: [
        { id: 'e1-2', source: '2', target: '1', label: 'ACCUSED_IN' },
        { id: 'e1-3', source: '3', target: '1', label: 'VICTIM_IN' },
        { id: 'e1-4', source: '1', target: '4', label: 'CASE_HAS_DEPENDENCY' }
      ]
    })
  }),

  // 4. GET /rollup/:district
  http.get(/\/rollup\/([^/]+)/, async () => {
    await delay(200)
    return HttpResponse.json({
      total_cases: 1205,
      red_clocks: 12,
      amber_clocks: 34,
      stale_dependencies: 45,
      station_rankings: [
        { station_name: "Mysuru Central", total: 150, critical: 5 },
        { station_name: "Mysuru East", total: 110, critical: 3 },
        { station_name: "Nanjangud Police Station", total: 85, critical: 2 },
        { station_name: "Srirangapatna Station", total: 60, critical: 2 }
      ]
    })
  }),

  // 5. GET /escalations
  http.get(/\/escalations/, async () => {
    return HttpResponse.json(mockEscalations)
  }),

  // 6. PATCH /deps/:id
  http.patch(/\/deps\/([^/]+)/, async ({ params, request }) => {
    await delay(200)
    const id = params[0] as string
    const body = (await request.json()) as { status: string }
    
    // Find dependency in memory
    let updatedDep: DependencyResponse | null = null
    
    mockCases = mockCases.map(c => {
      const deps = c.dependencies.map(d => {
        if (d.id === id) {
          updatedDep = { ...d, status: body.status as DependencyStatus }
          return updatedDep
        }
        return d
      })
      return { ...c, dependencies: deps }
    })

    if (!updatedDep) {
      return new HttpResponse(null, { status: 404, statusText: 'Dependency not found' })
    }

    // Interactive escalation logic for Demo Story:
    // If the FSL report (dep_847_1) is escalated, we append to mockEscalations list
    if (id === 'dep_847_1' && body.status === 'escalated') {
      const exists = mockEscalations.some(e => e.id === 'esc_dep_847_1')
      if (!exists) {
        mockEscalations.unshift({
          id: 'esc_dep_847_1',
          case_id: '847',
          triggered_at: new Date().toISOString(),
          reason: 'FSL report manual escalation triggered by IO',
          routed_to_rank: 'SHO',
          routed_to_officer_id: 'off_sho_1',
          resolved: false
        })
      }
    }

    return HttpResponse.json(updatedDep)
  }),

  // 7. POST /copilot/query
  http.post(/\/copilot\/query/, async ({ request }) => {
    await delay(600)
    const body = (await request.json()) as { query: string, case_id?: string }
    const queryLower = body.query.toLowerCase()
    
    const response: CopilotQueryResponse = {
      refused: false,
      confidence: 1.0
    }

    // Refusal Gate check (Law 13 & D6 - "Is the accused guilty?" -> Refusal)
    if (queryLower.includes('guilty') || queryLower.includes('commit') || queryLower.includes('culpable')) {
      response.refused = true
      response.refusal_reason = "I cannot infer guilt, innocence, or risk of reoffense. These are matters of judicial determination."
      response.confidence = 0.95
    } 
    // Explainable Query Response for Hero Case 847
    else if (body.case_id === '847' && (queryLower.includes('risk') || queryLower.includes('clock') || queryLower.includes('block'))) {
      response.answer = "Case 847 is at risk because the FSL report is 21 days stale, and the 60-day default-bail chargesheet clock has only 9 days remaining."
      response.reasoning_path = [
        "Case(847) -> ClockInstance(c_847_1) [status=red, days_remaining=9]",
        "Case(847) -> Dependency(dep_847_1) [name='FSL report', status='pending', days_stale=21]"
      ]
    } 
    // Generic response fallback
    else {
      response.answer = "This query was successfully parsed against the investigation graph. No critical risk triggers found."
      response.reasoning_path = [
        "Query parsed -> Intent: general_info",
        "Graph check -> OK"
      ]
    }

    return HttpResponse.json(response)
  }),

  // 8. POST /api/chat
  http.post(/\/api\/chat/, async ({ request }) => {
    await delay(400)
    const body = (await request.json()) as { message?: string; query?: string; case_id?: string; conversation_id?: string }
    const msg = (body.message || body.query || '').toLowerCase()
    
    let answer = "This query was successfully processed by the NEXUS Intelligence Graph pipeline."
    
    if (msg.includes('guilty') || msg.includes('commit') || msg.includes('culpable')) {
      answer = "I cannot infer guilt, innocence, or risk of reoffense. These are matters of judicial determination."
    } else if (msg.includes('hotspot')) {
      answer = "Hotspot analysis complete: Identified 4 high-priority cluster zones across Bengaluru and Mysuru stations with 12 stale forensic dependencies."
    } else if (msg.includes('offender')) {
      answer = "Repeat offender intelligence: Found 3 repeat offenders linked to 8 interconnected BNS cases."
    }

    const response: ChatResponse = {
      message: answer,
      conversation_id: body.conversation_id || 'conv-mock-123',
      intent: {
        name: msg.includes('hotspot') ? 'GET_HOTSPOTS' : msg.includes('offender') ? 'GET_REPEAT_OFFENDERS' : 'GENERAL_CHAT',
        confidence: 0.98,
      },
    }

    return HttpResponse.json(response)
  })
]
