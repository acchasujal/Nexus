import { useState } from 'react'
import { Navigate, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import type { UserRole } from '@shared/contracts/api'
import { 
  Network, 
  ShieldCheck, 
  ShieldAlert, 
  UserCheck, 
  Shield, 
  Lock, 
  User, 
  Eye, 
  EyeOff, 
  Loader2, 
  AlertCircle,
  KeyRound,
  ArrowRight
} from 'lucide-react'

interface OfficerProfile {
  id: string
  name: string
  rank: string
  badge: string
  role: UserRole
  roleName: string
  scope: string
  icon: typeof UserCheck
}

const AUTHORIZED_OFFICERS: OfficerProfile[] = [
  {
    id: 'KA-1001',
    name: 'Inspector Rajesh Kumar',
    rank: 'Inspector',
    badge: 'KA-1001',
    role: 'IO',
    roleName: 'Investigating Officer (IO)',
    scope: 'Case-level evidence, telecom CDRs, suspect pathfinding & grounded copilot',
    icon: UserCheck,
  },
  {
    id: 'KA-1002',
    name: 'SHO Sunita Sharma',
    rank: 'Station House Officer',
    badge: 'KA-1002',
    role: 'SHO',
    roleName: 'SHO / Intelligence Analyst',
    scope: 'Louvain syndicate communities, betweenness brokers & lead actioning',
    icon: ShieldAlert,
  },
  {
    id: 'KA-1003',
    name: 'SP Vikram Hegde',
    rank: 'Superintendent of Police',
    badge: 'KA-1003',
    role: 'SP',
    roleName: 'Superintendent of Police (SP)',
    scope: 'District hotspot rollup, cross-jurisdiction bridges & tamper-proof audit trail',
    icon: ShieldCheck,
  },
  {
    id: 'KA-1000',
    name: 'System Administrator',
    rank: 'Director of Cyber Intelligence',
    badge: 'KA-1000',
    role: 'ADMIN',
    roleName: 'System Administrator',
    scope: 'National cybercrime operations, ledger anchors & full forensic governance',
    icon: Shield,
  },
]

export default function Login() {
  const { role, login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [selectedRole, setSelectedRole] = useState<UserRole | undefined>(undefined)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Redirect if already authenticated
  if (isAuthenticated && role) {
    const from = (location.state as { from?: { pathname?: string } })?.from?.pathname || '/worklist'
    return <Navigate to={from} replace />
  }

  const handleSubmit = async (e?: React.FormEvent, overrideCreds?: { username: string; role?: UserRole }) => {
    if (e) e.preventDefault()
    
    const targetUsername = (overrideCreds?.username || username).trim()
    const targetRole = overrideCreds?.role || selectedRole
    
    if (!targetUsername) {
      setErrorMessage('Please enter your Officer ID or Service Number.')
      return
    }

    setIsLoading(true)
    setErrorMessage(null)

    try {
      await login({
        username: targetUsername,
        password: password || 'nexus-demo-passcode',
        role: targetRole,
      })
      const destination = (location.state as { from?: { pathname?: string } })?.from?.pathname || '/worklist'
      navigate(destination, { replace: true })
    } catch (err: any) {
      const msg = err?.message || 'Authentication failed. Please verify your officer credentials.'
      setErrorMessage(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectOfficer = (officer: OfficerProfile) => {
    setUsername(officer.badge)
    setSelectedRole(officer.role)
    setPassword('••••••••••••')
    setErrorMessage(null)
    handleSubmit(undefined, { username: officer.badge, role: officer.role })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-900 px-4 py-8 sm:px-6 lg:px-8">
      <div className="w-full max-w-xl space-y-5">
        {/* Compliance Header Badge */}
        <div className="flex justify-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-neutral-700 bg-neutral-800/80 px-3.5 py-1 text-xs font-medium text-neutral-300">
            <Shield className="h-3.5 w-3.5 text-neutral-400 shrink-0" />
            <span>Official System · Authorized Access Only</span>
          </div>
        </div>

        {/* Main Card */}
        <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-6 sm:p-8 shadow-xl space-y-6">
          {/* Brand Header */}
          <div className="text-center space-y-1.5">
            <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
              <Network className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              NEXUS
            </h1>
            <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">
              Investigative Network Intelligence Platform
            </p>
          </div>

          {/* Security Notice Banner */}
          <div className="rounded-lg border border-neutral-800 bg-neutral-900/80 px-3.5 py-2.5 text-center">
            <p className="text-xs font-medium text-neutral-300 flex items-center justify-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-neutral-400 shrink-0" />
              <span>Restricted Access · All Sessions Cryptographically Audited</span>
            </p>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div 
              role="alert" 
              className="flex items-start gap-2.5 rounded-lg border border-red-900/60 bg-red-950/40 p-3 text-xs text-red-200"
              data-testid="login-error-alert"
            >
              <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="font-semibold block">Authentication Error:</span>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={(e) => handleSubmit(e)} className="space-y-4">
            <div>
              <label 
                htmlFor="officer-id-input" 
                className="block text-xs font-semibold uppercase tracking-wider text-neutral-300 mb-1.5"
              >
                Officer ID / Service Identifier
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-500">
                  <User className="h-4 w-4" />
                </div>
                <input
                  id="officer-id-input"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. KA-1001"
                  disabled={isLoading}
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-900 pl-9 pr-3 py-2.5 text-sm text-white placeholder-neutral-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-hidden transition-colors"
                  data-testid="officer-id-input"
                />
              </div>
            </div>

            <div>
              <label 
                htmlFor="password-input" 
                className="block text-xs font-semibold uppercase tracking-wider text-neutral-300 mb-1.5"
              >
                Security Passcode / Token
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-500">
                  <KeyRound className="h-4 w-4" />
                </div>
                <input
                  id="password-input"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  disabled={isLoading}
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-900 pl-9 pr-10 py-2.5 text-sm text-white placeholder-neutral-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-hidden transition-colors"
                  data-testid="password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-neutral-400 hover:text-neutral-200 cursor-pointer"
                  aria-label={showPassword ? 'Hide passcode' : 'Show passcode'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm disabled:opacity-60 disabled:cursor-not-allowed transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-400"
              data-testid="login-submit-button"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Intelligence Workspace</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Authorized Officer Fast-Select */}
          <div className="border-t border-neutral-800/80 pt-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-neutral-400">
                Evaluation Workspace Access
              </span>
              <span className="text-[11px] text-neutral-500">
                Select profile to sign in
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {AUTHORIZED_OFFICERS.map((officer) => {
                const Icon = officer.icon
                return (
                  <button
                    key={officer.id}
                    type="button"
                    onClick={() => handleSelectOfficer(officer)}
                    disabled={isLoading}
                    className="group flex flex-col items-start p-3 rounded-lg border border-neutral-800 bg-neutral-900 hover:bg-neutral-850 hover:border-neutral-700 text-left transition-colors cursor-pointer disabled:opacity-50"
                    data-testid={`demo-officer-${officer.role.toLowerCase()}`}
                  >
                    <div className="flex items-center gap-2 w-full mb-1">
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-neutral-800 border border-neutral-700 text-neutral-300 group-hover:text-white">
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-semibold text-neutral-200 group-hover:text-white truncate block">
                          {officer.name}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between w-full text-[11px] text-neutral-400 mt-0.5">
                      <span className="font-mono text-[10px] text-neutral-300 bg-neutral-800 px-1.5 py-0.5 rounded border border-neutral-700">
                        {officer.badge}
                      </span>
                      <span className="text-neutral-400 text-[10px] font-medium uppercase">
                        {officer.role}
                      </span>
                    </div>
                    <p className="text-[10px] text-neutral-500 line-clamp-2 mt-1 leading-tight">
                      {officer.scope}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Footer Statutory Disclaimers */}
          <div className="border-t border-neutral-800/80 pt-4 text-center space-y-1">
            <p className="text-[11px] text-neutral-400 font-medium">
              Deterministic Graph Analytics · Evidence-Grounded Attribution · Tamper-Proof Audit Logging
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
