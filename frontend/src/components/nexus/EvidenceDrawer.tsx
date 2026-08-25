/**
 * frontend/src/components/nexus/EvidenceDrawer.tsx
 *
 * Click-any-link Evidence Drawer: relationship details, Fact/Derived/Hypothesis
 * badge, confidence, time, source locators with raw excerpts, derivation chain,
 * and copyable evidence IDs.
 */
import { useState } from 'react'
import { X, Copy, Check, FileSearch, Link2, ShieldQuestion, Clock } from 'lucide-react'
import { useEdgeEvidence } from '@/hooks/useNexus'
import { DerivationBadge } from './DerivationBadge'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'

interface EvidenceDrawerProps {
  relationshipId: string | null
  onClose: () => void
}

export function EvidenceDrawer({ relationshipId, onClose }: EvidenceDrawerProps) {
  const { data, isLoading, error } = useEdgeEvidence(relationshipId)
  const [copied, setCopied] = useState<string | null>(null)

  const copyId = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id)
      setCopied(id)
      setTimeout(() => setCopied(null), 1500)
    } catch {
      /* clipboard unavailable */
    }
  }

  if (!relationshipId) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-label="Relationship evidence drawer">
      <div className="absolute inset-0 bg-neutral-950/40 backdrop-blur-xs" onClick={onClose} />
      <aside className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-neutral-200 bg-white text-neutral-900 shadow-2xl">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-neutral-200 bg-white/95 px-5 py-4 backdrop-blur shadow-xs">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-blue-700">Evidence Drawer</p>
            <h2 className="mt-0.5 font-mono text-sm font-bold text-neutral-900">{relationshipId}</h2>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors" aria-label="Close evidence drawer">
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="space-y-5 px-5 py-5">
          {isLoading && <LoadingSkeleton layout="detail" />}

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4" role="alert">
              <div className="flex items-center gap-2 font-bold text-red-900">
                <ShieldQuestion className="h-5 w-5 text-red-600" /> Evidence chain unavailable
              </div>
              <p className="mt-2 text-sm text-red-800">
                The full lineage for this relationship cannot be returned right now. No summary is shown without its source chain — this view fails closed.
              </p>
            </div>
          )}

          {data && (
            <>
              <section className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 shadow-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <DerivationBadge klass={data.derivation_class} />
                  <span className="rounded-md border border-neutral-300 bg-white px-2 py-0.5 font-mono text-[10px] font-bold text-neutral-800 shadow-xs">{data.edge_type}</span>
                </div>
                <p className="mt-3 flex items-center gap-2 text-sm font-bold text-neutral-900">
                  <Link2 className="h-4 w-4 text-blue-600" />
                  {data.source_label} <span className="text-neutral-400">→</span> {data.target_label}
                </p>
                <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <dt className="text-neutral-500 font-medium">Confidence</dt>
                    <dd className="mt-0.5 font-bold text-neutral-900">{(data.confidence * 100).toFixed(0)}%</dd>
                  </div>
                  <div>
                    <dt className="text-neutral-500 font-medium">Recorded at</dt>
                    <dd className="mt-0.5 flex items-center gap-1 font-medium text-neutral-800">
                      <Clock className="h-3 w-3 text-neutral-400" />
                      {new Date(data.recorded_at).toLocaleString()}
                    </dd>
                  </div>
                </dl>
              </section>

              <section aria-labelledby="ev-sources">
                <h3 id="ev-sources" className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-neutral-600">
                  <FileSearch className="h-4 w-4 text-blue-600" /> Source records ({data.source_records.length})
                </h3>
                <ul className="mt-3 space-y-3">
                  {data.source_records.map((rec) => (
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
                  {data.derivation_chain.map((step) => (
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
