import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { DocumentIngestionPanel } from '@/components/DocumentIngestionPanel'
import { apiClient } from '@/lib/apiClient'
import type { DocumentResponse, DocumentTextResponse } from '@shared/contracts/api'

vi.mock('@/lib/apiClient', () => ({
  apiClient: {
    uploadDocument: vi.fn(),
    getDocumentText: vi.fn(),
  },
}))

describe('DocumentIngestionPanel (P1-A)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload form with file input, source type select, and disabled submit initially', () => {
    render(<DocumentIngestionPanel />)

    expect(screen.getByText('Unstructured Document Ingestion')).toBeInTheDocument()
    expect(screen.getByTestId('document-upload-input')).toBeInTheDocument()
    expect(screen.getByTestId('document-source-type-select')).toBeInTheDocument()
    expect(screen.getByTestId('document-case-id-input')).toBeInTheDocument()

    const submitBtn = screen.getByTestId('document-upload-submit')
    expect(submitBtn).toBeDisabled()
  })

  it('allows selecting a PDF file and enables the upload button', () => {
    render(<DocumentIngestionPanel />)

    const file = new File(['%PDF-1.4 sample content'], 'fir_notice.pdf', { type: 'application/pdf' })
    const fileInput = screen.getByTestId('document-upload-input')

    fireEvent.change(fileInput, { target: { files: [file] } })

    expect(screen.getByText('fir_notice.pdf')).toBeInTheDocument()
    const submitBtn = screen.getByTestId('document-upload-submit')
    expect(submitBtn).not.toBeDisabled()
  })

  it('displays error and rejects unsupported file extension', () => {
    render(<DocumentIngestionPanel />)

    const file = new File(['dummy docx'], 'report.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const fileInput = screen.getByTestId('document-upload-input')

    fireEvent.change(fileInput, { target: { files: [file] } })

    expect(screen.getByTestId('document-upload-error')).toBeInTheDocument()
    expect(screen.getByText(/Only \.pdf and \.txt files are supported/)).toBeInTheDocument()
    expect(screen.getByTestId('document-upload-submit')).toBeDisabled()
  })

  it('successfully uploads document, displays status, metrics, and content hash', async () => {
    const mockResponse: DocumentResponse = {
      document_id: 'doc-a1b2c3d4e5f67890',
      original_filename: 'fir_495_2026.pdf',
      source_type: 'FIR_DOCUMENT',
      mime_type: 'application/pdf',
      content_hash: 'a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890',
      uploaded_by: 'OFFICER-DEMO-IO-01',
      uploaded_at: '2026-03-20T10:00:00Z',
      case_id: 'case-0001',
      extraction_status: 'SUCCESS',
      extraction_metadata: {
        page_count: 2,
        character_count: 450,
        word_count: 85,
        extraction_method: 'pypdf',
        error_message: null,
      },
      provenance: {
        source_type: 'FIR_DOCUMENT',
        source_id: 'doc-a1b2c3d4e5f67890',
        timestamp: '2026-03-20T10:00:00Z',
        extracted_fact: 'FIR details for case-0001',
        derivation_method: 'DOCUMENT_EXTRACTION',
        confidence: 1.0,
      },
    }

    const mockTextResponse: DocumentTextResponse = {
      document_id: 'doc-a1b2c3d4e5f67890',
      content_hash: 'a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890',
      extracted_text: 'First Information Report No. 495/2026 Cyber Crime PS Bengaluru.',
      extraction_status: 'SUCCESS',
      extraction_metadata: mockResponse.extraction_metadata,
    }

    vi.mocked(apiClient.uploadDocument).mockResolvedValueOnce(mockResponse)
    vi.mocked(apiClient.getDocumentText).mockResolvedValueOnce(mockTextResponse)

    render(<DocumentIngestionPanel />)

    const file = new File(['dummy content'], 'fir_495_2026.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByTestId('document-upload-input'), { target: { files: [file] } })

    fireEvent.click(screen.getByTestId('document-upload-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('document-upload-status')).toBeInTheDocument()
    })

    expect(screen.getByTestId('document-id')).toHaveTextContent('doc-a1b2c3d4e5f67890')
    expect(screen.getByTestId('document-content-hash')).toHaveTextContent(mockResponse.content_hash)
    expect(screen.getByText('fir_495_2026.pdf')).toBeInTheDocument()
    expect(screen.getByText('case-0001')).toBeInTheDocument()

    // Toggle text preview
    const previewToggle = screen.getByText('View Extracted Text Preview')
    fireEvent.click(previewToggle)

    expect(screen.getByText(/First Information Report No\. 495\/2026/)).toBeInTheDocument()
  })

  it('displays error banner when upload fails with unauthorized/forbidden response', async () => {
    vi.mocked(apiClient.uploadDocument).mockRejectedValueOnce(
      new Error('Forbidden: Investigating Officer is not assigned to case-9999')
    )

    render(<DocumentIngestionPanel />)

    const file = new File(['memo'], 'secret_memo.txt', { type: 'text/plain' })
    fireEvent.change(screen.getByTestId('document-upload-input'), { target: { files: [file] } })
    fireEvent.change(screen.getByTestId('document-case-id-input'), { target: { value: 'case-9999' } })

    fireEvent.click(screen.getByTestId('document-upload-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('document-upload-error')).toBeInTheDocument()
    })

    expect(screen.getByText(/Investigating Officer is not assigned to case-9999/)).toBeInTheDocument()
  })

  it('allows clicking Upload Another to reset the form', async () => {
    const mockResponse: DocumentResponse = {
      document_id: 'doc-reset-test',
      original_filename: 'test.pdf',
      source_type: 'OTHER_DOCUMENT',
      mime_type: 'application/pdf',
      content_hash: '1234567890abcdef',
      uploaded_by: 'OFFICER-TEST',
      uploaded_at: '2026-03-20T10:00:00Z',
      case_id: null,
      extraction_status: 'SUCCESS',
      extraction_metadata: {
        page_count: 1,
        character_count: 10,
        word_count: 2,
        extraction_method: 'pypdf',
        error_message: null,
      },
      provenance: {
        source_type: 'OTHER_DOCUMENT',
        source_id: 'doc-reset-test',
        timestamp: '2026-03-20T10:00:00Z',
        extracted_fact: 'Test fact',
        derivation_method: 'DOCUMENT_EXTRACTION',
        confidence: 1.0,
      },
    }

    vi.mocked(apiClient.uploadDocument).mockResolvedValueOnce(mockResponse)
    vi.mocked(apiClient.getDocumentText).mockResolvedValueOnce({
      document_id: 'doc-reset-test',
      content_hash: '1234567890abcdef',
      extracted_text: 'Test text',
      extraction_status: 'SUCCESS',
      extraction_metadata: mockResponse.extraction_metadata,
    })

    render(<DocumentIngestionPanel />)

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByTestId('document-upload-input'), { target: { files: [file] } })
    fireEvent.click(screen.getByTestId('document-upload-submit'))

    await waitFor(() => {
      expect(screen.getByText('Upload Another')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Upload Another'))

    expect(screen.getByTestId('document-upload-input')).toBeInTheDocument()
    expect(screen.queryByTestId('document-upload-status')).not.toBeInTheDocument()
  })
})
