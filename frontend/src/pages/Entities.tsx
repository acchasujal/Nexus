import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams, useLocation, Link } from 'react-router-dom'
import { Users, CheckCircle2, HelpCircle, AlertTriangle, XCircle, Search, ArrowRight, ShieldAlert, Phone, MapPin, Tag } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import type { EntityResolutionMatchResponse } from '@shared/contracts/api'

export default function Entities() {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const navState = (location.state as Record<string, string> | undefined) || {}

  const getInitialValue = (keys: string[]) => {
    for (const key of keys) {
      const fromParam = searchParams.get(key)
      if (fromParam !== null && fromParam !== undefined && fromParam !== '') return fromParam
      const fromState = navState[key]
      if (fromState !== null && fromState !== undefined && fromState !== '') return fromState
    }
    return ''
  }

  const [nameQuery, setNameQuery] = useState(() => getInitialValue(['name', 'full_name']))
  const [phoneQuery, setPhoneQuery] = useState(() => getInitialValue(['phone', 'phone_number']))
  const [vehicleQuery, setVehicleQuery] = useState(() => getInitialValue(['vehicle', 'vehicle_number']))
  const [addressQuery, setAddressQuery] = useState(() => getInitialValue(['address', 'address_text']))
  const [matches, setMatches] = useState<EntityResolutionMatchResponse[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const initialResolvedRef = useRef(false)

  const executeResolve = useCallback(async (params: { name?: string; phone?: string; vehicle?: string; address?: string }) => {
    const { name, phone, vehicle, address } = params
    if (!name && !phone && !vehicle && !address) return

    setIsLoading(true)
    setHasSearched(true)
    try {
      const response = await apiClient.resolveEntities({
        full_name: name || undefined,
        phone_number: phone || undefined,
        vehicle_number: vehicle || undefined,
        address_text: address || undefined,
        confidence_threshold: 0.45,
      })
      setMatches(response.matches || [])
    } catch (err) {
      console.error('Entity resolution failed:', err)
      setMatches([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const name = searchParams.get('name') ?? searchParams.get('full_name') ?? (location.state as any)?.name ?? (location.state as any)?.full_name ?? ''
    const phone = searchParams.get('phone') ?? searchParams.get('phone_number') ?? (location.state as any)?.phone ?? (location.state as any)?.phone_number ?? ''
    const vehicle = searchParams.get('vehicle') ?? searchParams.get('vehicle_number') ?? (location.state as any)?.vehicle ?? (location.state as any)?.vehicle_number ?? ''
    const address = searchParams.get('address') ?? searchParams.get('address_text') ?? (location.state as any)?.address ?? (location.state as any)?.address_text ?? ''

    if (name || phone || vehicle || address) {
      setNameQuery(name)
      setPhoneQuery(phone)
      setVehicleQuery(vehicle)
      setAddressQuery(address)

      if (!initialResolvedRef.current) {
        initialResolvedRef.current = true
        executeResolve({ name, phone, vehicle, address })
      }
    }
  }, [searchParams, location.state, executeResolve])

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault()
    executeResolve({
      name: nameQuery,
      phone: phoneQuery,
      vehicle: vehicleQuery,
      address: addressQuery,
    })
  }

  const getStatusBadge = (status?: string, confidence?: number) => {
    const safeConfidence = typeof confidence === 'number' ? Math.round(confidence * 100) : 100
    const safeStatus = String(status || 'MATCHED').toUpperCase()

    switch (safeStatus) {
      case 'MATCHED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-800 border border-emerald-200 shadow-2xs">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> MATCHED ({safeConfidence}%)
          </span>
        )
      case 'PROBABLE_MATCH':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-900 border border-amber-200 shadow-2xs">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600" /> PROBABLE MATCH ({safeConfidence}%)
          </span>
        )
      case 'REVIEW_REQUIRED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-800 border border-blue-200 shadow-2xs">
            <HelpCircle className="h-3.5 w-3.5 text-blue-600" /> REVIEW REQUIRED ({safeConfidence}%)
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-bold text-neutral-800 border border-neutral-300 shadow-2xs">
            <XCircle className="h-3.5 w-3.5 text-neutral-500" /> NOT MATCHED
          </span>
        )
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={Users}
        title="Entity Resolution & Cross-Source Matching"
        subtitle="Indian phonetic disambiguation, normalized phone MSISDNs, and deterministic corroboration engine."
      />

      {/* Query Form */}
      <SectionCard
        title="Query Entity Registry"
        subtitle="Enter suspect or entity parameters to discover candidate matches across registered police databases."
      >
        <form onSubmit={handleResolve} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label htmlFor="full-name" className="block text-xs font-bold text-neutral-700 uppercase tracking-wider">
                Full Name / Suspect Name
              </label>
              <input
                id="full-name"
                type="text"
                value={nameQuery}
                onChange={(e) => setNameQuery(e.target.value)}
                placeholder="e.g. Ramesh Hegde"
                className="mt-1.5 w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs sm:text-sm text-neutral-900 placeholder-neutral-400 focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 shadow-2xs"
              />
            </div>

            <div>
              <label htmlFor="phone-number" className="block text-xs font-bold text-neutral-700 uppercase tracking-wider">
                Phone Number
              </label>
              <input
                id="phone-number"
                type="text"
                value={phoneQuery}
                onChange={(e) => setPhoneQuery(e.target.value)}
                placeholder="e.g. +91 98201 22334"
                className="mt-1.5 w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs sm:text-sm text-neutral-900 placeholder-neutral-400 focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 shadow-2xs"
              />
            </div>

            <div>
              <label htmlFor="vehicle-number" className="block text-xs font-bold text-neutral-700 uppercase tracking-wider">
                Vehicle Registration Number
              </label>
              <input
                id="vehicle-number"
                type="text"
                value={vehicleQuery}
                onChange={(e) => setVehicleQuery(e.target.value)}
                placeholder="e.g. MH-01-AB-1234"
                className="mt-1.5 w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs sm:text-sm text-neutral-900 placeholder-neutral-400 focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 shadow-2xs"
              />
            </div>

            <div>
              <label htmlFor="address-text" className="block text-xs font-bold text-neutral-700 uppercase tracking-wider">
                Address / Known Hideout
              </label>
              <input
                id="address-text"
                type="text"
                value={addressQuery}
                onChange={(e) => setAddressQuery(e.target.value)}
                placeholder="e.g. Kurla West, Mumbai"
                className="mt-1.5 w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs sm:text-sm text-neutral-900 placeholder-neutral-400 focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 shadow-2xs"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-xs sm:text-sm font-bold text-white transition-colors hover:bg-blue-700 shadow-xs disabled:opacity-50 cursor-pointer"
            >
              <Search className="h-4 w-4" />
              {isLoading ? 'Querying Knowledge Graph...' : 'Search & Corroborate'}
            </button>
          </div>
        </form>
      </SectionCard>

      {/* Results Container */}
      {hasSearched && (
        <div className="space-y-4">
          <h2 className="text-base font-bold text-neutral-900">
            Corroborated Resolution Matches ({matches.length})
          </h2>

          {matches.length === 0 ? (
            <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center shadow-xs">
              <Users className="mx-auto h-12 w-12 text-neutral-400" />
              <h3 className="mt-3 text-base font-bold text-neutral-800">No matching entities found</h3>
              <p className="mt-1 text-xs text-neutral-500">Try broadening your search query or removing restrictive filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {matches.map((m, idx) => {
                const nodeId = m.matched_node_id || (m as any).entity_id || `match-${idx}`
                const canonicalName = m.properties?.full_name || m.properties?.name || (m as any).canonical_name || (m as any).label || nodeId
                const status = m.status || (m as any).match_status || 'MATCHED'
                const confidence = typeof m.confidence === 'number' ? m.confidence : typeof (m as any).confidence_score === 'number' ? (m as any).confidence_score : 1.0
                const matchedFields = ((m.matched_fields || (m as any).matched_attributes || (m as any).matched_properties || []) as string[])
                const reason = m.reason || 'Corroborated cross-case entity match based on shared demographic and telephony attributes.'
                const properties = m.properties || {}

                return (
                  <div
                    key={nodeId}
                    className="rounded-xl border border-neutral-200/90 bg-white p-5 shadow-xs space-y-4 hover:border-neutral-300 transition-all"
                  >
                    <div className="flex items-start justify-between gap-2 border-b border-neutral-100 pb-3">
                      <div>
                        <h3 className="text-base font-bold text-neutral-900">{canonicalName}</h3>
                        <div className="text-xs text-neutral-500 font-mono mt-0.5">{nodeId}</div>
                      </div>
                      {getStatusBadge(status, confidence)}
                    </div>

                    <div className="space-y-2 text-xs">
                      <div className="text-neutral-700 leading-relaxed">
                        <strong className="text-neutral-900">Match Decision Basis:</strong> {reason}
                      </div>

                      {matchedFields.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          <span className="text-[11px] font-bold text-neutral-500 mr-1 flex items-center gap-1">
                            <Tag className="h-3 w-3" /> Corroborated:
                          </span>
                          {matchedFields.map((attr) => (
                            <span
                              key={attr}
                              className="rounded-md bg-blue-50 border border-blue-200 px-2 py-0.5 text-[11px] font-semibold text-blue-800"
                            >
                              ✓ {String(attr).replaceAll('_', ' ')}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Display key properties if present */}
                      {Object.keys(properties).length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-neutral-100 text-[11px] text-neutral-600">
                          {properties.phone_number && (
                            <div className="flex items-center gap-1.5 text-neutral-700">
                              <Phone className="h-3 w-3 text-neutral-400" />
                              <span>{String(properties.phone_number)}</span>
                            </div>
                          )}
                          {properties.district && (
                            <div className="flex items-center gap-1.5 text-neutral-700">
                              <MapPin className="h-3 w-3 text-neutral-400" />
                              <span>{String(properties.district)}</span>
                            </div>
                          )}
                          {properties.role && (
                            <div className="flex items-center gap-1.5 text-neutral-700">
                              <ShieldAlert className="h-3 w-3 text-amber-500" />
                              <span>Role: {String(properties.role)}</span>
                            </div>
                          )}
                          {Array.isArray(properties.aliases) && properties.aliases.length > 0 && (
                            <div className="col-span-full text-neutral-600">
                              <span className="font-semibold text-neutral-500">Aliases:</span> {properties.aliases.join(', ')}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="pt-3 border-t border-neutral-100 flex justify-end">
                      <Link
                        to={`/network?node_id=${encodeURIComponent(nodeId)}`}
                        className="inline-flex items-center gap-1.5 text-xs font-bold text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg border border-blue-200 transition-colors cursor-pointer shadow-2xs"
                      >
                        Inspect on Canvas <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
