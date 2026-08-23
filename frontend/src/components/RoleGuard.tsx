import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import type { UserRole } from '@shared/contracts/api'

interface RoleGuardProps {
  allowedRoles: UserRole[]
  children: ReactNode
}

export function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  const { role } = useAuth()
  const location = useLocation()

  if (!role) return <Navigate to="/login" replace state={{ from: location }} />
  if (!allowedRoles.includes(role)) return <Navigate to={role === 'SP' ? '/rollup' : '/worklist'} replace />
  return <>{children}</>
}
