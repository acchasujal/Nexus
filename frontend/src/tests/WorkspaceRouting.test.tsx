import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate, useRoutes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/contexts/AuthContext'
import { UIProvider } from '@/contexts/UIContext'
import { workspaceRoutes } from '@/routes/router'
import { apiClient, apiFetch, ApiError } from '@/lib/apiClient'

function token(role = 'IO', exp = Date.now() / 1000 + 3600) {
  return btoa(JSON.stringify({ sub: 'KA-1001', role, exp }))
}
function stored(role = 'IO', exp?: number) {
  localStorage.setItem('nexus_token', token(role, exp))
  localStorage.setItem('nexus_role', role)
}
const clients: QueryClient[] = []

function setup(path = '/login', state?: unknown) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  const router = { state: { location: { pathname: path, search: '', hash: '' } }, navigate: (() => {}) as ReturnType<typeof useNavigate> }
  function Driver() {
    router.state.location = useLocation()
    router.navigate = useNavigate()
    return useRoutes(workspaceRoutes)
  }
  clients.push(client)
  render(<QueryClientProvider client={client}><AuthProvider><UIProvider>
    <MemoryRouter initialEntries={[{ pathname: path, state }]}><Driver /></MemoryRouter>
  </UIProvider></AuthProvider></QueryClientProvider>)
  return router
}

beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  // The retired flag must not change routing, even if a host still sets it.
  vi.stubEnv('VITE_DEMO_MODE', 'true')
  vi.spyOn(apiClient, 'getIntelligenceBootstrap').mockImplementation(() => new Promise(() => {}))
  vi.spyOn(apiClient, 'getPulses').mockImplementation(() => new Promise(() => {}))
})
afterEach(() => {
  cleanup()
  clients.splice(0).forEach(client => client.clear())
  vi.restoreAllMocks()
  vi.unstubAllEnvs()
  vi.useRealTimers()
})

describe('authenticated investigator routing', () => {
  it.each(['/', '/demo', '/network', '/unknown-page'])('guards unauthenticated %s without loops', async path => {
    const router = setup(path)
    await screen.findByRole('region', { name: 'Officer Authentication Form' })
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('navigation', { name: 'Main Navigation' })).not.toBeInTheDocument()
  })

  it.each(['IO', 'SHO', 'SP', 'ADMIN'])('authenticates %s before entering the actual workspace', async role => {
    let complete!: (value: Awaited<ReturnType<typeof apiClient.login>>) => void
    const login = vi.spyOn(apiClient, 'login').mockImplementation(() => new Promise(resolve => { complete = resolve }))
    const router = setup()
    const choice = screen.getByTestId('demo-officer-' + role.toLowerCase())
    fireEvent.click(choice)
    fireEvent.click(choice)
    expect(login).toHaveBeenCalledTimes(1)
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('navigation', { name: 'Main Navigation' })).not.toBeInTheDocument()
    await act(async () => complete({ access_token: token(role), role, token_type: 'bearer', user_id: 'KA-1001', expires_in: 3600 }))
    await screen.findByRole('navigation', { name: 'Main Navigation' })
    expect(router.state.location.pathname).toBe('/intelligence')
    expect(localStorage.getItem('nexus_role')).toBe(role)
    expect(screen.getByTestId('officer-role')).toHaveTextContent(role)
    expect(screen.queryByText('Open server-authenticated workspace')).not.toBeInTheDocument()
  })

  it.each(['/', '/demo', '/login', '/not-a-route'])('restores a stored session from %s', async path => {
    stored()
    const router = setup(path)
    await screen.findByRole('navigation', { name: 'Main Navigation' })
    expect(router.state.location.pathname).toBe('/intelligence')
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('preserves an intended workspace URL including search and hash', async () => {
    vi.spyOn(apiClient, 'login').mockResolvedValue({ access_token: token(), role: 'IO', token_type: 'bearer', user_id: 'KA-1001', expires_in: 3600 })
    const router = setup()
    await act(async () => { await router.navigate('/intelligence?view=signals#review') })
    expect(router.state.location.pathname).toBe('/login')
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    await screen.findByRole('navigation', { name: 'Main Navigation' })
    expect(router.state.location.pathname + router.state.location.search + router.state.location.hash).toBe('/intelligence?view=signals#review')
  })

  it.each(['https://evil.example', '//evil.example', '/\\evil.example', '/login', '/demo', '/'])('rejects unsafe or looping return path %s', async pathname => {
    stored()
    const router = setup('/login', { from: { pathname } })
    await screen.findByRole('navigation', { name: 'Main Navigation' })
    expect(router.state.location.pathname).toBe('/intelligence')
  })

  it('keeps the shell and navigation visible while panel APIs never resolve', async () => {
    stored()
    setup('/intelligence')
    expect(await screen.findByRole('navigation', { name: 'Main Navigation' })).toBeInTheDocument()
    expect(screen.getByTestId('officer-name')).toHaveTextContent('Inspector Rajesh Kumar')
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(apiClient.getIntelligenceBootstrap).toHaveBeenCalled()
  })

  it('keeps the shell available on temporary data failure', async () => {
    vi.spyOn(apiClient, 'getIntelligenceBootstrap').mockRejectedValue(new ApiError(503, '', 'Temporarily unavailable'))
    stored()
    const router = setup('/intelligence')
    expect(await screen.findByRole('navigation', { name: 'Main Navigation' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/intelligence')
  })

  it('clears the session on logout and protects history navigation', async () => {
    stored()
    const router = setup('/intelligence')
    fireEvent.click(await screen.findByTestId('logout-button'))
    await screen.findByRole('region', { name: 'Officer Authentication Form' })
    expect(localStorage.getItem('nexus_token')).toBeNull()
    expect(localStorage.getItem('nexus_role')).toBeNull()
    await act(async () => { await router.navigate('/intelligence') })
    expect(router.state.location.pathname).toBe('/login')
    await act(async () => { await router.navigate(-1) })
    expect(router.state.location.pathname).toBe('/login')
  })

  it.each(['missing', 'malformed', 'expired'])('rejects %s stored credentials', async kind => {
    stored('IO', Date.now() / 1000 - 1)
    if (kind === 'missing') localStorage.removeItem('nexus_token')
    if (kind === 'malformed') localStorage.setItem('nexus_token', 'invalid-token')
    const router = setup('/intelligence')
    await screen.findByRole('region', { name: 'Officer Authentication Form' })
    expect(router.state.location.pathname).toBe('/login')
  })

  it('expires an active session without requiring a refresh', async () => {
    vi.useFakeTimers()
    stored('IO', Date.now() / 1000 + 5)
    const router = setup('/intelligence')
    await act(async () => { await vi.advanceTimersByTimeAsync(5100) })
    expect(router.state.location.pathname).toBe('/login')
    expect(localStorage.getItem('nexus_token')).toBeNull()
  })

  it('invalidates server-rejected credentials but preserves the session on 403', async () => {
    stored()
    setup('/intelligence')
    await screen.findByRole('navigation', { name: 'Main Navigation' })
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ detail: 'Forbidden' }), { status: 403 }))
    await expect(apiFetch('/protected-action')).rejects.toMatchObject({ status: 403 })
    expect(localStorage.getItem('nexus_token')).not.toBeNull()
    fetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'Expired token' }), { status: 401 }))
    await act(async () => { await expect(apiFetch('/protected-action')).rejects.toMatchObject({ status: 401 }) })
    await waitFor(() => expect(localStorage.getItem('nexus_token')).toBeNull())
  })

  it('keeps failed credential login visible and unauthenticated', async () => {
    vi.spyOn(apiClient, 'login').mockRejectedValue(new ApiError(401, '', 'Invalid credentials'))
    const router = setup()
    fireEvent.click(screen.getByTestId('demo-officer-io'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials')
    expect(router.state.location.pathname).toBe('/login')
    expect(localStorage.getItem('nexus_token')).toBeNull()
  })

  it('handles the backend verifier explicit invalid-token 403', async () => {
    stored()
    setup('/intelligence')
    await screen.findByRole('navigation', { name: 'Main Navigation' })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ detail: 'Invalid or expired authentication token.' }), { status: 403 }))
    await act(async () => { await expect(apiFetch('/protected-action')).rejects.toMatchObject({ status: 403 }) })
    await screen.findByRole('region', { name: 'Officer Authentication Form' })
    expect(localStorage.getItem('nexus_token')).toBeNull()
  })

  it('ignores a late unauthorized response belonging to an older token', async () => {
    stored()
    setup('/intelligence')
    await screen.findByRole('navigation', { name: 'Main Navigation' })
    let finish!: (response: Response) => void
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(resolve => { finish = resolve }))
    const request = apiFetch('/protected-action')
    const replacement = token('IO', Date.now() / 1000 + 7200)
    localStorage.setItem('nexus_token', replacement)
    finish(new Response(JSON.stringify({ detail: 'Expired token' }), { status: 401 }))
    await expect(request).rejects.toMatchObject({ status: 401 })
    expect(localStorage.getItem('nexus_token')).toBe(replacement)
    expect(screen.getByRole('navigation', { name: 'Main Navigation' })).toBeInTheDocument()
  })
})
