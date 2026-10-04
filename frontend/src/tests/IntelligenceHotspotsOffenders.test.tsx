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
import { http, HttpResponse } from 'msw'
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


  it('renders Network Pulse tab by default and switches to Crime Hotspots tab with concentration cards', async () => {
    renderPatterns()

    // Default tab is Network Pulse
    expect(screen.getByRole('button', { name: /Network Pulse/i })).toBeInTheDocument()

    // Tab buttons exist
    expect(screen.getByRole('button', { name: /Crime Hotspots/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Repeat-Case Entities/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Cross-District Bridges/i })).toBeInTheDocument()

    // Compliance banner
    expect(screen.getByText(/Investigative Use Only/i)).toBeInTheDocument()

    // Switch to Crime Hotspots tab
    const hotspotsTab = screen.getByRole('button', { name: /Crime Hotspots/i })
    fireEvent.click(hotspotsTab)

    // Wait for Hotspot Card
    await waitFor(() => {
      expect(screen.getByText('Mumbai Central')).toBeInTheDocument()
    }, { timeout: 10000 })

    // Exact user-specified elements
    expect(screen.getAllByText(/High Concentration — Review Required/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/3.4× baseline/i)).toBeInTheDocument()
    expect(screen.getByText('87')).toBeInTheDocument()
    expect(screen.getByText('Narcotics')).toBeInTheDocument()
    expect(screen.getByText('14')).toBeInTheDocument()
    expect(screen.getByText(/6 persons/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Evidence-backed: Yes/i).length).toBeGreaterThan(0)
  })

  it('opens district drilldown modal when clicking drill into cases', async () => {
    renderPatterns()

    // Switch to Crime Hotspots tab
    const hotspotsTab = screen.getByRole('button', { name: /Crime Hotspots/i })
    fireEvent.click(hotspotsTab)

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

  it('renders Repeat-Case Entities tab with resolved aliases and non-guilt compliance status', async () => {
    renderPatterns()

    const radarTab = screen.getByRole('button', { name: /Repeat-Case Entities/i })
    fireEvent.click(radarTab)

    // Wait for Radar Card
    await waitFor(() => {
      expect(screen.getByText('Ramesh Hegde')).toBeInTheDocument()
    })

    // Exact user-specified elements
    expect(screen.getAllByText(/Repeat-Case Signal/i).length).toBeGreaterThan(0)
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

  it('renders Cross-District Bridges tab with bridge detection alerts', async () => {
    renderPatterns()

    const bridgeTab = screen.getByRole('button', { name: /Cross-District Bridges/i })
    fireEvent.click(bridgeTab)

    await waitFor(() => {
      expect(screen.getByText(/Primary District: Mumbai Central/i)).toBeInTheDocument()
    })

    expect(screen.getAllByText(/RED FLAG — Cross-District Criminal Network Bridge/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/Crime hotspot: District Mumbai Central \(87 cases\)/i)).toBeInTheDocument()
    expect(screen.getByText(/Cross-case bridge detected\./i)).toBeInTheDocument()
    expect(screen.getByText(/Bridges Mumbai Central ↔ Pune City, Thane/i)).toBeInTheDocument()
  })

  it('switches to Network Communities & Connectors tab and renders communities', async () => {
    server.use(
      http.get('*/api/v1/communities', () => HttpResponse.json([])),
      http.get('*/api/v1/influence/bridges', () => HttpResponse.json([])),
    )
    renderPatterns()

    const commTab = screen.getByRole('button', { name: /Network Communities & Connectors/i })
    fireEvent.click(commTab)

    expect(await screen.findByText(/Detected Network Modules \/ Communities/i, {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText(/Bridge Nodes & Articulation Points/i)).toBeInTheDocument()
  })

})
