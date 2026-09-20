/**
 * frontend/src/components/nexus/CaseDNASection.tsx
 *
 * P2: Case DNA (Explainable Multi-Dimensional Structural Similarity Engine).
 * Displays explainable 5-vector topological similarity between criminal cases:
 *   1. Structure Similarity (Accused entity overlap + legal sections)
 *   2. Communication Similarity (Shared phone clusters & CDR burst overlap)
 *   3. Financial Similarity (Mule accounts, hawala layering, peeling chains)
 *   4. Location Similarity (District and police station spatial alignment)
 *   5. Temporal Similarity (Modus operandi time-window proximity)
 *
 * Strict Compliance:
 *   - Zero Predictive Guilt: strictly structural modus operandi & graph topology comparison.
 *   - Transparent Section 63 BSA evidence provenance references.
 */

import { useState } from 'react'
import {
  Dna,
  GitCompare,
  Layers,
  Phone,
  CreditCard,
  MapPin,
  Clock,
  ShieldCheck,
  ExternalLink,
  ChevronRight,
  Info,
  Search,
} from 'lucide-react'
import { useCaseDNA } from '@/hooks/useNexus'
import { MetricCard } from '@/components/ui/MetricCard'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import type { CaseDNA } from '@shared/contracts/api'

interface CaseDNASectionProps {
  initialCaseId?: string
}

export function CaseDNASection({ initialCaseId = 'CASE-141' }: CaseDNASectionProps) {
  const [selectedCaseId, setSelectedCaseId] = useState<string>(initialCaseId)
  const [searchInput, setSearchInput] = useState<string>(initialCaseId)
  const [selectedMatch, setSelectedMatch] = useState<CaseDNA | null>(null)

  const {
    data: caseDNAData,
    isLoading,
    error,
    refetch,
  } = useCaseDNA(selectedCaseId, 10)

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchInput.trim()) {
      setSelectedCaseId(searchInput.trim())
      setSelectedMatch(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Explanation */}
      <div className="bg-gradient-to-r from-indigo-900/10 via-sky-900/5 to-transparent border border-indigo-200/50 rounded-xl p-5">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-indigo-600 text-white rounded-lg shadow-sm">
            <Dna className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-900">Case DNA: Explainable Structural Similarity</h2>
              <span className="px-2.5 py-0.5 text-xs font-medium bg-indigo-100 text-indigo-800 rounded-full border border-indigo-200">
                Structural Similarity Engine
              </span>
              <span className="px-2.5 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-800 rounded-full border border-emerald-200">
                Zero Predictive Guilt
              </span>
            </div>
            <p className="text-sm text-slate-600 mt-1 max-w-4xl leading-relaxed">
              Computes deterministic 5-vector graph topological fingerprints across criminal networks. Rather than predicting guilt or recidivism, Case DNA uncovers shared modus operandi, communication convergence, financial peeling chains, and jurisdiction patterns with complete Section 63 BSA evidence citations.
            </p>
          </div>
        </div>

        {/* Case Selector / Search Bar */}
        <form onSubmit={handleSearchSubmit} className="mt-4 flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Enter Case ID (e.g. CASE-141, CASE-207)..."
              className="w-full pl-9 pr-4 py-2 text-sm text-slate-900 placeholder:text-slate-500 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            <GitCompare className="w-4 h-4" />
            Compute DNA Profile
          </button>
          <div className="flex items-center gap-1.5 ml-2">
            <span className="text-xs text-slate-500">Quick Test:</span>
            {['CASE-141', 'CASE-207', 'CASE-305'].map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => {
                  setSearchInput(id)
                  setSelectedCaseId(id)
                  setSelectedMatch(null)
                }}
                className={`px-2 py-1 text-xs rounded border transition-colors ${
                  selectedCaseId === id
                    ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-semibold'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                {id}
              </button>
            ))}
          </div>
        </form>
      </div>

      {/* Loading & Error States */}
      {isLoading && <LoadingSkeleton count={3} height="h-28" />}
      {error && <ErrorState title="Failed to load Case DNA profile" error={error} onRetry={refetch} />}

      {/* Metrics Row */}
      {caseDNAData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard
            label="Target Investigation"
            value={caseDNAData.target_case_id}
            subtext={`${caseDNAData.similar_cases.length} related cases identified`}
            icon={Dna}
          />
          <MetricCard
            label="Highest Structural Similarity"
            value={`${(caseDNAData.highest_similarity * 100).toFixed(1)}%`}
            subtext="Closest structural match"
            icon={GitCompare}
          />
          <MetricCard
            label="Average Cluster Overlap"
            value={`${(caseDNAData.average_similarity * 100).toFixed(1)}%`}
            subtext="Cross-dimension average"
            icon={Layers}
          />
          <MetricCard
            label="Shared High-Value Entities"
            value={caseDNAData.top_shared_entities.length}
            subtext="Accused, phones & jurisdictions"
            icon={ShieldCheck}
          />
        </div>
      )}


      {/* Main Content: Match List & Vector Breakdown */}
      {caseDNAData && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Matches List (Left Column) */}
          <div className="lg:col-span-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700 flex items-center justify-between">
              <span>Top Structural Matches</span>
              <span className="text-xs text-slate-500 font-normal">Ranked by 5-Vector Score</span>
            </h3>

            {caseDNAData.similar_cases.length === 0 ? (
              <div className="p-8 text-center bg-white border border-slate-200 rounded-xl">
                <Info className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <p className="text-sm text-slate-600 font-medium">No matching cases above threshold</p>
                <p className="text-xs text-slate-400 mt-1">This investigation currently exhibits unique topological indicators.</p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {caseDNAData.similar_cases.map((match, idx) => {
                  const isSelected = selectedMatch ? selectedMatch.case_pair[1] === match.case_pair[1] : idx === 0
                  const otherCaseId = match.case_pair[1]

                  return (
                    <div
                      key={otherCaseId}
                      data-testid={`match-card-${otherCaseId}`}
                      onClick={() => setSelectedMatch(match)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-indigo-50/70 border-indigo-400 shadow-sm'
                          : 'bg-white border-slate-200 hover:border-slate-300'
                      }`}
                    >

                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-bold text-slate-700">{otherCaseId}</span>
                            <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md font-medium">
                              {match.case_b_title}
                            </span>
                          </div>
                          <p className="text-xs text-slate-600 mt-1 line-clamp-1">{match.explanation}</p>
                        </div>
                        <div className="text-right">
                          <span className="text-base font-bold text-indigo-700">
                            {(match.overall_similarity * 100).toFixed(0)}%
                          </span>
                          <span className="block text-[10px] text-slate-400">Match</span>
                        </div>
                      </div>

                      {/* Mini vector indicators */}
                      <div className="mt-3 grid grid-cols-5 gap-1.5 pt-2 border-t border-slate-100">
                        <div className="text-center">
                          <span className="text-[10px] text-slate-400 block">Struct</span>
                          <span className="text-xs font-semibold text-slate-700">
                            {(match.structure_similarity * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="text-center">
                          <span className="text-[10px] text-slate-400 block">Comm</span>
                          <span className="text-xs font-semibold text-slate-700">
                            {(match.communication_similarity * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="text-center">
                          <span className="text-[10px] text-slate-400 block">Fin</span>
                          <span className="text-xs font-semibold text-slate-700">
                            {(match.financial_similarity * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="text-center">
                          <span className="text-[10px] text-slate-400 block">Loc</span>
                          <span className="text-xs font-semibold text-slate-700">
                            {(match.location_similarity * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="text-center">
                          <span className="text-[10px] text-slate-400 block">Temp</span>
                          <span className="text-xs font-semibold text-slate-700">
                            {(match.temporal_similarity * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Detailed 5-Vector Radar Breakdown (Right Column) */}
          <div className="lg:col-span-7">
            {(() => {
              const active = selectedMatch || caseDNAData.similar_cases[0]
              if (!active) {
                return (
                  <div className="p-12 text-center bg-white border border-slate-200 rounded-xl">
                    <p className="text-sm text-slate-500">Select a case match to inspect its 5-vector DNA profile.</p>
                  </div>
                )
              }

              return (
                <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
                  {/* Pair Header */}
                  <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-base font-bold text-slate-900">
                          {active.case_pair[0]} ↔ {active.case_pair[1]}
                        </h4>
                        <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 text-xs font-medium rounded">
                          {active.derivation_class}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {active.case_a_title} vs. {active.case_b_title}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-black text-indigo-600">
                        {(active.overall_similarity * 100).toFixed(1)}%
                      </div>
                      <span className="text-xs text-slate-500">Overall Case DNA</span>
                    </div>
                  </div>

                  {/* 5-Vector Detailed Breakdown */}
                  <div className="space-y-4">
                    <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      5-Vector Topological Breakdown
                    </h5>

                    {/* 1. Structure */}
                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="flex items-center gap-1.5 text-slate-700">
                          <Layers className="w-3.5 h-3.5 text-indigo-500" />
                          Structure & Network Topology (Weight: 30%)
                        </span>
                        <span className="font-semibold text-slate-900">
                          {(active.structure_similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div
                          className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, active.structure_similarity * 100)}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-slate-500 block mt-0.5">
                        Accused degree distribution, legal sections (BNS/SLL), and modular community overlap.
                      </span>
                    </div>

                    {/* 2. Communication */}
                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="flex items-center gap-1.5 text-slate-700">
                          <Phone className="w-3.5 h-3.5 text-sky-500" />
                          Communication & CDR Overlap (Weight: 25%)
                        </span>
                        <span className="font-semibold text-slate-900">
                          {(active.communication_similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div
                          className="bg-sky-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, active.communication_similarity * 100)}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-slate-500 block mt-0.5">
                        Co-occurring MSISDNs, CDR burst clusters, and telecom tower handovers.
                      </span>
                    </div>

                    {/* 3. Financial */}
                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="flex items-center gap-1.5 text-slate-700">
                          <CreditCard className="w-3.5 h-3.5 text-amber-500" />
                          Financial Flow & Mule Routing (Weight: 20%)
                        </span>
                        <span className="font-semibold text-slate-900">
                          {(active.financial_similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div
                          className="bg-amber-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, active.financial_similarity * 100)}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-slate-500 block mt-0.5">
                        Hawala smurfing patterns, peeling chain velocity, and shared beneficiary bank accounts.
                      </span>
                    </div>

                    {/* 4. Location */}
                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="flex items-center gap-1.5 text-slate-700">
                          <MapPin className="w-3.5 h-3.5 text-emerald-500" />
                          Jurisdiction & Spatial Convergence (Weight: 15%)
                        </span>
                        <span className="font-semibold text-slate-900">
                          {(active.location_similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div
                          className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, active.location_similarity * 100)}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-slate-500 block mt-0.5">
                        Police station proximity and cross-district boundary corridors.
                      </span>
                    </div>

                    {/* 5. Temporal */}
                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="flex items-center gap-1.5 text-slate-700">
                          <Clock className="w-3.5 h-3.5 text-purple-500" />
                          Temporal Proximity & Cadence (Weight: 10%)
                        </span>
                        <span className="font-semibold text-slate-900">
                          {(active.temporal_similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div
                          className="bg-purple-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, active.temporal_similarity * 100)}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-slate-500 block mt-0.5">
                        Incident registration window decay (60-day operational synchronization).
                      </span>
                    </div>
                  </div>

                  {/* Shared Entities Tag Cloud */}
                  {active.shared_entities.length > 0 && (
                    <div className="pt-4 border-t border-slate-100">
                      <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                        Intersecting Network Entities
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {active.shared_entities.map((ent, i) => (
                          <span
                            key={i}
                            className="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md font-medium flex items-center gap-1 transition-colors"
                          >
                            <ShieldCheck className="w-3 h-3 text-indigo-500" />
                            {ent}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Section 63 BSA Evidence Citations */}
                  <div className="pt-4 border-t border-slate-100 bg-slate-50/50 -mx-6 -mb-6 p-6 rounded-b-xl">
                    <h5 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-2 flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      Section 63 BSA Evidence Provenance
                    </h5>
                    <div className="flex flex-wrap gap-2">
                      {active.evidence_refs.map((ref, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 text-xs font-mono bg-white border border-slate-300 text-slate-800 rounded shadow-xs"
                        >
                          {ref}
                        </span>
                      ))}
                    </div>
                    <p className="text-[11px] text-slate-500 mt-2">
                      All similarity weights are derived strictly from cryptographically hashed primary forensic source records.
                    </p>
                  </div>
                </div>
              )
            })()}
          </div>
        </div>
      )}
    </div>
  )
}
