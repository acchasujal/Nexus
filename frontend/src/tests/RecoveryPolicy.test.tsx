import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useRecoveringQuery } from '@/hooks/useRecoveringQuery'
import { apiClient, ApiError } from '@/lib/apiClient'
import { DEMO_BASELINE } from '@/lib/demoBaseline'
import Worklist from '@/pages/Worklist'
import { IdentityDriftRadarSection } from '@/components/nexus/IdentityDriftRadarSection'
import { UIProvider } from '@/contexts/UIContext'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/lib/queryClient', async importOriginal => ({
  ...await importOriginal<typeof import('@/lib/queryClient')>(), coldStartRetryDelay: () => 10,
}))
afterEach(() => { cleanup(); vi.restoreAllMocks() })
function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { gcTime: 0 } } })
  const wrapper = ({ children }: { children: React.ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>
  return { client, wrapper }
}

describe('shared recovery and baseline honesty', () => {
  it('shows the artifact immediately but does not seed confirmed cache data', async () => {
    const { client, wrapper } = setup()
    let resolve!: (value: number[]) => void
    const fetch = vi.fn(() => new Promise<number[]>(done => { resolve = done }))
    const { result } = renderHook(() => useRecoveringQuery({ queryKey: ['baseline'], queryFn: fetch }, [3]), { wrapper })
    expect(result.current.data).toEqual([3])
    expect(result.current.isBaseline).toBe(true)
    expect(result.current.syncState).toBe('syncing')
    expect(client.getQueryData(['baseline'])).toBeUndefined()
    resolve([4])
    await waitFor(() => expect(result.current.syncState).toBe('confirmed'))
    expect(result.current.data).toEqual([4])
    expect(result.current.isBaseline).toBe(false)
  })

  it('allows only one catch-up request after a different healthy read', async () => {
    const { client, wrapper } = setup()
    const fn = vi.fn().mockRejectedValue(new ApiError(503, '', 'Starting'))
    const { result } = renderHook(() => useRecoveringQuery({ queryKey: ['exhausted'], queryFn: fn }, [3]), { wrapper })
    await waitFor(() => expect(result.current.syncState).toBe('baseline'))
    expect(fn).toHaveBeenCalledTimes(3)
    await client.fetchQuery({ queryKey: ['healthy-one'], queryFn: async () => [1], meta: { recoveringRead: true } })
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(4))
    await client.fetchQuery({ queryKey: ['healthy-two'], queryFn: async () => [2], meta: { recoveringRead: true } })
    expect(fn).toHaveBeenCalledTimes(4)
    expect(result.current.data).toEqual([3])
  })

  it.each([401, 403])('does not retry or show baseline for permission refusal %s', async status => {
    const { client, wrapper } = setup()
    const fn = vi.fn().mockRejectedValue(new ApiError(status, '', 'Refused'))
    const { result } = renderHook(() => useRecoveringQuery({ queryKey: ['refused'], queryFn: fn }, [3]), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.data).toBeUndefined()
    expect(result.current.isBaseline).toBe(false)
    await client.fetchQuery({ queryKey: ['healthy'], queryFn: async () => [1], meta: { recoveringRead: true } })
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('does not activate unopened secondary tabs during recovery', async () => {
    const { client, wrapper } = setup()
    const fn = vi.fn().mockRejectedValue(new ApiError(503, '', 'Starting'))
    const { rerender } = renderHook(({ enabled }) => useRecoveringQuery({ queryKey: ['tab'], queryFn: fn, enabled }), {
      wrapper, initialProps: { enabled: true },
    })
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(3))
    rerender({ enabled: false })
    await client.fetchQuery({ queryKey: ['healthy'], queryFn: async () => [1], meta: { recoveringRead: true } })
    expect(fn).toHaveBeenCalledTimes(3)
  })

  it('shows an unknown summary metric rather than zero after a failed summary request', async () => {
    const { wrapper } = setup()
    vi.spyOn(apiClient, 'getIdentityDrifts').mockResolvedValue([])
    const summary = vi.spyOn(apiClient, 'getIdentityDriftSummary').mockRejectedValue(new ApiError(503, '', 'Starting'))
    render(<MemoryRouter><IdentityDriftRadarSection /></MemoryRouter>, { wrapper })
    const card = await screen.findByText('Hardware IMEI Hops')
    await waitFor(() => expect(card.closest('.rounded-xl')).toHaveTextContent('Unavailable'))
    expect(card.closest('.rounded-xl')).not.toHaveTextContent(/\b0\b/)
    expect(summary).toHaveBeenCalledTimes(3)
  })

  it('hydrates Worklist without replacing the baseline with a failed empty array', async () => {
    const { wrapper } = setup()
    const fetch = vi.spyOn(apiClient, 'getInvestigations').mockRejectedValueOnce(new ApiError(503, '', 'Starting'))
      .mockResolvedValue([{ id: 'confirmed-case', fir_number: 'FIR-CONFIRMED', title: 'Confirmed investigation', station_name: 'Demo station', offence_category: 'Demo' }])
    render(<UIProvider><MemoryRouter><Worklist /></MemoryRouter></UIProvider>, { wrapper })
    expect(screen.getByText(/Canonical demo baseline/)).toBeInTheDocument()
    expect(screen.getByText(DEMO_BASELINE.worklist[0].fir_number)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Confirmed investigation')).toBeInTheDocument())
    expect(screen.getByText('Confirmed API data')).toBeInTheDocument()
    expect(screen.queryByText(DEMO_BASELINE.worklist[0].fir_number)).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
