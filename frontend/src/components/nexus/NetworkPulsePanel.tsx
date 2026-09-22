import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity, AlertTriangle, ShieldCheck, FileCheck, ArrowRight,
  Eye, RefreshCw, ChevronDown, ChevronUp, Network, Clock, ExternalLink,
  HelpCircle,
} from 'lucide-react'
import { useIntelligenceBootstrap, useNetworkPulses } from '@/hooks/useNexus'
import type { NetworkPulseItem } from '@shared/contracts/api'

export function NetworkPulsePanel() {
  const { data: bootstrap, isLoading: isBootstrapLoading } = useIntelligenceBootstrap()
  const { data: pulses = [], isLoading: isPulsesLoading, refetch } = useNetworkPulses()
  const [selectedPulse, setSelectedPulse] = useState<NetworkPulseItem | null>(null)
  const [isWhyExpanded, setIsWhyExpanded] = useState<boolean>(true)

  const effectivePulses = pulses.length > 0
    ? pulses
    : (bootstrap?.primary_pulse ? [bootstrap.primary_pulse] : [])

  if (isPulsesLoading && isBootstrapLoading && effectivePulses.length === 0) {
    return (
      <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 text-xs text-blue-800 flex items-center gap-2">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        <span>Scanning for proactive network changes...</span>
      </div>
    )
  }

  const active = selectedPulse || effectivePulses[0]

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-200 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-indigo-600 animate-pulse" />
          <div>
            <h3 className="text-sm font-bold text-neutral-900">Network Pulse Queue</h3>
            <p className="text-[11px] text-neutral-500">
              Proactive structural change intelligence, evidence assessment &amp; operational early warnings
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-100 text-indigo-800 border border-indigo-200">
            {effectivePulses.length} Active Pulse{effectivePulses.length === 1 ? '' : 's'}
          </span>
          <button
            onClick={() => void refetch()}
            className="p-1.5 text-neutral-500 hover:text-neutral-700 hover:bg-neutral-100 rounded-md transition cursor-pointer"
            title="Refresh network pulses"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {effectivePulses.length === 0 ? (
        <div className="text-center py-6 text-xs text-neutral-500">
          No active network pulses detected in the current window.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Pulses list */}
          <div className="space-y-2 lg:col-span-1 border-r border-neutral-100 pr-0 lg:pr-3">
            {effectivePulses.map((p) => {
              const isSelected = active?.pulse_id === p.pulse_id
              const isCrit = p.review_priority === 'CRITICAL_REVIEW'
              return (
                <div
                  key={p.pulse_id}
                  onClick={() => setSelectedPulse(p)}
                  className={`p-3 rounded-lg border cursor-pointer transition text-left space-y-1.5 ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-50/60 shadow-2xs'
                      : 'border-neutral-200 bg-neutral-50/50 hover:bg-neutral-100/70'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] font-bold text-neutral-600">
                      {p.pulse_id}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        isCrit
                          ? 'bg-rose-100 text-rose-800 border border-rose-200'
                          : 'bg-amber-100 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {p.review_priority.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-neutral-900 line-clamp-1">
                    {p.signal_headline}
                  </p>
                  <div className="flex items-center justify-between text-[11px] text-neutral-500">
                    <span>Evidence: {p.evidence_refs.length} records</span>
                    <span className="text-emerald-700 font-medium">
                      Support: {Math.round(p.support_level * 100)}%
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Active pulse detail */}
          {active && (
            <div className="lg:col-span-2 space-y-3.5">
              {/* Pulse Summary Banner */}
              <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-neutral-900 flex items-center gap-1.5">
                    <ShieldCheck className="h-4 w-4 text-emerald-600" />
                    <span>{active.signal_headline}</span>
                  </h4>
                  <span className="text-[11px] font-semibold text-neutral-500">
                    Action Window: <strong className="text-neutral-800">{active.action_window}</strong>
                  </span>
                </div>
                <p className="text-[11px] text-neutral-600">
                  Affected Entities: {active.affected_entities.join(', ')} | Affected Cases: {active.affected_cases.join(', ')}
                </p>

                {/* Primary Action Buttons */}
                <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-neutral-200/60">
                  {active.affected_entities.length > 0 && (
                    <Link
                      to={`/network?node_id=${encodeURIComponent(active.affected_entities[0])}`}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-[11px] transition shadow-2xs cursor-pointer"
                    >
                      <Network className="h-3 w-3" />
                      Inspect Network
                    </Link>
                  )}
                  <Link
                    to="/timeline"
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white hover:bg-neutral-50 text-neutral-700 border border-neutral-200 font-bold text-[11px] transition shadow-2xs cursor-pointer"
                  >
                    <Clock className="h-3 w-3" />
                    View Timeline
                  </Link>
                  {active.affected_cases.length > 0 && (
                    <Link
                      to={`/cases/${encodeURIComponent(active.affected_cases[0])}`}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white hover:bg-neutral-50 text-neutral-700 border border-neutral-200 font-bold text-[11px] transition shadow-2xs cursor-pointer"
                    >
                      <ExternalLink className="h-3 w-3" />
                      Open Case ({active.affected_cases[0]})
                    </Link>
                  )}
                </div>
              </div>

              {/* Expandable "Why This Appeared" grounded section */}
              <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden text-xs">
                <button
                  onClick={() => setIsWhyExpanded(!isWhyExpanded)}
                  className="w-full flex items-center justify-between p-2.5 bg-neutral-50 hover:bg-neutral-100 transition text-left cursor-pointer font-bold text-neutral-800"
                >
                  <span className="flex items-center gap-1.5">
                    <HelpCircle className="h-3.5 w-3.5 text-indigo-600" />
                    Why this appeared (Deterministic Signal Grounding)
                  </span>
                  {isWhyExpanded ? <ChevronUp className="h-4 w-4 text-neutral-500" /> : <ChevronDown className="h-4 w-4 text-neutral-500" />}
                </button>
                {isWhyExpanded && (
                  <div className="p-3 space-y-2 border-t border-neutral-200 bg-indigo-50/20">
                    <p className="text-[11px] text-neutral-700 leading-relaxed">
                      {active.signal_headline}. This pulse was triggered deterministically because structural network analysis detected shifts across {active.affected_entities.length} monitored entities and {active.affected_cases.length} intersecting criminal investigations.
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px] text-neutral-600 pt-1">
                      <div className="p-2 rounded bg-white border border-neutral-200 space-y-0.5">
                        <div className="font-bold text-neutral-800">Graph Trigger Scope:</div>
                        <div>Priority level: <strong>{active.review_priority.replace('_', ' ')}</strong></div>
                        <div>Supporting records: <strong>{active.evidence_refs.length} provenance items</strong></div>
                      </div>
                      <div className="p-2 rounded bg-white border border-neutral-200 space-y-0.5">
                        <div className="font-bold text-neutral-800">Evidence Baseline:</div>
                        <div>Assessed claims: <strong>{active.assessment.length} verifiable points</strong></div>
                        <div>Support level: <strong>{Math.round(active.support_level * 100)}% grounding</strong></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Evidence Assessment (SUPPORTS, CONFLICTS, MISSING) */}
              <div className="space-y-1.5">
                <h5 className="text-[11px] font-bold uppercase tracking-wider text-neutral-500">
                  Evidence Assessment ({active.assessment.length} claims verified)
                </h5>
                <div className="space-y-1.5">
                  {active.assessment.map((a) => {
                    let badgeBg = 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    if (a.state === 'MISSING') badgeBg = 'bg-amber-100 text-amber-800 border-amber-300'
                    if (a.state === 'CONFLICTS') badgeBg = 'bg-rose-100 text-rose-800 border-rose-300'
                    return (
                      <div
                        key={a.claim_id}
                        className="p-2 bg-white border border-neutral-200 rounded-md text-xs flex items-start gap-2"
                      >
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${badgeBg}`}>
                          {a.state}
                        </span>
                        <div className="flex-1 space-y-0.5">
                          <p className="text-neutral-800 text-[11px]">{a.rationale}</p>
                          <div className="text-[10px] text-neutral-500 flex gap-3">
                            <span>Ref: {a.evidence_ref}</span>
                            <span>Source Quality: {Math.round(a.source_quality * 100)}%</span>
                            <span>Freshness: {a.freshness_days}d</span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Operational Early Warning */}
              {active.forecast && (
                <div className="p-3 bg-indigo-50/50 rounded-lg border border-indigo-200 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-950 flex items-center gap-1.5">
                      <AlertTriangle className="h-3.5 w-3.5 text-indigo-600" />
                      Operational Early Warning: {active.forecast.target_state}
                    </span>
                    {active.forecast.abstained ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                        ABSTAINED (Insufficient Evidence)
                      </span>
                    ) : (
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300 inline-flex items-center gap-1 cursor-help"
                        title="Proportion of required evidence claims currently supported by available records within this pulse scope."
                      >
                        Evidence support: {Math.round(active.forecast.support_level * 100)}%
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-neutral-700">
                    {active.forecast.abstained
                      ? active.forecast.abstention_reason
                      : active.forecast.suggested_verification}
                  </p>
                </div>
              )}

              {/* Next Best Verification Actions */}
              {active.verification_plan.length > 0 && (
                <div className="space-y-1.5">
                  <h5 className="text-[11px] font-bold uppercase tracking-wider text-neutral-500">
                    Next Best Verification Planner (Investigator Actions)
                  </h5>
                  <div className="space-y-1">
                    {active.verification_plan.map((v) => (
                      <div
                        key={v.verification_id}
                        className="p-2 bg-neutral-50 border border-neutral-200 rounded-md text-xs flex items-center justify-between gap-2"
                      >
                        <div className="space-y-0.5">
                          <p className="font-semibold text-neutral-900 text-[11px]">
                            {v.recommended_action}
                          </p>
                          <p className="text-[10px] text-neutral-500">
                            Target: {v.target_claim} | Missing Evidence: {v.missing_evidence_type} | Role: {v.responsible_role}
                          </p>
                        </div>
                        <span className="px-2 py-1 bg-white border border-neutral-300 rounded text-[10px] font-semibold text-neutral-700">
                          {v.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
