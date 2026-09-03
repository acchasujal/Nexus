/**
 * frontend/src/tests/nexus.test.tsx
 *
 * Comprehensive integration tests for NEXUS prototype UI:
 * - DerivationBadge (Fact / Derived / Hypothesis)
 * - EvidenceDrawer (provenance locators, derivation chain, fail-closed)
 * - EntityFusion (match score, reasons, conflicts, Confirm / Reject / Defer)
 * - NetworkExplorer (Before/After snapshot replay, pathfinder)
 * - LeadInbox (evidence-backed connection path, grounded copilot answer)
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { nexusHandlers, nexusState } from '@/lib/mocks/nexusHandlers'
import { DerivationBadge } from '@/components/nexus/DerivationBadge'
import { EvidenceDrawer } from '@/components/nexus/EvidenceDrawer'
import { buildRegionSubgraph } from '@/components/nexus/GlobalNetworkCanvas'
import EntityFusion from '@/pages/EntityFusion'
import NetworkExplorer from '@/pages/NetworkExplorer'
import LeadInbox from '@/pages/LeadInbox'
import { BEFORE_NODES, BEFORE_EDGES } from '@/lib/mocks/nexusFixture'
import type { NexusNetworkResponse } from '@shared/contracts/api'

const server = setupServer(...nexusHandlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => {
  server.resetHandlers()
  nexusState.current.candidates.forEach((c) => {
    c.status = 'PENDING'
  })
  nexusState.current.lead.status = 'NEW'
})
afterAll(() => server.close())

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('NEXUS Frontend Prototype Suite', () => {
  describe('DerivationBadge', () => {
    it('renders Fact badge correctly', () => {
      render(<DerivationBadge klass="FACT" />)
      expect(screen.getByText('Fact')).toBeInTheDocument()
    })

    it('renders Derived badge correctly', () => {
      render(<DerivationBadge klass="DERIVED" />)
      expect(screen.getByText('Derived')).toBeInTheDocument()
    })

    it('renders Hypothesis badge correctly', () => {
      render(<DerivationBadge klass="HYPOTHESIS" />)
      expect(screen.getByText('Hypothesis')).toBeInTheDocument()
    })
  })

  describe('EvidenceDrawer', () => {
    it('returns null when relationshipId is null', () => {
      const { container } = render(<EvidenceDrawer relationshipId={null} onClose={() => {}} />, {
        wrapper: createWrapper(),
      })
      expect(container.firstChild).toBeNull()
    })

    it('renders source records and locators when relationshipId is provided', async () => {
      render(<EvidenceDrawer relationshipId="E-USEPH-A" onClose={() => {}} />, {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(screen.getByText('E-USEPH-A')).toBeInTheDocument()
        expect(screen.getByText(/Source records/i)).toBeInTheDocument()
      })
    })

    it('shows fail-closed error state for non-existent relationship', async () => {
      render(<EvidenceDrawer relationshipId="E-INVALID-ID" onClose={() => {}} />, {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(screen.getByText(/Evidence chain unavailable/i)).toBeInTheDocument()
      })
    })
  })

  describe('EntityFusion Workbench', () => {
    it('renders candidate comparison with match score, reasons, conflicts, and cross-case banner', async () => {
      render(<EntityFusion />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText(/Entity Fusion Workbench/i)).toBeInTheDocument()
        expect(screen.getByTestId('match-score')).toHaveTextContent('86/100')
        expect(screen.getAllByText('Rafiq Khan').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Rafiq Ahmed').length).toBeGreaterThan(0)
        expect(screen.getAllByText(/Cross-Case Match/i).length).toBeGreaterThan(0)
      })

      expect(screen.getByTestId('confirm-fusion')).toBeInTheDocument()
      expect(screen.getByTestId('reject-fusion')).toBeInTheDocument()
      expect(screen.getByTestId('defer-fusion')).toBeInTheDocument()
    })

    it('renders EvidenceConflictMatrix with verified agreements and flagged conflicts', async () => {
      render(<EntityFusion />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText(/Evidentiary Contradiction & Agreement Matrix/i)).toBeInTheDocument()
        expect(screen.getByText(/Corroborated Facts/i)).toBeInTheDocument()
        expect(screen.getByText(/Discrepancies \/ Conflicts/i)).toBeInTheDocument()
        expect(screen.getByText(/Unverified \/ Partial/i)).toBeInTheDocument()
      })
    })

    it('switches between candidate tabs correctly', async () => {
      render(<EntityFusion />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText(/#2 Vikram Sharma/i)).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText(/#2 Vikram Sharma/i))

      await waitFor(() => {
        expect(screen.getByTestId('match-score')).toHaveTextContent('92/100')
        expect(screen.getAllByText('Vikram Sharma').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Bikram Sarma').length).toBeGreaterThan(0)
      })
    })

    it('updates to post-decision state when Confirm Fusion is clicked', async () => {
      render(<EntityFusion />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByTestId('confirm-fusion')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByTestId('confirm-fusion'))

      await waitFor(() => {
        expect(screen.getByTestId('post-decision')).toBeInTheDocument()
        expect(screen.getByText(/confirmed — entities fused/i)).toBeInTheDocument()
      })
    })
  })

  describe('NetworkExplorer', () => {
    it('filters the graph to the selected region subgraph at the data layer', () => {
      const graph: NexusNetworkResponse = {
        snapshot_id: 'test-region',
        state: 'before',
        nodes: BEFORE_NODES,
        edges: BEFORE_EDGES,
        total_nodes: BEFORE_NODES.length,
        total_edges: BEFORE_EDGES.length,
      }

      const mysuruGraph = buildRegionSubgraph(graph, 'Mysuru')

      expect(mysuruGraph.nodes.map((node) => node.id)).toEqual(
        expect.arrayContaining(['CASE-141', 'P-RAFIQ-K', 'ACC-7731', 'PH-A'])
      )
      expect(mysuruGraph.nodes.map((node) => node.id)).not.toContain('CASE-207')
      expect(mysuruGraph.edges.map((edge) => edge.id)).not.toContain('E-TXN-55')
      expect(mysuruGraph.edges.map((edge) => edge.id)).not.toContain('E-TXN-71')
    })

    it('restores the full graph when selecting All Regions and returns an empty subgraph for unknown regions', () => {
      const graph: NexusNetworkResponse = {
        snapshot_id: 'test-region',
        state: 'before',
        nodes: BEFORE_NODES,
        edges: BEFORE_EDGES,
        total_nodes: BEFORE_NODES.length,
        total_edges: BEFORE_EDGES.length,
      }

      expect(buildRegionSubgraph(graph, 'ALL')).toMatchObject({
        total_nodes: BEFORE_NODES.length,
        total_edges: BEFORE_EDGES.length,
      })

      const emptyGraph = buildRegionSubgraph(graph, 'Unknown District')
      expect(emptyGraph.nodes).toHaveLength(0)
      expect(emptyGraph.edges).toHaveLength(0)
    })

    it('renders snapshot replay controls and Before resolution graph', async () => {
      render(<NetworkExplorer />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Global Network Explorer')).toBeInTheDocument()
        expect(screen.getByText('Before resolution')).toBeInTheDocument()
        expect(screen.getByText('After resolution')).toBeInTheDocument()
      })
    })

    it('toggles Investigative Pathfinder bar and allows selecting presets', async () => {
      render(<NetworkExplorer />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText(/Investigative Pathfinder/i)).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText(/Investigative Pathfinder/i))

      await waitFor(() => {
        expect(screen.getByText(/Interactive Graph Pathfinder/i)).toBeInTheDocument()
        expect(screen.getByText(/Source Entity \/ Case/i)).toBeInTheDocument()
        expect(screen.getByText(/Target Entity \/ Case/i)).toBeInTheDocument()
        expect(screen.getByText(/🌟 FIR-141 ↔ FIR-207/i)).toBeInTheDocument()
        expect(screen.getByText(/💳 Deepak ↔ Rafiq/i)).toBeInTheDocument()
      })

      // Click preset
      fireEvent.click(screen.getByText(/💳 Deepak ↔ Rafiq/i))

      await waitFor(() => {
        expect(screen.getByText(/Connected in/i)).toBeInTheDocument()
        expect(screen.getByText(/Investigative Chain Steps/i)).toBeInTheDocument()
      })
    })

    it('renders a region selector and shows the selected district in the explorer header', async () => {
      render(<NetworkExplorer />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByLabelText(/Region/i)).toBeInTheDocument()
      })

      fireEvent.change(screen.getByLabelText(/Region/i), {
        target: { value: 'Bengaluru' },
      })

      await waitFor(() => {
        expect(screen.getByText(/Showing region: Bengaluru/i)).toBeInTheDocument()
      })
    })
  })

  describe('LeadInbox', () => {
    it('renders without error and shows lead inbox header', async () => {
      render(<LeadInbox />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Lead Inbox')).toBeInTheDocument()
      })
    })
  })
})
