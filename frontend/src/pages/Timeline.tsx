import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Clock, FileText, Phone, Landmark, Briefcase, X, GitMerge, ShieldCheck, Activity, User, Tag } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import { allSourceRecords } from '@/lib/mocks/nexusFixture'
import { PageHeader } from '@/components/ui/PageHeader'
import { FilterPills } from '@/components/ui/FilterPills'

interface TimelineEvent {
  id: string
  event_type: string
  timestamp: string
  ingested_at?: string
  actor?: string
  description: string
  locator?: string
  batch_id?: string
  source_type?: string
  participant_ids?: string[]
  case_id?: string
}

type TimelineFilter = 'ALL' | 'CHANGES' | 'FIR' | 'EVIDENCE' | 'CDR' | 'TRANSACTIONS' | 'RESOLUTION'

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
  EVIDENCE: {
    badge: 'text-teal-900 bg-teal-50 border-teal-200 font-bold',
    dot: 'bg-teal-600',
    icon: ShieldCheck,
    label: 'Evidence Record',
  },
  RESOLUTION: {
    badge: 'text-emerald-900 bg-emerald-50 border-emerald-200 font-bold',
    dot: 'bg-emerald-600',
    icon: GitMerge,
    label: 'Entity Resolution',
  },
  CHANGES: {
    badge: 'text-indigo-900 bg-indigo-50 border-indigo-200 font-bold',
    dot: 'bg-indigo-600',
    icon: Activity,
    label: 'Investigative Change',
  },
  SIGNAL: {
    badge: 'text-rose-900 bg-rose-50 border-rose-200 font-bold',
    dot: 'bg-rose-600',
    icon: Activity,
    label: 'Network Pulse Signal',
  },
}

export default function Timeline() {
  const [searchParams, setSearchParams] = useSearchParams()
  const caseIdParam = searchParams.get('case_id')
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<TimelineFilter>('ALL')

  useEffect(() => {
    let active = true
    apiClient.getTimeline(caseIdParam || undefined)
      .then((data) => {
        if (!active) return
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
            ingested_at: ev.ingested_at || ev.created_at || ev.timestamp,
            actor: ev.actor || (ev.event_type?.includes('FIR') ? 'Station Duty Officer' : ev.event_type?.includes('CDR') ? 'Telecom Provider Gateway' : 'Investigating Officer'),
          }))
          setEvents(parsed)
        } else {
          // Fall back to converting golden fixture source records into chronological events
          let sourceEvents: TimelineEvent[] = Object.values(allSourceRecords).map((src) => ({
            id: src.id,
            event_type: src.source_type,
            timestamp: src.occurred_at,
            ingested_at: new Date(new Date(src.occurred_at).getTime() + 1000 * 60 * 15).toISOString(),
            actor: src.source_type.includes('CDR') ? 'Telecom Provider Nodal' : src.source_type.includes('BANK') ? 'Banking Core Gateway' : 'Station Duty Officer',
            description: src.raw_excerpt,
            locator: src.locator,
            batch_id: src.batch_id,
            source_type: src.source_type,
            case_id: src.case_ids?.[0],
          }))

          // Add synthetic investigative change and entity resolution events (B14)
          sourceEvents.push(
            {
              id: 'CHG-FUSION-01',
              event_type: 'RESOLUTION',
              timestamp: '2026-02-14T15:30:00Z',
              ingested_at: '2026-02-14T15:32:00Z',
              actor: 'Investigating Officer (IO)',
              description: 'Entity Fusion Decided: Rafiq Mohammed and Rafiq M. confirmed as unified suspect node, establishing cross-case bridge between CASE-141 and CASE-207.',
              locator: 'NEXUS Resolution Workbench #1',
              case_id: 'CASE-141',
            },
            {
              id: 'CHG-SIGNAL-02',
              event_type: 'CHANGES',
              timestamp: '2026-02-13T09:15:00Z',
              ingested_at: '2026-02-13T09:18:00Z',
              actor: 'Deterministic Graph Engine',
              description: 'Cross-District Telecom Bridge Emergence: 3 new telephony interactions detected between Mysuru and Bengaluru subscriber clusters.',
              locator: 'Network Pulse Engine PULSE-2026-0213',
              case_id: 'CASE-207',
            },
            {
              id: 'EV-SEIZURE-03',
              event_type: 'EVIDENCE',
              timestamp: '2026-02-12T18:45:00Z',
              ingested_at: '2026-02-12T19:30:00Z',
              actor: 'Cyber Crime Unit Head',
              description: 'Digital Storage Device Seized: 128GB MicroSD and Dual-SIM handset recovered from suspect vehicle during checkpoint intercept.',
              locator: 'Panchnama Property Register Item #4',
              case_id: 'CASE-141',
            }
          )

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
      .finally(() => {
        if (active) setIsLoading(false)
      })

    return () => {
      active = false
    }
  }, [caseIdParam])

  // Sort events chronologically
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
  }, [events])

  const filteredEvents = useMemo(() => {
    if (activeFilter === 'ALL') return sortedEvents
    return sortedEvents.filter((ev) => {
      const t = ev.event_type.toUpperCase()
      if (activeFilter === 'CHANGES') {
        return t.includes('SIGNAL') || t.includes('PULSE') || t.includes('CHANGE') || t.includes('MERGE') || t.includes('RESOLUTION')
      }
      if (activeFilter === 'FIR') return t.includes('FIR') || t.includes('CASE')
      if (activeFilter === 'EVIDENCE') return t.includes('EVIDENCE') || t.includes('SEIZURE')
      if (activeFilter === 'CDR') return t.includes('CDR') || t.includes('CALL') || t.includes('PHONE')
      if (activeFilter === 'TRANSACTIONS') return t.includes('BANK') || t.includes('TXN') || t.includes('FINANCE') || t.includes('TRANSACTION')
      if (activeFilter === 'RESOLUTION') return t.includes('RESOLUTION') || t.includes('FUSION') || t.includes('MERGE')
      return true
    })
  }, [sortedEvents, activeFilter])

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={Clock}
        title="Investigative Timeline &amp; Events"
        subtitle="Chronological sequence of verified evidence records, FIR filings, CDR call logs, banking transactions, and investigative graph changes."
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

      {/* Filter Tabs (B14: All, Investigative Changes, FIR, Evidence, CDR, Transactions, Entity Resolution) */}
      <FilterPills
        options={[
          { value: 'ALL', label: 'All Records', count: sortedEvents.length },
          { value: 'CHANGES', label: 'Investigative Changes', count: sortedEvents.filter(e => e.event_type.includes('SIGNAL') || e.event_type.includes('PULSE') || e.event_type.includes('CHANGE') || e.event_type.includes('MERGE') || e.event_type.includes('RESOLUTION')).length },
          { value: 'FIR', label: 'FIR Filings', count: sortedEvents.filter(e => e.event_type.includes('FIR') || e.event_type.includes('CASE')).length },
          { value: 'EVIDENCE', label: 'Evidence', count: sortedEvents.filter(e => e.event_type.includes('EVIDENCE') || e.event_type.includes('SEIZURE')).length },
          { value: 'CDR', label: 'CDR Call Logs', count: sortedEvents.filter(e => e.event_type.includes('CDR') || e.event_type.includes('CALL') || e.event_type.includes('PHONE')).length },
          { value: 'TRANSACTIONS', label: 'Transactions', count: sortedEvents.filter(e => e.event_type.includes('BANK') || e.event_type.includes('TXN') || e.event_type.includes('FINANCE')).length },
          { value: 'RESOLUTION', label: 'Entity Resolution', count: sortedEvents.filter(e => e.event_type.includes('RESOLUTION') || e.event_type.includes('FUSION') || e.event_type.includes('MERGE')).length },
        ]}
        value={activeFilter}
        onChange={(val) => setActiveFilter(val as TimelineFilter)}
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
            const observedDateStr = new Date(ev.timestamp).toLocaleString('en-IN', {
              dateStyle: 'medium',
              timeStyle: 'short',
            })
            const ingestedDateStr = ev.ingested_at ? new Date(ev.ingested_at).toLocaleString('en-IN', {
              dateStyle: 'short',
              timeStyle: 'short',
            }) : null

            return (
              <div key={ev.id} className="relative group">
                {/* Timeline Dot */}
                <div
                  className={`absolute -left-6 sm:-left-8 top-1.5 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white text-white shadow-2xs ${cfg.dot}`}
                >
                  <Icon className="h-3 w-3" />
                </div>

                {/* Event Card with Event Semantics (B14) */}
                <div className="rounded-xl border border-neutral-200/90 bg-white p-4 sm:p-5 shadow-xs space-y-2.5 hover:border-neutral-300 transition-all">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-100 pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${cfg.badge}`}>
                        {cfg.label}
                      </span>
                      <span className="font-mono text-xs font-semibold text-neutral-500">{ev.id}</span>
                      {ev.actor && (
                        <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-neutral-600 bg-neutral-100 px-2 py-0.5 rounded font-medium">
                          <User className="h-3 w-3 text-neutral-400" />
                          {ev.actor}
                        </span>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-bold text-neutral-800 tabular-nums">
                        Observed: {observedDateStr}
                      </div>
                      {ingestedDateStr && (
                        <div className="text-[10px] text-neutral-500 font-mono">
                          Ingested: {ingestedDateStr}
                        </div>
                      )}
                    </div>
                  </div>

                  <p className="text-xs sm:text-sm text-neutral-800 leading-relaxed font-medium">
                    {ev.description}
                  </p>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                    {ev.locator && (
                      <div className="flex items-center gap-2 text-[11px] font-mono text-amber-900 bg-amber-50/70 px-2 py-1 rounded-lg border border-amber-200/70">
                        <FileText className="h-3.5 w-3.5 text-amber-700 shrink-0" />
                        <span>{ev.locator}</span>
                      </div>
                    )}
                    {ev.case_id && (
                      <span className="text-[10px] font-mono font-bold text-neutral-500 bg-neutral-100 border border-neutral-200 px-1.5 py-0.5 rounded">
                        Case: {ev.case_id}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
