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
  ArrowRight,
  Scale,
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
    <div className="h-screen max-h-screen flex flex-col justify-between bg-neutral-50 text-neutral-800 selection:bg-blue-100 selection:text-blue-900 overflow-y-auto lg:overflow-hidden">
      {/* Top Institutional Masthead Bar — Full Width, Consistent Application Typography */}
      <header className="w-full relative z-20 border-b border-neutral-200/90 bg-white px-4 sm:px-6 lg:px-8 py-2 sm:py-2.5 shadow-2xs shrink-0">
        <div className="w-full max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
              <Network className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-black tracking-tight text-neutral-900">NCRB Intelligence</span>
                <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200/80 px-1.5 py-0.5 rounded uppercase tracking-wider">
                  MHA Portal
                </span>
              </div>
              <p className="text-xs text-neutral-500 font-medium hidden sm:block">
                Ministry of Home Affairs · National Crime Records Bureau · Women Safety Division
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-semibold text-neutral-700">
              <Shield className="h-3.5 w-3.5 text-blue-600 shrink-0" />
              <span>Official Law Enforcement Portal · Authorized Access Only</span>
            </div>
            <div className="hidden md:inline-flex items-center gap-1.5 rounded-full border border-amber-200/80 bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800">
              <Scale className="h-3.5 w-3.5 text-amber-600 shrink-0" />
              <span>Sec. 63 BSA Compliant</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container — Centered Authentication Console */}
      <main className="w-full flex-1 min-h-0 max-w-lg mx-auto px-4 sm:px-6 py-2 sm:py-3 flex flex-col justify-center items-center relative z-10 my-auto">
        {/* Authentication Console Card — Clean Width & Consistent Typography */}
        <div 
          role="region" 
          aria-label="Officer Authentication Form" 
          className="w-full max-w-[420px] rounded-2xl border border-neutral-200/80 bg-white p-5 sm:p-6 shadow-[0_1px_3px_0_rgb(0_0_0_/_0.04),0_8px_24px_-4px_rgb(0_0_0_/_0.06)] space-y-3"
        >
          {/* Integrated Brand Emblem & Title */}
          <div className="text-center pb-2.5 border-b border-neutral-100 space-y-1">
            <div className="mx-auto inline-flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-xs ring-4 ring-blue-50">
              <Network className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-neutral-900">
                NEXUS
              </h1>
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-700">
                Investigative Network Intelligence Platform
              </p>
            </div>
            <p className="text-xs text-neutral-500">
              Officer Authentication Console
            </p>
          </div>

          {/* Security Notice Banner */}
          <div className="rounded-lg border border-neutral-200/80 bg-neutral-50/70 px-3 py-1.5 text-center shadow-2xs">
            <p className="text-xs font-medium text-neutral-600 flex items-center justify-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-neutral-400 shrink-0" />
              <span>Restricted Access · All Sessions Cryptographically Audited</span>
            </p>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div 
              role="alert" 
              className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-800 animate-in fade-in duration-150"
              data-testid="login-error-alert"
            >
              <AlertCircle className="h-3.5 w-3.5 text-red-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="font-bold block text-xs">Authentication Error:</span>
                <span className="text-xs leading-normal">{errorMessage}</span>
              </div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={(e) => handleSubmit(e)} className="space-y-2.5">
            <div>
              <label 
                htmlFor="officer-id-input" 
                className="block text-xs font-bold uppercase tracking-wider text-neutral-700 mb-1"
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
                  className="w-full h-9 sm:h-9.5 rounded-lg border border-neutral-300 bg-white pl-9 pr-3 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15 transition-[border-color,box-shadow] duration-150 shadow-2xs disabled:bg-neutral-100"
                  data-testid="officer-id-input"
                />
              </div>
            </div>

            <div>
              <label 
                htmlFor="password-input" 
                className="block text-xs font-bold uppercase tracking-wider text-neutral-700 mb-1"
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
                  className="w-full h-9 sm:h-9.5 rounded-lg border border-neutral-300 bg-white pl-9 pr-9 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15 transition-[border-color,box-shadow] duration-150 shadow-2xs disabled:bg-neutral-100"
                  data-testid="password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-2.5 text-neutral-400 hover:text-neutral-700 active:scale-90 transition-transform duration-100 cursor-pointer"
                  aria-label={showPassword ? 'Hide passcode' : 'Show passcode'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-9.5 sm:h-10 flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 active:scale-[0.98] text-white text-sm font-semibold shadow-xs transition-[transform,background-color,box-shadow] duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
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

          {/* Authorized Officer Fast-Select Duty Profiles */}
          <div className="border-t border-neutral-200/90 pt-2.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-700">
                Evaluation Workspace Access
              </span>
              <span className="text-xs text-neutral-500">
                Select profile to sign in
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {AUTHORIZED_OFFICERS.map((officer) => {
                const Icon = officer.icon
                return (
                  <button
                    key={officer.id}
                    type="button"
                    onClick={() => handleSelectOfficer(officer)}
                    disabled={isLoading}
                    className="group flex flex-col items-start p-2 rounded-lg border border-neutral-200 bg-neutral-50/70 hover:bg-blue-50/40 hover:border-blue-300 active:scale-[0.98] text-left transition-[background-color,border-color,transform,box-shadow] duration-150 ease-out cursor-pointer disabled:opacity-50 shadow-2xs"
                    data-testid={`demo-officer-${officer.role.toLowerCase()}`}
                    aria-label={`Authenticate as ${officer.name} (${officer.role})`}
                  >
                    <div className="flex items-center gap-1.5 w-full mb-0.5">
                      <div className="flex h-5.5 w-5.5 shrink-0 items-center justify-center rounded bg-white border border-neutral-200 text-neutral-600 group-hover:text-blue-600 group-hover:border-blue-200 shadow-2xs transition-colors duration-150">
                        <Icon className="h-3 w-3" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-bold text-neutral-900 group-hover:text-blue-900 truncate block transition-colors duration-150">
                          {officer.name}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between w-full text-xs text-neutral-500">
                      <span className="font-mono text-[11px] font-semibold text-neutral-700 bg-neutral-200/80 px-1 py-0.2 rounded border border-neutral-300/80">
                        {officer.badge}
                      </span>
                      <span className="text-blue-700 bg-blue-50 border border-blue-200/80 px-1.5 py-0.2 rounded text-[10px] font-bold uppercase tracking-wider">
                        {officer.role}
                      </span>
                    </div>
                    <p className="text-xs text-neutral-500 line-clamp-1 mt-0.5">
                      {officer.scope}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Card Footer Statutory Disclaimers */}
          <div className="border-t border-neutral-200/90 pt-2 text-center">
            <p className="text-xs text-neutral-500 font-medium">
              Deterministic Graph Analytics · Evidence-Grounded Attribution · Tamper-Proof Audit Logging
            </p>
          </div>
        </div>
      </main>

      {/* Page Footer — Full Width, Consistent Application Typography */}
      <footer className="w-full relative z-20 border-t border-neutral-200/90 bg-white px-4 sm:px-6 lg:px-8 py-2 text-xs text-neutral-500 shadow-2xs shrink-0">
        <div className="w-full max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-1">
          <p className="text-xs text-neutral-500">
            Smart India Hackathon 2026 · Problem Statement ID: 26189 · Ministry of Home Affairs (MHA)
          </p>
          <p className="text-xs text-neutral-400">
            Section 63 BSA (2023) Compliant · Zero Real Citizen PII · Tamper-Evident Ledger Provenance
          </p>
        </div>
      </footer>
    </div>
  )
}


