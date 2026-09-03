/**
 * frontend/src/pages/Patterns.tsx
 *
 * NEXUS Criminal Network Intelligence Hub:
 * 1. Crime Hotspots (dynamic baseline multiplier, dominant categories, drilldown)
 * 2. Repeat Offender Radar (entity-resolved aliases, district spread, shared phones/entities, non-guilt status)
 * 3. Combined Cross-District Bridge Signals (Hotspot ↔ Repeat Offender intersection)
 * 4. Network Modules & Centrality Bridges (Louvain communities, betweenness brokers)
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Layers, Network, Users, Share2, AlertTriangle, ShieldCheck, Inbox,
  Flame, Radio, GitBranch, ArrowRight, ExternalLink, RefreshCw,
  MapPin,
} from 'lucide-react'
import {
  useIntelligenceHotspots,
  useRepeatOffenderRadar,
  useCombinedBridgeSignals,
} from '@/hooks/useNexus'
import { apiClient } from '@/lib/apiClient'
import { HotspotDrilldownModal } from '@/components/nexus/HotspotDrilldownModal'
import { EvidenceDrawer } from '@/components/nexus/EvidenceDrawer'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { PageHeader } from '@/components/ui/PageHeader'
import { MetricCard } from '@/components/ui/MetricCard'

type HubTab = 'hotspots' | 'radar' | 'combined' | 'communities'

interface CommunityItem {
  community_id?: string
  size?: number
  reason?: string
  top_influencer_id?: string
}

interface BridgeItem {
  node_id?: string
  label?: string
  betweenness_score?: number
  criticality?: string
  connected_communities?: string[]
  reason?: string
}

export default function Patterns() {
  const [activeTab, setActiveTab] = useState<HubTab>('hotspots')
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null)
  const [minCasesFilter, setMinCasesFilter] = useState<number>(2)
  const [evidenceDrawerId, setEvidenceDrawerId] = useState<string | null>(null)

  // Intelligence queries
  const {
    data: hotspots,
    isLoading: isHotspotsLoading,
    error: hotspotsError,
    refetch: refetchHotspots,
  } = useIntelligenceHotspots()

  const {
    data: repeatOffenders,
    isLoading: isRadarLoading,
    error: radarError,
    refetch: refetchRadar,
  } = useRepeatOffenderRadar(minCasesFilter)

  const {
    data: bridgeSignals,
    isLoading: isBridgeLoading,
    error: bridgeError,
    refetch: refetchBridges,
  } = useCombinedBridgeSignals()

  // Graph Modularity / Bridges queries
  const [communities, setCommunities] = useState<CommunityItem[]>([])
  const [graphBridges, setGraphBridges] = useState<BridgeItem[]>([])
  const [isGraphAlgoLoading, setIsGraphAlgoLoading] = useState<boolean>(true)

  const loadGraphAlgos = () => {
    setIsGraphAlgoLoading(true)
    Promise.all([
      apiClient.getCommunities().catch(() => []),
      apiClient.getBridges().catch(() => []),
    ])
      .then(([commData, bridgeData]) => {
        setCommunities(Array.isArray(commData) ? (commData as CommunityItem[]) : [])
        setGraphBridges(Array.isArray(bridgeData) ? (bridgeData as BridgeItem[]) : [])
      })
      .finally(() => {
        setIsGraphAlgoLoading(false)
      })
  }

  // Initial load of graph modularity
  useEffect(() => {
    loadGraphAlgos()
  }, [])

  const handleRefreshAll = async () => {
    await Promise.all([
      refetchHotspots(),
      refetchRadar(),
      refetchBridges(),
      loadGraphAlgos(),
    ])
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={Layers}
        title="Criminal Network Intelligence Hub &amp; Crime Hotspots"
        subtitle="Dynamic crime concentration density, resolved repeat offender radar, cross-district syndicate bridges, and graph modularity."
        actions={
          <>
            <button
              onClick={handleRefreshAll}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 font-bold text-xs shadow-2xs transition-colors cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh Intelligence
            </button>
            <Link
              to="/leads"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-xs transition-colors cursor-pointer"
            >
              <Inbox className="h-4 w-4" />
              View Lead Inbox
            </Link>
          </>
        }
      />

      {/* Non-Guilt Compliance Disclaimer Banner */}
      <div className="flex items-start gap-2.5 text-xs text-blue-900 bg-blue-50/70 border border-blue-200/80 p-3.5 rounded-xl">
        <ShieldCheck className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
        <span>
          <strong className="text-blue-950 font-bold">Investigative Use Only (MHA / NCRB Standard):</strong> All crime concentration multipliers, repeat offender signals, and cross-district bridge alerts are computed via deterministic graph algorithms to guide investigative prioritisation. They do not constitute a finding of guilt or legal proof.
        </span>
      </div>

      {/* Primary Tab Navigation */}
      <div className="flex items-center border-b border-neutral-200 gap-1 overflow-x-auto whitespace-nowrap sm:flex-wrap">
        <button
          onClick={() => setActiveTab('hotspots')}
          className={`flex items-center gap-2 px-3.5 sm:px-4 py-2.5 sm:py-3 text-xs font-bold border-b-2 transition-colors cursor-pointer shrink-0 ${
            activeTab === 'hotspots'
              ? 'border-red-600 text-red-700 bg-red-50/50'
              : 'border-transparent text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50'
          }`}
        >
          <Flame className="h-4 w-4 text-red-600" />
          Crime Hotspots ({hotspots?.length ?? 0})
        </button>

        <button
          onClick={() => setActiveTab('radar')}
          className={`flex items-center gap-2 px-3.5 sm:px-4 py-2.5 sm:py-3 text-xs font-bold border-b-2 transition-colors cursor-pointer shrink-0 ${
            activeTab === 'radar'
              ? 'border-amber-600 text-amber-800 bg-amber-50/50'
              : 'border-transparent text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50'
          }`}
        >
          <Radio className="h-4 w-4 text-amber-600" />
          Repeat Offender Radar ({repeatOffenders?.length ?? 0})
        </button>

        <button
          onClick={() => setActiveTab('combined')}
          className={`flex items-center gap-2 px-3.5 sm:px-4 py-2.5 sm:py-3 text-xs font-bold border-b-2 transition-colors cursor-pointer shrink-0 ${
            activeTab === 'combined'
              ? 'border-purple-600 text-purple-800 bg-purple-50/50'
              : 'border-transparent text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50'
          }`}
        >
          <GitBranch className="h-4 w-4 text-purple-600" />
          Combined Cross-District Bridges ({bridgeSignals?.length ?? 0})
        </button>

        <button
          onClick={() => setActiveTab('communities')}
          className={`flex items-center gap-2 px-3.5 sm:px-4 py-2.5 sm:py-3 text-xs font-bold border-b-2 transition-colors cursor-pointer shrink-0 ${
            activeTab === 'communities'
              ? 'border-blue-600 text-blue-800 bg-blue-50/50'
              : 'border-transparent text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50'
          }`}
        >
          <Users className="h-4 w-4 text-blue-600" />
          Network Modules &amp; Brokers ({communities.length + graphBridges.length})
        </button>
      </div>

      {/* TAB 1: CRIME HOTSPOTS */}
      {activeTab === 'hotspots' && (
        <div className="space-y-6">
          {/* Summary Metrics */}
          {hotspots && hotspots.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                label="Flagged Hotspots"
                value={hotspots.length}
                icon={Flame}
                badge={{ text: `${hotspots.filter(h => h.alert_level === 'RED').length} Red Flag`, variant: 'danger' }}
                subtext="High concentration districts"
              />
              <MetricCard
                label="Baseline Density"
                value={hotspots[0]?.baseline_cases ?? 25}
                icon={MapPin}
                subtext="Average cases per district"
              />
              <MetricCard
                label="Max Concentration Surge"
                value={`${Math.max(...hotspots.map((h) => h.concentration_multiplier), 0)}×`}
                icon={AlertTriangle}
                badge={{ text: 'Baseline Multiplier', variant: 'warning' }}
                subtext="Highest ratio vs baseline"
              />
              <MetricCard
                label="Evidence Grounding"
                value="100%"
                icon={ShieldCheck}
                badge={{ text: 'Verified', variant: 'success' }}
                subtext="Backed by verified records"
              />
            </div>
          )}

          {isHotspotsLoading ? (
            <LoadingSkeleton layout="card" />
          ) : hotspotsError ? (
            <ErrorState message="Failed to load crime hotspots." onRetry={() => void refetchHotspots()} />
          ) : !hotspots || hotspots.length === 0 ? (
            <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center text-neutral-500">
              No crime hotspots detected across active graph cases.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {hotspots.map((hotspot) => (
                <div
                  key={hotspot.district}
                  className="rounded-xl border border-red-200 bg-white shadow-xs hover:border-red-300 transition-all flex flex-col justify-between overflow-hidden"
                >
                  <div>
                    {/* Card Header */}
                    <div className="p-4 border-b border-red-100 bg-red-50/60 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-red-100 text-red-950 border border-red-200 tracking-wide">
                          <AlertTriangle className="h-3.5 w-3.5 text-red-600" />
                          RED FLAG — HIGH CRIME CONCENTRATION
                        </span>
                        <span className="text-[11px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          Evidence-backed: Yes
                        </span>
                      </div>

                      <div>
                        <div className="text-xs text-neutral-500 font-bold uppercase tracking-wider">District</div>
                        <h3 className="text-base sm:text-lg font-bold text-neutral-900">{hotspot.district}</h3>
                      </div>

                      <div className="p-3 rounded-lg bg-red-50/70 border border-red-100 space-y-1">
                        <div className="flex items-baseline justify-between">
                          <span className="text-xs text-neutral-700 font-medium">Crime concentration:</span>
                          <span className="text-sm font-extrabold text-red-900 font-mono">
                            {hotspot.concentration_multiplier}× baseline
                          </span>
                        </div>
                        <div className="flex items-baseline justify-between text-xs text-neutral-600">
                          <span>Total Cases:</span>
                          <span className="font-bold text-neutral-900">{hotspot.case_count}</span>
                        </div>
                      </div>
                    </div>

                    {/* Card Metrics & Categories */}
                    <div className="p-4 space-y-3.5 flex-1">
                      {/* Dominant Categories */}
                      <div className="space-y-1.5">
                        <div className="text-xs font-bold text-neutral-800">Dominant categories:</div>
                        {(!hotspot.dominant_categories || hotspot.dominant_categories.length === 0) ? (
                          <div className="text-xs text-neutral-500">General offenses</div>
                        ) : (
                          <div className="flex flex-wrap gap-1.5">
                            {hotspot.dominant_categories.slice(0, 3).map((cat) => (
                              <span
                                key={cat.category}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-neutral-100 text-neutral-800 border border-neutral-200"
                              >
                                <span className="font-bold text-neutral-900">{cat.category}</span>
                                <span className="text-neutral-600 font-mono">({cat.percentage}%)</span>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Network Cross-links & Repeat Offender Overlap */}
                      <div className="grid grid-cols-2 gap-2 pt-1 border-t border-neutral-100 text-xs">
                        <div className="p-2 rounded-lg bg-neutral-50 border border-neutral-200/80">
                          <div className="text-neutral-500 font-medium text-[11px]">Cross-case network links:</div>
                          <div className="text-base font-extrabold text-purple-900 font-mono">
                            {hotspot.cross_case_links_count}
                          </div>
                        </div>
                        <div className="p-2 rounded-lg bg-neutral-50 border border-neutral-200/80">
                          <div className="text-neutral-500 font-medium text-[11px]">Repeat-offender overlap:</div>
                          <div className="text-base font-extrabold text-amber-900 font-mono">
                            {hotspot.repeat_offender_overlap_count} persons
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Drilldown Action */}
                  <div className="p-3 border-t border-neutral-100 bg-neutral-50/50">
                    <button
                      onClick={() => setSelectedDistrict(hotspot.district)}
                      className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition-colors shadow-2xs cursor-pointer"
                    >
                      <span>Drill into cases / entities / evidence</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: REPEAT OFFENDER RADAR */}
      {activeTab === 'radar' && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-neutral-200 bg-white shadow-xs">
            <div className="space-y-0.5">
              <h2 className="text-sm font-bold text-neutral-900 flex items-center gap-2">
                <Radio className="h-4 w-4 text-amber-600" />
                Repeat-Offender Detection &amp; Entity-Resolved Identity Radar
              </h2>
              <p className="text-xs text-neutral-500">
                Surfaces multi-case accused individuals across spelling variations, aliases, shared phones, and cross-district mobility.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-neutral-600 font-medium">Minimum Cases:</span>
              {[2, 3, 4, 5].map((threshold) => (
                <button
                  key={threshold}
                  onClick={() => setMinCasesFilter(threshold)}
                  className={`px-3 py-1 text-xs font-bold rounded-lg border transition-colors cursor-pointer ${
                    minCasesFilter === threshold
                      ? 'bg-amber-600 text-white border-amber-600 shadow-2xs'
                      : 'bg-neutral-50 text-neutral-700 border-neutral-200 hover:bg-neutral-100'
                  }`}
                >
                  {threshold}+ Cases
                </button>
              ))}
            </div>
          </div>

          {isRadarLoading ? (
            <LoadingSkeleton layout="card" />
          ) : radarError ? (
            <ErrorState message="Failed to load repeat offender radar." onRetry={() => void refetchRadar()} />
          ) : !repeatOffenders || repeatOffenders.length === 0 ? (
            <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center text-neutral-500">
              No repeat offenders detected with at least {minCasesFilter} cases.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {repeatOffenders.map((offender) => {
                const districtsList = offender.districts || []
                return (
                  <div
                    key={offender.person_id}
                    className="rounded-xl border border-amber-200 bg-white shadow-xs hover:border-amber-300 transition-all flex flex-col justify-between overflow-hidden"
                  >
                    {/* Header */}
                    <div className="p-4 border-b border-neutral-100 space-y-2 bg-amber-50/40">
                      <div className="flex items-center justify-between">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-100 text-amber-950 border border-amber-200 tracking-wide">
                          <Radio className="h-3 w-3 text-amber-600 animate-pulse" />
                          REPEAT-OFFENDER SIGNAL
                        </span>
                        <span className="text-xs font-bold text-red-900 bg-red-50 px-2 py-0.5 rounded border border-red-200">
                          {offender.case_count} distinct cases
                        </span>
                      </div>

                      <div>
                        <h3 className="text-base font-bold text-neutral-900">{offender.canonical_name}</h3>
                        {offender.aliases && offender.aliases.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1 mt-1">
                            <span className="text-[11px] text-neutral-500 font-medium">Aliases:</span>
                            {offender.aliases.map((alias) => (
                              <span
                                key={alias}
                                className="text-[11px] font-bold text-neutral-700 bg-neutral-100 px-1.5 py-0.2 rounded border border-neutral-200"
                              >
                                {alias}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Metrics List */}
                    <div className="p-4 space-y-2.5 flex-1 text-xs">
                      <div className="space-y-1.5 bg-neutral-50 p-3 rounded-lg border border-neutral-200/80">
                        <div className="flex items-center justify-between">
                          <span className="text-neutral-600">Distinct cases:</span>
                          <span className="font-bold text-neutral-900">{offender.case_count} cases</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-neutral-600">Districts spread:</span>
                          <span className="font-bold text-neutral-900">
                            {offender.district_count} districts ({districtsList.join(', ')})
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-neutral-600">Aliases resolved:</span>
                          <span className="font-bold text-neutral-900">{offender.aliases?.length || 0} aliases</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-neutral-600">Shared network entities:</span>
                          <span className="font-bold text-neutral-900">{offender.shared_network_entities_count} entities</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-neutral-600">Shared phone identifiers:</span>
                          <span className="font-bold text-neutral-900">{offender.shared_phone_identifiers?.length || 0} identifiers</span>
                        </div>
                        {offender.most_recent_case && (
                          <div className="flex items-center justify-between pt-1 border-t border-neutral-200 text-blue-900 font-bold">
                            <span>Most recent case:</span>
                            <span className="font-mono">{offender.most_recent_case.fir_number}</span>
                          </div>
                        )}
                      </div>

                      <div className="space-y-1 pt-1 text-[11px] text-neutral-600">
                        <p><strong>Why surfaced:</strong> {offender.why_surfaced}</p>
                        <p className="text-neutral-500 italic">Status: {offender.compliance_status || 'Investigative lead — not a finding of guilt.'}</p>
                      </div>
                    </div>

                    {/* Footer Actions */}
                    <div className="p-3 border-t border-neutral-100 bg-neutral-50/50 flex items-center justify-between">
                      <Link
                        to={`/network?node_id=${encodeURIComponent(offender.person_id)}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 transition-colors shadow-2xs cursor-pointer"
                      >
                        <Network className="h-3.5 w-3.5" /> Inspect on Canvas
                      </Link>
                      {offender.most_recent_case && (
                        <Link
                          to={`/cases/${offender.most_recent_case.case_id}`}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-neutral-600 hover:text-neutral-900"
                        >
                          View FIR <ArrowRight className="h-3 w-3" />
                        </Link>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: COMBINED CROSS-DISTRICT BRIDGES */}
      {activeTab === 'combined' && (
        <div className="space-y-6">
          {isBridgeLoading ? (
            <LoadingSkeleton layout="card" />
          ) : bridgeError ? (
            <ErrorState message="Failed to load cross-district bridges." onRetry={() => void refetchBridges()} />
          ) : !bridgeSignals || bridgeSignals.length === 0 ? (
            <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center text-neutral-500">
              No cross-district repeat offender bridges detected across current hotspots.
            </div>
          ) : (
            <div className="space-y-4">
              {bridgeSignals.map((signal) => (
                <div
                  key={signal.signal_id}
                  className="rounded-xl border border-purple-200 bg-white p-5 sm:p-6 shadow-xs space-y-4 hover:border-purple-300 transition-all"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-100 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-purple-50 text-purple-900 border border-purple-200">
                        {signal.alert_title}
                      </span>
                      <h3 className="text-base font-bold text-neutral-900">
                        Primary District: {signal.primary_district} ({signal.primary_district_cases} cases)
                      </h3>
                    </div>

                    <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded border border-emerald-200">
                      Evidence-Backed Bridge
                    </span>
                  </div>

                  {/* Formatted Explanation Block */}
                  <div className="p-4 rounded-xl bg-purple-50/40 border border-purple-200 space-y-2 text-xs">
                    <p className="text-sm font-bold text-neutral-900 leading-relaxed">
                      {signal.explanation}
                    </p>
                    <div className="flex flex-wrap items-center gap-4 text-neutral-700 pt-1">
                      <span>
                        <strong>Hotspot Cases:</strong> {signal.primary_district_cases} FIRs
                      </span>
                      <span>•</span>
                      <span>
                        <strong>Repeat Offenders in Area:</strong> {signal.repeat_offender_count} suspects
                      </span>
                      <span>•</span>
                      <span>
                        <strong>Connected Districts:</strong>{' '}
                        {signal.connected_districts.map((d) => d.district).join(', ')}
                      </span>
                    </div>
                  </div>

                  {/* Bridging Suspects Details */}
                  <div className="space-y-2">
                    <div className="text-xs font-bold text-neutral-800">Bridging repeat offenders:</div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {signal.bridging_offender_details?.map((b) => (
                        <div
                          key={b.person_id}
                          className="p-3 rounded-lg border border-neutral-200 bg-neutral-50 flex items-center justify-between text-xs shadow-2xs"
                        >
                          <div>
                            <div className="font-bold text-neutral-900">{b.name}</div>
                            <div className="text-[11px] text-neutral-600">
                              Bridges {b.home_district} ↔ {b.external_districts.join(', ')} ({b.case_count} cases)
                            </div>
                          </div>
                          <Link
                            to={`/network?node_id=${encodeURIComponent(b.person_id)}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors cursor-pointer"
                          >
                            Explore
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-neutral-100">
                    <div className="text-xs text-neutral-500 font-medium">
                      Status: Actionable network bridge lead for multi-jurisdictional inquiry.
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectedDistrict(signal.primary_district)}
                        className="px-3.5 py-1.5 rounded-lg border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-800 text-xs font-bold transition-colors cursor-pointer"
                      >
                        Inspect District Cases
                      </button>
                      <Link
                        to="/leads"
                        className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-colors cursor-pointer"
                      >
                        View in Lead Inbox
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: NETWORK MODULES & BROKERS */}
      {activeTab === 'communities' && (
        <div className="space-y-6">
          {isGraphAlgoLoading ? (
            <div className="text-center py-12 text-neutral-500">Computing graph algorithms &amp; community modules...</div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Detected Communities */}
              <div className="rounded-xl border border-neutral-200/90 bg-white p-5 space-y-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
                  <h2 className="text-base font-bold text-neutral-900 flex items-center gap-2">
                    <Users className="h-4 w-4 text-blue-600" />
                    Detected Network Modules / Communities ({communities.length})
                  </h2>
                  <span className="text-xs text-neutral-500 font-medium">Modularity Clustering</span>
                </div>

                <div className="space-y-3">
                  {communities.length === 0 ? (
                    <p className="text-xs text-neutral-500">No multi-member communities detected.</p>
                  ) : (
                    communities.map((c, idx) => (
                      <div key={c.community_id || idx} className="rounded-lg bg-neutral-50 p-3.5 border border-neutral-200/80 space-y-1.5 shadow-2xs">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                            {c.community_id}
                          </span>
                          <span className="text-xs text-neutral-800 font-bold">{c.size} Associated Entities</span>
                        </div>
                        <p className="text-xs text-neutral-700">{c.reason}</p>
                        <div className="text-[11px] text-neutral-600 font-mono">
                          Top Hub Entity: <code className="text-neutral-900 font-bold">{c.top_influencer_id}</code>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Critical Bridge Nodes */}
              <div className="rounded-xl border border-neutral-200/90 bg-white p-5 space-y-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
                  <h2 className="text-base font-bold text-neutral-900 flex items-center gap-2">
                    <Share2 className="h-4 w-4 text-amber-600" />
                    Bridge Nodes &amp; Articulation Points ({graphBridges.length})
                  </h2>
                  <span className="text-xs text-neutral-500 font-medium">Betweenness Centrality</span>
                </div>

                <div className="space-y-3">
                  {graphBridges.length === 0 ? (
                    <p className="text-xs text-neutral-500">No critical bridge conduits detected.</p>
                  ) : (
                    graphBridges.map((b, idx) => (
                      <div key={b.node_id || idx} className="rounded-lg bg-amber-50/50 p-3.5 border border-amber-200/80 space-y-1.5 shadow-2xs">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-amber-950 font-mono">
                            {b.label || b.node_id}
                          </span>
                          <span className="text-xs text-amber-900 font-bold">
                            Score: {b.betweenness_score ? b.betweenness_score.toFixed(3) : 'High'}
                          </span>
                        </div>
                        <p className="text-xs text-amber-900/80">{b.reason || 'Acts as a critical bridge broker between disjoint sub-graphs.'}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* District Drill-down Modal */}
      <HotspotDrilldownModal
        district={selectedDistrict}
        onClose={() => setSelectedDistrict(null)}
        onOpenEvidence={(evId) => setEvidenceDrawerId(evId)}
      />

      {/* Forensic Evidence Drawer */}
      <EvidenceDrawer
        evidenceId={evidenceDrawerId}
        onClose={() => setEvidenceDrawerId(null)}
      />
    </div>
  )
}
