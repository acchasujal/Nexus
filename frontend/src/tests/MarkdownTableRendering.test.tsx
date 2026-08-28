import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { MarkdownContent } from '@/components/nexus/MarkdownContent'
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

describe('Markdown Table and Rich Content Rendering', () => {
  it('renders Markdown tables as styled native HTML <table>, <thead>, and <tbody> elements', () => {
    const tableMarkdown = `
Here is the multi-hop financial transfer path:

| Step | Entity | Relationship | Evidence ID |
|---|---|---|---|
| 1 | Rafiq Khan (P-RAFIQ-K) | Owns bank account ACC-7731 | SRC-FIR-141 |
| 2 | ACC-7731 → ACC-9914 | Transaction TXN-55 transfers funds | SRC-TXN-55 |
| 3 | ACC-9914 | Owned by Deepak Rao (P-DEEPAK) | SRC-FIR-207 |

This completes the verified transaction chain.
`

    const { container } = render(<MarkdownContent content={tableMarkdown} />)

    // Assert table structure exists
    const table = container.querySelector('table')
    expect(table).toBeInTheDocument()

    const thead = container.querySelector('thead')
    expect(thead).toBeInTheDocument()

    const tbody = container.querySelector('tbody')
    expect(tbody).toBeInTheDocument()

    // Assert headers
    const ths = container.querySelectorAll('th')
    expect(ths).toHaveLength(4)
    expect(ths[0]).toHaveTextContent('Step')
    expect(ths[1]).toHaveTextContent('Entity')
    expect(ths[2]).toHaveTextContent('Relationship')
    expect(ths[3]).toHaveTextContent('Evidence ID')

    // Assert table rows and cell contents
    const rows = tbody?.querySelectorAll('tr')
    expect(rows).toHaveLength(3)

    expect(screen.getByText('Rafiq Khan (P-RAFIQ-K)')).toBeInTheDocument()
    expect(screen.getByText('Owns bank account ACC-7731')).toBeInTheDocument()
    expect(screen.getByText('SRC-FIR-141')).toBeInTheDocument()

    expect(screen.getByText('ACC-7731 → ACC-9914')).toBeInTheDocument()
    expect(screen.getByText('Transaction TXN-55 transfers funds')).toBeInTheDocument()
    expect(screen.getByText('SRC-TXN-55')).toBeInTheDocument()

    expect(screen.getByText('Owned by Deepak Rao (P-DEEPAK)')).toBeInTheDocument()
    expect(screen.getByText('SRC-FIR-207')).toBeInTheDocument()

    // Assert raw pipe markdown is not rendered as literal text
    expect(container.textContent).not.toContain('| Step | Entity |')
    expect(container.textContent).not.toContain('|---|---|---|---|')
  })

  it('renders complex tables with bold text, formatting, and lists in Copilot page', () => {
    const copilotAnswer = `
**Cross-Case Linkage Report**

| Hop | Entity (ID) | Edge Type | Evidence |
|:---|:---|:---|:---|
| 1 | **P-RAFIQ-K** (accused) | \`E-OWN-7731\` | SRC-FIR-141 |
| 2 | **ACC-9914** (account) | \`E-TXN-55\` | SRC-TXN-55 |

Key findings:
- Funds routed through intermediary accounts
- Direct ownership documented in chargesheet
`

    const savedMessages = [
      {
        id: 'user-1',
        role: 'user',
        text: 'What evidence connects Rafiq and Deepak?',
        timestamp: '2026-08-28T12:00:00.000Z',
      },
      {
        id: 'assistant-1',
        role: 'assistant',
        text: copilotAnswer,
        citations: [
          {
            source_type: 'EVIDENCE',
            source_id: 'SRC-FIR-141',
            fact: 'Seized bank records',
            confidence: 1.0,
          },
        ],
        evidenceIds: ['SRC-FIR-141', 'SRC-TXN-55'],
        timestamp: '2026-08-28T12:00:01.000Z',
      },
    ]

    sessionStorage.setItem('nexus_copilot_chat_history', JSON.stringify(savedMessages))

    const { container } = render(<Copilot />, { wrapper: createWrapper() })

    // Verify table rendered inside Copilot
    const table = container.querySelector('table')
    expect(table).toBeInTheDocument()

    expect(screen.getByText('P-RAFIQ-K')).toBeInTheDocument()
    expect(screen.getByText('ACC-9914')).toBeInTheDocument()
    expect(screen.getByText('E-OWN-7731')).toBeInTheDocument()
    expect(screen.getByText('E-TXN-55')).toBeInTheDocument()

    // Verify list items rendered
    expect(screen.getByText('Funds routed through intermediary accounts')).toBeInTheDocument()
    expect(screen.getByText('Direct ownership documented in chargesheet')).toBeInTheDocument()

    // Verify evidence citations drawer/chips remain intact
    expect(screen.getAllByText(/SRC-FIR-141/).length).toBeGreaterThanOrEqual(2)
  })
})
