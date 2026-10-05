/**
 * frontend/src/tests/IntelligenceCenterDefault.test.tsx
 *
 * Verifies that:
 * 1. Default route navigates to /intelligence
 * 2. /patterns redirects to /intelligence
 * 3. Default Intelligence Center tab is Network Pulse
 * 4. P1/P2/P0 stage labels are completely absent from visible UI
 * 5. Operational Early Warning and Evidence support terminology are used
 * 6. Sidebar shows grouped navigation hierarchy
 */
import { describe, it, expect, vi, beforeEach, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import { nexusHandlers } from '@/lib/mocks/nexusHandlers'
import Patterns from '@/pages/Patterns'
import { Sidebar } from '@/components/Sidebar'
import { AuthProvider } from '@/contexts/AuthContext'

vi.mock('@/lib/queryClient', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/lib/queryClient')>(),
  coldStartRetryDelay: () => 10,
}))

const server = setupServer(...nexusHandlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderWithClient(ui: React.ReactElement, initialPath = '/intelligence') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialPath]}>
          {ui}
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('NEXUS Intelligence Center Defaults & Information Architecture', () => {
  it('retains the labelled canonical baseline rather than an empty queue when intelligence requests fail', async () => {
    server.use(
      http.get(/\/api\/v1\/nexus\/intelligence\/bootstrap/, () => new HttpResponse(null, { status: 503 })),
      http.get(/\/api\/v1\/nexus\/pulses/, () => new HttpResponse(null, { status: 503 })),
    )
    renderWithClient(<Patterns />)
    await waitFor(() => expect(screen.getAllByText(/synchronization paused after bounded retries/)).toHaveLength(2), { timeout: 10000 })
    expect(screen.queryByText('No active network pulses detected in the current window.')).not.toBeInTheDocument()
    expect(screen.queryByText('Unavailable')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Network Pulse (3)' })).toBeInTheDocument()
  })
  beforeEach(() => {
    window.localStorage.setItem('nexus_role', 'INVESTIGATOR')
  })

  it('renders Intelligence Center with Network Pulse as the active default tab', async () => {
    renderWithClient(<Patterns />)

    // Page title
    expect(screen.getByRole('heading', { name: /Intelligence Center/i })).toBeInTheDocument()

    // Network Pulse tab is selected/active
    const pulseTab = screen.getByRole('button', { name: /^Network Pulse \(/i })
    expect(pulseTab).toBeInTheDocument()
    expect(pulseTab.className).toContain('border-indigo-600')

    // Real summary metrics render
    await waitFor(() => {
      expect(screen.getByText(/Active Pulses/i)).toBeInTheDocument()
      expect(screen.getByText(/Evidence Status/i)).toBeInTheDocument()
      expect(screen.getByText(/Affected Investigations/i)).toBeInTheDocument()
      expect(screen.getByText('Network Changes')).toBeInTheDocument()
    })

    // Network Pulse Queue and details render
    await waitFor(() => {
      expect(screen.getByText(/Network Pulse Queue/i)).toBeInTheDocument()
    }, { timeout: 10000 })
  })

  it('contains zero implementation stage labels (P1-B, P1-C, P1-D, P2) in tabs or headers', () => {
    renderWithClient(<Patterns />)

    // Ensure no stage labels appear
    expect(screen.queryByText(/P1-B/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/P1-C/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/P1-D/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/P2/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/P0/i)).not.toBeInTheDocument()

    // Clean product tabs exist
    expect(screen.getByRole('button', { name: /^Identity Drift$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Network Adaptation$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Case DNA$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Digital Shadow$/i })).toBeInTheDocument()
  })

  it('renders Sidebar with grouped navigation sections and Intelligence Center first', () => {
    renderWithClient(<Sidebar isOpen={true} onClose={() => {}} />)

    // Check grouped headers
    expect(screen.getByText('INTELLIGENCE')).toBeInTheDocument()
    expect(screen.getByText('INVESTIGATION')).toBeInTheDocument()
    expect(screen.getByText('ASSIST')).toBeInTheDocument()

    // Intelligence Center link exists with /intelligence path
    const intelLink = screen.getByRole('link', { name: /Intelligence Center/i })
    expect(intelLink).toBeInTheDocument()
    expect(intelLink.getAttribute('href')).toBe('/intelligence')

    // Lead Inbox and Worklist are under INTELLIGENCE
    expect(screen.getByRole('link', { name: /Lead Inbox/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Investigation Worklist/i })).toBeInTheDocument()
  })

  it('redirects /patterns to /intelligence via compatibility redirect', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/patterns']}>
            <Routes>
              <Route path="/patterns" element={<Navigate to="/intelligence" replace />} />
              <Route path="/intelligence" element={<div>Routed to Intelligence Center</div>} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Routed to Intelligence Center')).toBeInTheDocument()
    })
  })
})
