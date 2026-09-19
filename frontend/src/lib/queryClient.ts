import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30s default freshness window for deduped requests
      gcTime: 10 * 60 * 1000, // 10 minute cache retention
      retry: 1,     // Prevents long loading states on network error
      refetchOnWindowFocus: false, // Avoid excessive network traffic during demo
    },
  },
})
