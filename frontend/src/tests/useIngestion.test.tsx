import { describe, it, expect, vi, afterEach } from 'vitest'
import { apiClient } from '@/lib/apiClient'

describe('apiClient.ingestFiles', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should successfully build FormData and transmit actual File bytes', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          batch_id: 'BATCH-TEST',
          status: 'COMPLETED',
          files_processed: [],
          summary: {
            received: 1,
            accepted: 1,
            rejected: 0,
            duplicates: 0,
            conflicts: 0,
            warnings: 0,
            source_records: 1,
            nodes_created: 1,
            nodes_reused: 0,
            relationships_created: 1,
            review_candidates: 0,
          },
          parse_issues: [],
          review_candidates: [],
          graph_updated: true,
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }
      )
    )
    const firContent = 'name,phone\nJohn Doe,1234567890'
    const firFile = new File([firContent], 'fir.csv', { type: 'text/csv' })

    const cdrContent = 'caller,receiver\n999,888'
    const cdrFile = new File([cdrContent], 'cdr.csv', { type: 'text/csv' })

    const result = await apiClient.ingestFiles({
      fir: firFile,
      cdr: cdrFile
    })

    expect(result.batch_id).toBe('BATCH-TEST')
    expect(result.graph_updated).toBe(true)

    // Verify fetch was called once
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    
    // Get the Request options passed to fetch
    const [url, options] = fetchSpy.mock.calls[0]
    expect(url).toContain('/api/v1/ingest')
    
    // Inspect the FormData body
    const formData = options?.body as FormData
    expect(formData).toBeInstanceOf(FormData)
    
    // Verify headers do NOT include application/json
    const headers = options?.headers as Record<string, string>
    expect(headers['Content-Type']).toBeUndefined()

    // Inspect FormData to prove actual file content is present
    const receivedFir = formData.get('fir') as File
    expect(receivedFir).toBeDefined()
    expect(receivedFir.name).toBe('fir.csv')
    expect(receivedFir).toBe(firFile)

    const receivedCdr = formData.get('cdr') as File
    expect(receivedCdr).toBeDefined()
    expect(receivedCdr.name).toBe('cdr.csv')
    expect(receivedCdr).toBe(cdrFile)
    
    // Ensure that it didn't send `bank` or `intelligence`
    expect(formData.get('bank')).toBeNull()
    expect(formData.get('intelligence')).toBeNull()
  })
})
