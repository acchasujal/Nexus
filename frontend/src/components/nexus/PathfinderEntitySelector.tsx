import React, { useState, useEffect, useRef, useMemo } from 'react'
import {
  Search,
  ChevronDown,
  X,
  User,
  Briefcase,
  Phone,
  Landmark,
  Car,
  MapPin,
  Shield,
  FileText,
  Check,
} from 'lucide-react'
import { useNexusSearch } from '@/hooks/useNexus'

export interface EntityOption {
  id: string
  label: string
  type: string
  subtext?: string
}

interface PathfinderEntitySelectorProps {
  label: string
  dotColor: 'blue' | 'rose'
  selectedId: string
  onSelect: (id: string) => void
  activeGraphNodes?: Array<{ id: string; label?: string; entity_type?: string; properties?: Record<string, unknown> }>
  testId?: string
}

export function getEntityIcon(type: string, className = 'h-3.5 w-3.5') {
  switch (type.toLowerCase()) {
    case 'case':
      return <Briefcase className={`${className} text-rose-600 shrink-0`} />
    case 'person':
      return <User className={`${className} text-sky-600 shrink-0`} />
    case 'phone':
      return <Phone className={`${className} text-amber-600 shrink-0`} />
    case 'account':
      return <Landmark className={`${className} text-violet-600 shrink-0`} />
    case 'vehicle':
      return <Car className={`${className} text-emerald-600 shrink-0`} />
    case 'location':
      return <MapPin className={`${className} text-red-500 shrink-0`} />
    case 'evidence':
      return <Shield className={`${className} text-emerald-600 shrink-0`} />
    case 'intelligencereport':
    case 'intel report':
      return <FileText className={`${className} text-indigo-600 shrink-0`} />
    default:
      return <FileText className={`${className} text-neutral-500 shrink-0`} />
  }
}

export function getTypeBadgeClass(type: string) {
  switch (type.toLowerCase()) {
    case 'case':
      return 'bg-rose-50 text-rose-700 border-rose-200'
    case 'person':
      return 'bg-sky-50 text-sky-700 border-sky-200'
    case 'phone':
      return 'bg-amber-50 text-amber-700 border-amber-200'
    case 'account':
      return 'bg-violet-50 text-violet-700 border-violet-200'
    case 'vehicle':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    case 'location':
      return 'bg-red-50 text-red-700 border-red-200'
    case 'evidence':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    case 'intelligencereport':
    case 'intel report':
      return 'bg-indigo-50 text-indigo-700 border-indigo-200'
    default:
      return 'bg-neutral-50 text-neutral-700 border-neutral-200'
  }
}

export const GOLDEN_SUGGESTIONS: EntityOption[] = [
  { id: 'CASE-141', label: 'FIR 141/2026 — Human Trafficking', type: 'Case', subtext: 'Mysuru South WS PS • Planted Case' },
  { id: 'CASE-207', label: 'FIR 207/2026 — Cyber Fraud', type: 'Case', subtext: 'Bengaluru CEN PS • Planted Case' },
  { id: 'P-RAFIQ-K', label: 'Rafiq Khan', type: 'Person', subtext: 'Mysuru • Accused in FIR 141 • Candidate RC-1' },
  { id: 'P-RAFIQ-A', label: 'Rafiq Ahmed', type: 'Person', subtext: 'Mysuru • Accused in FIR 207 • Candidate RC-1' },
  { id: 'P-DEEPAK', label: 'Deepak Rao', type: 'Person', subtext: 'Bengaluru • Co-accused in FIR 207 • Mule Account Owner' },
  { id: 'P-MEENA', label: 'Meena Kumari', type: 'Person', subtext: 'Mysuru • Victim in FIR 141' },
  { id: 'ACC-7731', label: 'ACC-7731 (Axis Bank)', type: 'Account', subtext: 'Rafiq Khan • Received ₹4.8L & ₹2.15L Hawala Flow' },
  { id: 'ACC-9914', label: 'ACC-9914 (Axis Bank)', type: 'Account', subtext: 'Deepak Rao • Originator of Hawala Flow' },
  { id: 'person-0051', label: 'Ramesh Hegde', type: 'Person', subtext: 'The Broker • Articulation Bridge Between Syndicates' },
  { id: 'person-0011', label: 'Praveen Iyer', type: 'Person', subtext: 'Coastal Narcotics Syndicate Lead' },
  { id: 'person-0026', label: 'Karan Gupta', type: 'Person', subtext: 'Cyber Hawala Syndicate Lead' },
  { id: 'case-0001', label: 'FIR-2026-101 — Narcotics Trafficking', type: 'Case', subtext: 'Mangaluru CCB • Syndicate Case' },
  { id: 'case-0049', label: 'FIR-2026-984 — Extortion', type: 'Case', subtext: 'Hubballi-Dharwad • Sanjay Patel Accused' },
]

export function PathfinderEntitySelector({
  label,
  dotColor,
  selectedId,
  onSelect,
  activeGraphNodes = [],
  testId,
}: PathfinderEntitySelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Universal search query
  const { data: searchResults, isLoading: isSearching } = useNexusSearch(query)

  // Map of active nodes for fast lookup
  const activeNodesMap = useMemo(() => {
    const map = new Map<string, EntityOption>()
    for (const n of activeGraphNodes) {
      const props = (n.properties || {}) as Record<string, unknown>
      map.set(n.id, {
        id: n.id,
        label: n.label || String(props.fir_number || props.full_name || n.id),
        type: String(n.entity_type || 'Entity'),
        subtext: props.fir_number
          ? `FIR: ${String(props.fir_number)}`
          : props.district
          ? `${String(props.district)}`
          : undefined,
      })
    }
    return map
  }, [activeGraphNodes])

  // Resolve currently selected entity display details
  const selectedEntity = useMemo<EntityOption | null>(() => {
    if (!selectedId || !selectedId.trim()) return null
    if (activeNodesMap.has(selectedId)) {
      return activeNodesMap.get(selectedId)!
    }
    const golden = GOLDEN_SUGGESTIONS.find((g) => g.id === selectedId)
    if (golden) return golden

    return {
      id: selectedId,
      label: selectedId,
      type: selectedId.startsWith('CASE') || selectedId.startsWith('case') ? 'Case' : 'Entity',
    }
  }, [selectedId, activeNodesMap])

  // Build candidate options
  const displayedOptions = useMemo<EntityOption[]>(() => {
    const cleanQuery = query.trim().toLowerCase()
    const seen = new Set<string>()
    const results: EntityOption[] = []

    // If active search query, prioritize API search results
    if (cleanQuery.length >= 2 && searchResults) {
      if (searchResults.cases) {
        for (const c of searchResults.cases) {
          if (!seen.has(c.id)) {
            seen.add(c.id)
            results.push({
              id: c.id,
              label: c.fir_number ? `${c.fir_number} — ${c.title}` : c.title,
              type: 'Case',
              subtext: `FIR ${c.fir_number}`,
            })
          }
        }
      }
      if (searchResults.entities) {
        for (const e of searchResults.entities) {
          if (!seen.has(e.id)) {
            seen.add(e.id)
            results.push({
              id: e.id,
              label: e.label,
              type: e.entity_type,
              subtext: e.subtext,
            })
          }
        }
      }
      return results
    }

    // Default suggestions when search query is short/empty
    // 1. All active graph nodes (so canvas nodes are instantly clickable)
    for (const opt of activeNodesMap.values()) {
      if (!seen.has(opt.id)) {
        if (!cleanQuery || opt.label.toLowerCase().includes(cleanQuery) || opt.id.toLowerCase().includes(cleanQuery)) {
          seen.add(opt.id)
          results.push(opt)
        }
      }
    }

    // 2. Golden suggestions & key syndicate hubs
    for (const g of GOLDEN_SUGGESTIONS) {
      if (!seen.has(g.id)) {
        if (!cleanQuery || g.label.toLowerCase().includes(cleanQuery) || g.id.toLowerCase().includes(cleanQuery)) {
          seen.add(g.id)
          results.push(g)
        }
      }
    }

    return results
  }, [query, searchResults, activeNodesMap])

  // Auto-focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50)
      setHighlightedIndex(-1)
    } else {
      setQuery('')
    }
  }, [isOpen])

  // Close on outside click
  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [])

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault()
        setIsOpen(true)
      }
      return
    }

    if (e.key === 'Escape') {
      e.preventDefault()
      setIsOpen(false)
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightedIndex((prev) => (prev < displayedOptions.length - 1 ? prev + 1 : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : displayedOptions.length - 1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (highlightedIndex >= 0 && highlightedIndex < displayedOptions.length) {
        const item = displayedOptions[highlightedIndex]
        onSelect(item.id)
        setIsOpen(false)
      }
    }
  }

  return (
    <div className="relative w-full" ref={containerRef} onKeyDown={handleKeyDown}>
      <label className="block text-xs font-bold text-neutral-700 mb-1 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <span
            className={`h-2 w-2 rounded-full ${dotColor === 'blue' ? 'bg-blue-600' : 'bg-rose-600'}`}
          />
          {label}
        </span>
        <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">
          445+ Graph Entities
        </span>
      </label>

      {/* Main Trigger Button */}
      <button
        type="button"
        data-testid={testId}
        onClick={() => setIsOpen((v) => !v)}
        className={`w-full flex items-center justify-between gap-2 rounded-lg border bg-white px-3 py-2 text-left text-xs sm:text-sm font-medium transition-all shadow-xs outline-none ${
          isOpen
            ? 'border-blue-500 ring-2 ring-blue-200'
            : 'border-neutral-300 hover:border-neutral-400 text-neutral-900'
        }`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {selectedEntity ? (
            <>
              {getEntityIcon(selectedEntity.type)}
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-bold border uppercase tracking-wider shrink-0 ${getTypeBadgeClass(
                  selectedEntity.type
                )}`}
              >
                {selectedEntity.type}
              </span>
              <span className="truncate font-semibold text-neutral-900">
                {selectedEntity.label}
              </span>
              <span className="font-mono text-[11px] text-neutral-500 shrink-0">
                ({selectedEntity.id})
              </span>
            </>
          ) : (
            <span className="text-neutral-400 text-xs sm:text-sm font-normal">
              Select entity or case...
            </span>
          )}
        </div>
        <ChevronDown className={`h-4 w-4 text-neutral-500 shrink-0 transition-transform ${isOpen ? 'rotate-180 text-blue-600' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute left-0 right-0 z-50 mt-1 max-h-80 w-full overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-xl flex flex-col animate-in fade-in-50 zoom-in-95 duration-100">
          {/* Search Header */}
          <div className="p-2 border-b border-neutral-100 bg-neutral-50/80 flex items-center gap-2">
            <Search className="h-4 w-4 text-neutral-400 shrink-0 ml-1" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search cases, suspects, phones, accounts, evidence..."
              className="w-full bg-transparent text-xs sm:text-sm font-medium text-neutral-900 placeholder:text-neutral-400 outline-none"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                className="text-neutral-400 hover:text-neutral-600 p-0.5 rounded"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Quick Info Bar */}
          <div className="px-3 py-1 bg-blue-50/60 border-b border-blue-100/50 flex items-center justify-between text-[11px] text-blue-700 font-medium">
            <span>
              {query.trim().length >= 2
                ? `Search results for "${query}" (${displayedOptions.length})`
                : 'Suggested & Golden demo entities:'}
            </span>
            {isSearching && <span className="animate-pulse">Searching…</span>}
          </div>

          {/* Options List */}
          <div className="overflow-y-auto flex-1 p-1 max-h-60 space-y-0.5">
            {displayedOptions.length === 0 ? (
              <div className="py-6 text-center text-xs text-neutral-500 space-y-1">
                <p className="font-semibold text-neutral-700">No entities found</p>
                <p className="text-[11px]">Try searching by name, FIR number, phone, bank account, or node ID.</p>
              </div>
            ) : (
              displayedOptions.map((opt, idx) => {
                const isSelected = opt.id === selectedId
                const isHighlighted = idx === highlightedIndex

                return (
                  <button
                    key={`${opt.id}-${idx}`}
                    type="button"
                    onClick={() => {
                      onSelect(opt.id)
                      setIsOpen(false)
                    }}
                    onMouseEnter={() => setHighlightedIndex(idx)}
                    className={`w-full text-left flex items-start justify-between gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                      isSelected
                        ? 'bg-blue-50/80 text-blue-900 font-semibold'
                        : isHighlighted
                        ? 'bg-neutral-100 text-neutral-900'
                        : 'text-neutral-800 hover:bg-neutral-50'
                    }`}
                  >
                    <div className="flex items-start gap-2 min-w-0 flex-1">
                      <div className="mt-0.5">{getEntityIcon(opt.type)}</div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span
                            className={`rounded px-1.5 py-0.2 text-[9px] font-bold border uppercase tracking-wider shrink-0 ${getTypeBadgeClass(
                              opt.type
                            )}`}
                          >
                            {opt.type}
                          </span>
                          <span className="font-bold text-neutral-900 truncate">{opt.label}</span>
                          <span className="font-mono text-[10px] text-neutral-500 shrink-0">
                            ({opt.id})
                          </span>
                        </div>
                        {opt.subtext && (
                          <p className="text-[11px] text-neutral-500 truncate mt-0.5 font-normal">
                            {opt.subtext}
                          </p>
                        )}
                      </div>
                    </div>
                    {isSelected && <Check className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />}
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
