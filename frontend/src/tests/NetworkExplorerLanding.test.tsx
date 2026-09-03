/**
 * frontend/src/tests/NetworkExplorerLanding.test.tsx
 *
 * Tests verifying that Global Network Explorer (/network) does NOT auto-load
 * the FIR-141/FIR-207 demo investigation graph by default, and behaves as a genuine
 * global network exploration workspace while keeping Pathfinder fully functional.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { nexusHandlers } from '@/lib/mocks/nexusHandlers'
import NetworkExplorer from '@/pages/NetworkExplorer'

const server = setupServer(...nexusHandlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function createWrapper(initialEntries: string[] = ['/network']) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return ({ children }: { children?: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Global Network Explorer Landing Experience', () => {
  it('opens /network without automatically loading FIR-141/FIR-207 demo case graph', async () => {
    const Wrapper = createWrapper(['/network'])
    render(
      <Wrapper>
        <NetworkExplorer />
      </Wrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Global Network Explorer')).toBeInTheDocument()
      expect(screen.getByText(/Multi-jurisdictional criminal network topology/i)).toBeInTheDocument()
    })

    // Confirms "No investigation selected" empty workspace banner is NOT visible, 
    // because the global network should render by default.
    expect(screen.queryByText(/No investigation selected/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Select entities or open a case to explore its network/i)).not.toBeInTheDocument()

    // Confirms snapshot graph is NOT rendered automatically
    expect(screen.queryByTestId('snapshot-label')).not.toBeInTheDocument()
  })

  it('defaults the Focus selector to All for a case network', async () => {
    const Wrapper = createWrapper(['/network?case_id=CASE-141'])
    render(
      <Wrapper>
        <NetworkExplorer />
      </Wrapper>
    )

    await waitFor(() => {
      expect(screen.getByTestId('snapshot-label')).toBeInTheDocument()
      expect(screen.getByLabelText('Focus')).toHaveValue('ALL')
    }, { timeout: 8000 })
  })

  it('honors an explicit case focus in the URL', async () => {
    const Wrapper = createWrapper(['/network?case_id=CASE-141&case_focus=CASE-141'])
    render(
      <Wrapper>
        <NetworkExplorer />
      </Wrapper>
    )

    await waitFor(() => expect(screen.getByLabelText('Focus')).toHaveValue('CASE-141'), { timeout: 8000 })
  })

  it('allows opening the Pathfinder and selecting entities without pre-selected demo values', async () => {
    const Wrapper = createWrapper(['/network'])
    render(
      <Wrapper>
        <NetworkExplorer />
      </Wrapper>
    )

    // Click Investigative Pathfinder button
    const pathfinderBtn = screen.getByRole('button', { name: /Investigative Pathfinder/i })
    fireEvent.click(pathfinderBtn)

    await waitFor(() => {
      expect(screen.getByText(/Interactive Graph Pathfinder/i)).toBeInTheDocument()
    })

    // Both source and target entity selectors show empty placeholder state
    const placeholders = screen.getAllByText(/Select entity or case\.\.\./i)
    expect(placeholders.length).toBeGreaterThanOrEqual(2)
  })

  it('loads the graph and calculates path when a preset is applied', async () => {
    const Wrapper = createWrapper(['/network'])
    render(
      <Wrapper>
        <NetworkExplorer />
      </Wrapper>
    )

    // Open Pathfinder
    const pathfinderBtn = screen.getByRole('button', { name: /Investigative Pathfinder/i })
    fireEvent.click(pathfinderBtn)

    await waitFor(() => {
      expect(screen.getByText(/🌟 FIR-141 ↔ FIR-207/i)).toBeInTheDocument()
    })

    // Click preset
    fireEvent.click(screen.getByText(/🌟 FIR-141 ↔ FIR-207/i))

    await waitFor(() => {
      expect(screen.getByText(/Connected in/i)).toBeInTheDocument()
      expect(screen.getByTestId('snapshot-label')).toBeInTheDocument()
    }, { timeout: 8000 })
  })

  it('automatically opens case graph when navigating with ?case_id=CASE-141 query parameter', async () => {
    const Wrapper = createWrapper(['/network?case_id=CASE-141'])
    render(
      <Wrapper>
        <NetworkExplorer />
      </Wrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Global Network Explorer')).toBeInTheDocument()
      expect(screen.getByTestId('snapshot-label')).toBeInTheDocument()
    }, { timeout: 8000 })
  })
})
