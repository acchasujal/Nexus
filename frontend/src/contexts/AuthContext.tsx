import React, { createContext, useContext, useRef, useState, useCallback } from 'react'
import { clearDemoRole } from '@/lib/demoMode'
import { useQueryClient } from '@tanstack/react-query'
import type { UserRole, AuthLoginRequest } from '@shared/contracts/api'
import { apiClient } from '@/lib/apiClient'
import { retryColdStartRequest, coldStartRetryDelay } from '@/lib/queryClient'

export interface OfficerUser {
  userId: string
  name: string
  badgeNumber: string
  rank: string
  role: UserRole
  officerId: string
  stationId?: string
  district?: string
  email?: string
}

export interface AuthContextType {
  role: UserRole | null
  user: OfficerUser | null
  login: (credentials: AuthLoginRequest | UserRole, options?: { signal: AbortSignal; background: true }) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Canonical default details for fallback and demo roles
const MAX_LOGIN_RETRY_DELAY_MS = 6000

export const CANONICAL_OFFICERS: Record<string, OfficerUser> = {
  INVESTIGATOR: {
    userId: 'officer_io',
    officerId: 'OFFICER-DEMO-IO-01',
    badgeNumber: 'KA-1001',
    name: 'Inspector Rajesh Kumar',
    rank: 'Inspector',
    role: 'INVESTIGATOR',
    stationId: 'STATION-CYBER-CRIME-BLR',
    district: 'Bengaluru Central',
    email: 'officer_io@nexus.internal',
  },
  IO: {
    userId: 'officer_io',
    officerId: 'OFFICER-DEMO-IO-01',
    badgeNumber: 'KA-1001',
    name: 'Inspector Rajesh Kumar',
    rank: 'Inspector',
    role: 'IO',
    stationId: 'STATION-CYBER-CRIME-BLR',
    district: 'Bengaluru Central',
    email: 'officer_io@nexus.internal',
  },
  ANALYST: {
    userId: 'officer_sho',
    officerId: 'OFFICER-DEMO-SHO-01',
    badgeNumber: 'KA-1002',
    name: 'SHO Sunita Sharma',
    rank: 'Station House Officer',
    role: 'ANALYST',
    stationId: 'STATION-CYBER-CRIME-BLR',
    district: 'Bengaluru Central',
    email: 'officer_sho@nexus.internal',
  },
  SHO: {
    userId: 'officer_sho',
    officerId: 'OFFICER-DEMO-SHO-01',
    badgeNumber: 'KA-1002',
    name: 'SHO Sunita Sharma',
    rank: 'Station House Officer',
    role: 'SHO',
    stationId: 'STATION-CYBER-CRIME-BLR',
    district: 'Bengaluru Central',
    email: 'officer_sho@nexus.internal',
  },
  SUPERVISOR: {
    userId: 'officer_sp',
    officerId: 'OFFICER-DEMO-SP-01',
    badgeNumber: 'KA-1003',
    name: 'SP Vikram Hegde',
    rank: 'Superintendent of Police',
    role: 'SUPERVISOR',
    stationId: 'HQ-CID-CYBER-KARNATAKA',
    district: 'State Cyber Division',
    email: 'officer_sp@nexus.internal',
  },
  SP: {
    userId: 'officer_sp',
    officerId: 'OFFICER-DEMO-SP-01',
    badgeNumber: 'KA-1003',
    name: 'SP Vikram Hegde',
    rank: 'Superintendent of Police',
    role: 'SP',
    stationId: 'HQ-CID-CYBER-KARNATAKA',
    district: 'State Cyber Division',
    email: 'officer_sp@nexus.internal',
  },
  ADMIN: {
    userId: 'officer_admin',
    officerId: 'OFFICER-DEMO-ADMIN-01',
    badgeNumber: 'KA-1000',
    name: 'Dir. Priya Mehta',
    rank: 'Director of Cyber Intelligence',
    role: 'ADMIN',
    stationId: 'HQ-MHA-NCRB-DELHI',
    district: 'National Cybercrime Operations',
    email: 'officer_admin@nexus.internal',
  },
}

function parseTokenPayload(token: string): Record<string, any> | null {
  try {
    let jsonStr = ''
    if (token.includes('.')) {
      const parts = token.split('.')
      if (parts.length >= 2) {
        const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
        jsonStr = decodeURIComponent(
          atob(base64)
            .split('')
            .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
            .join(''),
        )
      }
    } else {
      jsonStr = atob(token)
    }
    if (jsonStr) {
      return JSON.parse(jsonStr)
    }
  } catch {
    // Ignore decode errors
  }
  return null
}

function resolveUserFromTokenOrRole(token: string | null, role: UserRole | null): OfficerUser | null {
  if (!role && !token) return null
  const payload = token ? parseTokenPayload(token) : null
  const resolvedRole = (role || payload?.role || 'INVESTIGATOR') as UserRole
  const fallback = CANONICAL_OFFICERS[resolvedRole] || CANONICAL_OFFICERS.INVESTIGATOR

  if (payload) {
    return {
      userId: payload.sub || payload.user_id || fallback.userId,
      officerId: payload.officer_id || fallback.officerId,
      badgeNumber: payload.badge_number || fallback.badgeNumber,
      name: payload.name || fallback.name,
      rank: payload.rank || fallback.rank,
      role: resolvedRole,
      stationId: payload.station_id || fallback.stationId,
      district: payload.district || fallback.district,
      email: payload.email || fallback.email,
    }
  }

  return { ...fallback, role: resolvedRole }
}

function getStoredRole(): UserRole | null {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      return (window.localStorage.getItem('nexus_role') as UserRole) || null
    }
  } catch {
    // Ignore storage errors in test or sandbox environments
  }
  return null
}

function getStoredToken(): string | null {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      const token = window.localStorage.getItem('nexus_token')
      const payload = token ? parseTokenPayload(token) : null
      if (typeof payload?.exp === 'number' && payload.exp <= Date.now() / 1000) return null
      return token
    }
  } catch {
    // Ignore storage errors
  }
  return null
}

function safeSetStorage(key: string, value: string): boolean {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      window.localStorage.setItem(key, value)
      return window.localStorage.getItem(key) === value
    }
  } catch {
    // Ignore storage errors
  }
  return false
}

function safeRemoveStorage(key: string): void {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      window.localStorage.removeItem(key)
    }
  } catch {
    // Ignore storage errors
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryCache = useQueryClient()
  const sessionGeneration = useRef(0)
  const [role, setRole] = useState<UserRole | null>(() => {
    return getStoredToken() ? getStoredRole() : null
  })

  const [user, setUser] = useState<OfficerUser | null>(() => {
    const savedRole = getStoredRole()
    const savedToken = getStoredToken()
    return savedToken ? resolveUserFromTokenOrRole(savedToken, savedRole) : null
  })

  const login = useCallback<AuthContextType['login']>(async (credentials, options) => {
    const generation = ++sessionGeneration.current
    const request = typeof credentials === 'string'
      ? { username: CANONICAL_OFFICERS[credentials].badgeNumber, password: 'nexus-demo-passcode', role: credentials }
      : credentials

    // Login retries stay responsive; long wake-up delays belong to background reads.
    // Only a server response may establish a new session.
    const authenticate = async () => {
      for (let attempt = 0; ; attempt++) {
        try {
          options?.signal.throwIfAborted()
          return options ? await apiClient.login(request, options.signal) : await apiClient.login(request)
        } catch (error) {
          if (options?.signal.aborted || !retryColdStartRequest(attempt, error)) throw error
          const delay = options?.background ? coldStartRetryDelay(attempt)
            : Math.min(coldStartRetryDelay(0) * (attempt + 1), MAX_LOGIN_RETRY_DELAY_MS)
          await new Promise<void>((resolve, reject) => {
            const signal = options?.signal
            const abort = () => { clearTimeout(timer); reject(signal?.reason) }
            const timer = setTimeout(() => { signal?.removeEventListener('abort', abort); resolve() }, delay)
            signal?.addEventListener('abort', abort, { once: true })
            if (signal?.aborted) abort()
          })
        }
      }
    }
    const authRes = await authenticate()
    // Logout, a new login, or leaving demo entry invalidates late responses.
    if (generation !== sessionGeneration.current || options?.signal.aborted) throw new DOMException('Session changed', 'AbortError')
    if (typeof authRes.access_token !== 'string' || !authRes.access_token || !CANONICAL_OFFICERS[authRes.role]) {
      throw new Error('The server returned an invalid session. Please retry sign-in.')
    }
    queryCache.clear()
    const token = authRes.access_token
    const resolvedRole = authRes.role
    if (!safeSetStorage('nexus_token', token) || !safeSetStorage('nexus_role', resolvedRole)) {
      safeRemoveStorage('nexus_token')
      safeRemoveStorage('nexus_role')
      throw new Error('Session storage is unavailable. Allow browser storage and retry sign-in.')
    }
    setRole(resolvedRole)
    setUser(resolveUserFromTokenOrRole(token, resolvedRole))
  }, [queryCache])

  const logout = () => {
    sessionGeneration.current++
    queryCache.clear()
    setRole(null)
    setUser(null)
    safeRemoveStorage('nexus_role')
    safeRemoveStorage('nexus_token')
    clearDemoRole()
  }

  return (
    <AuthContext.Provider value={{ role, user, login, logout, isAuthenticated: !!role }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
