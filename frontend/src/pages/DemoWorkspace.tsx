import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Network, LogOut } from 'lucide-react'
import { useAuth, CANONICAL_OFFICERS } from '@/contexts/AuthContext'
import { useRecoveringQuery } from '@/hooks/useRecoveringQuery'
import { isDemoMode, getDemoRole } from '@/lib/demoMode'
import { DEMO_BASELINE } from '@/lib/demoBaseline'
import { apiClient } from '@/lib/apiClient'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { MetricCard } from '@/components/ui/MetricCard'
import type { UserRole, InvestigationSummaryResponse } from '@shared/contracts/api'

const CONNECTION_DEADLINE_MS = 120_000
const INITIAL_ROWS = 10
const columns: ColumnDef<InvestigationSummaryResponse>[] = [
  { header: 'FIR / Case ID', accessorKey: 'fir_number' },
  { header: 'Investigation', accessorKey: 'title' },
  { header: 'District', accessorKey: 'district' },
  { header: 'Status', accessorKey: 'status' },
]

// No local role ever becomes an AuthContext session. This surface exposes only
// the bundled synthetic snapshot until a real server login establishes access.
export default function DemoWorkspace() {
  const location = useLocation()
  const navigate = useNavigate()
  const { login, logout, isAuthenticated, role } = useAuth()
  const requestedRole = (location.state as { role?: UserRole } | null)?.role ?? getDemoRole()
  const demoRole = requestedRole && ['IO', 'SHO', 'SP', 'ADMIN'].includes(requestedRole) ? requestedRole : null
  const [connection, setConnection] = useState<'connecting' | 'offline' | 'authenticated'>('connecting')
  const [attempt, setAttempt] = useState(0)
  const [search, setSearch] = useState('')
  const enabled = isDemoMode() && !!demoRole && connection === 'authenticated' && isAuthenticated && role === demoRole

  const bootstrap = useRecoveringQuery({
    queryKey: ['demo', demoRole, 'bootstrap'],
    queryFn: () => apiClient.getIntelligenceBootstrap(),
    enabled,
    staleTime: 30_000,
  }, DEMO_BASELINE.bootstrap)
  const worklist = useRecoveringQuery({
    queryKey: ['demo', demoRole, 'investigations'],
    queryFn: () => apiClient.getInvestigations(),
    enabled,
    staleTime: 30_000,
  }, DEMO_BASELINE.entryWorklist)

  useEffect(() => {
    if (!isDemoMode() || !demoRole) return
    const controller = new AbortController()
    const deadline = setTimeout(() => controller.abort(new DOMException('Connection deadline exceeded', 'TimeoutError')), CONNECTION_DEADLINE_MS)
    // Start after paint; strict-mode cleanup cancels its first scheduled attempt.
    const start = setTimeout(() => {
      setConnection('connecting')
      void login({ username: CANONICAL_OFFICERS[demoRole].badgeNumber, role: demoRole, password: 'nexus-demo-passcode' },
        { signal: controller.signal, background: true })
        .then(() => { if (!controller.signal.aborted) setConnection('authenticated') })
        .catch(() => { if (!controller.signal.aborted) setConnection('offline') })
        .finally(() => clearTimeout(deadline))
    }, 0)
    const expired = () => setConnection('offline')
    controller.signal.addEventListener('abort', expired, { once: true })
    return () => {
      clearTimeout(start)
      clearTimeout(deadline)
      controller.signal.removeEventListener('abort', expired)
      controller.abort()
    }
  }, [demoRole, login, attempt])

  if (!isDemoMode() || !demoRole) return <Navigate to="/login" replace />

  const bothLive = !bootstrap.isBaseline && !worklist.isBaseline && bootstrap.isSuccess && worklist.isSuccess
  const paused = connection === 'offline' || (connection === 'authenticated' && role !== demoRole)
    || (enabled && !bootstrap.isFetching && !worklist.isFetching && !bothLive)
  const syncLabel = bothLive ? 'Live data connected' : paused ? 'Offline demo' : 'Demo snapshot · Connecting'
  const kpis = (bootstrap.data ?? DEMO_BASELINE.bootstrap).kpis
  const rows = worklist.data ?? DEMO_BASELINE.entryWorklist
  const visibleRows = rows.filter(item => `${item.fir_number} ${item.title} ${item.district}`.toLowerCase().includes(search.toLowerCase()))
  const dataLabel = bootstrap.isBaseline || !bootstrap.data ? 'Demo snapshot' : 'Live API data'

  return (
    <div className="min-h-[100svh] bg-neutral-50 text-neutral-900">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-200 bg-white px-4 py-4 sm:px-8">
        <div className="flex items-center gap-3"><Network className="text-blue-600" aria-hidden="true" /><strong>NEXUS</strong><span className="text-xs">Read-only synthetic demo · {demoRole}</span></div>
        <button type="button" className="flex items-center gap-2 rounded px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"
          onClick={() => { logout(); navigate('/login', { replace: true }) }}><LogOut size={16} aria-hidden="true" />Exit demo</button>
      </header>
      <main className="mx-auto max-w-7xl space-y-5 p-4 sm:p-8">
        <div role="status" aria-label="Demo connection" className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
          {syncLabel}. Snapshot {DEMO_BASELINE.bootstrap.dataset_version} · {DEMO_BASELINE.entryChecksum.slice(0, 12)}
          <span className="block text-xs mt-1">Server authorization is required for full workspace actions. Snapshot records are read-only.</span>
        </div>
        {paused && <button type="button" className="rounded border border-blue-300 px-4 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"
          onClick={() => { if (enabled) { void bootstrap.refetch(); void worklist.refetch() } else setAttempt(value => value + 1) }}>Reconnect services</button>}
        <h1 className="text-2xl font-bold">Intelligence workspace</h1>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Active pulses" value={kpis?.active_pulses_count ?? 'Access unavailable'} subtext={dataLabel} />
          <MetricCard label="Evidence-linked claims" value={kpis ? `${kpis.evidence_percent}%` : 'Access unavailable'} subtext={dataLabel} />
          <MetricCard label="Affected investigations" value={kpis?.affected_cases_count ?? 'Access unavailable'} subtext={dataLabel} />
          <MetricCard label="Network changes" value={kpis?.total_changes ?? 'Access unavailable'} subtext={dataLabel} />
        </div>
        <section aria-labelledby="demo-worklist-title" className="space-y-3">
          <h2 id="demo-worklist-title" className="text-lg font-semibold">Investigation worklist</h2>
          <p className="text-sm text-neutral-600">{worklist.isBaseline || !worklist.data ? `First ${Math.min(INITIAL_ROWS, rows.length)} canonical snapshot records` : `${rows.length} live records`} · {worklist.syncError ? 'Snapshot or last confirmed records retained; synchronization unavailable.' : 'Updates automatically when services connect.'}</p>
          <label className="block text-sm font-medium" htmlFor="demo-search">Search investigations</label>
          <input id="demo-search" type="search" value={search} onChange={event => setSearch(event.target.value)}
            className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600" />
          <DataTable columns={columns} data={visibleRows} ariaLabel="Read-only synthetic investigation worklist" emptyMessage="No investigations match this search." />
        </section>
        {enabled && <Link to="/intelligence" className="inline-flex rounded bg-blue-600 px-4 py-2 font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">Open server-authenticated workspace</Link>}
      </main>
    </div>
  )
}
