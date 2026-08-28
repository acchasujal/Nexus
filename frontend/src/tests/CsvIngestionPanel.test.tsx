import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CsvIngestionPanel } from '@/components/CsvIngestionPanel'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { apiClient } from '@/lib/apiClient'
import type { IngestionBatchResponse } from '@shared/contracts/api'

// Mock the API client
vi.mock('@/lib/apiClient', () => ({
  apiClient: {
    ingestFiles: vi.fn(),
  },
}))

// Mock DataTable to avoid UIProvider context error
vi.mock('@/components/DataTable', () => ({
  DataTable: () => <div data-testid="mock-data-table" />
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    )
  }
}

describe('CsvIngestionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all four file slots and the submit button is disabled initially', () => {
    render(<CsvIngestionPanel />, { wrapper: createWrapper() })
    
    expect(screen.getByText('FIR & Cases')).toBeInTheDocument()
    expect(screen.getByText('Telecom CDR')).toBeInTheDocument()
    expect(screen.getByText('Bank Transactions')).toBeInTheDocument()
    expect(screen.getByText('Intelligence (Optional)')).toBeInTheDocument()
    
    const submitBtn = screen.getByTestId('submit-btn')
    expect(submitBtn).toBeDisabled()
  })

  it('shows error for invalid file extension and keeps submit disabled', () => {
    render(<CsvIngestionPanel />, { wrapper: createWrapper() })
    
    const firInput = screen.getByTestId('file-input-fir')
    const invalidFile = new File(['fake content'], 'test.pdf', { type: 'application/pdf' })
    
    fireEvent.change(firInput, { target: { files: [invalidFile] } })
    
    expect(screen.getByTestId('error-fir')).toHaveTextContent('Must be a .csv or .txt file')
    expect(screen.getByTestId('submit-btn')).toBeDisabled()
  })

  it('shows error for empty file', () => {
    render(<CsvIngestionPanel />, { wrapper: createWrapper() })
    
    const cdrInput = screen.getByTestId('file-input-cdr')
    const emptyFile = new File([], 'empty.csv', { type: 'text/csv' })
    
    fireEvent.change(cdrInput, { target: { files: [emptyFile] } })
    
    expect(screen.getByTestId('error-cdr')).toHaveTextContent('File is empty')
  })

  it('allows file selection, replacement, and removal', async () => {
    const user = userEvent.setup()
    render(<CsvIngestionPanel />, { wrapper: createWrapper() })
    
    const firInput = screen.getByTestId('file-input-fir')
    const validFile1 = new File(['a,b,c\n1,2,3'], 'first.csv', { type: 'text/csv' })
    
    fireEvent.change(firInput, { target: { files: [validFile1] } })
    
    expect(screen.getByTestId('filename-fir')).toHaveTextContent('first.csv')
    expect(screen.queryByTestId('error-fir')).not.toBeInTheDocument()
    
    // Remove
    const removeBtn = screen.getByTestId('remove-fir')
    await user.click(removeBtn)
    
    expect(screen.queryByTestId('filename-fir')).not.toBeInTheDocument()
    
    // Replace
    const validFile2 = new File(['a,b,c\n4,5,6'], 'second.csv', { type: 'text/csv' })
    const newFirInput = screen.getByTestId('file-input-fir')
    fireEvent.change(newFirInput, { target: { files: [validFile2] } })
    
    expect(screen.getByTestId('filename-fir')).toHaveTextContent('second.csv')
  })

  it('enables submit button only when all required files are present and valid', () => {
    render(<CsvIngestionPanel />, { wrapper: createWrapper() })
    
    const validFile = new File(['data'], 'test.csv', { type: 'text/csv' })
    
    fireEvent.change(screen.getByTestId('file-input-fir'), { target: { files: [validFile] } })
    fireEvent.change(screen.getByTestId('file-input-cdr'), { target: { files: [validFile] } })
    
    // Still disabled because bank is missing
    expect(screen.getByTestId('submit-btn')).toBeDisabled()
    
    fireEvent.change(screen.getByTestId('file-input-bank'), { target: { files: [validFile] } })
    
    // Now enabled
    expect(screen.getByTestId('submit-btn')).not.toBeDisabled()
  })

  it('displays loading state and submits payload to apiClient', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.ingestFiles).mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100))) // Never resolves in this test timeline
    
    render(<CsvIngestionPanel />, { wrapper: createWrapper() })
    
    const validFile = new File(['data'], 'test.csv', { type: 'text/csv' })
    fireEvent.change(screen.getByTestId('file-input-fir'), { target: { files: [validFile] } })
    fireEvent.change(screen.getByTestId('file-input-cdr'), { target: { files: [validFile] } })
    fireEvent.change(screen.getByTestId('file-input-bank'), { target: { files: [validFile] } })
    
    const submitBtn = screen.getByTestId('submit-btn')
    await user.click(submitBtn)
    
    expect(apiClient.ingestFiles).toHaveBeenCalledWith({
      fir: validFile,
      cdr: validFile,
      bank: validFile,
      intelligence: undefined
    })
    
    await waitFor(() => {
      expect(screen.getByTestId('submit-btn')).toBeDisabled()
      expect(screen.getByText(/Uploading files securely/i)).toBeInTheDocument()
    })
  })

  it('displays error message when backend fails', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.ingestFiles).mockRejectedValueOnce(new Error('Network disconnected'))
    
    render(<CsvIngestionPanel />, { wrapper: createWrapper() })
    
    const validFile = new File(['data'], 'test.csv', { type: 'text/csv' })
    fireEvent.change(screen.getByTestId('file-input-fir'), { target: { files: [validFile] } })
    fireEvent.change(screen.getByTestId('file-input-cdr'), { target: { files: [validFile] } })
    fireEvent.change(screen.getByTestId('file-input-bank'), { target: { files: [validFile] } })
    
    await user.click(screen.getByTestId('submit-btn'))
    
    await waitFor(() => {
      expect(screen.getByTestId('submit-error')).toHaveTextContent('Network disconnected')
    })
  })

  it('displays success panel and summary cards on successful ingestion', async () => {
    const user = userEvent.setup()
    
    const mockResponse: IngestionBatchResponse = {
      batch_id: 'batch_123',
      status: 'COMPLETED_WITH_WARNINGS',
      files_processed: [],
      summary: {
        received: 100,
        accepted: 90,
        rejected: 10,
        duplicates: 5,
        conflicts: 2,
        warnings: 3,
        source_records: 90,
        nodes_created: 50,
        nodes_reused: 10,
        relationships_created: 100,
        review_required: 4,
      },
      parse_issues: [
        { source_type: 'FIR', file_name: 'fir.csv', row_number: 10, code: 'VAL_ERR', message: 'Missing date', severity: 'ERROR' }
      ],
      review_candidates: [],
      graph_updated: true
    }
    
    vi.mocked(apiClient.ingestFiles).mockResolvedValueOnce(mockResponse)
    
    render(<CsvIngestionPanel />, { wrapper: createWrapper() })
    
    const validFile = new File(['data'], 'test.csv', { type: 'text/csv' })
    await user.upload(screen.getByTestId('file-input-fir'), validFile)
    await user.upload(screen.getByTestId('file-input-cdr'), validFile)
    await user.upload(screen.getByTestId('file-input-bank'), validFile)
    
    await user.click(screen.getByTestId('submit-btn'))
    
    await waitFor(() => {
      expect(screen.getByTestId('success-panel')).toBeInTheDocument()
    })
    
    expect(screen.getByText('Ingestion COMPLETED WITH WARNINGS')).toBeInTheDocument()
    expect(screen.getByText('batch_123')).toBeInTheDocument()
    
    // Check summary cards
    expect(screen.getByTestId('summary-received-rows')).toHaveTextContent('100')
    expect(screen.getByTestId('summary-rejected-rows')).toHaveTextContent('10')
    
    // Check issue table (mocked)
    expect(screen.getByTestId('mock-data-table')).toBeInTheDocument()
    
    // Test filter
    const filterSelect = screen.getByTestId('issue-filter')
    await user.selectOptions(filterSelect, 'INFO')
    
    expect(screen.getByText('No issues match your current filters.')).toBeInTheDocument()
    
    // Test Reset
    await user.click(screen.getByTestId('upload-another-btn'))
    
    // Should be back to initial view
    expect(screen.getByText('FIR & Cases')).toBeInTheDocument()
    expect(screen.getByTestId('submit-btn')).toBeDisabled()
  })
})
