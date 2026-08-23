import { Link, useSearchParams, useParams } from 'react-router-dom'
import { ArrowLeft, Clock3, ShieldAlert, Network, Layers, MessageSquareCode, Calendar, FileText } from 'lucide-react'
import { DocumentScanModal } from '@/components/DocumentScanModal'
import { CaseCopilotPanel } from '@/components/CaseCopilotPanel'
import { ClockBadge } from '@/components/ClockBadge'
import { DependencyPanel } from '@/components/DependencyPanel'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { RiskBadge } from '@/components/RiskBadge'
import { useAuth } from '@/contexts/AuthContext'
import { useCaseDetail } from '@/hooks/useCaseDetail'
import { useUpdateDependency } from '@/hooks/useUpdateDependency'
import { NetworkAnalysisPanel } from '@/components/NetworkAnalysisPanel'
import { SimilarityPanel } from '@/components/SimilarityPanel'
import { InvestigationTimeline } from '@/components/InvestigationTimeline'
import { clockStatusToRisk } from '@/lib/utils'
import { useState } from 'react'
import { toast } from 'sonner'

const tabs = [
  { id: 'clock', label: 'Clock & Dependencies', icon: Clock3 },
  { id: 'dependencies', label: 'Dependencies', icon: ShieldAlert },
  { id: 'network', label: 'Network Analysis', icon: Network },
  { id: 'timeline', label: 'Investigation Timeline', icon: Calendar },
  { id: 'similarity', label: 'Similar Cases', icon: Layers },
  { id: 'copilot', label: 'Copilot', icon: MessageSquareCode },
] as const

type TabId = (typeof tabs)[number]['id']

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>()
  const { role } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)
  const [isDocModalOpen, setIsDocModalOpen] = useState(false)
  
  const activeTab = (tabs.some((tab) => tab.id === searchParams.get('tab'))
    ? searchParams.get('tab')
    : 'clock') as TabId

  const caseQuery = useCaseDetail(id)
  const dependencyUpdate = useUpdateDependency()

  if (!id) return <ErrorState message="A case identifier is required to open this record." />
  if (caseQuery.isLoading) return <LoadingSkeleton layout="detail" />
  if (caseQuery.isError) return <ErrorState message={caseQuery.error.message} onRetry={() => void caseQuery.refetch()} />
  if (!caseQuery.data) return <EmptyState message="This case record is not available." />

  const caseDetail = caseQuery.data

  const highestClockStatus = caseDetail.clocks.reduce((highest, clock) => {
    const order = { overdue: 4, red: 3, amber: 2, green: 1 }
    const currentOrder = order[clock.status as keyof typeof order] || 0
    const highestOrder = order[highest as keyof typeof order] || 0
    return currentOrder > highestOrder ? clock.status : highest
  }, 'green')
  const computedRisk = clockStatusToRisk(highestClockStatus as 'green' | 'amber' | 'red' | 'overdue')

  // Deterministic summary calculations for operational summary banner
  const breachedClocksCount = caseDetail.clocks.filter(c => c.status === 'overdue').length
  const criticalClocksCount = caseDetail.clocks.filter(c => c.status === 'red').length
  const unresolvedDepsCount = caseDetail.dependencies.filter(d => d.status !== 'resolved').length
  
  const mostCriticalDependencyName = caseDetail.dependencies.find(d => d.status === 'escalated')?.name 
    || caseDetail.dependencies.find(d => d.status !== 'resolved')?.name 
    || 'None'

  const nextRequiredAction = breachedClocksCount > 0 
    ? 'Execute supervisory case review and resolve overdue blockers immediately.'
    : unresolvedDepsCount > 0 
    ? `Obtain pending evidentiary requirements: ${mostCriticalDependencyName}.`
    : 'Monitor statutory clock deadlines for changes.'

  const investigationHealth = breachedClocksCount > 0 
    ? 'CRITICAL (Breached)'
    : criticalClocksCount > 0 
    ? 'HIGH RISK (Clock Warning)'
    : unresolvedDepsCount > 0 
    ? 'STABLE (Pending Blockers)'
    : 'EXCELLENT'

  const handleResolve = (dependencyId: string) => {
    toast.promise(
      dependencyUpdate.mutateAsync({ id: dependencyId, status: 'resolved', caseId: id }),
      {
        loading: 'Resolving dependency...',
        success: 'Dependency resolved. Worklist and escalation queue updated.',
        error: 'Failed to resolve dependency. Please try again.',
      },
    )
  }

  const activeTabLabel = tabs.find((t) => t.id === activeTab)?.label ?? activeTab

  return (
    <div className="space-y-6">
      <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2 text-small text-neutral-600">
        <Link
          to="/worklist"
          className="inline-flex min-h-11 items-center gap-2 rounded-radius-sm px-2 text-status-info hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-status-info"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to Worklist
        </Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{caseDetail.fir_number}</span>
      </nav>

      <header className="border-b border-neutral-200 pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Case detail</p>
          <span className="rounded-radius-sm border border-neutral-300 bg-neutral-100 px-2 py-1 text-caption font-semibold text-neutral-700">
            Synthetic Data
          </span>
        </div>
        <div className="mt-2 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h1 className="text-h1 font-semibold text-neutral-900">{caseDetail.fir_number}</h1>
            <p className="mt-1 text-body text-neutral-600">{caseDetail.offence_category}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setIsDocModalOpen(true)}
              className="inline-flex items-center gap-2 rounded-radius-sm bg-neutral-900 px-3 py-1.5 text-small font-semibold text-neutral-50 hover:bg-neutral-800 transition-colors shadow-xs"
            >
              <FileText className="h-4 w-4 text-status-info" /> Scan FIR / Document
            </button>
            <RiskBadge level={computedRisk} />
            <span className="text-caption text-neutral-500">Urgency level derived from statutory clock states</span>
          </div>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-4 border-t border-neutral-200 pt-4 sm:grid-cols-3 xl:grid-cols-6">
          <div>
            <dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Police station</dt>
            <dd className="mt-1 text-small font-bold text-neutral-800">{caseDetail.station_name}</dd>
          </div>
          <div>
            <dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Assigned officer</dt>
            <dd className="mt-1 text-small text-neutral-600">Awaiting assignment</dd>
          </div>
          <div>
            <dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Current stage</dt>
            <dd className="mt-1 text-small font-medium text-neutral-800">Active investigation</dd>
          </div>
          <div>
            <dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Active Clocks</dt>
            <dd className="mt-1 flex flex-wrap gap-1">
              {caseDetail.clocks.length ? (
                caseDetail.clocks.map((clock) => (
                  <ClockBadge key={clock.id} daysRemaining={clock.days_remaining} status={clock.status} />
                ))
              ) : (
                <span className="text-small text-neutral-600">None</span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Pending Blockers</dt>
            <dd className={`mt-1 text-small font-mono font-bold ${caseDetail.dependencies.filter(d => d.status !== 'resolved').length > 0 ? 'text-status-warning' : 'text-status-success'}`}>
              {caseDetail.dependencies.filter(d => d.status !== 'resolved').length}
            </dd>
          </div>
          <div>
            <dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Escalation Status</dt>
            <dd className="mt-1 text-small">
              {caseDetail.dependencies.some(d => d.status === 'escalated') ? (
                <span className="text-status-danger font-extrabold uppercase tracking-wider text-[10px]">Escalated</span>
              ) : (
                <span className="text-neutral-500 font-medium">Normal queue</span>
              )}
            </dd>
          </div>
        </dl>
      </header>

      {/* Deterministic Operational Summary Banner */}
      <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 shadow-sm grid grid-cols-1 md:grid-cols-4 gap-4 divide-y md:divide-y-0 md:divide-x divide-neutral-200">
        <div className="space-y-1">
          <span className="text-caption font-bold text-neutral-400 uppercase tracking-wider block">Operational Summary</span>
          <p className="text-small text-neutral-800 leading-normal">
            This investigation contains <span className="font-bold">{unresolvedDepsCount}</span> active evidentiary blockers. Clocks status: <span className="font-bold">{breachedClocksCount} breached</span>, <span className="font-bold text-status-warning">{criticalClocksCount} critical</span>.
          </p>
        </div>
        <div className="space-y-1 pt-3 md:pt-0 md:pl-4">
          <span className="text-caption font-bold text-neutral-400 uppercase tracking-wider block">Most Critical Blocker</span>
          <span className="text-small font-semibold text-neutral-800 block truncate">{mostCriticalDependencyName}</span>
          <span className="text-[10px] text-neutral-500">Current active dependency bottleneck</span>
        </div>
        <div className="space-y-1 pt-3 md:pt-0 md:pl-4">
          <span className="text-caption font-bold text-neutral-400 uppercase tracking-wider block">Next Required Action</span>
          <p className="text-small font-semibold text-status-info leading-tight">{nextRequiredAction}</p>
        </div>
        <div className="space-y-1 pt-3 md:pt-0 md:pl-4 flex flex-col justify-between">
          <div>
            <span className="text-caption font-bold text-neutral-400 uppercase tracking-wider block">Investigation Health</span>
            <span className={`text-small font-extrabold uppercase ${breachedClocksCount > 0 || criticalClocksCount > 0 ? 'text-status-danger animate-pulse' : 'text-status-success'}`}>
              {investigationHealth}
            </span>
          </div>
        </div>
      </div>

      {/* Tab navigation */}
      <nav
        className="overflow-x-auto border-b border-neutral-200"
        aria-label="Case detail sections"
        role="tablist"
      >
        <div className="flex min-w-max gap-5">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                id={`tab-${tab.id}`}
                aria-selected={isActive}
                aria-controls={`tabpanel-${tab.id}`}
                onClick={() => setSearchParams({ tab: tab.id })}
                className={`inline-flex items-center gap-2 border-b-2 px-1 py-3 text-small font-semibold transition-colors duration-fast ${
                  isActive
                    ? 'border-status-info text-status-info'
                    : 'border-transparent text-neutral-600 hover:border-neutral-300 hover:text-neutral-900'
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </nav>

      {/* Tab panels — each has role="tabpanel" and is labelled by its tab button */}
      {activeTab === 'clock' && (
        <div
          role="tabpanel"
          id="tabpanel-clock"
          aria-labelledby="tab-clock"
          tabIndex={0}
          className="grid gap-6 xl:grid-cols-3 focus:outline-none"
        >
          <div className="space-y-6 xl:col-span-2">
            <DependencyPanel
              dependencies={caseDetail.dependencies}
              isUpdating={dependencyUpdate.isPending}
              onResolve={handleResolve}
            />
          </div>
          <aside className="space-y-6">
            <section aria-labelledby="clock-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
              <h2 id="clock-heading" className="text-h2 font-semibold text-neutral-900">Statutory clocks</h2>
              <div className="mt-4 space-y-3">
                {caseDetail.clocks.length ? (
                  caseDetail.clocks.map((clock) => (
                    <div key={clock.id} className="rounded-radius-sm border border-neutral-200 p-3">
                      <p className="text-small font-semibold text-neutral-800">{clock.clock_type}</p>
                      <dl className="mt-2 space-y-1 text-small">
                        <div className="flex justify-between gap-3">
                          <dt className="text-neutral-600">Days remaining</dt>
                          <dd className="tabular-nums text-neutral-800">{clock.days_remaining}</dd>
                        </div>
                        <div className="flex justify-between gap-3">
                          <dt className="text-neutral-600">Status</dt>
                          <dd className="text-neutral-800">{clock.status}</dd>
                        </div>
                        <div>
                          <dt className="text-neutral-600">Statutory section</dt>
                          <dd className="mt-1 text-neutral-800">{clock.bnss_reference}</dd>
                        </div>
                      </dl>
                    </div>
                  ))
                ) : (
                  <EmptyState message="No statutory clocks are recorded for this case." />
                )}
              </div>
            </section>
            <CaseMetadata stationName={caseDetail.station_name} category={caseDetail.offence_category} />
          </aside>
        </div>
      )}

      {activeTab === 'dependencies' && (
        <div
          role="tabpanel"
          id="tabpanel-dependencies"
          aria-labelledby="tab-dependencies"
          tabIndex={0}
          className="focus:outline-none"
        >
          <DependencyPanel
            dependencies={caseDetail.dependencies}
            isUpdating={dependencyUpdate.isPending}
            onResolve={handleResolve}
          />
        </div>
      )}

      {activeTab === 'network' && (
        <div
          role="tabpanel"
          id="tabpanel-network"
          aria-labelledby="tab-network"
          tabIndex={0}
          className="focus:outline-none"
        >
          <NetworkAnalysisPanel 
            caseId={caseDetail.id} 
            selectedEntityId={selectedEntityId}
            onEntitySelect={setSelectedEntityId}
          />
        </div>
      )}

      {activeTab === 'timeline' && (
        <div
          role="tabpanel"
          id="tabpanel-timeline"
          aria-labelledby="tab-timeline"
          tabIndex={0}
          className="focus:outline-none"
        >
          <InvestigationTimeline 
            caseDetail={caseDetail}
            selectedEntityId={selectedEntityId}
            onEntitySelect={setSelectedEntityId}
          />
        </div>
      )}

      {activeTab === 'similarity' && (
        <div
          role="tabpanel"
          id="tabpanel-similarity"
          aria-labelledby="tab-similarity"
          tabIndex={0}
          className="focus:outline-none"
        >
          <SimilarityPanel caseId={caseDetail.id} firNumber={caseDetail.fir_number} />
        </div>
      )}

      {activeTab === 'copilot' && (
        <div
          role="tabpanel"
          id="tabpanel-copilot"
          aria-labelledby="tab-copilot"
          tabIndex={0}
          className="focus:outline-none"
        >
          <CaseCopilotPanel caseId={caseDetail.id} caseLabel={caseDetail.fir_number} role={role ?? 'IO'} />
        </div>
      )}

      {/* Document Intelligence Scan Modal */}
      <DocumentScanModal
        caseId={id}
        isOpen={isDocModalOpen}
        onClose={() => setIsDocModalOpen(false)}
        onConfirmed={() => void caseQuery.refetch()}
      />

      {/* Screen reader current tab announcement */}
      <p className="sr-only" role="status" aria-live="polite">
        {activeTabLabel} panel is now shown.
      </p>
    </div>
  )
}

function CaseMetadata({ stationName, category }: { stationName: string; category: string }) {
  return (
    <section aria-labelledby="metadata-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
      <h2 id="metadata-heading" className="text-h2 font-semibold text-neutral-900">Case metadata</h2>
      <dl className="mt-4 space-y-3 text-small">
        <div>
          <dt className="text-neutral-500">Police station</dt>
          <dd className="mt-1 text-neutral-800">{stationName}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Crime category</dt>
          <dd className="mt-1 text-neutral-800">{category}</dd>
        </div>
      </dl>
    </section>
  )
}
