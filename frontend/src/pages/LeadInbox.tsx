/**
 * frontend/src/pages/LeadInbox.tsx
 *
 * Lead Inbox + Pathfinder: cross-case bridge finding, evidence-backed
 * connection path, Accept/Reject controls, and grounded copilot explanation.
 */
import { useState, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Inbox, Route, ThumbsUp, ThumbsDown, ShieldCheck, ShieldQuestion,
  MessageSquareCode, FileText, AlertOctagon, ChevronRight, RefreshCw, Sparkles, CheckCircle2, XCircle,
} from 'lucide-react'
import { useLeads, useScanLeads, useDecideLead, useNexusCopilot, useNexusNetwork } from '@/hooks/useNexus'
import { DerivationBadge } from '@/components/nexus/DerivationBadge'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { EvidenceDrawer } from '@/components/nexus/EvidenceDrawer'
import { MarkdownContent } from '@/components/nexus/MarkdownContent'
import { EvidenceDossierActions } from '@/components/EvidenceDossierActions'
import { PageHeader } from '@/components/ui/PageHeader'
import { FilterPills, type FilterPillOption } from '@/components/ui/FilterPills'
import { SectionCard } from '@/components/ui/SectionCard'

/** Maps canonical source record IDs to the most representative graph edge
 *  that carries them in its evidence_ids. Derived from NEXUS golden fixture. */
const SOURCE_TO_EDGE: Record<string, string> = {
  'SRC-FIR-141':  'E-ACCUSE-141',
  'SRC-FIR-207':  'E-ACCUSE-207',
  'SRC-CDR-A12':  'E-USEPH-1',
  'SRC-CDR-B31':  'E-USEPH-2',
  'SRC-TXN-55':   'E-TXN-55',
  'SRC-TXN-71':   'E-TXN-71',
}

const PRIORITY_STYLE: Record<string, string> = {
  HIGH: 'border-red-200 bg-red-50 text-red-900 font-bold',
  MEDIUM: 'border-amber-200 bg-amber-50 text-amber-900 font-bold',
  LOW: 'border-neutral-200 bg-neutral-100 text-neutral-800 font-medium',
}

type QueueFilter = 'ALL' | 'HIGH' | 'PENDING' | 'ACCEPTED' | 'REJECTED'

export default function LeadInbox() {
  const [searchParams] = useSearchParams()
  const caseIdParam = searchParams.get('case_id')
  const { data: leads, isLoading, error, refetch } = useLeads()
  const scanLeadsMutation = useScanLeads()
  const decide = useDecideLead()
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<QueueFilter>('ALL')

  const effectiveLeads = useMemo(() => {
    if (!leads) return []
    return leads.filter((l) => {
      if (activeFilter === 'HIGH') return l.severity === 'HIGH' || l.review_priority === 'HIGH'
      if (activeFilter === 'PENDING') return l.status === 'NEW'
      if (activeFilter === 'ACCEPTED') return l.status === 'ACCEPTED'
      if (activeFilter === 'REJECTED') return l.status === 'REJECTED'
      return true
    })
  }, [leads, activeFilter])

  const effectiveSelectedId = selectedLeadId ?? effectiveLeads[0]?.id ?? leads?.[0]?.id
  const lead = effectiveLeads.find((l) => l.id === effectiveSelectedId) ?? effectiveLeads[0] ?? leads?.[0]

  const afterNetwork = useNexusNetwork('after', Boolean(lead))
  const [copilotAnswer, setCopilotAnswer] = useState<string | null>(null)
  const [copilotError, setCopilotError] = useState<string | null>(null)
  const copilotQuery = useNexusCopilot(copilotAnswer === null && !copilotError ? 'How are the two cases connected?' : null)
  
  const [evidenceDrawerEdgeId, setEvidenceDrawerEdgeId] = useState<string | null>(null)
  const [evidenceDrawerEvidenceId, setEvidenceDrawerEvidenceId] = useState<string | null>(null)

  const nodeLabel = (id: string) => afterNetwork.data?.nodes.find((n) => n.id === id)?.label ?? id

  const submit = async (decision: 'ACCEPT' | 'REJECT') => {
    setCopilotAnswer(null)
    setCopilotError(null)
    try {
      await decide.mutateAsync({ id: lead!.id, req: { decision, decided_by: 'Investigating Officer' } })
    } catch (e) {
      setCopilotError(e instanceof Error ? e.message : 'Decision failed')
    }
  }

  const handleScanLeads = async () => {
    try {
      await scanLeadsMutation.mutateAsync()
      await refetch()
    } catch (e) {
      console.error('Lead scan failed:', e)
    }
  }

  const openEvidence = (id: string) => {
    const relId = SOURCE_TO_EDGE[id] ?? null
    if (relId) {
      setEvidenceDrawerEdgeId(relId)
      setEvidenceDrawerEvidenceId(null)
    } else {
      setEvidenceDrawerEvidenceId(id)
      setEvidenceDrawerEdgeId(null)
    }
  }

  if (isLoading) return <LoadingSkeleton layout="detail" />
  if (error) return <ErrorState message="Failed to load leads." onRetry={() => void refetch()} />

  const filterOptions: FilterPillOption<QueueFilter>[] = [
    { value: 'ALL', label: 'All Leads', count: leads?.length ?? 0 },
    { value: 'HIGH', label: 'High Priority', count: leads?.filter(l => l.severity === 'HIGH' || l.review_priority === 'HIGH').length ?? 0 },
    { value: 'PENDING', label: 'Pending Action', count: leads?.filter(l => l.status === 'NEW').length ?? 0 },
    { value: 'ACCEPTED', label: 'Accepted', count: leads?.filter(l => l.status === 'ACCEPTED').length ?? 0 },
    { value: 'REJECTED', label: 'Rejected', count: leads?.filter(l => l.status === 'REJECTED').length ?? 0 },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Page Header */}
      <PageHeader
        icon={Inbox}
        title="Lead Inbox"
        subtitle="Explainable, evidence-backed investigative leads. Every lead is a deterministic hypothesis awaiting officer decision."
        badge={
          caseIdParam ? (
            <span className="rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 font-mono text-xs font-bold text-blue-800">
              {caseIdParam}
            </span>
          ) : undefined
        }
        actions={
          <button
            onClick={handleScanLeads}
            disabled={scanLeadsMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-blue-200 bg-blue-50 text-blue-800 text-xs font-bold hover:bg-blue-100 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${scanLeadsMutation.isPending ? 'animate-spin' : ''}`} />
            {scanLeadsMutation.isPending ? 'Scanning Graph...' : 'Scan Graph Leads'}
          </button>
        }
      />

      {/* Filter pills */}
      <FilterPills
        options={filterOptions}
        value={activeFilter}
        onChange={setActiveFilter}
        label="Filter Queue"
      />

      {!effectiveLeads.length ? (
        <div className="rounded-2xl border border-dashed border-neutral-300 bg-white py-16 text-center shadow-xs">
          <Inbox className="mx-auto h-12 w-12 text-neutral-400" />
          <h2 className="mt-3 text-base sm:text-lg font-bold text-neutral-900">
            {activeFilter === 'ALL' ? 'No open leads' : `No ${activeFilter.toLowerCase()} leads`}
          </h2>
          <p className="mx-auto mt-1 max-w-md text-xs sm:text-sm text-neutral-600 px-4 leading-relaxed">
            {activeFilter === 'ALL'
              ? <>Leads are discovered from deterministic graph patterns and confirmed entity matches. Click &quot;Scan Graph Leads&quot; or visit{' '}
                  <Link to="/fusion" className="font-bold text-blue-700 underline hover:text-blue-900">Entity Fusion</Link> to resolve pending candidates.</>           
              : `No leads match the "${activeFilter}" filter. Try "All Leads" to review the full queue.`
            }
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-4">
          {/* Queue list — xl:col-span-1 */}
          <section className="xl:col-span-1 rounded-xl border border-neutral-200/90 bg-white shadow-xs overflow-hidden" aria-label="Lead queue">
            <div className="border-b border-neutral-100 bg-neutral-50/60 px-4 py-3 flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-700">Lead Queue</h3>
              <span className="text-[11px] font-bold text-neutral-500">{effectiveLeads.length} Items</span>
            </div>
            <ul className="divide-y divide-neutral-100 max-h-[70vh] overflow-y-auto">
              {effectiveLeads.map((l) => (
                <li key={l.id}>
                  <button
                    onClick={() => setSelectedLeadId(l.id)}
                    className={`w-full text-left px-4 py-3 transition-colors flex items-start gap-2.5 cursor-pointer ${
                      l.id === (lead?.id) ? 'bg-blue-50/70 border-l-3 border-blue-600' : 'hover:bg-neutral-50'
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className={`rounded px-1.5 py-0.2 text-[9px] font-bold uppercase border ${
                          PRIORITY_STYLE[l.review_priority || l.severity] || PRIORITY_STYLE.HIGH
                        }`}>{l.review_priority || l.severity}</span>
                        {l.status !== 'NEW' && (
                          <span className={`text-[9px] font-bold uppercase px-1 rounded ${
                            l.status === 'ACCEPTED' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                          }`}>{l.status}</span>
                        )}
                      </div>
                      <p className="mt-1 text-xs font-semibold text-neutral-900 leading-tight line-clamp-2">{l.title}</p>
                    </div>
                    {l.id === (lead?.id) && <ChevronRight className="h-3.5 w-3.5 shrink-0 mt-0.5 text-blue-600" />}
                  </button>
                </li>
              ))}
            </ul>
          </section>

          {/* Lead Detail Panel — xl:col-span-3 */}
          <section className="space-y-5 xl:col-span-3" aria-label="Lead detail">
            <div className="rounded-xl border border-neutral-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${PRIORITY_STYLE[lead.review_priority || lead.severity] || PRIORITY_STYLE.HIGH}`}>
                  {lead.review_priority || lead.severity} Review Priority
                </span>
                <span className="rounded-md border border-neutral-200 bg-neutral-100 px-2 py-0.5 font-mono text-[10px] font-bold text-neutral-800">rule: {lead.rule_id}</span>
                <DerivationBadge klass={lead.derivation_class} />
                {lead.generation_mode && (
                  <span className="rounded-md border border-purple-200 bg-purple-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-purple-900 flex items-center gap-1">
                    <Sparkles className="h-3 w-3 text-purple-600" /> {lead.generation_mode}
                  </span>
                )}
                {lead.status !== 'NEW' && (
                  <span data-testid="lead-status" className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                    lead.status === 'ACCEPTED' ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-red-200 bg-red-50 text-red-900'
                  }`}>
                    {lead.status} by {lead.decided_by || 'Investigating Officer'}
                  </span>
                )}
              </div>
              <h2 className="text-lg sm:text-xl font-bold text-neutral-900">{lead.title}</h2>
              <div className="pt-1"><EvidenceDossierActions request={{ lead_id: lead.id }} /></div>
              
              {/* Rich Markdown Explanation */}
              <div className="rounded-xl border border-neutral-100 bg-neutral-50/50 p-4">
                <MarkdownContent content={lead.explanation} />
              </div>

              {/* Breadcrumb path visualization */}
              <div className="rounded-xl border border-neutral-200/80 bg-neutral-50/50 p-4 space-y-2">
                <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-neutral-700">
                  <Route className="h-4 w-4 text-blue-600" /> Grounded Evidence Graph Path
                </h4>
                <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto py-1">
                  {lead.path_node_ids.map((id, idx) => (
                    <div key={id} className="flex items-center gap-1.5 shrink-0">
                      {idx > 0 && <span className="text-xs text-neutral-400 font-bold">→</span>}
                      <Link
                        to={`/network?node_id=${encodeURIComponent(id)}`}
                        className="rounded-lg border border-neutral-200 bg-white px-2.5 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50 transition-colors shadow-2xs"
                      >
                        {nodeLabel(id)}
                      </Link>
                    </div>
                  ))}
                </div>
              </div>

              {/* Evidentiary Citations */}
              <div className="border-t border-neutral-100 pt-3">
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                  Authoritative Evidence Citations ({lead.supporting_evidence_ids.length})
                </h4>
                <div className="mt-2 flex flex-wrap gap-2">
                  {lead.supporting_evidence_ids.map((evId) => (
                    <button
                      key={evId}
                      onClick={() => openEvidence(evId)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs font-mono font-medium text-neutral-800 hover:bg-blue-50 hover:text-blue-700 transition-colors cursor-pointer"
                    >
                      <FileText className="h-3 w-3 text-neutral-500" />
                      {evId}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Officer Decision Bar */}
            <div className="rounded-xl border border-neutral-200/90 bg-white p-5 shadow-xs space-y-3">
              <h3 className="text-sm font-bold text-neutral-900">Investigative Action &amp; Triage</h3>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => submit('ACCEPT')}
                  disabled={decide.isPending}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-xs sm:text-sm font-bold text-white transition-colors hover:bg-emerald-700 shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  <CheckCircle2 className="h-4 w-4" /> Accept Lead
                </button>
                <button
                  onClick={() => submit('REJECT')}
                  disabled={decide.isPending}
                  className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-5 py-2.5 text-xs sm:text-sm font-bold text-red-800 transition-colors hover:bg-red-100 disabled:opacity-50 cursor-pointer"
                >
                  <XCircle className="h-4 w-4" /> Reject Lead
                </button>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* Forensic Evidence Drawer */}
      <EvidenceDrawer
        relationshipId={evidenceDrawerEdgeId}
        evidenceId={evidenceDrawerEvidenceId}
        onClose={() => {
          setEvidenceDrawerEdgeId(null)
          setEvidenceDrawerEvidenceId(null)
        }}
      />
    </div>
  )
}
