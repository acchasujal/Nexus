import React, { useState } from 'react'
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Copy,
  Check,
  Shield,
  Hash,
  Layers,
  FileCode,
  RotateCcw,
  Sparkles,
  Search,
  ExternalLink,
  ChevronRight,
  ChevronDown,
} from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import type {
  CandidateEntity,
  CandidateRelationship,
  DocumentExtractionResult,
  DocumentResponse,
  DocumentSourceType,
  DocumentTextResponse,
} from '@shared/contracts/api'

export interface DocumentIngestionPanelProps {
  onUploadSuccess?: (doc: DocumentResponse) => void
  defaultCaseId?: string
}

const SOURCE_TYPE_OPTIONS: { value: DocumentSourceType; label: string; desc: string }[] = [
  { value: 'FIR_DOCUMENT', label: 'FIR Document (PDF/TXT)', desc: 'First Information Report filings' },
  { value: 'POLICE_REPORT', label: 'Police Report / Memo', desc: 'Case diaries, seizure lists & memos' },
  { value: 'INTELLIGENCE_DOCUMENT', label: 'Intelligence Report', desc: 'Watchlists, covert bulletins & intel' },
  { value: 'OTHER_DOCUMENT', label: 'Other Document', desc: 'General evidentiary text or documents' },
]

export function DocumentIngestionPanel({ onUploadSuccess, defaultCaseId = '' }: DocumentIngestionPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [sourceType, setSourceType] = useState<DocumentSourceType>('FIR_DOCUMENT')
  const [caseId, setCaseId] = useState<string>(defaultCaseId)
  const [isUploading, setIsUploading] = useState<boolean>(false)
  const [uploadedDoc, setUploadedDoc] = useState<DocumentResponse | null>(null)
  const [extractedText, setExtractedText] = useState<string | null>(null)
  const [showTextPreview, setShowTextPreview] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [copiedHash, setCopiedHash] = useState<boolean>(false)

  // ── P1-B Candidate Intelligence State ─────────────────────────────────────
  const [isExtractingCandidates, setIsExtractingCandidates] = useState<boolean>(false)
  const [extractionResult, setExtractionResult] = useState<DocumentExtractionResult | null>(null)
  const [activeCandidateTab, setActiveCandidateTab] = useState<'entities' | 'relationships'>('entities')
  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(null)

  // ── P1-C Investigator Decision State ──────────────────────────────────────
  const [decisionInProgress, setDecisionInProgress] = useState<string | null>(null)
  const [decidedCandidates, setDecidedCandidates] = useState<Record<string, { status: string; targetId?: string }>>({})
  const [modalState, setModalState] = useState<{
    isOpen: boolean
    type: 'existing' | 'new' | 'relationship' | 'reject' | 'reject-rel'
    candidateId: string
    targetId?: string
    name?: string
    entityType?: string
    notes: string
  }>({
    isOpen: false,
    type: 'new',
    candidateId: '',
    notes: '',
  })

  const handleConfirmDecision = async () => {
    if (!modalState.candidateId) return
    const { type, candidateId, targetId, name, entityType, notes } = modalState
    setDecisionInProgress(candidateId)
    setErrorMessage(null)

    try {
      if (type === 'existing' && targetId) {
        const resp = await apiClient.acceptExistingEntity(candidateId, {
          target_canonical_id: targetId,
          case_id: uploadedDoc?.case_id || caseId || undefined,
          notes: notes || undefined,
        })
        setDecidedCandidates((prev) => ({
          ...prev,
          [candidateId]: { status: resp.status, targetId: resp.resulting_graph_id || targetId },
        }))
      } else if (type === 'new') {
        const resp = await apiClient.acceptNewEntity(candidateId, {
          entity_type: entityType || 'Person',
          canonical_name: name || '',
          case_id: uploadedDoc?.case_id || caseId || undefined,
          notes: notes || undefined,
        })
        setDecidedCandidates((prev) => ({
          ...prev,
          [candidateId]: { status: resp.status, targetId: resp.resulting_graph_id || undefined },
        }))
      } else if (type === 'relationship') {
        const rel = extractionResult?.candidate_relationships.find((r) => r.candidate_relationship_id === candidateId)
        if (!rel) throw new Error('Relationship not found')
        const resp = await apiClient.acceptCandidateRelationship(candidateId, {
          source_canonical_id: targetId || rel.source_candidate_id,
          target_canonical_id: rel.target_candidate_id,
          relationship_type: entityType || rel.relationship_type,
          case_id: uploadedDoc?.case_id || caseId || undefined,
          notes: notes || undefined,
        })
        setDecidedCandidates((prev) => ({
          ...prev,
          [candidateId]: { status: resp.status, targetId: resp.resulting_graph_id || undefined },
        }))
      } else if (type === 'reject') {
        const resp = await apiClient.rejectCandidateEntity(candidateId, {
          reason: notes || 'Investigator rejected candidate during review',
          notes: notes || undefined,
        })
        setDecidedCandidates((prev) => ({
          ...prev,
          [candidateId]: { status: resp.status },
        }))
      } else if (type === 'reject-rel') {
        const resp = await apiClient.rejectCandidateRelationship(candidateId, {
          reason: notes || 'Investigator rejected candidate relationship',
          notes: notes || undefined,
        })
        setDecidedCandidates((prev) => ({
          ...prev,
          [candidateId]: { status: resp.status },
        }))
      }
      setModalState((prev) => ({ ...prev, isOpen: false }))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Promotion failed'
      setErrorMessage(msg)
    } finally {
      setDecisionInProgress(null)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0]
      const lowerName = file.name.toLowerCase()
      if (!lowerName.endsWith('.pdf') && !lowerName.endsWith('.txt')) {
        setErrorMessage(`Unsupported format for '${file.name}'. Only .pdf and .txt files are supported.`)
        setSelectedFile(null)
        return
      }
      if (file.size > 10 * 1024 * 1024) {
        setErrorMessage(`File '${file.name}' exceeds maximum 10 MB limit.`)
        setSelectedFile(null)
        return
      }
      setSelectedFile(file)
      setErrorMessage(null)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (isUploading) return
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0]
      const lowerName = file.name.toLowerCase()
      if (!lowerName.endsWith('.pdf') && !lowerName.endsWith('.txt')) {
        setErrorMessage(`Unsupported format for '${file.name}'. Only .pdf and .txt files are supported.`)
        return
      }
      setSelectedFile(file)
      setErrorMessage(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile || isUploading) return
    setIsUploading(true)
    setErrorMessage(null)

    try {
      const docResp = await apiClient.uploadDocument(selectedFile, sourceType, caseId)
      setUploadedDoc(docResp)

      // Optionally fetch full extracted text
      try {
        const textResp: DocumentTextResponse = await apiClient.getDocumentText(docResp.document_id)
        setExtractedText(textResp.extracted_text)
      } catch {
        // Text retrieval non-fatal for upload view
      }

      onUploadSuccess?.(docResp)
    } catch (err: any) {
      const msg = err?.message || 'Failed to upload and extract document.'
      setErrorMessage(msg)
    } finally {
      setIsUploading(false)
    }
  }

  const handleCopyHash = () => {
    if (!uploadedDoc?.content_hash) return
    navigator.clipboard.writeText(uploadedDoc.content_hash)
    setCopiedHash(true)
    setTimeout(() => setCopiedHash(false), 2000)
  }

  const handleExtractCandidates = async () => {
    if (!uploadedDoc || isExtractingCandidates) return
    setIsExtractingCandidates(true)
    setErrorMessage(null)
    try {
      const result = await apiClient.extractDocumentCandidates(uploadedDoc.document_id)
      setExtractionResult(result)
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to extract candidate entities from document.')
    } finally {
      setIsExtractingCandidates(false)
    }
  }

  const handleReset = () => {
    setSelectedFile(null)
    setUploadedDoc(null)
    setExtractedText(null)
    setShowTextPreview(false)
    setErrorMessage(null)
    setExtractionResult(null)
    setExpandedCandidateId(null)
  }

  return (
    <div className="bg-white border border-neutral-200 rounded-xl shadow-xs p-5 transition-all">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-100 pb-3 mb-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-neutral-900">Unstructured Document Ingestion</h3>
            <p className="text-xs text-neutral-500">
              Deterministic text extraction & tamper-evident SHA-256 fingerprinting for .pdf and .txt
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-neutral-100 text-neutral-700">
            <Shield className="h-3 w-3 mr-1 text-neutral-500" />
            Strict RBAC Gated
          </span>
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div
          data-testid="document-upload-error"
          className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-start space-x-2"
        >
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-600" />
          <div className="flex-1 font-medium">{errorMessage}</div>
        </div>
      )}

      {!uploadedDoc ? (
        /* Upload Form */
        <div className="space-y-4">
          {/* Dropzone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
              selectedFile
                ? 'border-blue-400 bg-blue-50/30'
                : 'border-neutral-200 hover:border-blue-300 bg-neutral-50/50'
            }`}
          >
            <input
              type="file"
              id="doc-file-input"
              data-testid="document-upload-input"
              accept=".pdf,.txt,application/pdf,text/plain"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="doc-file-input" className="cursor-pointer flex flex-col items-center justify-center">
              <UploadCloud className={`h-9 w-9 mb-2 ${selectedFile ? 'text-blue-600' : 'text-neutral-400'}`} />
              {selectedFile ? (
                <div>
                  <p className="text-sm font-semibold text-neutral-900">{selectedFile.name}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    {(selectedFile.size / 1024).toFixed(1)} KB — Click or drop to replace
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-sm font-medium text-neutral-700">
                    <span className="text-blue-600 font-semibold hover:underline">Click to upload</span> or drag and drop
                  </p>
                  <p className="text-xs text-neutral-400 mt-1">Supported formats: Machine-readable .pdf, .txt (Max 10 MB)</p>
                </div>
              )}
            </label>
          </div>

          {/* Form Fields Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Document Source Type */}
            <div>
              <label htmlFor="source-type-select" className="block text-xs font-semibold text-neutral-700 mb-1">
                Document Source Type
              </label>
              <select
                id="source-type-select"
                data-testid="document-source-type-select"
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value as DocumentSourceType)}
                className="w-full text-xs bg-white border border-neutral-200 rounded-lg px-3 py-2 text-neutral-900 focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 shadow-2xs"
              >
                {SOURCE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Case ID Association */}
            <div>
              <label htmlFor="case-id-input" className="block text-xs font-semibold text-neutral-700 mb-1">
                Case Association <span className="text-neutral-400 font-normal">(Optional)</span>
              </label>
              <input
                id="case-id-input"
                data-testid="document-case-id-input"
                type="text"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                placeholder="e.g. case-0001, CASE-141"
                className="w-full text-xs bg-white border border-neutral-200 rounded-lg px-3 py-2 text-neutral-900 placeholder-neutral-400 focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 shadow-2xs"
              />
            </div>
          </div>

          {/* Submit Action */}
          <div className="flex justify-end pt-2">
            <button
              type="button"
              data-testid="document-upload-submit"
              disabled={!selectedFile || isUploading}
              onClick={handleUpload}
              className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all shadow-2xs ${
                !selectedFile || isUploading
                  ? 'bg-neutral-100 text-neutral-400 cursor-not-allowed border border-neutral-200'
                  : 'bg-blue-600 hover:bg-blue-700 text-white border border-blue-700'
              }`}
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Extracting Text & Fingerprinting...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="h-4 w-4" />
                  <span>Upload & Ingest Document</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* Ingestion Results Card */
        <div className="space-y-4" data-testid="document-upload-status">
          {/* Status Banner */}
          <div
            className={`p-4 rounded-xl border flex items-start justify-between ${
              uploadedDoc.extraction_status === 'SUCCESS'
                ? 'bg-emerald-50/60 border-emerald-200'
                : 'bg-amber-50/60 border-amber-200'
            }`}
          >
            <div className="flex items-start space-x-3">
              <CheckCircle2
                className={`h-5 w-5 shrink-0 mt-0.5 ${
                  uploadedDoc.extraction_status === 'SUCCESS' ? 'text-emerald-600' : 'text-amber-600'
                }`}
              />
              <div>
                <div className="flex items-center space-x-2">
                  <h4 className="text-xs font-bold text-neutral-900">
                    Document Ingested — Status: {uploadedDoc.extraction_status}
                  </h4>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                      uploadedDoc.extraction_status === 'SUCCESS'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {uploadedDoc.extraction_status}
                  </span>
                </div>
                <p className="text-xs text-neutral-600 mt-0.5">
                  File: <span className="font-semibold text-neutral-900">{uploadedDoc.original_filename}</span> ({uploadedDoc.source_type})
                </p>
              </div>
            </div>
            <button
              onClick={handleReset}
              className="inline-flex items-center space-x-1 text-xs text-neutral-600 hover:text-neutral-900 bg-white border border-neutral-200 rounded-lg px-2.5 py-1 shadow-2xs"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Upload Another</span>
            </button>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Document ID</div>
              <div data-testid="document-id" className="text-xs font-mono font-bold text-neutral-900 mt-1 truncate">
                {uploadedDoc.document_id}
              </div>
            </div>

            <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Pages Extracted</div>
              <div className="text-base font-bold text-neutral-900 mt-0.5 flex items-center space-x-1">
                <Layers className="h-3.5 w-3.5 text-neutral-400" />
                <span>{uploadedDoc.extraction_metadata?.page_count || 1}</span>
              </div>
            </div>

            <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Word Count</div>
              <div className="text-base font-bold text-neutral-900 mt-0.5 flex items-center space-x-1">
                <FileCode className="h-3.5 w-3.5 text-neutral-400" />
                <span>{uploadedDoc.extraction_metadata?.word_count?.toLocaleString() || 0}</span>
              </div>
            </div>

            <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Case Association</div>
              <div className="text-xs font-medium text-neutral-900 mt-1 truncate">
                {uploadedDoc.case_id || <span className="text-neutral-400">Unassigned</span>}
              </div>
            </div>
          </div>

          {/* Cryptographic Hash Fingerprint */}
          <div className="p-3 bg-neutral-900 text-neutral-200 rounded-lg text-xs font-mono border border-neutral-800 flex items-center justify-between">
            <div className="flex items-center space-x-2 truncate">
              <Hash className="h-4 w-4 text-neutral-400 shrink-0" />
              <span className="text-neutral-400 text-[11px]">SHA-256:</span>
              <span data-testid="document-content-hash" className="text-neutral-100 truncate text-[11px]">
                {uploadedDoc.content_hash}
              </span>
            </div>
            <button
              onClick={handleCopyHash}
              className="ml-2 px-2 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-[11px] flex items-center space-x-1 shrink-0"
              title="Copy hash fingerprint"
            >
              {copiedHash ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
              <span>{copiedHash ? 'Copied' : 'Copy'}</span>
            </button>
          </div>

          {/* Extracted Text Preview Toggle */}
          {extractedText && (
            <div className="border border-neutral-200 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => setShowTextPreview((prev) => !prev)}
                className="w-full px-3 py-2 bg-neutral-50 hover:bg-neutral-100 flex items-center justify-between text-xs font-semibold text-neutral-700 transition-colors"
              >
                <span>{showTextPreview ? 'Hide Extracted Text Preview' : 'View Extracted Text Preview'}</span>
                <span className="text-[11px] text-neutral-400 font-normal">
                  {uploadedDoc.extraction_metadata?.character_count} chars
                </span>
              </button>
              {showTextPreview && (
                <div className="p-3 bg-white max-h-60 overflow-y-auto text-xs font-mono text-neutral-800 whitespace-pre-wrap leading-relaxed border-t border-neutral-200">
                  {extractedText}
                </div>
              )}
            </div>
          )}

          {/* ── Candidate Intelligence Action (P1-B) ────────────────────────── */}
          <div className="pt-2 border-t border-neutral-100 flex items-center justify-between">
            <div className="text-xs text-neutral-500">
              {extractionResult ? (
                <span>
                  Extracted <strong className="text-neutral-900">{extractionResult.entity_count}</strong> entities &{' '}
                  <strong className="text-neutral-900">{extractionResult.relationship_count}</strong> relationships.
                </span>
              ) : (
                <span>Ready to extract candidate entities & relationships</span>
              )}
            </div>
            <button
              type="button"
              data-testid="extract-candidates-btn"
              disabled={isExtractingCandidates}
              onClick={handleExtractCandidates}
              className={`inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-2xs ${
                isExtractingCandidates
                  ? 'bg-neutral-100 text-neutral-400 cursor-not-allowed border border-neutral-200'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white border border-indigo-700'
              }`}
            >
              {isExtractingCandidates ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Extracting Candidates...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>{extractionResult ? 'Re-extract Candidates' : 'Extract Candidates'}</span>
                </>
              )}
            </button>
          </div>

          {/* ── Candidate Intelligence Review Panel (P1-B) ───────────────────── */}
          {extractionResult && (
            <div data-testid="candidate-intelligence-section" className="mt-4 pt-4 border-t border-neutral-200 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <h4 className="text-xs font-bold text-neutral-900">Extracted Intelligence Candidates</h4>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-200">
                    CANDIDATE — NOT YET CONFIRMED
                  </span>
                </div>
                <div className="flex items-center space-x-1 bg-neutral-100 p-0.5 rounded-lg text-xs font-medium">
                  <button
                    type="button"
                    onClick={() => setActiveCandidateTab('entities')}
                    className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                      activeCandidateTab === 'entities'
                        ? 'bg-white text-neutral-900 shadow-2xs'
                        : 'text-neutral-600 hover:text-neutral-900'
                    }`}
                  >
                    Entities ({extractionResult.entity_count})
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveCandidateTab('relationships')}
                    className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                      activeCandidateTab === 'relationships'
                        ? 'bg-white text-neutral-900 shadow-2xs'
                        : 'text-neutral-600 hover:text-neutral-900'
                    }`}
                  >
                    Relationships ({extractionResult.relationship_count})
                  </button>
                </div>
              </div>

              <p className="text-[11px] text-neutral-500 italic">
                P1B outputs are candidate extractions and are not treated by NEXUS as authoritative evidence or confirmed identities.
              </p>

              {/* Tab 1: Candidate Entities */}
              {activeCandidateTab === 'entities' && (
                <div className="space-y-2">
                  {extractionResult.candidate_entities.length === 0 ? (
                    <p className="text-xs text-neutral-500 py-3 text-center">No candidate entities identified.</p>
                  ) : (
                    <div className="divide-y divide-neutral-100 border border-neutral-200 rounded-lg overflow-hidden bg-white">
                      {extractionResult.candidate_entities.map((cand) => {
                        const isExpanded = expandedCandidateId === cand.candidate_id
                        const hasMatches = cand.resolution_candidates && cand.resolution_candidates.length > 0

                        return (
                          <div key={cand.candidate_id} className="p-3 text-xs space-y-2 hover:bg-neutral-50/50 transition-colors">
                            <div className="flex items-start justify-between">
                              <div className="flex items-start space-x-2.5">
                                <span
                                  className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                                    cand.entity_type === 'PERSON'
                                      ? 'bg-blue-100 text-blue-800'
                                      : cand.entity_type === 'PHONE'
                                      ? 'bg-emerald-100 text-emerald-800'
                                      : cand.entity_type === 'ACCOUNT'
                                      ? 'bg-purple-100 text-purple-800'
                                      : cand.entity_type === 'VEHICLE'
                                      ? 'bg-amber-100 text-amber-800'
                                      : cand.entity_type === 'LOCATION'
                                      ? 'bg-rose-100 text-rose-800'
                                      : 'bg-neutral-100 text-neutral-800'
                                  }`}
                                >
                                  {cand.entity_type}
                                </span>
                                <div>
                                  <div className="font-semibold text-neutral-900">{cand.surface_text}</div>
                                  <div className="text-[11px] text-neutral-500">
                                    Normalized: <span className="font-mono text-neutral-700">{cand.normalized_value}</span> ·
                                    Span: [{cand.source_span.start}..{cand.source_span.end}] · Confidence:{' '}
                                    {(cand.confidence * 100).toFixed(0)}%
                                  </div>
                                </div>
                              </div>

                              <div>
                                {hasMatches ? (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setExpandedCandidateId(isExpanded ? null : cand.candidate_id)
                                    }
                                    className="inline-flex items-center space-x-1 px-2 py-1 rounded bg-amber-50 text-amber-800 hover:bg-amber-100 font-semibold text-[11px] border border-amber-200 transition-colors"
                                  >
                                    <span>{cand.resolution_candidates.length} Candidate Matches</span>
                                    {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                                  </button>
                                ) : (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-neutral-100 text-neutral-600">
                                    No Prior Match
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Evidence Snippet */}
                            <div className="text-[11px] text-neutral-600 bg-neutral-50 p-2 rounded border border-neutral-100 font-mono">
                              <span className="text-neutral-400 font-normal">Evidence: </span>
                              "{cand.evidence_text}"
                            </div>

                            {/* Expanded Candidate Matches List */}
                            {isExpanded && hasMatches && (
                              <div className="mt-2 p-2.5 bg-neutral-50 border border-neutral-200 rounded-lg space-y-2">
                                <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                                  Candidate Canonical Entity Matches (Read-Only Graph Review)
                                </div>
                                <div className="space-y-1.5">
                                  {cand.resolution_candidates.map((match) => (
                                    <div
                                      key={match.canonical_entity_id}
                                      className="p-2 bg-white rounded border border-neutral-200 flex items-center justify-between text-xs"
                                    >
                                      <div>
                                        <div className="font-semibold text-neutral-900 flex items-center space-x-1.5">
                                          <span>{match.canonical_name}</span>
                                          <span className="text-[10px] font-mono text-neutral-400">
                                            ({match.canonical_entity_id})
                                          </span>
                                        </div>
                                        <div className="text-[10px] text-neutral-500 mt-0.5">
                                          {match.match_reasons.join(', ')}
                                        </div>
                                      </div>
                                      <div className="flex items-center space-x-2 shrink-0">
                                        <span className="inline-flex items-center px-2 py-0.5 rounded font-bold text-[10px] bg-blue-50 text-blue-700 border border-blue-100">
                                          {(match.match_score * 100).toFixed(0)}% Match
                                        </span>
                                        <button
                                          type="button"
                                          data-testid={`link-match-${match.canonical_entity_id}`}
                                          disabled={decisionInProgress !== null || !!decidedCandidates[cand.candidate_id]}
                                          onClick={() =>
                                            setModalState({
                                              isOpen: true,
                                              type: 'existing',
                                              candidateId: cand.candidate_id,
                                              targetId: match.canonical_entity_id,
                                              name: match.canonical_name,
                                              entityType: cand.entity_type,
                                              notes: '',
                                            })
                                          }
                                          className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded text-[10px] font-bold transition-colors"
                                        >
                                          Link
                                        </button>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* P1-C Decision Status or Action Bar */}
                            {decidedCandidates[cand.candidate_id] ? (
                              <div className="pt-2 border-t border-neutral-100 flex items-center justify-between">
                                <span
                                  className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                                    decidedCandidates[cand.candidate_id].status.includes('ACCEPTED')
                                      ? 'bg-emerald-100 text-emerald-900 border border-emerald-200'
                                      : 'bg-rose-100 text-rose-900 border border-rose-200'
                                  }`}
                                >
                                  {decidedCandidates[cand.candidate_id].status}
                                  {decidedCandidates[cand.candidate_id].targetId &&
                                    ` (${decidedCandidates[cand.candidate_id].targetId})`}
                                </span>
                              </div>
                            ) : (
                              <div className="pt-2 border-t border-neutral-100 flex items-center justify-end space-x-2">
                                <button
                                  type="button"
                                  data-testid={`accept-new-${cand.candidate_id}`}
                                  disabled={decisionInProgress !== null}
                                  onClick={() =>
                                    setModalState({
                                      isOpen: true,
                                      type: 'new',
                                      candidateId: cand.candidate_id,
                                      name: cand.surface_text,
                                      entityType: cand.entity_type,
                                      notes: '',
                                    })
                                  }
                                  className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50 text-indigo-700 rounded text-[11px] font-semibold border border-indigo-200 transition-colors"
                                >
                                  Accept as New {cand.entity_type}
                                </button>
                                <button
                                  type="button"
                                  data-testid={`reject-candidate-${cand.candidate_id}`}
                                  disabled={decisionInProgress !== null}
                                  onClick={() =>
                                    setModalState({
                                      isOpen: true,
                                      type: 'reject',
                                      candidateId: cand.candidate_id,
                                      name: cand.surface_text,
                                      entityType: cand.entity_type,
                                      notes: '',
                                    })
                                  }
                                  className="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 disabled:opacity-50 text-rose-700 rounded text-[11px] font-semibold border border-rose-200 transition-colors"
                                >
                                  Reject
                                </button>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Candidate Relationships */}
              {activeCandidateTab === 'relationships' && (
                <div className="space-y-2">
                  {extractionResult.candidate_relationships.length === 0 ? (
                    <div className="p-4 text-center border border-dashed border-neutral-200 rounded-lg text-xs text-neutral-500">
                      No candidate relationships identified with explicit textual evidence.
                    </div>
                  ) : (
                    <div className="divide-y divide-neutral-100 border border-neutral-200 rounded-lg overflow-hidden bg-white">
                      {extractionResult.candidate_relationships.map((rel) => (
                        <div key={rel.candidate_relationship_id} className="p-3 text-xs space-y-1.5">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span className="font-semibold text-neutral-900">{rel.source_text}</span>
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800">
                                {rel.relationship_type}
                              </span>
                              <span className="font-semibold text-neutral-900">{rel.target_text}</span>
                            </div>
                            <span className="text-[10px] font-semibold text-neutral-500">
                              {(rel.confidence * 100).toFixed(0)}% Conf
                            </span>
                          </div>
                          <div className="text-[11px] text-neutral-600 bg-neutral-50 p-2 rounded border border-neutral-100 font-mono">
                            <span className="text-neutral-400 font-normal">Evidence: </span>
                            "{rel.evidence_text}"
                          </div>

                          {/* P1-C Relationship Decision Status or Action Bar */}
                          {decidedCandidates[rel.candidate_relationship_id] ? (
                            <div className="pt-1.5 border-t border-neutral-100 flex items-center justify-between">
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                                  decidedCandidates[rel.candidate_relationship_id].status === 'ACCEPTED_RELATIONSHIP'
                                    ? 'bg-emerald-100 text-emerald-900 border border-emerald-200'
                                    : 'bg-rose-100 text-rose-900 border border-rose-200'
                                }`}
                              >
                                {decidedCandidates[rel.candidate_relationship_id].status}
                                {decidedCandidates[rel.candidate_relationship_id].targetId &&
                                  ` (${decidedCandidates[rel.candidate_relationship_id].targetId})`}
                              </span>
                            </div>
                          ) : (
                            <div className="pt-1.5 border-t border-neutral-100 flex items-center justify-end space-x-2">
                              <button
                                type="button"
                                data-testid={`accept-rel-${rel.candidate_relationship_id}`}
                                disabled={decisionInProgress !== null}
                                onClick={() =>
                                  setModalState({
                                    isOpen: true,
                                    type: 'relationship',
                                    candidateId: rel.candidate_relationship_id,
                                    targetId: rel.source_candidate_id,
                                    name: `${rel.source_text} -> ${rel.target_text}`,
                                    entityType: rel.relationship_type,
                                    notes: '',
                                  })
                                }
                                className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50 text-indigo-700 rounded text-[11px] font-semibold border border-indigo-200 transition-colors"
                              >
                                Accept Relationship
                              </button>
                              <button
                                type="button"
                                data-testid={`reject-rel-${rel.candidate_relationship_id}`}
                                disabled={decisionInProgress !== null}
                                onClick={() =>
                                  setModalState({
                                    isOpen: true,
                                    type: 'reject-rel',
                                    candidateId: rel.candidate_relationship_id,
                                    name: `${rel.source_text} -> ${rel.target_text}`,
                                    notes: '',
                                  })
                                }
                                className="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 disabled:opacity-50 text-rose-700 rounded text-[11px] font-semibold border border-rose-200 transition-colors"
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Confirmation Modal */}
      {modalState.isOpen && (
        <div
          data-testid="decision-confirm-modal"
          className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4"
        >
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-5 space-y-4 border border-neutral-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start space-x-3">
              <div className="p-2 bg-indigo-50 text-indigo-700 rounded-lg shrink-0">
                <Shield className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-neutral-900">
                  Authoritative Graph Promotion Confirmation
                </h3>
                <p className="text-xs text-neutral-500 mt-0.5">
                  Confirm your investigative determination. Graph mutations are permanent, signed by your officer badge,
                  and recorded in the audit trail.
                </p>
              </div>
            </div>

            <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200 space-y-1.5 text-xs">
              <div>
                <span className="font-semibold text-neutral-700">Action: </span>
                <span className="font-mono text-neutral-900 uppercase font-bold">{modalState.type}</span>
              </div>
              {modalState.name && (
                <div>
                  <span className="font-semibold text-neutral-700">Subject: </span>
                  <span className="font-medium text-neutral-900">{modalState.name}</span>
                </div>
              )}
              {modalState.targetId && (
                <div>
                  <span className="font-semibold text-neutral-700">Target Node: </span>
                  <span className="font-mono text-neutral-900 font-bold">{modalState.targetId}</span>
                </div>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-neutral-600">
                Investigator Notes (Optional)
              </label>
              <textarea
                value={modalState.notes}
                onChange={(e) => setModalState((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder="Enter justification or provenance notes for court dossier..."
                rows={2}
                className="w-full text-xs p-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
              />
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-neutral-100">
              <button
                type="button"
                disabled={decisionInProgress !== null}
                onClick={() => setModalState((prev) => ({ ...prev, isOpen: false }))}
                className="px-3 py-1.5 rounded-lg border border-neutral-300 text-neutral-700 text-xs font-semibold hover:bg-neutral-50"
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="confirm-decision-btn"
                disabled={decisionInProgress !== null}
                onClick={handleConfirmDecision}
                className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold shadow-2xs"
              >
                {decisionInProgress ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <span>Confirm Decision</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
