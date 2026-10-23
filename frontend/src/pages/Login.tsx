import { useRef, useState } from 'react'
import './Login.css'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import type { UserRole } from '@shared/contracts/api'
import { 
  Network, 
  ShieldCheck, 
  ShieldAlert, 
  UserCheck, 
  Shield, 
  User, 
  Eye, 
  EyeOff, 
  Loader2, 
  AlertCircle,
  KeyRound,
  ArrowRight,
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
    scope: 'Trace case evidence and connections',
    icon: UserCheck,
  },
  {
    id: 'KA-1002',
    name: 'SHO Sunita Sharma',
    rank: 'Station House Officer',
    badge: 'KA-1002',
    role: 'SHO',
    roleName: 'SHO / Intelligence Analyst',
    scope: 'Review network signals and action leads',
    icon: ShieldAlert,
  },
  {
    id: 'KA-1003',
    name: 'SP Vikram Hegde',
    rank: 'Superintendent of Police',
    badge: 'KA-1003',
    role: 'SP',
    roleName: 'Superintendent of Police (SP)',
    scope: 'Coordinate intelligence across districts',
    icon: ShieldCheck,
  },
  {
    id: 'KA-1000',
    name: 'Dir. Priya Mehta',
    rank: 'Director of Cyber Intelligence',
    badge: 'KA-1000',
    role: 'ADMIN',
    roleName: 'Forensic Governance Officer (Admin)',
    scope: 'Oversee operations and forensic governance',
    icon: Shield,
  },
]

export default function Login() {
  const { role, login, isAuthenticated } = useAuth()
  const location = useLocation()

  const submitting = useRef(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [selectedRole, setSelectedRole] = useState<UserRole | undefined>(undefined)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Redirect if already authenticated
  if (isAuthenticated && role) {
    const from = (location.state as { from?: { pathname?: string } })?.from?.pathname || '/intelligence'
    return <Navigate to={from} replace />
  }

  const handleSubmit = async (e?: React.FormEvent, overrideCreds?: { username: string; role?: UserRole }) => {
    if (e) e.preventDefault()
    if (submitting.current) return
    
    const targetUsername = (overrideCreds?.username || username).trim()
    let targetRole = overrideCreds?.role

    if (!targetUsername) {
      setErrorMessage('Please enter your Officer ID or Service Number.')
      return
    }

    // Auto-resolve known officer duty profile from badge ID if not explicitly specified
    if (!targetRole && targetUsername) {
      const u = targetUsername.toLowerCase()
      const matchingOfficer = AUTHORIZED_OFFICERS.find(
        (o) => o.badge.toLowerCase() === u ||
               o.id.toLowerCase() === u ||
               o.role.toLowerCase() === u
      )
      if (matchingOfficer) {
        targetRole = matchingOfficer.role
      } else if (u.includes('sho') || u.includes('1002') || u.includes('analyst')) {
        targetRole = 'SHO'
      } else if (u.includes('sp') || u.includes('1003') || u.includes('supervisor')) {
        targetRole = 'SP'
      } else if (u.includes('admin') || u.includes('1000')) {
        targetRole = 'ADMIN'
      } else if (u.includes('io') || u.includes('1001') || u.includes('investigator') || u.startsWith('ka-')) {
        targetRole = 'IO'
      }
    }

    submitting.current = true
    setIsLoading(true)
    setErrorMessage(null)

    try {
      await login({
        username: targetUsername,
        password: overrideCreds ? 'nexus-demo-passcode' : password,
        role: targetRole,
      })
      // The authenticated render above redirects after session state commits.
      // Navigating here can race the protected shell's authentication check.
    } catch (err: unknown) {
      const msg = (err && typeof err === 'object' && 'message' in err ? String(err.message) : '') || 'Authentication failed. Please verify your officer credentials.'
      setErrorMessage(`${msg} Please retry sign-in.`)
    } finally {
      submitting.current = false
      setIsLoading(false)
    }
  }

  const handleSelectOfficer = (officer: OfficerProfile) => {
    if (submitting.current) return
    setUsername(officer.badge)
    setSelectedRole(officer.role)
    setPassword('')
    setErrorMessage(null)
    handleSubmit(undefined, { username: officer.badge, role: officer.role })
  }

  return (
    <div className="nexus-login min-h-screen min-h-[100dvh] flex flex-col justify-center items-center bg-neutral-50 text-neutral-800 selection:bg-blue-100 selection:text-blue-900 px-3.5 py-4 sm:p-6 overflow-y-auto">
      <aside className="login-identity" aria-label="NEXUS intelligence workspace">
        <div className="login-wordmark"><Network aria-hidden="true" /><span>NEXUS</span><span className="login-edition">INTELLIGENCE WORKSPACE</span></div>
        <div className="login-identity-content">
          <p className="login-eyebrow">OBSERVE / CONNECT / VERIFY</p>
          <h2>See the connections.<br /><span>Ground every finding.</span></h2>
          <svg className="login-topology" viewBox="0 0 560 250" fill="none" aria-hidden="true">
            <g stroke="currentColor" strokeWidth="1"><path d="M30 180 115 75 230 125 330 40 430 95 525 35M30 180 170 215 230 125 355 205 430 95 530 200M115 75 170 215M230 125 430 95M355 205 530 200" /><path d="M0 125H560M0 65H560M0 185H560M100 0V250M220 0V250M340 0V250M460 0V250" opacity=".15" /></g>
            {[[30,180],[115,75],[230,125],[330,40],[430,95],[525,35],[170,215],[355,205],[530,200]].map(([cx,cy], i) => <g key={i}><circle cx={cx} cy={cy} r="12" fill="#14263d" /><circle cx={cx} cy={cy} r={i === 2 ? 6 : 4} fill={i === 2 ? '#76a8ff' : '#a5b4c6'} /></g>)}
            <circle cx="230" cy="125" r="23" stroke="#76a8ff" strokeDasharray="3 5" />
          </svg>
          <p className="login-caption">Evidence-grounded network intelligence</p>
        </div>
        <div className="login-identity-footer"><ShieldCheck size={16} aria-hidden="true" /> Authorized access ? Synthetic evaluation workspace</div>
      </aside>
      {/* Main Container — Purely Centered Authentication Console */}
      <main className="login-access w-full">
        {/* Authentication Console Card */}
        <div 
          role="region" 
          aria-label="Officer Authentication Form" 
          className="login-console w-full rounded-xl sm:rounded-2xl border border-neutral-200/80 bg-white p-4 sm:p-5.5 shadow-sm sm:shadow-[0_1px_3px_0_rgb(0_0_0_/_0.04),0_8px_24px_-4px_rgb(0_0_0_/_0.06)] space-y-3 sm:space-y-3.5"
        >
          {/* Integrated Brand Emblem & Title */}
          <div className="login-console-heading text-center pb-2.5 border-b border-neutral-100 space-y-1">
            <div className="mx-auto inline-flex h-9.5 w-9.5 sm:h-10 sm:w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-xs ring-4 ring-blue-50">
              <Network className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg sm:text-xl font-bold tracking-tight text-neutral-900">
                NEXUS
              </h1>
              <p className="text-[11px] sm:text-xs font-semibold uppercase tracking-wider text-blue-700">
                Investigative Network Intelligence Platform
              </p>
            </div>
            <p className="text-xs text-neutral-500">
              Officer Authentication Console
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

          {isLoading && selectedRole && (
            <div role="status" className="flex items-center gap-2 rounded-lg bg-blue-50 p-3 text-sm font-semibold text-blue-900">
              <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
              Opening {selectedRole} Investigation Workspace...
            </div>
          )}
          {/* Authorized Officer Duty Profiles — Dropdown on Mobile, Rich Cards on Desktop */}
          <div className="border-t border-neutral-200/90 pt-2.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span
                id="evaluation-profile-label"
                className="text-xs font-bold uppercase tracking-wider text-neutral-700 cursor-pointer sm:cursor-default"
              >
                Choose your workspace
              </span>
              <span className="text-[11px] text-neutral-500">
                <span className="inline sm:hidden">Demo Accounts</span>
                <span className="hidden sm:inline">Select an officer to enter</span>
              </span>
            </div>

            {/* Shared keyboard-accessible choices at every viewport */}
            <div role="group" aria-labelledby="evaluation-profile-label" className="login-officers grid gap-2">
              {AUTHORIZED_OFFICERS.map((officer) => {
                const Icon = officer.icon
                return (
                  <button
                    key={officer.id}
                    type="button"
                    onClick={() => handleSelectOfficer(officer)}
                    disabled={isLoading}
                    aria-pressed={selectedRole === officer.role}
                    className="login-officer group flex flex-col items-start p-2 rounded-lg border border-neutral-200 bg-neutral-50/70 hover:bg-blue-50/40 hover:border-blue-300 active:scale-[0.98] text-left transition-[background-color,border-color,transform,box-shadow] duration-150 ease-out cursor-pointer disabled:opacity-50 shadow-2xs focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                    data-testid={`demo-officer-${officer.role.toLowerCase()}`}
                    aria-label={`Authenticate as ${officer.name} (${officer.role})`}
                  >
                    <div className="flex items-center gap-1.5 w-full mb-0.5">
                      <div className="flex h-5.5 w-5.5 shrink-0 items-center justify-center rounded bg-white border border-neutral-200 text-neutral-600 group-hover:text-blue-600 group-hover:border-blue-200 shadow-2xs transition-colors duration-150">
                        <Icon className="h-3 w-3" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-bold text-neutral-900 group-hover:text-blue-900 block transition-colors duration-150">
                          {officer.name}
                        </span><span className="login-rank">{officer.rank}</span>
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
                    <p className="text-xs text-neutral-500 mt-0.5">
                      {officer.scope}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>

          <details className="border-t border-neutral-200 pt-3">
            <summary className="cursor-pointer text-sm font-semibold focus-visible:outline-blue-600">Sign in with officer credentials</summary>
          {/* Login Form */}
          <form onSubmit={(e) => handleSubmit(e)} className="space-y-2.5 sm:space-y-3">
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
                  <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
                  <span>{selectedRole ? `Opening ${selectedRole} Investigation Workspace...` : 'Verifying Credentials...'}</span>
                </>
              ) : (
                <>
                  <span>Sign In to Intelligence Workspace</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          </details>

        </div>
      </main>
    </div>
  )
}


