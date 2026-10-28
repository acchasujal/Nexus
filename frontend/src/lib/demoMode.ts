import type { UserRole } from '@shared/contracts/api'

// Only the explicitly configured synthetic evaluation build exposes local entry.
export const isDemoMode = () => import.meta.env.VITE_DEMO_MODE === 'true'
const DEMO_ROLE_KEY = 'nexus_demo_role'
const DEMO_ROLES: UserRole[] = ['IO', 'SHO', 'SP', 'ADMIN']

export function getDemoRole(): UserRole | null {
  if (!isDemoMode()) return null
  try {
    const role = sessionStorage.getItem(DEMO_ROLE_KEY) as UserRole
    return DEMO_ROLES.includes(role) ? role : null
  } catch {
    return null
  }
}

export function saveDemoRole(role: UserRole): void {
  if (isDemoMode() && DEMO_ROLES.includes(role)) {
    try { sessionStorage.setItem(DEMO_ROLE_KEY, role) } catch { /* Route state still permits entry. */ }
  }
}

export function clearDemoRole(): void {
  try { sessionStorage.removeItem(DEMO_ROLE_KEY) } catch { /* Storage may be unavailable. */ }
}
