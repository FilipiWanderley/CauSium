import { lazy, type ComponentType, type LazyExoticComponent } from 'react'

type PreloadableLazy<T extends ComponentType<any>> = LazyExoticComponent<T> & {
  preload: () => Promise<unknown>
}

function lazyWithPreload<T extends ComponentType<any>>(
  importer: () => Promise<{ default: T }>
): PreloadableLazy<T> {
  const Component = lazy(importer) as PreloadableLazy<T>
  Component.preload = importer
  return Component
}

export const LoginPage = lazyWithPreload(() =>
  import('../pages/Login/LoginPage').then((m) => ({ default: m.LoginPage }))
)
export const ForgotPasswordPage = lazyWithPreload(() =>
  import('../pages/ForgotPassword/ForgotPasswordPage').then((m) => ({ default: m.ForgotPasswordPage }))
)
export const ResetPasswordPage = lazyWithPreload(() =>
  import('../pages/ResetPassword/ResetPasswordPage').then((m) => ({ default: m.ResetPasswordPage }))
)
export const ActivateInvitePage = lazyWithPreload(() =>
  import('../pages/ActivateInvite/ActivateInvitePage').then((m) => ({ default: m.ActivateInvitePage }))
)
export const ChangePasswordPage = lazyWithPreload(() =>
  import('../pages/ChangePassword/ChangePasswordPage').then((m) => ({ default: m.ChangePasswordPage }))
)

export const DashboardPage = lazyWithPreload(() =>
  import('../pages/Dashboard/DashboardPage').then((m) => ({ default: m.DashboardPage }))
)
export const EconomicsCostsPage = lazyWithPreload(() =>
  import('../pages/EconomicsCosts/EconomicsCostsPage').then((m) => ({ default: m.EconomicsCostsPage }))
)
export const EconomicsUsagePage = lazyWithPreload(() =>
  import('../pages/EconomicsUsage/EconomicsUsagePage').then((m) => ({ default: m.EconomicsUsagePage }))
)
export const EconomicsSkusPage = lazyWithPreload(() =>
  import('../pages/EconomicsSkus/EconomicsSkusPage').then((m) => ({ default: m.EconomicsSkusPage }))
)
export const EconomicsReportsPage = lazyWithPreload(() =>
  import('../pages/EconomicsReports/EconomicsReportsPage').then((m) => ({ default: m.EconomicsReportsPage }))
)
export const OpportunitiesPage = lazyWithPreload(() =>
  import('../pages/Opportunities/OpportunitiesPage').then((m) => ({ default: m.OpportunitiesPage }))
)
export const OptimizationPlanPage = lazyWithPreload(() =>
  import('../pages/OptimizationPlan/OptimizationPlanPage').then((m) => ({ default: m.OptimizationPlanPage }))
)
export const InitiativesPage = lazyWithPreload(() =>
  import('../pages/Initiatives/InitiativesPage').then((m) => ({ default: m.InitiativesPage }))
)
export const ExperimentsPage = lazyWithPreload(() =>
  import('../pages/Experiments/ExperimentsPage').then((m) => ({ default: m.ExperimentsPage }))
)
export const RiskBudgetsPage = lazyWithPreload(() =>
  import('../pages/RiskBudgets/RiskBudgetsPage').then((m) => ({ default: m.RiskBudgetsPage }))
)
export const ChangeEventsPage = lazyWithPreload(() =>
  import('../pages/ChangeEvents/ChangeEventsPage').then((m) => ({ default: m.ChangeEventsPage }))
)
export const ExecutivePage = lazyWithPreload(() =>
  import('../pages/Executive/ExecutivePage').then((m) => ({ default: m.ExecutivePage }))
)
export const NotificationsPage = lazyWithPreload(() =>
  import('../pages/Notifications/NotificationsPage').then((m) => ({ default: m.NotificationsPage }))
)
export const GovPage = lazyWithPreload(() =>
  import('../pages/Gov/GovPage').then((m) => ({ default: m.GovPage }))
)
export const GreenPage = lazyWithPreload(() =>
  import('../pages/Green/GreenPage').then((m) => ({ default: m.GreenPage }))
)
export const MembersPage = lazyWithPreload(() =>
  import('../pages/Members/MembersPage').then((m) => ({ default: m.MembersPage }))
)
export const SettingsPage = lazyWithPreload(() =>
  import('../pages/Settings/SettingsPage').then((m) => ({ default: m.SettingsPage }))
)
export const WorkspacesPage = lazyWithPreload(() =>
  import('../pages/Platform/WorkspacesPage').then((m) => ({ default: m.WorkspacesPage }))
)
export const SyncStatusPage = lazyWithPreload(() =>
  import('../pages/Platform/SyncStatusPage').then((m) => ({ default: m.SyncStatusPage }))
)
export const SloPage = lazyWithPreload(() =>
  import('../pages/Platform/SloPage').then((m) => ({ default: m.SloPage }))
)
export const ReconciliationPage = lazyWithPreload(() =>
  import('../pages/Reconciliation/ReconciliationPage').then((m) => ({ default: m.ReconciliationPage }))
)

const PRELOAD_BY_PATH: Array<[string, () => Promise<unknown>]> = [
  ['/login', LoginPage.preload],
  ['/forgot-password', ForgotPasswordPage.preload],
  ['/reset-password', ResetPasswordPage.preload],
  ['/activate', ActivateInvitePage.preload],
  ['/app/change-password', ChangePasswordPage.preload],
  ['/app/dashboard', DashboardPage.preload],
  ['/app/economics/costs', EconomicsCostsPage.preload],
  ['/app/economics/usage', EconomicsUsagePage.preload],
  ['/app/economics/skus', EconomicsSkusPage.preload],
  ['/app/economics/reports', EconomicsReportsPage.preload],
  ['/app/economics', DashboardPage.preload],
  ['/app/opportunities', OpportunitiesPage.preload],
  ['/app/intel', OpportunitiesPage.preload],
  ['/app/optimization-plan', OptimizationPlanPage.preload],
  ['/app/initiatives', InitiativesPage.preload],
  ['/app/experiments', ExperimentsPage.preload],
  ['/app/lab', ExperimentsPage.preload],
  ['/app/risk-budgets', RiskBudgetsPage.preload],
  ['/app/change-events', ChangeEventsPage.preload],
  ['/app/executive', ExecutivePage.preload],
  ['/app/notifications', NotificationsPage.preload],
  ['/app/gov', GovPage.preload],
  ['/app/green', GreenPage.preload],
  ['/app/members', MembersPage.preload],
  ['/app/cloud', SettingsPage.preload],
  ['/app/settings/team', SettingsPage.preload],
  ['/app/settings/cloud', SettingsPage.preload],
  ['/app/settings/security', SettingsPage.preload],
  ['/app/settings', SettingsPage.preload],
  ['/app/platform/workspaces', WorkspacesPage.preload],
  ['/app/platform/sync', SyncStatusPage.preload],
  ['/app/platform/slo', SloPage.preload],
  ['/app/admin/reconciliation', ReconciliationPage.preload],
]

export function preloadRoute(path: string): void {
  const normalizedPath = path.split('?')[0].split('#')[0]
  const match = PRELOAD_BY_PATH.find(([routePath]) => routePath === normalizedPath)
  if (!match) return
  void match[1]()
}
