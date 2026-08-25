/**
 * frontend/src/pages/EntityFusion.tsx
 *
 * Entity Fusion Workbench: side-by-side candidate records, match score,
 * reasons, conflicts, source links, and Confirm/Reject/Defer actions.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  GitMerge, CheckCircle2, XCircle, Clock, FileText, AlertTriangle,
  ThumbsUp, PauseCircle, ShieldCheck, Network,
} from 'lucide-react'
import { useResolutionCandidates, useDecideCandidate } from '@/hooks/useNexus'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import type { ResolutionCandidateRecord } from '@shared/contracts/api'

function RecordPanel({ title, record, accent }: { title: string; record: ResolutionCandidateRecord; accent: 'sky' | 'rose' }) {
  const border = accent === 'sky' ? 'border-sky-300' : 'border-rose-300'
  const chip = accent === 'sky' ? 'bg-sky-100 text-sky-900 border border-sky-200' : 'bg-rose-100 text-rose-900 border border-rose-200'
  return (
    <div className={`rounded-xl border ${border} bg-white p-4 shadow-sm`}>
      <div className="flex items-center justify-between">
        <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${chip}`}>{title}</span>
        <code className="font-mono text-[10px] text-neutral-500 font-semibold">{record.node_id}</code>
      </div>
      <h3 className="mt-2 text-lg font-bold text-neutral-900">{record.label}</h3>
      <p className="mt-0.5 text-xs text-neutral-500 font-medium">{record.case_ids.join(', ')}</p>
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
  const { data: candidates, isLoading, error, refetch } = useResolutionCandidates()
  const decide = useDecideCandidate()
  const [note, setNote] = useState('')
  const [decisionError, setDecisionError] = useState<string | null>(null)

  const candidate = candidates?.[0]
  const decided = candidate && candidate.status !== 'PENDING'

  const submit = async (decision: 'CONFIRM' | 'REJECT' | 'DEFER') => {
    setDecisionError(null)
    try {
      await decide.mutateAsync({ id: candidate!.id, req: { decision, decided_by: 'IO Demo', note: note || undefined } })
    } catch (e) {
      setDecisionError(e instanceof Error ? e.message : 'Decision failed')
    }
  }

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
          <div data-testid="match-score" className="text-3xl font-extrabold text-emerald-700" aria-label={`Match score ${(candidate.score * 100).toFixed(0)} percent`}>
            {(candidate.score * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RecordPanel title="Record A" record={candidate.left} accent="sky" />
        <RecordPanel title="Record B" record={candidate.right} accent="rose" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 shadow-sm" aria-label="Match reasons">
          <h3 className="flex items-center gap-2 text-sm font-bold text-emerald-900">
            <ThumbsUp className="h-4 w-4 text-emerald-600" /> Why they might match
          </h3>
          <ul className="mt-3 space-y-2">
            {candidate.reasons.map((r) => (
              <li key={r.field} className="rounded-lg border border-emerald-100 bg-white p-3 text-sm shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold capitalize text-neutral-900">{r.field.replaceAll('_', ' ')}</span>
                  <span className="rounded bg-emerald-100 border border-emerald-200 px-1.5 py-0.5 font-mono text-[10px] font-bold text-emerald-800">+{r.weight.toFixed(2)}</span>
                </div>
                <p className="mt-1 text-xs text-neutral-600">{r.detail}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 shadow-sm" aria-label="Conflicts">
          <h3 className="flex items-center gap-2 text-sm font-bold text-amber-900">
            <AlertTriangle className="h-4 w-4 text-amber-600" /> Conflicting fields — judge these yourself
          </h3>
          <ul className="mt-3 space-y-2">
            {candidate.conflicts.map((c) => (
              <li key={c.field} className="rounded-lg border border-amber-100 bg-white p-3 text-sm shadow-xs">
                <span className="font-bold capitalize text-neutral-900">{c.field.replaceAll('_', ' ')}</span>
                <div className="mt-1.5 grid grid-cols-2 gap-2 text-xs">
                  <span className="rounded bg-sky-50 border border-sky-200 px-2 py-1 text-sky-900 font-medium">A: {c.left_value}</span>
                  <span className="rounded bg-rose-50 border border-rose-200 px-2 py-1 text-rose-900 font-medium">B: {c.right_value}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>

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
              <Link to="/network" className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-emerald-700 shadow-sm">
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
