/**
 * frontend/src/hooks/useIngestion.ts
 *
 * React Query hooks for the real CSV ingestion API (/api/v1/ingest).
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import type { IngestionBatchResponse } from '@shared/contracts/api'

export interface IngestFilesParams {
  fir?: File
  cdr?: File
  bank?: File
  intelligence?: File
}

export function useIngestFiles() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (files: IngestFilesParams) => apiClient.ingestFiles(files),
    onSuccess: (data: IngestionBatchResponse) => {
      if (data.graph_updated) {
        void qc.invalidateQueries({ queryKey: ['worklist'] })
        void qc.invalidateQueries({ queryKey: ['case-network'] })
        void qc.invalidateQueries({ queryKey: ['network'] })
        void qc.invalidateQueries({ queryKey: ['case'] })
        void qc.invalidateQueries({ queryKey: ['similar-cases'] })
        void qc.invalidateQueries({ queryKey: ['entities'] })
        void qc.invalidateQueries({ queryKey: ['timeline'] })
        void qc.invalidateQueries({ queryKey: ['evidence'] })
        void qc.invalidateQueries({ queryKey: ['patterns'] })
        void qc.invalidateQueries({ queryKey: ['nexus'] }) 
      }
    },
  })
}
