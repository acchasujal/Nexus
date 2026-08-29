/**
 * frontend/src/components/nexus/HotspotDrilldownModal.tsx
 *
 * Interactive drill-down modal for Crime Hotspots: allows investigators
 * to inspect underlying cases, accused entities, repeat offenders,
 * cross-case connections, and backing forensic evidence.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  X, AlertTriangle, FileText, Users, Network, ShieldCheck,
  ExternalLink, ChevronRight, MapPin, Calendar, Hash
} from 'lucide-react'
import { useHotspotDrilldown } from '@/hooks/useNexus'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'

interface HotspotDrilldownModalProps {
  district: string | null
  onClose: () => void
  onOpenEvidence?: (evidenceId: string) => void
}

type DrilldownTab = 'cases' | 'entities' | 'offenders' | 'links' | 'evidence'

export function HotspotDrilldownModal({
  district,
  onClose,
  onOpenEvidence,
}: HotspotDrilldownModalProps) {
  const [activeTab, setActiveTab] = useState<DrilldownTab>('cases')
  const { data: drilldown, isLoading, error } = useHotspotDrilldown(district)

  if (!district) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drilldown-title"
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose()
      }}
    >
      <div className="relative flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-neutral-200 bg-white shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-neutral-200 bg-neutral-50 px-6 py-5">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-900 border border-red-200">
                <AlertTriangle className="h-3.5 w-3.5 text-red-600" />
                RED FLAG HOTSPOT
              </span>
              <h2 id="drilldown-title" className="text-xl font-bold text-neutral-900">
                District: {district}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-600">
              <span>
                <strong>Cases:</strong> {drilldown?.case_count ?? '...'} registered
              </span>
              <span>•</span>
              <span>
                <strong>Crime Concentration:</strong>{' '}
                <span className="font-bold text-red-800 bg-red-50 px-1.5 py-0.5 rounded border border-red-200">
                  {drilldown?.concentration_multiplier ?? '...'}× baseline
                </span>{' '}
                (baseline: {drilldown?.baseline_cases ?? '...'} cases/dist)
              </span>
              <span>•</span>
              <span className="text-emerald-800 font-bold flex items-center gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                Evidence-Backed
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700 transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-neutral-200 bg-white px-6">
          <button
            onClick={() => setActiveTab('cases')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-bold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'cases'
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <FileText className="h-4 w-4" />
            Underlying Cases ({drilldown?.cases.length ?? 0})
          </button>
          <button
            onClick={() => setActiveTab('entities')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-bold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'entities'
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <Users className="h-4 w-4" />
            Accused &amp; Entities ({drilldown?.entities.length ?? 0})
          </button>
          <button
            onClick={() => setActiveTab('offenders')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-bold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'offenders'
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            Repeat Offenders ({drilldown?.repeat_offenders.length ?? 0})
          </button>
          <button
            onClick={() => setActiveTab('links')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-bold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'links'
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <Network className="h-4 w-4 text-purple-600" />
            Cross-Case Links ({drilldown?.cross_case_links.length ?? 0})
          </button>
          <button
            onClick={() => setActiveTab('evidence')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-bold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'evidence'
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            Forensic Evidence ({drilldown?.evidence.length ?? 0})
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <LoadingSkeleton layout="detail" />
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
              Failed to load district drilldown details.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Tab 1: Cases */}
              {activeTab === 'cases' && (
                <div className="space-y-3">
                  {drilldown?.cases.length === 0 ? (
                    <p className="text-xs text-neutral-500">No cases recorded in this district.</p>
                  ) : (
                    drilldown?.cases.map((c) => (
                      <div
                        key={c.case_id}
                        className="flex items-center justify-between p-3.5 rounded-xl border border-neutral-200 bg-neutral-50 hover:bg-neutral-100 transition-colors shadow-2xs"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                              {c.fir_number}
                            </span>
                            <span className="text-xs font-bold text-neutral-900">{c.title}</span>
                            <span className="text-[11px] font-bold text-neutral-600 bg-neutral-200/80 px-2 py-0.5 rounded-full">
                              {c.crime_head}
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-3 text-[11px] text-neutral-600">
                            {c.date && (
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3 text-neutral-400" />
                                {c.date.slice(0, 10)}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3 text-neutral-400" />
                              {c.police_station}
                            </span>
                            {c.sections.length > 0 && (
                              <span>
                                Sections: <code className="font-mono text-neutral-900">{c.sections.join(', ')}</code>
                              </span>
                            )}
                            <span>{c.accused_count} Accused Listed</span>
                          </div>
                        </div>

                        <Link
                          to={`/cases/${c.case_id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 transition-colors cursor-pointer shrink-0"
                        >
                          View Case
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Tab 2: Entities */}
              {activeTab === 'entities' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {drilldown?.entities.length === 0 ? (
                    <p className="text-xs text-neutral-500">No entities listed in this district.</p>
                  ) : (
                    drilldown?.entities.map((e) => (
                      <div
                        key={e.entity_id}
                        className="p-3 rounded-xl border border-neutral-200 bg-neutral-50 space-y-1 shadow-2xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-neutral-900">{e.name}</span>
                          <span className="text-[11px] font-bold text-neutral-700 bg-neutral-200 px-2 py-0.5 rounded">
                            {e.entity_type}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-neutral-600">
                          <span>Role: {e.role}</span>
                          <span>Appears in {e.case_count} case(s)</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Tab 3: Repeat Offenders */}
              {activeTab === 'offenders' && (
                <div className="space-y-3">
                  {drilldown?.repeat_offenders.length === 0 ? (
                    <p className="text-xs text-neutral-500">No multi-case repeat offenders active in this district.</p>
                  ) : (
                    drilldown?.repeat_offenders.map((off, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl border border-amber-200 bg-amber-50/50 space-y-2 shadow-2xs"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-sm font-bold text-neutral-900">{off.canonical_name}</span>
                            {off.aliases && off.aliases.length > 0 && (
                              <span className="ml-2 text-xs text-neutral-600">
                                (Aliases: {off.aliases.join(', ')})
                              </span>
                            )}
                          </div>
                          <span className="text-xs font-bold text-red-900 bg-red-100 px-2.5 py-1 rounded-full border border-red-200">
                            {off.case_count} Total Cases
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-700">
                          <span>
                            <strong>Districts:</strong> {off.districts?.join(', ')}
                          </span>
                          <span>•</span>
                          <span>
                            <strong>FIRs:</strong> {off.fir_numbers?.join(', ')}
                          </span>
                        </div>

                        <div className="text-[11px] text-neutral-600 bg-white/80 p-2.5 rounded-lg border border-neutral-200">
                          {off.why_surfaced}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Tab 4: Cross-Case Links */}
              {activeTab === 'links' && (
                <div className="space-y-2.5">
                  {drilldown?.cross_case_links.length === 0 ? (
                    <p className="text-xs text-neutral-500">No external cross-case relationship links detected.</p>
                  ) : (
                    drilldown?.cross_case_links.map((link, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 rounded-lg border border-neutral-200 bg-neutral-50 text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <code className="font-mono text-neutral-900 font-bold">{link.source_id}</code>
                          <span className="text-purple-800 font-bold bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                            {link.edge_type}
                          </span>
                          <code className="font-mono text-neutral-900 font-bold">{link.target_id}</code>
                        </div>
                        <span className="text-[11px] text-neutral-500">
                          Cases: {(link.case_ids || []).join(', ')}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Tab 5: Evidence */}
              {activeTab === 'evidence' && (
                <div className="space-y-2.5">
                  {drilldown?.evidence.length === 0 ? (
                    <p className="text-xs text-neutral-500">No evidence items registered for this district.</p>
                  ) : (
                    drilldown?.evidence.map((ev, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 rounded-lg border border-neutral-200 bg-neutral-50 text-xs"
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-emerald-900 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                              {ev.evidence_id}
                            </span>
                            <span className="font-bold text-neutral-800">{ev.source_type}</span>
                          </div>
                          <p className="text-neutral-600">{ev.description}</p>
                        </div>

                        {onOpenEvidence && (
                          <button
                            onClick={() => onOpenEvidence(ev.evidence_id)}
                            className="px-2.5 py-1 text-xs font-bold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-md transition-colors cursor-pointer"
                          >
                            Inspect
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-neutral-200 bg-neutral-50 px-6 py-4">
          <div className="text-xs text-neutral-500 flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4 text-blue-600" />
            <span>Deterministic graph facts only. Non-predictive investigative baseline.</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white font-bold text-xs transition-colors cursor-pointer"
          >
            Close Drilldown
          </button>
        </div>
      </div>
    </div>
  )
}
