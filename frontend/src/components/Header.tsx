import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUI } from '@/contexts/UIContext'
import { useAuth } from '@/contexts/AuthContext'
import { 
  Menu, 
  Bell, 
  Search, 
  Keyboard, 
  RotateCcw, 
  Loader2, 
  Check, 
  Briefcase, 
  User, 
  X as CloseX 
} from 'lucide-react'
import { KeyboardShortcutsDialog } from './KeyboardShortcutsDialog'
import { useNexusSearch, useResetDemo } from '@/hooks/useNexus'

interface HeaderProps {
  onMenuToggle: () => void
}

export function Header({ onMenuToggle }: HeaderProps) {
  const navigate = useNavigate()
  const { tableDensity, setTableDensity } = useUI()
  const { role } = useAuth()
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  // Search state
  const [query, setQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const searchContainerRef = useRef<HTMLDivElement>(null)
  const { data: searchResults, isLoading: isSearching } = useNexusSearch(query)

  // Reset demo mutation
  const resetMutation = useResetDemo()
  const [resetSuccess, setResetSuccess] = useState(false)

  const handleReset = async () => {
    try {
      await resetMutation.mutateAsync()
      setResetSuccess(true)
      setTimeout(() => setResetSuccess(false), 2000)
    } catch {
      // handled by mutation
    }
  }

  // Close search dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setSearchOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Global '?' shortcut opens the keyboard shortcuts dialog
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement instanceof HTMLInputElement ||
        document.activeElement instanceof HTMLTextAreaElement ||
        document.activeElement instanceof HTMLSelectElement
      ) {
        if (e.key === 'Escape') {
          setSearchOpen(false)
        }
        return
      }
      if (e.key === '?') {
        e.preventDefault()
        setShortcutsOpen(true)
      }
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        const searchInput = document.getElementById('global-search') as HTMLInputElement
        searchInput?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const hasCases = Boolean(searchResults?.cases && searchResults.cases.length > 0)
  const hasEntities = Boolean(searchResults?.entities && searchResults.entities.length > 0)
  const showResults = searchOpen && query.trim().length >= 2

  return (
    <>
      <header
        role="banner"
        className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-neutral-200 bg-white px-4 lg:px-8 text-neutral-900 shadow-sm"
      >
        {/* Mobile Hamburger menu */}
        <button
          onClick={onMenuToggle}
          className="min-h-11 min-w-11 rounded-lg p-2 text-neutral-600 hover:bg-neutral-100 lg:hidden focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label="Toggle Navigation Menu"
          aria-expanded={false}
          aria-controls="sidebar-nav"
        >
          <Menu className="h-6 w-6" aria-hidden="true" />
        </button>

        {/* Global Live Search */}
        <div ref={searchContainerRef} className="relative w-64 max-w-xs lg:w-96">
          <label htmlFor="global-search" className="sr-only">Search cases, FIRs, suspects</label>
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <Search className="h-4 w-4 text-neutral-400" aria-hidden="true" />
          </div>
          <input
            id="global-search"
            type="search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSearchOpen(true)
            }}
            onFocus={() => setSearchOpen(true)}
            placeholder="Search cases, FIRs, suspects... (press /)"
            className="w-full rounded-lg border border-neutral-300 bg-neutral-100 py-1.5 pl-10 pr-8 text-sm text-neutral-900 placeholder-neutral-500 focus:bg-white focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition-colors shadow-inner"
            aria-label="Search cases, FIRs, suspects"
            autoComplete="off"
          />
          {query && (
            <button
              onClick={() => {
                setQuery('')
                setSearchOpen(false)
              }}
              className="absolute inset-y-0 right-0 flex items-center pr-2.5 text-neutral-400 hover:text-neutral-600"
              aria-label="Clear search"
            >
              <CloseX className="h-3.5 w-3.5" />
            </button>
          )}

          {/* Search Dropdown */}
          {showResults && (
            <div className="absolute left-0 right-0 top-full mt-1.5 max-h-80 overflow-y-auto rounded-lg border border-neutral-200 bg-white shadow-2xl z-50 p-2 space-y-2">
              {isSearching && (
                <div className="flex items-center gap-2 p-3 text-xs text-neutral-600">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" /> Searching intelligence graph…
                </div>
              )}

              {!isSearching && !hasCases && !hasEntities && (
                <div className="p-3 text-center text-xs text-neutral-500">
                  No matching cases or suspects found for "{query}"
                </div>
              )}

              {hasCases && (
                <div>
                  <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                    Cases / FIRs
                  </div>
                  {searchResults?.cases.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        setSearchOpen(false)
                        navigate(`/cases/${c.id}`)
                      }}
                      className="w-full flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-xs text-neutral-800 hover:bg-blue-50 hover:text-blue-900 transition-colors"
                    >
                      <Briefcase className="h-3.5 w-3.5 text-rose-600 shrink-0" />
                      <div className="truncate">
                        <span className="font-semibold text-neutral-900">{c.fir_number}</span>
                        <span className="ml-2 text-neutral-500 truncate">{c.title}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {hasEntities && (
                <div>
                  <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                    Entities & Suspects
                  </div>
                  {searchResults?.entities.map((e) => (
                    <button
                      key={e.id}
                      onClick={() => {
                        setSearchOpen(false)
                        navigate('/network')
                      }}
                      className="w-full flex items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-neutral-800 hover:bg-blue-50 hover:text-blue-900 transition-colors"
                    >
                      <div className="flex items-center gap-2.5 truncate">
                        <User className="h-3.5 w-3.5 text-sky-600 shrink-0" />
                        <span className="font-medium text-neutral-900 truncate">{e.label}</span>
                      </div>
                      <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-mono text-neutral-600 border border-neutral-200">
                        {e.entity_type}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Utility Actions */}
        <div className="flex items-center space-x-2 lg:space-x-3">
          {/* Reset Demo Button */}
          <button
            onClick={handleReset}
            disabled={resetMutation.isPending}
            className="flex items-center gap-1.5 rounded-lg border border-neutral-300 bg-white px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 hover:text-neutral-900 shadow-sm transition-colors"
            title="Reset synthetic demo fixture to original state"
            aria-label="Reset Demo Fixture"
          >
            {resetMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" />
            ) : resetSuccess ? (
              <Check className="h-3.5 w-3.5 text-emerald-600" />
            ) : (
              <RotateCcw className="h-3.5 w-3.5 text-neutral-500" />
            )}
            <span className="hidden sm:inline">
              {resetMutation.isPending ? 'Resetting…' : resetSuccess ? 'Reset!' : 'Reset Demo'}
            </span>
          </button>

          {/* Table Density Selector */}
          <div
            className="flex items-center rounded-lg bg-neutral-100 p-0.5 text-xs font-semibold border border-neutral-200"
            role="group"
            aria-label="Table density"
          >
            <button
              onClick={() => setTableDensity('dense')}
              aria-pressed={tableDensity === 'dense'}
              className={`rounded-md px-2 py-1 transition-all ${
                tableDensity === 'dense'
                  ? 'bg-white shadow-sm text-neutral-900 font-semibold'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              Dense
            </button>
            <button
              onClick={() => setTableDensity('comfortable')}
              aria-pressed={tableDensity === 'comfortable'}
              className={`rounded-md px-2 py-1 transition-all ${
                tableDensity === 'comfortable'
                  ? 'bg-white shadow-sm text-neutral-900 font-semibold'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              Comfortable
            </button>
          </div>

          {/* Keyboard Shortcuts Button */}
          <button
            onClick={() => setShortcutsOpen(true)}
            className="min-h-9 min-w-9 inline-flex items-center justify-center rounded-lg text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors border border-transparent hover:border-neutral-200"
            aria-label="Open keyboard shortcuts (press ? anytime)"
            title="Keyboard shortcuts (?)"
          >
            <Keyboard className="h-4 w-4" aria-hidden="true" />
          </button>

          {/* Notifications */}
          <button
            className="relative min-h-9 min-w-9 inline-flex items-center justify-center rounded-lg p-2 text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
            aria-label="View notifications"
          >
            <Bell className="h-4 w-4" aria-hidden="true" />
            <span
              className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-blue-600"
              aria-hidden="true"
            />
          </button>

          {/* Active Role Indicator */}
          <div className="hidden items-center space-x-2 text-xs text-neutral-600 lg:flex" aria-label={`Active role: ${role ?? 'None'}`}>
            <span aria-hidden="true">Role:</span>
            <span className="rounded-md bg-blue-50 px-2 py-0.5 font-bold text-blue-700 border border-blue-200">
              {role ?? 'None'}
            </span>
          </div>
        </div>
      </header>

      <KeyboardShortcutsDialog
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
    </>
  )
}
