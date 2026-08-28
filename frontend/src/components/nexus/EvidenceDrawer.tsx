/**
 * frontend/src/components/nexus/EvidenceDrawer.tsx
 *
 * Click-any-link Evidence Drawer: relationship details, Fact/Derived/Hypothesis
 * badge, confidence, time, source locators with raw excerpts, derivation chain,
 * and copyable evidence IDs.
 */
import { useState, useEffect } from 'react'
import { X, Copy, Check, FileSearch, Link2, ShieldQuestion, Clock, FileText } from 'lucide-react'
import { useEdgeEvidence } from '@/hooks/useNexus'
import { apiClient } from '@/lib/apiClient'
import { DerivationBadge } from './DerivationBadge'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import type { NexusSourceRecord } from '@shared/contracts/api'

interface EvidenceDrawerProps {
  relationshipId?: string | null
  evidenceId?: string | null
  onClose: () => void
}

export function EvidenceDrawer({ relationshipId, evidenceId, onClose }: EvidenceDrawerProps) {
  const activeRelationshipId = relationshipId && !relationshipId.startsWith('SRC-') ? relationshipId : null
  const activeEvidenceId = evidenceId || (relationshipId && relationshipId.startsWith('SRC-') ? relationshipId : null)

  const { data: edgeData, isLoading: isEdgeLoading, error: edgeError } = useEdgeEvidence(activeRelationshipId)
  const [sourceData, setSourceData] = useState<NexusSourceRecord | null>(null)
  const [isSourceLoading, setIsSourceLoading] = useState(false)
  const [sourceError, setSourceError] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  useEffect(() => {
    if (!activeEvidenceId) {
      setSourceData(null)
      setSourceError(null)
      return
    }

    let isMounted = true
    setIsSourceLoading(true)
    setSourceError(null)

    apiClient
      .getSourceRecord(activeEvidenceId)
      .then((rec) => {
        if (isMounted) {
          setSourceData(rec)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setSourceError(err instanceof Error ? err.message : 'Evidence record not found.')
          setSourceData(null)
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsSourceLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [activeEvidenceId])

  const copyId = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id)
      setCopied(id)
      setTimeout(() => setCopied(null), 1500)
    } catch {
      /* clipboard unavailable */
    }
  }

  const effectiveId = activeEvidenceId || activeRelationshipId
  if (!effectiveId) return null

  const isLoading = isEdgeLoading || isSourceLoading
  const hasError = (activeRelationshipId && edgeError) || (activeEvidenceId && sourceError)

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-label="Relationship evidence drawer">
      <div className="absolute inset-0 bg-neutral-950/40 backdrop-blur-xs" onClick={onClose} />
      <aside className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-neutral-200 bg-white text-neutral-900 shadow-2xl">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-neutral-200 bg-white/95 px-5 py-4 backdrop-blur shadow-xs">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-blue-700">
              {activeEvidenceId ? 'Source Evidence Record' : 'Relationship Evidence Chain'}
            </p>
            <h2 className="mt-0.5 font-mono text-sm font-bold text-neutral-900">{effectiveId}</h2>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors" aria-label="Close evidence drawer">
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="space-y-5 px-5 py-5">
          {isLoading && <LoadingSkeleton layout="detail" />}

          {hasError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4" role="alert">
              <div className="flex items-center gap-2 font-bold text-red-900">
                <ShieldQuestion className="h-5 w-5 text-red-600" /> {activeEvidenceId ? 'Evidence record unavailable' : 'Evidence chain unavailable'}
              </div>
              <p className="mt-2 text-sm text-red-800">
                {sourceError || 'The full lineage for this record cannot be returned right now. No summary is shown without its source chain — this view fails closed.'}
              </p>
            </div>
          )}

          {/* Direct Source Record View */}
          {sourceData && (
            <div className="space-y-4">
              <section className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 shadow-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="rounded bg-blue-100 border border-blue-200 px-2 py-0.5 font-mono text-xs font-bold text-blue-900">
                    {sourceData.source_type}
                  </span>
                  <button onClick={() => copyId(sourceData.id)} className="flex items-center gap-1 rounded border border-neutral-200 px-2 py-0.5 font-mono text-[10px] text-neutral-600 hover:bg-white transition-colors" aria-label={`Copy evidence ID ${sourceData.id}`}>
                    {copied === sourceData.id ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                    {copied === sourceData.id ? 'Copied' : sourceData.id}
                  </button>
                </div>
                <div className="pt-2">
                  <p className="text-xs text-neutral-500 font-bold uppercase tracking-wider">Forensic Locator</p>
                  <p className="font-mono text-xs text-amber-900 bg-amber-50 px-2 py-1 rounded border border-amber-200 mt-1">{sourceData.locator}</p>
                </div>
              </section>

              <section className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-600 flex items-center gap-1.5">
                  <FileSearch className="h-4 w-4 text-blue-600" /> Verbatim Source Excerpt
                </h3>
                <blockquote className="border-l-4 border-blue-600 bg-neutral-50 p-3 text-xs leading-relaxed text-neutral-800 rounded-r shadow-2xs font-mono">
                  "{sourceData.raw_excerpt}"
                </blockquote>
              </section>

              <section className="rounded-xl border border-neutral-200 bg-white p-3.5 shadow-2xs space-y-1.5 text-xs">
                <div className="flex justify-between text-neutral-600">
                  <span>Occurred:</span>
                  <span className="font-medium text-neutral-900">{new Date(sourceData.occurred_at).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-neutral-600">
                  <span>Ingestion Batch:</span>
                  <span className="font-mono text-neutral-900">{sourceData.batch_id}</span>
                </div>
                {sourceData.case_ids && sourceData.case_ids.length > 0 && (
                  <div className="flex justify-between text-neutral-600 pt-1 border-t border-neutral-100">
                    <span>Associated Cases:</span>
                    <span className="font-bold text-blue-700">{sourceData.case_ids.join(', ')}</span>
                  </div>
                )}
              </section>
            </div>
          )}

          {/* Relationship Edge View */}
          {edgeData && !sourceData && (
            <>
              <section className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 shadow-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <DerivationBadge klass={edgeData.derivation_class} />
                  <span className="rounded-md border border-neutral-300 bg-white px-2 py-0.5 font-mono text-[10px] font-bold text-neutral-800 shadow-xs">{edgeData.edge_type}</span>
                </div>
                <p className="mt-3 flex items-center gap-2 text-sm font-bold text-neutral-900">
                  <Link2 className="h-4 w-4 text-blue-600" />
                  {edgeData.source_label} <span className="text-neutral-400">→</span> {edgeData.target_label}
                </p>
                <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <dt className="text-neutral-500 font-medium">Confidence</dt>
                    <dd className="mt-0.5 font-bold text-neutral-900">{(edgeData.confidence * 100).toFixed(0)}%</dd>
                  </div>
                  <div>
                    <dt className="text-neutral-500 font-medium">Recorded at</dt>
                    <dd className="mt-0.5 flex items-center gap-1 font-medium text-neutral-800">
                      <Clock className="h-3 w-3 text-neutral-400" />
                      {new Date(edgeData.recorded_at).toLocaleString()}
                    </dd>
                  </div>
                </dl>
              </section>

              <section aria-labelledby="ev-sources">
                <h3 id="ev-sources" className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-neutral-600">
                  <FileSearch className="h-4 w-4 text-blue-600" /> Source records ({edgeData.source_records.length})
                </h3>
                <ul className="mt-3 space-y-3">
                  {edgeData.source_records.map((rec) => (
                    <li key={rec.id} className="rounded-lg border border-neutral-200 bg-white p-3.5 shadow-sm space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded bg-blue-50 border border-blue-200 px-2 py-0.5 font-mono text-[10px] font-bold text-blue-800">{rec.source_type}</span>
                        <button onClick={() => copyId(rec.id)} className="flex items-center gap-1 rounded border border-neutral-200 px-2 py-0.5 font-mono text-[10px] text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900 transition-colors" aria-label={`Copy evidence ID ${rec.id}`}>
                          {copied === rec.id ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                          {copied === rec.id ? 'Copied' : rec.id}
                        </button>
                      </div>
                      <p className="rounded bg-amber-50 border border-amber-200 px-2 py-1 font-mono text-[11px] text-amber-900">{rec.locator}</p>
                      <blockquote className="border-l-4 border-blue-600 bg-neutral-50 p-2.5 text-xs leading-relaxed text-neutral-800 rounded-r">
                        "{rec.raw_excerpt}"
                      </blockquote>
                      <p className="text-[10px] text-neutral-500">
                        Occurred {new Date(rec.occurred_at).toLocaleString()} · batch {rec.batch_id}
                      </p>
                    </li>
                  ))}
                </ul>
              </section>

              <section aria-labelledby="ev-derivation">
                <h3 id="ev-derivation" className="text-xs font-bold uppercase tracking-wider text-neutral-600">Derivation chain</h3>
                <ol className="mt-3 space-y-2">
                  {edgeData.derivation_chain.map((step) => (
                    <li key={step.step} className="flex gap-3 rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-xs shadow-xs">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 font-bold text-blue-800">{step.step}</span>
                      <div>
                        <code className="font-mono font-bold text-blue-800">{step.rule}</code>
                        <p className="mt-1 text-neutral-600">inputs: {step.inputs.join(', ')}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
