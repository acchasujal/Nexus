import { NavLink } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { 
  Clock, 
  AlertTriangle, 
  BarChart3, 
  MessageSquareCode, 
  Settings, 
  LogOut,
  LayoutDashboard
} from 'lucide-react'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { role, logout } = useAuth()

  const navItems = [
    {
      name: 'Worklist',
      to: '/worklist',
      icon: LayoutDashboard,
      roles: ['IO', 'SHO']
    },
    {
      name: 'Escalation Queue',
      to: '/escalations',
      icon: AlertTriangle,
      roles: ['SHO', 'SP']
    },
    {
      name: 'District Rollup',
      to: '/rollup',
      icon: BarChart3,
      roles: ['SP']
    },
    {
      name: 'Patterns & Trends',
      to: '/patterns',
      icon: BarChart3,
      roles: ['IO', 'SHO', 'SP']
    },
    {
      name: 'Copilot',
      to: '/copilot',
      icon: MessageSquareCode,
      roles: ['IO', 'SHO', 'SP']
    }
  ]

  // Filter navigation by role permission
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
        className={`fixed inset-y-0 left-0 z-50 flex w-sidebar flex-col border-r border-neutral-200 bg-neutral-900 text-neutral-100 transition-transform duration-normal lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Wordmark */}
        <div className="flex h-16 items-center border-b border-neutral-800 px-6">
          <Clock className="mr-3 h-6 w-6 text-status-info" />
          <span className="text-h2 font-bold tracking-tight text-neutral-50">CaseClock</span>
        </div>

        {/* User Role Badge */}
        <div className="px-6 py-4 border-b border-neutral-800">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-radius-full bg-neutral-800 flex items-center justify-center font-bold text-status-info text-small">
              {role ? role.substring(0, 2) : 'U'}
            </div>
            <div>
              <div className="text-small font-semibold text-neutral-200">{role || 'Guest'}</div>
              <div className="text-caption text-neutral-400">
                {role === 'SP' ? 'Superintendent' : role === 'SHO' ? 'Station Head Officer' : 'Investigating Officer'}
              </div>
            </div>
          </div>
        </div>

        {/* Primary Navigation */}
        <nav className="flex-1 space-y-1 px-4 py-6 overflow-y-auto">
          {filteredNavItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.name}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex min-h-11 items-center px-4 py-2 text-body rounded-radius-md transition-colors duration-fast ${
                    isActive
                      ? 'bg-neutral-800 text-neutral-50 font-medium'
                      : 'text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200'
                  }`
                }
              >
                <Icon className="mr-3 h-5 w-5" />
                {item.name}
              </NavLink>
            )
          })}
        </nav>

        {/* Footer Area */}
        <div className="border-t border-neutral-800 p-4 space-y-1">
          <NavLink
            to="/settings"
            onClick={onClose}
            className={({ isActive }) =>
              `flex min-h-11 items-center px-4 py-2 text-body rounded-radius-md transition-colors duration-fast ${
                isActive
                  ? 'bg-neutral-800 text-neutral-50 font-medium'
                  : 'text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200'
              }`
            }
          >
            <Settings className="mr-3 h-5 w-5" />
            Settings
          </NavLink>
          <button
            onClick={logout}
            className="flex min-h-11 w-full items-center px-4 py-2 text-body text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200 rounded-radius-md transition-colors duration-fast focus-visible:ring-2 focus-visible:ring-status-info"
          >
            <LogOut className="mr-3 h-5 w-5" />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  )
}
