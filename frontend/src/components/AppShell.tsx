import { useState, useEffect, useRef } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { WifiOff } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useOnlineStatus } from '@/hooks/useOnlineStatus'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function AppShell() {
  const { isAuthenticated } = useAuth()
  const [isSidebarOpen, setSidebarOpen] = useState(false)
  const isOnline = useOnlineStatus()
  const location = useLocation()

  // Live region ref for route change announcements
  const announceRef = useRef<HTMLParagraphElement>(null)

  // Announce route changes to screen readers
  useEffect(() => {
    if (announceRef.current) {
      // Map pathnames to human-readable page names
      const pageNames: Record<string, string> = {
        '/worklist': 'Risk-Ranked Worklist',
        '/escalations': 'Escalation Queue',
        '/rollup': 'District Rollup',
        '/patterns': 'Patterns and Analytics',
        '/copilot': 'Copilot',
        '/settings': 'Settings',
      }

      const pathKey = Object.keys(pageNames).find(k => location.pathname.startsWith(k))
      const pageName = pathKey ? pageNames[pathKey] : 'Case Detail'

      // Set the text and immediately clear it to force re-announcement
      announceRef.current.textContent = `Navigated to ${pageName}`
      const timer = setTimeout(() => {
        if (announceRef.current) {
          announceRef.current.textContent = ''
        }
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [location.pathname])

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-screen bg-neutral-50 flex">
      {/* Skip to main content link — first focusable element on every page */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:inline-flex focus:items-center focus:rounded-radius-sm focus:bg-status-info focus:px-4 focus:py-2 focus:text-small focus:font-semibold focus:text-neutral-50 focus:shadow-lg"
      >
        Skip to main content
      </a>

      {/* Screen reader live region for route announcements */}
      <p
        ref={announceRef}
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      />

      {/* Sidebar Navigation */}
      <Sidebar isOpen={isSidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Layout Area */}
      <div className="flex-1 flex flex-col lg:pl-sidebar min-w-0">
        <Header onMenuToggle={() => setSidebarOpen(true)} />

        {/* Offline Banner */}
        {!isOnline && (
          <div
            role="alert"
            className="flex items-center gap-2 bg-status-warning/10 border-b border-status-warning/20 px-4 py-2 text-small text-status-warning"
          >
            <WifiOff className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>
              <strong>Offline.</strong> You are not connected to the network. Data may be stale.
            </span>
          </div>
        )}

        {/* Dynamic Content Outlet */}
        <main id="main-content" className="flex-1 overflow-auto p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
