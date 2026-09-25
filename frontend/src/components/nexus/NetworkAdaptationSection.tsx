/**
 * frontend/src/components/nexus/NetworkAdaptationSection.tsx
 *
 * P1-C: Network Adaptation Radar & Structural Reconfiguration Section.
 * Detects and presents criminal network topological reorganizations post-enforcement:
 *   - Intermediary Replacement: Proxy conduits (A -> X -> B) replacing severed direct contact
 *   - Bridge Substitution: Alternate brokers assuming inter-community articulation roles
 *   - Financial Rerouting: High-value transaction flows fragmented or routed through mule accounts
 *   - Community Reconnection: New cross-cell conduits bridging previously isolated modules
 *
 * Compliant with:
 *   - Zero Predictive Guilt Constraints (Pure topological structural transition logging)
 *   - Strict Evidence Grounding (Citations to underlying FIR/CDR/KYC/TXN source records)
 *   - Officer Decision Workflow (CONFIRM, DISMISS, MONITOR) with immutable cryptographic audit trail.
 */

import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  GitFork,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Eye,
  RefreshCw,
  Clock,
  Filter,
  Layers,
  Repeat,
  Landmark,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Network,
} from 'lucide-react'
import {
  useNetworkAdaptations,
  useDecideNetworkAdaptation,
  useNetworkAdaptationSummary,
} from '@/hooks/useNexus'
import { MetricCard } from '@/components/ui/MetricCard'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import type {
  NetworkAdaptationEvent,
  AdaptationReviewStatus,
} from '@shared/contracts/api'

const TYPE_CONFIG: Record<
  string,
  { label: string; icon: React.ComponentType<{ className?: string }>; border: string; bg: string; text: string }
> = {
  INTERMEDIARY_REPLACEMENT: {
    label: 'Intermediary Replacement (Proxy Conduit)',
    icon: Repeat,
    border: 'border-blue-200',
    bg: 'bg-blue-50',
    text: 'text-blue-800',
  },
  BRIDGE_SUBSTITUTION: {
    label: 'Bridge Substitution (Cross-Cell Broker)',
    icon: GitFork,
    border: 'border-amber-200',
    bg: 'bg-amber-50',
    text: 'text-amber-900',
  },
  FINANCIAL_REROUTING: {
    label: 'Financial Rerouting (Smurfing Layer)',
    icon: Landmark,
    border: 'border-emerald-200',
    bg: 'bg-emerald-50',
    text: 'text-emerald-900',
  },
  COMMUNITY_RECONNECTION: {
    label: 'Community Reconnection (Syndicate Fusion)',
    icon: Layers,
    border: 'border-purple-200',
    bg: 'bg-purple-50',
    text: 'text-purple-900',
  },
}

const STATUS_BADGE: Record<string, { label: string; bg: string; text: string; border: string }> = {
  DETECTED: { label: 'ADAPTATION DETECTED', bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200' },
  CONFIRMED: { label: 'INVESTIGATOR CONFIRMED', bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200' },
  DISMISSED: { label: 'DISMISSED', bg: 'bg-neutral-100', text: 'text-neutral-600', border: 'border-neutral-200' },
  MONITORING: { label: 'ACTIVE MONITORING', bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-200' },
}

export function NetworkAdaptationSection() {
  const {
    data: adaptations = [],
    isLoading,
    error,
    refetch,
  } = useNetworkAdaptations()

  const { data: summary, refetch: refetchSummary } = useNetworkAdaptationSummary()
  const decideMutation = useDecideNetworkAdaptation()

  const [typeFilter, setTypeFilter] = useState<string>('ALL')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [decisionNote, setDecisionNote] = useState('')
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null)
  const [expandedWhy, setExpandedWhy] = useState<string | null>(null)

  const filteredAdaptations = useMemo(() => {
    return adaptations.filter((a) => {
      if (typeFilter !== 'ALL' && a.adaptation_type !== typeFilter) return false
      if (statusFilter !== 'ALL' && a.review_status !== statusFilter) return false
      return true
    })
  }, [adaptations, typeFilter, statusFilter])

  const handleDecide = async (adaptationId: string, status: AdaptationReviewStatus) => {
    setFeedbackMsg(null)
    try {
      await decideMutation.mutateAsync({
        adaptationId,
        req: {
          status,
          note: decisionNote.trim() || undefined,
        },
      })
      setDecisionNote('')
      setFeedbackMsg(`Decision successfully logged: Marked as ${status}`)
      void refetchSummary()
    } catch (err) {
      console.error('Failed to decide network adaptation:', err)
      setFeedbackMsg('Failed to record adaptation decision. Please try again.')
    }
  }

  if (isLoading) return <LoadingSkeleton layout="card" />
  if (error) return <ErrorState message="Failed to load Network Adaptation Radar." onRetry={() => void refetch()} />

  return (
    <div className="space-y-6">
      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Structural Adaptations"
          value={summary?.total_adaptations ?? adaptations.length}
          icon={GitFork}
          badge={{ text: `${summary?.intermediary_replacements ?? 0} Proxy Hops`, variant: 'info' }}
          subtext="Reconfigurations post-enforcement"
        />
        <MetricCard
          label="Bridge Broker Substitutions"
          value={summary?.bridge_substitutions ?? 0}
          icon={Layers}
          badge={{ text: 'Inter-Syndicate', variant: 'warning' }}
          subtext="Articulation points replaced"
        />
        <MetricCard
          label="Financial Layering Reroutes"
          value={summary?.financial_reroutings ?? 0}
          icon={Landmark}
          badge={{ text: 'Mule Layering', variant: 'neutral' }}
          subtext="Transaction path redirections"
        />
        <MetricCard
          label="Confirmed Adaptations"
          value={summary?.confirmed_adaptations ?? 0}
          icon={ShieldCheck}
          badge={{ text: 'IO Corroborated', variant: 'success' }}
          subtext="Signed into investigation record"
        />
      </div>

      {/* Control Bar: Filters & Refresh */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl border border-neutral-200/80 shadow-2xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-neutral-500 flex items-center gap-1 mr-1">
            <Filter className="h-3.5 w-3.5" /> Adaptation Type:
          </span>
          {['ALL', 'INTERMEDIARY_REPLACEMENT', 'BRIDGE_SUBSTITUTION', 'FINANCIAL_REROUTING', 'COMMUNITY_RECONNECTION'].map((t) => (
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
            title="Refresh Network Adaptation Radar"
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

      {/* Adaptation Events Grid */}
      {filteredAdaptations.length === 0 ? (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center text-neutral-500">
          No network adaptation events match the current filter selection.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredAdaptations.map((a) => {
            const typeConf = TYPE_CONFIG[a.adaptation_type] || TYPE_CONFIG.INTERMEDIARY_REPLACEMENT
            const statusConf = STATUS_BADGE[a.review_status] || STATUS_BADGE.DETECTED
            const Icon = typeConf.icon

            return (
              <div
                key={a.adaptation_id}
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
                        <h3 className="text-sm font-bold text-neutral-900">{a.primary_entity_name}</h3>
                        <p className="text-[11px] font-mono text-neutral-500">Target: {a.secondary_entity_name}</p>
                      </div>
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusConf.bg} ${statusConf.text} ${statusConf.border}`}
                    >
                      {statusConf.label}
                    </span>
                  </div>

                  {/* Structural Path Reconfiguration Panel */}
                  <div className="mt-4 rounded-lg bg-neutral-50 border border-neutral-200/80 p-3.5 space-y-2">
                    <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider flex items-center justify-between">
                      <span>{typeConf.label}</span>
                      {a.time_lag_days !== null && (
                        <span className="text-neutral-700 font-bold flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {a.time_lag_days} Days Lag
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 pt-1">
                      <div className="flex-1 bg-white p-2.5 rounded-md border border-neutral-200 shadow-2xs">
                        <div className="flex items-center justify-between">
                          <span className="block text-[10px] font-bold text-neutral-400 uppercase">Previous Direct Link</span>
                          <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-neutral-100 text-neutral-600 font-bold">OBSERVED</span>
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <code className="text-xs font-bold text-neutral-700">{a.previous_path[0]}</code>
                          <ArrowRight className="h-3 w-3 text-neutral-400" />
                          <code className="text-xs font-bold text-neutral-700">{a.previous_path[a.previous_path.length - 1]}</code>
                        </div>
                        <span className="block text-[10px] text-red-600 font-semibold mt-0.5">Direct link severed</span>
                      </div>

                      <ArrowRight className="h-4 w-4 text-neutral-400 shrink-0" />

                      <div className="flex-1 bg-white p-2.5 rounded-md border border-blue-200 shadow-2xs">
                        <div className="flex items-center justify-between">
                          <span className="block text-[10px] font-bold text-blue-800 uppercase">Substituted Proxy Conduit</span>
                          <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                            a.review_status === 'CONFIRMED'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : 'bg-amber-100 text-amber-800 border border-amber-200'
                          }`}>
                            {a.review_status === 'CONFIRMED' ? 'CONFIRMED' : 'PROPOSED'}
                          </span>
                        </div>
                        <div className="flex items-center gap-1 flex-wrap mt-0.5">
                          <code className="text-xs font-bold text-neutral-700">{a.new_path[0]}</code>
                          <ArrowRight className="h-3 w-3 text-neutral-400" />
                          <span className="px-1.5 py-0.5 bg-blue-100 text-blue-900 font-bold rounded text-[11px]">
                            {a.substitute_intermediary_name}
                          </span>
                          {a.new_path.length > 2 && (
                            <>
                              <ArrowRight className="h-3 w-3 text-neutral-400" />
                              <code className="text-xs font-bold text-neutral-700">{a.new_path[a.new_path.length - 1]}</code>
                            </>
                          )}
                        </div>
                        <span className="block text-[10px] text-blue-700 font-semibold mt-0.5">
                          Sig: {(a.structural_significance * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Corroborating Context */}
                  <p className="mt-3 text-xs text-neutral-700 leading-relaxed bg-neutral-50/50 p-2.5 rounded-lg border border-neutral-100">
                    {a.corroborating_context}
                  </p>

                  {/* Evidence Provenance Citations */}
                  {a.evidence_refs.length > 0 && (
                    <div className="mt-3 flex flex-wrap items-center gap-1.5">
                      <span className="text-[11px] font-bold text-neutral-500 mr-1">Section 63 BSA Grounding:</span>
                      {a.evidence_refs.map((ref) => (
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
                      onClick={() => setExpandedWhy(expandedWhy === a.adaptation_id ? null : a.adaptation_id)}
                      className="w-full flex items-center justify-between p-2.5 bg-neutral-50 hover:bg-neutral-100 transition text-left cursor-pointer font-bold text-neutral-800"
                    >
                      <span className="flex items-center gap-1.5">
                        <HelpCircle className="h-3.5 w-3.5 text-indigo-600" />
                        Why this appeared (Deterministic Signal Grounding)
                      </span>
                      {expandedWhy === a.adaptation_id ? <ChevronUp className="h-4 w-4 text-neutral-500" /> : <ChevronDown className="h-4 w-4 text-neutral-500" />}
                    </button>
                    {expandedWhy === a.adaptation_id && (
                      <div className="p-3 space-y-2 border-t border-neutral-200 bg-indigo-50/20">
                        <p className="text-[11px] text-neutral-700 leading-relaxed">
                          This {typeConf.label.toLowerCase()} anomaly was detected via deterministic structural graph analysis comparing snapshots. 
                          The system observed a severed link replaced by <strong className="text-neutral-900">{a.substitute_intermediary_name}</strong>.
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px] text-neutral-600 pt-1">
                          <div className="p-2 rounded bg-white border border-neutral-200 space-y-0.5">
                            <div className="font-bold text-neutral-800">Graph Trigger Scope:</div>
                            <div>Identifier: <strong>{typeConf.label}</strong></div>
                            <div>Supporting records: <strong>{a.evidence_refs.length} provenance items</strong></div>
                          </div>
                          <div className="p-2 rounded bg-white border border-neutral-200 space-y-0.5">
                            <div className="font-bold text-neutral-800">Evidence Baseline:</div>
                            <div>Structural Sig: <strong>{(a.structural_significance * 100).toFixed(0)}%</strong></div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Investigator Decision Record if decided */}
                  {a.decided_at && (
                    <div className="mt-3 p-2.5 rounded-lg bg-emerald-50/60 border border-emerald-200 text-xs text-emerald-950 space-y-1">
                      <div className="flex items-center gap-1.5 font-bold">
                        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                        <span>Actioned by {a.decided_by} on {new Date(a.decided_at).toLocaleString()}</span>
                      </div>
                      {a.investigator_note && (
                        <p className="text-[11px] text-emerald-900 italic">"{a.investigator_note}"</p>
                      )}
                    </div>
                  )}

                  {/* Next Action Links */}
                  <div className="mt-3 flex items-center gap-2 pt-2 border-t border-neutral-100">
                    <Link
                      to={`/network?node_id=${encodeURIComponent(a.primary_entity_id)}&snapshot_id=snap-current&focus=2hop&drawer=true&feature_type=NETWORK_ADAPTATION`}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-[11px] transition shadow-2xs cursor-pointer"
                    >
                      <Network className="h-3 w-3" />
                      Inspect {a.primary_entity_name} in Graph
                    </Link>
                  </div>
                </div>

                {/* Investigator Action Bar */}
                <div className="pt-3 border-t border-neutral-100 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleDecide(a.adaptation_id, 'CONFIRMED' as AdaptationReviewStatus)}
                      disabled={decideMutation.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 hover:text-emerald-900 bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md border border-emerald-200 transition-colors cursor-pointer"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" /> Confirm
                    </button>
                    <button
                      onClick={() => handleDecide(a.adaptation_id, 'MONITORING' as AdaptationReviewStatus)}
                      disabled={decideMutation.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-md border border-blue-200 transition-colors cursor-pointer"
                    >
                      <Eye className="h-3.5 w-3.5" /> Monitor
                    </button>
                    <button
                      onClick={() => handleDecide(a.adaptation_id, 'DISMISSED' as AdaptationReviewStatus)}
                      disabled={decideMutation.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-neutral-600 hover:text-neutral-900 bg-neutral-100 hover:bg-neutral-200 px-2.5 py-1 rounded-md border border-neutral-200 transition-colors cursor-pointer"
                    >
                      <XCircle className="h-3.5 w-3.5" /> Dismiss
                    </button>
                  </div>

                  <span className="text-[10px] font-mono text-neutral-400">
                    {a.adaptation_id}
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
