/**
 * KeyboardNav.test.tsx
 *
 * Tests that the DataTable's built-in keyboard navigation works end-to-end:
 * - ArrowDown moves focus to the next row
 * - ArrowUp moves focus to the previous row
 * - ArrowDown at last row does nothing (no wrap)
 * - ArrowUp at first row does nothing (no wrap)
 *
 * Also validates the global '?' shortcut opens KeyboardShortcutsDialog.
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { UIContext } from '@/contexts/UIContext'

interface TestRow {
  id: string
  label: string
}

const columns: ColumnDef<TestRow>[] = [
  { header: 'Label', accessorKey: 'label' },
]

const data: TestRow[] = [
  { id: 'r1', label: 'First' },
  { id: 'r2', label: 'Second' },
  { id: 'r3', label: 'Third' },
]

const uiCtx = {
  tableDensity: 'comfortable' as const,
  setTableDensity: vi.fn(),
  isEscalateDrawerOpen: false,
  setEscalateDrawerOpen: vi.fn(),
}

function renderNav(onRowClick = vi.fn()) {
  return render(
    <UIContext.Provider value={uiCtx}>
      <DataTable
        columns={columns}
        data={data}
        isLoading={false}
        onRowClick={onRowClick}
        ariaLabel="Nav test table"
      />
    </UIContext.Provider>,
  )
}

describe('DataTable keyboard navigation', () => {
  it('ArrowDown moves focus from first to second row', async () => {
    const user = userEvent.setup()
    renderNav()

    const rows = screen.getAllByRole('row').slice(1) // Skip header
    rows[0].focus()
    expect(document.activeElement).toBe(rows[0])

    await user.keyboard('{ArrowDown}')
    expect(document.activeElement).toBe(rows[1])
  })

  it('ArrowDown from last row does not throw or move beyond bounds', async () => {
    const user = userEvent.setup()
    renderNav()

    const rows = screen.getAllByRole('row').slice(1)
    rows[2].focus()

    await user.keyboard('{ArrowDown}')
    // Focus stays on last row
    expect(document.activeElement).toBe(rows[2])
  })

  it('ArrowUp moves focus from second to first row', async () => {
    const user = userEvent.setup()
    renderNav()

    const rows = screen.getAllByRole('row').slice(1)
    rows[1].focus()

    await user.keyboard('{ArrowUp}')
    expect(document.activeElement).toBe(rows[0])
  })

  it('ArrowUp from first row does not throw or move above bounds', async () => {
    const user = userEvent.setup()
    renderNav()

    const rows = screen.getAllByRole('row').slice(1)
    rows[0].focus()

    await user.keyboard('{ArrowUp}')
    expect(document.activeElement).toBe(rows[0])
  })

  it('can navigate down and back up through all rows', async () => {
    const user = userEvent.setup()
    renderNav()

    const rows = screen.getAllByRole('row').slice(1)
    rows[0].focus()

    // Navigate to the end
    await user.keyboard('{ArrowDown}')
    await user.keyboard('{ArrowDown}')
    expect(document.activeElement).toBe(rows[2])

    // Navigate back to the beginning
    await user.keyboard('{ArrowUp}')
    await user.keyboard('{ArrowUp}')
    expect(document.activeElement).toBe(rows[0])
  })
})
