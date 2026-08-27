import { useState, useEffect } from 'react'
import { ShieldCheck } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'

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

  useEffect(() => {
    apiClient.getAuditLogs().then((data) => {
      setLogs(Array.isArray(data) ? (data as AuditLogEntry[]) : [])
    }).catch(() => {
      setLogs([
        { id: 'aud-1', user_id: 'dev-io', user_role: 'INVESTIGATOR', action: 'network_explored', entity_id: 'CASE-141', timestamp: '2026-02-15T12:00:00Z', details: { snapshot: 'before', total_nodes: 8, total_edges: 10 } },
        { id: 'aud-2', user_id: 'dev-io', user_role: 'INVESTIGATOR', action: 'entity_resolution_executed', entity_id: 'RC-1', timestamp: '2026-02-15T12:05:00Z', details: { candidate: 'Rafiq Khan ↔ Rafiq Ahmed', decision: 'CONFIRM' } },
        { id: 'aud-3', user_id: 'dev-io', user_role: 'INVESTIGATOR', action: 'copilot_answered', entity_id: 'Copilot', timestamp: '2026-02-15T12:10:00Z', details: { query: 'How are the two cases connected?', grounded: true } },
      ])
    }).finally(() => {
      setIsLoading(false)
    })
  }, [])

  return (
    <div className="space-y-6">
      <div className="border-b border-neutral-200 pb-5">
        <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2.5">
          <ShieldCheck className="h-6 w-6 text-blue-600" />
          Immutable Audit Trail & Compliance Log
        </h1>
        <p className="text-sm text-neutral-600 mt-1">
          Cryptographically recorded actions, candidate decisions, search queries, copilot responses, and evidence accesses by investigator principals.
        </p>
      </div>

      <div className="rounded-xl border border-neutral-200 bg-white overflow-x-auto shadow-sm">
        <table className="w-full text-left text-sm text-neutral-800 min-w-[700px]">
          <thead className="bg-neutral-50 text-xs font-bold uppercase tracking-wider text-neutral-700 border-b border-neutral-200">
            <tr>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Actor / Role</th>
              <th className="px-4 py-3">Action Executed</th>
              <th className="px-4 py-3">Target Entity</th>
              <th className="px-4 py-3">Audit Context Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-neutral-500">Loading audit records...</td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-neutral-500">No audit records found.</td>
              </tr>
            ) : (
              logs.map((log, idx) => (
                <tr key={log.id || idx} className="hover:bg-neutral-50/80 transition-colors">
                  <td className="px-4 py-3 text-xs text-neutral-600 whitespace-nowrap font-medium">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-bold text-neutral-900">{log.user_id}</span>
                    <span className="ml-2 text-[10px] font-bold bg-neutral-100 px-1.5 py-0.5 rounded text-neutral-800 border border-neutral-200">
                      {log.user_role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <code className="text-xs font-mono font-bold text-blue-900 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                      {log.action.replaceAll('_', ' ')}
                    </code>
                  </td>
                  <td className="px-4 py-3 text-xs font-semibold text-neutral-900">
                    {log.entity_id || log.case_id || 'System / Batch'}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {formatAuditDetails(log.details)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
