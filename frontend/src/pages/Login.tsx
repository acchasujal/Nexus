import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import type { UserRole } from '@shared/contracts/api'
import { Network, ShieldCheck, ShieldAlert, UserCheck, ArrowRight, Shield } from 'lucide-react'

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

  const rolesList: Array<{
    id: UserRole
    title: string
    subtitle: string
    description: string
    icon: typeof ShieldCheck
    badgeColor: string
  }> = [
    {
      id: 'IO',
      title: 'Investigating Officer (IO)',
      subtitle: 'Field & Station Intelligence',
      description: 'FIR analysis, phone/bank entity resolution, graph pathfinding & grounded copilot.',
      icon: UserCheck,
      badgeColor: 'text-blue-700 bg-blue-50 border-blue-200',
    },
    {
      id: 'SHO',
      title: 'Intelligence Analyst / SHO',
      subtitle: 'Syndicate & Modularity Analysis',
      description: 'Louvain community clustering, betweenness bridge broker discovery & lead triage.',
      icon: ShieldAlert,
      badgeColor: 'text-amber-800 bg-amber-50 border-amber-200',
    },
    {
      id: 'SP',
      title: 'Superintendent of Police (SP)',
      subtitle: 'Supervisory & Audit Oversight',
      description: 'District crime hotspot rollup, multi-jurisdiction bridges & tamper-proof audit trail.',
      icon: ShieldCheck,
      badgeColor: 'text-emerald-800 bg-emerald-50 border-emerald-200',
    },
  ]

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="w-full max-w-lg space-y-6">
        {/* Compliance Pill */}
        <div className="flex justify-center">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-blue-200/80 bg-blue-50/70 px-3 py-1 text-xs font-semibold text-blue-900 shadow-2xs">
            <Shield className="h-3.5 w-3.5 text-blue-600" />
            <span>MHA / NCRB Intelligence Standard · SIH 2026 PS 26189</span>
          </div>
        </div>

        {/* Card Container */}
        <div className="rounded-2xl border border-neutral-200/90 bg-white p-6 sm:p-8 shadow-sm space-y-6">
          {/* Brand & Heading */}
          <div className="text-center space-y-2">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white shadow-xs">
              <Network className="h-6 w-6" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-neutral-900">
              NEXUS
            </h1>
            <p className="text-xs font-bold uppercase tracking-wider text-blue-700">
              Evidence-Grounded Criminal Network Intelligence
            </p>
            <p className="text-xs sm:text-sm text-neutral-600 max-w-sm mx-auto pt-1">
              Select an authorized investigator role to access the multi-jurisdictional evidence graph workspace.
            </p>
          </div>

          {/* Role Cards */}
          <div className="space-y-3 pt-2">
            {rolesList.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  onClick={() => handleRoleSelection(item.id)}
                  className="group w-full flex items-start justify-between gap-3.5 rounded-xl border border-neutral-200/80 bg-neutral-50/50 p-4 text-left hover:bg-white hover:border-blue-300 hover:shadow-xs transition-all cursor-pointer"
                >
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white border border-neutral-200 shadow-2xs group-hover:border-blue-200 group-hover:text-blue-600 transition-colors">
                      <Icon className="h-4 w-4 text-neutral-700 group-hover:text-blue-600" />
                    </div>
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-neutral-900 group-hover:text-blue-700 transition-colors">
                          {item.title}
                        </span>
                      </div>
                      <p className="text-xs font-medium text-neutral-500">
                        {item.subtitle}
                      </p>
                      <p className="text-xs text-neutral-600 pt-1 leading-relaxed">
                        {item.description}
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-neutral-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all shrink-0 mt-1" />
                </button>
              )
            })}
          </div>

          {/* Governance Footer */}
          <div className="border-t border-neutral-100 pt-4 text-center space-y-1">
            <p className="text-[11px] text-neutral-500 font-medium">
              Deterministic Graph Analytics · Zero Black-Box Predictive Bias · Section 63 BSA Provenance
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
