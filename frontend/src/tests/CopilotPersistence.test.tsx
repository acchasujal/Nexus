import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Copilot from '@/pages/Copilot'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    )
  }
}

describe('Copilot Chat History Persistence', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('restores chat messages from sessionStorage upon remounting (simulating in-app navigation)', async () => {
    const savedMessages = [
      {
        id: 'welcome-0',
        role: 'assistant',
        text: 'Hello Investigator.',
        timestamp: '2026-08-23T00:00:00.000Z',
      },
      {
        id: 'user-1',
        role: 'user',
        text: 'Tell me about case FIR-2026-608',
        timestamp: '2026-08-28T12:00:00.000Z',
      },
      {
        id: 'assistant-1',
        role: 'assistant',
        text: 'CASE BRIEF: FIR-2026-608\nJurisdiction: Koramangala PS, Belagavi',
        caseId: 'case-0031',
        timestamp: '2026-08-28T12:00:01.000Z',
      },
    ]

    sessionStorage.setItem('nexus_copilot_chat_history', JSON.stringify(savedMessages))

    const { unmount } = render(<Copilot />, { wrapper: createWrapper() })

    // Verify previously saved messages appear on the page
    expect(screen.getByText('Tell me about case FIR-2026-608')).toBeInTheDocument()
    expect(screen.getByText(/CASE BRIEF: FIR-2026-608/)).toBeInTheDocument()
    expect(screen.getByText(/Investigation Case Context: case-0031/)).toBeInTheDocument()

    // Unmount (user navigates away to Case Detail / Network Explorer)
    unmount()

    // Re-mount (user navigates back to /copilot)
    render(<Copilot />, { wrapper: createWrapper() })

    // Messages should still be present
    expect(screen.getByText('Tell me about case FIR-2026-608')).toBeInTheDocument()
    expect(screen.getByText(/CASE BRIEF: FIR-2026-608/)).toBeInTheDocument()
  })

  it('clears sessionStorage and restores welcome message when Reset Chat is clicked', async () => {
    const savedMessages = [
      {
        id: 'user-1',
        role: 'user',
        text: 'Previous query',
        timestamp: '2026-08-28T12:00:00.000Z',
      },
    ]
    sessionStorage.setItem('nexus_copilot_chat_history', JSON.stringify(savedMessages))

    render(<Copilot />, { wrapper: createWrapper() })

    expect(screen.getByText('Previous query')).toBeInTheDocument()

    const resetButton = screen.getByRole('button', { name: /Reset Chat/i })
    fireEvent.click(resetButton)

    await waitFor(() => {
      expect(screen.queryByText('Previous query')).not.toBeInTheDocument()
      expect(screen.getByText(/Hello Investigator/i)).toBeInTheDocument()
    })
  })
})
