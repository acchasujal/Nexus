import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { UIProvider } from '@/contexts/UIContext'
import Login from '@/pages/Login'
import DemoWorkspace from '@/pages/DemoWorkspace'
import { apiClient, ApiError } from '@/lib/apiClient'
import { DEMO_BASELINE } from '@/lib/demoBaseline'

vi.mock('@/lib/queryClient', async original => ({
  ...await original<typeof import('@/lib/queryClient')>(), coldStartRetryDelay: () => 10,
}))

function AuthProbe() {
  const { isAuthenticated } = useAuth()
  return <output data-testid="server-auth">{String(isAuthenticated)}</output>
}
function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { gcTime: 0 } } })
  render(<StrictMode><QueryClientProvider client={client}><AuthProvider><UIProvider>
    <AuthProbe /><MemoryRouter initialEntries={['/login']}><Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/demo" element={<DemoWorkspace />} />
      <Route path="/intelligence" element={<p>Full authenticated workspace</p>} />
    </Routes></MemoryRouter>
  </UIProvider></AuthProvider></QueryClientProvider></StrictMode>)
  return client
}
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); vi.stubEnv('VITE_DEMO_MODE', 'true') })
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.useRealTimers() })

describe('explicit synthetic demo entry', () => {
  it('does not offer local entry when the evaluation flag is disabled', async () => {
    vi.stubEnv('VITE_DEMO_MODE', 'false')
    const login = vi.spyOn(apiClient, 'login').mockImplementation(() => new Promise(() => {}))
    setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    expect(screen.queryByRole('heading', { name: 'Intelligence workspace' })).not.toBeInTheDocument()
    expect(screen.getByTestId('server-auth')).toHaveTextContent('false')
    expect(login).toHaveBeenCalledTimes(1)
  })

  it('never enables live reads using a locally selected role that differs from the server response', async () => {
    vi.spyOn(apiClient, 'login').mockResolvedValue({ access_token: 'server-issued', token_type: 'bearer', role: 'SHO', user_id: 'KA-1002', expires_in: 86400 })
    const reads = vi.spyOn(apiClient, 'getInvestigations')
    setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    await waitFor(() => expect(screen.getByRole('status', { name: 'Demo connection' })).toHaveTextContent('Offline demo'))
    expect(reads).not.toHaveBeenCalled()
    expect(screen.queryByRole('link', { name: /server-authenticated/ })).not.toBeInTheDocument()
  })

  it('remains usable without browser storage and never sends protected reads without a stored server session', async () => {
    vi.spyOn(sessionStorage, 'setItem').mockImplementation(() => { throw new Error('Storage blocked') })
    vi.spyOn(localStorage, 'setItem').mockImplementation(() => { throw new Error('Storage blocked') })
    vi.spyOn(apiClient, 'login').mockResolvedValue({ access_token: 'server-issued', token_type: 'bearer', role: 'IO', user_id: 'KA-1001', expires_in: 86400 })
    const reads = vi.spyOn(apiClient, 'getInvestigations')
    setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    expect(screen.getByRole('grid')).toHaveAttribute('aria-rowcount', '10')
    await waitFor(() => expect(screen.getByRole('status', { name: 'Demo connection' })).toHaveTextContent('Offline demo'))
    expect(screen.getByTestId('server-auth')).toHaveTextContent('false')
    expect(reads).not.toHaveBeenCalled()
  })

  it('keeps a held request alive beyond the old 20-second deadline and reconciles its late response', async () => {
    vi.useFakeTimers()
    let complete!: (value: Awaited<ReturnType<typeof apiClient.login>>) => void
    const login = vi.spyOn(apiClient, 'login').mockImplementation(() => new Promise(done => { complete = done }))
    vi.spyOn(apiClient, 'getIntelligenceBootstrap').mockResolvedValue(DEMO_BASELINE.bootstrap)
    vi.spyOn(apiClient, 'getInvestigations').mockResolvedValue(DEMO_BASELINE.entryWorklist)
    setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    await act(async () => { await vi.advanceTimersByTimeAsync(21_000) })
    expect(login).toHaveBeenCalledTimes(1)
    expect(login.mock.calls[0][1]?.aborted).toBe(false)
    expect(screen.getByTestId('server-auth')).toHaveTextContent('false')
    await act(async () => {
      complete({ access_token: 'late-server-issued', token_type: 'bearer', role: 'IO', user_id: 'KA-1001', expires_in: 86400 })
    })
    await act(async () => { await vi.advanceTimersByTimeAsync(10) })
    expect(screen.getByRole('status', { name: 'Demo connection' })).toHaveTextContent('Live data connected')
    expect(login).toHaveBeenCalledTimes(1)
  })

  it('exhausts its background deadline without trapping the read-only interface', async () => {
    vi.useFakeTimers()
    const login = vi.spyOn(apiClient, 'login').mockImplementation((_, signal) => new Promise((resolve, reject) => {
      signal?.addEventListener('abort', () => reject(signal.reason), { once: true })
    }))
    setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    await act(async () => { await vi.advanceTimersByTimeAsync(120_000) })
    expect(screen.getByRole('status', { name: 'Demo connection' })).toHaveTextContent('Offline demo')
    expect(screen.getByRole('grid')).toHaveAttribute('aria-rowcount', '10')
    expect(screen.getByTestId('server-auth')).toHaveTextContent('false')
    expect(login).toHaveBeenCalledTimes(1)
    fireEvent.change(screen.getByLabelText('Search investigations'), { target: { value: DEMO_BASELINE.entryWorklist[0].fir_number } })
    expect(screen.getByRole('grid')).toHaveAttribute('aria-rowcount', '1')
  })

  it.each(['io', 'sho', 'sp', 'admin'])('renders %s and ten rows before server login completes', async role => {
    const login = vi.spyOn(apiClient, 'login').mockImplementation(() => new Promise(() => {}))
    const reads = vi.spyOn(apiClient, 'getInvestigations')
    setup()
    const start = performance.now()
    fireEvent.click(screen.getByTestId(`demo-officer-${role}`))
    expect(screen.getByRole('heading', { name: 'Intelligence workspace' })).toBeInTheDocument()
    const elapsed = performance.now() - start
    console.info(`Demo entry component timing: ${role} ${elapsed.toFixed(1)}ms (jsdom, not browser paint)`)
    expect(elapsed).toBeLessThan(1000)
    expect(screen.getByRole('grid')).toHaveAttribute('aria-rowcount', '10')
    expect(screen.getByTestId('server-auth')).toHaveTextContent('false')
    expect(localStorage.getItem('nexus_token')).toBeNull()
    expect(screen.getByRole('status', { name: 'Demo connection' })).toHaveTextContent('Demo snapshot · Connecting')
    expect(screen.queryByRole('link', { name: /server-authenticated/ })).not.toBeInTheDocument()
    await waitFor(() => expect(login).toHaveBeenCalledTimes(1))
    expect(login.mock.calls[0][0]).toEqual(expect.objectContaining({ role: role.toUpperCase() }))
    expect(reads).not.toHaveBeenCalled()
  })

  it('reconciles late login and data automatically without duplicate navigation or requests', async () => {
    let complete!: (value: Awaited<ReturnType<typeof apiClient.login>>) => void
    const login = vi.spyOn(apiClient, 'login').mockImplementation(() => new Promise(done => { complete = done }))
    const bootstrap = vi.spyOn(apiClient, 'getIntelligenceBootstrap').mockResolvedValue({ ...DEMO_BASELINE.bootstrap, kpis: { ...DEMO_BASELINE.bootstrap.kpis, active_pulses_count: 19 } })
    const worklist = vi.spyOn(apiClient, 'getInvestigations').mockResolvedValue([{ id: 'live-case', title: 'Live synthetic case', fir_number: 'FIR-LIVE' }])
    setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    await waitFor(() => expect(login).toHaveBeenCalledTimes(1))
    await act(async () => complete({ access_token: 'server-issued', token_type: 'bearer', role: 'IO', user_id: 'KA-1001', expires_in: 86400 }))
    await waitFor(() => expect(screen.getByRole('status', { name: 'Demo connection' })).toHaveTextContent('Live data connected'))
    expect(screen.getByText('Live synthetic case')).toBeInTheDocument()
    expect(screen.getByText('19')).toBeInTheDocument()
    expect(screen.getByTestId('server-auth')).toHaveTextContent('true')
    expect(bootstrap).toHaveBeenCalledTimes(1)
    expect(worklist).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('Full authenticated workspace')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: /server-authenticated/ }))
    expect(screen.getByText('Full authenticated workspace')).toBeInTheDocument()
  })

  it.each([new ApiError(503, '', 'Starting'), new DOMException('signal timed out', 'TimeoutError'), new TypeError('DNS unavailable')])('retains the snapshot through %s and retries background login', async error => {
    const login = vi.spyOn(apiClient, 'login').mockRejectedValueOnce(error).mockResolvedValue({ access_token: 'server-issued', token_type: 'bearer', role: 'IO', user_id: 'KA-1001', expires_in: 86400 })
    vi.spyOn(apiClient, 'getIntelligenceBootstrap').mockResolvedValue(DEMO_BASELINE.bootstrap)
    vi.spyOn(apiClient, 'getInvestigations').mockResolvedValue([{ id: 'live-case', title: 'Recovered synthetic case' }])
    setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    expect(screen.getByRole('grid')).toHaveAttribute('aria-rowcount', '10')
    await waitFor(() => expect(screen.getByRole('status', { name: 'Demo connection' })).toHaveTextContent('Live data connected'))
    expect(login).toHaveBeenCalledTimes(2)
    expect(screen.getByText('Recovered synthetic case')).toBeInTheDocument()
  })

  it('preserves ten rows after exhausted reads and reconnects them on explicit retry', async () => {
    vi.spyOn(apiClient, 'login').mockResolvedValue({ access_token: 'server-issued', token_type: 'bearer', role: 'IO', user_id: 'KA-1001', expires_in: 86400 })
    vi.spyOn(apiClient, 'getIntelligenceBootstrap').mockRejectedValue(new ApiError(503, '', 'Starting'))
    const worklist = vi.spyOn(apiClient, 'getInvestigations').mockRejectedValue(new TypeError('network failed'))
    setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    await waitFor(() => expect(screen.getByRole('status', { name: 'Demo connection' })).toHaveTextContent('Offline demo'))
    expect(screen.getByRole('grid')).toHaveAttribute('aria-rowcount', '10')
    expect(worklist).toHaveBeenCalledTimes(4)
    worklist.mockResolvedValue([{ id: 'reconnected', title: 'Reconnected synthetic case' }])
    fireEvent.click(screen.getByRole('button', { name: 'Reconnect services' }))
    await screen.findByText('Reconnected synthetic case')
  })

  it('does not accept a late login after exiting and clears the local demo selection', async () => {
    let complete!: (value: Awaited<ReturnType<typeof apiClient.login>>) => void
    const login = vi.spyOn(apiClient, 'login').mockImplementation(() => new Promise(done => { complete = done }))
    setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    await waitFor(() => expect(login).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('button', { name: 'Exit demo' }))
    await act(async () => complete({ access_token: 'late-server-token', token_type: 'bearer', role: 'IO', user_id: 'KA-1001', expires_in: 86400 }))
    expect(screen.getByTestId('demo-officer-io')).toBeInTheDocument()
    expect(screen.getByTestId('server-auth')).toHaveTextContent('false')
    expect(localStorage.getItem('nexus_token')).toBeNull()
    expect(sessionStorage.getItem('nexus_demo_role')).toBeNull()
  })

  it('keeps credential sign-in server authenticated even in the demo build', async () => {
    const login = vi.spyOn(apiClient, 'login').mockRejectedValue(new ApiError(401, '', 'Invalid credentials'))
    setup()
    fireEvent.click(screen.getByText('Sign in with officer credentials'))
    fireEvent.change(screen.getByTestId('officer-id-input'), { target: { value: 'KA-1001' } })
    fireEvent.click(screen.getByTestId('login-submit-button'))
    await screen.findByRole('alert')
    expect(login).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('heading', { name: 'Intelligence workspace' })).not.toBeInTheDocument()
    expect(screen.getByTestId('server-auth')).toHaveTextContent('false')
  })
})
