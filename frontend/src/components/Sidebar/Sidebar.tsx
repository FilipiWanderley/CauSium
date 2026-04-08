import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Lightbulb,
  ListTodo,
  Users,
  BarChart3,
  Settings,
  Cloud,
  FlaskConical,
  Activity,
  ShieldAlert,
  Building2,
  RefreshCw,
  Bell,
  Leaf,
  Landmark,
  Receipt,
  Boxes,
  FileSpreadsheet,
} from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'

type NavItem = {
  to: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  soon?: boolean
}

const CORE_NAV: NavItem[] = [
  { to: '/app/economics', icon: LayoutDashboard, label: 'Economics' },
  { to: '/app/economics/costs', icon: Receipt, label: 'Economics Costs', soon: true },
  { to: '/app/economics/usage', icon: BarChart3, label: 'Economics Usage', soon: true },
  { to: '/app/economics/skus', icon: Boxes, label: 'Economics SKUs', soon: true },
  { to: '/app/economics/reports', icon: FileSpreadsheet, label: 'Economics Reports', soon: true },
  { to: '/app/intel', icon: Lightbulb, label: 'PulseIntel' },
  { to: '/app/lab', icon: FlaskConical, label: 'PulseLab' },
  { to: '/app/notifications', icon: Bell, label: 'Notifications', soon: true },
  { to: '/app/gov', icon: Landmark, label: 'PulseGov', soon: true },
  { to: '/app/green', icon: Leaf, label: 'PulseGreen', soon: true },
  { to: '/app/initiatives', icon: ListTodo, label: 'Initiatives' },
  { to: '/app/risk-budgets', icon: ShieldAlert, label: 'Risk Budgets' },
  { to: '/app/change-events', icon: Activity, label: 'Change Events' },
  { to: '/app/executive', icon: BarChart3, label: 'Executive' },
]

export function Sidebar() {
  const { user } = useAuth()
  const isPlatformAdmin = user?.role === 'platform_admin'
  const isAdmin = user?.role === 'admin' || isPlatformAdmin

  return (
    <aside className="flex w-60 flex-col bg-gray-900 text-white">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-gray-700">
        <Cloud className="h-6 w-6 text-brand-500" />
        <span className="font-bold text-lg tracking-tight">StratoPulse</span>
      </div>
      <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
        {CORE_NAV.map(({ to, icon: Icon, label, soon }) => (
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
            <span className="flex-1 truncate">{label}</span>
            {soon && (
              <span className="rounded bg-gray-700 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-gray-300">
                Soon
              </span>
            )}
          </NavLink>
        ))}

        {isAdmin && (
          <>
            <div className="my-2 mx-3 border-t border-gray-700" />
            <NavLink
              to="/app/members"
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <Users className="h-4 w-4" />
              Members
            </NavLink>
            <NavLink
              to="/app/settings/team"
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <Settings className="h-4 w-4" />
              Settings Team
            </NavLink>
            <NavLink
              to="/app/settings/cloud"
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <Settings className="h-4 w-4" />
              Settings Cloud
            </NavLink>
            <NavLink
              to="/app/settings/security"
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <Settings className="h-4 w-4" />
              Settings Security
            </NavLink>
          </>
        )}

        <NavLink
          to="/app/settings"
          className={({ isActive }) =>
            clsx(
              'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
              isActive
                ? 'bg-brand-600 text-white'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            )
          }
        >
          <Settings className="h-4 w-4" />
          Settings
        </NavLink>

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
            <NavLink
              to="/app/platform/sync"
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <RefreshCw className="h-4 w-4" />
              Platform Sync
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
