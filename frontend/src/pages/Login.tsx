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
    <div className="h-screen max-h-screen flex flex-col justify-between bg-neutral-50 text-neutral-800 selection:bg-blue-100 selection:text-blue-900 overflow-hidden">
      {/* Top Institutional Masthead Bar — Full Width, Compact */}
      <header className="w-full relative z-20 border-b border-neutral-200/90 bg-white px-3 sm:px-6 py-1.5 sm:py-2 shadow-2xs shrink-0">
        <div className="w-full max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-1.5">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 sm:h-7 sm:w-7 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
              <Network className="h-3.5 w-3.5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs sm:text-sm font-black tracking-tight text-neutral-900">NCRB Intelligence</span>
                <span className="text-[9px] font-bold text-blue-700 bg-blue-50 border border-blue-200/80 px-1 py-0.2 rounded uppercase tracking-wider">
                  MHA Portal
                </span>
              </div>
              <p className="text-[10px] text-neutral-500 font-medium hidden sm:block">
                Ministry of Home Affairs · National Crime Records Bureau · Women Safety Division
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-0.5 text-[10px] sm:text-[11px] font-semibold text-neutral-700">
              <Shield className="h-3 w-3 text-blue-600 shrink-0" />
              <span>Official Law Enforcement Portal · Authorized Access Only</span>
            </div>
            <div className="hidden md:inline-flex items-center gap-1 rounded-full border border-amber-200/80 bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800">
              <Scale className="h-3 w-3 text-amber-600 shrink-0" />
              <span>Sec. 63 BSA Compliant</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container — Centered Authentication Console, Strictly Fits Viewport Height */}
      <main className="w-full flex-1 min-h-0 max-w-[420px] mx-auto px-4 py-2 flex flex-col justify-center items-center relative z-10">
        {/* Authentication Console Card — Integrated Brand & Compact Fit */}
        <div 
          role="region" 
          aria-label="Officer Authentication Form" 
          className="w-full max-w-[400px] rounded-xl border border-neutral-200/80 bg-white p-3.5 sm:p-4 shadow-[0_1px_3px_0_rgb(0_0_0_/_0.04),0_8px_24px_-4px_rgb(0_0_0_/_0.06)] space-y-2"
        >
          {/* Integrated Brand Emblem & Title */}
          <div className="text-center pb-1.5 border-b border-neutral-100 space-y-0.5">
            <div className="mx-auto inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs ring-2 ring-blue-50">
              <Network className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-neutral-900 leading-tight">
                NEXUS
              </h1>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-700 leading-tight">
                Investigative Network Intelligence Platform
              </p>
            </div>
            <p className="text-[10px] text-neutral-500 leading-tight">
              Officer Authentication Console
            </p>
          </div>

          {/* Security Notice Banner */}
          <div className="rounded border border-neutral-200/80 bg-neutral-50/70 px-2.5 py-1 text-center shadow-2xs">
            <p className="text-[10px] font-medium text-neutral-600 flex items-center justify-center gap-1.5 leading-tight">
              <Lock className="h-3 w-3 text-neutral-400 shrink-0" />
              <span>Restricted Access · All Sessions Cryptographically Audited</span>
            </p>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div 
              role="alert" 
              className="flex items-start gap-1.5 rounded-lg border border-red-200 bg-red-50 p-2 text-[11px] text-red-800 animate-in fade-in duration-150"
              data-testid="login-error-alert"
            >
              <AlertCircle className="h-3 w-3 text-red-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="font-bold block text-[10px]">Authentication Error:</span>
                <span className="text-[10px] leading-tight">{errorMessage}</span>
              </div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={(e) => handleSubmit(e)} className="space-y-1.5">
            <div>
              <label 
                htmlFor="officer-id-input" 
                className="block text-[10px] font-bold uppercase tracking-wider text-neutral-700 mb-0.5"
              >
                Officer ID / Service Identifier
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2.5 text-neutral-400">
                  <User className="h-3.5 w-3.5" />
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
                  className="w-full h-8 rounded-md border border-neutral-300 bg-white pl-8 pr-2.5 text-xs text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600/20 transition-[border-color,box-shadow] duration-150 shadow-2xs disabled:bg-neutral-100"
                  data-testid="officer-id-input"
                />
              </div>
            </div>

            <div>
              <label 
                htmlFor="password-input" 
                className="block text-[10px] font-bold uppercase tracking-wider text-neutral-700 mb-0.5"
              >
                Security Passcode / Token
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2.5 text-neutral-400">
                  <KeyRound className="h-3.5 w-3.5" />
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
                  className="w-full h-8 rounded-md border border-neutral-300 bg-white pl-8 pr-8 text-xs text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600/20 transition-[border-color,box-shadow] duration-150 shadow-2xs disabled:bg-neutral-100"
                  data-testid="password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-2 text-neutral-400 hover:text-neutral-700 active:scale-90 transition-transform duration-100 cursor-pointer"
                  aria-label={showPassword ? 'Hide passcode' : 'Show passcode'}
                >
                  {showPassword ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-8 rounded-md bg-blue-600 hover:bg-blue-700 active:scale-[0.98] text-white text-xs font-semibold shadow-xs transition-[transform,background-color,box-shadow] duration-150 ease-out flex items-center justify-center gap-1.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-600 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
              data-testid="login-submit-button"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Intelligence Workspace</span>
                  <ArrowRight className="h-3 w-3" />
                </>
              )}
            </button>
          </form>

          {/* Authorized Officer Fast-Select Duty Profiles */}
          <div className="border-t border-neutral-200/90 pt-1.5 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-700">
                Evaluation Workspace Access
              </span>
              <span className="text-[9px] text-neutral-400">
                Select profile to sign in
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              {AUTHORIZED_OFFICERS.map((officer) => {
                const Icon = officer.icon
                return (
                  <button
                    key={officer.id}
                    type="button"
                    onClick={() => handleSelectOfficer(officer)}
                    disabled={isLoading}
                    className="group flex flex-col items-start p-1.5 rounded-lg border border-neutral-200 bg-neutral-50/70 hover:bg-blue-50/40 hover:border-blue-300 active:scale-[0.98] text-left transition-[background-color,border-color,transform,box-shadow] duration-150 ease-out cursor-pointer disabled:opacity-50 shadow-2xs"
                    data-testid={`demo-officer-${officer.role.toLowerCase()}`}
                    aria-label={`Authenticate as ${officer.name} (${officer.role})`}
                  >
                    <div className="flex items-center gap-1.5 w-full mb-0.5">
                      <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-white border border-neutral-200 text-neutral-600 group-hover:text-blue-600 group-hover:border-blue-200 shadow-2xs transition-colors duration-150">
                        <Icon className="h-2.5 w-2.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="text-[10px] font-bold text-neutral-900 group-hover:text-blue-900 truncate block transition-colors duration-150 leading-tight">
                          {officer.name}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between w-full text-[9px] text-neutral-500 leading-tight">
                      <span className="font-mono text-[8px] font-semibold text-neutral-700 bg-neutral-200/80 px-1 py-0.2 rounded border border-neutral-300/80">
                        {officer.badge}
                      </span>
                      <span className="text-blue-700 bg-blue-50 border border-blue-200/80 px-1 py-0.2 rounded text-[8px] font-bold uppercase tracking-wider">
                        {officer.role}
                      </span>
                    </div>
                    <p className="text-[8px] text-neutral-600 line-clamp-1 mt-0.5 leading-tight">
                      {officer.scope}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Card Footer Statutory Disclaimers */}
          <div className="border-t border-neutral-200/90 pt-1.5 text-center">
            <p className="text-[9px] text-neutral-400 font-medium leading-tight">
              Deterministic Graph Analytics · Evidence-Grounded Attribution · Tamper-Proof Audit Logging
            </p>
          </div>
        </div>
      </main>

      {/* Page Footer — Full Width, Compact */}
      <footer className="w-full relative z-20 border-t border-neutral-200/90 bg-white px-4 sm:px-6 py-1.5 text-[10px] text-neutral-500 shadow-2xs shrink-0">
        <div className="w-full max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-0.5">
          <p className="text-[10px] text-neutral-500">
            Smart India Hackathon 2026 · Problem Statement ID: 26189 · Ministry of Home Affairs (MHA)
          </p>
          <p className="text-[9px] text-neutral-400">
            Section 63 BSA (2023) Compliant · Zero Real Citizen PII · Tamper-Evident Ledger Provenance
          </p>
        </div>
      </footer>
    </div>
  )
}


