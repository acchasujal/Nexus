import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import type { UserRole } from '@shared/contracts/api'
import { Network, ShieldCheck, ShieldAlert } from 'lucide-react'

export default function Login() {
  const { role, login, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  if (isAuthenticated && role) {
    return <Navigate to="/worklist" replace />
  }

  const handleRoleSelection = (selectedRole: UserRole) => {
    login(selectedRole)
    navigate('/worklist')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-950 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 bg-neutral-900/90 p-8 rounded-2xl border border-neutral-800 shadow-2xl text-center">
        {/* Title area */}
        <div className="space-y-3">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 shadow-lg shadow-blue-500/20 text-white">
            <Network className="h-8 w-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">NEXUS</h1>
          <p className="text-xs text-blue-400 font-semibold uppercase tracking-wider">
            Criminal Network Intelligence Platform
          </p>
          <p className="text-xs text-neutral-400">
            Select an investigator role to enter the intelligence graph workspace
          </p>
        </div>

        {/* Role Selector Buttons */}
        <div className="mt-8 space-y-3">
          <button
            onClick={() => handleRoleSelection('IO')}
            className="flex w-full items-center justify-between rounded-xl border border-neutral-800 bg-neutral-950/80 px-5 py-3.5 text-left text-neutral-200 hover:bg-neutral-800 hover:border-blue-500/50 hover:text-white transition-all shadow-sm group"
          >
            <div>
              <div className="text-sm font-bold group-hover:text-blue-400 transition-colors">Investigating Officer (IO)</div>
              <div className="text-xs text-neutral-400">Case exploration, entity resolution & copilot</div>
            </div>
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
          </button>

          <button
            onClick={() => handleRoleSelection('SHO')}
            className="flex w-full items-center justify-between rounded-xl border border-neutral-800 bg-neutral-950/80 px-5 py-3.5 text-left text-neutral-200 hover:bg-neutral-800 hover:border-blue-500/50 hover:text-white transition-all shadow-sm group"
          >
            <div>
              <div className="text-sm font-bold group-hover:text-blue-400 transition-colors">Intelligence Analyst / SHO</div>
              <div className="text-xs text-neutral-400">Syndicate modularity & bridge broker discovery</div>
            </div>
            <ShieldAlert className="h-5 w-5 text-amber-400" />
          </button>

          <button
            onClick={() => handleRoleSelection('SP')}
            className="flex w-full items-center justify-between rounded-xl border border-neutral-800 bg-neutral-950/80 px-5 py-3.5 text-left text-neutral-200 hover:bg-neutral-800 hover:border-blue-500/50 hover:text-white transition-all shadow-sm group"
          >
            <div>
              <div className="text-sm font-bold group-hover:text-blue-400 transition-colors">Superintendent / Supervisor (SP)</div>
              <div className="text-xs text-neutral-400">District intelligence rollup & immutable audit trail</div>
            </div>
            <ShieldCheck className="h-5 w-5 text-blue-400" />
          </button>
        </div>

        {/* Footer */}
        <div className="text-[11px] text-neutral-500 pt-2 border-t border-neutral-800/60">
          SIH 2026 PS 26189. Evidence-Grounded Criminal Intelligence Platform.
        </div>
      </div>
    </div>
  )
}
