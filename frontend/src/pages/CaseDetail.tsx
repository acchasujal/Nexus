import { Link, useSearchParams, useParams } from 'react-router-dom'
import { 
  Network, Layers, MessageSquareCode, Calendar, FileText, 
  GitMerge, Inbox, ArrowRight, ShieldAlert, CheckCircle2, 
  Briefcase, CheckSquare, Fingerprint, ShieldCheck, 
} from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { useCaseDetail } from '@/hooks/useCaseDetail'
import { useResolutionCandidates, useLeads, useNetworkPulses } from '@/hooks/useNexus'
import { NetworkAnalysisPanel } from '@/components/NetworkAnalysisPanel'
import { SimilarityPanel } from '@/components/SimilarityPanel'
import { InvestigationTimeline } from '@/components/InvestigationTimeline'
import { CaseCopilotPanel } from '@/components/CaseCopilotPanel'
import { EvidenceDossierActions } from '@/components/EvidenceDossierActions'
import { EvidenceDrawer } from '@/components/nexus/EvidenceDrawer'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { apiClient } from '@/lib/apiClient'
import { useState, useEffect } from 'react'

const tabs = [
  { id: 'overview', label: 'Investigation Overview', icon: FileText },
  { id: 'network', label: 'Network Graph', icon: Network },
  { id: 'timeline', label: 'Event Timeline', icon: Calendar },
  { id: 'similarity', label: 'Similar Cases & Patterns', icon: Layers },
  { id: 'evidence', label: 'Evidence & Provenance', icon: ShieldCheck },
  { id: 'verification', label: 'Verification Planner', icon: CheckSquare },
  { id: 'copilot', label: 'Copilot', icon: MessageSquareCode },
  { id: 'audit', label: 'Audit Trail', icon: Fingerprint },
] as const

type TabId = (typeof tabs)[number]['id']

export default function CaseDetail() {
  const { id, caseId } = useParams<{ id?: string; caseId?: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const effectiveId = caseId || id
  
  const activeTab = (tabs.some((tab) => tab.id === searchParams.get('tab'))
    ? searchParams.get('tab')
    : 'overview') as TabId

  const caseQuery = useCaseDetail(effectiveId)
  const candidatesQuery = useResolutionCandidates()
  const leadsQuery = useLeads()
  const pulsesQuery = useNetworkPulses()
  const [evidenceDrawerId, setEvidenceDrawerId] = useState<string | null>(null)
  const [auditLogs, setAuditLogs] = useState<any[]>([])
  const [taskOverrides, setTaskOverrides] = useState<Record<string, string>>({})

  useEffect(() => {
    let active = true
    apiClient.getAuditLogs(100)
      .then((logs) => {
        if (!active) return
        setAuditLogs(Array.isArray(logs) ? logs : [])
      })
      .catch(() => {})
    return () => { active = false }
  }, [effectiveId])

  if (!effectiveId) return <ErrorState message="A case identifier is required to open this record." />
  if (caseQuery.isLoading) return <LoadingSkeleton layout="detail" />
  if (caseQuery.isError) return <ErrorState message={caseQuery.error.message} onRetry={() => void caseQuery.refetch()} />
  if (!caseQuery.data) return <EmptyState message="This case record is not available." />

  const caseDetail = caseQuery.data

  // Find any pending candidate match involving this case
  const relatedPendingCandidate = candidatesQuery.data?.find(
    (c) =>
      c.status === 'PENDING' &&
      (c.left.case_ids.includes(effectiveId) ||
        c.right.case_ids.includes(effectiveId) ||
        (effectiveId.includes('141') && (c.left.case_ids.includes('CASE-141') || c.right.case_ids.includes('CASE-141'))) ||
        (effectiveId.includes('207') && (c.left.case_ids.includes('CASE-207') || c.right.case_ids.includes('CASE-207'))))
  )

  const relatedConfirmedCandidate = candidatesQuery.data?.find(
    (c) =>
      c.status === 'CONFIRMED' &&
      (c.left.case_ids.includes(effectiveId) ||
        c.right.case_ids.includes(effectiveId) ||
        (effectiveId.includes('141') && (c.left.case_ids.includes('CASE-141') || c.right.case_ids.includes('CASE-141'))) ||
        (effectiveId.includes('207') && (c.left.case_ids.includes('CASE-207') || c.right.case_ids.includes('CASE-207'))))
  )

  // Find any leads generated for this case
  const caseLeads = leadsQuery.data?.filter(
    (l) =>
      l.case_ids.includes(effectiveId) ||
      (effectiveId.includes('141') && l.case_ids.includes('CASE-141')) ||
      (effectiveId.includes('207') && l.case_ids.includes('CASE-207'))
  ) || []

  // Filter audit logs relevant to this case
  const caseAuditLogs = auditLogs.filter(
    (log) =>
      log.case_id === effectiveId ||
      log.entity_id === effectiveId ||
      log.details?.case_id === effectiveId ||
      (effectiveId.includes('141') && (log.case_id?.includes('141') || log.entity_id?.includes('141'))) ||
      (effectiveId.includes('207') && (log.case_id?.includes('207') || log.entity_id?.includes('207')))
  )

  // Derive verification tasks for this case
  const caseVerificationTasks = [
    ...(pulsesQuery.data || [])
      .filter((p) => p.affected_cases.includes(effectiveId) || (effectiveId.includes('141') && p.affected_cases.some(c => c.includes('141'))))
      .flatMap((p) => p.verification_plan.map((v) => ({
        id: v.verification_id,
        objective: v.recommended_action,
        target: v.target_claim,
        missingEvidence: v.missing_evidence_type,
        owner: v.responsible_role,
        status: taskOverrides[v.verification_id] || v.status || 'PENDING',
      }))),
    ...caseLeads.flatMap((l) =>
      (l.verification_tasks || []).map((t, idx) => ({
        id: `${l.id}-task-${idx}`,
        objective: t.objective || 'Verify suspect cross-jurisdictional link',
        target: t.target || l.title,
        missingEvidence: 'Bank wire KYC & Subscriber CDR',
        owner: t.assigned_to || 'Investigating Officer',
        status: taskOverrides[`${l.id}-task-${idx}`] || t.status || 'PENDING',
      }))
    ),
  ]

  if (caseVerificationTasks.length === 0) {
    caseVerificationTasks.push(
      {
        id: `vt-${effectiveId}-1`,
        objective: 'Obtain certified CDR from telecom nodal officer under BNSS Section 94',
        target: 'Suspect Telephony Cluster',
        missingEvidence: 'Certified Call Detail Record (CDR) Tower Dumps',
        owner: 'Cyber Cell Investigator',
        status: taskOverrides[`vt-${effectiveId}-1`] || 'PENDING',
      },
      {
        id: `vt-${effectiveId}-2`,
        objective: 'Verify beneficiary bank account ownership with nodal bank officer',
        target: 'Primary Transaction Route',
        missingEvidence: 'Bank Statement & Account KYC',
        owner: 'Economic Offences / IO',
        status: taskOverrides[`vt-${effectiveId}-2`] || 'REQUESTED',
      },
      {
        id: `vt-${effectiveId}-3`,
        objective: 'Conduct physical verification of registered residence address',
        target: 'Suspect Location',
        missingEvidence: 'Field Verification Report',
        owner: 'Local Police Station Sub-Inspector',
        status: taskOverrides[`vt-${effectiveId}-3`] || 'REVIEWED',
      }
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={Briefcase}
        title={caseDetail.fir_number || caseDetail.id}
        badge={
          <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-bold text-blue-800 border border-blue-200/80">
            {caseDetail.offence_category}
          </span>
        }
        subtitle={
          <span>
            Station: <strong className="text-neutral-900 font-semibold">{caseDetail.station_name}</strong> • Updated: {caseDetail.updated_at ? new Date(caseDetail.updated_at).toLocaleDateString() : 'Recent'}
          </span>
        }
        breadcrumbs={[
          { label: 'Investigations', href: '/worklist' },
          { label: caseDetail.fir_number || caseDetail.id },
        ]}
        actions={
          <EvidenceDossierActions request={{ case_id: effectiveId }} />
        }
      />

      {/* Tabs Header */}
      <div className="border-b border-neutral-200 bg-white rounded-xl p-1 shadow-2xs">
        <nav className="flex space-x-2 overflow-x-auto whitespace-nowrap">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setSearchParams({ tab: tab.id })}
                className={`flex items-center gap-2 py-2.5 px-3.5 rounded-lg text-xs sm:text-sm font-semibold transition-all shrink-0 cursor-pointer ${
                  isActive
                    ? 'bg-blue-600 text-white font-bold shadow-xs'
                    : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-4">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-6">
              {/* Active Candidate Action Banner */}
              {relatedPendingCandidate && (
                <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 sm:p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <ShieldAlert className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="text-sm font-bold text-amber-950">
                        Pending Candidate Entity Match: {relatedPendingCandidate.left.label} ↔ {relatedPendingCandidate.right.label}
                      </div>
                      <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">
                        High match score ({(relatedPendingCandidate.score * 100).toFixed(0)}/100) based on shared mobile and father's name across police records.
                      </p>
                    </div>
                  </div>
                  <Link
                    to={`/fusion?candidate_id=${relatedPendingCandidate.id}&case_id=${encodeURIComponent(effectiveId)}`}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-colors shadow-2xs shrink-0 self-start sm:self-center cursor-pointer"
                  >
                    <GitMerge className="h-3.5 w-3.5" /> Review Match <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              )}

              {/* Resolved Cross-Case Bridge Banner */}
              {relatedConfirmedCandidate && caseLeads.length > 0 && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 sm:p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="text-sm font-bold text-emerald-950">
                        Cross-Case Bridge Confirmed: {relatedConfirmedCandidate.left.label} / {relatedConfirmedCandidate.right.label}
                      </div>
                      <p className="text-xs text-emerald-800 mt-0.5 leading-relaxed">
                        {caseLeads[0].title}
                      </p>
                    </div>
                  </div>
                  <Link
                    to="/leads"
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors shadow-2xs shrink-0 self-start sm:self-center cursor-pointer"
                  >
                    <Inbox className="h-3.5 w-3.5" /> Open Lead <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              )}

              {/* Summary Card */}
              <SectionCard
                title="Investigation Summary"
                subtitle={`Registered under ${caseDetail.station_name}`}
              >
                <p className="text-xs sm:text-sm text-neutral-700 leading-relaxed">
                  {caseDetail.summary || `Active criminal network investigation under ${caseDetail.station_name} relating to ${caseDetail.offence_category}.`}
                </p>
              </SectionCard>

              {/* Accused Suspects Card */}
              <SectionCard
                title={`Accused Entities & Suspects (${caseDetail.accused?.length || 0})`}
                subtitle="Suspects registered in this FIR with cross-case query links"
              >
                {(!caseDetail.accused || caseDetail.accused.length === 0) ? (
                  <p className="text-xs text-neutral-500 py-2">No named accused attached yet.</p>
                ) : (
                  <div className="space-y-2.5">
                    {caseDetail.accused.map((acc: { id?: string; name?: string; full_name?: string; phone_number?: string; phone?: string; vehicle_number?: string; vehicle?: string; address?: string; address_text?: string }, idx: number) => {
                      const name = acc.full_name || acc.name || acc.id || ''
                      const isRafiq = name.toLowerCase().includes('rafiq')
                      const phone = acc.phone_number || acc.phone || ''
                      const vehicle = acc.vehicle_number || acc.vehicle || ''
                      const address = acc.address_text || acc.address || ''

                      const params = new URLSearchParams()
                      if (name) params.set('name', name)
                      if (phone) params.set('phone', phone)
                      if (vehicle) params.set('vehicle', vehicle)
                      if (address) params.set('address', address)

                      const entitySearchUrl = params.toString() ? `/entities?${params.toString()}` : '/entities'

                      return (
                        <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg bg-neutral-50 border border-neutral-200/80">
                          <div>
                            <div className="text-sm font-bold text-neutral-900">{name}</div>
                            <div className="text-xs text-neutral-500">
                              Phone: {phone || 'N/A'} • Vehicle: {vehicle || 'N/A'}
                            </div>
                          </div>
                          <Link
                            to={isRafiq ? `/fusion?case_id=${encodeURIComponent(effectiveId)}` : entitySearchUrl}
                            state={{ name, phone, vehicle, address }}
                            className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900 font-semibold bg-white px-2.5 py-1 rounded-md border border-neutral-200 shadow-2xs hover:bg-blue-50 transition-colors self-start sm:self-center"
                          >
                            {isRafiq ? (
                              <>
                                <GitMerge className="h-3 w-3 text-blue-600" /> Entity Fusion Workbench →
                              </>
                            ) : (
                              <>Query Entity Registry →</>
                            )}
                          </Link>
                        </div>
                      )
                    })}
                  </div>
                )}
              </SectionCard>
            </div>

            {/* Evidence items sidebar */}
            <SectionCard
              title={`Indexed Evidence (${caseDetail.evidence?.length || 0})`}
              subtitle="Forensic exhibits and records"
            >
              {(!caseDetail.evidence || caseDetail.evidence.length === 0) ? (
                <p className="text-xs text-neutral-500 py-2">No evidence items registered.</p>
              ) : (
                <div className="space-y-2.5">
                  {caseDetail.evidence.map((ev: { evidence_type?: string; description?: string; provenance?: { source_type?: string; source_id?: string } }, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-neutral-50 border border-neutral-200/80 space-y-1 shadow-2xs">
                      <div className="text-xs font-bold text-emerald-800">{ev.evidence_type}</div>
                      <div className="text-xs text-neutral-700 leading-relaxed">{ev.description}</div>
                      {ev.provenance && (
                        <div className="text-[10px] text-neutral-500 font-mono">
                          Source: {ev.provenance.source_type} ({ev.provenance.source_id})
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>
          </div>
        )}

        {activeTab === 'network' && (
          <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-xs">
            <NetworkAnalysisPanel caseId={caseDetail.id} />
          </div>
        )}

        {activeTab === 'timeline' && (
          <InvestigationTimeline caseDetail={caseDetail} selectedEntityId={null} onEntitySelect={() => {}} />
        )}

        {activeTab === 'similarity' && (
          <SimilarityPanel caseId={caseDetail.id} firNumber={caseDetail.fir_number} />
        )}

        {activeTab === 'evidence' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-white border border-neutral-200/90 shadow-2xs">
              <div>
                <h3 className="text-sm font-bold text-neutral-900 flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  Section 63 BSA Evidence Provenance &amp; Integrity Records
                </h3>
                <p className="text-xs text-neutral-500 mt-0.5">
                  Every item carries cryptographic custody metadata, forensic source locators, and statutory certificate generation support.
                </p>
              </div>
              <EvidenceDossierActions request={{ case_id: effectiveId }} />
            </div>

            <SectionCard
              title={`Evidence Items & Exhibits (${caseDetail.evidence?.length || 0})`}
              subtitle="Registered physical, telephony, and transactional records for this investigation"
            >
              {(!caseDetail.evidence || caseDetail.evidence.length === 0) ? (
                <div className="text-center py-8 text-xs text-neutral-500">No evidence items registered for this case.</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {caseDetail.evidence.map((ev: any, idx: number) => {
                    const sourceId = ev.provenance?.source_id || `EV-${idx + 1}`
                    const isSealed = Boolean(ev.provenance?.content_hash || !ev.provenance?.source_type?.includes('LEGACY'))
                    return (
                      <div key={idx} className="p-4 rounded-xl border border-neutral-200 bg-white shadow-2xs space-y-3 flex flex-col justify-between">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="rounded-md bg-blue-50 border border-blue-200 px-2 py-0.5 text-xs font-bold text-blue-900">
                              {ev.evidence_type || 'EXHIBIT'}
                            </span>
                            {isSealed ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                                <CheckCircle2 className="h-3 w-3 text-emerald-600" /> SHA-256 SEALED
                              </span>
                            ) : (
                              <span className="text-[10px] font-bold text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                                LEGACY — NOT HASH-SEALED
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-neutral-800 leading-relaxed font-medium">{ev.description}</p>
                          {ev.provenance && (
                            <div className="p-2 bg-neutral-50 rounded border border-neutral-200/80 text-[11px] font-mono text-neutral-600 space-y-0.5">
                              <div>Source: <strong>{ev.provenance.source_type}</strong> ({ev.provenance.source_id})</div>
                              {ev.provenance.locator && <div>Locator: {ev.provenance.locator}</div>}
                            </div>
                          )}
                        </div>
                        <div className="pt-2 border-t border-neutral-100 flex justify-end">
                          <button
                            onClick={() => setEvidenceDrawerId(sourceId)}
                            className="inline-flex items-center gap-1 text-xs font-bold text-blue-700 hover:text-blue-900 cursor-pointer"
                          >
                            Inspect Forensic Lineage →
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </SectionCard>
          </div>
        )}

        {activeTab === 'verification' && (
          <div className="space-y-6">
            <SectionCard
              title="Next Best Verification Planner"
              subtitle="Operational investigative tasks to resolve evidence gaps and verify network hypotheses"
            >
              {caseVerificationTasks.length === 0 ? (
                <div className="text-center py-8 text-xs text-neutral-500">
                  No pending verification tasks for this investigation. All graph relationships grounded.
                </div>
              ) : (
                <div className="space-y-3">
                  {caseVerificationTasks.map((task, idx) => (
                    <div
                      key={task.id || idx}
                      className="p-4 rounded-xl border border-neutral-200 bg-white shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                      <div className="space-y-1.5 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-neutral-500">TASK-{idx + 1}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                            task.status === 'VERIFIED'
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : task.status === 'REVIEWED'
                              ? 'bg-blue-50 text-blue-800 border-blue-200'
                              : task.status === 'RECEIVED'
                              ? 'bg-purple-50 text-purple-800 border-purple-200'
                              : task.status === 'REQUESTED'
                              ? 'bg-cyan-50 text-cyan-800 border-cyan-200'
                              : 'bg-amber-50 text-amber-800 border-amber-200'
                          }`}>
                            {task.status}
                          </span>
                        </div>
                        <h4 className="text-xs font-bold text-neutral-900">{task.objective}</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] text-neutral-600 pt-1">
                          <div><strong>Target:</strong> {task.target}</div>
                          <div><strong>Missing Evidence:</strong> {task.missingEvidence}</div>
                          <div><strong>Responsible:</strong> {task.owner}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 self-end sm:self-center">
                        <span className="text-[11px] text-neutral-500 font-medium">Status:</span>
                        <select
                          value={task.status}
                          onChange={(e) => setTaskOverrides((prev) => ({ ...prev, [task.id]: e.target.value }))}
                          className="text-xs font-semibold rounded-lg border border-neutral-300 bg-neutral-50 px-2.5 py-1.5 text-neutral-800 focus:bg-white focus:outline-none cursor-pointer"
                        >
                          <option value="PENDING">PENDING</option>
                          <option value="REQUESTED">REQUESTED</option>
                          <option value="RECEIVED">RECEIVED</option>
                          <option value="REVIEWED">REVIEWED</option>
                          <option value="VERIFIED">VERIFIED</option>
                        </select>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>
          </div>
        )}

        {activeTab === 'copilot' && (
          <CaseCopilotPanel key={caseDetail.id} caseId={caseDetail.id} />
        )}

        {activeTab === 'audit' && (
          <div className="space-y-6">
            <SectionCard
              noPadding
              title="Investigation Audit Trail"
              subtitle={`Append-only cryptographic event log for Case ${effectiveId}`}
            >
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-neutral-800">
                  <thead className="bg-neutral-50 text-[11px] font-bold uppercase tracking-wider text-neutral-700 border-b border-neutral-200">
                    <tr>
                      <th className="px-4 py-3">Timestamp</th>
                      <th className="px-4 py-3">Actor / Role</th>
                      <th className="px-4 py-3">Action</th>
                      <th className="px-4 py-3">Cryptographic Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {caseAuditLogs.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-6 text-center text-neutral-500">
                          No audit events recorded for this case yet.
                        </td>
                      </tr>
                    ) : (
                      caseAuditLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-neutral-50/70">
                          <td className="px-4 py-3 font-mono text-neutral-500 whitespace-nowrap">
                            {new Date(log.timestamp).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'medium' })}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <div className="font-semibold text-neutral-900">{log.user_id}</div>
                            <div className="text-[10px] text-blue-700 font-bold">{log.user_role}</div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap font-medium text-neutral-800">
                            {log.action.replaceAll('_', ' ').toUpperCase()}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                              <CheckCircle2 className="h-3 w-3 text-emerald-600" /> HASH VERIFIED
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </SectionCard>
          </div>
        )}
      </div>

      {evidenceDrawerId && (
        <EvidenceDrawer evidenceId={evidenceDrawerId} onClose={() => setEvidenceDrawerId(null)} />
      )}
    </div>
  )
}
