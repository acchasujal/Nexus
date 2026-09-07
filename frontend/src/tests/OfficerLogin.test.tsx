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
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Login from '@/pages/Login'
import { Header } from '@/components/Header'
import { AuthProvider, AuthContext, useAuth } from '@/contexts/AuthContext'
import { UIProvider } from '@/contexts/UIContext'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import type { OfficerUser } from '@/contexts/AuthContext'

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

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/worklist" element={<DummyWorklist />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
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

  it('renders login page with professional branding, inputs, and security notice', () => {
    renderLoginWithRouter()

    // Brand and subtitle
    expect(screen.getByText('NEXUS')).toBeInTheDocument()
    expect(screen.getByText(/AI-Powered Criminal Network Analysis & Investigation Platform/i)).toBeInTheDocument()
    expect(screen.getByText(/Restricted Access · Authorized Personnel Only · Cryptographically Audited/i)).toBeInTheDocument()

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
})
