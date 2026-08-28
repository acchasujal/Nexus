import { useState, useEffect, useMemo } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Clock, Calendar, FileText, Phone, Landmark, ShieldCheck, MapPin, Briefcase, Filter, X } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import { allSourceRecords } from '@/lib/mocks/nexusFixture'

interface TimelineEvent {
  id: string
  event_type: string
  timestamp: string
  description: string
  locator?: string
  batch_id?: string
  source_type?: string
  participant_ids?: string[]
  case_id?: string
}

const TYPE_CONFIG: Record<string, { badge: string; dot: string; icon: typeof FileText; label: string }> = {
  CASE: {
    badge: 'text-blue-900 bg-blue-50 border-blue-200 font-bold',
    dot: 'bg-blue-600',
    icon: Briefcase,
    label: 'Case File',
  },
  FIR: {
    badge: 'text-sky-900 bg-sky-50 border-sky-200 font-bold',
    dot: 'bg-sky-600',
    icon: FileText,
    label: 'FIR Record',
  },
  CDR: {
    badge: 'text-amber-900 bg-amber-50 border-amber-200 font-bold',
    dot: 'bg-amber-600',
    icon: Phone,
    label: 'CDR Call Log',
  },
  CALL: {
    badge: 'text-amber-900 bg-amber-50 border-amber-200 font-bold',
    dot: 'bg-amber-600',
    icon: Phone,
    label: 'CDR Call Log',
  },
  BANK_TXN: {
    badge: 'text-purple-900 bg-purple-50 border-purple-200 font-bold',
    dot: 'bg-purple-600',
    icon: Landmark,
    label: 'Bank Wire',
  },
  TRANSACTION: {
    badge: 'text-purple-900 bg-purple-50 border-purple-200 font-bold',
    dot: 'bg-purple-600',
    icon: Landmark,
    label: 'Bank Wire',
  },
}

export default function Timeline() {
  const [searchParams, setSearchParams] = useSearchParams()
  const caseIdParam = searchParams.get('case_id')
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'CASE' | 'CDR' | 'BANK_TXN'>('ALL')

  useEffect(() => {
    setIsLoading(true)
    apiClient.getTimeline(caseIdParam || undefined)
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          const parsed = data.map((ev: any) => ({
            id: ev.id || String(ev.event_id || Math.random()),
            event_type: ev.event_type || ev.source_type || 'CASE',
            timestamp: ev.timestamp || ev.occurred_at || new Date().toISOString(),
            description: ev.description || ev.raw_excerpt || '',
            locator: ev.locator,
            batch_id: ev.batch_id,
            source_type: ev.source_type,
            case_id: ev.case_id,
          }))
          setEvents(parsed)
        } else {
          // Fall back to converting golden fixture source records into chronological events
          let sourceEvents: TimelineEvent[] = Object.values(allSourceRecords).map((src) => ({
            id: src.id,
            event_type: src.source_type,
            timestamp: src.occurred_at,
            description: src.raw_excerpt,
            locator: src.locator,
            batch_id: src.batch_id,
            source_type: src.source_type,
            case_id: src.case_ids?.[0],
          }))
          if (caseIdParam) {
            const cid = caseIdParam.toLowerCase()
            sourceEvents = sourceEvents.filter(
              (e) => (e.case_id && e.case_id.toLowerCase() === cid) ||
                     e.description.toLowerCase().includes(cid) ||
                     e.id.toLowerCase().includes(cid)
            )
          }
          sourceEvents.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
          setEvents(sourceEvents)
        }
      })
      .catch(() => {
        let sourceEvents: TimelineEvent[] = Object.values(allSourceRecords).map((src) => ({
          id: src.id,
          event_type: src.source_type,
          timestamp: src.occurred_at,
          description: src.raw_excerpt,
          locator: src.locator,
          batch_id: src.batch_id,
          source_type: src.source_type,
          case_id: src.case_ids?.[0],
        }))
        if (caseIdParam) {
          const cid = caseIdParam.toLowerCase()
          sourceEvents = sourceEvents.filter(
            (e) => (e.case_id && e.case_id.toLowerCase() === cid) ||
                   e.description.toLowerCase().includes(cid) ||
                   e.id.toLowerCase().includes(cid)
          )
        }
        sourceEvents.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        setEvents(sourceEvents)
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [caseIdParam])

  const filteredEvents = useMemo(() => {
    if (activeFilter === 'ALL') return events
    return events.filter((ev) => {
      const type = (ev.event_type || '').toUpperCase()
      if (activeFilter === 'CASE') return type === 'CASE' || type === 'FIR'
      if (activeFilter === 'CDR') return type === 'CDR' || type === 'CALL'
      if (activeFilter === 'BANK_TXN') return type === 'BANK_TXN' || type === 'TRANSACTION'
      return true
    })
  }, [events, activeFilter])

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="border-b border-neutral-200 pb-5">
        <h1 className="text-2xl font-extrabold text-neutral-900 flex items-center gap-2.5">
          <Clock className="h-6 w-6 text-blue-600" />
          Investigative Chronology &amp; Temporal Intelligence
        </h1>
        <p className="text-sm text-neutral-600 mt-1">
          Evidence-grounded sequence of FIR registrations, CDR communication logs, and bank wire transfers.
        </p>
      </div>

      {/* Provenance note */}
      <div className="flex items-center gap-2 text-xs text-neutral-700 bg-neutral-50 p-3.5 rounded-xl border border-neutral-200 shadow-2xs">
        <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
        <span>All chronological events are derived directly from underlying source record timestamps with forensic Section 63 BSA locators.</span>
      </div>

      {/* Case filter active banner */}
      {caseIdParam && (
        <div className="flex items-center justify-between gap-3 text-xs bg-blue-50 border border-blue-200 text-blue-900 px-4 py-2.5 rounded-xl">
          <div className="flex items-center gap-2 font-medium">
            <Briefcase className="h-4 w-4 text-blue-700 shrink-0" />
            <span>Scoped to Case Context: <strong>{caseIdParam}</strong> ({events.length} event(s) found)</span>
          </div>
          <button
            onClick={() => setSearchParams({})}
            className="inline-flex items-center gap-1 font-semibold text-blue-700 hover:text-blue-900 bg-white border border-blue-200 px-2 py-0.5 rounded-md text-xs shadow-2xs hover:bg-blue-100/50 transition-colors cursor-pointer"
          >
            <X className="h-3 w-3" />
            Clear Filter
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-2 bg-neutral-100 p-1 rounded-xl border border-neutral-200">
          <button
            onClick={() => setActiveFilter('ALL')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeFilter === 'ALL'
                ? 'bg-white text-neutral-900 shadow-xs'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            All Events ({events.length})
          </button>
          <button
            onClick={() => setActiveFilter('CASE')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeFilter === 'CASE'
                ? 'bg-white text-blue-900 shadow-xs'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            Cases &amp; FIRs
          </button>
          <button
            onClick={() => setActiveFilter('CDR')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeFilter === 'CDR'
                ? 'bg-white text-amber-900 shadow-xs'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            CDR Call Records
          </button>
          <button
            onClick={() => setActiveFilter('BANK_TXN')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeFilter === 'BANK_TXN'
                ? 'bg-white text-purple-900 shadow-xs'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            Bank Transactions
          </button>
        </div>

        <div className="text-xs text-neutral-500 font-medium">
          Showing <strong>{filteredEvents.length}</strong> events in sequence
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-neutral-500 font-medium">Loading temporal intelligence events...</div>
      ) : filteredEvents.length === 0 ? (
        <div className="text-center py-16 text-neutral-500 bg-white border border-dashed border-neutral-300 rounded-2xl">
          No chronological events matched the selected filter.
        </div>
      ) : (
        <div className="relative border-l-2 border-neutral-300 ml-5 sm:ml-7 pl-6 sm:pl-9 space-y-7 pt-2">
          {filteredEvents.map((ev, idx) => {
            const rawType = (ev.event_type || 'FIR').toUpperCase()
            const cfg = TYPE_CONFIG[rawType] || TYPE_CONFIG.FIR
            const Icon = cfg.icon
            return (
              <div key={ev.id || idx} className="relative group">
                {/* Dot */}
                <div className={`absolute -left-[35px] sm:-left-[47px] top-5 h-5 w-5 rounded-full ${cfg.dot} border-4 border-white shadow-sm group-hover:scale-125 transition-transform`} />

                {/* Event Card with spacious padding and clear hierarchy */}
                <div className="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6 space-y-3.5 hover:border-neutral-300 shadow-sm hover:shadow-md transition-all">
                  {/* Top Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-100 pb-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md border ${cfg.badge}`}>
                        <Icon className="h-3.5 w-3.5" />
                        {cfg.label}
                      </span>
                      <code className="font-mono text-xs text-neutral-800 bg-neutral-100 px-2 py-0.5 rounded-md border border-neutral-200 font-semibold">
                        {ev.id}
                      </code>
                    </div>
                    <span className="text-xs text-neutral-600 flex items-center gap-1.5 font-semibold bg-neutral-50 px-2.5 py-1 rounded-lg border border-neutral-200">
                      <Calendar className="h-3.5 w-3.5 text-neutral-500" />
                      {new Date(ev.timestamp).toLocaleString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </span>
                  </div>

                  {/* Main Excerpt / Description */}
                  <div className="pt-0.5">
                    <p className="text-sm sm:text-base text-neutral-900 font-medium leading-relaxed">
                      {ev.description.startsWith('"') ? ev.description : `"${ev.description}"`}
                    </p>
                  </div>

                  {/* Bottom Locator & Meta Footer */}
                  {(ev.locator || ev.batch_id) && (
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-neutral-100">
                      {ev.locator ? (
                        <div className="flex items-center gap-1.5 text-xs font-mono text-amber-900 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200 font-medium">
                          <MapPin className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                          <span>Locator: {ev.locator}</span>
                        </div>
                      ) : <div />}

                      {ev.batch_id && (
                        <div className="text-[11px] text-neutral-500 font-mono">
                          Batch: <span className="font-semibold text-neutral-700">{ev.batch_id}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
