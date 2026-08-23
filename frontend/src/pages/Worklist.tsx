import { useState, useMemo, useEffect } from 'react'
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
  AlertTriangle,
  ArrowRight,
  Sparkles
} from 'lucide-react'

export default function Worklist() {
  const navigate = useNavigate()
  const [investigations, setInvestigations] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [districtFilter, setDistrictFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')

  const fetchInvestigations = () => {
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
  }

  useEffect(() => {
    fetchInvestigations()
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

  const columns: ColumnDef<any>[] = [
    {
      header: 'FIR Number / Title',
      accessorKey: 'fir_number',
      cell: (row) => (
        <div>
          <div className="font-bold text-neutral-100 flex items-center gap-1.5">
            {row.fir_number}
          </div>
          <div className="text-xs text-neutral-400 max-w-sm truncate">{row.title}</div>
        </div>
      ),
    },
    {
      header: 'Category',
      accessorKey: 'offence_category',
      cell: (row) => (
        <span className="inline-flex items-center rounded-md bg-neutral-800 px-2.5 py-1 text-xs font-medium text-neutral-200 border border-neutral-700">
          {row.offence_category}
        </span>
      ),
    },
    {
      header: 'Police Station / District',
      accessorKey: 'station_name',
      cell: (row) => (
        <div>
          <div className="text-sm font-medium text-neutral-200">{row.station_name}</div>
          <div className="text-xs text-neutral-400">{row.district}</div>
        </div>
      ),
    },
    {
      header: 'Accused / Evidence',
      accessorKey: 'accused_count',
      cell: (row) => (
        <div className="flex items-center gap-3 text-xs text-neutral-300">
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5 text-blue-400" />
            {row.accused_count} Accused
          </span>
          <span className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5 text-emerald-400" />
            {row.evidence_count} Evidence
          </span>
        </div>
      ),
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (row) => (
        <span className="inline-flex items-center rounded-full bg-blue-950/70 px-2.5 py-0.5 text-xs font-semibold text-blue-400 border border-blue-800/50">
          {row.status}
        </span>
      ),
    },
    {
      header: 'Action',
      accessorKey: 'id',
      cell: (row) => (
        <button
          onClick={() => navigate(`/cases/${row.id}`)}
          className="inline-flex items-center gap-1 text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors"
        >
          Explore Graph <ArrowRight className="h-3 w-3" />
        </button>
      ),
    },
  ]

  if (isLoading) return <LoadingSkeleton layout="table" />
  if (error) return <ErrorState message={error} onRetry={fetchInvestigations} />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100 flex items-center gap-2.5">
            <ShieldAlert className="h-6 w-6 text-blue-500" />
            Active Criminal Network Investigations
          </h1>
          <p className="text-sm text-neutral-400 mt-1">
            Cross-jurisdictional intelligence overview with multi-hop link analysis and provenance tracking.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to="/network"
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-sm"
          >
            <Network className="h-4 w-4" />
            Open Graph Explorer
          </Link>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-neutral-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by FIR number, station, or title..."
            className="w-full rounded-lg border border-neutral-800 bg-neutral-900/80 pl-9 pr-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none"
          />
        </div>

        <select
          value={districtFilter}
          onChange={(e) => setDistrictFilter(e.target.value)}
          className="rounded-lg border border-neutral-800 bg-neutral-900/80 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
        >
          <option value="all">All Districts</option>
          <option value="Bengaluru Urban">Bengaluru Urban</option>
          <option value="Bengaluru Rural">Bengaluru Rural</option>
          <option value="Mysuru">Mysuru</option>
          <option value="Mangaluru">Mangaluru</option>
        </select>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-lg border border-neutral-800 bg-neutral-900/80 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
        >
          <option value="all">All Crime Categories</option>
          <option value="Narcotics & Drug Trafficking">Narcotics & Drug Trafficking</option>
          <option value="Cyber Financial Fraud & Phishing">Cyber Financial Fraud</option>
          <option value="Organized Extortion & Protection Racketeering">Organized Extortion</option>
          <option value="Illegal Arms Trafficking">Illegal Arms Trafficking</option>
          <option value="Hawala & Money Laundering">Hawala & Money Laundering</option>
        </select>
      </div>

      {/* Investigations Table */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 overflow-hidden shadow-lg">
        <DataTable
          columns={columns}
          data={filteredData}
          onRowClick={(row) => navigate(`/cases/${row.id}`)}
        />
      </div>
    </div>
  )
}
