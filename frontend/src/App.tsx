import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/Layout/AppLayout'
import { ActivateInvitePage } from './pages/ActivateInvite/ActivateInvitePage'
import { ChangeEventsPage } from './pages/ChangeEvents/ChangeEventsPage'
import { ChangePasswordPage } from './pages/ChangePassword/ChangePasswordPage'
import { DashboardPage } from './pages/Dashboard/DashboardPage'
import { EconomicsCostsPage } from './pages/EconomicsCosts/EconomicsCostsPage'
import { EconomicsReportsPage } from './pages/EconomicsReports/EconomicsReportsPage'
import { EconomicsSkusPage } from './pages/EconomicsSkus/EconomicsSkusPage'
import { EconomicsUsagePage } from './pages/EconomicsUsage/EconomicsUsagePage'
import { ExecutivePage } from './pages/Executive/ExecutivePage'
import { ExperimentsPage } from './pages/Experiments/ExperimentsPage'
import { ForgotPasswordPage } from './pages/ForgotPassword/ForgotPasswordPage'
import { GovPage } from './pages/Gov/GovPage'
import { GreenPage } from './pages/Green/GreenPage'
import { InitiativesPage } from './pages/Initiatives/InitiativesPage'
import { LoginPage } from './pages/Login/LoginPage'
import { MembersPage } from './pages/Members/MembersPage'
import { NotificationsPage } from './pages/Notifications/NotificationsPage'
import { OpportunitiesPage } from './pages/Opportunities/OpportunitiesPage'
import { SloPage } from './pages/Platform/SloPage'
import { SyncStatusPage } from './pages/Platform/SyncStatusPage'
import { WorkspacesPage } from './pages/Platform/WorkspacesPage'
import { ResetPasswordPage } from './pages/ResetPassword/ResetPasswordPage'
import { RiskBudgetsPage } from './pages/RiskBudgets/RiskBudgetsPage'
import { SettingsPage } from './pages/Settings/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ── Public routes ─────────────────────────────────────────────── */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/activate" element={<ActivateInvitePage />} />

        {/* ── SP-A01: Change-password — outside AppLayout ── */}
        <Route path="/app/change-password" element={<ChangePasswordPage />} />

        {/* ── Authenticated app shell ───────────────────────────────────── */}
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Navigate to="/app/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="economics" element={<DashboardPage />} />
          <Route path="economics/costs" element={<EconomicsCostsPage />} />
          <Route path="economics/usage" element={<EconomicsUsagePage />} />
          <Route path="economics/skus" element={<EconomicsSkusPage />} />
          <Route path="economics/reports" element={<EconomicsReportsPage />} />
          <Route path="opportunities" element={<OpportunitiesPage />} />
          <Route path="intel" element={<OpportunitiesPage />} />
          <Route path="initiatives" element={<InitiativesPage />} />
          <Route path="experiments" element={<ExperimentsPage />} />
          <Route path="lab" element={<ExperimentsPage />} />
          <Route path="risk-budgets" element={<RiskBudgetsPage />} />
          <Route path="change-events" element={<ChangeEventsPage />} />
          <Route path="executive" element={<ExecutivePage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="gov" element={<GovPage />} />
          <Route path="green" element={<GreenPage />} />
          <Route path="members" element={<MembersPage />} />
          <Route path="cloud" element={<SettingsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="settings/team" element={<SettingsPage />} />
          <Route path="settings/cloud" element={<SettingsPage />} />
          <Route path="settings/security" element={<SettingsPage />} />
          <Route path="platform/workspaces" element={<WorkspacesPage />} />
          <Route path="platform/sync" element={<SyncStatusPage />} />
          <Route path="platform/slo" element={<SloPage />} />
        </Route>

        {/* ── Fallback ─────────────────────────────────────────────── */}
        <Route path="/" element={<Navigate to="/landing/index.html" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
