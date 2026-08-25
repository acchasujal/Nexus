import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { RoleGuard } from '@/components/RoleGuard'
import type { UserRole } from '@shared/contracts/api'

// Eager-loaded Shell pages
import Login from '@/pages/Login'

// Lazy-loaded routes
const Worklist = lazy(() => import('@/pages/Worklist'))
const NetworkExplorer = lazy(() => import('@/pages/NetworkExplorer'))
const EntityFusion = lazy(() => import('@/pages/EntityFusion'))
const LeadInbox = lazy(() => import('@/pages/LeadInbox'))
const Entities = lazy(() => import('@/pages/Entities'))
const Patterns = lazy(() => import('@/pages/Patterns'))
const Timeline = lazy(() => import('@/pages/Timeline'))
const Evidence = lazy(() => import('@/pages/Evidence'))
const Copilot = lazy(() => import('@/pages/Copilot'))
const Audit = lazy(() => import('@/pages/Audit'))
const CaseDetail = lazy(() => import('@/pages/CaseDetail'))
const Settings = lazy(() => import('@/pages/Settings'))

const allRoles: UserRole[] = ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
const supervisorRoles: UserRole[] = ['SUPERVISOR', 'ADMIN', 'SHO', 'SP']

export const router = createBrowserRouter([
  // Public Route
  {
    path: '/login',
    element: <Login />,
  },

  // Protected Intelligence Workspace Routes
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
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <Worklist />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'network',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <NetworkExplorer />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'fusion',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <EntityFusion />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'leads',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <LeadInbox />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'entities',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <Entities />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'patterns',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <Patterns />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'timeline',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <Timeline />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'evidence',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <Evidence />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'copilot',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <Copilot />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'audit',
        element: (
          <RoleGuard allowedRoles={supervisorRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <Audit />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'cases/:caseId',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <CaseDetail />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'investigations/:caseId',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <CaseDetail />
            </Suspense>
          </RoleGuard>
        ),
      },
      {
        path: 'settings',
        element: (
          <RoleGuard allowedRoles={allRoles}>
            <Suspense fallback={<LoadingSkeleton layout="table" />}>
              <Settings />
            </Suspense>
          </RoleGuard>
        ),
      },
    ],
  },

  // Fallback Route
  {
    path: '*',
    element: <Navigate to="/worklist" replace />,
  },
], {
  future: {
    v7_startTransition: true,
    v7_relativeSplatPath: true,
  },
})

