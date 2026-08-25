import { useState, useMemo } from 'react'
import { FileText, Calendar, Copy, Check, Phone, Landmark, FileSearch, ShieldCheck, MapPin } from 'lucide-react'
import { allSourceRecords } from '@/lib/mocks/nexusFixture'
import type { NexusSourceRecord } from '@shared/contracts/api'

const TYPE_CONFIG: Record<string, { badge: string; icon: typeof FileText }> = {
  FIR: {
    badge: 'text-sky-900 bg-sky-50 border-sky-200 font-bold',
    icon: FileText,
  },
  CDR: {
    badge: 'text-amber-900 bg-amber-50 border-amber-200 font-bold',
    icon: Phone,
  },
  BANK_TXN: {
    badge: 'text-purple-900 bg-purple-50 border-purple-200 font-bold',
    icon: Landmark,
  },
}

export default function Evidence() {
  const sources = useMemo<NexusSourceRecord[]>(() => Object.values(allSourceRecords), [])
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const copyId = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 1500)
    } catch {
      // clipboard unavailable
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2.5">
            <FileText className="h-6 w-6 text-blue-600" />
            Evidence &amp; Provenance Registry
          </h1>
          <p className="text-sm text-neutral-600 mt-1">
            Forensic chain-of-custody for seized documents, telecom CDR records, and banking logs with Section 63 BSA provenance.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-neutral-700 bg-neutral-50 p-3 rounded-lg border border-neutral-200">
        <FileSearch className="h-4 w-4 text-blue-600 shrink-0" />
        <span>All source records carry exact page/row locators and raw excerpts. Click any edge in the Network Explorer to trace its derivation chain via the Evidence Drawer.</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sources.map((item) => {
            const cfg = TYPE_CONFIG[item.source_type] || TYPE_CONFIG.FIR
            const Icon = cfg.icon
            return (
              <div key={item.id} className="rounded-xl border border-neutral-200 bg-white p-5 space-y-3.5 shadow-sm hover:border-neutral-300 transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <span className={`inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded border ${cfg.badge}`}>
                      <Icon className="h-3 w-3" />
                      {item.source_type}
                    </span>
                    <h3 className="text-base font-bold font-mono text-neutral-900 flex items-center gap-2">
                      {item.id}
                      <button
                        onClick={() => copyId(item.id)}
                        className="text-neutral-400 hover:text-neutral-800 p-1 rounded hover:bg-neutral-100 transition-colors"
                        title="Copy source ID"
                        aria-label={`Copy source ID ${item.id}`}
                      >
                        {copiedId === item.id ? (
                          <Check className="h-3.5 w-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </h3>
                  </div>
                  <span className="text-xs text-neutral-600 flex items-center gap-1 shrink-0 font-medium">
                    <Calendar className="h-3.5 w-3.5 text-neutral-400" />
                    {new Date(item.occurred_at).toLocaleString()}
                  </span>
                </div>

                <div className="rounded-lg bg-neutral-50 p-3 text-xs border border-neutral-200 space-y-2">
                  <div className="flex items-center gap-1.5 font-mono text-amber-900 bg-amber-50 px-2 py-1 rounded border border-amber-200 text-xs">
                    <MapPin className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                    <span>{item.locator}</span>
                  </div>

                  <blockquote className="border-l-4 border-blue-600 pl-3 text-xs leading-relaxed text-neutral-800 bg-white p-2.5 rounded-r">
                    "{item.raw_excerpt}"
                  </blockquote>
                </div>

                <div className="flex items-center justify-between text-[11px] text-neutral-600 pt-1 border-t border-neutral-200">
                  <span>Batch: <code className="text-neutral-800 font-mono font-medium">{item.batch_id}</code></span>
                  <span className="inline-flex items-center gap-1 text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-bold">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> Section 63 BSA Grounded
                  </span>
                </div>
              </div>
            )
          })}
        </div>
    </div>
  )
}
