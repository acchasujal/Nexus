/**
 * OfficerLogin.test.tsx
 *
 * Comprehensive integration tests for NEXUS Officer Authentication Flow:
 * - Professional Login Page rendering, form fields, and security notices
 * - Successful authentication with backend API integration
 * - Authentication refusal / error message rendering
 * - Loading spinner and disabled states during submission
 * - Demo profile quick-select helper
 * - Header authoritative Officer Identity rendering (name, rank, badge, role)
 * - Verification that role-switching select dropdown is completely removed
 * - Logout clearing session state and storage
 * - Protected route redirection when unauthenticated
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Login from '@/pages/Login'
import { Header } from '@/components/Header'
import { AuthProvider, AuthContext, useAuth } from '@/contexts/AuthContext'
import { UIProvider } from '@/contexts/UIContext'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { apiClient, ApiError } from '@/lib/apiClient'
import { AppShell } from '@/components/AppShell'
import { RoleGuard } from '@/components/RoleGuard'
import { useQuery } from '@tanstack/react-query'
import type { OfficerUser } from '@/contexts/AuthContext'

vi.mock('@/lib/queryClient', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/lib/queryClient')>(),
  coldStartRetryDelay: () => 10,
}))

// Helper component to display auth status
function DummyWorklist() {
  const { user, role, logout } = useAuth()
  return (
    <div>
      <div data-testid="worklist-content">Worklist Page</div>
      <div data-testid="auth-user">{user?.name}</div>
      <div data-testid="auth-role">{role}</div>
      <button onClick={logout} data-testid="test-logout-btn">Test Logout</button>
    </div>
  )
}

function renderLoginWithRouter(initialEntry = '/login') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  const view = render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/intelligence" element={<DummyWorklist />} />
            <Route path="/worklist" element={<DummyWorklist />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
  return { ...view, queryClient }
}

function renderHeaderWithAuth(officer: OfficerUser | null) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const mockLogout = vi.fn()

  return render(
    <QueryClientProvider client={queryClient}>
      <UIProvider>
        <AuthContext.Provider
          value={{
            role: officer?.role || null,
            user: officer,
            isAuthenticated: officer !== null,
            login: vi.fn(),
            logout: mockLogout,
          }}
        >
          <MemoryRouter initialEntries={['/worklist']}>
            <Header onMenuToggle={vi.fn()} />
          </MemoryRouter>
        </AuthContext.Provider>
      </UIProvider>
    </QueryClientProvider>
  )
}

describe('NEXUS Officer Login UI & Authentication Flow', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it.each([
    ['IO', 'KA-1001'], ['SHO', 'KA-1002'], ['SP', 'KA-1003'], ['ADMIN', 'KA-1000'],
  ] as const)('enters the default workspace as %s with one authoritative request', async (role, badge) => {
    const login = vi.spyOn(apiClient, 'login').mockResolvedValueOnce({
      access_token: 'server-issued-session', token_type: 'bearer', user_id: badge, role, expires_in: 86400,
    })
    renderLoginWithRouter()
    await userEvent.click(screen.getByTestId(`demo-officer-${role.toLowerCase()}`))
    await waitFor(() => expect(screen.getByTestId('auth-role')).toHaveTextContent(role))
    expect(login).toHaveBeenCalledExactlyOnceWith({ username: badge, role, password: 'nexus-demo-passcode' })
    expect(localStorage.getItem('nexus_token')).toBe('server-issued-session')
  })

  it('guards repeated clicks synchronously and preserves the selected officer on failure', async () => {
    let reject!: (error: Error) => void
    const login = vi.spyOn(apiClient, 'login').mockImplementationOnce(() => new Promise((_, fail) => { reject = fail }))
    renderLoginWithRouter()
    const button = screen.getByTestId('demo-officer-sho')
    fireEvent.click(button)
    fireEvent.click(button)
    fireEvent.click(screen.getByTestId('demo-officer-admin'))
    expect(login).toHaveBeenCalledTimes(1)
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute('aria-pressed', 'true')
    await act(async () => reject(new ApiError(401, 'Unauthorized', 'Please check your badge')))
    expect(screen.getByRole('alert')).toHaveTextContent(/retry sign-in/i)
    expect(button).toBeEnabled()
    expect(button).toHaveAttribute('aria-pressed', 'true')
    expect(localStorage.getItem('nexus_token')).toBeNull()
    login.mockResolvedValueOnce({ access_token: 'server-issued', token_type: 'bearer', user_id: 'KA-1002', role: 'SHO', expires_in: 86400 })
    await userEvent.click(button)
    await waitFor(() => expect(screen.getByTestId('auth-role')).toHaveTextContent('SHO'))
  })

  it('keeps an exhausted transport failure unauthenticated and retryable', async () => {
    const login = vi.spyOn(apiClient, 'login').mockRejectedValue(new TypeError('Service connection failed'))
    renderLoginWithRouter()
    await userEvent.click(screen.getByTestId('demo-officer-io'))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/retry sign-in/i))
    expect(login).toHaveBeenCalledTimes(4)
    expect(localStorage.getItem('nexus_token')).toBeNull()
    expect(screen.queryByTestId('worklist-content')).not.toBeInTheDocument()
  })

  it('does not restore a role-only or expired stored session', () => {
    localStorage.setItem('nexus_role', 'ADMIN')
    const view = renderLoginWithRouter()
    expect(screen.getByRole('heading', { name: 'NEXUS' })).toBeInTheDocument()
    expect(localStorage.getItem('nexus_token')).toBeNull()
    view.unmount()
    localStorage.setItem('nexus_token', btoa(JSON.stringify({ role: 'ADMIN', exp: 1 })))
    renderLoginWithRouter()
    expect(screen.queryByTestId('worklist-content')).not.toBeInTheDocument()
  })

  it('supports keyboard demo entry and keeps credentials collapsed', async () => {
    const user = userEvent.setup()
    vi.spyOn(apiClient, 'login').mockResolvedValueOnce({ access_token: 'server-issued', token_type: 'bearer', user_id: 'KA-1001', role: 'IO', expires_in: 86400 })
    renderLoginWithRouter()
    expect(screen.getByText('Sign in with officer credentials').closest('details')).not.toHaveAttribute('open')
    expect(screen.getByRole('group', { name: 'Choose your workspace' })).toBeInTheDocument()
    await user.tab()
    expect(screen.getByTestId('demo-officer-io')).toHaveFocus()
    await user.keyboard('{Enter}')
    await waitFor(() => expect(screen.getByTestId('auth-role')).toHaveTextContent('IO'))
  })

  it.each(['pending', 'failed'])('opens the protected shell while intelligence is %s', async state => {
    function Intelligence() {
      const query = useQuery({ queryKey: ['slow-intelligence'], retry: false,
        queryFn: () => state === 'pending' ? new Promise<string>(() => {}) : Promise.reject(new Error('Intelligence offline')) })
      return <p>{query.isError ? 'Intelligence retry available' : 'Intelligence loading'}</p>
    }
    vi.spyOn(apiClient, 'login').mockResolvedValueOnce({ access_token: 'server-issued', token_type: 'bearer', user_id: 'KA-1001', role: 'IO', expires_in: 86400 })
    render(<QueryClientProvider client={new QueryClient()}><AuthProvider><UIProvider><MemoryRouter initialEntries={['/login']}><Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<AppShell />}><Route path="/intelligence" element={<RoleGuard allowedRoles={['IO']}><Intelligence /></RoleGuard>} /></Route>
    </Routes></MemoryRouter></UIProvider></AuthProvider></QueryClientProvider>)
    await userEvent.click(screen.getByTestId('demo-officer-io'))
    await waitFor(() => expect(screen.getByTestId('logout-button')).toBeInTheDocument())
    expect(await screen.findByText(state === 'pending' ? 'Intelligence loading' : 'Intelligence retry available')).toBeInTheDocument()
  })

  it('renders login page with professional branding and inputs', () => {
    renderLoginWithRouter()

    // Brand and subtitle
    expect(screen.getByRole('heading', { name: 'NEXUS', level: 1 })).toBeInTheDocument()
    expect(screen.getByText(/Investigative Network Intelligence Platform/i)).toBeInTheDocument()
    expect(screen.getByText('Officer Authentication Console')).toBeInTheDocument()

    // Inputs
    expect(screen.getByLabelText(/Officer ID \/ Service Identifier/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Security Passcode \/ Token/i)).toBeInTheDocument()
    expect(screen.getByTestId('login-submit-button')).toBeInTheDocument()

    // Demo officers
    expect(screen.getByTestId('demo-officer-io')).toBeInTheDocument()
    expect(screen.getByTestId('demo-officer-sho')).toBeInTheDocument()
    expect(screen.getByTestId('demo-officer-sp')).toBeInTheDocument()
    expect(screen.getByTestId('demo-officer-admin')).toBeInTheDocument()
  })

  it('renders clean centered authentication console', () => {
    renderLoginWithRouter()

    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: /Officer Authentication Form/i })).toBeInTheDocument()
    expect(screen.getByText('Officer Authentication Console')).toBeInTheDocument()
  })

  it('recovers from a cold backend and persists the authoritative session before navigating', async () => {
    const user = userEvent.setup()
    const login = vi.spyOn(apiClient, 'login')
      .mockRejectedValueOnce(new ApiError(503, 'Starting', 'Starting'))
      .mockRejectedValueOnce(new TypeError('fetch failed'))
      .mockResolvedValueOnce({ access_token: 'backend-issued-test-token', token_type: 'bearer', user_id: 'KA-1001', role: 'IO', expires_in: 86400 })
    const { queryClient } = renderLoginWithRouter()
    queryClient.setQueryData(['nexus', 'investigations'], [{ id: 'previous-officer-case' }])
    await user.type(screen.getByTestId('officer-id-input'), 'KA-1001')
    await user.type(screen.getByTestId('password-input'), 'secure-password')
    await user.click(screen.getByTestId('login-submit-button'))
    await waitFor(() => expect(screen.getByTestId('worklist-content')).toBeInTheDocument())
    expect(login).toHaveBeenCalledTimes(3)
    expect(queryClient.getQueryData(['nexus', 'investigations'])).toBeUndefined()
    expect(window.localStorage.getItem('nexus_token')).toBe('backend-issued-test-token')
    queryClient.setQueryData(['nexus', 'investigations'], [{ id: 'current-officer-case' }])
    await user.click(screen.getByTestId('test-logout-btn'))
    expect(queryClient.getQueryData(['nexus', 'investigations'])).toBeUndefined()
    expect(window.localStorage.getItem('nexus_token')).toBeNull()
  })

  it('authenticates officer successfully and redirects to /worklist', async () => {
    const user = userEvent.setup()
    
    // Mock apiClient.login
    vi.spyOn(apiClient, 'login').mockResolvedValueOnce({
      access_token: 'dummy.jwt.token',
      token_type: 'bearer',
      user_id: 'KA-1001',
      role: 'IO',
      expires_in: 86400,
    })

    renderLoginWithRouter()

    const idInput = screen.getByTestId('officer-id-input')
    const passInput = screen.getByTestId('password-input')
    const submitBtn = screen.getByTestId('login-submit-button')

    await user.type(idInput, 'KA-1001')
    await user.type(passInput, 'secure-password')
    await user.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByTestId('worklist-content')).toBeInTheDocument()
    })
  })

  it('redirects to relevant user profile when entering KA-xxxx badge in input box', async () => {
    const user = userEvent.setup()

    const loginSpy = vi.spyOn(apiClient, 'login').mockImplementation(async (req) => {
      const u = req.username.toUpperCase()
      const role = req.role || 'IO'
      return {
        access_token: 'dummy.jwt.token',
        token_type: 'bearer',
        user_id: u,
        role: role,
        expires_in: 86400,
      }
    })

    renderLoginWithRouter()

    const idInput = screen.getByTestId('officer-id-input')
    const submitBtn = screen.getByTestId('login-submit-button')

    // Enter KA-1002 (SHO Sunita Sharma) directly without clicking helper cards
    await user.type(idInput, 'KA-1002')
    await user.click(submitBtn)

    expect(loginSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        username: 'KA-1002',
        role: 'SHO',
      })
    )

    await waitFor(() => {
      expect(screen.getByTestId('worklist-content')).toBeInTheDocument()
    })
  })

  it('handles login failure and displays error alert banner', async () => {
    const user = userEvent.setup()

    vi.spyOn(apiClient, 'login').mockRejectedValueOnce({
      status: 401,
      statusText: 'Unauthorized',
      message: 'Invalid badge ID or security token',
    })

    renderLoginWithRouter()

    const idInput = screen.getByTestId('officer-id-input')
    const submitBtn = screen.getByTestId('login-submit-button')

    await user.type(idInput, 'INVALID-OFFICER')
    await user.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByTestId('login-error-alert')).toBeInTheDocument()
      expect(screen.getByText(/Invalid badge ID or security token/i)).toBeInTheDocument()
    })
  })

  it('authenticates via demo officer helper card', async () => {
    const user = userEvent.setup()

    vi.spyOn(apiClient, 'login').mockResolvedValueOnce({
      access_token: 'dummy.jwt.token',
      token_type: 'bearer',
      user_id: 'KA-1002',
      role: 'SHO',
      expires_in: 86400,
    })

    renderLoginWithRouter()

    const shoCard = screen.getByTestId('demo-officer-sho')
    await user.click(shoCard)

    await waitFor(() => {
      expect(screen.getByTestId('worklist-content')).toBeInTheDocument()
    })
  })

  it('authenticates with the compact SP officer choice', async () => {
    const user = userEvent.setup()

    vi.spyOn(apiClient, 'login').mockResolvedValueOnce({
      access_token: 'dummy.jwt.token',
      token_type: 'bearer',
      user_id: 'KA-1003',
      role: 'SP',
      expires_in: 86400,
    })

    renderLoginWithRouter()

    await user.click(screen.getByTestId('demo-officer-sp'))

    await waitFor(() => {
      expect(screen.getByTestId('worklist-content')).toBeInTheDocument()
    })
  })

  it('displays authenticated officer details in the Header without role-switching dropdown', () => {
    const mockOfficer: OfficerUser = {
      userId: 'officer_io',
      officerId: 'OFFICER-DEMO-IO-01',
      badgeNumber: 'KA-1001',
      name: 'Inspector Rajesh Kumar',
      rank: 'Inspector',
      role: 'IO',
      stationId: 'STATION-CYBER-CRIME-BLR',
      district: 'Bengaluru Central',
      email: 'officer_io@nexus.internal',
    }

    renderHeaderWithAuth(mockOfficer)

    // Name, badge, rank and role are rendered
    expect(screen.getByTestId('officer-name')).toHaveTextContent('Inspector Rajesh Kumar')
    expect(screen.getByTestId('officer-meta')).toHaveTextContent('Inspector · KA-1001')
    expect(screen.getByTestId('officer-role')).toHaveTextContent('IO')

    // Verify NO <select> dropdown for role switching exists
    expect(screen.queryByLabelText(/Switch Active Officer Profile & Role/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: /role/i })).not.toBeInTheDocument()

    // Verify Logout button exists
    expect(screen.getByTestId('logout-button')).toBeInTheDocument()
  })

  it('performs logout and clears authenticated session', async () => {
    const user = userEvent.setup()
    
    // Seed initial session in localStorage
    localStorage.setItem('nexus_role', 'IO')
    localStorage.setItem('nexus_token', 'initial-token')

    renderLoginWithRouter('/worklist')

    expect(screen.getByTestId('worklist-content')).toBeInTheDocument()

    const logoutBtn = screen.getByTestId('test-logout-btn')
    await user.click(logoutBtn)

    expect(localStorage.getItem('nexus_role')).toBeNull()
    expect(localStorage.getItem('nexus_token')).toBeNull()
  })

  it('authenticates and navigates to /intelligence by default when no previous location is specified', async () => {
    const user = userEvent.setup()
    vi.spyOn(apiClient, 'login').mockResolvedValueOnce({
      access_token: 'dummy.jwt.token',
      token_type: 'bearer',
      user_id: 'KA-1001',
      role: 'IO',
      expires_in: 86400,
    })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/login']}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/intelligence" element={<div data-testid="intelligence-landing">Intelligence Center</div>} />
              <Route path="/worklist" element={<div data-testid="worklist-landing">Worklist</div>} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    )

    const idInput = screen.getByTestId('officer-id-input')
    const submitBtn = screen.getByTestId('login-submit-button')

    await user.type(idInput, 'KA-1001')
    await user.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByTestId('intelligence-landing')).toBeInTheDocument()
      expect(screen.queryByTestId('worklist-landing')).not.toBeInTheDocument()
    })
  })
})
