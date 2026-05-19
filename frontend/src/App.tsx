import { Suspense, useEffect, useState, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/Layout/AppLayout'
import { SessionExpired } from './components/UX/SessionExpired'
import { SESSION_EXPIRED_EVENT } from './api/client'
import {
  ActivateInvitePage,
  ChangeEventsPage,
  ChangePasswordPage,
  DashboardPage,
  EconomicsCostsPage,
  EconomicsReportsPage,
  EconomicsSkusPage,
  EconomicsUsagePage,
  ExecutivePage,
  ExperimentsPage,
  ForgotPasswordPage,
  GovPage,
  GreenPage,
  InitiativesPage,
  IntegrationHealthPage,
  LoginPage,
  MembersPage,
  NotificationsPage,
  OptimizationPlanPage,
  OpportunitiesPage,
  ReconciliationPage,
  ResetPasswordPage,
  RiskBudgetsPage,
  SettingsPage,
  SloPage,
  SyncStatusPage,
  WorkspacesPage,
} from './routes/lazyPages'

function lazyRoute(node: ReactNode) {
  return <Suspense fallback={null}>{node}</Suspense>
}

export default function App() {
  const [sessionExpired, setSessionExpired] = useState(false)

  useEffect(() => {
    const handler = () => setSessionExpired(true)
    window.addEventListener(SESSION_EXPIRED_EVENT, handler)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handler)
  }, [])

  if (sessionExpired) {
    return <SessionExpired />
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* ── Public routes ─────────────────────────────────────────────── */}
        <Route path="/login" element={lazyRoute(<LoginPage />)} />
        <Route path="/forgot-password" element={lazyRoute(<ForgotPasswordPage />)} />
        <Route path="/reset-password" element={lazyRoute(<ResetPasswordPage />)} />
        <Route path="/activate" element={lazyRoute(<ActivateInvitePage />)} />

        {/* ── SP-A01: Change-password — outside AppLayout ── */}
        <Route path="/app/change-password" element={lazyRoute(<ChangePasswordPage />)} />

        {/* ── Authenticated app shell ───────────────────────────────────── */}
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Navigate to="/app/dashboard" replace />} />
          <Route path="dashboard" element={lazyRoute(<DashboardPage />)} />
          <Route path="economics" element={lazyRoute(<DashboardPage />)} />
          <Route path="economics/costs" element={lazyRoute(<EconomicsCostsPage />)} />
          <Route path="economics/usage" element={lazyRoute(<EconomicsUsagePage />)} />
          <Route path="economics/skus" element={lazyRoute(<EconomicsSkusPage />)} />
          <Route path="economics/reports" element={lazyRoute(<EconomicsReportsPage />)} />
          <Route path="opportunities" element={lazyRoute(<OpportunitiesPage />)} />
          <Route path="intel" element={lazyRoute(<OpportunitiesPage />)} />
          <Route path="optimization-plan" element={lazyRoute(<OptimizationPlanPage />)} />
          <Route path="initiatives" element={lazyRoute(<InitiativesPage />)} />
          <Route path="experiments" element={lazyRoute(<ExperimentsPage />)} />
          <Route path="lab" element={lazyRoute(<ExperimentsPage />)} />
          <Route path="risk-budgets" element={lazyRoute(<RiskBudgetsPage />)} />
          <Route path="change-events" element={lazyRoute(<ChangeEventsPage />)} />
          <Route path="executive" element={lazyRoute(<ExecutivePage />)} />
          <Route path="notifications" element={lazyRoute(<NotificationsPage />)} />
          <Route path="gov" element={lazyRoute(<GovPage />)} />
          <Route path="green" element={lazyRoute(<GreenPage />)} />
          <Route path="members" element={lazyRoute(<MembersPage />)} />
          <Route path="cloud" element={lazyRoute(<SettingsPage />)} />
          <Route path="settings" element={lazyRoute(<SettingsPage />)} />
          <Route path="settings/team" element={lazyRoute(<SettingsPage />)} />
          <Route path="settings/cloud" element={lazyRoute(<SettingsPage />)} />
          <Route path="settings/security" element={lazyRoute(<SettingsPage />)} />
          <Route path="platform/workspaces" element={lazyRoute(<WorkspacesPage />)} />
          <Route path="platform/sync" element={lazyRoute(<SyncStatusPage />)} />
          <Route path="platform/integration-health" element={lazyRoute(<IntegrationHealthPage />)} />
          <Route path="platform/slo" element={lazyRoute(<SloPage />)} />
          <Route path="admin/reconciliation" element={lazyRoute(<ReconciliationPage />)} />
        </Route>

        {/* ── Fallback ─────────────────────────────────────────────── */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
