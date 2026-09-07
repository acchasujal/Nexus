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

interface DemoOfficer {
  id: string
  name: string
  rank: string
  badge: string
  role: UserRole
  roleName: string
  scope: string
  icon: typeof UserCheck
  badgeColor: string
}

const DEMO_OFFICERS: DemoOfficer[] = [
  {
    id: 'KA-1001',
    name: 'Inspector Rajesh Kumar',
    rank: 'Inspector',
    badge: 'KA-1001',
    role: 'IO',
    roleName: 'Investigating Officer (IO)',
    scope: 'Case-level evidence, telecom CDRs, suspect pathfinding & grounded copilot',
    icon: UserCheck,
    badgeColor: 'text-blue-700 bg-blue-50 border-blue-200',
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
    badgeColor: 'text-amber-800 bg-amber-50 border-amber-200',
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
    badgeColor: 'text-emerald-800 bg-emerald-50 border-emerald-200',
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
    badgeColor: 'text-purple-800 bg-purple-50 border-purple-200',
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

  const handleSelectDemoOfficer = (officer: DemoOfficer) => {
    setUsername(officer.badge)
    setSelectedRole(officer.role)
    setPassword('••••••••••••')
    setErrorMessage(null)
    handleSubmit(undefined, { username: officer.badge, role: officer.role })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-900 px-4 py-8 sm:px-6 lg:px-8 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-neutral-800 via-neutral-900 to-black">
      <div className="w-full max-w-xl space-y-5">
        {/* Compliance Header Badge */}
        <div className="flex justify-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-950/60 px-3.5 py-1 text-xs font-semibold text-blue-300 shadow-inner backdrop-blur-xs">
            <Shield className="h-3.5 w-3.5 text-blue-400 shrink-0" />
            <span>NEXUS · Law Enforcement Intelligence Platform · SIH 2026</span>
          </div>
        </div>

        {/* Main Card */}
        <div className="rounded-2xl border border-neutral-800 bg-neutral-950/90 p-6 sm:p-8 shadow-2xl backdrop-blur-md space-y-6">
          {/* Brand Header */}
          <div className="text-center space-y-2">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-600/30">
              <Network className="h-6 w-6" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              NEXUS
            </h1>
            <p className="text-xs font-bold uppercase tracking-wider text-blue-400">
              AI-Powered Criminal Network Analysis & Investigation Platform
            </p>
          </div>

          {/* Security Notice Banner */}
          <div className="rounded-lg border border-amber-500/30 bg-amber-950/30 px-3.5 py-2.5 text-center">
            <p className="text-xs font-medium text-amber-200/90 flex items-center justify-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-amber-400 shrink-0" />
              <span>Restricted Access · Authorized Personnel Only · Cryptographically Audited</span>
            </p>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div 
              role="alert" 
              className="flex items-start gap-2.5 rounded-lg border border-red-500/40 bg-red-950/40 p-3 text-xs text-red-200"
              data-testid="login-error-alert"
            >
              <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="font-semibold block">Authentication Refusal:</span>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={(e) => handleSubmit(e)} className="space-y-4">
            <div>
              <label 
                htmlFor="officer-id-input" 
                className="block text-xs font-bold uppercase tracking-wider text-neutral-300 mb-1.5"
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
                  placeholder="e.g. KA-1001 or officer_io"
                  disabled={isLoading}
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-900/90 pl-9 pr-3 py-2.5 text-sm text-white placeholder-neutral-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-hidden transition-colors"
                  data-testid="officer-id-input"
                />
              </div>
            </div>

            <div>
              <label 
                htmlFor="password-input" 
                className="block text-xs font-bold uppercase tracking-wider text-neutral-300 mb-1.5"
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
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-900/90 pl-9 pr-10 py-2.5 text-sm text-white placeholder-neutral-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-hidden transition-colors"
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
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 px-4 py-2.5 text-sm font-bold text-white shadow-md shadow-blue-600/20 disabled:opacity-60 disabled:cursor-not-allowed transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-400"
              data-testid="login-submit-button"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Verifying Officer Credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Intelligence Workspace</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Demo Officers Quick Fill Helper */}
          <div className="border-t border-neutral-800 pt-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-400">
                Authorized Demo Profiles
              </span>
              <span className="text-[11px] text-neutral-500">
                Click to authenticate
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {DEMO_OFFICERS.map((officer) => {
                const Icon = officer.icon
                return (
                  <button
                    key={officer.id}
                    type="button"
                    onClick={() => handleSelectDemoOfficer(officer)}
                    disabled={isLoading}
                    className="group flex flex-col items-start p-3 rounded-xl border border-neutral-800 bg-neutral-900/60 hover:bg-neutral-800/80 hover:border-blue-500/50 text-left transition-all cursor-pointer disabled:opacity-50"
                    data-testid={`demo-officer-${officer.role.toLowerCase()}`}
                  >
                    <div className="flex items-center gap-2 w-full mb-1">
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-neutral-800 border border-neutral-700 text-blue-400 group-hover:border-blue-500 group-hover:text-blue-300">
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-bold text-white group-hover:text-blue-300 truncate block">
                          {officer.name}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between w-full text-[11px] text-neutral-400 mt-0.5">
                      <span className="font-mono text-[10px] text-blue-400 bg-blue-950/60 px-1.5 py-0.5 rounded border border-blue-800/50">
                        {officer.badge}
                      </span>
                      <span className="text-neutral-400 text-[10px] font-semibold uppercase">
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
          <div className="border-t border-neutral-800 pt-4 text-center space-y-1">
            <p className="text-[11px] text-neutral-400 font-medium">
              Deterministic Graph Analytics · Evidence-Grounded Attribution · Tamper-Proof Audit Logging
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
