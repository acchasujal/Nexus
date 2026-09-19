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
    <div className="flex min-h-screen flex-col justify-between bg-neutral-50 text-neutral-800 px-4 py-8 sm:px-6 lg:px-8">
      {/* Top Institutional Header */}
      <header className="w-full max-w-xl mx-auto flex flex-col items-center text-center space-y-2">
        <div className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-3.5 py-1 text-xs font-semibold text-neutral-600 shadow-2xs">
          <Shield className="h-3.5 w-3.5 text-blue-600 shrink-0" />
          <span>Official Law Enforcement Portal · Authorized Access Only</span>
        </div>
        <p className="text-[11px] font-medium tracking-wide text-neutral-500 uppercase">
          Ministry of Home Affairs (MHA) · National Crime Records Bureau · Women Safety Division
        </p>
      </header>

      {/* Main Login Card */}
      <main className="w-full max-w-xl mx-auto my-auto py-4">
        <div className="rounded-xl border border-neutral-200/90 bg-white p-6 sm:p-8 shadow-sm space-y-6">
          {/* Brand Header */}
          <div className="text-center space-y-2">
            <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
              <Network className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-neutral-900">
                NEXUS
              </h1>
              <p className="text-xs font-bold uppercase tracking-wider text-blue-700 mt-0.5">
                Investigative Network Intelligence Platform
              </p>
            </div>
          </div>

          {/* Security Notice Banner */}
          <div className="rounded-lg border border-neutral-200 bg-neutral-50/80 px-3.5 py-2.5 text-center shadow-2xs">
            <p className="text-xs font-medium text-neutral-700 flex items-center justify-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-neutral-500 shrink-0" />
              <span>Restricted Access · All Sessions Cryptographically Audited</span>
            </p>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div 
              role="alert" 
              className="flex items-start gap-2.5 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800"
              data-testid="login-error-alert"
            >
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="font-bold block">Authentication Error:</span>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={(e) => handleSubmit(e)} className="space-y-4">
            <div>
              <label 
                htmlFor="officer-id-input" 
                className="block text-xs font-bold uppercase tracking-wider text-neutral-700 mb-1.5"
              >
                Officer ID / Service Identifier
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-400">
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
                  className="w-full rounded-lg border border-neutral-300 bg-white pl-9 pr-3 py-2.5 text-sm text-neutral-900 placeholder-neutral-400 focus:border-blue-600 focus:ring-1 focus:ring-blue-600 focus:outline-hidden transition-colors shadow-2xs disabled:bg-neutral-100"
                  data-testid="officer-id-input"
                />
              </div>
            </div>

            <div>
              <label 
                htmlFor="password-input" 
                className="block text-xs font-bold uppercase tracking-wider text-neutral-700 mb-1.5"
              >
                Security Passcode / Token
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-400">
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
                  className="w-full rounded-lg border border-neutral-300 bg-white pl-9 pr-10 py-2.5 text-sm text-neutral-900 placeholder-neutral-400 focus:border-blue-600 focus:ring-1 focus:ring-blue-600 focus:outline-hidden transition-colors shadow-2xs disabled:bg-neutral-100"
                  data-testid="password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-neutral-400 hover:text-neutral-700 cursor-pointer"
                  aria-label={showPassword ? 'Hide passcode' : 'Show passcode'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-xs disabled:opacity-60 disabled:cursor-not-allowed transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-600"
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
          <div className="border-t border-neutral-200/90 pt-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-700">
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
                    className="group flex flex-col items-start p-3 rounded-lg border border-neutral-200 bg-neutral-50/70 hover:bg-blue-50/40 hover:border-blue-300 text-left transition-all cursor-pointer disabled:opacity-50 shadow-2xs"
                    data-testid={`demo-officer-${officer.role.toLowerCase()}`}
                  >
                    <div className="flex items-center gap-2 w-full mb-1">
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-white border border-neutral-200 text-neutral-600 group-hover:text-blue-600 group-hover:border-blue-200 shadow-2xs">
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-bold text-neutral-900 group-hover:text-blue-900 truncate block">
                          {officer.name}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between w-full text-[11px] text-neutral-500 mt-0.5">
                      <span className="font-mono text-[10px] font-semibold text-neutral-700 bg-neutral-200/80 px-1.5 py-0.5 rounded border border-neutral-300/80">
                        {officer.badge}
                      </span>
                      <span className="text-blue-700 bg-blue-50 border border-blue-200/80 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                        {officer.role}
                      </span>
                    </div>
                    <p className="text-[10px] text-neutral-600 line-clamp-2 mt-1.5 leading-snug">
                      {officer.scope}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Card Footer Statutory Disclaimers */}
          <div className="border-t border-neutral-200/90 pt-4 text-center space-y-1">
            <p className="text-[11px] text-neutral-600 font-medium">
              Deterministic Graph Analytics · Evidence-Grounded Attribution · Tamper-Proof Audit Logging
            </p>
          </div>
        </div>
      </main>

      {/* Page Footer */}
      <footer className="w-full max-w-xl mx-auto text-center space-y-1 pt-2">
        <p className="text-[11px] text-neutral-500">
          Smart India Hackathon 2026 · Problem Statement ID: 26189 · Section 63 BSA (2023) Compliant
        </p>
        <p className="text-[10px] text-neutral-400">
          Zero Citizen PII on Ledger · Cryptographic Integrity Verifications Active
        </p>
      </footer>
    </div>
  )
}
