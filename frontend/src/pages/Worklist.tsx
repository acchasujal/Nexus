import { useState, useMemo, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { apiClient } from '@/lib/apiClient'
import { useResetDemo } from '@/hooks/useNexus'
import type { NexusIngestResponse } from '@shared/contracts/api'
import { 
  ShieldAlert, 
  Search, 
  Filter, 
  Network, 
  FileText, 
  Users, 
  ArrowRight,
  Upload,
  Phone,
  Landmark,
  RotateCcw,
  CheckCircle2,
  Loader2,
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

  // Ingestion state
  const [ingestingType, setIngestingType] = useState<string | null>(null)
  const [ingestResult, setIngestResult] = useState<NexusIngestResponse | null>(null)
  const [ingestError, setIngestError] = useState<string | null>(null)
  const resetDemo = useResetDemo()

  const handleIngest = async (sourceType: string, fileName: string) => {
    setIngestingType(sourceType)
    setIngestError(null)
    try {
      const res = await apiClient.nexusIngest([{ source_type: sourceType, file_name: fileName }])
      setIngestResult(res)
    } catch (err) {
      setIngestError(err instanceof Error ? err.message : 'Ingestion failed')
    } finally {
      setIngestingType(null)
    }
  }

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

  const columns: ColumnDef<any>[] = [
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
            to={`/investigations/${row.id}`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900 font-semibold p-1 hover:bg-blue-50 rounded transition-colors"
          >
            Open <ArrowRight className="h-3 w-3" />
          </Link>
          <Link
            to={`/network?case_id=${row.id}`}
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

      {/* Hero: Load Demo Investigation Sources */}
      <section className="rounded-xl border border-blue-200 bg-white p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-neutral-200 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <Upload className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-neutral-900 flex items-center gap-2">
                Load Demo Investigation Sources
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-200">Golden Fixture</span>
              </h2>
              <p className="text-xs text-neutral-600">
                Ingest synthetic police files, phone records, and banking logs to populate the intelligence graph.
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              resetDemo.mutate()
              setIngestResult(null)
            }}
            disabled={resetDemo.isPending}
            className="self-start sm:self-auto flex items-center gap-1.5 text-xs text-neutral-700 hover:text-neutral-900 px-3 py-1.5 rounded-lg border border-neutral-300 bg-white hover:bg-neutral-50 shadow-sm transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5 text-neutral-500" />
            {resetDemo.isPending ? 'Resetting…' : 'Reset Demo'}
          </button>
        </div>

        {/* 3 Action Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            onClick={() => handleIngest('FIR', 'fir_141_207_2026.txt')}
            disabled={ingestingType !== null}
            className="flex items-center justify-between p-3.5 rounded-lg border border-sky-200 bg-sky-50/50 hover:bg-sky-50 text-left transition-all disabled:opacity-50 shadow-sm"
          >
            <div className="flex items-center gap-2.5">
              <FileText className="h-5 w-5 text-sky-600 shrink-0" />
              <div>
                <div className="text-xs font-bold text-sky-950">Load FIR Fixture</div>
                <div className="text-[11px] text-neutral-600">FIR 141 &amp; 207 Records</div>
              </div>
            </div>
            {ingestingType === 'FIR' ? (
              <Loader2 className="h-4 w-4 animate-spin text-sky-600" />
            ) : (
              <ArrowRight className="h-4 w-4 text-sky-600" />
            )}
          </button>

          <button
            onClick={() => handleIngest('CDR', 'cdr_mysuru_bengaluru.csv')}
            disabled={ingestingType !== null}
            className="flex items-center justify-between p-3.5 rounded-lg border border-amber-200 bg-amber-50/50 hover:bg-amber-50 text-left transition-all disabled:opacity-50 shadow-sm"
          >
            <div className="flex items-center gap-2.5">
              <Phone className="h-5 w-5 text-amber-600 shrink-0" />
              <div>
                <div className="text-xs font-bold text-amber-950">Load CDR Records</div>
                <div className="text-[11px] text-neutral-600">Mysuru &amp; BLR Calls</div>
              </div>
            </div>
            {ingestingType === 'CDR' ? (
              <Loader2 className="h-4 w-4 animate-spin text-amber-600" />
            ) : (
              <ArrowRight className="h-4 w-4 text-amber-600" />
            )}
          </button>

          <button
            onClick={() => handleIngest('BANK_TXN', 'txns_axis_2026.csv')}
            disabled={ingestingType !== null}
            className="flex items-center justify-between p-3.5 rounded-lg border border-purple-200 bg-purple-50/50 hover:bg-purple-50 text-left transition-all disabled:opacity-50 shadow-sm"
          >
            <div className="flex items-center gap-2.5">
              <Landmark className="h-5 w-5 text-purple-600 shrink-0" />
              <div>
                <div className="text-xs font-bold text-purple-950">Load Transaction Log</div>
                <div className="text-[11px] text-neutral-600">Axis Layering Ledger</div>
              </div>
            </div>
            {ingestingType === 'BANK_TXN' ? (
              <Loader2 className="h-4 w-4 animate-spin text-purple-600" />
            ) : (
              <ArrowRight className="h-4 w-4 text-purple-600" />
            )}
          </button>
        </div>

        {/* Ingest Result Card */}
        {ingestResult && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 space-y-3 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-900">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Ingestion Batch Completed: {ingestResult.batch_id}
              </div>
              <Link
                to="/network"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors shadow-sm"
              >
                Begin Investigation in Network Explorer <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
              <div className="bg-white rounded-lg p-2.5 border border-emerald-100 shadow-xs">
                <div className="text-[11px] text-neutral-500 font-medium">Persons</div>
                <div className="text-base font-bold text-neutral-900">{ingestResult.extraction_summary.persons}</div>
              </div>
              <div className="bg-white rounded-lg p-2.5 border border-emerald-100 shadow-xs">
                <div className="text-[11px] text-neutral-500 font-medium">Phones</div>
                <div className="text-base font-bold text-neutral-900">{ingestResult.extraction_summary.phones}</div>
              </div>
              <div className="bg-white rounded-lg p-2.5 border border-emerald-100 shadow-xs">
                <div className="text-[11px] text-neutral-500 font-medium">Accounts</div>
                <div className="text-base font-bold text-neutral-900">{ingestResult.extraction_summary.accounts}</div>
              </div>
              <div className="bg-white rounded-lg p-2.5 border border-emerald-100 shadow-xs">
                <div className="text-[11px] text-neutral-500 font-medium">Events</div>
                <div className="text-base font-bold text-neutral-900">{ingestResult.extraction_summary.events}</div>
              </div>
              <div className="bg-white rounded-lg p-2.5 border border-emerald-100 shadow-xs col-span-2 sm:col-span-1">
                <div className="text-[11px] text-neutral-500 font-medium">Relationships</div>
                <div className="text-base font-bold text-emerald-700">{ingestResult.extraction_summary.relationships}</div>
              </div>
            </div>
          </div>
        )}

        {ingestError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
            {ingestError}
          </div>
        )}

        <p className="text-[11px] text-neutral-600">
          🛡️ All files are synthetic demo fixtures. No real citizen data. Fully explainable and verified.
        </p>
      </section>

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

      {/* Content */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : (
        <DataTable
          data={filteredData}
          columns={columns}
          onRowClick={(row) => navigate(`/investigations/${row.id}`)}
        />
      )}
    </div>
  )
}
