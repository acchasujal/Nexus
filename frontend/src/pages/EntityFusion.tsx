/**
 * frontend/src/pages/EntityFusion.tsx
 *
 * Entity Fusion Workbench: side-by-side candidate records, match score,
 * reasons, conflicts, source links, and Confirm/Reject/Defer actions.
 */
import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  GitMerge, CheckCircle2, XCircle, Clock, FileText, AlertTriangle,
  ThumbsUp, PauseCircle, ShieldCheck, Network, Sparkles, ArrowRight,
} from 'lucide-react'
import { useResolutionCandidates, useDecideCandidate } from '@/hooks/useNexus'
import { DerivationBadge } from '@/components/nexus/DerivationBadge'
import { EvidenceConflictMatrix } from '@/components/nexus/EvidenceConflictMatrix'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import type { ResolutionCandidateRecord } from '@shared/contracts/api'

function RecordPanel({ title, record, accent }: { title: string; record: ResolutionCandidateRecord; accent: 'sky' | 'rose' }) {
  const isSky = accent === 'sky'
  const border = isSky ? 'border-sky-200' : 'border-rose-200'
  const chip = isSky ? 'bg-sky-50 text-sky-900 border-sky-200' : 'bg-rose-50 text-rose-900 border-rose-200'
  const headerBg = isSky ? 'bg-sky-50/40' : 'bg-rose-50/40'

  return (
    <div className={`rounded-xl border ${border} bg-white shadow-xs overflow-hidden flex flex-col justify-between`}>
      <div>
        <div className={`flex items-center justify-between px-4 py-3 border-b border-neutral-100 ${headerBg}`}>
          <span className="text-xs font-bold uppercase tracking-wider text-neutral-500">{title}</span>
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold border ${chip}`}>{record.entity_type}</span>
        </div>

        <div className="p-4 sm:p-5 space-y-4">
          <div>
            <h3 className="text-base sm:text-lg font-bold text-neutral-900">{record.label}</h3>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              {record.case_ids.map((cid) => (
                <span key={cid} className="inline-flex items-center gap-1 rounded-md bg-neutral-100 border border-neutral-200 px-2 py-0.5 font-mono text-[11px] font-bold text-neutral-800">
                  Case: {cid}
                </span>
              ))}
            </div>
          </div>

          {/* Properties List */}
          <dl className="space-y-2 text-xs sm:text-sm border-t border-neutral-100 pt-3">
            {Object.entries(record.properties).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3">
                <dt className="text-neutral-500 capitalize">{k.replaceAll('_', ' ')}</dt>
                <dd className="text-right font-semibold text-neutral-900">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      {/* Source Records */}
      <div className="p-4 sm:p-5 border-t border-neutral-100 bg-neutral-50/50">
        <h4 className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-neutral-500">
          <FileText className="h-3.5 w-3.5 text-blue-600" /> Grounding Source Records ({record.source_records.length})
        </h4>
        <ul className="mt-2.5 space-y-2">
          {record.source_records.map((s) => (
            <li key={s.id} className="rounded-lg border border-neutral-200 bg-white p-2.5 space-y-1 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="rounded bg-blue-50 border border-blue-200 px-1.5 py-0.2 font-mono text-[10px] font-bold text-blue-900">{s.source_type}</span>
                <code className="font-mono text-[10px] text-neutral-500">{s.id}</code>
              </div>
              <p className="font-mono text-[11px] text-amber-900 bg-amber-50/60 px-1.5 py-0.5 rounded border border-amber-200/80">{s.locator}</p>
              <blockquote className="border-l-2 border-neutral-300 pl-2 text-xs text-neutral-700 italic leading-relaxed">"{s.raw_excerpt}"</blockquote>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default function EntityFusion() {
  const [searchParams] = useSearchParams()
  const caseIdParam = searchParams.get('case_id')
  const candidateIdParam = searchParams.get('candidate_id') || searchParams.get('id')

  const { data: candidates, isLoading, error, refetch } = useResolutionCandidates()
  const decide = useDecideCandidate()
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [decisionError, setDecisionError] = useState<string | null>(null)

  useEffect(() => {
    if (candidateIdParam) {
      setSelectedCandidateId(candidateIdParam)
    } else if (caseIdParam && candidates) {
      const match = candidates.find(c => 
        c.left.case_ids.includes(caseIdParam) || 
        c.right.case_ids.includes(caseIdParam) ||
        (caseIdParam.includes('141') && (c.left.case_ids.includes('CASE-141') || c.right.case_ids.includes('CASE-141'))) ||
        (caseIdParam.includes('207') && (c.left.case_ids.includes('CASE-207') || c.right.case_ids.includes('CASE-207')))
      )
      if (match) {
        setSelectedCandidateId(match.id)
      }
    }
  }, [caseIdParam, candidateIdParam, candidates])

  const effectiveSelectedId = selectedCandidateId ?? candidates?.[0]?.id
  const candidate = candidates?.find((c) => c.id === effectiveSelectedId) ?? candidates?.[0]
  const decided = candidate && candidate.status !== 'PENDING'

  const submit = async (decision: 'CONFIRM' | 'REJECT' | 'DEFER') => {
    setDecisionError(null)
    try {
      await decide.mutateAsync({ id: candidate!.id, req: { decision, decided_by: 'Investigating Officer', note: note || undefined } })
    } catch (e) {
      setDecisionError(e instanceof Error ? e.message : 'Decision failed')
    }
  }

  // Auto-select first pending candidate when candidates load
  useEffect(() => {
    if (candidates && candidates.length > 0 && !selectedCandidateId) {
      const firstPending = candidates.find((c) => c.status === 'PENDING')
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedCandidateId((firstPending ?? candidates[0]).id)
    }
  }, [candidates, selectedCandidateId])

  if (isLoading) return <LoadingSkeleton layout="detail" />
  if (error) return <ErrorState message="Failed to load resolution candidates." onRetry={() => void refetch()} />
  if (!candidate) {
    return (
      <div className="rounded-xl border border-dashed border-neutral-300 bg-white py-16 text-center shadow-xs max-w-7xl mx-auto w-full">
        <GitMerge className="mx-auto h-12 w-12 text-neutral-400" />
        <h2 className="mt-3 text-lg font-semibold text-neutral-800">No pending entity matches</h2>
        <p className="mt-1 text-sm text-neutral-500">New candidates appear here as sources are ingested and compared.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={GitMerge}
        title="Entity Fusion Workbench"
        subtitle="Review each candidate match on deterministic evidence corroboration. Nothing merges without explicit investigator approval."
        actions={
          <div className="flex items-center gap-3 bg-white border border-neutral-200/90 rounded-xl px-4 py-2 shadow-2xs">
            <div className="text-right">
              <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Evidence Similarity</div>
              <div data-testid="match-score" className="text-xl sm:text-2xl font-extrabold text-emerald-700 tabular-nums" aria-label={`Match score ${(candidate.score * 100).toFixed(0)} out of 100`}>
                {(candidate.score * 100).toFixed(0)}/100
              </div>
            </div>
          </div>
        }
      />

      {/* Candidate Selector Tabs */}
      {candidates && candidates.length > 0 && (
        <div className="flex items-center gap-2 p-1.5 bg-neutral-100/70 rounded-xl border border-neutral-200/80 overflow-x-auto whitespace-nowrap" role="tablist" aria-label="Resolution candidates">
          <span className="text-[11px] font-bold text-neutral-500 uppercase tracking-wider px-2 shrink-0">Candidates ({candidates.length}):</span>
          {candidates.map((c) => {
            const isSelected = c.id === candidate.id
            const isConfirmed = c.status === 'CONFIRMED'
            const isRejected = c.status === 'REJECTED'
            const isPending = c.status === 'PENDING'
            const isCrossCase = c.left.case_ids[0] !== c.right.case_ids[0]
            return (
              <button
                key={c.id}
                role="tab"
                aria-selected={isSelected}
                onClick={() => {
                  setSelectedCandidateId(c.id)
                  setNote('')
                  setDecisionError(null)
                }}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all shrink-0 cursor-pointer ${
                  isSelected
                    ? 'bg-white text-neutral-950 shadow-xs border border-neutral-200 font-bold'
                    : 'text-neutral-600 hover:text-neutral-950 hover:bg-white/60'
                }`}
              >
                <span className="flex flex-col items-start text-left">
                  <span className="font-bold">#{candidates.indexOf(c) + 1} {c.left.label} ↔ {c.right.label}</span>
                  <span className="text-[9px] text-neutral-500 font-normal flex items-center gap-1">
                    <span>{c.left.case_ids[0]} · {c.right.case_ids[0]}</span>
                    {isCrossCase && <span className="font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-1 rounded text-[8px]">Cross-Case</span>}
                  </span>
                </span>
                <span className="rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.5 text-[10px] font-mono font-bold">
                  {(c.score * 100).toFixed(0)}%
                </span>
                {isConfirmed && <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-bold">Merged</span>}
                {isRejected && <span className="text-[10px] bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded font-bold">Rejected</span>}
                {isPending && <span className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded font-bold">Pending</span>}
              </button>
            )
          })}
        </div>
      )}

      {/* Cross-case context alert */}
      {candidate.left.case_ids[0] !== candidate.right.case_ids[0] && (
        <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-blue-50/70 border border-blue-200/80 text-blue-900 text-xs font-medium">
          <span className="rounded-md bg-blue-600 text-white text-[10px] font-bold uppercase px-2 py-0.5 tracking-wider shrink-0">Cross-Case Match</span>
          <span>Comparing record from <strong>{candidate.left.case_ids.join(', ')}</strong> with independent record from <strong>{candidate.right.case_ids.join(', ')}</strong>.</span>
        </div>
      )}

      {/* 2-Entity Comparison Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecordPanel title="Record A" record={candidate.left} accent="sky" />
        <RecordPanel title="Record B" record={candidate.right} accent="rose" />
      </div>

      {/* Evidentiary Contradiction & Agreement Matrix */}
      <EvidenceConflictMatrix candidate={candidate} />

      {/* Decision Section */}
      {decided ? (
        <section data-testid="post-decision" className={`rounded-xl border p-5 sm:p-6 shadow-xs ${
          candidate.status === 'CONFIRMED' ? 'border-emerald-200 bg-emerald-50/50 text-emerald-950'
            : candidate.status === 'REJECTED' ? 'border-red-200 bg-red-50/50 text-red-950'
              : 'border-amber-200 bg-amber-50/50 text-amber-950'
        }`} aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              {candidate.status === 'CONFIRMED' ? <CheckCircle2 className="h-8 w-8 text-emerald-600 shrink-0" />
                : candidate.status === 'REJECTED' ? <XCircle className="h-8 w-8 text-red-600 shrink-0" />
                  : <PauseCircle className="h-8 w-8 text-amber-600 shrink-0" />}
              <div>
                <h3 className="text-base sm:text-lg font-bold text-neutral-900">
                  Candidate {candidate.status === 'CONFIRMED' ? 'confirmed — entities fused in intelligence graph' : candidate.status.toLowerCase()}
                </h3>
                <p className="mt-0.5 text-xs sm:text-sm text-neutral-600">
                  Decision recorded by <strong>{candidate.decided_by}</strong> on{' '}
                  {candidate.decided_at ? new Date(candidate.decided_at).toLocaleString() : '—'} · Immutable audit entry written
                  <ShieldCheck className="ml-1 inline h-4 w-4 text-emerald-600" />
                </p>
              </div>
            </div>
            {candidate.status === 'CONFIRMED' && (
              <Link
                to={`/network?case_id=${encodeURIComponent(candidate.left.case_ids[0] || 'CASE-141')}&target_case_id=${encodeURIComponent(candidate.right.case_ids[0] || '')}&snapshot=after`}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs sm:text-sm font-bold text-white transition-colors hover:bg-emerald-700 shadow-xs"
              >
                <Network className="h-4 w-4" /> Replay Before → After on Canvas <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>
        </section>
      ) : (
        <section className="rounded-xl border border-neutral-200/90 bg-white p-5 sm:p-6 shadow-xs" aria-label="Decision controls">
          <h3 className="text-sm font-bold text-neutral-900">Investigator Decision &amp; Audit Trail</h3>
          <p className="mt-1 text-xs text-neutral-500">Your decision is cryptographically audited and drives every downstream graph link. Nothing is applied without your explicit choice.</p>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Decision rationale (optional) — e.g., Confirmed match based on matching phone MSISDN and father's name corroboration across FIR-141 and FIR-207."
            className="mt-3 w-full rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-xs sm:text-sm text-neutral-900 placeholder-neutral-400 focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 shadow-2xs"
            rows={2}
            aria-label="Decision note"
          />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={() => submit('CONFIRM')}
              disabled={decide.isPending}
              data-testid="confirm-fusion"
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-xs sm:text-sm font-bold text-white transition-colors hover:bg-emerald-700 shadow-xs disabled:opacity-50 cursor-pointer"
            >
              <CheckCircle2 className="h-4 w-4" /> Confirm Fusion
            </button>
            <button
              onClick={() => submit('REJECT')}
              disabled={decide.isPending}
              data-testid="reject-fusion"
              className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-5 py-2.5 text-xs sm:text-sm font-bold text-red-800 transition-colors hover:bg-red-100 disabled:opacity-50 cursor-pointer"
            >
              <XCircle className="h-4 w-4" /> Reject Match
            </button>
            <button
              onClick={() => submit('DEFER')}
              disabled={decide.isPending}
              data-testid="defer-fusion"
              className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 bg-white px-5 py-2.5 text-xs sm:text-sm font-bold text-neutral-700 transition-colors hover:bg-neutral-50 disabled:opacity-50 cursor-pointer"
            >
              <Clock className="h-4 w-4 text-neutral-500" /> Defer Decision
            </button>
            {decide.isPending && <span className="self-center text-xs sm:text-sm text-neutral-500">Writing immutable audit log…</span>}
          </div>
          {decisionError && <p role="alert" className="mt-3 text-xs sm:text-sm text-red-600 font-semibold">{decisionError}</p>}
        </section>
      )}
    </div>
  )
}
