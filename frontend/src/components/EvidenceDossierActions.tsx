import { useState } from 'react'
import { CheckCircle2, Download, FileText, ShieldCheck, XCircle } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import type { NexusDossierRequest, NexusDossierResponse } from '@shared/contracts/api'

export function EvidenceDossierActions({ request }: { request: NexusDossierRequest }) {
  const [dossier, setDossier] = useState<NexusDossierResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [verification, setVerification] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)

  const downloadPdf = async (generated: NexusDossierResponse) => {
    const blob = await apiClient.downloadEvidenceDossier(generated.dossier_id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `NEXUS_Evidence_Dossier_${generated.dossier_id}.pdf`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }

  const generate = async () => {
    setBusy(true)
    setError(null)
    try {
      const generated = await apiClient.generateEvidenceDossier(request)
      await downloadPdf(generated)
      setDossier(generated)
      setVerification(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Dossier generation or download failed')
    } finally {
      setBusy(false)
    }
  }

  const download = async () => {
    if (!dossier) return
    setBusy(true)
    setError(null)
    try {
      await downloadPdf(dossier)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Dossier download failed')
    } finally {
      setBusy(false)
    }
  }

  const verify = async () => {
    if (!dossier) return
    setBusy(true)
    setError(null)
    try {
      const [pdfResult, evidenceResult] = await Promise.all([
        apiClient.verifyEvidenceDossier(dossier.dossier_id),
        apiClient.verifyEvidence({ evidence_ids: dossier.evidence_ids, dossier_id: dossier.dossier_id }),
      ])
      setVerification(pdfResult.verified && evidenceResult.overall_verified)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Integrity verification failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2">
      {!dossier ? (
        <button onClick={() => void generate()} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50">
          <FileText className="h-4 w-4" /> {busy ? 'Generating...' : 'Generate Evidence Dossier'}
        </button>
      ) : (
        <div className="space-y-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-950">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-bold"><CheckCircle2 className="h-4 w-4" /> Dossier generated <span>{dossier.evidence_ids.length} evidence records included</span></div>
          <div className="font-mono break-all">SHA-256: {dossier.pdf_sha256}</div>
          <div className="flex flex-wrap gap-2 pt-1">
            <button onClick={() => void download()} className="inline-flex items-center gap-1 rounded border border-emerald-300 bg-white px-2 py-1 font-bold hover:bg-emerald-100"><Download className="h-3.5 w-3.5" /> Download PDF</button>
            <button onClick={() => void verify()} disabled={busy} className="inline-flex items-center gap-1 rounded border border-emerald-300 bg-white px-2 py-1 font-bold hover:bg-emerald-100 disabled:opacity-50"><ShieldCheck className="h-3.5 w-3.5" /> Verify Integrity</button>
          </div>
          {verification !== null && <div className={`flex items-center gap-1 font-bold ${verification ? 'text-emerald-800' : 'text-red-800'}`}>{verification ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />} {verification ? 'Integrity Verified' : 'Integrity Mismatch'}</div>}
        </div>
      )}
      {error && <p className="text-xs font-semibold text-red-700">{error}</p>}
    </div>
  )
}