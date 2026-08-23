import { useMemo, useState } from 'react'
import { ClockBadge } from '@/components/ClockBadge'
import { 
  Briefcase, 
  User, 
  ShieldAlert, 
  Layers, 
  AlertTriangle, 
  FileText, 
  TrendingUp, 
  ChevronRight, 
  Printer, 
  Download,
  Calendar,
  Sparkles
} from 'lucide-react'

interface TimelineEvent {
  id: string
  type: 'fir' | 'evidence' | 'dependency' | 'escalation' | 'clock' | 'audit'
  timestamp: string
  title: string
  description: string
  severity: 'normal' | 'warning' | 'critical'
  milestone: boolean
  entityId?: string
}

interface InvestigationTimelineProps {
  caseDetail: any
  selectedEntityId: string | null
  onEntitySelect: (id: string | null) => void
}

export function InvestigationTimeline({ caseDetail, selectedEntityId, onEntitySelect }: InvestigationTimelineProps) {
  const [filter, setFilter] = useState<string>('all')

  // Deterministically derive chronological timeline events from case record properties
  const events = useMemo<TimelineEvent[]>(() => {
    if (!caseDetail) return []
    const list: TimelineEvent[] = []

    // 1. FIR Registration Milestone
    list.push({
      id: `fir-${caseDetail.id}`,
      type: 'fir',
      timestamp: '12 Oct 2026',
      title: 'FIR Registered & Clock Initiated',
      description: `Statutory clock bounds configured for Ashok Nagar PS jurisdiction. Category: ${caseDetail.offence_category}.`,
      severity: 'normal',
      milestone: true,
      entityId: caseDetail.id
    })

    // 2. Evidence Collected events
    list.push({
      id: 'ev-cdr',
      type: 'evidence',
      timestamp: '14 Oct 2026',
      title: 'CDR Phone logs acquired',
      description: 'Call Detail Record logs for prime suspect Ramesh Gowda requested and parsed.',
      severity: 'normal',
      milestone: false,
      entityId: '2' // Ramesh Gowda
    })

    // 3. Dependencies created/escalated
    caseDetail.dependencies.forEach((dep: any, index: number) => {
      list.push({
        id: `dep-created-${dep.id}`,
        type: 'dependency',
        timestamp: `${15 + index} Oct 2026`,
        title: `${dep.name} Pending`,
        description: `Evidentiary dependency created. Status: ${dep.status}. Stale: ${dep.days_stale} days.`,
        severity: dep.status === 'escalated' ? 'warning' : 'normal',
        milestone: false,
        entityId: dep.id
      })

      if (dep.status === 'escalated') {
        list.push({
          id: `dep-esc-${dep.id}`,
          type: 'escalation',
          timestamp: `${20 + index} Oct 2026`,
          title: `Blocker Escalated to SHO`,
          description: `Evidentiary blocker '${dep.name}' exceeded statutory SLA threshold. Route escalation trigger.`,
          severity: 'critical',
          milestone: true,
          entityId: dep.id
        })
      }
    })

    // 4. Clock warnings / breaches
    caseDetail.clocks.forEach((clk: any) => {
      if (clk.status === 'red') {
        list.push({
          id: `clk-warn-${clk.id}`,
          type: 'clock',
          timestamp: '26 Oct 2026',
          title: 'Statutory Clock Alert',
          description: `Clock '${clk.clock_type}' has entered RED status under BNSS guidelines. Only ${clk.days_remaining} days remaining.`,
          severity: 'warning',
          milestone: true,
          entityId: clk.id
        })
      } else if (clk.status === 'overdue') {
        list.push({
          id: `clk-breach-${clk.id}`,
          type: 'clock',
          timestamp: '02 Nov 2026',
          title: 'Statutory Clock Breached',
          description: `Statutory clock bounds exceeded for '${clk.clock_type}'. High risk of default bail assignment.`,
          severity: 'critical',
          milestone: true,
          entityId: clk.id
        })
      }
    })

    return list.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
  }, [caseDetail])

  // Filtered list
  const filteredEvents = useMemo(() => {
    if (filter === 'all') return events
    return events.filter(e => e.type === filter)
  }, [events, filter])

  // Deterministic summary calculation
  const totalClocks = caseDetail?.clocks?.length || 0
  const breachedClocks = caseDetail?.clocks?.filter((c: any) => c.status === 'overdue').length || 0
  const pendingDeps = caseDetail?.dependencies?.filter((d: any) => d.status !== 'resolved').length || 0

  const summaryText = useMemo(() => {
    return `Investigation has remained active. There are ${totalClocks} statutory clocks, ${breachedClocks} of which are breached. ${pendingDeps} unresolved evidentiary dependencies are currently blocking progress. Immediate review recommended.`
  }, [totalClocks, breachedClocks, pendingDeps])

  const handlePrint = () => {
    window.print()
  }

  return (
    <div className="space-y-6">
      {/* Narrative Progress Indicator */}
      <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-neutral-200 pb-2">
          <h3 className="text-small font-bold text-neutral-800 uppercase flex items-center gap-1.5">
            <TrendingUp className="h-4.5 w-4.5 text-status-info" /> Narrative Progress
          </h3>
          <div className="flex gap-2">
            <button
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-caption font-semibold bg-white border border-neutral-200 rounded-radius-sm text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              <Printer className="h-3.5 w-3.5" /> Print Timeline
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between text-caption font-semibold text-neutral-500 mt-2 px-2">
          <div className="flex flex-col items-center gap-1">
            <span className="w-6 h-6 rounded-full bg-status-success text-white flex items-center justify-center font-mono">1</span>
            <span>FIR Registered</span>
          </div>
          <ChevronRight className="h-4 w-4 text-neutral-300" />
          <div className="flex flex-col items-center gap-1">
            <span className={`w-6 h-6 rounded-full text-white flex items-center justify-center font-mono ${events.some(e => e.type === 'evidence') ? 'bg-status-success' : 'bg-neutral-300'}`}>2</span>
            <span>Evidence Collected</span>
          </div>
          <ChevronRight className="h-4 w-4 text-neutral-300" />
          <div className="flex flex-col items-center gap-1">
            <span className={`w-6 h-6 rounded-full text-white flex items-center justify-center font-mono ${pendingDeps > 0 ? 'bg-status-warning' : 'bg-neutral-300'}`}>3</span>
            <span>Dependencies</span>
          </div>
          <ChevronRight className="h-4 w-4 text-neutral-300" />
          <div className="flex flex-col items-center gap-1">
            <span className={`w-6 h-6 rounded-full text-white flex items-center justify-center font-mono ${breachedClocks > 0 ? 'bg-status-danger' : 'bg-neutral-300'}`}>4</span>
            <span>Clock Breach</span>
          </div>
          <ChevronRight className="h-4 w-4 text-neutral-300" />
          <div className="flex flex-col items-center gap-1">
            <span className={`w-6 h-6 rounded-full text-white flex items-center justify-center font-mono ${events.some(e => e.type === 'escalation') ? 'bg-status-danger' : 'bg-neutral-300'}`}>5</span>
            <span>Escalation</span>
          </div>
        </div>

        <div className="text-small text-neutral-600 bg-white border border-neutral-200 p-3 rounded-radius-sm mt-3 leading-relaxed">
          <span className="font-bold text-neutral-800">Investigation Chronological Summary:</span> {summaryText}
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-neutral-200 pb-3">
        {['all', 'fir', 'evidence', 'dependency', 'escalation', 'clock'].map(type => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`px-3 py-1.5 rounded-radius-md text-caption font-semibold uppercase tracking-wider transition-colors ${
              filter === type 
                ? 'bg-neutral-800 text-neutral-100' 
                : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
            }`}
          >
            {type}
          </button>
        ))}
      </div>

      {/* Vertical Timeline */}
      <div className="relative border-l border-neutral-200 pl-6 ml-3 space-y-6">
        {filteredEvents.map(event => {
          const isSelected = selectedEntityId === event.entityId
          let iconBg = 'bg-neutral-100 text-neutral-500'
          let severityClass = 'border-neutral-200 bg-white'

          if (event.type === 'fir') iconBg = 'bg-rose-100 text-rose-600'
          else if (event.type === 'evidence') iconBg = 'bg-sky-100 text-sky-600'
          else if (event.type === 'dependency') iconBg = 'bg-amber-100 text-amber-600'
          else if (event.type === 'escalation') iconBg = 'bg-rose-600 text-white'

          if (event.severity === 'warning') severityClass = 'border-amber-200 bg-amber-50/50'
          else if (event.severity === 'critical') severityClass = 'border-rose-200 bg-rose-50/50'

          return (
            <div 
              key={event.id} 
              onClick={() => event.entityId && onEntitySelect(event.entityId)}
              className={`relative p-4 rounded-radius-md border shadow-xs transition-all duration-fast cursor-pointer ${severityClass} ${
                isSelected ? 'ring-2 ring-status-info border-status-info scale-[1.01]' : 'hover:border-neutral-300'
              }`}
            >
              {/* Event Icon bullet */}
              <span className={`absolute -left-9 top-4 w-6 h-6 rounded-full flex items-center justify-center shadow-sm z-10 ${iconBg}`}>
                {event.type === 'fir' && <Briefcase className="h-3 w-3" />}
                {event.type === 'evidence' && <Layers className="h-3 w-3" />}
                {event.type === 'dependency' && <ShieldAlert className="h-3 w-3" />}
                {event.type === 'escalation' && <AlertTriangle className="h-3 w-3" />}
                {event.type === 'clock' && <Calendar className="h-3 w-3" />}
              </span>

              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] font-mono font-bold text-neutral-400 block mb-0.5">{event.timestamp}</span>
                  <h4 className="text-small font-bold text-neutral-800 flex items-center gap-1.5">
                    {event.title}
                    {event.milestone && (
                      <span className="text-[9px] font-bold text-white bg-neutral-700 px-1 rounded-radius-sm flex items-center gap-0.5">
                        <Sparkles className="h-2 w-2" /> Milestone
                      </span>
                    )}
                  </h4>
                </div>
                <span className="text-[10px] uppercase font-bold text-neutral-400 bg-neutral-200/50 px-1.5 py-0.5 rounded-radius-sm">
                  {event.type}
                </span>
              </div>

              <p className="text-small text-neutral-600 mt-2 leading-relaxed">
                {event.description}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
