import React, { createContext, useContext, useState } from 'react'
import type { UserRole } from '@shared/contracts/api'

interface AuthContextType {
  role: UserRole | null
  login: (role: UserRole) => void
  logout: () => void
  isAuthenticated: boolean
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

function createSessionToken(role: UserRole): string {
  const payload = {
    sub: `officer_${role.toLowerCase()}`,
    email: `officer_${role.toLowerCase()}@nexus.gov.in`,
    role: role,
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
    const saved = getStoredRole()
    if (saved && !getStoredToken()) {
      const token = createSessionToken(saved)
      safeSetStorage('nexus_token', token)
    }
    return saved
  })

  const login = (newRole: UserRole) => {
    setRole(newRole)
    const token = createSessionToken(newRole)
    safeSetStorage('nexus_role', newRole)
    safeSetStorage('nexus_token', token)
  }

  const logout = () => {
    setRole(null)
    safeRemoveStorage('nexus_role')
    safeRemoveStorage('nexus_token')
  }

  return (
    <AuthContext.Provider value={{ role, login, logout, isAuthenticated: !!role }}>
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
