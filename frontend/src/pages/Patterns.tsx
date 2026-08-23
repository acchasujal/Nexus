import { useState, useEffect } from 'react'
import { Layers, Network, Users, Share2, AlertTriangle, ShieldCheck, Activity, BarChart3 } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'

export default function Patterns() {
  const [communities, setCommunities] = useState<any[]>([])
  const [bridges, setBridges] = useState<any[]>([])
  const [repeatOffenders, setRepeatOffenders] = useState<any[]>([])
  const [sharedClusters, setSharedClusters] = useState<any[]>([])
  const [influenceRankings, setInfluenceRankings] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      apiClient.getCommunities().catch(() => []),
      apiClient.getBridges().catch(() => []),
      apiClient.getRepeatOffenders().catch(() => []),
      apiClient.getSharedClusters().catch(() => []),
      apiClient.getInfluenceRankings().catch(() => []),
    ]).then(([commData, bridgeData, repeatData, clusterData, rankData]) => {
      setCommunities(Array.isArray(commData) ? commData : [])
      setBridges(Array.isArray(bridgeData) ? bridgeData : [])
      setRepeatOffenders(Array.isArray(repeatData) ? repeatData : [])
      setSharedClusters(Array.isArray(clusterData) ? clusterData : [])
      setInfluenceRankings(Array.isArray(rankData) ? rankData : [])
    }).finally(() => {
      setIsLoading(false)
    })
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-neutral-800 pb-5">
        <h1 className="text-2xl font-bold text-neutral-100 flex items-center gap-2.5">
          <Layers className="h-6 w-6 text-blue-500" />
          Criminal Network Patterns & Community Analytics
        </h1>
        <p className="text-sm text-neutral-400 mt-1">
          Graph modularity communities, bridge broker nodes, shared attribute clusters, and repeat offender matrices.
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-neutral-500">Computing graph algorithms & community modules...</div>
      ) : (
        <div className="space-y-6">
          {/* Top Row: Communities and Bridge Nodes */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Detected Communities */}
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-4 shadow-lg">
              <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Users className="h-4 w-4 text-blue-400" />
                  Detected Network Modules / Communities ({communities.length})
                </h2>
                <span className="text-xs text-neutral-400">Modularity Clustering</span>
              </div>

              <div className="space-y-3">
                {communities.length === 0 ? (
                  <p className="text-xs text-neutral-500">No multi-member communities detected.</p>
                ) : (
                  communities.map((c, idx) => (
                    <div key={c.community_id || idx} className="rounded-lg bg-neutral-950/80 p-3.5 border border-neutral-800 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-blue-400 bg-blue-950 px-2 py-0.5 rounded border border-blue-800/40">
                          {c.community_id}
                        </span>
                        <span className="text-xs text-neutral-300 font-semibold">{c.size} Associated Entities</span>
                      </div>
                      <p className="text-xs text-neutral-300">{c.reason}</p>
                      <div className="text-[11px] text-neutral-500">
                        Top Hub Entity: <code className="text-neutral-400">{c.top_influencer_id}</code>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Critical Bridge Nodes */}
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-4 shadow-lg">
              <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Share2 className="h-4 w-4 text-amber-400" />
                  Bridge Nodes & Articulation Points ({bridges.length})
                </h2>
                <span className="text-xs text-neutral-400">Betweenness Centrality</span>
              </div>

              <div className="space-y-3">
                {bridges.length === 0 ? (
                  <p className="text-xs text-neutral-500">No single point of failure bridge brokers detected.</p>
                ) : (
                  bridges.map((b, idx) => (
                    <div key={b.node_id || idx} className="rounded-lg bg-neutral-950/80 p-3.5 border border-neutral-800 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-amber-300">{b.label}</span>
                        <span className="text-xs text-amber-400/90 font-mono bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/40">
                          Score: {b.betweenness_score}
                        </span>
                      </div>
                      <p className="text-xs text-neutral-400">{b.reason}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Bottom Row: Repeat Accused & Shared Attribute Clusters */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Repeat Accused */}
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-4 shadow-lg">
              <h2 className="text-base font-bold text-white flex items-center gap-2 border-b border-neutral-800 pb-3">
                <AlertTriangle className="h-4 w-4 text-red-400" />
                Cross-Case Repeat Accused Entities ({repeatOffenders.length})
              </h2>

              <div className="space-y-2.5">
                {repeatOffenders.length === 0 ? (
                  <p className="text-xs text-neutral-500">No multi-case accused entities found.</p>
                ) : (
                  repeatOffenders.map((r, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-neutral-950/80 border border-neutral-800">
                      <div>
                        <div className="text-sm font-semibold text-white">{r.person_name}</div>
                        <div className="text-xs text-neutral-400">Accused across {r.case_count} distinct cases ({r.case_ids.join(', ')})</div>
                      </div>
                      <span className="text-xs font-bold text-red-400 bg-red-950 px-2.5 py-1 rounded-full border border-red-800">
                        {r.case_count} Cases
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Shared Attribute Clusters */}
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-4 shadow-lg">
              <h2 className="text-base font-bold text-white flex items-center gap-2 border-b border-neutral-800 pb-3">
                <Network className="h-4 w-4 text-purple-400" />
                Shared Attribute Clusters (Phones & Vehicles) ({sharedClusters.length})
              </h2>

              <div className="space-y-2.5">
                {sharedClusters.length === 0 ? (
                  <p className="text-xs text-neutral-500">No shared phone/vehicle clusters detected.</p>
                ) : (
                  sharedClusters.map((c, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-neutral-950/80 border border-neutral-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-purple-400 uppercase">{c.cluster_type} Cluster</span>
                        <span className="text-xs text-neutral-400">{c.person_ids.length} Linked Persons</span>
                      </div>
                      <div className="text-xs text-neutral-300">{c.reason}</div>
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
