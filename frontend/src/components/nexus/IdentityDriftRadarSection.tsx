/**
 * frontend/src/components/nexus/IdentityDriftRadarSection.tsx
 *
 * P1-B: Identity Drift Radar & Identifier Transition Section.
 * Surfaces operational transitions across suspects and persons of interest:
 *   - Phone Turnover (Burner SIM hopping)
 *   - Device Hopping (IMEI switching)
 *   - Vehicle Drift (Registration switches)
 *   - Alias Evolution (Moniker variations across FIRs)
 *
 * Compliant with:
 *   - Zero Predictive Guilt Constraints (Pure operational communication anomaly tracking)
 *   - Strict Evidence Grounding (Citations to underlying FIR/CDR/KYC source records)
 *   - Officer Decision Workflow (CONFIRM, DISMISS, MONITOR) with immutable audit trail.
 */

import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Radio,
  Phone,
  Smartphone,
  Car,
  UserCheck,
  CheckCircle2,
  XCircle,
  Eye,
  ShieldCheck,
  RefreshCw,
  Clock,
  ArrowRight,
  Filter,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Network,
} from 'lucide-react'
import {
  useIdentityDrifts,
  useDecideIdentityDrift,
  useIdentityDriftSummary,
} from '@/hooks/useNexus'
import { SyncStatus } from '@/components/SyncStatus'
import { MetricCard } from '@/components/ui/MetricCard'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import type {
  IdentityDriftEvent,
  IdentityDriftStatus,
  IdentityDriftType,
} from '@shared/contracts/api'

interface IdentityDriftRadarSectionProps {
  personId?: string | null
}

const TYPE_CONFIG: Record<
  string,
  { label: string; icon: React.ComponentType<{ className?: string }>; border: string; bg: string; text: string }
> = {
  PHONE_TURNOVER: {
    label: 'Phone Turnover (Burner SIM)',
    icon: Phone,
    border: 'border-blue-200',
    bg: 'bg-blue-50',
    text: 'text-blue-800',
  },
  DEVICE_HOP: {
    label: 'Device Hopping (IMEI Switch)',
    icon: Smartphone,
    border: 'border-amber-200',
    bg: 'bg-amber-50',
    text: 'text-amber-900',
  },
  VEHICLE_DRIFT: {
    label: 'Vehicle Registration Drift',
    icon: Car,
    border: 'border-emerald-200',
    bg: 'bg-emerald-50',
    text: 'text-emerald-900',
  },
  ALIAS_EVOLUTION: {
    label: 'Alias Moniker Evolution',
    icon: UserCheck,
    border: 'border-purple-200',
    bg: 'bg-purple-50',
    text: 'text-purple-900',
  },
}

const STATUS_BADGE: Record<string, { label: string; bg: string; text: string; border: string }> = {
  DETECTED: { label: 'ANOMALY DETECTED', bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200' },
  CONFIRMED: { label: 'INVESTIGATOR CONFIRMED', bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200' },
  DISMISSED: { label: 'DISMISSED', bg: 'bg-neutral-100', text: 'text-neutral-600', border: 'border-neutral-200' },
  MONITORING: { label: 'ACTIVE MONITORING', bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-200' },
}

export function IdentityDriftRadarSection({ personId }: IdentityDriftRadarSectionProps) {
  const {
    data: drifts = [],
    isLoading,
    error,
    refetch,
    syncState,
  } = useIdentityDrifts(personId || undefined)

  const { data: summary, refetch: refetchSummary, syncState: summaryState, isError: summaryError } = useIdentityDriftSummary()
  const decideMutation = useDecideIdentityDrift()

  const [typeFilter, setTypeFilter] = useState<string>('ALL')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [selectedDrift, setSelectedDrift] = useState<IdentityDriftEvent | null>(null)
  const [decisionNote, setDecisionNote] = useState('')
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null)
  const [expandedWhy, setExpandedWhy] = useState<string | null>(null)

  const filteredDrifts = useMemo(() => {
    return drifts.filter((d) => {
      if (typeFilter !== 'ALL' && d.drift_type !== typeFilter) return false
      if (statusFilter !== 'ALL' && d.human_status !== statusFilter) return false
      return true
    })
  }, [drifts, typeFilter, statusFilter])

  const handleDecide = async (driftId: string, status: IdentityDriftStatus) => {
    setFeedbackMsg(null)
    try {
      await decideMutation.mutateAsync({
        driftId,
        req: {
          status,
          note: decisionNote.trim() || undefined,
        },
      })
      setDecisionNote('')
      setFeedbackMsg(`Decision successfully logged: Marked as ${status}`)
      void refetchSummary()
    } catch (err) {
      console.error('Failed to decide identity drift:', err)
      setFeedbackMsg('Failed to record decision. Please try again.')
    }
  }

  if (isLoading) return <LoadingSkeleton layout="card" />
  if (error) return <ErrorState message="Failed to load Identity Drift Radar." onRetry={() => void refetch()} />

  return (
    <div className="space-y-6">
      <SyncStatus state={syncState === 'confirmed' ? summaryState : syncState} />
      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Drift Events"
          value={summary?.total_drifts ?? drifts.length}
          icon={Radio}
          badge={{ text: `${summary?.phone_turnovers ?? (summaryError ? 'Unavailable' : '...')} SIM Shifts`, variant: 'info' }}
          subtext="Identifier transitions across records"
        />
        <MetricCard
          label="Hardware IMEI Hops"
          value={summary?.device_hops ?? (summaryError ? 'Unavailable' : '...')}
          icon={Smartphone}
          badge={{ text: 'Device Hopping', variant: 'warning' }}
          subtext="Telecom switch device movements"
        />
        <MetricCard
          label="Moniker Evolutions"
          value={summary?.alias_evolutions ?? (summaryError ? 'Unavailable' : '...')}
          icon={UserCheck}
          badge={{ text: 'Multi-Jurisdiction', variant: 'neutral' }}
          subtext="Cross-case suspect alias variants"
        />
        <MetricCard
          label="Confirmed Links"
          value={summary?.confirmed_drifts ?? (summaryError ? 'Unavailable' : '...')}
          icon={ShieldCheck}
          badge={{ text: 'Officer Audited', variant: 'success' }}
          subtext="Signed into investigation record"
        />
      </div>

      {/* Control Bar: Filters & Refresh */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl border border-neutral-200/80 shadow-2xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-neutral-500 flex items-center gap-1 mr-1">
            <Filter className="h-3.5 w-3.5" /> Type:
          </span>
          {['ALL', 'PHONE_TURNOVER', 'DEVICE_HOP', 'VEHICLE_DRIFT', 'ALIAS_EVOLUTION'].map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`px-3 py-1 text-xs font-semibold rounded-lg border transition-colors cursor-pointer ${
                typeFilter === t
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'bg-neutral-50 text-neutral-600 border-neutral-200 hover:bg-neutral-100'
              }`}
            >
              {t === 'ALL' ? 'All Types' : t.replaceAll('_', ' ')}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border border-neutral-200 rounded-lg px-3 py-1.5 bg-neutral-50 font-medium text-neutral-700"
          >
            <option value="ALL">All Statuses</option>
            <option value="DETECTED">Detected (Pending)</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="MONITORING">Monitoring</option>
            <option value="DISMISSED">Dismissed</option>
          </select>
          <button
            onClick={() => {
              void refetch()
              void refetchSummary()
            }}
            className="p-1.5 text-neutral-500 hover:text-neutral-900 rounded-lg border border-neutral-200 hover:bg-neutral-50 cursor-pointer"
            title="Refresh Drift Radar"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {feedbackMsg && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-xs font-semibold text-blue-900 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-blue-600 shrink-0" />
          <span>{feedbackMsg}</span>
        </div>
      )}

      {/* Drift Events Grid */}
      {filteredDrifts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center text-neutral-500">
          No identity drift events match the current filter selection.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredDrifts.map((d) => {
            const typeConf = TYPE_CONFIG[d.drift_type] || TYPE_CONFIG.PHONE_TURNOVER
            const statusConf = STATUS_BADGE[d.human_status] || STATUS_BADGE.DETECTED
            const Icon = typeConf.icon

            return (
              <div
                key={d.drift_id}
                className={`rounded-xl border ${typeConf.border} bg-white shadow-xs p-5 flex flex-col justify-between space-y-4 hover:border-neutral-400 transition-all`}
              >
                <div>
                  {/* Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className={`p-2 rounded-lg ${typeConf.bg} ${typeConf.text}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-neutral-900">{d.person_name}</h3>
                        <p className="text-[11px] font-mono text-neutral-500">ID: {d.person_id}</p>
                      </div>
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusConf.bg} ${statusConf.text} ${statusConf.border}`}
                    >
                      {statusConf.label}
                    </span>
                  </div>

                  {/* Transition Panel */}
                  <div className="mt-4 rounded-lg bg-neutral-50 border border-neutral-200/80 p-3.5 space-y-2">
                    <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider flex items-center justify-between">
                      <span>{typeConf.label}</span>
                      {d.time_window_days !== null && (
                        <span className="text-neutral-700 font-bold flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {d.time_window_days} Days Window
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 pt-1">
                      <div className="flex-1 bg-white p-2.5 rounded-md border border-neutral-200 shadow-2xs">
                        <span className="block text-[10px] font-bold text-neutral-400 uppercase">Prior Identifier</span>
                        <code className="text-xs font-bold text-neutral-800 break-all">{d.previous_value}</code>
                        {d.previous_seen_at && (
                          <span className="block text-[10px] text-neutral-400 mt-0.5">
                            {new Date(d.previous_seen_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>

                      <ArrowRight className="h-4 w-4 text-neutral-400 shrink-0" />

                      <div className="flex-1 bg-white p-2.5 rounded-md border border-neutral-200 shadow-2xs">
                        <span className="block text-[10px] font-bold text-neutral-400 uppercase">New Identifier</span>
                        <code className="text-xs font-bold text-blue-900 break-all">{d.new_value}</code>
                        {d.new_seen_at && (
                          <span className="block text-[10px] text-neutral-400 mt-0.5">
                            {new Date(d.new_seen_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Corroborating Context */}
                  <p className="mt-3 text-xs text-neutral-700 leading-relaxed bg-neutral-50/50 p-2.5 rounded-lg border border-neutral-100">
                    {d.corroborating_context}
                  </p>

                  {/* Evidence Provenance Citations */}
                  {d.evidence_refs.length > 0 && (
                    <div className="mt-3 flex flex-wrap items-center gap-1.5">
                      <span className="text-[11px] font-bold text-neutral-500 mr-1">Section 63 BSA Grounding:</span>
                      {d.evidence_refs.map((ref) => (
                        <span
                          key={ref}
                          className="px-2 py-0.5 rounded-md bg-blue-50 border border-blue-200 font-mono text-[10px] font-bold text-blue-800"
                        >
                          {ref}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* "Why This Appeared" grounded section */}
                  <div className="mt-3 rounded-lg border border-neutral-200 bg-white overflow-hidden text-xs">
                    <button
                      onClick={() => setExpandedWhy(expandedWhy === d.drift_id ? null : d.drift_id)}
                      className="w-full flex items-center justify-between p-2.5 bg-neutral-50 hover:bg-neutral-100 transition text-left cursor-pointer font-bold text-neutral-800"
                    >
                      <span className="flex items-center gap-1.5">
                        <HelpCircle className="h-3.5 w-3.5 text-indigo-600" />
                        Why this appeared (Deterministic Signal Grounding)
                      </span>
                      {expandedWhy === d.drift_id ? <ChevronUp className="h-4 w-4 text-neutral-500" /> : <ChevronDown className="h-4 w-4 text-neutral-500" />}
                    </button>
                    {expandedWhy === d.drift_id && (
                      <div className="p-3 space-y-2 border-t border-neutral-200 bg-indigo-50/20">
                        <p className="text-[11px] text-neutral-700 leading-relaxed">
                          This {typeConf.label.toLowerCase()} anomaly was detected via deterministic entity resolution comparing source records. 
                          The system observed a transition from <strong className="text-neutral-900">{d.previous_value}</strong> to <strong className="text-neutral-900">{d.new_value}</strong>.
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px] text-neutral-600 pt-1">
                          <div className="p-2 rounded bg-white border border-neutral-200 space-y-0.5">
                            <div className="font-bold text-neutral-800">Graph Trigger Scope:</div>
                            <div>Identifier: <strong>{typeConf.label}</strong></div>
                            <div>Supporting records: <strong>{d.evidence_refs.length} provenance items</strong></div>
                          </div>
                          <div className="p-2 rounded bg-white border border-neutral-200 space-y-0.5">
                            <div className="font-bold text-neutral-800">Evidence Baseline:</div>
                            <div>Transition Window: <strong>{d.time_window_days ?? 'Unknown'} days</strong></div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Investigator Decision Record if decided */}
                  {d.decided_at && (
                    <div className="mt-3 p-2.5 rounded-lg bg-emerald-50/60 border border-emerald-200 text-xs text-emerald-950 space-y-1">
                      <div className="flex items-center gap-1.5 font-bold">
                        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                        <span>Actioned by {d.decided_by} on {new Date(d.decided_at).toLocaleString()}</span>
                      </div>
                      {d.investigator_note && (
                        <p className="text-[11px] text-emerald-900 italic">"{d.investigator_note}"</p>
                      )}
                    </div>
                  )}
                  
                  {/* Next Action Links */}
                  <div className="mt-3 flex items-center gap-2 pt-2 border-t border-neutral-100">
                    <Link
                      to={`/network?node_id=${encodeURIComponent(d.person_id)}`}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-[11px] transition shadow-2xs cursor-pointer"
                    >
                      <Network className="h-3 w-3" />
                      Inspect {d.person_name} in Graph
                    </Link>
                  </div>
                </div>

                {/* Investigator Action Bar */}
                <div className="pt-3 border-t border-neutral-100 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleDecide(d.drift_id, 'CONFIRMED' as IdentityDriftStatus)}
                      disabled={decideMutation.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 hover:text-emerald-900 bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md border border-emerald-200 transition-colors cursor-pointer"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" /> Confirm
                    </button>
                    <button
                      onClick={() => handleDecide(d.drift_id, 'MONITORING' as IdentityDriftStatus)}
                      disabled={decideMutation.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-md border border-blue-200 transition-colors cursor-pointer"
                    >
                      <Eye className="h-3.5 w-3.5" /> Monitor
                    </button>
                    <button
                      onClick={() => handleDecide(d.drift_id, 'DISMISSED' as IdentityDriftStatus)}
                      disabled={decideMutation.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-neutral-600 hover:text-neutral-900 bg-neutral-100 hover:bg-neutral-200 px-2.5 py-1 rounded-md border border-neutral-200 transition-colors cursor-pointer"
                    >
                      <XCircle className="h-3.5 w-3.5" /> Dismiss
                    </button>
                  </div>

                  <span className="text-[10px] font-mono text-neutral-400">
                    {d.drift_id}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
