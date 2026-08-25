import { useState } from 'react'
import { Users, CheckCircle2, HelpCircle, AlertTriangle, XCircle, ShieldCheck, Search } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import type { EntityResolutionMatchResponse } from '@shared/contracts/api'

export default function Entities() {
  const [nameQuery, setNameQuery] = useState('Vikram Sharma')
  const [phoneQuery, setPhoneQuery] = useState('9845012345')
  const [vehicleQuery, setVehicleQuery] = useState('KA01AB1001')
  const [addressQuery, setAddressQuery] = useState('MG Road, Bengaluru')
  const [matches, setMatches] = useState<EntityResolutionMatchResponse[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setHasSearched(true)
    try {
      const response = await apiClient.resolveEntities({
        full_name: nameQuery,
        phone_number: phoneQuery,
        vehicle_number: vehicleQuery,
        address_text: addressQuery,
        confidence_threshold: 0.45,
      })
      setMatches(response.matches || [])
    } catch (err) {
      console.error('Entity resolution failed:', err)
      setMatches([])
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusBadge = (status: string, confidence: number) => {
    switch (status) {
      case 'MATCHED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-800 border border-emerald-200 shadow-xs">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> MATCHED ({Math.round(confidence * 100)}%)
          </span>
        )
      case 'PROBABLE_MATCH':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-900 border border-amber-200 shadow-xs">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600" /> PROBABLE MATCH ({Math.round(confidence * 100)}%)
          </span>
        )
      case 'REVIEW_REQUIRED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-800 border border-blue-200 shadow-xs">
            <HelpCircle className="h-3.5 w-3.5 text-blue-600" /> REVIEW REQUIRED ({Math.round(confidence * 100)}%)
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-bold text-neutral-800 border border-neutral-300 shadow-xs">
            <XCircle className="h-3.5 w-3.5 text-neutral-500" /> NOT MATCHED
          </span>
        )
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-neutral-200 pb-5">
        <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2.5">
          <Users className="h-6 w-6 text-blue-600" />
          Entity Resolution & Cross-Source Matching
        </h1>
        <p className="text-sm text-neutral-600 mt-1">
          Deterministic phonetic normalization, alias correlation, phone/vehicle corroboration, and explainable confidence scoring.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6">
        {/* Search Query Form */}
        <div className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-neutral-900">Suspect Query Attributes</h2>
          <form onSubmit={handleResolve} className="space-y-3.5">
            <div>
              <label className="block text-xs font-bold text-neutral-700 mb-1">Full Name / Suspect Name</label>
              <input
                type="text"
                value={nameQuery}
                onChange={(e) => setNameQuery(e.target.value)}
                placeholder="e.g. Vikram Sharma or Bikram Sarma"
                className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder-neutral-500 focus:bg-white focus:border-blue-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-neutral-700 mb-1">Phone Number (CDR / Subscribed)</label>
              <input
                type="text"
                value={phoneQuery}
                onChange={(e) => setPhoneQuery(e.target.value)}
                placeholder="e.g. 9845012345"
                className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder-neutral-500 focus:bg-white focus:border-blue-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-neutral-700 mb-1">Vehicle Registration Number</label>
              <input
                type="text"
                value={vehicleQuery}
                onChange={(e) => setVehicleQuery(e.target.value)}
                placeholder="e.g. KA-01-AB-1001"
                className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder-neutral-500 focus:bg-white focus:border-blue-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-neutral-700 mb-1">Address / Known Hideout</label>
              <input
                type="text"
                value={addressQuery}
                onChange={(e) => setAddressQuery(e.target.value)}
                placeholder="e.g. MG Road, Bengaluru"
                className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder-neutral-500 focus:bg-white focus:border-blue-600 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-blue-700 transition-colors disabled:opacity-50 shadow-sm"
            >
              <Search className="h-4 w-4" />
              {isLoading ? 'Running Multi-Source Match...' : 'Resolve Across Intelligence Graph'}
            </button>
          </form>
        </div>

        {/* Results Container */}
        <div className="space-y-4 overflow-y-auto max-h-[calc(100vh-180px)]">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-neutral-900">
              Resolved Candidate Entities {hasSearched && `(${matches.length} found)`}
            </h2>
            <span className="text-xs text-neutral-500 font-medium">Zero silent merges • Evidence-grounded</span>
          </div>

          {!hasSearched ? (
            <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center text-neutral-500 shadow-xs">
              <Users className="mx-auto h-10 w-10 mb-3 text-neutral-400" />
              <p className="text-sm">Enter suspect details or phone/vehicle records on the left to run entity resolution.</p>
            </div>
          ) : matches.length === 0 ? (
            <div className="rounded-xl border border-neutral-300 bg-white p-8 text-center text-neutral-600 shadow-xs">
              <p className="text-sm">No candidate entities matched the provided threshold.</p>
            </div>
          ) : (
            <div className="space-y-3.5">
              {matches.map((m, idx) => (
                <div key={idx} className="rounded-xl border border-neutral-200 bg-white p-4.5 space-y-3 hover:border-neutral-300 shadow-sm transition-colors min-w-0 overflow-hidden">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-base font-bold text-neutral-900 flex items-center gap-2 truncate">
                        {m.properties.full_name || m.matched_node_id}
                        {m.properties.aliases && m.properties.aliases.length > 0 && (
                          <span className="text-xs font-bold text-blue-800 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
                            Alias: {m.properties.aliases.join(', ')}
                          </span>
                        )}
                      </h3>
                      <div className="text-xs text-neutral-600 mt-0.5">
                        Node ID: <code className="text-neutral-800 font-mono font-semibold">{m.matched_node_id}</code> • Phone: {m.properties.phone_number || 'N/A'} • Vehicle: {m.properties.vehicle_number || 'N/A'}
                      </div>
                    </div>
                    <div className="flex-shrink-0 ml-2">{getStatusBadge(m.status, m.confidence)}</div>
                  </div>

                  {/* Why Match was made (Reason & Evidence) */}
                  <div className="rounded-lg bg-neutral-50 p-3 text-xs border border-neutral-200">
                    <div className="font-bold text-neutral-800 mb-1 flex items-center gap-1.5">
                      <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                      Resolution Evidence & Derivation:
                    </div>
                    <div className="text-xs text-neutral-600 leading-relaxed break-words">{m.reason}</div>
                    
                    {m.evidence_breakdown && Object.keys(m.evidence_breakdown).length > 0 && (
                      <div className="mt-2.5 flex flex-wrap gap-1 pt-2 border-t border-neutral-200">
                        {Object.entries(m.evidence_breakdown).map(([k, v]) => (
                          <span key={k} className="text-[11px] bg-white px-2 py-0.5 rounded text-neutral-800 border border-neutral-200 font-medium">
                            {k}: <strong className="text-emerald-700">+{v as number}</strong>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

