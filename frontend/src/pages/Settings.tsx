import { useState } from 'react'
import { Monitor, Bell, ShieldCheck, ShieldAlert, RotateCcw, Loader2, CheckCircle2 } from 'lucide-react'
import { useResetDemo } from '@/hooks/useNexus'

export default function Settings() {
  const resetMutation = useResetDemo()
  const [resetMsg, setResetMsg] = useState<string | null>(null)

  const handleReset = async () => {
    try {
      await resetMutation.mutateAsync()
      setResetMsg('Synthetic demo graph and fixture state successfully reset!')
      setTimeout(() => setResetMsg(null), 3000)
    } catch (err) {
      setResetMsg(err instanceof Error ? err.message : 'Reset failed')
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="border-b border-neutral-200 pb-5">
        <h1 className="text-2xl font-bold text-neutral-900">Workspace Settings</h1>
        <p className="text-sm text-neutral-600 mt-1">
          Investigator environment preferences, role status, and demo sandbox management.
        </p>
      </div>

      {/* Prototype Demo Mode & Sandbox */}
      <section aria-labelledby="demo-mode-heading" className="rounded-xl border border-blue-200 bg-white p-6 space-y-4 shadow-sm">
        <div className="flex items-center gap-3">
          <ShieldAlert className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <h2 id="demo-mode-heading" className="text-base font-bold text-neutral-900">
            Prototype Demo Mode
          </h2>
        </div>

        <div className="rounded-lg bg-amber-50 border border-amber-200 p-4 text-xs text-amber-950 leading-relaxed space-y-1.5 shadow-xs">
          <div className="font-bold text-amber-900 flex items-center gap-1.5">
            <span>🛡️ Hackathon Prototype Disclosure:</span>
          </div>
          <p>
            This system runs against <strong>synthetic intelligence fixtures</strong> generated for evaluation. Authentication is provided in role-switching demo mode and is not production SSO. Zero real citizen PII is processed.
          </p>
        </div>

        <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-neutral-200">
          <div>
            <div className="text-xs font-bold text-neutral-900">Reset Demo Fixture</div>
            <div className="text-[11px] text-neutral-600">Restore candidate decisions, graph links, and leads to clean initial state</div>
          </div>
          <button
            onClick={handleReset}
            disabled={resetMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 text-xs font-bold shadow-sm transition-colors disabled:opacity-50"
          >
            {resetMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RotateCcw className="h-3.5 w-3.5" />
            )}
            {resetMutation.isPending ? 'Resetting…' : 'Reset Demo State'}
          </button>
        </div>

        {resetMsg && (
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-900 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            {resetMsg}
          </div>
        )}
      </section>

      {/* Display Settings */}
      <section aria-labelledby="display-settings-heading" className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <Monitor className="h-5 w-5 text-neutral-600" aria-hidden="true" />
          <h2 id="display-settings-heading" className="text-base font-bold text-neutral-900">
            Display &amp; Density
          </h2>
        </div>
        <div className="space-y-4 text-xs">
          <div className="flex items-center justify-between py-3 border-b border-neutral-200">
            <div>
              <p className="font-bold text-neutral-900">Table Density</p>
              <p className="text-neutral-600 mt-0.5">Toggle between dense table view and comfortable card layout</p>
            </div>
            <span className="text-neutral-600 font-mono bg-neutral-100 px-2 py-0.5 rounded border border-neutral-200">Header control</span>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-bold text-neutral-900">Color Palette &amp; Theme</p>
              <p className="text-neutral-600 mt-0.5">Clean light theme optimized for law enforcement investigations</p>
            </div>
            <span className="text-blue-800 font-bold bg-blue-50 px-2 py-0.5 rounded border border-blue-200">Light Workspace</span>
          </div>
        </div>
      </section>

      {/* Security & Access */}
      <section aria-labelledby="security-settings-heading" className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <ShieldCheck className="h-5 w-5 text-emerald-600" aria-hidden="true" />
          <h2 id="security-settings-heading" className="text-base font-bold text-neutral-900">
            Security &amp; Audit Governance
          </h2>
        </div>
        <div className="space-y-4 text-xs">
          <div className="flex items-center justify-between py-3 border-b border-neutral-200">
            <div>
              <p className="font-bold text-neutral-900">Audit Logging</p>
              <p className="text-neutral-600 mt-0.5">Immutable audit logging on every investigator confirmation, deferral, and lead decision</p>
            </div>
            <span className="text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-bold font-mono">Active (100%)</span>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-bold text-neutral-900">Statutory Guardrail</p>
              <p className="text-neutral-600 mt-0.5">Deterministic refusal gate active against predictive guilt scoring</p>
            </div>
            <span className="text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-bold font-mono">Enforced</span>
          </div>
        </div>
      </section>
    </div>
  )
}
