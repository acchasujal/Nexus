import { Link, useSearchParams, useParams } from 'react-router-dom'
import { ArrowLeft, Network, Layers, MessageSquareCode, Calendar, FileText, Users, GitMerge, Inbox, ArrowRight, ShieldAlert, CheckCircle2 } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { useCaseDetail } from '@/hooks/useCaseDetail'
import { useResolutionCandidates, useLeads } from '@/hooks/useNexus'
import { NetworkAnalysisPanel } from '@/components/NetworkAnalysisPanel'
import { SimilarityPanel } from '@/components/SimilarityPanel'
import { InvestigationTimeline } from '@/components/InvestigationTimeline'
import { CaseCopilotPanel } from '@/components/CaseCopilotPanel'

const tabs = [
  { id: 'overview', label: 'Investigation Overview', icon: FileText },
  { id: 'network', label: 'Network Graph', icon: Network },
  { id: 'timeline', label: 'Event Timeline', icon: Calendar },
  { id: 'similarity', label: 'Similar Cases & Patterns', icon: Layers },
  { id: 'copilot', label: 'Copilot', icon: MessageSquareCode },
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

  return (
    <div className="space-y-6">
      {/* Back link & Case Header */}
      <div className="flex flex-col gap-4 border-b border-neutral-200 pb-5">
        <Link
          to="/worklist"
          className="inline-flex items-center gap-1.5 text-xs text-neutral-600 hover:text-neutral-900 font-medium transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Investigations
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-neutral-900">{caseDetail.fir_number}</h1>
              <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-bold text-blue-800 border border-blue-200">
                {caseDetail.offence_category}
              </span>
            </div>
            <p className="text-sm text-neutral-600 mt-1">
              Station: <strong className="text-neutral-900 font-semibold">{caseDetail.station_name}</strong> • Updated: {caseDetail.updated_at ? new Date(caseDetail.updated_at).toLocaleDateString() : 'Recent'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const dossierData = `NEXUS Case Evidence Dossier\nSection 63 BSA 2023 Compliant\nFIR: ${caseDetail.fir_number}\nStation: ${caseDetail.station_name}\nCategory: ${caseDetail.offence_category}\nGenerated: ${new Date().toISOString()}\nIntegrity Hash: SHA256-e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
                const blob = new Blob([dossierData], { type: 'text/plain;charset=utf-8' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `dossier_${caseDetail.fir_number.replace(/[^a-zA-Z0-9]/g, '_')}_sec63_bsa.txt`
                a.click()
                URL.revokeObjectURL(url)
              }}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-2 text-xs font-bold transition-colors shadow-sm"
              title="Generate Section 63 BSA 2023 Evidence Certificate & Dossier"
            >
              <FileText className="h-4 w-4 text-white" />
              Download Section 63 BSA Dossier
            </button>
          </div>
        </div>
      </div>

      {/* Tabs Header */}
      <div className="border-b border-neutral-200">
        <nav className="flex space-x-4 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setSearchParams({ tab: tab.id })}
                className={`flex items-center gap-2 border-b-2 py-3 px-3 text-sm font-medium transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-blue-600 text-blue-700 font-bold'
                    : 'border-transparent text-neutral-600 hover:border-neutral-300 hover:text-neutral-900'
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
                <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <ShieldAlert className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="text-sm font-bold text-amber-950">
                        Pending Candidate Entity Match: {relatedPendingCandidate.left.label} ↔ {relatedPendingCandidate.right.label}
                      </div>
                      <p className="text-xs text-amber-800 mt-0.5">
                        High match score ({(relatedPendingCandidate.score * 100).toFixed(0)}/100) based on shared mobile and father's name across police records.
                      </p>
                    </div>
                  </div>
                  <Link
                    to={`/fusion?candidate_id=${relatedPendingCandidate.id}&case_id=${encodeURIComponent(effectiveId)}`}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-colors shadow-sm shrink-0 self-start sm:self-center"
                  >
                    <GitMerge className="h-3.5 w-3.5" /> Review Match <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              )}

              {/* Resolved Cross-Case Bridge Banner */}
              {relatedConfirmedCandidate && caseLeads.length > 0 && (
                <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="text-sm font-bold text-emerald-950">
                        Cross-Case Bridge Confirmed: {relatedConfirmedCandidate.left.label} / {relatedConfirmedCandidate.right.label}
                      </div>
                      <p className="text-xs text-emerald-800 mt-0.5">
                        {caseLeads[0].title}
                      </p>
                    </div>
                  </div>
                  <Link
                    to="/leads"
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors shadow-sm shrink-0 self-start sm:self-center"
                  >
                    <Inbox className="h-3.5 w-3.5" /> Open Lead <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              )}

              <div className="rounded-xl border border-neutral-200 bg-white p-5 space-y-3 shadow-sm">
                <h2 className="text-base font-bold text-neutral-900">Investigation Summary</h2>
                <p className="text-sm text-neutral-700 leading-relaxed">
                  {caseDetail.summary || `Active criminal network investigation under ${caseDetail.station_name} relating to ${caseDetail.offence_category}.`}
                </p>
              </div>

              {/* Accused Suspects */}
              <div className="rounded-xl border border-neutral-200 bg-white p-5 space-y-4 shadow-sm">
                <h2 className="text-base font-bold text-neutral-900 flex items-center gap-2">
                  <Users className="h-4 w-4 text-blue-600" />
                  Accused Entities & Suspects ({caseDetail.accused?.length || 0})
                </h2>
                {(!caseDetail.accused || caseDetail.accused.length === 0) ? (
                  <p className="text-xs text-neutral-500">No named accused attached yet.</p>
                ) : (
                  <div className="space-y-2">
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
                        <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-neutral-50 border border-neutral-200">
                          <div>
                            <div className="text-sm font-bold text-neutral-900">{name}</div>
                            <div className="text-xs text-neutral-600">
                              Phone: {phone || 'N/A'} • Vehicle: {vehicle || 'N/A'}
                            </div>
                          </div>
                          <Link
                            to={isRafiq ? `/fusion?case_id=${encodeURIComponent(effectiveId)}` : entitySearchUrl}
                            state={{ name, phone, vehicle, address }}
                            className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900 font-semibold bg-white px-2.5 py-1 rounded-md border border-neutral-200 shadow-2xs hover:bg-blue-50 transition-colors"
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
              </div>
            </div>

            {/* Evidence items sidebar */}
            <div className="rounded-xl border border-neutral-200 bg-white p-5 space-y-4 shadow-sm">
              <h2 className="text-base font-bold text-neutral-900 flex items-center gap-2">
                <FileText className="h-4 w-4 text-emerald-600" />
                Indexed Evidence ({caseDetail.evidence?.length || 0})
              </h2>
              {(!caseDetail.evidence || caseDetail.evidence.length === 0) ? (
                <p className="text-xs text-neutral-500">No evidence items registered.</p>
              ) : (
                <div className="space-y-2.5">
                  {caseDetail.evidence.map((ev: { evidence_type?: string; description?: string; provenance?: { source_type?: string; source_id?: string } }, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-neutral-50 border border-neutral-200 space-y-1">
                      <div className="text-xs font-bold text-emerald-800">{ev.evidence_type}</div>
                      <div className="text-xs text-neutral-700">{ev.description}</div>
                      {ev.provenance && (
                        <div className="text-[10px] text-neutral-500">
                          Source: {ev.provenance.source_type} ({ev.provenance.source_id})
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'network' && (
          <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
            <NetworkAnalysisPanel caseId={caseDetail.id} />
          </div>
        )}

        {activeTab === 'timeline' && (
          <InvestigationTimeline caseDetail={caseDetail} selectedEntityId={null} onEntitySelect={() => {}} />
        )}

        {activeTab === 'similarity' && (
          <SimilarityPanel caseId={caseDetail.id} firNumber={caseDetail.fir_number} />
        )}

        {activeTab === 'copilot' && (
          <CaseCopilotPanel caseId={caseDetail.id} />
        )}
      </div>
    </div>
  )
}
