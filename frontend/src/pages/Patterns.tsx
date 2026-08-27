import { useState, useEffect } from 'react'
import { Layers, Network, Users, Share2, AlertTriangle, ShieldCheck } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'

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
}

interface RepeatOffenderItem {
  person_id?: string
  person_name?: string
  case_count?: number
  case_ids?: string[]
  reason?: string
}

interface SharedClusterItem {
  cluster_id?: string
  cluster_type?: string
  person_ids?: string[]
  case_ids?: string[]
  reason?: string
}

export default function Patterns() {
  const [communities, setCommunities] = useState<CommunityItem[]>([])
  const [bridges, setBridges] = useState<BridgeItem[]>([])
  const [repeatOffenders, setRepeatOffenders] = useState<RepeatOffenderItem[]>([])
  const [sharedClusters, setSharedClusters] = useState<SharedClusterItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      apiClient.getCommunities().catch(() => []),
      apiClient.getBridges().catch(() => []),
      apiClient.getRepeatOffenders().catch(() => []),
      apiClient.getSharedClusters().catch(() => []),
    ]).then(([commData, bridgeData, repeatData, clusterData]) => {
      setCommunities(Array.isArray(commData) ? (commData as CommunityItem[]) : [])
      setBridges(Array.isArray(bridgeData) ? (bridgeData as BridgeItem[]) : [])
      setRepeatOffenders(Array.isArray(repeatData) ? (repeatData as RepeatOffenderItem[]) : [])
      setSharedClusters(Array.isArray(clusterData) ? (clusterData as SharedClusterItem[]) : [])
    }).finally(() => {
      setIsLoading(false)
    })
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-neutral-200 pb-5">
        <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2.5">
          <Layers className="h-6 w-6 text-blue-600" />
          Criminal Network Patterns & Community Analytics
        </h1>
        <p className="text-sm text-neutral-600 mt-1">
          Graph modularity communities, bridge broker nodes, shared attribute clusters, and repeat offender matrices.
        </p>
      </div>

      {/* Investigative framing disclaimer */}
      <div className="flex items-start gap-2.5 text-xs text-neutral-700 bg-blue-50 border border-blue-200 p-3.5 rounded-xl">
        <ShieldCheck className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
        <span>
          <strong className="text-blue-900">Investigative use only:</strong> Community membership, betweenness centrality, and bridge scores are structural graph metrics that support investigative prioritisation. High centrality or bridge status does not establish criminal responsibility or guilt. All findings require investigator judgment and further corroboration.
        </span>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-neutral-500">Computing graph algorithms & community modules...</div>
      ) : (
        <div className="space-y-6">
          {/* Top Row: Communities and Bridge Nodes */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Detected Communities */}
            <div className="rounded-xl border border-neutral-200 bg-white p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
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
                    <div key={c.community_id || idx} className="rounded-lg bg-neutral-50 p-3.5 border border-neutral-200 space-y-1.5 shadow-xs">
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
            <div className="rounded-xl border border-neutral-200 bg-white p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
                <h2 className="text-base font-bold text-neutral-900 flex items-center gap-2">
                  <Share2 className="h-4 w-4 text-amber-600" />
                  Bridge Nodes & Articulation Points ({bridges.length})
                </h2>
                <span className="text-xs text-neutral-500 font-medium">Betweenness Centrality</span>
              </div>

              <div className="space-y-3">
                {bridges.length === 0 ? (
                  <p className="text-xs text-neutral-500">No single point of failure bridge brokers detected.</p>
                ) : (
                  bridges.map((b, idx) => (
                    <div key={b.node_id || idx} className="rounded-lg bg-neutral-50 p-3.5 border border-neutral-200 space-y-1.5 shadow-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-neutral-900">{b.label}</span>
                        <span className="text-xs text-amber-900 font-mono font-bold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          Score: {b.betweenness_score}
                        </span>
                      </div>
                      <p className="text-xs text-neutral-700">{b.reason}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Bottom Row: Repeat Accused & Shared Attribute Clusters */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Repeat Accused */}
            <div className="rounded-xl border border-neutral-200 bg-white p-5 space-y-4 shadow-sm">
              <h2 className="text-base font-bold text-neutral-900 flex items-center gap-2 border-b border-neutral-200 pb-3">
                <AlertTriangle className="h-4 w-4 text-red-600" />
                Cross-Case Repeat Accused Entities ({repeatOffenders.length})
              </h2>

              <div className="space-y-2.5">
                {repeatOffenders.length === 0 ? (
                  <p className="text-xs text-neutral-500">No multi-case accused entities found.</p>
                ) : (
                  repeatOffenders.map((r, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-neutral-50 border border-neutral-200">
                      <div>
                        <div className="text-sm font-bold text-neutral-900">{r.person_name}</div>
                        <div className="text-xs text-neutral-600">Accused across {r.case_count ?? 0} distinct cases ({(r.case_ids ?? []).join(', ')})</div>
                      </div>
                      <span className="text-xs font-bold text-red-900 bg-red-50 px-2.5 py-1 rounded-full border border-red-200 shadow-xs">
                        {r.case_count} Cases
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Shared Attribute Clusters */}
            <div className="rounded-xl border border-neutral-200 bg-white p-5 space-y-4 shadow-sm">
              <h2 className="text-base font-bold text-neutral-900 flex items-center gap-2 border-b border-neutral-200 pb-3">
                <Network className="h-4 w-4 text-purple-600" />
                Shared Attribute Clusters (Phones & Vehicles) ({sharedClusters.length})
              </h2>

              <div className="space-y-2.5">
                {sharedClusters.length === 0 ? (
                  <p className="text-xs text-neutral-500">No shared phone/vehicle clusters detected.</p>
                ) : (
                  sharedClusters.map((c, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-neutral-50 border border-neutral-200 space-y-1 shadow-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-purple-900 uppercase bg-purple-50 px-2 py-0.5 rounded border border-purple-200">{c.cluster_type} Cluster</span>
                        <span className="text-xs text-neutral-600 font-medium">{(c.person_ids ?? []).length} Linked Persons</span>
                      </div>
                      <div className="text-xs text-neutral-700">{c.reason}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
