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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<UserRole | null>(() => {
    const saved = localStorage.getItem('nexus_role') || localStorage.getItem('caseclock_role')
    if (saved && !localStorage.getItem('nexus_token')) {
      const token = createSessionToken(saved as UserRole)
      localStorage.setItem('nexus_token', token)
    }
    return (saved as UserRole) || null
  })

  const login = (newRole: UserRole) => {
    setRole(newRole)
    const token = createSessionToken(newRole)
    localStorage.setItem('nexus_role', newRole)
    localStorage.setItem('nexus_token', token)
  }

  const logout = () => {
    setRole(null)
    localStorage.removeItem('nexus_role')
    localStorage.removeItem('nexus_token')
    localStorage.removeItem('caseclock_role')
    localStorage.removeItem('caseclock_token')
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
