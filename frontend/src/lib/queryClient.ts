import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './apiClient'

export function retryTransientRequest(failureCount: number, error: Error) {
  // A declared degraded service requires manual retry; transient transport errors get one retry.
  return failureCount < 1 && !(error instanceof ApiError && error.status >= 400 && error.status < 600)
}

// Only lightweight canonical reads use the cold-start recovery budget.
export function retryColdStartRequest(failureCount: number, error: Error) {
  return failureCount < 2 && (
    error instanceof ApiError
      ? [502, 503, 504].includes(error.status)
      : error instanceof TypeError || error.name === 'TimeoutError'
  )
}

export function coldStartRetryDelay(attempt: number) {
  // The final attempt also covers a 37s wake-up when proxies return 503 immediately.
  return attempt === 0 ? 2000 : 40000
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
