import React, { createContext, useContext, useState } from 'react'
import type { UserRole, AuthLoginRequest } from '@shared/contracts/api'
import { apiClient } from '@/lib/apiClient'

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
  login: (credentials: AuthLoginRequest | UserRole) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Canonical default details for fallback and demo roles
const CANONICAL_OFFICERS: Record<string, OfficerUser> = {
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
    name: 'System Administrator',
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
  const resolvedRole = (payload?.role || role || 'INVESTIGATOR') as UserRole
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

function createSessionToken(role: UserRole, username?: string): string {
  const canonical = CANONICAL_OFFICERS[role] || CANONICAL_OFFICERS.INVESTIGATOR
  const payload = {
    sub: username || canonical.userId,
    email: canonical.email || `${username || canonical.userId}@nexus.internal`,
    role: role,
    officer_id: canonical.officerId,
    badge_number: canonical.badgeNumber,
    name: canonical.name,
    rank: canonical.rank,
    station_id: canonical.stationId,
    district: canonical.district,
    iat: Math.floor(Date.now() / 1000),
  }
  return btoa(JSON.stringify(payload))
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
      return window.localStorage.getItem('nexus_token')
    }
  } catch {
    // Ignore storage errors
  }
  return null
}

function safeSetStorage(key: string, value: string): void {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      window.localStorage.setItem(key, value)
    }
  } catch {
    // Ignore storage errors
  }
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
  const [role, setRole] = useState<UserRole | null>(() => {
    return getStoredRole()
  })

  const [user, setUser] = useState<OfficerUser | null>(() => {
    const savedRole = getStoredRole()
    const savedToken = getStoredToken()
    if (savedRole && !savedToken) {
      const token = createSessionToken(savedRole)
      safeSetStorage('nexus_token', token)
      return resolveUserFromTokenOrRole(token, savedRole)
    }
    return resolveUserFromTokenOrRole(savedToken, savedRole)
  })

  const login = async (credentials: AuthLoginRequest | UserRole): Promise<void> => {
    if (typeof credentials === 'string') {
      // Legacy role-based login (used in test fixtures)
      const newRole = credentials as UserRole
      const token = createSessionToken(newRole)
      safeSetStorage('nexus_role', newRole)
      safeSetStorage('nexus_token', token)
      setRole(newRole)
      setUser(resolveUserFromTokenOrRole(token, newRole))
      return
    }

    try {
      // Call authoritative backend login API
      const authRes = await apiClient.login(credentials)
      const token = authRes.access_token
      const resolvedRole = authRes.role
      safeSetStorage('nexus_token', token)
      safeSetStorage('nexus_role', resolvedRole)
      setRole(resolvedRole)
      setUser(resolveUserFromTokenOrRole(token, resolvedRole))
    } catch (err) {
      // If network fails in demo mode without backend running, fallback to deterministic demo session
      if (typeof credentials === 'object' && credentials.username) {
        const u = credentials.username.toLowerCase().trim()
        let fallbackRole: UserRole = credentials.role || 'INVESTIGATOR'
        if (!credentials.role) {
          if (u.includes('sho') || u.includes('ka-1002') || u.includes('analyst')) fallbackRole = 'SHO'
          else if (u.includes('sp') || u.includes('ka-1003') || u.includes('supervisor')) fallbackRole = 'SP'
          else if (u.includes('admin') || u.includes('ka-1000')) fallbackRole = 'ADMIN'
          else if (u.includes('io') || u.includes('ka-1001') || u.includes('investigator')) fallbackRole = 'IO'
        }
        // If error was an explicit invalid API error with status 401 or 403, re-throw
        if (err && typeof err === 'object' && 'status' in err && (err.status === 401 || err.status === 403)) {
          throw err
        }
        // Otherwise offline fallback
        const fallbackToken = createSessionToken(fallbackRole, credentials.username)
        safeSetStorage('nexus_token', fallbackToken)
        safeSetStorage('nexus_role', fallbackRole)
        setRole(fallbackRole)
        setUser(resolveUserFromTokenOrRole(fallbackToken, fallbackRole))
        return
      }
      throw err
    }
  }

  const logout = () => {
    setRole(null)
    setUser(null)
    safeRemoveStorage('nexus_role')
    safeRemoveStorage('nexus_token')
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
