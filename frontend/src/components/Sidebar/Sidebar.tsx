import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Lightbulb,
  ListTodo,
  BarChart3,
  Settings,
  Cloud,
  FlaskConical,
  Activity,
  ShieldAlert,
  Building2,
} from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'

const NAV = [
  { to: '/app/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/app/opportunities', icon: Lightbulb, label: 'Opportunities' },
  { to: '/app/initiatives', icon: ListTodo, label: 'Initiatives' },
  { to: '/app/experiments', icon: FlaskConical, label: 'Experiments' },
  { to: '/app/risk-budgets', icon: ShieldAlert, label: 'Risk Budgets' },
  { to: '/app/change-events', icon: Activity, label: 'Change Events' },
  { to: '/app/executive', icon: BarChart3, label: 'Executive' },
  { to: '/app/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
  const { user } = useAuth()
  const isPlatformAdmin = user?.role === 'platform_admin'

  return (
    <aside className="flex w-60 flex-col bg-gray-900 text-white">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-gray-700">
        <Cloud className="h-6 w-6 text-brand-500" />
        <span className="font-bold text-lg tracking-tight">StratoPulse</span>
      </div>
      <nav className="flex-1 py-4 space-y-1 px-2">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}

        {isPlatformAdmin && (
          <>
            <div className="my-2 mx-3 border-t border-gray-700" />
            <NavLink
              to="/app/platform/workspaces"
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <Building2 className="h-4 w-4" />
              Platform Workspaces
            </NavLink>
          </>
        )}
      </nav>
      <div className="px-5 py-4 border-t border-gray-700 text-xs text-gray-400">
        v0.1.0 · Azure-first MVP
      </div>
    </aside>
  )
}
