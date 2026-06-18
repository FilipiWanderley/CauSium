import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bell, ChevronRight, LogOut, Menu } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { notificationsApi } from '../../api/notifications'
import { featureFlags } from '../../featureFlags'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'
import { usePersistentString } from '../../hooks/usePersistentBoolean'
import type { CloudProvider } from '../../types'
import { UserAvatar } from '../Avatar/UserAvatar'
import { preloadRoute } from '../../routes/lazyPages'

type HeaderProps = {
  onOpenSidebar?: () => void
}

export function Header({ onOpenSidebar }: HeaderProps) {
  const { user, logout } = useAuth()
  const { t } = useI18n()
  const location = useLocation()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)
  const [selectedProvider] = usePersistentString('enterprise-shell:provider', '')
  const enterpriseShellEnabled = featureFlags.enterpriseShell
  const showBreadcrumbs = enterpriseShellEnabled && featureFlags.breadcrumbs
  const showScopeSelector = enterpriseShellEnabled && featureFlags.scopeSelector
  const { data: unreadCount } = useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => notificationsApi.getUnreadCount(),
    enabled: !!user,
    refetchInterval: 30_000,
  })
  const unread = unreadCount?.unread ?? 0

  const providerLabelMap: Record<'' | CloudProvider, string> = {
    '': t.header.allProviders,
    azure: 'Azure',
    aws: 'AWS',
    gcp: 'GCP',
  }

  const providerContextLabel = providerLabelMap[(selectedProvider as '' | CloudProvider) || ''] ?? t.header.allProviders
  const breadcrumbs = useMemo(() => {
    const routes = [
      { match: '/app/economics/reports', items: [t.nav.sectionEconomics, t.nav.economicsReports] },
      { match: '/app/economics/skus', items: [t.nav.sectionEconomics, t.nav.economicsSkus] },
      { match: '/app/economics/usage', items: [t.nav.sectionEconomics, t.nav.economicsUsage] },
      { match: '/app/economics/costs', items: [t.nav.sectionEconomics, t.nav.economicsCosts] },
      { match: '/app/economics', items: [t.nav.sectionEconomics, t.nav.economics] },
      { match: '/app/intel', items: [t.nav.sectionOptimization, t.nav.opportunities] },
      { match: '/app/optimization-plan', items: [t.nav.sectionOptimization, t.nav.optimizationPlan] },
      { match: '/app/lab', items: [t.nav.sectionOptimization, t.nav.experiments] },
      { match: '/app/initiatives', items: [t.nav.sectionOptimization, t.nav.initiatives] },
      { match: '/app/risk-budgets', items: [t.nav.sectionGovernance, t.nav.riskBudgets] },
      { match: '/app/change-events', items: [t.nav.sectionGovernance, t.nav.changeEvents] },
      { match: '/app/executive', items: [t.nav.sectionGovernance, t.nav.executive] },
      { match: '/app/gov', items: [t.nav.sectionGovernance, t.nav.gov] },
      { match: '/app/green', items: [t.nav.sectionSustainability, t.nav.green] },
      { match: '/app/notifications', items: [t.nav.sectionOperations, t.nav.notifications] },
      { match: '/app/cloud', items: [t.nav.sectionOperations, t.nav.settingsCloud] },
      { match: '/app/members', items: [t.nav.sectionAdministration, t.nav.members] },
      { match: '/app/settings/team', items: [t.nav.sectionAdministration, t.nav.settingsTeam] },
      { match: '/app/settings/security', items: [t.nav.sectionAdministration, t.nav.settingsSecurity] },
      { match: '/app/settings', items: [t.nav.sectionAdministration, t.nav.settings] },
      { match: '/app/admin/reconciliation', items: [t.nav.sectionAdministration, t.nav.adminReconciliation] },
      { match: '/app/platform/workspaces', items: [t.nav.sectionAdministration, t.nav.platformWorkspaces] },
      { match: '/app/platform/sync', items: [t.nav.sectionAdministration, t.nav.platformSync] },
      { match: '/app/platform/integration-health', items: [t.nav.sectionAdministration, t.platform.integrationHealthTitle] },
      { match: '/app/platform/slo', items: [t.nav.sectionAdministration, t.nav.platformSlo] },
    ]
    const resolved = routes.find((route) => location.pathname === route.match || location.pathname.startsWith(`${route.match}/`))
    return [t.header.breadcrumbsHome, ...(resolved?.items ?? [t.header.operationalConsole])]
  }, [location.pathname, t])

  const handleLogout = async () => {
    setLogoutError(null)
    setIsLoggingOut(true)
    try {
      await logout()
    } catch (error) {
      console.error('Logout failed:', error)
      setLogoutError('Failed to sign out. Please try again.')
    } finally {
      setIsLoggingOut(false)
    }
  }

  return (
    <header
      className={
        enterpriseShellEnabled
          ? 'border-b border-gray-light bg-white px-4 py-3 shadow-card-premium lg:px-5'
          : 'flex items-center justify-between border-b bg-white px-4 py-3 shadow-sm lg:px-6'
      }
    >
      <div
        className={
          enterpriseShellEnabled
            ? 'flex w-full min-w-0 flex-col gap-3 xl:flex-row xl:items-start xl:justify-between xl:gap-4'
            : 'flex w-full min-w-0 items-center justify-between'
        }
      >
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <button
            type="button"
            onClick={onOpenSidebar}
            className="rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900 lg:hidden"
            aria-label="Open sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>

          {enterpriseShellEnabled ? (
            <div className="min-w-0 flex-1">
              {showBreadcrumbs && (
                <nav className="mb-1.5 flex min-w-0 max-w-full items-center gap-1 overflow-x-auto whitespace-nowrap text-[11px] font-medium text-gray-cool xl:max-w-[720px]">
                  {breadcrumbs.map((crumb, index) => (
                    <span key={`${crumb}-${index}`} className="flex items-center gap-1.5">
                      {index > 0 && <ChevronRight className="h-3 w-3 text-gray-light" />}
                      <span className={index === breadcrumbs.length - 1 ? 'text-navy' : undefined}>{crumb}</span>
                    </span>
                  ))}
                </nav>
              )}

              <div className="flex min-w-0 flex-col gap-2">
                {showScopeSelector && (
                  <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-gray-cool">
                    <span className="font-medium text-gray-cool">{t.header.scopeProvider}</span>
                    <span className="rounded-md border border-gray-light bg-gray-light/30 px-2.5 py-1 text-slate-struct">
                      {providerContextLabel}
                    </span>
                  </div>
                )}
                <div className="text-[11px] font-semibold text-navy">{t.header.operationalConsole}</div>
              </div>
            </div>
          ) : null}
        </div>

        {!enterpriseShellEnabled && <div className="flex min-w-0 items-center gap-2" />}

        <div
          className={
            enterpriseShellEnabled
              ? 'flex w-full min-w-0 flex-wrap items-center justify-between gap-2 md:gap-4 xl:w-auto xl:shrink-0 xl:justify-end'
              : 'flex min-w-0 items-center gap-2 md:gap-4'
          }
        >
          {user && (
            <div className="flex min-w-0 items-center gap-2.5">
              <UserAvatar name={user.full_name} />
              <div className="hidden min-w-0 max-w-[180px] leading-tight sm:block lg:max-w-[220px]">
                <p className="truncate text-sm font-semibold text-navy">{user.full_name}</p>
                <p className="hidden truncate text-xs text-gray-cool md:block">{user.org_name}</p>
              </div>
              <span className="hidden rounded bg-gray-light px-2 py-0.5 text-xs font-medium text-slate-struct xl:inline-flex">
                {user.role}
              </span>
            </div>
          )}

          <Link
            to="/app/notifications"
            onMouseEnter={() => preloadRoute('/app/notifications')}
            onFocus={() => preloadRoute('/app/notifications')}
            onPointerDown={() => preloadRoute('/app/notifications')}
            className="relative rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900"
            title={t.nav.notifications}
            aria-label={t.nav.notifications}
          >
            <Bell className="h-5 w-5" />
            {unread > 0 && (
              <span className="absolute -right-1 -top-1 rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                {unread > 99 ? '99+' : unread}
              </span>
            )}
          </Link>

          <button
            onClick={() => {
              void handleLogout()
            }}
            disabled={isLoggingOut}
            className="flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-900 disabled:opacity-60"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">{t.header.logout}</span>
          </button>
        </div>
      </div>

      {logoutError && (
        <div className={enterpriseShellEnabled ? 'mt-2 text-xs text-red-600' : 'text-xs text-red-600'}>
          {logoutError}
        </div>
      )}
    </header>
  )
}
