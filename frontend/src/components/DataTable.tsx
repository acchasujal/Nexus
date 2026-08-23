import React, { useRef, useState } from 'react'
import { useUI } from '@/contexts/UIContext'
import { resolveObjectPath } from '@/lib/utils'
import { LoadingSkeleton } from './LoadingSkeleton'
import { EmptyState } from './EmptyState'

export interface ColumnDef<T> {
  header: string
  accessorKey: string
  cell?: (row: T, index: number) => React.ReactNode
}

interface DataTableProps<T> {
  columns: ColumnDef<T>[]
  data: T[]
  isLoading: boolean
  onRowClick?: (row: T) => void
  emptyMessage?: string
  /** Accessible label for the table. Defaults to "Data table". */
  ariaLabel?: string
}

export function DataTable<T extends { id: string }>({
  columns,
  data,
  isLoading,
  onRowClick,
  emptyMessage = 'No records found.',
  ariaLabel = 'Data table',
}: DataTableProps<T>) {
  const { tableDensity } = useUI()
  const rowRefs = useRef<Array<HTMLTableRowElement | null>>([])
  const [selectedRowId, setSelectedRowId] = useState<string | null>(null)

  if (isLoading) {
    return <LoadingSkeleton layout="table" />
  }

  if (data.length === 0) {
    return <EmptyState message={emptyMessage} />
  }

  const rowHeightClass = tableDensity === 'dense' ? 'h-10 py-1' : 'h-14 py-3'

  return (
    <div className="w-full overflow-x-auto rounded-radius-md border border-neutral-200 bg-neutral-50">
      <table
        className="w-full border-collapse text-left text-body text-neutral-800"
        role="grid"
        aria-label={ariaLabel}
        aria-rowcount={data.length}
      >
        <thead className="border-b border-neutral-200 bg-neutral-100 text-small font-semibold text-neutral-600">
          <tr role="row">
            {columns.map((column, index) => (
              <th
                key={index}
                scope="col"
                role="columnheader"
                className="px-4 py-3 font-semibold uppercase tracking-wider"
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200" role="rowgroup">
          {data.map((row, rowIndex) => (
            <tr
              key={row.id}
              ref={(element) => { rowRefs.current[rowIndex] = element }}
              role="row"
              aria-rowindex={rowIndex + 1}
              onClick={() => onRowClick?.(row)}
              tabIndex={onRowClick ? 0 : undefined}
              aria-selected={onRowClick && selectedRowId === row.id ? 'true' : undefined}
              onFocus={() => setSelectedRowId(row.id)}
              onBlur={() => setSelectedRowId(null)}
              onKeyDown={(event) => {
                if (!onRowClick || event.target !== event.currentTarget) return
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  onRowClick(row)
                } else if (event.key === 'ArrowDown' && rowIndex < data.length - 1) {
                  event.preventDefault()
                  rowRefs.current[rowIndex + 1]?.focus()
                } else if (event.key === 'ArrowUp' && rowIndex > 0) {
                  event.preventDefault()
                  rowRefs.current[rowIndex - 1]?.focus()
                }
              }}
              className={`transition-colors duration-fast hover:bg-neutral-100/50 focus-visible:bg-neutral-100 focus-visible:outline-none ${
                onRowClick ? 'cursor-pointer' : ''
              } ${selectedRowId === row.id ? 'bg-neutral-100/30' : ''}`}
            >
              {columns.map((column, colIdx) => {
                const cellContent = column.cell
                  ? column.cell(row, rowIndex)
                  : String(resolveObjectPath(row, column.accessorKey) ?? '')

                // Detect overdue clocks dynamically to apply warning border on first column cell
                const isOverdue = 
                  ('clock' in row && (row.clock as Record<string, unknown>)?.status === 'overdue') || 
                  ('clock_status' in row && (row as Record<string, unknown>).clock_status === 'overdue') ||
                  ('status' in row && (row as Record<string, unknown>).status === 'overdue')

                const borderClass = isOverdue && colIdx === 0 ? 'border-l-[4px] border-l-status-danger' : ''

                return (
                  <td
                    key={colIdx}
                    role="gridcell"
                    className={`px-4 text-small align-middle transition-all duration-fast ${rowHeightClass} ${borderClass}`}
                  >
                    {cellContent}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
