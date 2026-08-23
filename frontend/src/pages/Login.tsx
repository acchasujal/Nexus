import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import type { UserRole } from '@shared/contracts/api'
import { Clock, Shield } from 'lucide-react'

export default function Login() {
  const { role, login, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  // If already logged in, redirect to worklist
  if (isAuthenticated && role) {
    const targetRoute = role === 'SP' ? '/rollup' : '/worklist'
    return <Navigate to={targetRoute} replace />
  }

  const handleRoleSelection = (selectedRole: UserRole) => {
    login(selectedRole)
    // Redirect SP to Rollup home, IO/SHO to Worklist home
    if (selectedRole === 'SP') {
      navigate('/rollup')
    } else {
      navigate('/worklist')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-900 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 bg-neutral-800 p-8 rounded-radius-lg border border-neutral-700 shadow-lg text-center">
        {/* Title area */}
        <div className="space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-radius-full bg-status-info/10 text-status-info">
            <Clock className="h-6 w-6" />
          </div>
          <h2 className="text-h1 font-bold tracking-tight text-neutral-50">CaseClock</h2>
          <p className="text-body text-neutral-400">
            Select a policing role to enter the investigation command center
          </p>
        </div>

        {/* Role Selector Buttons */}
        <div className="mt-8 space-y-4">
          <button
            onClick={() => handleRoleSelection('IO')}
            className="flex w-full items-center justify-between rounded-radius-md border border-neutral-700 bg-neutral-800 px-6 py-4 text-left text-neutral-200 hover:bg-neutral-700/80 hover:text-neutral-50 transition-colors duration-fast focus-visible:outline-status-info focus-visible:ring-1 focus-visible:ring-status-info"
          >
            <div>
              <div className="text-body font-bold">Investigating Officer (IO)</div>
              <div className="text-caption text-neutral-400">Manage daily case lists and statutory clocks</div>
            </div>
            <Shield className="h-5 w-5 text-status-success" />
          </button>

          <button
            onClick={() => handleRoleSelection('SHO')}
            className="flex w-full items-center justify-between rounded-radius-md border border-neutral-700 bg-neutral-800 px-6 py-4 text-left text-neutral-200 hover:bg-neutral-700/80 hover:text-neutral-50 transition-colors duration-fast focus-visible:outline-status-info focus-visible:ring-1 focus-visible:ring-status-info"
          >
            <div>
              <div className="text-body font-bold">Station Head Officer (SHO)</div>
              <div className="text-caption text-neutral-400">Review case blockers and escalation queues</div>
            </div>
            <Shield className="h-5 w-5 text-status-warning" />
          </button>

          <button
            onClick={() => handleRoleSelection('SP')}
            className="flex w-full items-center justify-between rounded-radius-md border border-neutral-700 bg-neutral-800 px-6 py-4 text-left text-neutral-200 hover:bg-neutral-700/80 hover:text-neutral-50 transition-colors duration-fast focus-visible:outline-status-info focus-visible:ring-1 focus-visible:ring-status-info"
          >
            <div>
              <div className="text-body font-bold">Superintendent of Police (SP)</div>
              <div className="text-caption text-neutral-400">Exception-only district-wide metrics rollup</div>
            </div>
            <Shield className="h-5 w-5 text-status-danger" />
          </button>
        </div>

        {/* Footer */}
        <div className="text-caption text-neutral-500">
          Karnataka State Police Datathon 2026. DPDP Compliant (Synthetic Data).
        </div>
      </div>
    </div>
  )
}
