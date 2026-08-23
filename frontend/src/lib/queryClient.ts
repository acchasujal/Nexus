import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0, // Enforces fresh refetches on every mount/invalidation
      retry: 1,     // Prevents long loading states on network error
      refetchOnWindowFocus: false, // Avoid excessive network traffic during demo
    },
  },
})
