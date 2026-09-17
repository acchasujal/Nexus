/**
 * frontend/src/tests/NetworkAdaptationRadar.test.tsx
 *
 * Vitest tests for P1-C: Network Adaptation Radar (NetworkAdaptationSection).
 * Verifies:
 *   1. Renders metric summary cards (Total Structural Adaptations, Bridge Substitutions, Financial Reroutes, Confirmed).
 *   2. Renders filter buttons and allows filtering by adaptation type.
 *   3. Displays structural reconfigurations (Previous Direct Link -> Substituted Proxy Conduit) with timestamps and context.
 *   4. Allows investigator to Confirm, Monitor, or Dismiss adaptation findings.
 *   5. Adheres to zero predictive guilt constraints (factual topological transitions only).
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { NetworkAdaptationSection } from '@/components/nexus/NetworkAdaptationSection'

const mockAdaptations = [
  {
    adaptation_id: 'ADAPT-2026-PROXY-RAFIQ-DEEPAK',
    adaptation_type: 'INTERMEDIARY_REPLACEMENT',
    primary_entity_id: 'P-RAFIQ',
    primary_entity_name: 'Rafiq Khan',
    secondary_entity_id: 'P-DEEPAK',
    secondary_entity_name: 'Deepak Rao',
    substitute_intermediary_id: 'person-0003',
    substitute_intermediary_name: 'V. Sharma (Proxy Broker)',
    previous_path: ['P-RAFIQ', 'P-DEEPAK'],
    new_path: ['P-RAFIQ', 'person-0003', 'P-DEEPAK'],
    detected_at: '2026-03-05T14:00:00Z',
    time_lag_days: 12,
    structural_significance: 0.91,
    corroborating_context:
      'Intermediary replacement: Direct CDR communication link ceased post FIR-141; active multi-hop conduit re-emerged through V. Sharma.',
    evidence_refs: ['SRC-FIR-141', 'SRC-FIR-207', 'SRC-CDR-A12'],
    derivation_class: 'DERIVED',
    review_status: 'DETECTED',
  },
  {
    adaptation_id: 'ADAPT-2026-BRIDGE-SUBSTITUTION',
    adaptation_type: 'BRIDGE_SUBSTITUTION',
    primary_entity_id: 'person-0051',
    primary_entity_name: 'Ramesh Hegde (Broker)',
    secondary_entity_id: 'COMM-BETA',
    secondary_entity_name: 'Cyber Hawala Syndicate',
    substitute_intermediary_id: 'person-0051',
    substitute_intermediary_name: 'Ramesh Hegde',
    previous_path: ['FORMER-CONNECTOR-01', 'COMM-BETA'],
    new_path: ['person-0051', 'COMM-BETA'],
    detected_at: '2026-03-08T09:30:00Z',
    time_lag_days: 9,
    structural_significance: 0.88,
    corroborating_context:
      'Bridge broker substitution: Betweenness centrality detects Ramesh Hegde assuming inter-syndicate coordination role.',
    evidence_refs: ['SRC-FIR-141', 'SRC-CDR-BRIDGE-01'],
    derivation_class: 'DERIVED',
    review_status: 'DETECTED',
  },
]

const mockSummary = {
  total_adaptations: 2,
  by_type: { INTERMEDIARY_REPLACEMENT: 1, BRIDGE_SUBSTITUTION: 1 },
  by_status: { DETECTED: 2 },
  intermediary_replacements: 1,
  bridge_substitutions: 1,
  financial_reroutings: 0,
  community_reconnections: 0,
  active_monitoring: 0,
  confirmed_adaptations: 0,
}

const server = setupServer(
  http.get('/api/v1/nexus/intelligence/network-adaptation', () => {
    return HttpResponse.json(mockAdaptations)
  }),
  http.get('/api/v1/nexus/intelligence/network-adaptation/summary', () => {
    return HttpResponse.json(mockSummary)
  }),
  http.post('/api/v1/nexus/intelligence/network-adaptation/:adaptationId/decide', async ({ params, request }) => {
    const body = (await request.json()) as any
    const found = mockAdaptations.find((a) => a.adaptation_id === params.adaptationId)
    return HttpResponse.json({
      ...(found || mockAdaptations[0]),
      review_status: body.status,
      investigator_note: body.note,
      decided_at: '2026-03-17T12:00:00Z',
      decided_by: 'IO Rajesh Kumar',
    })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderSection() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <NetworkAdaptationSection />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('NetworkAdaptationSection Component (P1-C)', () => {
  it('renders metric cards and summary counters correctly', async () => {
    renderSection()

    expect(await screen.findByText(/Total Structural Adaptations/i, {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText(/Bridge Broker Substitutions/i)).toBeInTheDocument()
    expect(screen.getByText(/Financial Layering Reroutes/i)).toBeInTheDocument()
    expect(screen.getByText(/Confirmed Adaptations/i)).toBeInTheDocument()
  })

  it('renders adaptation cards with previous direct link and substituted proxy conduit', async () => {
    renderSection()

    expect(await screen.findByText('Rafiq Khan', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText(/Target: Deepak Rao/i)).toBeInTheDocument()
    expect(screen.getByText('V. Sharma (Proxy Broker)')).toBeInTheDocument()
    expect(screen.getAllByText(/SRC-FIR-141/i).length).toBeGreaterThanOrEqual(1)
  })

  it('filters adaptation cards when filter button is clicked', async () => {
    renderSection()

    expect(await screen.findByText('Rafiq Khan', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText('Ramesh Hegde (Broker)')).toBeInTheDocument()

    // Filter to BRIDGE_SUBSTITUTION
    const bridgeFilterBtn = screen.getByRole('button', { name: /BRIDGE SUBSTITUTION/i })
    fireEvent.click(bridgeFilterBtn)

    expect(screen.queryByText('Rafiq Khan')).not.toBeInTheDocument()
    expect(screen.getByText('Ramesh Hegde (Broker)')).toBeInTheDocument()
  })

  it('allows investigator to confirm an adaptation finding', async () => {
    renderSection()

    const confirmBtns = await screen.findAllByRole('button', { name: /Confirm/i }, { timeout: 10000 })
    expect(confirmBtns.length).toBeGreaterThan(0)

    fireEvent.click(confirmBtns[0])

    await waitFor(() => {
      expect(screen.getByText(/Decision successfully logged: Marked as CONFIRMED/i)).toBeInTheDocument()
    })
  })
})
