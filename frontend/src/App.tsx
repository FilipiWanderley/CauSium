import { Suspense, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/Layout/AppLayout'
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
  LoginPage,
  MembersPage,
  NotificationsPage,
  OpportunitiesPage,
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
          <Route path="platform/slo" element={lazyRoute(<SloPage />)} />
        </Route>

        {/* ── Fallback ─────────────────────────────────────────────── */}
        <Route path="/" element={<Navigate to="/landing/index.html" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
