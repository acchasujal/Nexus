import { Link, useSearchParams, useParams } from 'react-router-dom'
import { ArrowLeft, Network, Layers, MessageSquareCode, Calendar, FileText, Users, Building, AlertCircle } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { useCaseDetail } from '@/hooks/useCaseDetail'
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
  const { id } = useParams<{ id: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  
  const activeTab = (tabs.some((tab) => tab.id === searchParams.get('tab'))
    ? searchParams.get('tab')
    : 'overview') as TabId

  const caseQuery = useCaseDetail(id)

  if (!id) return <ErrorState message="A case identifier is required to open this record." />
  if (caseQuery.isLoading) return <LoadingSkeleton layout="detail" />
  if (caseQuery.isError) return <ErrorState message={caseQuery.error.message} onRetry={() => void caseQuery.refetch()} />
  if (!caseQuery.data) return <EmptyState message="This case record is not available." />

  const caseDetail = caseQuery.data

  return (
    <div className="space-y-6">
      {/* Back link & Case Header */}
      <div className="flex flex-col gap-4 border-b border-neutral-800 pb-5">
        <Link
          to="/worklist"
          className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-neutral-200 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Investigations
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-neutral-100">{caseDetail.fir_number}</h1>
              <span className="rounded-full bg-blue-950 px-2.5 py-0.5 text-xs font-semibold text-blue-400 border border-blue-800">
                {caseDetail.offence_category}
              </span>
            </div>
            <p className="text-sm text-neutral-400 mt-1">
              Station: <strong className="text-neutral-300">{caseDetail.station_name}</strong> • Updated: {caseDetail.updated_at ? new Date(caseDetail.updated_at).toLocaleDateString() : 'Recent'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs Header */}
      <div className="border-b border-neutral-800">
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
                    ? 'border-blue-500 text-blue-400 font-semibold'
                    : 'border-transparent text-neutral-400 hover:border-neutral-700 hover:text-neutral-300'
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
              <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-3">
                <h2 className="text-base font-semibold text-white">Investigation Summary</h2>
                <p className="text-sm text-neutral-300 leading-relaxed">
                  {caseDetail.summary || `Active criminal network investigation under ${caseDetail.station_name} relating to ${caseDetail.offence_category}.`}
                </p>
              </div>

              {/* Accused Suspects */}
              <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-4">
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <Users className="h-4 w-4 text-blue-400" />
                  Accused Entities & Suspects ({caseDetail.accused?.length || 0})
                </h2>
                {(!caseDetail.accused || caseDetail.accused.length === 0) ? (
                  <p className="text-xs text-neutral-500">No named accused attached yet.</p>
                ) : (
                  <div className="space-y-2">
                    {caseDetail.accused.map((acc: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-neutral-950/70 border border-neutral-800">
                        <div>
                          <div className="text-sm font-bold text-white">{acc.full_name || acc.name || acc.id}</div>
                          <div className="text-xs text-neutral-400">
                            Phone: {acc.phone_number || 'N/A'} • Vehicle: {acc.vehicle_number || 'N/A'}
                          </div>
                        </div>
                        <Link
                          to={`/entities`}
                          className="text-xs text-blue-400 hover:text-blue-300"
                        >
                          Resolve Entity →
                        </Link>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Evidence items sidebar */}
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-4">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <FileText className="h-4 w-4 text-emerald-400" />
                Indexed Evidence ({caseDetail.evidence?.length || 0})
              </h2>
              {(!caseDetail.evidence || caseDetail.evidence.length === 0) ? (
                <p className="text-xs text-neutral-500">No evidence items registered.</p>
              ) : (
                <div className="space-y-2.5">
                  {caseDetail.evidence.map((ev: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-neutral-950/70 border border-neutral-800 space-y-1">
                      <div className="text-xs font-semibold text-emerald-400">{ev.evidence_type}</div>
                      <div className="text-xs text-neutral-300">{ev.description}</div>
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
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
            <NetworkAnalysisPanel caseId={caseDetail.id} />
          </div>
        )}

        {activeTab === 'timeline' && (
          <InvestigationTimeline caseId={caseDetail.id} />
        )}

        {activeTab === 'similarity' && (
          <SimilarityPanel caseId={caseDetail.id} />
        )}

        {activeTab === 'copilot' && (
          <CaseCopilotPanel caseId={caseDetail.id} />
        )}
      </div>
    </div>
  )
}
