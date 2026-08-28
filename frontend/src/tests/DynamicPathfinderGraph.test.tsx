/**
 * frontend/src/tests/DynamicPathfinderGraph.test.tsx
 *
 * Tests verifying that Pathfinder graph visualization is dynamic and context-aware:
 * When arbitrary entities (e.g. Sunil Shetty -> Sunil Gupta) are selected in Pathfinder,
 * the displayed graph contains those specific entities and connections and NEVER silently
 * falls back to the hardcoded FIR-141/FIR-207 demo graph.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { nexusHandlers } from '@/lib/mocks/nexusHandlers'
import NetworkExplorer from '@/pages/NetworkExplorer'
import { UIProvider } from '@/contexts/UIContext'
import { AuthProvider } from '@/contexts/AuthContext'
import React from 'react'

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
      <AuthProvider>
        <UIProvider>
          <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
        </UIProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('Dynamic Pathfinder Graph Synchronization', () => {
  it('renders dynamic graph for Sunil Shetty (person-0040) -> Sunil Gupta (person-0037) without demo graph fallback', async () => {
    const Wrapper = createWrapper(['/network'])
    render(
      <Wrapper>
        <NetworkExplorer />
      </Wrapper>
    )

    // Open Pathfinder
    const openPathfinderBtn = screen.getByRole('button', { name: /Investigative Pathfinder/i })
    fireEvent.click(openPathfinderBtn)

    // Select Source Entity (person-0040 / Sunil Shetty)
    const sourceBtn = screen.getByTestId('pathfinder-source-select')
    fireEvent.click(sourceBtn)
    const sourceSearch = screen.getByPlaceholderText(/Search cases, suspects/i)
    fireEvent.change(sourceSearch, { target: { value: 'Sunil Shetty' } })
    const shettyOpt = await screen.findByText('Sunil Shetty')
    fireEvent.click(shettyOpt.closest('button') || shettyOpt)

    // Select Target Entity (person-0037 / Sunil Gupta)
    const targetBtn = screen.getByTestId('pathfinder-target-select')
    fireEvent.click(targetBtn)
    const targetSearch = screen.getByPlaceholderText(/Search cases, suspects/i)
    fireEvent.change(targetSearch, { target: { value: 'Sunil Gupta' } })
    const guptaOpt = await screen.findByText('Sunil Gupta')
    fireEvent.click(guptaOpt.closest('button') || guptaOpt)

    // Wait for path and graph to render
    await waitFor(() => {
      expect(screen.getByText(/Connected in 1 Hop/i)).toBeInTheDocument()
      expect(screen.getByTestId('snapshot-label')).toBeInTheDocument()
    }, { timeout: 10000 })

    // Confirms snapshot label references the dynamic entity
    expect(screen.getByText('ENTITY-person-0040')).toBeInTheDocument()

    // Confirms Pathfinder explanation contains the discovered path
    expect(screen.getByText(/Sunil Shetty ➔ Sunil Gupta/i)).toBeInTheDocument()

    // CRITICAL: Confirms the unrelated demo graph nodes/snapshots are NOT in the active view
    expect(screen.queryByText('SNAP-BEFORE-001')).not.toBeInTheDocument()
    expect(screen.queryByText('SNAP-AFTER-002')).not.toBeInTheDocument()
    expect(screen.queryByText('Rafiq Khan')).not.toBeInTheDocument()
    expect(screen.queryByText('Meena Devi')).not.toBeInTheDocument()
    expect(screen.queryByText('Deepak Rao')).not.toBeInTheDocument()
  }, 15000)
})
