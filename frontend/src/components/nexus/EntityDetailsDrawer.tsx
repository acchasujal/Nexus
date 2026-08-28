/**
 * frontend/src/components/nexus/EntityDetailsDrawer.tsx
 *
 * Canonical reusable Entity Details Drawer for NEXUS.
 * Opens on any entity node click across Canvas, Case Overview, Leads, and Search.
 * Displays: entity attributes, aliases, degree, betweenness centrality,
 * Section 63 BSA evidence citations, and case context actions.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  X,
  User,
  Phone,
  Landmark,
  Car,
  MapPin,
  FileText,
  ShieldCheck,
  Network,
  ExternalLink,
  GitMerge,
  Copy,
  Check,
  Layers,
} from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import type { EntityProfileResponse } from '@shared/contracts/api'

interface EntityDetailsDrawerProps {
  entityId: string | null
  onClose: () => void
  onFocusEntity?: (entityId: string) => void
}

export function EntityDetailsDrawer({
  entityId,
  onClose,
  onFocusEntity,
}: EntityDetailsDrawerProps) {
  const [profile, setProfile] = useState<EntityProfileResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  useEffect(() => {
    if (!entityId) {
      setProfile(null)
      setError(null)
      return
    }

    let isMounted = true
    setIsLoading(true)
    setError(null)

    apiClient
      .getEntityProfile(entityId)
      .then((data) => {
        if (isMounted) {
          setProfile(data)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Entity record not found.')
          setProfile(null)
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [entityId])

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(text)
      setTimeout(() => setCopied(null), 1500)
    } catch {
      // ignore
    }
  }

  if (!entityId) return null

  const getEntityIcon = (type?: string) => {
    switch (type?.toLowerCase()) {
      case 'person':
        return <User className="h-5 w-5 text-sky-600" />
      case 'phone':
        return <Phone className="h-5 w-5 text-amber-600" />
      case 'account':
      case 'bank_account':
        return <Landmark className="h-5 w-5 text-purple-600" />
      case 'vehicle':
        return <Car className="h-5 w-5 text-emerald-600" />
      case 'location':
        return <MapPin className="h-5 w-5 text-rose-600" />
      default:
        return <Layers className="h-5 w-5 text-blue-600" />
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-label="Entity intelligence drawer"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-950/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Body */}
      <aside className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-neutral-200 bg-white text-neutral-900 shadow-2xl z-10 animate-in slide-in-from-right duration-200">
        {/* Sticky Header */}
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-neutral-200 bg-white/95 px-5 py-4 backdrop-blur shadow-xs">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-neutral-100 border border-neutral-200 shadow-2xs">
              {getEntityIcon(profile?.entity_type)}
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-blue-700">
                Entity Intelligence Record
              </p>
              <h2 className="font-mono text-sm font-bold text-neutral-900 truncate max-w-[240px]">
                {profile?.label || entityId}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors cursor-pointer"
            aria-label="Close entity drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        {/* Content */}
        <div className="space-y-5 px-5 py-5 flex-1">
          {isLoading && <LoadingSkeleton layout="detail" />}

          {error && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4" role="alert">
              <div className="flex items-center gap-2 font-bold text-amber-900">
                <FileText className="h-4 w-4 text-amber-600" /> Entity details unrecorded
              </div>
              <p className="mt-2 text-xs text-amber-800 leading-relaxed">
                {error} Node identifier <code className="font-mono bg-white px-1 py-0.5 rounded border border-amber-200">{entityId}</code> is present in graph topology but detailed attributes have not been indexed.
              </p>
            </div>
          )}

          {profile && (
            <>
              {/* Top Summary Card */}
              <section className="rounded-xl border border-neutral-200 bg-neutral-50/80 p-4 shadow-xs space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 font-mono text-[10px] font-bold text-blue-800">
                    {profile.entity_type}
                  </span>
                  <button
                    onClick={() => copyText(profile.id)}
                    className="inline-flex items-center gap-1 text-[10px] font-mono text-neutral-500 hover:text-neutral-900 bg-white border border-neutral-200 px-1.5 py-0.5 rounded"
                  >
                    {copied === profile.id ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                    {profile.id}
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                  <div className="bg-white p-2.5 rounded-lg border border-neutral-200 shadow-2xs">
                    <dt className="text-neutral-500 text-[10px] uppercase font-bold tracking-wider">Network Degree</dt>
                    <dd className="mt-0.5 text-base font-bold text-neutral-900">{profile.degree} connections</dd>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-neutral-200 shadow-2xs">
                    <dt className="text-neutral-500 text-[10px] uppercase font-bold tracking-wider">Connector Position</dt>
                    <dd className="mt-0.5 text-base font-bold text-blue-700">
                      {typeof profile.betweenness_score === 'number'
                        ? `${(profile.betweenness_score * 100).toFixed(1)}% Central`
                        : 'Standard'}
                    </dd>
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="flex flex-wrap gap-2 pt-2 border-t border-neutral-200">
                  {onFocusEntity && (
                    <button
                      onClick={() => {
                        onFocusEntity(profile.id)
                        onClose()
                      }}
                      className="inline-flex items-center gap-1.5 text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-2.5 py-1.5 rounded-lg transition-colors"
                    >
                      <Network className="h-3.5 w-3.5" />
                      Focus Neighborhood
                    </button>
                  )}
                  <Link
                    to={`/network?node_id=${encodeURIComponent(profile.id)}`}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-neutral-700 bg-white hover:bg-neutral-50 border border-neutral-300 px-2.5 py-1.5 rounded-lg transition-colors"
                  >
                    <ExternalLink className="h-3.5 w-3.5 text-neutral-500" />
                    Open in Explorer
                  </Link>
                </div>
              </section>

              {/* Entity Properties */}
              {profile.properties && Object.keys(profile.properties).length > 0 && (
                <section className="space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-600">
                    Recorded Attributes
                  </h3>
                  <div className="rounded-xl border border-neutral-200 bg-white p-3.5 shadow-2xs">
                    <dl className="space-y-2 text-xs">
                      {Object.entries(profile.properties)
                        .filter(([k]) => !['badges', 'case_id', 'case_ids', 'source_records'].includes(k))
                        .map(([k, v]) => {
                          let formattedValue = ''
                          if (v !== null && v !== undefined) {
                            if (Array.isArray(v)) {
                              formattedValue = v.map(String).join(', ')
                            } else if (typeof v === 'object') {
                              try { formattedValue = JSON.stringify(v) } catch { formattedValue = '[Object]' }
                            } else {
                              formattedValue = String(v)
                            }
                          }
                          
                          return (
                            <div key={k} className="flex justify-between gap-3 border-b border-neutral-100 pb-1.5 last:border-0 last:pb-0">
                              <dt className="text-neutral-500 capitalize font-medium">{k.replaceAll('_', ' ')}</dt>
                              <dd className="text-right font-semibold text-neutral-900 break-all">{formattedValue}</dd>
                            </div>
                          )
                        })}
                    </dl>
                  </div>
                </section>
              )}

              {/* Aliases */}
              {profile.aliases && profile.aliases.length > 0 && (
                <section className="space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-600 flex items-center gap-1.5">
                    <GitMerge className="h-3.5 w-3.5 text-emerald-600" />
                    Unified Aliases ({profile.aliases.length})
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {profile.aliases.map((alias) => (
                      <span
                        key={alias}
                        className="rounded bg-emerald-50 text-emerald-900 border border-emerald-200 px-2 py-0.5 text-xs font-bold font-mono shadow-2xs"
                      >
                        {alias}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {/* Section 63 BSA Evidence Items */}
              <section className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-600 flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                  Section 63 BSA Citations ({profile.evidence_items?.length || 0})
                </h3>
                {(!profile.evidence_items || profile.evidence_items.length === 0) ? (
                  <p className="text-xs text-neutral-500 italic">No direct Section 63 BSA citations linked to this entity.</p>
                ) : (
                  <ul className="space-y-2.5">
                    {profile.evidence_items.map((ev) => (
                      <li key={ev.id} className="rounded-lg border border-neutral-200 bg-white p-3 shadow-2xs space-y-1.5 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="rounded bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.2 font-mono text-[10px] font-bold">
                            {ev.evidence_type}
                          </span>
                          <code className="font-mono text-[10px] text-neutral-500">{ev.id}</code>
                        </div>
                        <p className="text-neutral-800 font-medium">{ev.description}</p>
                        {ev.provenance && (
                          <div className="text-[10px] text-neutral-500 flex items-center gap-1">
                            <span>Source:</span>
                            <code className="font-mono font-bold text-neutral-700">{ev.provenance.source_id || ev.provenance.source_type}</code>
                            {ev.provenance.file_hash && (
                              <span className="text-neutral-400 font-mono">({ev.provenance.file_hash.substring(0, 8)}...)</span>
                            )}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
