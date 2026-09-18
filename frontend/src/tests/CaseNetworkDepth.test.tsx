/**
 * frontend/src/tests/CaseNetworkDepth.test.tsx
 *
 * Tests verifying investigator-controlled depth exploration and deterministic
 * node context provenance display in the Case Network Analysis Panel.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import NetworkAnalysisPanel from '@/components/NetworkAnalysisPanel'
import type { NetworkGraphResponse } from '@shared/contracts/api'

const mockCaseNetworkDepth1: NetworkGraphResponse = {
  case_id: 'FIR-2026-495',
  depth: 1,
  total_nodes: 4,
  total_edges: 3,
  nodes: [
    {
      id: 'case-0016',
      label: 'FIR-2026-495',
      type: 'case',
      properties: {
        fir_number: 'FIR-2026-495',
        title: 'Cyber Hawala Case',
      },
      context: {
        node_id: 'case-0016',
        presence_type: 'DIRECT_CASE',
        reason: 'Root case entity representing the primary FIR investigation scope.',
        source_ids: ['FIR-2026-495'],
        relationship_types: [],
        distance_from_case: 0,
        path: ['case-0016'],
        readable_path: 'FIR-2026-495',
      },
    },
    {
      id: 'person-0101',
      label: 'Karan Gupta',
      type: 'person',
      properties: {
        role: 'Accused',
      },
      context: {
        node_id: 'person-0101',
        presence_type: 'DIRECT_CASE',
        reason: 'Directly accused in FIR-2026-495 (Section 318(4) BNS)',
        source_ids: ['FIR-2026-495'],
        relationship_types: ['ACCUSED_IN'],
        distance_from_case: 1,
        path: ['case-0016', 'person-0101'],
        readable_path: 'FIR-2026-495 ➔ Karan Gupta',
      },
    },
    {
      id: 'person-0102',
      label: 'Imran Malhotra',
      type: 'person',
      properties: {
        role: 'Accused',
      },
      context: {
        node_id: 'person-0102',
        presence_type: 'DIRECT_CASE',
        reason: 'Directly accused in FIR-2026-495 (Section 318(4) BNS)',
        source_ids: ['FIR-2026-495'],
        relationship_types: ['ACCUSED_IN'],
        distance_from_case: 1,
        path: ['case-0016', 'person-0102'],
        readable_path: 'FIR-2026-495 ➔ Imran Malhotra',
      },
    },
    {
      id: 'evidence-001',
      label: 'EV-2026-6493',
      type: 'evidence',
      properties: {
        category: 'Digital Evidence',
      },
      context: {
        node_id: 'evidence-001',
        presence_type: 'EVIDENCE',
        reason: 'Primary evidentiary record seized in FIR-2026-495',
        source_ids: ['FIR-2026-495'],
        relationship_types: ['EVIDENCE_IN'],
        distance_from_case: 1,
        path: ['case-0016', 'evidence-001'],
        readable_path: 'FIR-2026-495 ➔ EV-2026-6493',
      },
    },
  ],
  edges: [
    {
      id: 'edge-1',
      source: 'person-0101',
      target: 'case-0016',
      edge_type: 'ACCUSED_IN',
      label: 'ACCUSED_IN',
      reason: 'Named accused in FIR',
    },
    {
      id: 'edge-2',
      source: 'person-0102',
      target: 'case-0016',
      edge_type: 'ACCUSED_IN',
      label: 'ACCUSED_IN',
      reason: 'Named accused in FIR',
    },
    {
      id: 'edge-3',
      source: 'evidence-001',
      target: 'case-0016',
      edge_type: 'EVIDENCE_IN',
      label: 'EVIDENCE_IN',
      reason: 'Seizure memorandum',
    },
  ],
}

const mockCaseNetworkDepth2: NetworkGraphResponse = {
  case_id: 'FIR-2026-495',
  depth: 2,
  total_nodes: 5,
  total_edges: 4,
  nodes: [
    ...mockCaseNetworkDepth1.nodes,
    {
      id: 'person-0104',
      label: 'Pradeep Iyer',
      type: 'person',
      properties: {
        role: 'Syndicate Operative',
      },
      context: {
        node_id: 'person-0104',
        presence_type: 'INTELLIGENCE_EXPANSION',
        reason: 'Multi-hop intelligence expansion (2 hops) via Karan Gupta',
        source_ids: ['INTEL-BETA-CYBER'],
        relationship_types: ['MEMBER_OF'],
        distance_from_case: 2,
        path: ['case-0016', 'person-0101', 'person-0104'],
        readable_path: 'FIR-2026-495 ➔ Karan Gupta ➔ Pradeep Iyer',
      },
    },
  ],
  edges: [
    ...mockCaseNetworkDepth1.edges,
    {
      id: 'edge-4',
      source: 'person-0101',
      target: 'person-0104',
      edge_type: 'MEMBER_OF',
      label: 'MEMBER_OF',
      reason: 'Syndicate membership link',
    },
  ],
}

const mockCaseNetworkDepth0: NetworkGraphResponse = {
  case_id: 'FIR-2026-495',
  depth: 0,
  total_nodes: 1,
  total_edges: 0,
  nodes: [mockCaseNetworkDepth1.nodes[0]],
  edges: [],
}

let capturedDepths: string[] = []

const server = setupServer(
  http.get('/api/v1/network/cases/:caseId', ({ request }) => {
    const url = new URL(request.url)
    const depthParam = url.searchParams.get('depth') || '1'
    capturedDepths.push(depthParam)

    if (depthParam === '0') return HttpResponse.json(mockCaseNetworkDepth0)
    if (depthParam === '2') return HttpResponse.json(mockCaseNetworkDepth2)
    return HttpResponse.json(mockCaseNetworkDepth1)
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => {
  server.resetHandlers()
  capturedDepths = []
})
afterAll(() => server.close())

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return ({ children }: { children?: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Case Network Depth Control & Entity Context Provenance', () => {
  it('defaults to depth=1, displaying direct case accused and context header', async () => {
    const Wrapper = createWrapper()
    render(
      <Wrapper>
        <NetworkAnalysisPanel caseId="FIR-2026-495" />
      </Wrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/CASE: FIR-2026-495/i)).toBeInTheDocument()
      expect(screen.getByText('Direct Relationships (1 Hop)')).toBeInTheDocument()
    })

    // Confirms depth=1 was requested by default
    expect(capturedDepths).toContain('1')

    // Confirms Scope control buttons are present with 1 Hop active
    const oneHopBtn = screen.getByRole('button', { name: '1 Hop' })
    expect(oneHopBtn).toHaveAttribute('aria-pressed', 'true')

    const caseOnlyBtn = screen.getByRole('button', { name: 'Case Only' })
    expect(caseOnlyBtn).toHaveAttribute('aria-pressed', 'false')
  })

  it('displays deterministic "Why is this entity shown?" card in the inspector for direct accused', async () => {
    const Wrapper = createWrapper()
    render(
      <Wrapper>
        <NetworkAnalysisPanel caseId="FIR-2026-495" selectedEntityId="person-0101" />
      </Wrapper>
    )

    await waitFor(() => {
      expect(screen.getAllByText('Karan Gupta').length).toBeGreaterThan(0)
    })

    // Check "Why is this entity shown?" card (rendered in both canvas card and inspector)
    expect(screen.getAllByText(/Why is this entity shown\?/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/DIRECT CASE/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Directly accused in FIR-2026-495 \(Section 318\(4\) BNS\)/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText('1 hop').length).toBeGreaterThan(0)
    expect(screen.getAllByText('FIR-2026-495 ➔ Karan Gupta').length).toBeGreaterThan(0)
  })

  it('switches to depth=2 when 2 Hops button is clicked and displays intelligence expansion context', async () => {
    const Wrapper = createWrapper()
    render(
      <Wrapper>
        <NetworkAnalysisPanel caseId="FIR-2026-495" />
      </Wrapper>
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '2 Hops' })).toBeInTheDocument()
    })

    // Click 2 Hops
    fireEvent.click(screen.getByRole('button', { name: '2 Hops' }))

    await waitFor(() => {
      expect(capturedDepths).toContain('2')
      expect(screen.getByText('Expanded Intelligence (2 Hops)')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: '2 Hops' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('switches to depth=0 when Case Only button is clicked', async () => {
    const Wrapper = createWrapper()
    render(
      <Wrapper>
        <NetworkAnalysisPanel caseId="FIR-2026-495" />
      </Wrapper>
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Case Only' })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Case Only' }))

    await waitFor(() => {
      expect(capturedDepths).toContain('0')
      expect(screen.getByText('Case Only (Strict)')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: 'Case Only' })).toHaveAttribute('aria-pressed', 'true')
  })
})
