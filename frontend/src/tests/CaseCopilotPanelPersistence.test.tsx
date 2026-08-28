import { describe, it, expect, beforeEach, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { CaseCopilotPanel } from '@/components/CaseCopilotPanel'
import { apiClient } from '@/lib/apiClient'

vi.mock('@/lib/apiClient', async () => {
  const actual = await vi.importActual<typeof import('@/lib/apiClient')>('@/lib/apiClient')
  return { ...actual, apiClient: { ...actual.apiClient, queryCopilot: vi.fn() } }
})

const queryCopilot = vi.mocked(apiClient.queryCopilot)

function response(query: string, evidenceId: string) {
  return {
    query,
    intent: 'EVIDENCE_LOOKUP',
    answer: `Answer for ${query}`,
    grounded_citations: [{ source_type: 'FIR', source_id: evidenceId, fact: 'Verified fact' }],
    evidence_ids: [evidenceId],
    reasoning_path: [],
    suggested_actions: [],
    case_id: 'case-a',
  }
}

describe('Case Copilot transcript persistence', () => {
  beforeEach(() => {
    sessionStorage.clear()
    queryCopilot.mockReset()
    queryCopilot.mockImplementation(async ({ query }) => response(query, `EV-${query}`))
  })

  it('appends exchanges and persists citations across remount', async () => {
    const first = render(<CaseCopilotPanel caseId="case-a" />)
    const input = screen.getByRole('textbox')

    fireEvent.change(input, { target: { value: 'Question one' } })
    fireEvent.submit(input.closest('form')!)
    await waitFor(() => expect(screen.getByText('Answer for Question one')).toBeInTheDocument())

    fireEvent.change(input, { target: { value: 'Question two' } })
    fireEvent.submit(input.closest('form')!)
    await waitFor(() => expect(screen.getByText('Answer for Question two')).toBeInTheDocument())

    expect(screen.getByText('Question one')).toBeInTheDocument()
    expect(screen.getByText('Question two')).toBeInTheDocument()
    expect(screen.getByText('[FIR EV-Question one]')).toBeInTheDocument()
    first.unmount()

    render(<CaseCopilotPanel caseId="case-a" />)
    expect(screen.getByText('Question one')).toBeInTheDocument()
    expect(screen.getByText('Answer for Question two')).toBeInTheDocument()
    expect(screen.getByText('[FIR EV-Question two]')).toBeInTheDocument()
  })

  it('isolates case transcripts and reset clears only the current case', () => {
    sessionStorage.setItem('nexus_case_copilot_case-a', JSON.stringify({ messages: [{ id: 'a', role: 'user', text: 'Case A question', timestamp: new Date().toISOString() }] }))
    sessionStorage.setItem('nexus_case_copilot_case-b', JSON.stringify({ messages: [{ id: 'b', role: 'user', text: 'Case B question', timestamp: new Date().toISOString() }] }))

    const { unmount } = render(<CaseCopilotPanel caseId="case-a" />)
    expect(screen.getByText('Case A question')).toBeInTheDocument()
    expect(screen.queryByText('Case B question')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Reset Chat/i }))
    expect(screen.queryByText('Case A question')).not.toBeInTheDocument()
    expect(sessionStorage.getItem('nexus_case_copilot_case-a')).toBeNull()
    unmount()

    render(<CaseCopilotPanel caseId="case-b" />)
    expect(screen.getByText('Case B question')).toBeInTheDocument()
  })
})
