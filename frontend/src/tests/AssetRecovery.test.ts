import { afterEach, describe, expect, it, vi } from 'vitest'
import { installAssetRecovery } from '@/lib/assetRecovery'

afterEach(() => { sessionStorage.clear(); vi.restoreAllMocks() })
describe('deployment-race fallback', () => {
  it('reloads at most once and leaves a persistent failure available to the route boundary', () => {
    const reload = vi.fn()
    installAssetRecovery(reload)
    const first = new Event('vite:preloadError', { cancelable: true })
    window.dispatchEvent(first)
    expect(reload).toHaveBeenCalledTimes(1)
    expect(first.defaultPrevented).toBe(true)
    const second = new Event('vite:preloadError', { cancelable: true })
    window.dispatchEvent(second)
    expect(reload).toHaveBeenCalledTimes(1)
    expect(second.defaultPrevented).toBe(false)
  })
})
