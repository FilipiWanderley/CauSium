import { NavLink, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useRef, useState, useEffect } from 'react'
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
  ClipboardCheck,
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'
import type { Translations } from '../../locales/en'
import { notificationsApi } from '../../api/notifications'
import { preloadRoute } from '../../routes/lazyPages'
import { featureFlags } from '../../featureFlags'
import { usePersistentBoolean } from '../../hooks/usePersistentBoolean'

type NavItem = {
  to: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  end?: boolean
  badge?: number
  hidden?: boolean
}

type SidebarProps = {
  onNavigate?: () => void
}

type NavGroup = {
  id: 'economics' | 'optimization' | 'governance' | 'platform'
  label: string
  items: NavItem[]
}

const NAV_LINK_CLASS = 'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors'
const ACTIVE_CLASS = 'bg-brand-600 text-white'
const INACTIVE_CLASS = 'text-gray-300 hover:bg-gray-800 hover:text-white'
const ENTERPRISE_NAV_LINK_CLASS =
  'flex items-center gap-3 rounded-xl px-3 py-2 text-[13px] font-medium transition-all duration-150'
const ENTERPRISE_ACTIVE_CLASS = 'bg-slate-800 text-white shadow-sm ring-1 ring-slate-700/80'
const ENTERPRISE_INACTIVE_CLASS = 'text-slate-300 hover:bg-slate-800/80 hover:text-white'

function pathMatches(pathname: string, to: string) {
  return pathname === to || pathname.startsWith(`${to}/`)
}

function getLegacyNav(nav: Translations['nav']): NavItem[] {
  return [
    { to: '/app/economics', icon: LayoutDashboard, label: nav.economics },
    { to: '/app/economics/costs', icon: Receipt, label: nav.economicsCosts },
    { to: '/app/economics/usage', icon: BarChart3, label: nav.economicsUsage },
    { to: '/app/economics/skus', icon: Boxes, label: nav.economicsSkus },
    { to: '/app/economics/reports', icon: FileSpreadsheet, label: nav.economicsReports },
    { to: '/app/intel', icon: Lightbulb, label: nav.opportunities },
    { to: '/app/optimization-plan', icon: ListTodo, label: nav.optimizationPlan },
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

function getEnterpriseGroups(
  nav: Translations['nav'],
  isAdmin: boolean,
  isPlatformAdmin: boolean,
): NavGroup[] {
  return [
    {
      id: 'economics',
      label: nav.sectionEconomics,
      items: [
        { to: '/app/economics', icon: LayoutDashboard, label: nav.economics },
        { to: '/app/economics/costs', icon: Receipt, label: nav.economicsCosts },
        { to: '/app/economics/usage', icon: BarChart3, label: nav.economicsUsage },
        { to: '/app/economics/skus', icon: Boxes, label: nav.economicsSkus },
        { to: '/app/economics/reports', icon: FileSpreadsheet, label: nav.economicsReports },
      ],
    },
    {
      id: 'optimization',
      label: nav.sectionOptimization,
      items: [
        { to: '/app/intel', icon: Lightbulb, label: nav.opportunities },
        { to: '/app/optimization-plan', icon: ListTodo, label: nav.optimizationPlan },
        { to: '/app/lab', icon: FlaskConical, label: nav.experiments },
        { to: '/app/initiatives', icon: ListTodo, label: nav.initiatives },
      ],
    },
    {
      id: 'governance',
      label: nav.sectionGovernance,
      items: [
        { to: '/app/risk-budgets', icon: ShieldAlert, label: nav.riskBudgets },
        { to: '/app/change-events', icon: Activity, label: nav.changeEvents },
        { to: '/app/executive', icon: BarChart3, label: nav.executive },
        { to: '/app/gov', icon: Landmark, label: nav.gov },
        { to: '/app/green', icon: Leaf, label: nav.green },
      ],
    },
    {
      id: 'platform',
      label: nav.sectionPlatform,
      items: [
        { to: '/app/notifications', icon: Bell, label: nav.notifications },
        { to: '/app/cloud', icon: Cloud, label: nav.settingsCloud, hidden: !isAdmin },
        { to: '/app/members', icon: Users, label: nav.members, hidden: !isAdmin },
        { to: '/app/settings/team', icon: Settings, label: nav.settingsTeam, hidden: !isAdmin },
        { to: '/app/settings/security', icon: Settings, label: nav.settingsSecurity, hidden: !isAdmin },
        { to: '/app/settings', icon: Settings, label: nav.settings },
        { to: '/app/admin/reconciliation', icon: ClipboardCheck, label: nav.adminReconciliation, hidden: !isPlatformAdmin },
        { to: '/app/platform/workspaces', icon: Building2, label: nav.platformWorkspaces, hidden: !isPlatformAdmin },
        { to: '/app/platform/sync', icon: RefreshCw, label: nav.platformSync, hidden: !isPlatformAdmin },
        { to: '/app/platform/slo', icon: Siren, label: nav.platformSlo, hidden: !isPlatformAdmin },
      ],
    },
  ]
}

function SideNavLink({
  to,
  icon: Icon,
  label,
  badge,
  end,
  onNavigate,
  enterprise,
}: NavItem & { onNavigate?: () => void; enterprise?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end ?? true}
      onClick={onNavigate}
      onMouseEnter={() => preloadRoute(to)}
      onFocus={() => preloadRoute(to)}
      onPointerDown={() => preloadRoute(to)}
      className={({ isActive }) =>
        clsx(
          enterprise ? ENTERPRISE_NAV_LINK_CLASS : NAV_LINK_CLASS,
          isActive
            ? enterprise
              ? ENTERPRISE_ACTIVE_CLASS
              : ACTIVE_CLASS
            : enterprise
              ? ENTERPRISE_INACTIVE_CLASS
              : INACTIVE_CLASS,
        )
      }
    >
      <Icon className={clsx('h-4 w-4', enterprise && 'shrink-0')} />
      <span className="flex-1 truncate">{label}</span>
      {typeof badge === 'number' && badge > 0 && (
        <span
          className={clsx(
            'rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white',
            enterprise && 'bg-red-500/90',
          )}
        >
          {badge > 99 ? '99+' : badge}
        </span>
      )}
    </NavLink>
  )
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const { user } = useAuth()
  const location = useLocation()
  const { t } = useI18n()
  const isPlatformAdmin = user?.role === 'platform_admin'
  const isAdmin = user?.role === 'admin' || isPlatformAdmin
  const legacyNav = getLegacyNav(t.nav)
  const enterpriseGroups = getEnterpriseGroups(t.nav, isAdmin, isPlatformAdmin)
  const { data: unreadCount } = useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => notificationsApi.getUnreadCount(),
    enabled: !!user,
    refetchInterval: 30_000,
  })
  const unread = unreadCount?.unread ?? 0

  const enterpriseShellEnabled = featureFlags.enterpriseShell
  const [sidebarDense, setSidebarDense] = usePersistentBoolean('enterprise-shell:sidebar:dense', true)
  const [economicsOpen, setEconomicsOpen] = usePersistentBoolean('enterprise-shell:group:economics', true)
  const [optimizationOpen, setOptimizationOpen] = usePersistentBoolean('enterprise-shell:group:optimization', true)
  const [governanceOpen, setGovernanceOpen] = usePersistentBoolean('enterprise-shell:group:governance', true)
  const [platformOpen, setPlatformOpen] = usePersistentBoolean('enterprise-shell:group:platform', true)
  const navRef = useRef<HTMLDivElement>(null)
  const [showTopFade, setShowTopFade] = useState(false)
  const [showBottomFade, setShowBottomFade] = useState(false)

  useEffect(() => {
    const el = navRef.current
    if (!el) return
    const update = () => {
      setShowTopFade(el.scrollTop > 8)
      setShowBottomFade(el.scrollTop + el.clientHeight < el.scrollHeight - 8)
    }
    update()
    el.addEventListener('scroll', update, { passive: true })
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => {
      el.removeEventListener('scroll', update)
      ro.disconnect()
    }
  }, [])

  const groupState = {
    economics: [economicsOpen, setEconomicsOpen] as const,
    optimization: [optimizationOpen, setOptimizationOpen] as const,
    governance: [governanceOpen, setGovernanceOpen] as const,
    platform: [platformOpen, setPlatformOpen] as const,
  }

  return (
    <aside
      className={clsx(
        'flex w-60 flex-col bg-gray-900 text-white',
        enterpriseShellEnabled && 'w-72 border-r border-slate-800 bg-slate-950/95 text-slate-100',
      )}
    >
      <div
        className={clsx(
          'flex items-center gap-2 border-b border-gray-700 px-5 py-5',
          enterpriseShellEnabled && 'justify-between border-slate-800 px-4 py-4',
        )}
      >
        <div className="flex items-center gap-3">
          <div className={clsx('rounded-xl bg-white/5 p-2', enterpriseShellEnabled && 'border border-slate-800 bg-slate-900')}>
            <Cpu className="h-5 w-5 text-white" strokeWidth={1.5} />
          </div>
          <div className="min-w-0">
            <span className="block text-xs font-semibold uppercase tracking-[0.15em] text-white">CauSium</span>
            {enterpriseShellEnabled && (
              <span className="block truncate text-[11px] text-slate-400">{t.header.operationalConsole}</span>
            )}
          </div>
        </div>
        {enterpriseShellEnabled && (
          <button
            type="button"
            onClick={() => setSidebarDense((value) => !value)}
            className="hidden rounded-lg border border-slate-800 bg-slate-900 p-2 text-slate-400 transition-colors hover:border-slate-700 hover:text-white lg:inline-flex"
            aria-label={sidebarDense ? t.header.compactDensity : t.header.comfortDensity}
            title={sidebarDense ? t.header.compactDensity : t.header.comfortDensity}
          >
            {sidebarDense ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
          </button>
        )}
      </div>

      <div className="relative flex-1 overflow-hidden">
        <div
          className={clsx(
            'pointer-events-none absolute inset-x-0 top-0 z-10 h-8 bg-gradient-to-b transition-opacity duration-200',
            enterpriseShellEnabled ? 'from-slate-950 to-transparent' : 'from-gray-900 to-transparent',
            showTopFade ? 'opacity-100' : 'opacity-0',
          )}
        />

        <div
          ref={navRef}
          className={clsx(
            'h-full overflow-y-auto space-y-1 px-2 py-4 scrollbar-dark',
            enterpriseShellEnabled && (sidebarDense ? 'px-3 py-3' : 'px-3 py-4'),
          )}
        >
          {!enterpriseShellEnabled &&
            legacyNav.map((item) => (
              <SideNavLink
                key={item.to}
                {...item}
                onNavigate={onNavigate}
                badge={item.to === '/app/notifications' ? unread : undefined}
              />
            ))}

          {!enterpriseShellEnabled && isAdmin && (
            <>
              <div className="mx-3 my-2 border-t border-gray-700" />
              <SideNavLink to="/app/cloud" icon={Cloud} label={t.nav.settingsCloud} onNavigate={onNavigate} />
              <SideNavLink to="/app/members" icon={Users} label={t.nav.members} onNavigate={onNavigate} />
              <SideNavLink to="/app/settings/team" icon={Settings} label={t.nav.settingsTeam} onNavigate={onNavigate} />
              <SideNavLink to="/app/settings/security" icon={Settings} label={t.nav.settingsSecurity} onNavigate={onNavigate} />
            </>
          )}

          {!enterpriseShellEnabled && (
            <SideNavLink to="/app/settings" icon={Settings} label={t.nav.settings} onNavigate={onNavigate} />
          )}

          {!enterpriseShellEnabled && isPlatformAdmin && (
            <>
              <div className="mx-3 my-2 border-t border-gray-700" />
              <SideNavLink to="/app/admin/reconciliation" icon={ClipboardCheck} label={t.nav.adminReconciliation} onNavigate={onNavigate} />
              <SideNavLink
                to="/app/platform/workspaces"
                icon={Building2}
                label={t.nav.platformWorkspaces}
                onNavigate={onNavigate}
              />
              <SideNavLink to="/app/platform/sync" icon={RefreshCw} label={t.nav.platformSync} onNavigate={onNavigate} />
              <SideNavLink to="/app/platform/slo" icon={Siren} label={t.nav.platformSlo} onNavigate={onNavigate} />
            </>
          )}

          {enterpriseShellEnabled &&
            enterpriseGroups.map((group) => {
              const [open, setOpen] = groupState[group.id]
              const visibleItems = group.items.filter((item) => !item.hidden)
              const hasActiveItem = visibleItems.some((item) => pathMatches(location.pathname, item.to))
              const expanded = open || hasActiveItem

              return (
                <section
                  key={group.id}
                  className={clsx(
                    'rounded-2xl border border-transparent px-1 py-1',
                    hasActiveItem && 'border-slate-800 bg-slate-900/50',
                  )}
                >
                  <button
                    type="button"
                    onClick={() => setOpen(!open)}
                    className={clsx(
                      'flex w-full items-center gap-2 rounded-xl px-2 py-2 text-left text-[11px] font-semibold uppercase tracking-[0.12em] transition-colors',
                      hasActiveItem
                        ? 'text-white'
                        : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200',
                    )}
                  >
                    <span className="flex-1 truncate">{group.label}</span>
                    <ChevronDown className={clsx('h-4 w-4 transition-transform', expanded && 'rotate-180')} />
                  </button>

                  {expanded && (
                    <div className={clsx('mt-1 space-y-1', sidebarDense ? 'pb-1' : 'pb-2')}>
                      {visibleItems.map((item) => (
                        <div key={item.to} className={clsx(sidebarDense ? '' : 'px-1')}>
                          <SideNavLink
                            {...item}
                            enterprise
                            onNavigate={onNavigate}
                            badge={item.to === '/app/notifications' ? unread : undefined}
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              )
            })}
        </div>

        <div
          className={clsx(
            'pointer-events-none absolute inset-x-0 bottom-0 z-10 h-10 bg-gradient-to-t transition-opacity duration-200',
            enterpriseShellEnabled ? 'from-slate-950 to-transparent' : 'from-gray-900 to-transparent',
            showBottomFade ? 'opacity-100' : 'opacity-0',
          )}
        />
      </div>

      <div
        className={clsx(
          'border-t border-gray-700 px-5 py-4 text-xs text-gray-400',
          enterpriseShellEnabled && 'border-slate-800 px-4 py-3 text-[11px] text-slate-500',
        )}
      >
        {enterpriseShellEnabled ? t.header.enterpriseShellVersion : 'v0.1.0'}
      </div>
    </aside>
  )
}
