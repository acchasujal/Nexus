import { useState, useMemo, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { apiClient } from '@/lib/apiClient'
import { 
  ShieldAlert, 
  Search, 
  Filter, 
  Network, 
  FileText, 
  Users, 
  ArrowRight,
  ShieldAlert,
} from 'lucide-react'
import { CsvIngestionPanel } from '@/components/CsvIngestionPanel'

interface InvestigationItem {
  id: string
  fir_number?: string
  title?: string
  status?: string
  priority?: string
  station?: string
  district?: string
  offence_category?: string
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
        setInvestigations(Array.isArray(data) ? data : [])
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
          setInvestigations(Array.isArray(data) ? data : [])
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
      const matchesSearch = 
        !searchQuery ||
        item.fir_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.station_name?.toLowerCase().includes(searchQuery.toLowerCase())

      const matchesDistrict = districtFilter === 'all' || item.district === districtFilter
      const matchesCategory = categoryFilter === 'all' || item.offence_category === categoryFilter

      return matchesSearch && matchesDistrict && matchesCategory
    })
  }, [investigations, searchQuery, districtFilter, categoryFilter])

  // Unique filter options
  const districts = useMemo(() => {
    return Array.from(new Set(investigations.map((i) => i.district).filter(Boolean)))
  }, [investigations])

  const categories = useMemo(() => {
    return Array.from(new Set(investigations.map((i) => i.offence_category).filter(Boolean)))
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
          <div className="text-xs text-neutral-600">{row.offence_category}</div>
        </div>
      ),
    },
    {
      header: 'Police Station / District',
      accessorKey: 'station_name',
      cell: (row) => (
        <div>
          <div className="text-neutral-800 font-medium">{row.station_name}</div>
          <div className="text-xs text-neutral-600">{row.district}</div>
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2.5">
            <ShieldAlert className="h-6 w-6 text-blue-600" />
            Active Investigation Worklist
          </h1>
          <p className="text-sm text-neutral-600 mt-1">
            Browse and query ongoing criminal investigations and cross-case intelligence graphs.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3 rounded-xl border border-neutral-200 shadow-sm">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search FIR, title, police station..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-neutral-50 border border-neutral-300 rounded-lg pl-9 pr-3 py-1.5 text-xs text-neutral-900 placeholder-neutral-500 focus:bg-white focus:outline-none focus:border-blue-600 transition-colors"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-neutral-400 shrink-0" />
          <select
            value={districtFilter}
            onChange={(e) => setDistrictFilter(e.target.value)}
            className="w-full bg-neutral-50 border border-neutral-300 rounded-lg px-2.5 py-1.5 text-xs text-neutral-900 focus:bg-white focus:outline-none focus:border-blue-600 transition-colors"
          >
            <option value="all">All Districts</option>
            {districts.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-neutral-400 shrink-0" />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-full bg-neutral-50 border border-neutral-300 rounded-lg px-2.5 py-1.5 text-xs text-neutral-900 focus:bg-white focus:outline-none focus:border-blue-600 transition-colors"
          >
            <option value="all">All Offence Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Csv Ingestion Interface */}
      <CsvIngestionPanel />

      {/* Content */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : (
        <DataTable
          data={filteredData}
          columns={columns}
          onRowClick={(row) => navigate(`/cases/${row.id}`)}
        />
      )}
    </div>
  )
}
