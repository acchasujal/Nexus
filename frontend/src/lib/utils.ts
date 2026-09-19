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

/**
 * Masks a telephone / MSISDN for privacy preservation (e.g. +91 98201 22334 -> +91 98*** **334).
 */
export function maskPhone(phone?: string | null): string {
  if (!phone) return '—'
  const trimmed = phone.trim()
  if (trimmed.length <= 5) return '***'
  const prefix = trimmed.slice(0, Math.min(6, trimmed.length - 4))
  const suffix = trimmed.slice(-3)
  return `${prefix}***${suffix}`
}

/**
 * Masks a vehicle registration number (e.g. KA-01-AB-1234 -> KA-01-**-**34).
 */
export function maskVehicle(vehicle?: string | null): string {
  if (!vehicle) return '—'
  const parts = vehicle.split(/[- ]/)
  if (parts.length >= 4) {
    return `${parts[0]}-${parts[1]}-**-**${parts[3].slice(-2)}`
  }
  if (vehicle.length > 6) {
    return `${vehicle.slice(0, 4)}***${vehicle.slice(-2)}`
  }
  return '***'
}

/**
 * Masks a national identifier / Aadhaar / PAN (e.g. 1234 5678 9012 -> ****-****-9012).
 */
export function maskNationalId(id?: string | null): string {
  if (!id) return '—'
  const clean = id.replaceAll(/\s|-/g, '')
  if (clean.length < 6) return '****'
  return `****-****-${clean.slice(-4)}`
}

/**
 * Partially masks street address while preserving district / locality context.
 */
export function maskAddress(address?: string | null): string {
  if (!address) return '—'
  const parts = address.split(',')
  if (parts.length > 1) {
    return `***, ${parts.slice(1).join(',').trim()}`
  }
  return `*** ${address.slice(-10)}`
}
