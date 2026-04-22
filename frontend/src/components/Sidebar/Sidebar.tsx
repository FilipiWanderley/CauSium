import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
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
  Siren,
  Receipt,
  Boxes,
  FileSpreadsheet,
  Cpu,
} from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'
import type { Translations } from '../../locales/en'
import { notificationsApi } from '../../api/notifications'

type NavItem = {
  to: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  soon?: boolean
  end?: boolean
  badge?: number
}

function getCoreNav(nav: Translations['nav']): NavItem[] {
  return [
    { to: '/app/economics', icon: LayoutDashboard, label: nav.economics },
    { to: '/app/economics/costs', icon: Receipt, label: nav.economicsCosts },
    { to: '/app/economics/usage', icon: BarChart3, label: nav.economicsUsage },
    { to: '/app/economics/skus', icon: Boxes, label: nav.economicsSkus },
    { to: '/app/economics/reports', icon: FileSpreadsheet, label: nav.economicsReports },
    { to: '/app/intel', icon: Lightbulb, label: nav.opportunities },
    { to: '/app/lab', icon: FlaskConical, label: nav.experiments },
    { to: '/app/initiatives', icon: ListTodo, label: nav.initiatives },
    { to: '/app/risk-budgets', icon: ShieldAlert, label: nav.riskBudgets },
    { to: '/app/change-events', icon: Activity, label: nav.changeEvents },
    { to: '/app/executive', icon: BarChart3, label: nav.executive },
    { to: '/app/gov', icon: Landmark, label: nav.gov },
    { to: '/app/green', icon: Leaf, label: nav.green },
    { to: '/app/notifications', icon: Bell, label: nav.notifications },
  ]
}

const NAV_LINK_CLASS = 'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors'
const ACTIVE_CLASS = 'bg-brand-600 text-white'
const INACTIVE_CLASS = 'text-gray-300 hover:bg-gray-800 hover:text-white'

function SideNavLink({ to, icon: Icon, label, soon, badge }: NavItem) {
  const { t } = useI18n()
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        clsx(NAV_LINK_CLASS, isActive ? ACTIVE_CLASS : INACTIVE_CLASS)
      }
    >
      <Icon className="h-4 w-4" />
      <span className="flex-1 truncate">{label}</span>
      {typeof badge === 'number' && badge > 0 && (
        <span className="rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
      {soon && (
        <span className="rounded bg-gray-700 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-gray-300">
          {t.nav.soon}
        </span>
      )}
    </NavLink>
  )
}

export function Sidebar() {
  const { user } = useAuth()
  const { t } = useI18n()
  const isPlatformAdmin = user?.role === 'platform_admin'
  const isAdmin = user?.role === 'admin' || isPlatformAdmin
  const coreNav = getCoreNav(t.nav)
  const { data: unreadCount } = useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => notificationsApi.getUnreadCount(),
    enabled: !!user,
    refetchInterval: 30_000,
  })
  const unread = unreadCount?.unread ?? 0

  return (
    <aside className="flex w-60 flex-col bg-gray-900 text-white">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-gray-700">
        <Cpu className="h-6 w-6 text-white" strokeWidth={1.5} />
        <span className="text-xs font-semibold uppercase tracking-[0.15em] text-white">CauSium</span>
      </div>
      <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
        {coreNav.map((item) => (
          <SideNavLink key={item.to} {...item} badge={item.to === '/app/notifications' ? unread : undefined} />
        ))}

        {isAdmin && (
          <>
            <div className="my-2 mx-3 border-t border-gray-700" />
            <SideNavLink to="/app/cloud" icon={Cloud} label={t.nav.settingsCloud} />
            <SideNavLink to="/app/members" icon={Users} label={t.nav.members} />
            <SideNavLink to="/app/settings/team" icon={Settings} label={t.nav.settingsTeam} />
            <SideNavLink to="/app/settings/security" icon={Settings} label={t.nav.settingsSecurity} />
          </>
        )}

        <SideNavLink to="/app/settings" icon={Settings} label={t.nav.settings} />

        {isPlatformAdmin && (
          <>
            <div className="my-2 mx-3 border-t border-gray-700" />
            <SideNavLink to="/app/platform/workspaces" icon={Building2} label={t.nav.platformWorkspaces} />
            <SideNavLink to="/app/platform/sync" icon={RefreshCw} label={t.nav.platformSync} />
            <SideNavLink to="/app/platform/slo" icon={Siren} label={t.nav.platformSlo} />
          </>
        )}
      </nav>
      <div className="px-5 py-4 border-t border-gray-700 text-xs text-gray-400">
        v0.1.0 · Azure-first MVP
      </div>
    </aside>
  )
}
