import { useState } from 'react'
import { Monitor, ShieldCheck, ShieldAlert, RotateCcw, Loader2, CheckCircle2, Settings as SettingsIcon } from 'lucide-react'
import { useResetDemo } from '@/hooks/useNexus'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'

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
    <div className="space-y-6 max-w-4xl mx-auto w-full">
      {/* Header */}
      <PageHeader
        icon={SettingsIcon}
        title="Workspace Settings"
        subtitle="Investigator environment preferences, role status, and demo sandbox management."
      />

      {/* Prototype Demo Mode & Sandbox */}
      <SectionCard
        title="Prototype Demo Mode &amp; Sandbox"
        subtitle="Manage synthetic demo data and test scenario resets"
      >
        <div className="space-y-4">
          <div className="rounded-lg bg-amber-50/70 border border-amber-200/80 p-4 text-xs text-amber-950 leading-relaxed space-y-1.5 shadow-2xs">
            <div className="font-bold text-amber-900 flex items-center gap-1.5">
              <span>🛡️ Hackathon Prototype Disclosure:</span>
            </div>
            <p>
              This system runs against <strong>synthetic intelligence fixtures</strong> generated for evaluation. Authentication is provided in role-switching demo mode and is not production SSO. Zero real citizen PII is processed.
            </p>
          </div>

          <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-neutral-100">
            <div>
              <div className="text-xs font-bold text-neutral-900">Reset Demo Fixture</div>
              <div className="text-[11px] text-neutral-500">Restore candidate decisions, graph links, and leads to clean initial state</div>
            </div>
            <button
              onClick={handleReset}
              disabled={resetMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 cursor-pointer shrink-0"
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
        </div>
      </SectionCard>

      {/* Display Settings */}
      <SectionCard
        title="Display &amp; Density"
        subtitle="Visual layout preferences and readability options"
      >
        <div className="space-y-4 text-xs">
          <div className="flex items-center justify-between py-2 border-b border-neutral-100">
            <div>
              <p className="font-bold text-neutral-900">Table Density</p>
              <p className="text-neutral-500 mt-0.5">Toggle between dense table view and comfortable layout</p>
            </div>
            <span className="text-neutral-600 font-mono bg-neutral-100 px-2 py-0.5 rounded border border-neutral-200 text-[11px]">Header toggle</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-bold text-neutral-900">Color Palette &amp; Theme</p>
              <p className="text-neutral-500 mt-0.5">Clean light theme optimized for law enforcement investigations</p>
            </div>
            <span className="text-blue-800 font-bold bg-blue-50 px-2 py-0.5 rounded border border-blue-200 text-[11px]">Light Workspace</span>
          </div>
        </div>
      </SectionCard>

      {/* Security & Access */}
      <SectionCard
        title="Security &amp; Regulatory Compliance"
        subtitle="Constitutional non-guilt principles and audit guarantees"
      >
        <div className="rounded-lg bg-neutral-50 p-4 border border-neutral-200/80 text-xs text-neutral-700 space-y-2">
          <div className="flex items-center gap-2 font-bold text-neutral-900">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            <span>Strict Indian Evidence Act &amp; Bharatiya Sakshya Adhiniyam (BSA) Compliance</span>
          </div>
          <p className="text-neutral-600 leading-relaxed">
            All graph operations preserve immutable provenance back to source records (FIRs, CDRs, Bank Transactions). No automated guilt determination is performed by the AI system.
          </p>
        </div>
      </SectionCard>
    </div>
  )
}
