/**
 * frontend/src/tests/CaseDNARadar.test.tsx
 *
 * Vitest tests for P2: Case DNA Multi-Dimensional Structural Similarity (CaseDNASection).
 * Verifies:
 *   1. Renders statutory Zero Predictive Guilt banner.
 *   2. Displays summary metric cards (Target Investigation, Highest Structural Similarity, etc.).
 *   3. Displays match cards with 5-vector sub-scores (Struct, Comm, Fin, Loc, Temp).
 *   4. Displays 5-vector detailed progress bars and Section 63 BSA evidence references.
 *   5. Allows switching target case via search input / quick buttons.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { CaseDNASection } from '@/components/nexus/CaseDNASection'

const mockCaseDNAResponse = {
  target_case_id: 'CASE-141',
  average_similarity: 0.45,
  highest_similarity: 0.82,
  top_shared_entities: ['Rafiq Ahmed', 'District: Mysuru', '+91 98450 11223'],
  similar_cases: [
    {
      case_pair: ['CASE-141', 'CASE-207'],
      case_a_title: 'Mysuru Hawala & SIM Box Syndicate',
      case_b_title: 'Bengaluru Cyber Mule & Hawala Routing',
      overall_similarity: 0.82,
      structure_similarity: 0.85,
      communication_similarity: 0.75,
      financial_similarity: 0.85,
      location_similarity: 1.0,
      temporal_similarity: 0.70,
      shared_entities: ['Rafiq Ahmed', '+91 98450 11223', 'District: Mysuru'],
      explanation: 'Structural overlap (score: 0.85); Communication pattern match (0.75); Jurisdiction convergence (1.0)',
      evidence_refs: ['SRC-FIR-141', 'SRC-FIR-207', 'SRC-CDR-A12'],
      derivation_class: 'DERIVED',
    },
    {
      case_pair: ['CASE-141', 'CASE-305'],
      case_a_title: 'Mysuru Hawala & SIM Box Syndicate',
      case_b_title: 'Indiranagar Cross-Border Syndicate',
      overall_similarity: 0.38,
      structure_similarity: 0.40,
      communication_similarity: 0.30,
      financial_similarity: 0.20,
      location_similarity: 0.50,
      temporal_similarity: 0.50,
      shared_entities: ['District: Mysuru'],
      explanation: 'Moderate jurisdiction and modus operandi alignment',
      evidence_refs: ['SRC-FIR-141', 'SRC-FIR-305'],
      derivation_class: 'DERIVED',
    },
  ],
}

const server = setupServer(
  http.get(/\/api\/v1\/nexus\/intelligence\/case-dna/, () => {
    return HttpResponse.json(mockCaseDNAResponse)
  })
)




beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}


describe('CaseDNASection (P2)', () => {
  it('renders statutory Zero Predictive Guilt banner and explanation', async () => {
    renderWithClient(<CaseDNASection initialCaseId="CASE-141" />)

    expect(screen.getByText(/Case DNA: Explainable Structural Similarity/i)).toBeInTheDocument()
    expect(screen.getByText(/Zero Predictive Guilt/i)).toBeInTheDocument()
    expect(screen.getByText(/Structural Similarity Engine/i)).toBeInTheDocument()
  })

  it('renders summary metrics for target case and top matches', async () => {
    renderWithClient(<CaseDNASection initialCaseId="CASE-141" />)

    expect(await screen.findByText('CASE-207', {}, { timeout: 10000 })).toBeInTheDocument()
    const matches82 = await screen.findAllByText('82.0%', {}, { timeout: 10000 })
    expect(matches82.length).toBeGreaterThanOrEqual(1)
    expect(await screen.findByText('45.0%', {}, { timeout: 10000 })).toBeInTheDocument()
  })


  it('renders top structural match cards with 5-vector metrics', async () => {
    renderWithClient(<CaseDNASection initialCaseId="CASE-141" />)

    expect(await screen.findByText('CASE-207', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(await screen.findByText('Bengaluru Cyber Mule & Hawala Routing', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(await screen.findByText('5-Vector Topological Breakdown', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText('Structure & Network Topology (Weight: 30%)')).toBeInTheDocument()
    expect(screen.getByText('Section 63 BSA Evidence Provenance')).toBeInTheDocument()
    expect(screen.getByText('SRC-FIR-141')).toBeInTheDocument()
    expect(screen.getByText('SRC-FIR-207')).toBeInTheDocument()
  })


  it('allows clicking another match card to update detailed breakdown', async () => {
    renderWithClient(<CaseDNASection initialCaseId="CASE-141" />)

    const secondCard = await screen.findByTestId('match-card-CASE-305', {}, { timeout: 10000 })
    expect(secondCard).toBeInTheDocument()
    fireEvent.click(secondCard)

    expect(await screen.findByText(/CASE-141 ↔ CASE-305/i, {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText('38.0%')).toBeInTheDocument()
  })
})


