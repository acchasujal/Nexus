/**
 * frontend/src/tests/DigitalShadowRadar.test.tsx
 *
 * Vitest tests for P1-D: Digital Shadow & SOCMINT Governance (DigitalShadowSection).
 * Verifies:
 *   1. Renders statutory Section 63 BSA compliance banner (Non-Equivalence Rule).
 *   2. Renders summary metric cards (Total Footprints, Telegram/Darknet Intel, VPAs, Confirmed).
 *   3. Displays digital shadow cards with digital identifier and physical hard-ID corroboration.
 *   4. Allows filtering by digital platform.
 *   5. Allows investigator to advance lifecycle state (Confirm, Corroborate, Dismiss).
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { DigitalShadowSection } from '@/components/nexus/DigitalShadowSection'

const mockShadows = [
  {
    corroboration_id: 'SHADOW-2026-TG-RAFIQ',
    person_id: 'P-RAFIQ',
    person_name: 'Rafiq Khan',
    platform: 'TELEGRAM',
    digital_identifier: '@hawk_ops_mysuru',
    corroborating_physical_id: '+91 98450 11223',
    corroborating_physical_type: 'Phone',
    confidence_score: 0.92,
    lifecycle_state: 'CORROBORATED',
    observation_context:
      "Telegram handle '@hawk_ops_mysuru' surfaced in seized device handset dump. Linked to primary MSISDN.",
    source_url_or_channel: 'https://t.me/hawk_ops_mysuru',
    evidence_refs: ['SRC-FIR-141', 'SRC-CDR-A12'],
    derivation_class: 'DERIVED',
    first_observed_at: '2026-02-15T10:00:00Z',
    last_verified_at: '2026-03-01T14:30:00Z',
  },
  {
    corroboration_id: 'SHADOW-2026-DARK-DEEPAK',
    person_id: 'P-DEEPAK',
    person_name: 'Deepak Rao',
    platform: 'DARKWEB_FORUM',
    digital_identifier: 'vendor_deepak_hyd',
    corroborating_physical_id: '861234567890123',
    corroborating_physical_type: 'Device IMEI',
    confidence_score: 0.88,
    lifecycle_state: 'CANDIDATE_LINK',
    observation_context:
      "Public forum escrow identifier 'vendor_deepak_hyd' referenced in cyber hawala chatter.",
    source_url_or_channel: 'https://sec-forum.internal/u/vendor_deepak_hyd',
    evidence_refs: ['SRC-CDR-B31', 'SRC-FIR-207'],
    derivation_class: 'DERIVED',
    first_observed_at: '2026-02-20T16:45:00Z',
  },
]

const mockSummary = {
  total_corroborations: 2,
  by_platform: { TELEGRAM: 1, DARKWEB_FORUM: 1 },
  by_lifecycle: { CORROBORATED: 1, CANDIDATE_LINK: 1 },
  telegram_channels: 1,
  darknet_forum_links: 1,
  payment_gateways: 0,
  corroborated_links: 1,
  confirmed_links: 0,
  candidate_links: 1,
}

const server = setupServer(
  http.get('/api/v1/nexus/intelligence/digital-shadow', () => {
    return HttpResponse.json(mockShadows)
  }),
  http.get('/api/v1/nexus/intelligence/digital-shadow/summary', () => {
    return HttpResponse.json(mockSummary)
  }),
  http.post('/api/v1/nexus/intelligence/digital-shadow/:corroborationId/decide', async ({ params, request }) => {
    const body = (await request.json()) as any
    const found = mockShadows.find((s) => s.corroboration_id === params.corroborationId)
    return HttpResponse.json({
      ...(found || mockShadows[0]),
      lifecycle_state: body.lifecycle_state,
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
        <DigitalShadowSection />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('DigitalShadowSection Component (P1-D)', () => {
  it('renders statutory Section 63 BSA compliance warning and metric cards', async () => {
    renderSection()

    expect(await screen.findByText(/Section 63 BSA & DPDP Act 2023 Digital Evidence Governance Protocol/i, {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText(/Total Digital Footprints/i)).toBeInTheDocument()
    expect(screen.getByText(/Telegram \/ Darknet Intel/i)).toBeInTheDocument()
    expect(screen.getByText(/Payment Gateway VPAs/i)).toBeInTheDocument()
    expect(screen.getByText(/Officer Confirmed/i)).toBeInTheDocument()
  })

  it('renders digital shadow cards with digital identifier and physical hard link', async () => {
    renderSection()

    expect(await screen.findByText('Rafiq Khan', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText('@hawk_ops_mysuru')).toBeInTheDocument()
    expect(screen.getByText('+91 98450 11223')).toBeInTheDocument()
    expect(screen.getByText('Deepak Rao')).toBeInTheDocument()
    expect(screen.getByText('vendor_deepak_hyd')).toBeInTheDocument()
    expect(screen.getByText('861234567890123')).toBeInTheDocument()
  })

  it('filters digital shadow cards when platform filter button is clicked', async () => {
    renderSection()

    expect(await screen.findByText('Rafiq Khan', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText('Deepak Rao')).toBeInTheDocument()

    // Filter to TELEGRAM
    const tgBtn = screen.getByRole('button', { name: /^TELEGRAM$/i })
    fireEvent.click(tgBtn)

    expect(screen.getByText('Rafiq Khan')).toBeInTheDocument()
    expect(screen.queryByText('Deepak Rao')).not.toBeInTheDocument()
  })

  it('allows investigator to confirm digital shadow corroboration', async () => {
    renderSection()

    const confirmBtns = await screen.findAllByRole('button', { name: /Confirm/i }, { timeout: 10000 })
    expect(confirmBtns.length).toBeGreaterThan(0)

    fireEvent.click(confirmBtns[0])

    await waitFor(() => {
      expect(screen.getByText(/Lifecycle state updated: Marked as INVESTIGATOR_CONFIRMED/i)).toBeInTheDocument()
    })
  })
})
