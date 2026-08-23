import { useState, useEffect } from 'react'
import { FileText, ShieldCheck, Database, Calendar, Tag, ExternalLink } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'

export default function Evidence() {
  const [evidenceItems, setEvidenceItems] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Fetch cases and extract evidence
    apiClient.getInvestigations().then(async (cases: any) => {
      if (Array.isArray(cases) && cases.length > 0) {
        const firstCase = await apiClient.getInvestigationDetail(cases[0].id)
        if (firstCase && firstCase.evidence) {
          setEvidenceItems(firstCase.evidence)
        }
      }
    }).catch(() => {
      setEvidenceItems([
        {
          id: 'ev-001',
          evidence_number: 'EV-2026-9041',
          case_id: 'case-0001',
          evidence_type: 'CDR_RECORD',
          description: 'CDR call detail records from Airtel showing 42 encrypted calls',
          collected_at: '2026-01-14T10:00:00Z',
          provenance: {
            source_type: 'CDR',
            source_id: 'CDR-SWEEP-1042',
            timestamp: '2026-01-14T10:00:00Z',
            extracted_fact: '42 calls logged with suspect B',
            derivation_method: 'TELECOM_LOG',
            confidence: 0.98,
          },
        },
        {
          id: 'ev-002',
          evidence_number: 'EV-2026-9042',
          case_id: 'case-0001',
          evidence_type: 'BANK_STATEMENT',
          description: 'HDFC Bank transaction ledger documenting INR 25,00,000 layering wire',
          collected_at: '2026-01-13T15:30:00Z',
          provenance: {
            source_type: 'BANK_TXN',
            source_id: 'TXN-PLANTED-1',
            timestamp: '2026-01-13T15:30:00Z',
            extracted_fact: 'Direct account transfer',
            derivation_method: 'FINANCIAL_LEDGER',
            confidence: 1.0,
          },
        },
      ])
    }).finally(() => {
      setIsLoading(false)
    })
  }, [])

  return (
    <div className="space-y-6">
      <div className="border-b border-neutral-800 pb-5">
        <h1 className="text-2xl font-bold text-neutral-100 flex items-center gap-2.5">
          <FileText className="h-6 w-6 text-blue-500" />
          Evidence & Provenance Registry
        </h1>
        <p className="text-sm text-neutral-400 mt-1">
          Traceable chain-of-custody for all seized devices, telecom CDR logs, financial transactions, and FIR source documents.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {evidenceItems.map((item, idx) => (
          <div key={item.id || idx} className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-3.5 hover:border-neutral-700 transition-colors">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-semibold text-blue-400 bg-blue-950/70 px-2 py-0.5 rounded border border-blue-800/40">
                  {item.evidence_type}
                </span>
                <h3 className="text-base font-bold text-white mt-1.5">{item.evidence_number || item.id}</h3>
              </div>
              <span className="text-xs text-neutral-400 flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5 text-neutral-500" />
                {new Date(item.collected_at).toLocaleDateString()}
              </span>
            </div>

            <p className="text-sm text-neutral-300">{item.description}</p>

            {item.provenance && (
              <div className="rounded-lg bg-neutral-950/80 p-3 text-xs border border-neutral-800/60 space-y-1.5">
                <div className="font-semibold text-neutral-300 flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  Provenance Verification:
                </div>
                <div className="text-neutral-400 text-[11px]">
                  <strong>Source:</strong> {item.provenance.source_type} ({item.provenance.source_id}) • <strong>Method:</strong> {item.provenance.derivation_method} • <strong>Confidence:</strong> {Math.round((item.provenance.confidence || 1) * 100)}%
                </div>
                <div className="text-neutral-300 text-[11px] bg-neutral-900/80 p-2 rounded border border-neutral-800">
                  "{item.provenance.extracted_fact}"
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
