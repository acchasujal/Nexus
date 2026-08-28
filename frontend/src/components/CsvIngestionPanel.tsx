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

type FileSlotType = 'fir' | 'cdr' | 'bank' | 'intelligence'

interface FileSlot {
  id: FileSlotType
  label: string
  icon: React.ElementType
  required: boolean
  description: string
}

const FILE_SLOTS: FileSlot[] = [
  { id: 'fir', label: 'FIR & Cases', icon: ShieldAlert, required: false, description: 'Base case data and suspect entities' },
  { id: 'cdr', label: 'Telecom CDR', icon: Phone, required: false, description: 'Call Detail Records for network links' },
  { id: 'bank', label: 'Bank Transactions', icon: Landmark, required: false, description: 'Financial flow and account entities' },
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
    const hasAtLeastOneFile = Boolean(files.fir || files.cdr || files.bank || files.intelligence)
    const hasNoErrors = Object.values(errors).every(e => e === null)
    return hasAtLeastOneFile && hasNoErrors
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
            Select one or more data sources. Only one CSV file is required. The system will automatically map identities, discover graph relationships, and check for conflicts.
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
            <span className="font-bold">AT LEAST ONE REQUIRED.</span> Files must be valid CSV format, up to 5MB each.
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
                Validate, Ingest & Build Graph
              </>
            )}
          </button>
        </div>
      </div>
    )
  }

  // Success View
  const { status, batch_id, received_rows, accepted_rows, rejected_rows, duplicates, conflicts, warnings, nodes_extracted, relations_formed, review_required, graph_ready } = result

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
            Batch ID: <span className="font-bold font-mono bg-neutral-100 px-1.5 py-0.5 rounded text-neutral-800">{batch_id}</span>
          </p>
          <div className="mt-4 text-sm text-neutral-700 bg-neutral-50 p-3 rounded-lg border border-neutral-200">
            <div><span className="font-semibold">FIR:</span> {files.fir ? 'Uploaded' : 'Not uploaded'}</div>
            <div><span className="font-semibold">CDR:</span> {files.cdr ? 'Uploaded' : 'Not uploaded'}</div>
            <div><span className="font-semibold">Bank:</span> {files.bank ? 'Uploaded' : 'Not uploaded'}</div>
            <div><span className="font-semibold">Intelligence:</span> {files.intelligence ? 'Uploaded' : 'Not uploaded'}</div>
            <div className="mt-2 text-blue-700 font-semibold">Graph status: {graph_ready ? 'Ready' : 'Not ready'}</div>
          </div>
          {review_required === 0 && graph_ready && (
            <p className="mt-4 text-sm font-semibold text-emerald-700 bg-emerald-50 p-3 rounded-lg border border-emerald-200">
              No entity matches require human review.<br/>
              The graph was built successfully.
            </p>
          )}
        </div>
        
        <div className="flex flex-wrap gap-2">
          {review_required > 0 && (
            <Link to={`/fusion?batch_id=${batch_id}`} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg text-sm font-semibold transition-colors">
              <Users className="h-4 w-4" /> Review Entity Matches
            </Link>
          )}
          {graph_ready && (
            <Link to={`/network?batch_id=${batch_id}`} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 rounded-lg text-sm font-semibold transition-colors">
              <Network className="h-4 w-4" /> Open Built Graph
            </Link>
          )}
          <button onClick={onReset} data-testid="upload-another-btn" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white text-neutral-700 hover:bg-neutral-50 border border-neutral-300 rounded-lg text-sm font-semibold transition-colors">
            <RotateCcw className="h-4 w-4" /> Upload Another
          </button>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        <SummaryCard label="Received Rows" value={received_rows} />
        <SummaryCard label="Accepted Rows" value={accepted_rows} type="success" />
        <SummaryCard label="Rejected Rows" value={rejected_rows} type="error" />
        <SummaryCard label="Duplicates" value={duplicates} type="info" />
        <SummaryCard label="Conflicts" value={conflicts} type="warning" />
        
        <SummaryCard label="Warnings" value={warnings} type="warning" />
        <SummaryCard label="Nodes Extracted" value={nodes_extracted} type="success" />
        <SummaryCard label="Relations Formed" value={relations_formed} type="success" />
        <SummaryCard label="Review Required" value={review_required} type={review_required > 0 ? 'warning' : 'neutral'} />
      </div>
    </div>
  )
}
