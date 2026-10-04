import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './apiClient'

export function retryTransientRequest(failureCount: number, error: Error) {
  // A declared degraded service requires manual retry; transient transport errors get one retry.
  return failureCount < 1 && !(error instanceof ApiError && error.status >= 400 && error.status < 600)
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30s default freshness window for deduped requests
      gcTime: 10 * 60 * 1000, // 10 minute cache retention
      retry: retryTransientRequest,
      retryDelay: 1000,
      refetchOnWindowFocus: false, // Avoid excessive network traffic during demo
    },
  },
})
