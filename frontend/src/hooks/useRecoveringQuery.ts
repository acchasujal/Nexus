import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient, hashKey, type UseQueryOptions } from '@tanstack/react-query'
import { ApiError } from '@/lib/apiClient'
import { retryColdStartRequest, coldStartRetryDelay } from '@/lib/queryClient'

const catchUpUsed = new WeakSet<object>()

export type SyncState = 'baseline' | 'syncing' | 'confirmed' | 'stale' | 'unavailable'

export function useRecoveringQuery<T>(options: UseQueryOptions<T, Error>, baseline?: T) {
  const client = useQueryClient()
  const latestOptions = useRef(options)
  useEffect(() => { latestOptions.current = options }, [options])
  const key = hashKey(options.queryKey)
  const query = useQuery({
    retry: retryColdStartRequest,
    retryDelay: coldStartRetryDelay,
    refetchOnWindowFocus: query => query.state.status === 'error',
    ...options,
    meta: { ...options.meta, recoveringRead: true },
  })
  useEffect(() => {
    const cache = client.getQueryCache()
    const target = cache.find({ queryKey: latestOptions.current.queryKey, exact: true })
    return cache.subscribe(event => {
      if (event.type !== 'updated' || event.action.type !== 'success' || event.action.manual || event.query === target) return
      if (!target || !target.isActive() || target.state.status !== 'error' || catchUpUsed.has(target)) return
      const error = target.state.error
      // One healthy read can wake an exhausted observer once. Never wake disabled tabs,
      // retry permission failures, or allow success/failure cycles to create a retry storm.
      if (!(error instanceof Error) || !retryColdStartRequest(0, error)) return
      if (event.query.meta?.recoveringRead !== true) return
      catchUpUsed.add(target)
      void client.fetchQuery({ ...latestOptions.current, retry: false }).catch(() => undefined)
    })
  }, [client, key])

  // Keep the baseline outside the cache so it cannot delay or masquerade as API confirmation.
  // Permission failures must remain visible and must not reveal baseline detail as a fallback.
  const refused = query.error instanceof ApiError && [401, 403].includes(query.error.status)
  const isBaseline = !refused && query.data === undefined && baseline !== undefined
  const data = refused ? undefined : query.data ?? baseline
  const transient = query.error && retryColdStartRequest(0, query.error)
  const showError = query.isError && !(transient && data !== undefined)
  const syncState: SyncState = isBaseline
    ? query.isFetching ? 'syncing' : 'baseline'
    : query.isFetching ? 'syncing'
    : query.isError ? data !== undefined && !showError ? 'stale' : 'unavailable'
    : data !== undefined ? 'confirmed' : 'syncing'
  return { ...query, data, isBaseline, syncState,
    isPending: query.isPending && data === undefined,
    isLoading: query.isLoading && data === undefined,
    isError: showError, error: showError ? query.error : null, syncError: query.error }
}
