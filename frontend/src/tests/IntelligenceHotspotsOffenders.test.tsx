/**
 * frontend/src/tests/IntelligenceHotspotsOffenders.test.tsx
 *
 * Vitest tests for Crime Hotspots, Repeat Offender Radar,
 * Combined Cross-District Bridges, and District Drilldown Modal.
 */
import { describe, it, expect, beforeEach, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { nexusHandlers } from '@/lib/mocks/nexusHandlers'
import Patterns from '@/pages/Patterns'

const server = setupServer(...nexusHandlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderPatterns() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Patterns />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Criminal Network Intelligence Hub & Crime Hotspots', () => {
  beforeEach(() => {
    window.localStorage.setItem('nexus_role', 'INVESTIGATOR')
  })


  it('renders Crime Hotspots tab by default with RED FLAG concentration cards', async () => {
    renderPatterns()

    // Tab buttons
    expect(screen.getByRole('button', { name: /Crime Hotspots/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Repeat Offender Radar/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Combined Cross-District Bridges/i })).toBeInTheDocument()

    // Compliance banner
    expect(screen.getByText(/Investigative Use Only/i)).toBeInTheDocument()

    // Wait for Hotspot Card
    await waitFor(() => {
      expect(screen.getByText('Mumbai Central')).toBeInTheDocument()
    })

    // Exact user-specified elements
    expect(screen.getAllByText(/RED FLAG — HIGH CRIME CONCENTRATION/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/3.4× baseline/i)).toBeInTheDocument()
    expect(screen.getByText('87')).toBeInTheDocument()
    expect(screen.getByText('Narcotics')).toBeInTheDocument()
    expect(screen.getByText('14')).toBeInTheDocument()
    expect(screen.getByText(/6 persons/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Evidence-backed: Yes/i).length).toBeGreaterThan(0)
  })

  it('opens district drilldown modal when clicking drill into cases', async () => {
    renderPatterns()

    await waitFor(() => {
      expect(screen.getByText('Mumbai Central')).toBeInTheDocument()
    })

    const drillButtons = screen.getAllByRole('button', { name: /Drill into cases/i })
    fireEvent.click(drillButtons[0])

    // Verify modal elements
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /District: Mumbai Central/i })).toBeInTheDocument()
      expect(screen.getByText(/Underlying Cases/i)).toBeInTheDocument()
      expect(screen.getByText('FIR-2026-141')).toBeInTheDocument()
      expect(screen.getByText('FIR-2026-142')).toBeInTheDocument()
    })

    // Switch to Accused & Entities tab in modal
    const entitiesTab = screen.getByRole('button', { name: /Accused & Entities/i })
    fireEvent.click(entitiesTab)
    await waitFor(() => {
      expect(screen.getByText('Ramesh Hegde')).toBeInTheDocument()
      expect(screen.getByText('Sunil Gupta')).toBeInTheDocument()
    })

    // Close modal
    const closeBtn = screen.getByRole('button', { name: /Close Drilldown/i })
    fireEvent.click(closeBtn)

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /District: Mumbai Central/i })).not.toBeInTheDocument()
    })
  })

  it('renders Repeat Offender Radar tab with resolved aliases and non-guilt compliance status', async () => {
    renderPatterns()

    const radarTab = screen.getByRole('button', { name: /Repeat Offender Radar/i })
    fireEvent.click(radarTab)

    // Wait for Radar Card
    await waitFor(() => {
      expect(screen.getByText('Ramesh Hegde')).toBeInTheDocument()
    })

    // Exact user-specified elements
    expect(screen.getAllByText(/REPEAT-OFFENDER SIGNAL/i).length).toBeGreaterThan(0)
    expect(screen.getByText('Ramesh H.')).toBeInTheDocument()
    expect(screen.getByText('R. Hegde')).toBeInTheDocument()
    expect(screen.getByText(/3 districts \(Mumbai Central, Pune City, Thane\)/i)).toBeInTheDocument()
    expect(screen.getByText(/2 aliases/i)).toBeInTheDocument()
    expect(screen.getByText(/4 entities/i)).toBeInTheDocument()
    expect(screen.getByText(/2 identifiers/i)).toBeInTheDocument()
    expect(screen.getByText('FIR-2026-142')).toBeInTheDocument()
    expect(screen.getByText(/Deterministic repeat-case \+ entity-resolution evidence\./i)).toBeInTheDocument()
    expect(screen.getByText(/Status: Investigative lead — not a finding of guilt\./i)).toBeInTheDocument()
  })

  it('renders Combined Cross-District Bridges tab with bridge detection alerts', async () => {
    renderPatterns()

    const bridgeTab = screen.getByRole('button', { name: /Combined Cross-District Bridges/i })
    fireEvent.click(bridgeTab)

    await waitFor(() => {
      expect(screen.getByText(/Primary District: Mumbai Central/i)).toBeInTheDocument()
    })

    expect(screen.getAllByText(/RED FLAG — Cross-District Criminal Network Bridge/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/Crime hotspot: District Mumbai Central \(87 cases\)/i)).toBeInTheDocument()
    expect(screen.getByText(/Cross-case bridge detected\./i)).toBeInTheDocument()
    expect(screen.getByText(/Bridges Mumbai Central ↔ Pune City, Thane/i)).toBeInTheDocument()
  })

  it('switches to Network Modules & Brokers tab and renders communities', async () => {
    renderPatterns()

    const commTab = screen.getByRole('button', { name: /Network Modules & Brokers/i })
    fireEvent.click(commTab)

    expect(await screen.findByText(/Detected Network Modules \/ Communities/i)).toBeInTheDocument()
    expect(screen.getByText(/Bridge Nodes & Articulation Points/i)).toBeInTheDocument()
  })

})
