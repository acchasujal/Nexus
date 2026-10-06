import type { SyncState } from '@/hooks/useRecoveringQuery'

export function SyncStatus({ state, isBaseline = false }: { state: SyncState; isBaseline?: boolean }) {
  const message = isBaseline
    ? state === 'syncing'
      ? 'Canonical demo baseline; Connecting to intelligence services...'
      : 'Canonical demo baseline; synchronization paused after bounded retries.'
    : state === 'refreshing' ? 'Refreshing live data...'
    : state === 'confirmed' ? 'Confirmed API data'
    : state === 'stale' ? 'Last confirmed data; synchronization paused after bounded retries.'
    : state === 'retrying' ? 'Connecting to intelligence services; automatic retries exhausted. Retry or return when connected.'
    : state === 'unavailable' ? 'Intelligence request failed; check access or request details.'
    : 'Loading network intelligence...'
  return <div role="status" className="rounded-lg border border-blue-200 bg-blue-50/60 px-3 py-2 text-xs text-blue-900">{message}</div>
}
