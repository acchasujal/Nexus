import { useState, useEffect } from 'react'
import { ShieldCheck, AlertTriangle, CheckCircle2, ChevronRight, ChevronDown, Fingerprint, AlertCircle } from 'lucide-react'
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
  integrity_hash?: string
  previous_hash?: string
  details?: Record<string, unknown>
}

interface VerificationStatus {
  loading: boolean
  verified?: boolean
  stored_hash?: string | null
  computed_hash?: string
  reason?: string
  previous_hash?: string | null
  error?: string
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
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [verifications, setVerifications] = useState<Record<string, VerificationStatus>>({})

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

  const handleVerifyEvent = async (eventId: string) => {
    setVerifications(prev => ({
      ...prev,
      [eventId]: { loading: true }
    }))

    try {
      const res = await apiClient.verifyAuditEvent(eventId)
      setVerifications(prev => ({
        ...prev,
        [eventId]: {
          loading: false,
          verified: res.verified,
          stored_hash: res.stored_hash,
          computed_hash: res.computed_hash,
          reason: res.reason,
          previous_hash: res.previous_hash,
        }
      }))
    } catch (err: unknown) {
      setVerifications(prev => ({
        ...prev,
        [eventId]: {
          loading: false,
          verified: false,
          error: err instanceof Error ? err.message : 'Verification failed'
        }
      }))
    }
  }

  const toggleRow = (eventId: string) => {
    if (expandedRow === eventId) {
      setExpandedRow(null)
    } else {
      setExpandedRow(eventId)
      if (!verifications[eventId]) {
        void handleVerifyEvent(eventId)
      }
    }
  }

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
          <table className="w-full text-left text-xs sm:text-sm text-neutral-800 min-w-[850px]">
            <thead className="bg-neutral-50/80 text-[11px] font-bold uppercase tracking-wider text-neutral-700 border-b border-neutral-200/80">
              <tr>
                <th className="px-4 py-3.5 w-10"></th>
                <th className="px-4 py-3.5">Timestamp</th>
                <th className="px-4 py-3.5">Actor / Role</th>
                <th className="px-4 py-3.5">Action Executed</th>
                <th className="px-4 py-3.5">Target Entity</th>
                <th className="px-4 py-3.5">Cryptographic Integrity</th>
                <th className="px-4 py-3.5">Audit Context Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-neutral-500">Loading audit records...</td>
                </tr>
              ) : fetchError ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center">
                    <div className="flex flex-col items-center gap-2 text-amber-800">
                      <AlertTriangle className="h-6 w-6 text-amber-500" />
                      <p className="font-semibold text-sm">Audit log unavailable</p>
                      <p className="text-xs text-neutral-600 max-w-md">{fetchError}</p>
                    </div>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-neutral-500">No audit events recorded yet.</td>
                </tr>
              ) : (
                logs.map((log) => {
                  const isExpanded = expandedRow === log.id
                  const verifyInfo = verifications[log.id]

                  return (
                    <tr key={log.id} className="hover:bg-neutral-50/70 transition-colors group">
                      <td className="px-3 py-3 text-center">
                        <button
                          onClick={() => toggleRow(log.id)}
                          className="p-1 rounded hover:bg-neutral-200 text-neutral-500 transition-colors"
                          title="Inspect cryptographic fingerprint"
                        >
                          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        </button>
                      </td>
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
                      <td className="px-4 py-3 whitespace-nowrap">
                        {log.integrity_hash ? (
                          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                            <span>VERIFIED</span>
                          </div>
                        ) : (
                          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                            <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
                            <span>UNHASHED</span>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {formatAuditDetails(log.details)}
                        {isExpanded && (
                          <div className="mt-3 p-3 bg-neutral-900 text-neutral-100 rounded-lg font-mono text-[11px] space-y-2 border border-neutral-800 shadow-inner">
                            <div className="flex items-center justify-between text-neutral-400 border-b border-neutral-800 pb-1.5">
                              <span className="flex items-center gap-1 font-bold text-neutral-300">
                                <Fingerprint className="h-3.5 w-3.5 text-blue-400" /> SHA-256 Fingerprint &amp; Verification
                              </span>
                              {verifyInfo?.loading ? (
                                <span className="text-blue-400 animate-pulse">Verifying...</span>
                              ) : verifyInfo?.verified ? (
                                <span className="text-emerald-400 font-bold flex items-center gap-1">
                                  <CheckCircle2 className="h-3.5 w-3.5" /> Hash Matches Canonical Event
                                </span>
                              ) : verifyInfo?.verified === false ? (
                                <span className="text-red-400 font-bold flex items-center gap-1">
                                  <AlertTriangle className="h-3.5 w-3.5" /> ⚠ INTEGRITY FAILURE
                                </span>
                              ) : null}
                            </div>
                            <div>
                              <span className="text-neutral-500">Integrity Hash:</span>
                              <div className="break-all text-blue-300 select-all font-semibold">
                                {log.integrity_hash || 'None'}
                              </div>
                            </div>
                            {log.previous_hash && (
                              <div>
                                <span className="text-neutral-500">Previous Event Hash (Audit Chain):</span>
                                <div className="break-all text-neutral-400 select-all">
                                  {log.previous_hash}
                                </div>
                              </div>
                            )}
                            {verifyInfo?.reason && (
                              <div className="text-[10px] text-neutral-400 italic pt-1">
                                Note: {verifyInfo.reason}
                              </div>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  )
}
