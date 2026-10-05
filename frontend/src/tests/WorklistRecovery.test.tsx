import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { UIProvider } from '@/contexts/UIContext'
import { apiClient } from '@/lib/apiClient'
import Worklist from '@/pages/Worklist'

// Reproduce the real ingestion panel's success effect and callback dependency.
vi.mock('@/components/CsvIngestionPanel', async () => {
  const { useEffect, useState } = await import('react')
  return { CsvIngestionPanel: ({ onIngestSuccess }: { onIngestSuccess?: () => void }) => {
    const [complete, setComplete] = useState(false)
    useEffect(() => { if (complete) onIngestSuccess?.() }, [complete, onIngestSuccess])
    return <button onClick={() => setComplete(true)}>Complete simulated ingestion</button>
  } }
})
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('Worklist ingestion hydration', () => {
  it('refetches once after ingestion without a render-driven request storm', async () => {
    const fetch = vi.spyOn(apiClient, 'getInvestigations').mockResolvedValue([
      { id: 'case-one', fir_number: 'FIR-ONE', title: 'Known investigation', station_name: 'Demo station', offence_category: 'Demo' },
    ])
    const client = new QueryClient({ defaultOptions: { queries: { gcTime: 0 } } })
    render(<QueryClientProvider client={client}><UIProvider><MemoryRouter><Worklist /></MemoryRouter></UIProvider></QueryClientProvider>)
    await screen.findByText('Confirmed API data')
    expect(fetch).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByText('Complete simulated ingestion'))
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    await new Promise(resolve => setTimeout(resolve, 100))
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(screen.getByText('Known investigation')).toBeInTheDocument()
  })
})
