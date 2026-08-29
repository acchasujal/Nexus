import { useState, useEffect } from 'react'
import { ShieldCheck, AlertTriangle } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'

interface AuditLogEntry {
  id: string
  user_id: string
  user_role: string
  action: string
  entity_id?: string
  case_id?: string
  timestamp: string
  details?: Record<string, unknown>
}

function formatAuditDetails(details?: Record<string, unknown>): React.ReactNode {
  if (!details || Object.keys(details).length === 0) {
    return <span className="text-neutral-400 italic text-xs">No extra metadata</span>
  }

  return (
    <div className="flex flex-wrap gap-1.5 max-w-md">
      {Object.entries(details).map(([k, v]) => {
        let displayVal = String(v)
        if (typeof v === 'boolean') displayVal = v ? 'true' : 'false'
        else if (Array.isArray(v)) displayVal = v.join(', ')
        else if (typeof v === 'object' && v !== null) displayVal = JSON.stringify(v)

        const formattedKey = k.replaceAll('_', ' ')
        return (
          <span
            key={k}
            className="inline-flex items-center gap-1 text-[11px] bg-neutral-100 border border-neutral-200 px-2 py-0.5 rounded-md text-neutral-800 font-medium"
          >
            <span className="text-neutral-500 capitalize">{formattedKey}:</span>
            <span className="font-semibold text-neutral-900">{displayVal}</span>
          </span>
        )
      })}
    </div>
  )
}

export default function Audit() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)

  useEffect(() => {
    apiClient.getAuditLogs().then((data) => {
      setFetchError(null)
      setLogs(Array.isArray(data) ? (data as AuditLogEntry[]) : [])
    }).catch((err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Unable to load audit records'
      setFetchError(msg)
      setLogs([])
    }).finally(() => {
      setIsLoading(false)
    })
  }, [])

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={ShieldCheck}
        title="Immutable Audit Trail &amp; Compliance Log"
        subtitle="Cryptographically recorded actions, candidate decisions, search queries, copilot responses, and evidence accesses by investigator principals."
      />

      {/* Audit Log Table Container */}
      <SectionCard noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm text-neutral-800 min-w-[700px]">
            <thead className="bg-neutral-50/80 text-[11px] font-bold uppercase tracking-wider text-neutral-700 border-b border-neutral-200/80">
              <tr>
                <th className="px-4 py-3.5">Timestamp</th>
                <th className="px-4 py-3.5">Actor / Role</th>
                <th className="px-4 py-3.5">Action Executed</th>
                <th className="px-4 py-3.5">Target Entity</th>
                <th className="px-4 py-3.5">Audit Context Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-neutral-500">Loading audit records...</td>
                </tr>
              ) : fetchError ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center">
                    <div className="flex flex-col items-center gap-2 text-amber-800">
                      <AlertTriangle className="h-6 w-6 text-amber-500" />
                      <p className="font-semibold text-sm">Audit log unavailable</p>
                      <p className="text-xs text-neutral-600 max-w-md">{fetchError}</p>
                    </div>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-neutral-500">No audit events recorded yet.</td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-neutral-50/70 transition-colors">
                    <td className="px-4 py-3 text-xs text-neutral-500 font-mono tabular-nums whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString('en-IN', {
                        dateStyle: 'short',
                        timeStyle: 'medium',
                      })}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="font-semibold text-neutral-900">{log.user_id}</div>
                      <div className="text-[11px] text-blue-700 font-bold">{log.user_role}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono font-bold bg-neutral-100 border border-neutral-200 text-neutral-800">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap font-mono text-xs text-neutral-700">
                      {log.entity_id || log.case_id || '—'}
                    </td>
                    <td className="px-4 py-3">
                      {formatAuditDetails(log.details)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  )
}
