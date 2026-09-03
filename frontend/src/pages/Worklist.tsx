import { useState, useMemo, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { apiClient } from '@/lib/apiClient'
import { PageHeader } from '@/components/ui/PageHeader'
import { MetricCard } from '@/components/ui/MetricCard'
import { SectionCard } from '@/components/ui/SectionCard'
import { 
  ShieldAlert, 
  Search, 
  Network, 
  FileText, 
  Users, 
  ArrowRight,
  Briefcase,
  MapPin,
} from 'lucide-react'
import { CsvIngestionPanel } from '@/components/CsvIngestionPanel'

interface InvestigationItem {
  id: string
  fir_number?: string
  title?: string
  status?: string
  priority?: string
  station_name?: string
  station?: string
  district?: string
  offence_category?: string
  accused_count?: number
  total_entities?: number
  total_relationships?: number
  created_at?: string
  updated_at?: string
  days_open?: number
  io_name?: string
}

export default function Worklist() {
  const navigate = useNavigate()
  const [investigations, setInvestigations] = useState<InvestigationItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [districtFilter, setDistrictFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')

  const fetchInvestigations = useCallback(() => {
    setIsLoading(true)
    apiClient.getInvestigations()
      .then((data) => {
        setInvestigations(Array.isArray(data) ? (data as InvestigationItem[]) : [])
        setError(null)
      })
      .catch((err) => {
        console.error('Failed to load investigations:', err)
        setError('Unable to connect to NEXUS backend intelligence service.')
      })
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => {
    let isMounted = true
    apiClient.getInvestigations()
      .then((data) => {
        if (isMounted) {
          setInvestigations(Array.isArray(data) ? (data as InvestigationItem[]) : [])
          setError(null)
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('Failed to load investigations:', err)
          setError('Unable to connect to NEXUS backend intelligence service.')
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  // Filtered dataset
  const filteredData = useMemo(() => {
    return investigations.filter((item) => {
      const station = item.station_name || item.station || ''
      const matchesSearch = 
        !searchQuery ||
        item.fir_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        station.toLowerCase().includes(searchQuery.toLowerCase())

      const matchesDistrict = districtFilter === 'all' || item.district === districtFilter
      const matchesCategory = categoryFilter === 'all' || item.offence_category === categoryFilter

      return matchesSearch && matchesDistrict && matchesCategory
    })
  }, [investigations, searchQuery, districtFilter, categoryFilter])

  // Unique filter options
  const districts = useMemo(() => {
    return Array.from(new Set(investigations.map((i) => i.district).filter(Boolean))) as string[]
  }, [investigations])

  const categories = useMemo(() => {
    return Array.from(new Set(investigations.map((i) => i.offence_category).filter(Boolean))) as string[]
  }, [investigations])

  const totalAccused = useMemo(() => {
    return investigations.reduce((acc, i) => acc + (i.accused_count || 0), 0)
  }, [investigations])

  const activeInvestigations = useMemo(() => {
    return investigations.filter((i) => i.status !== 'CHARGESHEETED').length
  }, [investigations])

  const columns: ColumnDef<InvestigationItem>[] = [
    {
      header: 'FIR / Case ID',
      accessorKey: 'fir_number',
      cell: (row) => (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-600 shrink-0" />
          <span className="font-semibold text-neutral-900">{row.fir_number || row.id}</span>
        </div>
      ),
    },
    {
      header: 'Case Title & Offence',
      accessorKey: 'title',
      cell: (row) => (
        <div>
          <div className="font-medium text-neutral-900">{row.title}</div>
          <div className="text-xs text-neutral-500">{row.offence_category}</div>
        </div>
      ),
    },
    {
      header: 'Police Station / District',
      accessorKey: 'station_name',
      cell: (row) => (
        <div>
          <div className="text-neutral-800 font-medium">{row.station_name || row.station || '—'}</div>
          <div className="text-xs text-neutral-500">{row.district || '—'}</div>
        </div>
      ),
    },
    {
      header: 'Accused',
      accessorKey: 'accused_count',
      cell: (row) => (
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-800 border border-neutral-200">
          <Users className="h-3 w-3 text-neutral-500" /> {row.accused_count || 0}
        </span>
      ),
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (row) => {
        const isChargesheeted = row.status === 'CHARGESHEETED'
        return (
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
              isChargesheeted
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-blue-50 text-blue-800 border border-blue-200'
            }`}
          >
            {row.status || 'UNDER_INVESTIGATION'}
          </span>
        )
      },
    },
    {
      header: 'Actions',
      accessorKey: 'id',
      cell: (row) => (
        <div className="flex items-center gap-2">
          <Link
            to={`/cases/${row.id}`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900 font-semibold p-1 hover:bg-blue-50 rounded transition-colors"
          >
            Open <ArrowRight className="h-3 w-3" />
          </Link>
          <Link
            to={`/cases/${row.id}?tab=network`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-900 font-semibold p-1 hover:bg-emerald-50 rounded transition-colors"
          >
            <Network className="h-3 w-3" /> Graph
          </Link>
        </div>
      ),
    },
  ]

  if (error) {
    return (
      <ErrorState
        title="Failed to Load Investigations"
        description={error}
        onRetry={fetchInvestigations}
      />
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto w-full">
      {/* Page Header */}
      <PageHeader
        icon={ShieldAlert}
        title="Active Investigation Worklist"
        subtitle="Browse and query ongoing criminal investigations, accused suspects, and cross-case intelligence graphs."
      />

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Cases"
          value={investigations.length}
          icon={Briefcase}
          subtext="Registered in registry"
        />
        <MetricCard
          label="Active Inquiries"
          value={activeInvestigations}
          icon={FileText}
          badge={{ text: 'Active', variant: 'info' }}
          subtext="Under active investigation"
        />
        <MetricCard
          label="Accused Tracked"
          value={totalAccused}
          icon={Users}
          badge={{ text: 'Resolved', variant: 'success' }}
          subtext="Unique accused entities"
        />
        <MetricCard
          label="Districts Covered"
          value={districts.length}
          icon={MapPin}
          subtext="Jurisdictions active"
        />
      </div>

      {/* Hero Ingestion Utility */}
      <CsvIngestionPanel onIngestSuccess={fetchInvestigations} />

      {/* Filter Bar & Case Table */}
      <SectionCard noPadding>
        {/* Controls Bar */}
        <div className="p-4 sm:p-5 border-b border-neutral-100 bg-neutral-50/50">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="relative">
              <label htmlFor="case-search" className="sr-only">Search investigations</label>
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-neutral-400" aria-hidden="true" />
              <input
                id="case-search"
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search FIR, title, station..."
                className="w-full pl-9 pr-4 py-2 bg-white border border-neutral-200 rounded-lg text-xs sm:text-sm text-neutral-900 placeholder-neutral-400 focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition-colors shadow-2xs"
              />
            </div>

            <div className="relative">
              <label htmlFor="district-filter" className="sr-only">Filter by district</label>
              <select
                id="district-filter"
                value={districtFilter}
                onChange={(e) => setDistrictFilter(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-neutral-200 rounded-lg text-xs sm:text-sm text-neutral-800 focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition-colors shadow-2xs appearance-none cursor-pointer"
              >
                <option value="all">All Districts ({districts.length})</option>
                {districts.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <div className="relative">
              <label htmlFor="category-filter" className="sr-only">Filter by offence category</label>
              <select
                id="category-filter"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-neutral-200 rounded-lg text-xs sm:text-sm text-neutral-800 focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition-colors shadow-2xs appearance-none cursor-pointer"
              >
                <option value="all">All Offence Categories ({categories.length})</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Table Content */}
        {isLoading ? (
          <div className="p-6">
            <LoadingSkeleton layout="table" />
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={filteredData}
            onRowClick={(row) => navigate(`/cases/${row.id}`)}
          />
        )}
      </SectionCard>
    </div>
  )
}
