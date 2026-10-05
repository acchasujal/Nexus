import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { apiClient, ApiError } from '@/lib/apiClient'
import { DEMO_BASELINE } from '@/lib/demoBaseline'
import { retryColdStartRequest } from '@/lib/queryClient'
import Patterns from '@/pages/Patterns'

vi.mock('@/lib/queryClient', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/lib/queryClient')>(),
  coldStartRetryDelay: () => 10,
}))

const bootstrap = {
  kpis: { active_pulses_count: 0, critical_pulses_count: 0, affected_cases_count: 0,
    evidence_percent: 0, supported_claims: 0, total_claims: 0, added_nodes: 4, added_edges: 12, total_changes: 16 },
  primary_pulse: null,
} as unknown as Awaited<ReturnType<typeof apiClient.getIntelligenceBootstrap>>

afterEach(() => { cleanup(); vi.restoreAllMocks() })

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><Patterns /></MemoryRouter></QueryClientProvider>)
}

describe('bounded cold-start recovery', () => {
  it.each([new ApiError(503, 'Starting', 'Starting'), new TypeError('fetch failed'), new DOMException('deadline', 'TimeoutError')])('recovers without refresh from %s', async (error) => {
    const boot = vi.spyOn(apiClient, 'getIntelligenceBootstrap').mockRejectedValueOnce(error).mockRejectedValueOnce(error).mockResolvedValue(bootstrap)
    const pulses = vi.spyOn(apiClient, 'getPulses').mockRejectedValueOnce(error).mockRejectedValueOnce(error).mockResolvedValue([])
    const heavy = vi.spyOn(apiClient, 'getCommunities')
    mount()
    expect(screen.getAllByText(/Canonical demo baseline/).length).toBeGreaterThan(0)
    expect(screen.queryByText('No active network pulses detected in the current window.')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getAllByText('Confirmed API data')).toHaveLength(2))
    await waitFor(() => expect(screen.getByText('No active network pulses detected in the current window.')).toBeInTheDocument())
    expect(boot).toHaveBeenCalledTimes(3)
    expect(pulses).toHaveBeenCalledTimes(3)
    expect(heavy).not.toHaveBeenCalled()
    expect(screen.queryByText('Unavailable')).not.toBeInTheDocument()
  })

  it('stops at four attempts and never converts failure to empty', async () => {
    const error = new ApiError(503, 'Starting', 'Starting')
    const boot = vi.spyOn(apiClient, 'getIntelligenceBootstrap').mockRejectedValue(error)
    const pulses = vi.spyOn(apiClient, 'getPulses').mockRejectedValue(error)
    mount()
    await waitFor(() => expect(screen.getAllByText(/synchronization paused after bounded retries/)).toHaveLength(2))
    expect(screen.getByRole('button', { name: `Network Pulse (${DEMO_BASELINE.pulses.length})` })).toBeInTheDocument()
    expect(screen.queryByText('Unavailable')).not.toBeInTheDocument()
    expect(boot).toHaveBeenCalledTimes(4)
    expect(pulses).toHaveBeenCalledTimes(4)
    expect(screen.queryByText('No active network pulses detected in the current window.')).not.toBeInTheDocument()
  })

  it('covers a minute-plus cold wake even when proxies reject immediately', async () => {
    const { coldStartRetryDelay: delay } = await vi.importActual<typeof import('@/lib/queryClient')>('@/lib/queryClient')
    expect([0, 1, 2].map(delay)).toEqual([2000, 40000, 70000])
    expect([0, 1, 2].reduce((sum, attempt) => sum + delay(attempt), 0)).toBe(112000)
    expect(retryColdStartRequest(2, new ApiError(503, '', 'Starting'))).toBe(true)
    expect(retryColdStartRequest(3, new ApiError(503, '', 'Starting'))).toBe(false)
  })

  it('does not retry authentication refusals or aborts', () => {
    for (const status of [400, 401, 403, 404, 500]) expect(retryColdStartRequest(0, new ApiError(status, '', ''))).toBe(false)
    expect(retryColdStartRequest(0, new DOMException('cancelled', 'AbortError'))).toBe(false)
    expect(retryColdStartRequest(3, new TypeError('fetch failed'))).toBe(false)
  })
})
