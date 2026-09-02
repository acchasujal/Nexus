import { useState, useEffect, useCallback } from 'react'
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  Fingerprint,
  AlertCircle,
  Blocks,
  RefreshCw,
  PlusCircle,
} from 'lucide-react'
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

interface BlockchainAnchor {
  anchor_id: string
  batch_start: string
  batch_end: string
  event_count: number
  root_hash: string
  anchored_at: string
  creator_participant: string
  block_index: number
  block_hash: string
  ledger_id: string
}

interface AnchorVerificationState {
  loading: boolean
  verified?: boolean
  reason?: string
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
  const [anchors, setAnchors] = useState<BlockchainAnchor[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [verifications, setVerifications] = useState<Record<string, VerificationStatus>>({})
  const [anchorVerifications, setAnchorVerifications] = useState<Record<string, AnchorVerificationState>>({})
  const [isAnchoring, setIsAnchoring] = useState(false)
  const [anchorMessage, setAnchorMessage] = useState<string | null>(null)

  const loadData = useCallback(() => {
    setIsLoading(true)
    Promise.all([
      apiClient.getAuditLogs(),
      apiClient.listAuditAnchors().catch(() => [] as BlockchainAnchor[]),
    ])
      .then(([logsData, anchorsData]) => {
        setFetchError(null)
        setLogs(Array.isArray(logsData) ? (logsData as AuditLogEntry[]) : [])
        setAnchors(Array.isArray(anchorsData) ? anchorsData : [])
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Unable to load audit records'
        setFetchError(msg)
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleVerifyEvent = async (eventId: string) => {
    setVerifications((prev) => ({
      ...prev,
      [eventId]: { loading: true },
    }))

    try {
      const res = await apiClient.verifyAuditEvent(eventId)
      setVerifications((prev) => ({
        ...prev,
        [eventId]: {
          loading: false,
          verified: res.verified,
          stored_hash: res.stored_hash,
          computed_hash: res.computed_hash,
          reason: res.reason,
          previous_hash: res.previous_hash,
        },
      }))
    } catch (err: unknown) {
      setVerifications((prev) => ({
        ...prev,
        [eventId]: {
          loading: false,
          verified: false,
          error: err instanceof Error ? err.message : 'Verification failed',
        },
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

  const handleCreateAnchor = async () => {
    setIsAnchoring(true)
    setAnchorMessage(null)
    try {
      const newAnchor = await apiClient.createAuditAnchor(50)
      setAnchorMessage(`Created ${newAnchor.anchor_id} with Merkle root ${newAnchor.root_hash.slice(0, 16)}...`)
      loadData()
    } catch (err: unknown) {
      setAnchorMessage(err instanceof Error ? err.message : 'Failed to create anchor')
    } finally {
      setIsAnchoring(false)
    }
  }

  const handleVerifyAnchor = async (anchorId: string) => {
    setAnchorVerifications((prev) => ({
      ...prev,
      [anchorId]: { loading: true },
    }))

    try {
      const res = await apiClient.verifyAuditAnchor(anchorId)
      setAnchorVerifications((prev) => ({
        ...prev,
        [anchorId]: {
          loading: false,
          verified: res.verified,
          reason: res.reason,
        },
      }))
    } catch (err: unknown) {
      setAnchorVerifications((prev) => ({
        ...prev,
        [anchorId]: {
          loading: false,
          verified: false,
          error: err instanceof Error ? err.message : 'Anchor verification failed',
        },
      }))
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={ShieldCheck}
        title="Immutable Audit Trail &amp; Permissioned Blockchain Ledger"
        subtitle="Cryptographically sealed audit history, canonical SHA-256 digests, and Merkle root anchoring to an append-only permissioned block chain."
      />

      {/* Permissioned Blockchain Anchors Section */}
      <SectionCard
        title="Permissioned Blockchain Trust Anchors"
        subtitle="Cryptographic Merkle batch roots anchored to local permissioned blocks (NEXUS-POLICE-HQ / CYBER-CELL / DISTRICT-HQ)"
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreateAnchor}
              disabled={isAnchoring}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold shadow-sm disabled:opacity-50 transition-colors"
            >
              <PlusCircle className="h-3.5 w-3.5" />
              {isAnchoring ? 'Anchoring Batch...' : 'Anchor Audit Batch'}
            </button>
            <button
              onClick={loadData}
              className="p-1.5 text-neutral-500 hover:text-neutral-700 hover:bg-neutral-100 rounded-md transition-colors"
              title="Refresh ledger"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        }
      >
        {anchorMessage && (
          <div className="mb-4 text-xs font-mono p-2 bg-blue-50 border border-blue-200 text-blue-800 rounded-md">
            {anchorMessage}
          </div>
        )}

        {anchors.length === 0 ? (
          <div className="p-4 text-center text-xs text-neutral-500">
            No blockchain anchors committed yet. Click &quot;Anchor Audit Batch&quot; to commit the first batch.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {anchors.map((anc) => {
              const vState = anchorVerifications[anc.anchor_id]
              return (
                <div
                  key={anc.anchor_id}
                  className="p-3.5 rounded-lg border border-neutral-200/80 bg-neutral-50/50 hover:bg-white hover:border-neutral-300 transition-all flex flex-col justify-between space-y-3"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 border-b border-neutral-200/60 pb-2">
                      <span className="font-mono font-bold text-xs text-neutral-900 flex items-center gap-1.5">
                        <Blocks className="h-4 w-4 text-blue-600" />
                        {anc.anchor_id}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-neutral-200 text-neutral-700">
                        Block #{anc.block_index}
                      </span>
                    </div>

                    <div className="mt-2.5 space-y-1.5 text-xs">
                      <div className="flex justify-between text-neutral-600">
                        <span>Participant:</span>
                        <span className="font-mono text-[11px] font-semibold text-neutral-800">
                          {anc.creator_participant}
                        </span>
                      </div>
                      <div className="flex justify-between text-neutral-600">
                        <span>Anchored Events:</span>
                        <span className="font-semibold text-neutral-900">{anc.event_count} events</span>
                      </div>
                      <div className="pt-1">
                        <span className="text-neutral-500 text-[11px] block">Merkle Batch Root Hash:</span>
                        <div className="font-mono text-[11px] text-blue-700 break-all select-all font-semibold">
                          {anc.root_hash}
                        </div>
                      </div>
                      <div className="pt-1">
                        <span className="text-neutral-500 text-[11px] block">Block Hash:</span>
                        <div className="font-mono text-[10px] text-neutral-600 break-all select-all">
                          {anc.block_hash}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-neutral-200/60 flex items-center justify-between">
                    <div>
                      {vState?.loading ? (
                        <span className="text-xs text-blue-600 animate-pulse">Verifying...</span>
                      ) : vState?.verified ? (
                        <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> BLOCKCHAIN VERIFIED
                        </span>
                      ) : vState?.verified === false ? (
                        <span className="inline-flex items-center gap-1 text-xs font-bold text-red-600">
                          <AlertTriangle className="h-3.5 w-3.5" /> LEDGER INTEGRITY FAILURE
                        </span>
                      ) : (
                        <span className="text-[11px] text-neutral-400">Unverified</span>
                      )}
                    </div>
                    <button
                      onClick={() => handleVerifyAnchor(anc.anchor_id)}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-neutral-200 hover:bg-neutral-300 text-neutral-800 transition-colors"
                    >
                      Verify
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </SectionCard>

      {/* Audit Log Table Container */}
      <SectionCard noPadding title="Audit Trail Records" subtitle="Sequential event log with backward SHA-256 hash chaining">
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
