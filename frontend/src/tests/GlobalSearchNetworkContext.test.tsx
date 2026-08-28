/**
 * frontend/src/tests/GlobalSearchNetworkContext.test.tsx
 *
 * Tests verifying that Global Search & Navigation accurately propagate entity context
 * to Network Explorer and that Network Explorer dynamically renders the selected entity's
 * actual intelligence subgraph without silently falling back to unrelated demo graphs.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { nexusHandlers } from '@/lib/mocks/nexusHandlers'
import NetworkExplorer from '@/pages/NetworkExplorer'
import { Header } from '@/components/Header'
import { UIProvider } from '@/contexts/UIContext'
import { AuthProvider } from '@/contexts/AuthContext'
import React from 'react'

const server = setupServer(...nexusHandlers)

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location-search">{location.search}</output>
}

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function createWrapper(initialEntries: string[] = ['/network?node_id=person-0073']) {
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

describe('Global Search to Network Explorer Context Propagation', () => {
  it('renders selected entity network graph for Vinod Sharma (person-0073) without demo fallback', async () => {
    const Wrapper = createWrapper(['/network?node_id=person-0073'])
    render(
      <Wrapper>
        <NetworkExplorer />
      </Wrapper>
    )

    // Wait for graph to load
    await waitFor(() => {
      expect(screen.getByText('Global Network Explorer')).toBeInTheDocument()
      expect(screen.getByTestId('snapshot-label')).toBeInTheDocument()
    }, { timeout: 10000 })

    // Confirms snapshot label references the entity ID
    expect(screen.getByText('ENTITY-person-0073')).toBeInTheDocument()

    // Confirms Pathfinder source is synchronized to Vinod Sharma
    expect(screen.getAllByText(/Vinod Sharma/i).length).toBeGreaterThan(0)
    expect(screen.getByText('(person-0073)')).toBeInTheDocument()

    // Confirms unrelated demo case graph is NOT rendered
    expect(screen.queryByText('SNAP-BEFORE-001')).not.toBeInTheDocument()
    expect(screen.queryByText('SNAP-AFTER-002')).not.toBeInTheDocument()
  }, 15000)

  it('displays clear message when selected entity has no recorded graph connections', async () => {
    const Wrapper = createWrapper(['/network?node_id=empty-entity'])
    render(
      <Wrapper>
        <NetworkExplorer />
      </Wrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/No graph relationships found for entity/i)).toBeInTheDocument()
      expect(screen.getAllByText('empty-entity').length).toBeGreaterThan(0)
    }, { timeout: 10000 })

    // Confirms it does NOT silently fall back to demo snapshot
    expect(screen.queryByTestId('snapshot-label')).not.toBeInTheDocument()
    expect(screen.queryByText('SNAP-BEFORE-001')).not.toBeInTheDocument()
  }, 15000)

  it('closes the entity drawer and removes the URL selection', async () => {
    const Wrapper = createWrapper(['/network?node_id=person-0073'])
    render(
      <Wrapper>
        <LocationProbe />
        <NetworkExplorer />
      </Wrapper>
    )

    await waitFor(() => expect(screen.getByRole('dialog', { name: /Entity intelligence drawer/i })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /Close entity drawer/i }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /Entity intelligence drawer/i })).not.toBeInTheDocument()
      expect(screen.getByTestId('location-search')).toHaveTextContent('')
    })
  })

  it('navigates from Header Global Search to Network Explorer and loads entity network', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <UIProvider>
            <MemoryRouter initialEntries={['/']}>
              <Header onMenuToggle={() => {}} />
              <Routes>
                <Route path="/" element={<div>Home</div>} />
                <Route path="/network" element={<NetworkExplorer />} />
              </Routes>
            </MemoryRouter>
          </UIProvider>
        </AuthProvider>
      </QueryClientProvider>
    )

    // Open search and search for Vinod
    const searchInput = screen.getByPlaceholderText(/Search cases, FIRs, suspects/i)
    fireEvent.change(searchInput, { target: { value: 'Vinod' } })

    // Find and click Vinod Sharma in the search results
    await waitFor(() => {
      expect(screen.getByText('Vinod Sharma')).toBeInTheDocument()
    }, { timeout: 10000 })

    const vinodResult = screen.getByText('Vinod Sharma')
    fireEvent.click(vinodResult)

    // Verify Network Explorer mounted with Vinod Sharma's graph
    await waitFor(() => {
      expect(screen.getByText('Global Network Explorer')).toBeInTheDocument()
      expect(screen.getByText('ENTITY-person-0073')).toBeInTheDocument()
    }, { timeout: 10000 })
  }, 15000)
})
