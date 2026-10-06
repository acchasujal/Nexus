/**
 * frontend/src/tests/TrustFabricLedger.test.tsx
 *
 * Comprehensive tests for NEXUS Trust Fabric & Tamper-Evident Merkle Audit Ledger (Audit page).
 * Verifies:
 *   1. Renders Section 63 BSA statutory compliance banner.
 *   2. Displays Tamper-Evident Ledger Anchors section with anchored blocks.
 *   3. Triggers batch anchor verification and displays INTEGRITY VERIFIED badge.
 *   4. Allows inspecting Merkle inclusion proof for audit records.
 *   5. Renders Merkle inclusion certificate modal with proof path steps.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import Audit from '@/pages/Audit'

const mockLogs = [
  {
    id: 'evt-001',
    user_id: 'officer_sp',
    user_role: 'SP',
    action: 'investigation_viewed',
    case_id: 'CASE-141',
    timestamp: '2026-03-01T10:00:00Z',
    integrity_hash: '1111111111111111111111111111111111111111111111111111111111111111',
    previous_hash: null,
    details: { case_title: 'Mysuru Hawala Syndicate' },
  },
]

const mockAnchors = [
  {
    anchor_id: 'ANCHOR-2026-A1B2C3D4',
    batch_start: 'evt-001',
    batch_end: 'evt-001',
    event_count: 1,
    root_hash: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    anchored_at: '2026-03-01T10:05:00Z',
    creator_participant: 'NEXUS-POLICE-HQ',
    block_index: 1,
    block_hash: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    ledger_id: 'NEXUS-PERMISSIONED-LEDGER',
  },
]

const mockVerifyAnchor = {
  verified: true,
  anchor_id: 'ANCHOR-2026-A1B2C3D4',
  root_hash: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  block_index: 1,
  block_hash: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
  ledger_id: 'NEXUS-PERMISSIONED-LEDGER',
  reason: 'Anchor and permissioned ledger chain verified.',
  chain_valid: true,
  anchored_event_count: 1,
}

const mockProof = {
  verified: true,
  event_id: 'evt-001',
  event_hash: '1111111111111111111111111111111111111111111111111111111111111111',
  anchor_id: 'ANCHOR-2026-A1B2C3D4',
  block_index: 1,
  block_hash: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
  root_hash: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  leaf_index: 0,
  total_leaves: 1,
  proof: [
    { sibling_hash: 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', direction: 'right' },
  ],
  ledger_id: 'NEXUS-PERMISSIONED-LEDGER',
  participant: 'NEXUS-POLICE-HQ',
  anchored_at: '2026-03-01T10:05:00Z',
}

const server = setupServer(
  http.get(/\/api\/v1\/audit(\?.*)?$/, () => {
    return HttpResponse.json(mockLogs)
  }),
  http.get('/api/v1/audit/anchors', () => {
    return HttpResponse.json(mockAnchors)
  }),
  http.get('/api/v1/audit/anchors/:anchorId/verify', () => {
    return HttpResponse.json(mockVerifyAnchor)
  }),
  http.get('/api/v1/audit/:eventId/verify', () => {
    return HttpResponse.json({
      event_id: 'evt-001',
      verified: true,
      stored_hash: '1111111111111111111111111111111111111111111111111111111111111111',
      computed_hash: '1111111111111111111111111111111111111111111111111111111111111111',
      reason: 'Hash matches canonical audit event.',
    })
  }),
  http.get('/api/v1/audit/:eventId/proof', () => {
    return HttpResponse.json(mockProof)
  }),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Trust Fabric & Merkle Ledger UI (Audit.tsx)', () => {
  it('does not claim verification from hash presence and copies the disclosed hash', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
    renderWithClient(<Audit />)
    expect(await screen.findByText('Recorded; verify proof')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Copy hash' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'View technical proof for evt-001' }))
    expect(await screen.findByText('Verified')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Copy hash' }))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(mockLogs[0].integrity_hash))
    expect(await screen.findByText('Copy hash confirmed')).toBeInTheDocument()
  })

  it('renders statutory Section 63 BSA compliance banner', async () => {
    renderWithClient(<Audit />)

    expect(screen.getByText(/Section 63 Bharatiya Sakshya Adhiniyam \(BSA\) 2023 Statutory Compliance/i)).toBeInTheDocument()
    expect(screen.getByText('Section 63 Certificate Preparation')).toBeInTheDocument()
    expect(screen.getByText(/RFC 6962 prefix-hardened binary Merkle tree roots/i)).toBeInTheDocument()
  })

  it('renders Tamper-Evident Ledger Anchors section and cards', async () => {
    renderWithClient(<Audit />)

    expect(screen.getByText('Tamper-Evident Ledger Anchors')).toBeInTheDocument()
    expect(await screen.findByText('ANCHOR-2026-A1B2C3D4', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText('Block #1')).toBeInTheDocument()
    expect(screen.getByText('NEXUS-POLICE-HQ')).toBeInTheDocument()
  })

  it('verifies anchored block on demand and shows INTEGRITY VERIFIED badge', async () => {
    renderWithClient(<Audit />)

    expect(await screen.findByText('ANCHOR-2026-A1B2C3D4', {}, { timeout: 10000 })).toBeInTheDocument()
    const verifyButtons = screen.getAllByRole('button', { name: /^Verify$/i })
    expect(verifyButtons.length).toBeGreaterThanOrEqual(1)

    fireEvent.click(verifyButtons[0])

    expect(await screen.findByText(/INTEGRITY VERIFIED/i, {}, { timeout: 10000 })).toBeInTheDocument()
  })

  it('opens row inspection and allows viewing Merkle inclusion proof modal', async () => {
    renderWithClient(<Audit />)

    expect(await screen.findByText('officer_sp', {}, { timeout: 10000 })).toBeInTheDocument()

    // Click expand chevron
    const chevronButton = screen.getByRole('button', { name: 'View technical proof for evt-001' })
    fireEvent.click(chevronButton)

    // Inspect Merkle inclusion proof button should be present
    const proofButton = await screen.findByText(/Inspect Merkle Inclusion Proof \(Sec\. 63 BSA\)/i, {}, { timeout: 10000 })
    expect(proofButton).toBeInTheDocument()

    fireEvent.click(proofButton)

    // Merkle modal opens
    expect(await screen.findByText('Section 63 BSA Merkle Audit Inclusion Certificate', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(await screen.findByText(/MATHEMATICALLY VERIFIED/i, {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText(/Step 1 \(right\)/i)).toBeInTheDocument()
  })
})
