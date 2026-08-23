/**
 * RoleGuard.test.tsx
 *
 * Integration tests for the RoleGuard component.
 * Verifies that:
 * 1. Unauthenticated users are redirected to /login
 * 2. Users with allowed roles can view the protected content
 * 3. Users with disallowed roles are redirected to their role-appropriate home
 *
 * Test fixture roles: IO, SHO, SP (from @shared/contracts/api)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { RoleGuard } from '@/components/RoleGuard'
import { AuthContext } from '@/contexts/AuthContext'
import type { UserRole } from '@shared/contracts/api'

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildAuthValue(role: UserRole | null) {
  return {
    role,
    isAuthenticated: role !== null,
    login: vi.fn(),
    logout: vi.fn(),
  }
}

function renderGuard(role: UserRole | null, allowedRoles: UserRole[], initialPath = '/protected') {
  return render(
    <AuthContext.Provider value={buildAuthValue(role)}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
          <Route path="/worklist" element={<div data-testid="worklist-page">Worklist</div>} />
          <Route path="/rollup" element={<div data-testid="rollup-page">Rollup</div>} />
          <Route
            path="/protected"
            element={
              <RoleGuard allowedRoles={allowedRoles}>
                <div data-testid="protected-content">Protected Content</div>
              </RoleGuard>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('RoleGuard', () => {
  describe('Unauthenticated user (role=null)', () => {
    it('redirects to /login', () => {
      renderGuard(null, ['IO', 'SHO', 'SP'])
      expect(screen.getByTestId('login-page')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })
  })

  describe('IO role', () => {
    it('can view pages that include IO in allowedRoles', () => {
      renderGuard('IO', ['IO', 'SHO', 'SP'])
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('is redirected to /worklist when accessing SP-only pages', () => {
      renderGuard('IO', ['SP'])
      expect(screen.getByTestId('worklist-page')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('is redirected to /worklist when accessing SHO + SP pages', () => {
      renderGuard('IO', ['SHO', 'SP'])
      expect(screen.getByTestId('worklist-page')).toBeInTheDocument()
    })
  })

  describe('SHO role', () => {
    it('can view escalations page (SHO + SP allowed)', () => {
      renderGuard('SHO', ['SHO', 'SP'])
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('is redirected to /worklist when accessing SP-only rollup', () => {
      renderGuard('SHO', ['SP'])
      expect(screen.getByTestId('worklist-page')).toBeInTheDocument()
    })
  })

  describe('SP role', () => {
    it('can view the rollup page (SP only)', () => {
      renderGuard('SP', ['SP'])
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('is redirected to /rollup when accessing IO-only pages', () => {
      renderGuard('SP', ['IO'])
      // SP redirects to /rollup (not /worklist)
      expect(screen.getByTestId('rollup-page')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })
  })
})
