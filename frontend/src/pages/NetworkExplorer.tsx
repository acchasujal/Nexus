import { useState, useEffect } from 'react'
import { Network } from 'lucide-react'
import { NetworkAnalysisPanel } from '@/components/NetworkAnalysisPanel'
import { apiClient } from '@/lib/apiClient'

export default function NetworkExplorer() {
  const [selectedCaseId, setSelectedCaseId] = useState<string>('case-0001')
  const [cases, setCases] = useState<any[]>([])
  const [depth, setDepth] = useState<number>(2)

  useEffect(() => {
    // Fetch available investigations
    apiClient.getInvestigations().then((data: any) => {
      if (Array.isArray(data) && data.length > 0) {
        setCases(data)
        setSelectedCaseId((prev) => prev || data[0].id)
      }
    }).catch(() => {
      // Fallback
      setCases([
        { id: 'case-0001', fir_number: 'FIR-2026-101', title: 'Narcotics Syndicate Investigation' },
        { id: 'case-0002', fir_number: 'FIR-2026-102', title: 'Cyber Phishing Network' },
      ])
    })
  }, [])

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100 flex items-center gap-2.5">
            <Network className="h-6 w-6 text-blue-500" />
            Unified Intelligence Graph Explorer
          </h1>
          <p className="text-sm text-neutral-400 mt-1">
            Multi-hop entity graph visualization, co-accused discovery, and cross-source link analysis.
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          <select
            value={selectedCaseId}
            onChange={(e) => setSelectedCaseId(e.target.value)}
            className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
          >
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.fir_number} - {c.title || c.offence_category}
              </option>
            ))}
          </select>

          <select
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
          >
            <option value={1}>1 Hop (Direct)</option>
            <option value={2}>2 Hops (Expanded)</option>
            <option value={3}>3 Hops (Syndicate)</option>
          </select>
        </div>
      </div>

      {/* Network Graph Container */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 shadow-lg">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-4 text-xs text-neutral-400">
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-blue-500" /> Person / Suspect</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-emerald-500" /> Case / FIR</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-amber-500" /> Monitored Phone</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-purple-500" /> Bank Account</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-cyan-500" /> Intelligence Report</span>
          </div>
          <span className="text-xs text-neutral-500">Interactive: Drag, Zoom, Click to inspect provenance</span>
        </div>

        <NetworkAnalysisPanel caseId={selectedCaseId} />
      </div>
    </div>
  )
}
