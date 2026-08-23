import { useMemo } from 'react'
import { useWorklist } from '@/hooks/useWorklist'
import { useEscalations } from '@/hooks/useEscalations'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { StatusChip } from '@/components/StatusChip'
import { 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend,
  LineChart,
  Line,
  CartesianGrid
} from 'recharts'
import { AlertCircle, ShieldAlert, BarChart3, TrendingUp, Info } from 'lucide-react'

// Color theme variables matching index.css design tokens
const COLORS = {
  overdue: '#E11D48', // Rose 600
  red: '#EF4444',     // Red 500
  amber: '#F59E0B',   // Amber 500
  green: '#10B981',   // Emerald 500
}

interface StationSummary {
  station_name: string
  total_cases: number
  critical_cases: number
  dependency_count: number
  escalations_count: number
  rank: number
}

export default function Patterns() {
  const { data: cases, isLoading: isCasesLoading, error: casesError, refetch: refetchCases } = useWorklist()
  const { data: escalations, isLoading: isEscalationsLoading, error: escalationsError, refetch: refetchEscalations } = useEscalations()

  // 1. KPI Calculations (Deterministic client-side derivations)
  const kpiData = useMemo(() => {
    if (!cases || !escalations) return null

    const totalActive = cases.length
    const totalEscalations = escalations.length
    const breaches = cases.filter((c) => c.clock.status === 'overdue').length
    const highRisk = cases.filter((c) => c.clock.status === 'red' || c.clock.status === 'overdue').length
    const activeDependencies = cases.reduce((sum, c) => sum + c.unresolved_dependency_count, 0)

    return {
      totalActive,
      totalEscalations,
      breaches,
      highRisk,
      activeDependencies,
    }
  }, [cases, escalations])

  // 1b. Enhanced Derived Stats for KPI Card contexts and Recommendation Panel
  const derivedStats = useMemo(() => {
    if (!cases || !escalations) return null

    const overdueByStation: Record<string, number> = {}
    const redByStation: Record<string, number> = {}
    const blockedByStation: Record<string, number> = {}
    
    cases.forEach(c => {
      if (c.clock.status === 'overdue') {
        overdueByStation[c.station_name] = (overdueByStation[c.station_name] || 0) + 1
      }
      if (c.clock.status === 'red') {
        redByStation[c.station_name] = (redByStation[c.station_name] || 0) + 1
      }
      if (c.unresolved_dependency_count > 0) {
        blockedByStation[c.station_name] = (blockedByStation[c.station_name] || 0) + c.unresolved_dependency_count
      }
    })

    const topBreachedStation = Object.entries(overdueByStation).reduce((a, b) => a[1] > b[1] ? a : b, ['None', 0])[0]
    const topRedStation = Object.entries(redByStation).reduce((a, b) => a[1] > b[1] ? a : b, ['None', 0])[0]
    const topBlockedStation = Object.entries(blockedByStation).reduce((a, b) => a[1] > b[1] ? a : b, ['None', 0])[0]

    const escalatedByStation: Record<string, number> = {}
    escalations.forEach(esc => {
      if (!esc.resolved) {
        const matchedCase = cases.find(c => c.id === esc.case_id)
        if (matchedCase) {
          escalatedByStation[matchedCase.station_name] = (escalatedByStation[matchedCase.station_name] || 0) + 1
        }
      }
    })
    const topEscalatedStation = Object.entries(escalatedByStation).reduce((a, b) => a[1] > b[1] ? a : b, ['None', 0])[0]

    // Determine top violation station for supervisory recommendation
    const stationViolations: Record<string, number> = {}
    cases.forEach(c => {
      if (c.clock.status === 'red' || c.clock.status === 'overdue') {
        stationViolations[c.station_name] = (stationViolations[c.station_name] || 0) + 1
      }
    })
    const topViolationStationEntry = Object.entries(stationViolations).reduce((a, b) => a[1] > b[1] ? a : b, ['None', 0])
    const recommendationStation = topViolationStationEntry[0]
    const recommendationCount = topViolationStationEntry[1]

    return {
      topBreachedStation,
      topRedStation,
      topBlockedStation,
      topEscalatedStation,
      recommendationStation,
      recommendationCount
    }
  }, [cases, escalations])

  // 2. Clock Health Distributions
  const clockHealthData = useMemo(() => {
    if (!cases) return []

    const counts = { green: 0, amber: 0, red: 0, overdue: 0 }
    cases.forEach((c) => {
      if (c.clock.status in counts) {
        counts[c.clock.status as keyof typeof counts]++
      }
    })

    return [
      { name: 'Overdue (Breach)', value: counts.overdue, color: COLORS.overdue },
      { name: 'Critical (Red)', value: counts.red, color: COLORS.red },
      { name: 'Approaching (Amber)', value: counts.amber, color: COLORS.amber },
      { name: 'Healthy (Green)', value: counts.green, color: COLORS.green },
    ]
  }, [cases])

  // 3. Risk Distribution Mappings
  const riskDistributionData = useMemo(() => {
    if (!cases) return []

    let high = 0
    let medium = 0
    let low = 0

    cases.forEach((c) => {
      if (c.clock.status === 'red' || c.clock.status === 'overdue') {
        high++
      } else if (c.clock.status === 'amber') {
        medium++
      } else {
        low++
      }
    })

    return [
      { name: 'High Risk', count: high, fill: COLORS.red },
      { name: 'Medium Risk', count: medium, fill: COLORS.amber },
      { name: 'Low Risk', count: low, fill: COLORS.green },
    ]
  }, [cases])

  // 4. Station Aggregations (Deterministic Join)
  const stationRankings = useMemo(() => {
    if (!cases || !escalations) return []

    const summaries: Record<string, Omit<StationSummary, 'rank'>> = {}

    cases.forEach((c) => {
      if (!summaries[c.station_name]) {
        summaries[c.station_name] = {
          station_name: c.station_name,
          total_cases: 0,
          critical_cases: 0,
          dependency_count: 0,
          escalations_count: 0,
        }
      }

      const summary = summaries[c.station_name]
      summary.total_cases++
      summary.dependency_count += c.unresolved_dependency_count
      if (c.clock.status === 'red' || c.clock.status === 'overdue') {
        summary.critical_cases++
      }

      // Join count of active escalations for this case
      const hasEscalation = escalations.some((esc) => esc.case_id === c.id && !esc.resolved)
      if (hasEscalation) {
        summary.escalations_count++
      }
    })

    // Convert to list, sort by critical cases, then total cases
    const list = Object.values(summaries).sort((a, b) => {
      if (b.critical_cases !== a.critical_cases) {
        return b.critical_cases - a.critical_cases
      }
      return b.total_cases - a.total_cases
    })

    // Assign ranks
    return list.map((item, idx) => ({
      ...item,
      rank: idx + 1,
    })) as StationSummary[]
  }, [cases, escalations])

  // 5. Mock Escalation Trends (Current snapshot fallback)
  const escalationSnapshotData = useMemo(() => {
    if (!escalations) return []

    return [
      { date: 'Jul 10', escalations: Math.max(0, escalations.length - 2) },
      { date: 'Jul 12', escalations: Math.max(0, escalations.length - 1) },
      { date: 'Jul 14', escalations: escalations.length },
      { date: 'Current (Snapshot)', escalations: escalations.length }
    ]
  }, [escalations])

  // Columns for the Station Summary DataTable
  const stationColumns: ColumnDef<StationSummary>[] = [
    {
      header: 'Rank',
      accessorKey: 'rank',
      cell: (row) => <span className="font-bold text-neutral-600 font-mono">#{row.rank}</span>
    },
    {
      header: 'Police Station',
      accessorKey: 'station_name'
    },
    {
      header: 'Active Cases',
      accessorKey: 'total_cases',
      cell: (row) => <span className="font-mono">{row.total_cases}</span>
    },
    {
      header: 'Critical/Breached Clocks',
      accessorKey: 'critical_cases',
      cell: (row) => (
        <span className={`font-semibold font-mono ${row.critical_cases > 0 ? 'text-status-danger' : 'text-status-success'}`}>
          {row.critical_cases}
        </span>
      )
    },
    {
      header: 'Active Blockers',
      accessorKey: 'dependency_count',
      cell: (row) => (
        <StatusChip 
          status={row.dependency_count > 0 ? 'stale' : 'healthy'}
          label={`${row.dependency_count} Pending`}
        />
      )
    },
    {
      header: 'Active Escalations',
      accessorKey: 'escalations_count',
      cell: (row) => (
        <span className={`font-semibold font-mono ${row.escalations_count > 0 ? 'text-status-warning' : 'text-neutral-500'}`}>
          {row.escalations_count}
        </span>
      )
    }
  ]

  // Handle Loading States
  if (isCasesLoading || isEscalationsLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-h1 font-bold text-neutral-900">Patterns & Analytics</h1>
          <p className="text-body text-neutral-500">Compiling investigation patterns and statutory clock states...</p>
        </div>
        <LoadingSkeleton layout="card" />
        <LoadingSkeleton layout="table" />
      </div>
    )
  }

  // Handle Error States
  if (casesError || escalationsError) {
    return (
      <div className="py-12">
        <ErrorState
          message="Failed to synchronize with analytics data sources. Check connection to the mock database."
          onRetry={() => {
            refetchCases()
            refetchEscalations()
          }}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6 outline-none" tabIndex={0} aria-label="Patterns and Analytics Dashboard">
      {/* Title Block */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-neutral-200 pb-4">
        <div>
          <h1 className="text-h1 font-bold text-neutral-900">Patterns &amp; Analytics</h1>
          <p className="text-body text-neutral-500">
            Executive operational intelligence dashboard for district investigation control
          </p>
        </div>
      </div>

      {/* Deterministic Operational Recommendations Panel */}
      {derivedStats && derivedStats.recommendationStation !== 'None' && (
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 shadow-sm flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-status-danger shrink-0 mt-0.5" />
          <div className="text-small text-neutral-800">
            <span className="font-bold text-neutral-900">Operational Recommendation:</span>{' '}
            Station <span className="font-bold">{derivedStats.recommendationStation}</span> registers{' '}
            <span className="font-bold text-status-danger">{derivedStats.recommendationCount}</span> critical statutory violations (Red/Overdue clocks). Immediate supervisory review and blocker resolution are recommended.
          </div>
        </div>
      )}

      {/* KPI Cards Row (Stripe/Linear style) */}
      {kpiData && derivedStats && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 shadow-xs">
            <div className="text-caption font-semibold text-neutral-500 uppercase tracking-wide">Total Active Cases</div>
            <div className="text-h1 font-bold text-neutral-800 mt-2 font-mono">{kpiData.totalActive}</div>
            <div className="mt-2 text-caption text-neutral-400">Active criminal investigations</div>
          </div>
          
          <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 shadow-xs">
            <div className="text-caption font-semibold text-status-warning uppercase tracking-wide">Escalated Cases</div>
            <div className="text-h1 font-bold text-status-warning mt-2 font-mono">{kpiData.totalEscalations}</div>
            <div className="mt-2 text-caption text-neutral-500 truncate">
              Top: <span className="font-semibold text-neutral-700">{derivedStats.topEscalatedStation}</span>
            </div>
          </div>

          <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 shadow-xs">
            <div className="text-caption font-semibold text-status-danger uppercase tracking-wide">Statutory Breaches</div>
            <div className="text-h1 font-bold text-status-danger mt-2 font-mono">{kpiData.breaches}</div>
            <div className="mt-2 text-caption text-neutral-500 truncate">
              Highest: <span className="font-semibold text-neutral-700">{derivedStats.topBreachedStation}</span>
            </div>
          </div>

          <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 shadow-xs">
            <div className="text-caption font-semibold text-status-danger uppercase tracking-wide font-bold">High Risk Clocks</div>
            <div className="text-h1 font-bold text-status-danger mt-2 font-mono">{kpiData.highRisk}</div>
            <div className="mt-2 text-caption text-neutral-500 truncate">
              Highest: <span className="font-semibold text-neutral-700">{derivedStats.topRedStation}</span>
            </div>
          </div>

          <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 shadow-xs">
            <div className="text-caption font-semibold text-status-info uppercase tracking-wide">Active Dependencies</div>
            <div className="text-h1 font-bold text-status-info mt-2 font-mono">{kpiData.activeDependencies}</div>
            <div className="mt-2 text-caption text-neutral-500 truncate">
              Highest: <span className="font-semibold text-neutral-700">{derivedStats.topBlockedStation}</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Visualizations Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Clock Health Distribution */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-6 shadow-sm">
          <div className="flex items-center space-x-2 mb-4">
            <BarChart3 className="h-5 w-5 text-neutral-500" />
            <h2 className="text-h2 font-semibold text-neutral-800">Clock Health Distribution</h2>
          </div>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={clockHealthData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {clockHealthData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend layout="horizontal" align="center" verticalAlign="bottom" />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-caption text-neutral-500 border-t border-neutral-200 pt-4">
            <div className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-status-success mr-2" /> Green: &gt; 14 days remaining</div>
            <div className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-status-warning mr-2" /> Amber: 7-14 days remaining</div>
            <div className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-status-danger mr-2" /> Red: &lt; 7 days remaining</div>
            <div className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-status-danger mr-2" /> Overdue: Deadline passed</div>
          </div>
        </div>

        {/* Risk Distribution Chart */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-6 shadow-sm">
          <div className="flex items-center space-x-2 mb-4">
            <ShieldAlert className="h-5 w-5 text-neutral-500" />
            <h2 className="text-h2 font-semibold text-neutral-800">Risk Profile Mappings</h2>
          </div>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskDistributionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={45}>
                  {riskDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 border-t border-neutral-200 pt-4 text-caption text-neutral-500 flex items-start space-x-2">
            <Info className="h-4 w-4 text-neutral-400 mt-0.5 shrink-0" />
            <p>Risk is computed strictly from statutory clock statuses. Low corresponds to Green, Medium to Amber, and High to Red or Overdue. No local heuristics are calculated.</p>
          </div>
        </div>
      </div>

      {/* Station Overview Table */}
      <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-6 shadow-sm space-y-4">
        <h2 className="text-h2 font-semibold text-neutral-800 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-neutral-500" /> Station Performance Rankings
        </h2>
        <DataTable
          columns={stationColumns}
          data={stationRankings}
          isLoading={false}
        />
      </div>

      {/* Analytics Limitations & Unpopulated Channels */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Officer Workload Fallback */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-100 p-6 shadow-sm relative flex flex-col justify-between">
          <div>
            <h3 className="font-semibold text-neutral-600 uppercase text-caption">Officer Workloads</h3>
            <p className="text-small text-neutral-500 mt-2">
              Visualizes caseload distributions and blocker assignments per Investigating Officer.
            </p>
          </div>
          <div className="mt-6 p-4 border border-dashed border-neutral-300 rounded-radius-sm bg-neutral-50 text-center">
            <AlertCircle className="mx-auto h-8 w-8 text-neutral-400 mb-2" />
            <p className="text-caption font-semibold text-neutral-500">Awaiting continuous event capture</p>
            <p className="text-caption text-neutral-400 mt-1">Operational analytics require historical investigation history</p>
          </div>
        </div>

        {/* Dependency Analytics Fallback */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-100 p-6 shadow-sm relative flex flex-col justify-between">
          <div>
            <h3 className="font-semibold text-neutral-600 uppercase text-caption">Dependency Blocker Analytics</h3>
            <p className="text-small text-neutral-500 mt-2">
              Analyzes FSL turnaround metrics, stale blocker waiting times, and laboratory backlogs.
            </p>
          </div>
          <div className="mt-6 p-4 border border-dashed border-neutral-300 rounded-radius-sm bg-neutral-50 text-center">
            <AlertCircle className="mx-auto h-8 w-8 text-neutral-400 mb-2" />
            <p className="text-caption font-semibold text-neutral-500">Awaiting continuous case detail synchronization</p>
            <p className="text-caption text-neutral-400 mt-1">Evidence trails become available after audit capture</p>
          </div>
        </div>

        {/* Escalation Snapshot trend */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-neutral-700 uppercase text-caption">Escalation Trends</h3>
            <span className="text-[10px] bg-neutral-200 text-neutral-600 px-2 py-0.5 rounded-radius-sm font-semibold uppercase tracking-wider">Current Snapshot</span>
          </div>
          <div className="h-[120px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={escalationSnapshotData} margin={{ top: 5, right: 5, left: -30, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" stroke="#888888" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#888888" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip />
                <Line type="monotone" dataKey="escalations" stroke={COLORS.amber} strokeWidth={2} activeDot={{ r: 4 }} dot={{ r: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="text-[10px] text-neutral-400 mt-2 leading-normal">
            *Historical timeline models are simulated. Real historical metrics require database audit logging.
          </p>
        </div>
      </div>
    </div>
  )
}
