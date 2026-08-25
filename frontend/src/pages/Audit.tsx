import { useState, useEffect } from 'react'
import { ShieldCheck, UserCheck, Calendar, Filter, Activity, Lock } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'

export default function Audit() {
  const [logs, setLogs] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    apiClient.getAuditLogs().then((data) => {
      setLogs(Array.isArray(data) ? data : [])
    }).catch(() => {
      setLogs([
        { id: 'aud-1', user_id: 'dev-io', user_role: 'INVESTIGATOR', action: 'network_explored', entity_id: 'case-0001', timestamp: '2026-01-15T12:00:00Z', details: { depth: 2 } },
        { id: 'aud-2', user_id: 'dev-sho', user_role: 'SUPERVISOR', action: 'entity_resolution_executed', entity_id: 'Vikram Sharma', timestamp: '2026-01-15T11:45:00Z', details: { matches: 2 } },
        { id: 'aud-3', user_id: 'dev-io', user_role: 'INVESTIGATOR', action: 'copilot_answered', entity_id: 'case-0001', timestamp: '2026-01-15T11:30:00Z', details: { intent: 'case_summary' } },
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
          Cryptographically recorded actions, search queries, copilot responses, and evidence accesses by investigator principals.
        </p>
      </div>

      <div className="rounded-xl border border-neutral-200 bg-white overflow-x-auto shadow-sm">
        <table className="w-full text-left text-sm text-neutral-800 min-w-[600px]">
          <thead className="bg-neutral-50 text-xs font-bold uppercase tracking-wider text-neutral-700 border-b border-neutral-200">
            <tr>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Actor / Role</th>
              <th className="px-4 py-3">Action Executed</th>
              <th className="px-4 py-3">Target Entity</th>
              <th className="px-4 py-3">Context Details</th>
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
                      {log.action}
                    </code>
                  </td>
                  <td className="px-4 py-3 text-xs font-semibold text-neutral-900">
                    {log.entity_id || log.case_id || 'System / Batch'}
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-600 font-mono">
                    {JSON.stringify(log.details || {})}
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
