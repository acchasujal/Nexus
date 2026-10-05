import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './apiClient'

export function retryTransientRequest(failureCount: number, error: Error) {
  // A declared degraded service requires manual retry; transient transport errors get one retry.
  return failureCount < 1 && !(error instanceof ApiError && error.status >= 400 && error.status < 600)
}

// Designated read queries opt into bounded cold-start recovery; mutations retain their own policy.
export function retryColdStartRequest(failureCount: number, error: Error) {
  return failureCount < 3 && (
    error instanceof ApiError
      ? [502, 503, 504].includes(error.status)
      : error instanceof TypeError || error.name === 'TimeoutError'
  )
}

export function coldStartRetryDelay(attempt: number) {
  // Preserve the early recovery window, then cover the observed ~89s idle wake
  // even when proxies fail immediately rather than holding the 20s request deadline.
  return attempt === 0 ? 2000 : attempt === 1 ? 40000 : 70000
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
