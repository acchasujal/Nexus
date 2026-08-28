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
  ThumbsUp, PauseCircle, ShieldCheck, Network,
} from 'lucide-react'
import { useResolutionCandidates, useDecideCandidate } from '@/hooks/useNexus'
import { DerivationBadge } from '@/components/nexus/DerivationBadge'
import { EvidenceConflictMatrix } from '@/components/nexus/EvidenceConflictMatrix'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import type { ResolutionCandidateRecord } from '@shared/contracts/api'

function RecordPanel({ title, record, accent }: { title: string; record: ResolutionCandidateRecord; accent: 'sky' | 'rose' }) {
  const border = accent === 'sky' ? 'border-sky-300' : 'border-rose-300'
  const chip = accent === 'sky' ? 'bg-sky-100 text-sky-900 border border-sky-200' : 'bg-rose-100 text-rose-900 border border-rose-200'
  return (
    <div className={`rounded-xl border ${border} bg-white p-4 shadow-sm`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-neutral-500">{title}</span>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${chip}`}>{record.entity_type}</span>
      </div>
      <h3 className="mt-2 text-base font-bold text-neutral-900">{record.label}</h3>
      <div className="mt-1 flex flex-wrap items-center gap-1.5">
        {record.case_ids.map((cid) => (
          <span key={cid} className="inline-flex items-center gap-1 rounded bg-neutral-100 border border-neutral-300 px-2 py-0.5 font-mono text-[11px] font-bold text-neutral-800">
            Case: {cid}
          </span>
        ))}
      </div>
      <dl className="mt-3 space-y-1.5 text-sm">
        {Object.entries(record.properties).map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3">
            <dt className="text-neutral-500 capitalize">{k.replaceAll('_', ' ')}</dt>
            <dd className="text-right font-semibold text-neutral-900">{String(v)}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4">
        <h4 className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-neutral-500">
          <FileText className="h-3.5 w-3.5 text-blue-600" /> Source records
        </h4>
        <ul className="mt-2 space-y-1.5">
          {record.source_records.map((s) => (
            <li key={s.id} className="rounded-lg border border-neutral-200 bg-neutral-50 p-2.5 space-y-1">
              <div className="flex items-center justify-between">
                <span className="rounded bg-blue-100 border border-blue-200 px-1.5 py-0.5 font-mono text-[10px] font-bold text-blue-900">{s.source_type}</span>
                <code className="font-mono text-[10px] text-neutral-500">{s.id}</code>
              </div>
              <p className="font-mono text-[11px] text-amber-900 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">{s.locator}</p>
              <blockquote className="border-l-2 border-neutral-300 pl-2 text-xs text-neutral-700 italic">"{s.raw_excerpt}"</blockquote>
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
      <div className="rounded-xl border border-dashed border-neutral-300 bg-white py-16 text-center shadow-xs">
        <GitMerge className="mx-auto h-12 w-12 text-neutral-400" />
        <h2 className="mt-3 text-lg font-semibold text-neutral-800">No pending entity matches</h2>
        <p className="mt-1 text-sm text-neutral-500">New candidates appear here as sources are ingested and compared.</p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 border-b border-neutral-200 pb-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="flex items-center gap-2.5 text-2xl font-bold text-neutral-900">
            <GitMerge className="h-6 w-6 text-blue-600" /> Entity Fusion Workbench
          </h1>
          <p className="mt-1 text-sm text-neutral-600">Review each candidate match on its evidence. Nothing merges automatically.</p>
        </div>
        <div className="text-right">
          <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Match score</div>
          <div data-testid="match-score" className="text-2xl sm:text-3xl font-extrabold text-emerald-700" aria-label={`Match score ${(candidate.score * 100).toFixed(0)} out of 100`}>
            {(candidate.score * 100).toFixed(0)}/100
          </div>
          <div className="text-[10px] text-neutral-500 max-w-[200px] text-right mt-0.5">
            Weighted evidence similarity score; not probability of identity.
          </div>
        </div>
      </div>

      {/* Candidate Selector Tabs */}
      {candidates && candidates.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 p-2 bg-neutral-100/80 rounded-xl border border-neutral-200" role="tablist" aria-label="Resolution candidates">
          <span className="text-xs font-bold text-neutral-500 uppercase tracking-wider px-2">Candidates ({candidates.length}):</span>
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
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isSelected
                    ? 'bg-white text-neutral-950 shadow-sm border border-neutral-300 ring-1 ring-neutral-300 font-bold'
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
                <span className="rounded bg-emerald-100 text-emerald-800 px-1.5 py-0.5 text-[10px] font-mono font-bold">
                  {(c.score * 100).toFixed(0)}/100
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
        <div className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-blue-50 border border-blue-200 text-blue-900 text-xs font-semibold">
          <span className="rounded bg-blue-600 text-white text-[10px] font-bold uppercase px-1.5 py-0.5 tracking-wider">Cross-Case Match</span>
          <span>Comparing record from <strong>{candidate.left.case_ids.join(', ')}</strong> with independent record from <strong>{candidate.right.case_ids.join(', ')}</strong>.</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RecordPanel title="Record A" record={candidate.left} accent="sky" />
        <RecordPanel title="Record B" record={candidate.right} accent="rose" />
      </div>

      {/* Evidentiary Contradiction & Agreement Matrix */}
      <EvidenceConflictMatrix candidate={candidate} />

      {decided ? (
        <section data-testid="post-decision" className={`rounded-xl border p-5 shadow-sm ${
          candidate.status === 'CONFIRMED' ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
            : candidate.status === 'REJECTED' ? 'border-red-300 bg-red-50 text-red-950'
              : 'border-amber-300 bg-amber-50 text-amber-950'
        }`} aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {candidate.status === 'CONFIRMED' ? <CheckCircle2 className="h-8 w-8 text-emerald-600" />
                : candidate.status === 'REJECTED' ? <XCircle className="h-8 w-8 text-red-600" />
                  : <PauseCircle className="h-8 w-8 text-amber-600" />}
              <div>
                <h3 className="text-lg font-bold text-neutral-900">
                  Candidate {candidate.status === 'CONFIRMED' ? 'confirmed — entities fused' : candidate.status.toLowerCase()}
                </h3>
                <p className="mt-0.5 text-sm text-neutral-700">
                  Decision recorded by <strong>{candidate.decided_by}</strong> on{' '}
                  {candidate.decided_at ? new Date(candidate.decided_at).toLocaleString() : '—'} · audit entry written
                  <ShieldCheck className="ml-1 inline h-3.5 w-3.5 text-emerald-600" />
                </p>
              </div>
            </div>
            {candidate.status === 'CONFIRMED' && (
              <Link
                to={`/network?case_id=${encodeURIComponent(candidate.left.case_ids[0] || 'CASE-141')}&target_case_id=${encodeURIComponent(candidate.right.case_ids[0] || '')}&snapshot=after`}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-emerald-700 shadow-sm"
              >
                <Network className="h-4 w-4" /> Replay Before → After
              </Link>
            )}
          </div>
        </section>
      ) : (
        <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm" aria-label="Decision controls">
          <h3 className="text-sm font-bold text-neutral-900">Investigator decision</h3>
          <p className="mt-1 text-xs text-neutral-600">Your decision is audited and drives every downstream network change. Nothing is applied until you choose.</p>
          <textarea value={note} onChange={(e) => setNote(e.target.value)}
            placeholder="Decision note (optional) — e.g. DOB difference is a day/month transposition, same father's name."
            className="mt-3 w-full rounded-lg border border-neutral-300 bg-neutral-50 p-3 text-sm text-neutral-900 placeholder-neutral-500 focus:bg-white focus:border-blue-600 focus:outline-none" rows={2} aria-label="Decision note" />
          <div className="mt-4 flex flex-wrap gap-3">
            <button onClick={() => submit('CONFIRM')} disabled={decide.isPending} data-testid="confirm-fusion"
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-bold text-white transition-colors hover:bg-emerald-700 shadow-sm disabled:opacity-50">
              <CheckCircle2 className="h-4 w-4" /> Confirm fusion
            </button>
            <button onClick={() => submit('REJECT')} disabled={decide.isPending} data-testid="reject-fusion"
              className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 px-5 py-2.5 text-sm font-bold text-red-800 transition-colors hover:bg-red-100 disabled:opacity-50">
              <XCircle className="h-4 w-4" /> Reject
            </button>
            <button onClick={() => submit('DEFER')} disabled={decide.isPending} data-testid="defer-fusion"
              className="inline-flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-5 py-2.5 text-sm font-bold text-amber-900 transition-colors hover:bg-amber-100 disabled:opacity-50">
              <Clock className="h-4 w-4" /> Defer
            </button>
            {decide.isPending && <span className="self-center text-sm text-neutral-600">Recording decision…</span>}
          </div>
          {decisionError && <p role="alert" className="mt-3 text-sm text-red-600 font-semibold">{decisionError}</p>}
        </section>
      )}
    </div>
  )
}
