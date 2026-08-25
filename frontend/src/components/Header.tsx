import { useState, useEffect, useRef, useMemo } from 'react'
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
  Phone,
  Landmark,
  Car,
  MapPin,
  Shield,
  FileText,
  X as CloseX 
} from 'lucide-react'
import { KeyboardShortcutsDialog } from './KeyboardShortcutsDialog'
import { useNexusSearch, useResetDemo } from '@/hooks/useNexus'

interface HeaderProps {
  onMenuToggle: () => void
}

function getEntityIcon(type: string) {
  switch (type) {
    case 'Case':
      return <Briefcase className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
    case 'Person':
      return <User className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
    case 'Phone':
      return <Phone className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
    case 'Account':
      return <Landmark className="h-4 w-4 text-violet-600 shrink-0 mt-0.5" />
    case 'Vehicle':
      return <Car className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
    case 'Location':
      return <MapPin className="h-4 w-4 text-rose-500 shrink-0 mt-0.5" />
    case 'Organization':
      return <Shield className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
    default:
      return <FileText className="h-4 w-4 text-neutral-500 shrink-0 mt-0.5" />
  }
}

export function Header({ onMenuToggle }: HeaderProps) {
  const navigate = useNavigate()
  const { tableDensity, setTableDensity } = useUI()
  const { role } = useAuth()
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  // Search state
  const [query, setQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1)
  const searchContainerRef = useRef<HTMLDivElement>(null)
  const { data: searchResults, isLoading: isSearching, isError } = useNexusSearch(query)

  // Flattened results for keyboard navigation
  const allResults = useMemo(() => {
    const items: Array<{
      id: string
      type: 'case' | 'entity'
      route: string
      label: string
      subtext?: string
      entity_type: string
    }> = []

    if (searchResults?.cases) {
      for (const c of searchResults.cases) {
        items.push({
          id: c.id,
          type: 'case',
          route: `/cases/${c.id}`,
          label: c.fir_number ? `${c.fir_number} — ${c.title}` : c.title,
          subtext: `FIR ${c.fir_number}`,
          entity_type: 'Case',
        })
      }
    }

    if (searchResults?.entities) {
      for (const e of searchResults.entities) {
        items.push({
          id: e.id,
          type: 'entity',
          route: `/network?node_id=${encodeURIComponent(e.id)}`,
          label: e.label,
          subtext: e.subtext,
          entity_type: e.entity_type,
        })
      }
    }

    return items
  }, [searchResults])

  // Reset highlight index when query or results change
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setHighlightedIndex(-1)
  }, [query, searchResults])
  /* eslint-enable react-hooks/set-state-in-effect */

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

  const handleKeyDownInInput = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showResults || allResults.length === 0) {
      if (e.key === 'Escape') {
        setSearchOpen(false)
      }
      return
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightedIndex((prev) => (prev + 1 >= allResults.length ? 0 : prev + 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightedIndex((prev) => (prev - 1 < 0 ? allResults.length - 1 : prev - 1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const targetIdx = highlightedIndex >= 0 ? highlightedIndex : 0
      const targetItem = allResults[targetIdx]
      if (targetItem) {
        setSearchOpen(false)
        navigate(targetItem.route)
      }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setSearchOpen(false)
    }
  }

  let itemCounter = 0

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
        <div ref={searchContainerRef} className="relative flex-1 min-w-[130px] max-w-xs sm:max-w-sm lg:max-w-md mx-2 sm:mx-4">
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
            onKeyDown={handleKeyDownInInput}
            placeholder="Search cases, FIRs, suspects... (/)"
            className="w-full rounded-lg border border-neutral-300 bg-neutral-100 py-1.5 pl-9 sm:pl-10 pr-7 text-xs sm:text-sm text-neutral-900 placeholder-neutral-500 focus:bg-white focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition-colors shadow-inner"
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

              {isError && (
                <div className="p-3 text-center text-xs text-rose-600">
                  Failed to perform search. Please try again.
                </div>
              )}

              {!isSearching && !isError && !hasCases && !hasEntities && (
                <div className="p-3 text-center text-xs text-neutral-500">
                  No matching cases or entities found for "{query}"
                </div>
              )}

              {hasCases && (
                <div>
                  <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                    Cases / FIRs
                  </div>
                  {searchResults?.cases.map((c) => {
                    const currentIndex = itemCounter++
                    const isHighlighted = highlightedIndex === currentIndex
                    return (
                      <button
                        key={c.id}
                        onClick={() => {
                          setSearchOpen(false)
                          navigate(`/cases/${c.id}`)
                        }}
                        onMouseEnter={() => setHighlightedIndex(currentIndex)}
                        className={`w-full flex items-center justify-between gap-3 rounded-md px-2.5 py-1.5 text-left text-xs transition-colors ${
                          isHighlighted ? 'bg-blue-50 text-blue-900 ring-1 ring-blue-300' : 'hover:bg-neutral-50 text-neutral-800'
                        }`}
                      >
                        <div className="flex items-start gap-2.5 min-w-0 flex-1">
                          <Briefcase className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                          <div className="min-w-0 flex-1">
                            <div className="font-semibold text-neutral-900 truncate">
                              {c.fir_number} <span className="font-normal text-neutral-600">{c.title}</span>
                            </div>
                            <div className="text-[11px] text-neutral-500 truncate">
                              Case / FIR {c.fir_number}
                            </div>
                          </div>
                        </div>
                        <span className="rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-mono text-rose-700 border border-rose-200 shrink-0">
                          Case
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}

              {hasEntities && (
                <div>
                  <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                    Entities & Intelligence
                  </div>
                  {searchResults?.entities.map((e) => {
                    const currentIndex = itemCounter++
                    const isHighlighted = highlightedIndex === currentIndex
                    return (
                      <button
                        key={e.id}
                        onClick={() => {
                          setSearchOpen(false)
                          navigate(`/network?node_id=${encodeURIComponent(e.id)}`)
                        }}
                        onMouseEnter={() => setHighlightedIndex(currentIndex)}
                        className={`w-full flex items-center justify-between gap-3 rounded-md px-2.5 py-1.5 text-left text-xs transition-colors ${
                          isHighlighted ? 'bg-blue-50 text-blue-900 ring-1 ring-blue-300' : 'hover:bg-neutral-50 text-neutral-800'
                        }`}
                      >
                        <div className="flex items-start gap-2.5 min-w-0 flex-1">
                          {getEntityIcon(e.entity_type)}
                          <div className="min-w-0 flex-1">
                            <div className="font-semibold text-neutral-900 truncate">
                              {e.label}
                            </div>
                            {e.subtext && (
                              <div className="text-[11px] text-neutral-500 truncate mt-0.5">
                                {e.subtext}
                              </div>
                            )}
                          </div>
                        </div>
                        <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-mono text-neutral-600 border border-neutral-200 shrink-0">
                          {e.entity_type}
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Utility Actions */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 lg:space-x-3 shrink-0">
          {/* Reset Demo Button */}
          <button
            onClick={handleReset}
            disabled={resetMutation.isPending}
            className="flex items-center gap-1.5 rounded-lg border border-neutral-300 bg-white px-2 sm:px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 hover:text-neutral-900 shadow-sm transition-colors"
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
            className="hidden md:flex items-center rounded-lg bg-neutral-100 p-0.5 text-xs font-semibold border border-neutral-200"
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
            className="hidden sm:inline-flex min-h-9 min-w-9 items-center justify-center rounded-lg text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors border border-transparent hover:border-neutral-200"
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
