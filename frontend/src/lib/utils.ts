import type { ClockStatus } from '@shared/contracts/api'

/** Maps a clock status from the backend to a display-level risk label.
 *
 * This is NOT business logic — it is a display mapping only.
 * The backend owns all actual risk computation. Clock status is provided
 * by the backend; this only translates it to the three-tier label used
 * by RiskBadge and filter dropdowns.
 *
 * Used by: Worklist, Escalations, Patterns (column cells + filters).
 */
export function clockStatusToRisk(status: ClockStatus): 'HIGH' | 'MEDIUM' | 'LOW' {
  if (status === 'red' || status === 'overdue') return 'HIGH'
  if (status === 'amber') return 'MEDIUM'
  return 'LOW'
}

/** Resolves a nested object path like 'clock.days_remaining' from an object.
 * Used by DataTable to resolve accessor keys.
 */
export function resolveObjectPath(obj: unknown, path: string): unknown {
  return path.split('.').reduce((acc: unknown, part) => {
    if (acc === null || acc === undefined) return undefined
    return (acc as Record<string, unknown>)[part]
  }, obj)
}
