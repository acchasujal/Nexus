import { useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FileText, Calendar, Copy, Check, Phone, Landmark, FileSearch, ShieldCheck, MapPin, Briefcase, X } from 'lucide-react'
import { allSourceRecords } from '@/lib/mocks/nexusFixture'
import { PageHeader } from '@/components/ui/PageHeader'
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
  const [searchParams, setSearchParams] = useSearchParams()
  const caseIdParam = searchParams.get('case_id')
  const allSources = useMemo<NexusSourceRecord[]>(() => Object.values(allSourceRecords), [])
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const sources = useMemo(() => {
    if (!caseIdParam) return allSources
    const cid = caseIdParam.toLowerCase()
    return allSources.filter(
      (item) =>
        (item.case_ids && item.case_ids.some((c) => c.toLowerCase() === cid)) ||
        item.id.toLowerCase().includes(cid) ||
        item.raw_excerpt.toLowerCase().includes(cid) ||
        item.locator.toLowerCase().includes(cid)
    )
  }, [allSources, caseIdParam])

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
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={FileText}
        title="Evidence &amp; Provenance Registry"
        subtitle="Source traceability for FIR records, telecom CDR logs, and banking wires. Each record carries exact file locators and raw excerpts under Section 63 BSA 2023."
        badge={
          caseIdParam ? (
            <div className="flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-900 border border-blue-200/80">
              <span>Scoped to {caseIdParam}</span>
              <button
                onClick={() => setSearchParams({})}
                className="hover:text-blue-950 ml-1 cursor-pointer"
                title="Clear filter"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : undefined
        }
      />

      {/* Compliance Note */}
      <div className="flex items-start gap-2.5 text-xs text-neutral-700 bg-neutral-50/80 p-3.5 rounded-xl border border-neutral-200/80">
        <FileSearch className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
        <span>All source records carry exact page/row locators and raw forensic excerpts. Click any edge in the Network Explorer to trace its derivation chain via the Evidence Drawer.</span>
      </div>

      {/* Evidence Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {sources.map((item) => {
          const cfg = TYPE_CONFIG[item.source_type] || TYPE_CONFIG.FIR
          const Icon = cfg.icon
          return (
            <div key={item.id} className="rounded-xl border border-neutral-200/90 bg-white p-5 space-y-3.5 shadow-xs hover:border-neutral-300 transition-all flex flex-col justify-between">
              <div className="space-y-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${cfg.badge}`}>
                      <Icon className="h-3 w-3" />
                      {item.source_type}
                    </span>
                    <h3 className="text-sm sm:text-base font-bold font-mono text-neutral-900 flex items-center gap-2">
                      {item.id}
                      <button
                        onClick={() => copyId(item.id)}
                        className="text-neutral-400 hover:text-neutral-700 transition-colors cursor-pointer"
                        title="Copy Evidence ID"
                      >
                        {copiedId === item.id ? (
                          <Check className="h-3.5 w-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </h3>
                  </div>
                  <span className="text-xs font-semibold text-neutral-500 tabular-nums">
                    {new Date(item.occurred_at).toLocaleDateString('en-IN', { dateStyle: 'medium' })}
                  </span>
                </div>

                <div className="rounded-lg bg-neutral-50 p-2.5 font-mono text-xs text-amber-900 border border-neutral-200/80">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 block mb-0.5">Locator:</span>
                  {item.locator}
                </div>

                <blockquote className="border-l-2 border-blue-500 pl-3 text-xs text-neutral-700 italic leading-relaxed">
                  "{item.raw_excerpt}"
                </blockquote>
              </div>

              <div className="pt-2 border-t border-neutral-100 flex items-center justify-between text-xs text-neutral-500 font-medium">
                <span>Batch: <code className="font-mono text-neutral-700">{item.batch_id}</code></span>
                {item.case_ids && item.case_ids.length > 0 && (
                  <span>Cases: <strong className="text-neutral-800">{item.case_ids.join(', ')}</strong></span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
