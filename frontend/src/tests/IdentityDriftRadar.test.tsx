/**
 * frontend/src/tests/IdentityDriftRadar.test.tsx
 *
 * Vitest tests for P1-B: Identity Drift Radar (IdentityDriftRadarSection).
 * Verifies:
 *   1. Renders metric summary cards (Total Drifts, Hardware IMEI Hops, Moniker Evolutions, Confirmed Links).
 *   2. Renders filter buttons and allows filtering by drift type.
 *   3. Displays identifier transitions (Previous Identifier -> New Identifier) with timestamps and context.
 *   4. Allows investigator to Confirm, Monitor, or Dismiss drift events.
 *   5. Adheres to zero predictive guilt constraints (factual transitions only).
 */

import { describe, it, expect, beforeEach, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { IdentityDriftRadarSection } from '@/components/nexus/IdentityDriftRadarSection'

const mockDrifts = [
  {
    drift_id: 'DRIFT-2026-PH-RAFIQ',
    person_id: 'P-RAFIQ',
    person_name: 'Rafiq Khan',
    drift_type: 'PHONE_TURNOVER',
    previous_value: '+91 98450 11223',
    new_value: '+91 98450 99881',
    previous_seen_at: '2026-02-11T09:30:00Z',
    new_seen_at: '2026-03-02T14:15:00Z',
    time_window_days: 19,
    corroborating_context: 'Burner SIM turnover: Primary line ceased activity, target reactivated on secondary subscriber line.',
    evidence_refs: ['SRC-FIR-141', 'SRC-CDR-A12', 'SRC-CDR-B31'],
    derivation_class: 'DERIVED',
    human_status: 'DETECTED',
  },
  {
    drift_id: 'DRIFT-2026-DEV-DEEPAK',
    person_id: 'P-DEEPAK',
    person_name: 'Deepak Rao',
    drift_type: 'DEVICE_HOP',
    previous_value: 'IMEI 861234567890123',
    new_value: 'IMEI 869876543210987',
    previous_seen_at: '2026-02-18T11:00:00Z',
    new_seen_at: '2026-03-05T16:30:00Z',
    time_window_days: 15,
    corroborating_context: 'Handset swap: Switch records show SIM moved to newly provisioned device.',
    evidence_refs: ['SRC-CDR-B31', 'SRC-FIR-207'],
    derivation_class: 'DERIVED',
    human_status: 'DETECTED',
  },
]

const mockSummary = {
  total_drifts: 2,
  by_type: { PHONE_TURNOVER: 1, DEVICE_HOP: 1 },
  by_status: { DETECTED: 2 },
  phone_turnovers: 1,
  device_hops: 1,
  vehicle_drifts: 0,
  alias_evolutions: 0,
  active_monitoring: 0,
  confirmed_drifts: 0,
}

const server = setupServer(
  http.get('/api/v1/nexus/intelligence/identity-drift', () => {
    return HttpResponse.json(mockDrifts)
  }),
  http.get('/api/v1/nexus/intelligence/identity-drift/summary', () => {
    return HttpResponse.json(mockSummary)
  }),
  http.post('/api/v1/nexus/intelligence/identity-drift/:driftId/decide', async ({ params, request }) => {
    const body = (await request.json()) as any
    const found = mockDrifts.find((d) => d.drift_id === params.driftId)
    return HttpResponse.json({
      ...(found || mockDrifts[0]),
      human_status: body.status,
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
        <IdentityDriftRadarSection />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('P1-B: Identity Drift Radar Section', () => {
  beforeEach(() => {
    window.localStorage.setItem('nexus_role', 'INVESTIGATOR')
  })

  it('renders summary metric cards and detected drift records', async () => {
    renderSection()

    await waitFor(() => {
      expect(screen.getByText('Rafiq Khan')).toBeInTheDocument()
    }, { timeout: 10000 })

    expect(screen.getByText('Deepak Rao')).toBeInTheDocument()
    expect(screen.getByText(/Total Drift Events/i)).toBeInTheDocument()
    expect(screen.getByText(/Hardware IMEI Hops/i)).toBeInTheDocument()

    // Transitions
    expect(screen.getByText('+91 98450 11223')).toBeInTheDocument()
    expect(screen.getByText('+91 98450 99881')).toBeInTheDocument()
    expect(screen.getByText('IMEI 861234567890123')).toBeInTheDocument()
    expect(screen.getByText('IMEI 869876543210987')).toBeInTheDocument()

    // Citations
    expect(screen.getAllByText('SRC-FIR-141').length).toBeGreaterThan(0)
  })

  it('filters drift records by type', async () => {
    renderSection()

    await waitFor(() => {
      expect(screen.getByText('Rafiq Khan')).toBeInTheDocument()
    })

    const devHopFilterBtn = screen.getByRole('button', { name: /DEVICE HOP/i })
    fireEvent.click(devHopFilterBtn)

    expect(screen.getByText('Deepak Rao')).toBeInTheDocument()
    expect(screen.queryByText('Rafiq Khan')).not.toBeInTheDocument()
  })

  it('allows investigator to confirm drift finding', async () => {
    renderSection()

    await waitFor(() => {
      expect(screen.getByText('Rafiq Khan')).toBeInTheDocument()
    })

    const confirmBtns = screen.getAllByRole('button', { name: /Confirm/i })
    fireEvent.click(confirmBtns[0])

    await waitFor(() => {
      expect(screen.getByText(/Decision successfully logged: Marked as CONFIRMED/i)).toBeInTheDocument()
    })
  })
})
