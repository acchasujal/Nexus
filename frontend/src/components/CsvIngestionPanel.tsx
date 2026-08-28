import React, { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  UploadCloud,
  FileText,
  Database,
  ShieldAlert,
  AlertTriangle,
  AlertCircle,
  X,
  CheckCircle2,
  Phone,
  Landmark,
  Network,
  Users,
  Search,
  Filter,
  Loader2,
  RotateCcw,
  Info,
} from 'lucide-react'
import { useIngestFiles } from '@/hooks/useIngestion'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import type { IngestionParseIssue } from '@shared/contracts/api'

type FileSlotType = 'fir' | 'cdr' | 'bank' | 'intelligence'

interface FileSlot {
  id: FileSlotType
  label: string
  icon: React.ElementType
  required: boolean
  description: string
}

const FILE_SLOTS: FileSlot[] = [
  { id: 'fir', label: 'FIR & Cases', icon: ShieldAlert, required: true, description: 'Base case data and suspect entities' },
  { id: 'cdr', label: 'Telecom CDR', icon: Phone, required: true, description: 'Call Detail Records for network links' },
  { id: 'bank', label: 'Bank Transactions', icon: Landmark, required: true, description: 'Financial flow and account entities' },
  { id: 'intelligence', label: 'Intelligence (Optional)', icon: FileText, required: false, description: 'Custom watchlists and OSINT reports' },
]

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5 MB

const PROGRESS_STAGES = [
  'Uploading files securely',
  'Validating headers and formats',
  'Resolving phonetic identities',
  'Building cross-case graph',
  'Updating investigation workspace',
]

export function CsvIngestionPanel() {
  const [files, setFiles] = useState<Record<FileSlotType, File | null>>({
    fir: null,
    cdr: null,
    bank: null,
    intelligence: null,
  })
  const [errors, setErrors] = useState<Record<FileSlotType, string | null>>({
    fir: null,
    cdr: null,
    bank: null,
    intelligence: null,
  })

  const [stageIndex, setStageIndex] = useState(0)
  const { mutate: ingestFiles, isPending, isSuccess, data: result, error: submitError, reset } = useIngestFiles()

  const [issueSeverityFilter, setIssueSeverityFilter] = useState<string>('all')
  const [issueSearch, setIssueSearch] = useState<string>('')

  // Simulate progress steps while pending
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isPending) {
      setStageIndex(0)
      interval = setInterval(() => {
        setStageIndex((prev) => Math.min(prev + 1, PROGRESS_STAGES.length - 1))
      }, 800)
    } else {
      setStageIndex(0)
    }
    return () => clearInterval(interval)
  }, [isPending])

  const validateFile = (file: File): string | null => {
    if (!file.name.endsWith('.csv') && !file.name.endsWith('.txt')) {
      return 'Must be a .csv or .txt file'
    }
    if (file.size === 0) {
      return 'File is empty'
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'Exceeds 5MB limit'
    }
    return null
  }

  const handleFileSelect = (slotId: FileSlotType, selectedFile: File) => {
    const errorMsg = validateFile(selectedFile)
    setFiles((prev) => ({ ...prev, [slotId]: selectedFile }))
    setErrors((prev) => ({ ...prev, [slotId]: errorMsg }))
  }

  const handleRemove = (slotId: FileSlotType) => {
    setFiles((prev) => ({ ...prev, [slotId]: null }))
    setErrors((prev) => ({ ...prev, [slotId]: null }))
  }

  const handleDrop = (e: React.DragEvent, slotId: FileSlotType) => {
    e.preventDefault()
    if (isPending) return
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(slotId, e.dataTransfer.files[0])
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const isFormValid = useMemo(() => {
    const hasRequiredFiles = FILE_SLOTS.filter(s => s.required).every(s => files[s.id] !== null)
    const hasNoErrors = Object.values(errors).every(e => e === null)
    return hasRequiredFiles && hasNoErrors
  }, [files, errors])

  const onSubmit = () => {
    if (!isFormValid || isPending) return
    ingestFiles({
      fir: files.fir || undefined,
      cdr: files.cdr || undefined,
      bank: files.bank || undefined,
      intelligence: files.intelligence || undefined,
    })
  }

  const onReset = () => {
    reset()
    setFiles({ fir: null, cdr: null, bank: null, intelligence: null })
    setErrors({ fir: null, cdr: null, bank: null, intelligence: null })
    setIssueSeverityFilter('all')
    setIssueSearch('')
  }

  // File Selection View
  if (!isSuccess || !result) {
    return (
      <div className="bg-white rounded-xl border border-neutral-200 shadow-sm p-6 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-neutral-900 flex items-center gap-2">
            <Database className="h-5 w-5 text-blue-600" />
            Upload Evidence & Intelligence
          </h2>
          <p className="text-sm text-neutral-600 mt-1">
            Provide the required CSV extracts to populate the investigation workspace. The system will automatically map identities, discover graph relationships, and check for conflicts.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {FILE_SLOTS.map((slot) => {
            const currentFile = files[slot.id]
            const currentError = errors[slot.id]
            const Icon = slot.icon

            return (
              <div
                key={slot.id}
                onDrop={(e) => handleDrop(e, slot.id)}
                onDragOver={handleDragOver}
                className={`relative flex flex-col items-center justify-center p-4 border-2 rounded-xl transition-colors
                  ${isPending ? 'opacity-60 cursor-not-allowed bg-neutral-50 border-neutral-200' : 'cursor-pointer hover:bg-blue-50'}
                  ${currentError ? 'border-red-300 bg-red-50' : currentFile ? 'border-blue-300 bg-blue-50/50' : 'border-dashed border-neutral-300 bg-neutral-50'}
                `}
                data-testid={`dropzone-${slot.id}`}
              >
                {!currentFile ? (
                  <>
                    <Icon className={`h-8 w-8 mb-2 ${currentError ? 'text-red-400' : 'text-neutral-400'}`} />
                    <div className="text-sm font-semibold text-neutral-800 flex items-center gap-1.5">
                      {slot.label}
                      {!slot.required && <span className="text-[10px] uppercase bg-neutral-200 text-neutral-600 px-1.5 py-0.5 rounded">Optional</span>}
                    </div>
                    <div className="text-[11px] text-neutral-500 text-center mt-1 px-2">{slot.description}</div>
                    
                    <label className="absolute inset-0 w-full h-full cursor-pointer">
                      <input
                        type="file"
                        className="hidden"
                        accept=".csv,text/csv"
                        disabled={isPending}
                        data-testid={`file-input-${slot.id}`}
                        onChange={(e) => {
                          if (e.target.files && e.target.files.length > 0) {
                            handleFileSelect(slot.id, e.target.files[0])
                          }
                          // Reset input value so same file can be re-selected if removed
                          e.target.value = ''
                        }}
                      />
                    </label>

                    {currentError && (
                      <div className="absolute bottom-2 text-xs font-semibold text-red-600 flex items-center gap-1">
                        <AlertCircle className="h-3.5 w-3.5" />
                        {currentError}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="w-full flex flex-col justify-between h-full relative z-10">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2 text-blue-700">
                        <FileText className="h-5 w-5" />
                        <span className="text-sm font-bold truncate max-w-[140px]" data-testid={`filename-${slot.id}`}>{currentFile.name}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleRemove(slot.id)
                        }}
                        disabled={isPending}
                        className="p-1 rounded-md text-neutral-500 hover:bg-neutral-200 transition-colors"
                        aria-label={`Remove ${slot.label} file`}
                        data-testid={`remove-${slot.id}`}
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    
                    <div className="mt-2 text-xs text-neutral-600 font-medium" data-testid={`filesize-${slot.id}`}>
                      {(currentFile.size / 1024).toFixed(1)} KB
                    </div>
                    
                    {currentError ? (
                      <div className="mt-2 text-xs font-semibold text-red-600 flex items-center gap-1" data-testid={`error-${slot.id}`}>
                        <AlertCircle className="h-3.5 w-3.5" />
                        {currentError}
                      </div>
                    ) : (
                      <div className="mt-2 text-xs font-semibold text-emerald-600 flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Ready
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {submitError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 flex items-start gap-3 text-red-800" data-testid="submit-error">
            <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold">Ingestion Request Failed</h4>
              <p className="text-sm mt-1">{submitError.message}</p>
            </div>
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-neutral-100">
          <div className="text-xs text-neutral-500 flex items-center gap-1.5">
            <Info className="h-4 w-4" />
            Files must be valid CSV format, up to 5MB each.
          </div>
          <button
            onClick={onSubmit}
            disabled={!isFormValid || isPending}
            data-testid="submit-btn"
            className="flex items-center justify-center gap-2 px-6 py-2.5 bg-blue-600 text-white text-sm font-bold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {PROGRESS_STAGES[stageIndex]}
              </>
            ) : (
              <>
                <UploadCloud className="h-4 w-4" />
                Validate and Ingest Files
              </>
            )}
          </button>
        </div>
      </div>
    )
  }

  // Success View
  const { summary, parse_issues, status, batch_id } = result

  const filteredIssues = parse_issues.filter(issue => {
    const matchesSeverity = issueSeverityFilter === 'all' || issue.severity === issueSeverityFilter
    const matchesSearch = !issueSearch || 
      issue.code.toLowerCase().includes(issueSearch.toLowerCase()) ||
      issue.message.toLowerCase().includes(issueSearch.toLowerCase())
    return matchesSeverity && matchesSearch
  })

  const columns: ColumnDef<IngestionParseIssue>[] = [
    {
      header: 'Severity',
      accessorKey: 'severity',
      cell: (row) => {
        let color = 'bg-neutral-100 text-neutral-800'
        if (row.severity === 'ERROR') color = 'bg-red-100 text-red-800'
        if (row.severity === 'WARNING') color = 'bg-amber-100 text-amber-800'
        if (row.severity === 'INFO') color = 'bg-blue-100 text-blue-800'
        
        return (
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${color}`}>
            {row.severity}
          </span>
        )
      }
    },
    { header: 'File', accessorKey: 'file_name' },
    { 
      header: 'Location', 
      accessorKey: 'row_number',
      cell: (row) => row.row_number ? `Row ${row.row_number}` : 'Global'
    },
    { header: 'Code', accessorKey: 'code' },
    { header: 'Message', accessorKey: 'message' },
  ]

  const SummaryCard = ({ label, value, type = 'neutral' }: { label: string, value: number, type?: 'success' | 'warning' | 'error' | 'neutral' | 'info' }) => {
    let colorCls = 'text-neutral-900 border-neutral-200 bg-white'
    let valCls = 'text-neutral-900'
    
    if (type === 'success') { colorCls = 'border-emerald-200 bg-emerald-50'; valCls = 'text-emerald-700' }
    if (type === 'warning') { colorCls = 'border-amber-200 bg-amber-50'; valCls = 'text-amber-700' }
    if (type === 'error' && value > 0) { colorCls = 'border-red-200 bg-red-50'; valCls = 'text-red-700' }
    if (type === 'info') { colorCls = 'border-blue-200 bg-blue-50'; valCls = 'text-blue-700' }

    return (
      <div className={`p-3 rounded-lg border shadow-sm ${colorCls} text-center`} data-testid={`summary-${label.toLowerCase().replace(/ /g, '-')}`}>
        <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">{label}</div>
        <div className={`text-2xl font-bold mt-1 ${valCls}`}>{value.toLocaleString()}</div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-neutral-200 shadow-sm p-6 space-y-6" data-testid="success-panel">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-neutral-900 flex items-center gap-2">
            {status === 'COMPLETED' ? (
              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
            ) : status === 'COMPLETED_WITH_WARNINGS' ? (
              <AlertTriangle className="h-6 w-6 text-amber-500" />
            ) : (
              <AlertCircle className="h-6 w-6 text-red-600" />
            )}
            Ingestion {status.replace(/_/g, ' ')}
          </h2>
          <p className="text-sm text-neutral-600 mt-1">
            Batch ID: <span className="font-mono bg-neutral-100 px-1.5 py-0.5 rounded text-neutral-800">{batch_id}</span>
          </p>
        </div>
        
        <div className="flex flex-wrap gap-2">
          {summary.review_required > 0 && (
            <Link to="/fusion" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg text-sm font-semibold transition-colors">
              <Users className="h-4 w-4" /> Review Entity Matches
            </Link>
          )}
          <Link to="/network" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 rounded-lg text-sm font-semibold transition-colors">
            <Network className="h-4 w-4" /> Open Network
          </Link>
          <button onClick={onReset} data-testid="upload-another-btn" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white text-neutral-700 hover:bg-neutral-50 border border-neutral-300 rounded-lg text-sm font-semibold transition-colors">
            <RotateCcw className="h-4 w-4" /> Upload Another
          </button>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        <SummaryCard label="Received Rows" value={summary.received} />
        <SummaryCard label="Accepted Rows" value={summary.accepted} type="success" />
        <SummaryCard label="Rejected Rows" value={summary.rejected} type="error" />
        <SummaryCard label="Duplicates" value={summary.duplicates} type="info" />
        <SummaryCard label="Conflicts" value={summary.conflicts} type="warning" />
        
        <SummaryCard label="Warnings" value={summary.warnings} type="warning" />
        <SummaryCard label="Nodes Extracted" value={summary.nodes_created} type="success" />
        <SummaryCard label="Relations Formed" value={summary.relationships_created} type="success" />
        <SummaryCard label="Review Required" value={summary.review_required} type={summary.review_required > 0 ? 'warning' : 'neutral'} />
      </div>

      {/* Issue Table */}
      {parse_issues.length > 0 && (
        <div className="pt-4 border-t border-neutral-100 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h3 className="font-bold text-neutral-900">Parse Issues & Logs</h3>
            <div className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-2 h-4 w-4 text-neutral-400" />
                <input
                  type="text"
                  placeholder="Search code or message..."
                  value={issueSearch}
                  onChange={(e) => setIssueSearch(e.target.value)}
                  data-testid="issue-search"
                  className="pl-8 pr-3 py-1.5 text-sm border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
              <div className="flex items-center gap-2 border border-neutral-300 rounded-md px-2.5 py-1.5">
                <Filter className="h-4 w-4 text-neutral-400" />
                <select
                  value={issueSeverityFilter}
                  onChange={(e) => setIssueSeverityFilter(e.target.value)}
                  data-testid="issue-filter"
                  className="text-sm bg-transparent focus:outline-none"
                >
                  <option value="all">All Severities</option>
                  <option value="ERROR">Error</option>
                  <option value="WARNING">Warning</option>
                  <option value="INFO">Info</option>
                </select>
              </div>
            </div>
          </div>
          
          <div className="border border-neutral-200 rounded-lg overflow-hidden">
            <DataTable
              data={filteredIssues}
              columns={columns}
              onRowClick={() => {}}
            />
            {filteredIssues.length === 0 && (
              <div className="p-4 text-center text-sm text-neutral-500">
                No issues match your current filters.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
