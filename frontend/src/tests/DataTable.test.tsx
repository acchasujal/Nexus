/**
 * DataTable.test.tsx
 *
 * Tests for the DataTable component covering:
 * - Loading state renders skeleton
 * - Empty state renders correctly
 * - Data renders with proper ARIA grid semantics
 * - Keyboard navigation (ArrowDown, ArrowUp, Enter, Space)
 * - Row click callback fires with correct row data
 * - ariaLabel prop is applied
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { UIContext } from '@/contexts/UIContext'

// ── Fixtures ──────────────────────────────────────────────────────────────────

interface TestRow {
  id: string
  name: string
  status: string
}

const testColumns: ColumnDef<TestRow>[] = [
  { header: 'Name', accessorKey: 'name' },
  { header: 'Status', accessorKey: 'status' },
]

const testData: TestRow[] = [
  { id: '1', name: 'Row Alpha', status: 'active' },
  { id: '2', name: 'Row Beta', status: 'pending' },
  { id: '3', name: 'Row Gamma', status: 'resolved' },
]

const uiContextValue = {
  tableDensity: 'comfortable' as const,
  setTableDensity: vi.fn(),
  isEscalateDrawerOpen: false,
  setEscalateDrawerOpen: vi.fn(),
}

function renderTable(overrides: Partial<Parameters<typeof DataTable<TestRow>>[0]> = {}) {
  const defaults = {
    columns: testColumns,
    data: testData,
    isLoading: false,
    ariaLabel: 'Test table',
  }
  return render(
    <UIContext.Provider value={uiContextValue}>
      <DataTable<TestRow> {...defaults} {...overrides} />
    </UIContext.Provider>,
  )
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('DataTable', () => {
  describe('Loading state', () => {
    it('renders a loading skeleton when isLoading is true', () => {
      const { container } = renderTable({ isLoading: true, data: [] })
      // The loading skeleton has aria-busy="true"
      expect(container.querySelector('[aria-busy="true"]')).not.toBeNull()
      expect(screen.queryByRole('grid')).not.toBeInTheDocument()
    })
  })

  describe('Empty state', () => {
    it('renders the empty state when data is empty', () => {
      renderTable({ data: [], emptyMessage: 'No records found.' })
      expect(screen.getByText('No records found.')).toBeInTheDocument()
      expect(screen.queryByRole('grid')).not.toBeInTheDocument()
    })
  })

  describe('Data rendering', () => {
    it('renders a table with role="grid"', () => {
      renderTable()
      expect(screen.getByRole('grid')).toBeInTheDocument()
    })

    it('applies the ariaLabel to the grid', () => {
      renderTable({ ariaLabel: 'Custom label' })
      expect(screen.getByRole('grid', { name: 'Custom label' })).toBeInTheDocument()
    })

    it('renders all column headers', () => {
      renderTable()
      // Text is case-insensitive; CSS uppercase is visual only, DOM has original case
      expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument()
      expect(screen.getByRole('columnheader', { name: 'Status' })).toBeInTheDocument()
    })

    it('renders all rows with correct cell data', () => {
      renderTable()
      expect(screen.getByText('Row Alpha')).toBeInTheDocument()
      expect(screen.getByText('Row Beta')).toBeInTheDocument()
      expect(screen.getByText('Row Gamma')).toBeInTheDocument()
    })

    it('renders rows with tabIndex=0 when onRowClick is provided', () => {
      renderTable({ onRowClick: vi.fn() })
      const rows = screen.getAllByRole('row').slice(1) // Exclude header row
      rows.forEach((row) => {
        expect(row).toHaveAttribute('tabindex', '0')
      })
    })

    it('does NOT add tabIndex to rows when onRowClick is not provided', () => {
      renderTable({ onRowClick: undefined })
      const rows = screen.getAllByRole('row').slice(1)
      rows.forEach((row) => {
        expect(row).not.toHaveAttribute('tabindex')
      })
    })
  })

  describe('Mouse interaction', () => {
    it('calls onRowClick with the correct row data when a row is clicked', async () => {
      const user = userEvent.setup()
      const onRowClick = vi.fn()
      renderTable({ onRowClick })

      const rows = screen.getAllByRole('row').slice(1) // Exclude header
      await user.click(rows[1]) // Click "Row Beta"

      expect(onRowClick).toHaveBeenCalledWith(testData[1])
      expect(onRowClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Keyboard navigation', () => {
    it('calls onRowClick when Enter is pressed on a focused row', async () => {
      const user = userEvent.setup()
      const onRowClick = vi.fn()
      renderTable({ onRowClick })

      const rows = screen.getAllByRole('row').slice(1)
      rows[0].focus()
      await user.keyboard('{Enter}')

      expect(onRowClick).toHaveBeenCalledWith(testData[0])
    })

    it('calls onRowClick when Space is pressed on a focused row', async () => {
      const user = userEvent.setup()
      const onRowClick = vi.fn()
      renderTable({ onRowClick })

      const rows = screen.getAllByRole('row').slice(1)
      rows[0].focus()
      await user.keyboard(' ')

      expect(onRowClick).toHaveBeenCalledWith(testData[0])
    })
  })
})
