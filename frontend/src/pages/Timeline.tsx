import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Clock, FileText, Phone, Landmark, Briefcase, X } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import { allSourceRecords } from '@/lib/mocks/nexusFixture'
import { PageHeader } from '@/components/ui/PageHeader'
import { FilterPills } from '@/components/ui/FilterPills'

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
          setEvents(sourceEvents)
        }
      })
      .catch((err) => {
        console.error('Failed to load timeline:', err)
        setEvents([])
      })
      .finally(() => setIsLoading(false))
  }, [caseIdParam])

  // Sort events chronologically
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
  }, [events])

  const filteredEvents = useMemo(() => {
    if (activeFilter === 'ALL') return sortedEvents
    return sortedEvents.filter((ev) => {
      const t = ev.event_type.toUpperCase()
      if (activeFilter === 'CASE') return t.includes('FIR') || t.includes('CASE')
      if (activeFilter === 'CDR') return t.includes('CDR') || t.includes('CALL') || t.includes('PHONE')
      if (activeFilter === 'BANK_TXN') return t.includes('BANK') || t.includes('TXN') || t.includes('FINANCE')
      return true
    })
  }, [sortedEvents, activeFilter])

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={Clock}
        title="Investigative Timeline &amp; Events"
        subtitle="Chronological sequence of verified evidence records, FIR filings, CDR call logs, and banking transactions."
        badge={
          caseIdParam ? (
            <div className="flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-900 border border-blue-200/80">
              <span>Scoped to {caseIdParam}</span>
              <button
                onClick={() => setSearchParams({})}
                className="hover:text-blue-950 ml-1 cursor-pointer"
                title="Clear filter"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : undefined
        }
      />

      {/* Filter Tabs */}
      <FilterPills
        options={[
          { value: 'ALL', label: 'All Records', count: sortedEvents.length },
          { value: 'CASE', label: 'Case & FIR Filings', count: sortedEvents.filter(e => e.event_type.includes('FIR') || e.event_type.includes('CASE')).length },
          { value: 'CDR', label: 'CDR Call Logs', count: sortedEvents.filter(e => e.event_type.includes('CDR') || e.event_type.includes('CALL')).length },
          { value: 'BANK_TXN', label: 'Banking Wires', count: sortedEvents.filter(e => e.event_type.includes('BANK') || e.event_type.includes('TXN')).length },
        ]}
        value={activeFilter}
        onChange={setActiveFilter}
        label="Filter Source"
      />

      {/* Timeline Stream */}
      {isLoading ? (
        <div className="p-8 text-center text-xs text-neutral-500">Loading chronological timeline…</div>
      ) : filteredEvents.length === 0 ? (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center shadow-xs">
          <Clock className="mx-auto h-12 w-12 text-neutral-400" />
          <h3 className="mt-3 text-base font-bold text-neutral-800">No timeline events found</h3>
          <p className="mt-1 text-xs text-neutral-500">No events matched the selected filter in the active investigation.</p>
        </div>
      ) : (
        <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-2 before:bottom-2 before:w-0.5 before:bg-neutral-200">
          {filteredEvents.map((ev) => {
            const cfg = TYPE_CONFIG[ev.event_type.toUpperCase()] || {
              badge: 'text-neutral-800 bg-neutral-100 border-neutral-200',
              dot: 'bg-neutral-500',
              icon: FileText,
              label: ev.event_type,
            }
            const Icon = cfg.icon
            const dateStr = new Date(ev.timestamp).toLocaleString('en-IN', {
              dateStyle: 'medium',
              timeStyle: 'short',
            })

            return (
              <div key={ev.id} className="relative group">
                {/* Timeline Dot */}
                <div
                  className={`absolute -left-6 sm:-left-8 top-1.5 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white text-white shadow-2xs ${cfg.dot}`}
                >
                  <Icon className="h-3 w-3" />
                </div>

                {/* Event Card */}
                <div className="rounded-xl border border-neutral-200/90 bg-white p-4 sm:p-5 shadow-xs space-y-2 hover:border-neutral-300 transition-all">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-100 pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${cfg.badge}`}>
                        {cfg.label}
                      </span>
                      <span className="font-mono text-xs font-semibold text-neutral-500">{ev.id}</span>
                    </div>
                    <time className="text-xs font-semibold text-neutral-600 tabular-nums">
                      {dateStr}
                    </time>
                  </div>

                  <p className="text-xs sm:text-sm text-neutral-800 leading-relaxed font-medium">
                    {ev.description}
                  </p>

                  {ev.locator && (
                    <div className="flex items-center gap-2 pt-1 text-[11px] font-mono text-amber-900 bg-amber-50/70 p-2 rounded-lg border border-amber-200/70">
                      <FileText className="h-3.5 w-3.5 text-amber-700 shrink-0" />
                      <span>{ev.locator}</span>
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
