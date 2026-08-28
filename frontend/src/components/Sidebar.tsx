import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { 
  Network, 
  Users, 
  Layers, 
  Clock, 
  FileText, 
  MessageSquareCode, 
  ShieldCheck, 
  Settings, 
  LogOut,
  LayoutDashboard,
  GitMerge,
  Inbox,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { role, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('nexus-sidebar-collapsed') === 'true' } catch { return false }
  })

  useEffect(() => {
    try {
      localStorage.setItem('nexus-sidebar-collapsed', String(collapsed))
      document.documentElement.setAttribute('data-sidebar-collapsed', String(collapsed))
    } catch {}
  }, [collapsed])

  // Sync initial state to attribute
  useEffect(() => {
    document.documentElement.setAttribute('data-sidebar-collapsed', String(collapsed))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const navItems = [
    {
      name: 'Network Explorer',
      to: '/network',
      icon: Network,
      roles: ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
    },
    {
      name: 'Entity Fusion (Workbench)',
      to: '/fusion',
      icon: GitMerge,
      roles: ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
    },
    {
      name: 'Lead Inbox',
      to: '/leads',
      icon: Inbox,
      roles: ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
    },
    {
      name: 'Investigation Worklist',
      to: '/worklist',
      icon: LayoutDashboard,
      roles: ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
    },
    {
      name: 'Entity Search & Query',
      to: '/entities',
      icon: Users,
      roles: ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
    },
    {
      name: 'Timeline & Events',
      to: '/timeline',
      icon: Clock,
      roles: ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
    },
    {
      name: 'Evidence & Provenance',
      to: '/evidence',
      icon: FileText,
      roles: ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
    },
    {
      name: 'Investigator Copilot',
      to: '/copilot',
      icon: MessageSquareCode,
      roles: ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
    },
    {
      name: 'Audit Trail',
      to: '/audit',
      icon: ShieldCheck,
      roles: ['SUPERVISOR', 'ADMIN', 'SHO', 'SP']
    },
    {
      name: 'Patterns & Communities',
      to: '/patterns',
      icon: Layers,
      roles: ['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN', 'IO', 'SHO', 'SP']
    }
  ]

  const filteredNavItems = navItems.filter(item => !role || item.roles.includes(role))

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40 bg-neutral-900/50 lg:hidden transition-opacity duration-normal"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex flex-col border-r border-neutral-200 bg-white text-neutral-900 shadow-xs transition-all duration-200 lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } ${
          collapsed ? 'w-14' : 'w-sidebar'
        }`}
      >
        {/* Brand Wordmark */}
        <div className={`flex h-16 items-center border-b border-neutral-200 gap-3 ${collapsed ? 'justify-center px-2' : 'px-6'}`}>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-600 shadow-md">
            <Network className="h-5 w-5 text-white" />
          </div>
          {!collapsed && (
            <div>
              <span className="text-lg font-extrabold tracking-tight text-neutral-900">NEXUS</span>
              <div className="text-[10px] font-bold text-blue-700 uppercase tracking-wider">Network Intelligence</div>
            </div>
          )}
        </div>

        {/* User Role Badge */}
        {!collapsed && (
          <div className="px-6 py-3.5 border-b border-neutral-200 bg-neutral-50">
            <div className="flex items-center space-x-3">
              <div className="h-8 w-8 rounded-full bg-blue-100 border border-blue-300 flex items-center justify-center font-bold text-blue-900 text-xs">
                {role ? role.substring(0, 2) : 'NV'}
              </div>
              <div>
                <div className="text-xs font-bold text-neutral-900">{role || 'Investigator'}</div>
                <div className="text-[11px] text-neutral-500 font-medium">
                  {role === 'SP' || role === 'SUPERVISOR' ? 'Supervisor / SP' : role === 'ANALYST' ? 'Intelligence Analyst' : 'Investigating Officer'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Primary Navigation */}
        <nav className={`flex-1 space-y-1 py-4 overflow-y-auto ${collapsed ? 'px-1' : 'px-3'}`}>
          {filteredNavItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.name}
                to={item.to}
                onClick={onClose}
                title={collapsed ? item.name : undefined}
                className={({ isActive }) => `
                  flex items-center rounded-lg text-sm font-medium transition-all
                  ${collapsed ? 'justify-center px-2 py-2.5' : 'px-3 py-2.5'}
                  ${isActive 
                    ? 'bg-blue-600 text-white font-bold shadow-sm' 
                    : 'text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900'
                  }
                `}
              >
                <Icon className={`h-4 w-4 shrink-0 ${!collapsed ? 'mr-3' : ''}`} />
                {!collapsed && item.name}
              </NavLink>
            )
          })}
        </nav>

        {/* Secondary Navigation, Collapse Toggle & Logout */}
        <div className="border-t border-neutral-200 p-2 space-y-1">
          {/* Desktop collapse toggle */}
          <button
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="hidden lg:flex w-full items-center justify-center rounded-lg px-2 py-2 text-xs font-medium text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-all"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            {!collapsed && <span className="ml-2">Collapse</span>}
          </button>
          {!collapsed && (
            <NavLink
              to="/settings"
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center px-3 py-2 rounded-lg text-xs font-medium transition-all
                ${isActive ? 'bg-neutral-100 text-neutral-900 font-bold' : 'text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900'}`
              }
            >
              <Settings className="mr-3 h-4 w-4" /> Settings
            </NavLink>
          )}
          <button
            onClick={() => { logout(); onClose() }}
            title={collapsed ? 'Sign Out' : undefined}
            className={`flex w-full items-center rounded-lg text-xs font-semibold text-red-700 hover:bg-red-50 hover:text-red-800 transition-all ${collapsed ? 'justify-center px-2 py-2' : 'px-3 py-2'}`}
          >
            <LogOut className={`h-4 w-4 ${!collapsed ? 'mr-3' : ''}`} />
            {!collapsed && 'Sign Out'}
          </button>
        </div>
      </aside>
    </>
  )
}
