import { CheckCircle2, AlertTriangle, HelpCircle, ShieldAlert } from 'lucide-react'
import type { ResolutionCandidate } from '@shared/contracts/api'

interface ConflictMatrixProps {
  candidate: ResolutionCandidate
}

export function EvidenceConflictMatrix({ candidate }: ConflictMatrixProps) {
  const leftProps = candidate.left.properties || {}
  const rightProps = candidate.right.properties || {}

  // Find all field keys across both records
  const allKeys = Array.from(new Set([...Object.keys(leftProps), ...Object.keys(rightProps)]))
    .filter((k) => !['role', 'case_id', 'case_ids', 'source_records'].includes(k))

  const conflictFields = new Set(candidate.conflicts.map((c) => c.field))
  const reasonFields = new Set(candidate.reasons.map((r) => r.field))

  // Group fields into 3 explicit categories: AGREES, CONFLICTS, UNKNOWN
  const agrees = candidate.reasons.map((r) => ({
    field: r.field,
    label: r.field.replaceAll('_', ' '),
    detail: r.detail,
    weight: r.weight,
    leftVal: String(leftProps[r.field] || '—'),
    rightVal: String(rightProps[r.field] || '—'),
  }))

  const conflicts = candidate.conflicts.map((c) => ({
    field: c.field,
    label: c.field.replaceAll('_', ' '),
    leftVal: c.left_value,
    rightVal: c.right_value,
  }))

  const unknowns = allKeys
    .filter((k) => !conflictFields.has(k) && !reasonFields.has(k))
    .map((k) => ({
      field: k,
      label: k.replaceAll('_', ' '),
      leftVal: leftProps[k] ? String(leftProps[k]) : null,
      rightVal: rightProps[k] ? String(rightProps[k]) : null,
    }))
    .filter((u) => !u.leftVal || !u.rightVal || u.leftVal !== u.rightVal)

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-neutral-200 pb-3">
        <div>
          <h3 className="text-base font-bold text-neutral-900 flex items-center gap-2">
            <ShieldAlert className="h-4.5 w-4.5 text-blue-600" />
            Evidentiary Contradiction &amp; Agreement Matrix
          </h3>
          <p className="text-xs text-neutral-600 mt-0.5">
            Transparent breakdown of corroborating facts, explicit discrepancies, and unverified data points.
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-bold">
          <span className="rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5">
            {agrees.length} Agrees
          </span>
          <span className="rounded-md bg-amber-50 text-amber-900 border border-amber-200 px-2 py-0.5">
            {conflicts.length} Conflicts
          </span>
          <span className="rounded-md bg-neutral-100 text-neutral-700 border border-neutral-200 px-2 py-0.5">
            {unknowns.length} Unverified
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 1. Verified Agreements */}
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/40 p-3.5 space-y-2.5">
          <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-900 uppercase tracking-wider">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            Corroborated Facts ({agrees.length})
          </div>
          {agrees.length === 0 ? (
            <p className="text-xs text-neutral-500 italic">No corroborating fields found.</p>
          ) : (
            <ul className="space-y-2">
              {agrees.map((item) => (
                <li key={item.field} className="p-2.5 bg-white rounded-md border border-emerald-100 shadow-2xs text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-neutral-900 capitalize">{item.label}</span>
                    <span className="text-[10px] font-mono font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                      +{item.weight.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-[11px] text-neutral-600">{item.detail}</div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 2. Flagged Conflicts */}
        <div className="rounded-lg border border-amber-200 bg-amber-50/40 p-3.5 space-y-2.5">
          <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900 uppercase tracking-wider">
            <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
            Discrepancies / Conflicts ({conflicts.length})
          </div>
          {conflicts.length === 0 ? (
            <p className="text-xs text-neutral-500 italic">No conflicting fields detected.</p>
          ) : (
            <ul className="space-y-2">
              {conflicts.map((item) => (
                <li key={item.field} className="p-2.5 bg-white rounded-md border border-amber-200 shadow-2xs text-xs space-y-1.5">
                  <div className="font-bold text-neutral-900 capitalize flex items-center justify-between">
                    <span>{item.label}</span>
                    <span className="text-[9px] font-bold text-amber-800 bg-amber-100 px-1 py-0.5 rounded uppercase">Mismatch</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                    <div className="bg-sky-50 border border-sky-200 p-1.5 rounded text-sky-950">
                      <div className="text-[9px] font-bold text-sky-700 uppercase">Rec A</div>
                      <div className="font-medium truncate">{item.leftVal}</div>
                    </div>
                    <div className="bg-rose-50 border border-rose-200 p-1.5 rounded text-rose-950">
                      <div className="text-[9px] font-bold text-rose-700 uppercase">Rec B</div>
                      <div className="font-medium truncate">{item.rightVal}</div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 3. Unknown / Unverified Data */}
        <div className="rounded-lg border border-neutral-200 bg-neutral-50/60 p-3.5 space-y-2.5">
          <div className="flex items-center gap-1.5 text-xs font-bold text-neutral-700 uppercase tracking-wider">
            <HelpCircle className="h-4 w-4 text-neutral-500 shrink-0" />
            Unverified / Partial ({unknowns.length})
          </div>
          {unknowns.length === 0 ? (
            <p className="text-xs text-neutral-500 italic">All key identity fields present.</p>
          ) : (
            <ul className="space-y-2">
              {unknowns.map((item) => (
                <li key={item.field} className="p-2.5 bg-white rounded-md border border-neutral-200 shadow-2xs text-xs space-y-1">
                  <div className="font-bold text-neutral-800 capitalize flex items-center justify-between">
                    <span>{item.label}</span>
                    <span className="text-[9px] font-semibold text-neutral-500 bg-neutral-100 px-1 py-0.5 rounded">Unverified</span>
                  </div>
                  <div className="text-[11px] text-neutral-600">
                    {item.leftVal ? `Present in Record A (${item.leftVal})` : 'Missing in Record A'} •{' '}
                    {item.rightVal ? `Present in Record B (${item.rightVal})` : 'Missing in Record B'}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
