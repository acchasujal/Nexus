import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { RoleGuard } from '@/components/RoleGuard'
import type { UserRole } from '@shared/contracts/api'

// Eager-loaded (not lazy) — Login and AppShell are part of the initial shell
import Login from '@/pages/Login'

// Lazy-loaded pages — each gets its own JS chunk for route-level code splitting
const Worklist = lazy(() => import('@/pages/Worklist'))
const Escalations = lazy(() => import('@/pages/Escalations'))
const Rollup = lazy(() => import('@/pages/Rollup'))
const Patterns = lazy(() => import('@/pages/Patterns'))
const Copilot = lazy(() => import('@/pages/Copilot'))
const CaseDetail = lazy(() => import('@/pages/CaseDetail'))
const Settings = lazy(() => import('@/pages/Settings'))

const allRoles: UserRole[] = ['IO', 'SHO', 'SP']
const worklistRoles: UserRole[] = ['IO', 'SHO']
const escalationRoles: UserRole[] = ['SHO', 'SP']

/** Suspense fallback that matches the layout the page will render */
function PageFallback() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 rounded-radius-sm bg-neutral-200 animate-shimmer" />
      <LoadingSkeleton layout="table" />
    </div>
  )
}

export const router = createBrowserRouter([
  // Public Route
  {
    path: '/login',
    element: <Login />,
  },

  // Protected Routes (Wrapped in AppShell)
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/worklist" replace />,
      },
      {
        path: 'worklist',
        element: (
          <RoleGuard allowedRoles={worklistRoles}>
            <Suspense fallback={<PageFallback />}>
              <Worklist />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'escalations',
        element: (
          <RoleGuard allowedRoles={escalationRoles}>
            <Suspense fallback={<PageFallback />}>
              <Escalations />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'rollup',
        element: (
          <RoleGuard allowedRoles={['SP']}>
            <Suspense fallback={<PageFallback />}>
              <Rollup />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'patterns',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<PageFallback />}>
              <Patterns />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'copilot',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<PageFallback />}>
              <Copilot />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'case/:id',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="detail" />}>
              <CaseDetail />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'settings',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<PageFallback />}>
              <Settings />
            </Suspense>
          </RoleGuard>
        ),
      },
    ],
  },

  // Fallback Redirect
  {
    path: '*',
    element: <Navigate to="/login" replace />,
  },
])
