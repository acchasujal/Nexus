const RECOVERY_KEY = 'nexus_asset_recovery'

export function installAssetRecovery(reload = () => window.location.reload()) {
  window.addEventListener('vite:preloadError', event => {
    const build = import.meta.env.VITE_BUILD_ID || 'local'
    try {
      if (sessionStorage.getItem(RECOVERY_KEY) === build) return
      sessionStorage.setItem(RECOVERY_KEY, build)
      event.preventDefault()
      reload()
    } catch {
      // Storage denial must not introduce an unbounded reload loop.
    }
  })
}
