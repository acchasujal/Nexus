import { describe, it, expect, afterEach, beforeAll, afterAll, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { setupServer } from 'msw/node'
import { nexusHandlers } from '@/lib/mocks/nexusHandlers'
import { AuthProvider } from '@/contexts/AuthContext'
import { UIProvider } from '@/contexts/UIContext'
import { AppShell } from '@/components/AppShell'
import Patterns from '@/pages/Patterns'
import EntityFusion from '@/pages/EntityFusion'
import LeadInbox from '@/pages/LeadInbox'

const server = setupServer(...nexusHandlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderWithProviders(ui: React.ReactElement, initialRoute = '/patterns') {
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
      <AuthProvider>
        <UIProvider>
          <MemoryRouter initialEntries={[initialRoute]}>
            {ui}
          </MemoryRouter>
        </UIProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('Responsive Workspace & Viewport Adaptation', () => {
  const originalInnerWidth = window.innerWidth

  beforeEach(() => {
    window.localStorage.setItem('nexus_role', 'INVESTIGATOR')
  })

  afterEach(() => {
    window.innerWidth = originalInnerWidth
  })

  it('renders AppShell with responsive mobile layout and toggles slide-over sidebar', async () => {
    window.innerWidth = 375 // Mobile iPhone width

    renderWithProviders(
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route path="patterns" element={<Patterns />} />
        </Route>
      </Routes>,
      '/patterns'
    )

    // Mobile Hamburger button should be in the DOM
    const menuButton = screen.getByLabelText(/Toggle Navigation Menu/i)
    expect(menuButton).toBeInTheDocument()

    // Clicking hamburger opens mobile sidebar
    fireEvent.click(menuButton)

    // Navigation item should be visible in slide-over
    expect(screen.getByText('Network Explorer')).toBeInTheDocument()
  })

  it('renders responsive Patterns Intelligence Hub with touch-scrollable tabs and cards', async () => {
    window.innerWidth = 768 // Tablet iPad width

    renderWithProviders(<Patterns />, '/patterns')

    // Expect Intelligence Hub banner & tabs
    expect(screen.getByText(/Criminal Network Intelligence Hub/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Crime Hotspots/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Repeat Offender Radar/i })).toBeInTheDocument()

    // Wait for Hotspot cards to render
    await waitFor(() => {
      expect(screen.getByText('Mumbai Central')).toBeInTheDocument()
    })

    // Drilldown button clickable
    const drillBtn = screen.getAllByText(/Drill into cases/i)[0]
    expect(drillBtn).toBeInTheDocument()
    fireEvent.click(drillBtn)

    // Modal opens with responsive tabs
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText(/RED FLAG HOTSPOT/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Underlying Cases/i })).toBeInTheDocument()
    })
  })

  it('renders Entity Fusion Workbench with responsive candidate tabs and decision bar', async () => {
    window.innerWidth = 375 // Mobile iPhone width

    renderWithProviders(<EntityFusion />, '/fusion')

    await waitFor(() => {
      expect(screen.getByText(/Entity Fusion Workbench/i)).toBeInTheDocument()
    })

    // Candidates and match score should render
    await waitFor(() => {
      expect(screen.getByTestId('match-score')).toBeInTheDocument()
      expect(screen.getByTestId('confirm-fusion')).toBeInTheDocument()
    })
  })

  it('renders Lead Inbox with adaptive responsive layout', async () => {
    window.innerWidth = 375 // Mobile width

    renderWithProviders(<LeadInbox />, '/leads')

    await waitFor(() => {
      expect(screen.getByText(/Lead Inbox/i)).toBeInTheDocument()
      expect(screen.getByText(/No open leads/i)).toBeInTheDocument()
    })
  })
})
