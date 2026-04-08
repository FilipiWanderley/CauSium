import { Suspense, lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/Layout/AppLayout'
import { ComingSoonPage } from './pages/ComingSoon/ComingSoonPage'

const LoginPage = lazy(() => import('./pages/Login/LoginPage').then((m) => ({ default: m.LoginPage })))
const ForgotPasswordPage = lazy(() =>
  import('./pages/ForgotPassword/ForgotPasswordPage').then((m) => ({ default: m.ForgotPasswordPage }))
)
const ResetPasswordPage = lazy(() =>
  import('./pages/ResetPassword/ResetPasswordPage').then((m) => ({ default: m.ResetPasswordPage }))
)
const ActivateInvitePage = lazy(() =>
  import('./pages/ActivateInvite/ActivateInvitePage').then((m) => ({ default: m.ActivateInvitePage }))
)
const ChangePasswordPage = lazy(() =>
  import('./pages/ChangePassword/ChangePasswordPage').then((m) => ({ default: m.ChangePasswordPage }))
)
const DashboardPage = lazy(() =>
  import('./pages/Dashboard/DashboardPage').then((m) => ({ default: m.DashboardPage }))
)
const OpportunitiesPage = lazy(() =>
  import('./pages/Opportunities/OpportunitiesPage').then((m) => ({ default: m.OpportunitiesPage }))
)
const InitiativesPage = lazy(() =>
  import('./pages/Initiatives/InitiativesPage').then((m) => ({ default: m.InitiativesPage }))
)
const ExperimentsPage = lazy(() =>
  import('./pages/Experiments/ExperimentsPage').then((m) => ({ default: m.ExperimentsPage }))
)
const RiskBudgetsPage = lazy(() =>
  import('./pages/RiskBudgets/RiskBudgetsPage').then((m) => ({ default: m.RiskBudgetsPage }))
)
const ChangeEventsPage = lazy(() =>
  import('./pages/ChangeEvents/ChangeEventsPage').then((m) => ({ default: m.ChangeEventsPage }))
)
const ExecutivePage = lazy(() =>
  import('./pages/Executive/ExecutivePage').then((m) => ({ default: m.ExecutivePage }))
)
const SettingsPage = lazy(() =>
  import('./pages/Settings/SettingsPage').then((m) => ({ default: m.SettingsPage }))
)
const MembersPage = lazy(() =>
  import('./pages/Members/MembersPage').then((m) => ({ default: m.MembersPage }))
)
const WorkspacesPage = lazy(() =>
  import('./pages/Platform/WorkspacesPage').then((m) => ({ default: m.WorkspacesPage }))
)
const SyncStatusPage = lazy(() =>
  import('./pages/Platform/SyncStatusPage').then((m) => ({ default: m.SyncStatusPage }))
)
const EconomicsSkusPage = lazy(() =>
  import('./pages/EconomicsSkus/EconomicsSkusPage').then((m) => ({ default: m.EconomicsSkusPage }))
)
const EconomicsReportsPage = lazy(() =>
  import('./pages/EconomicsReports/EconomicsReportsPage').then((m) => ({ default: m.EconomicsReportsPage }))
)

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="p-6 text-sm text-gray-500">Loading page...</div>}>
        <Routes>
          {/* ── Public routes ─────────────────────────────────────────────── */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/activate" element={<ActivateInvitePage />} />

          {/* ── SP-A01: Change-password — authenticated but outside AppLayout ── */}
          {/* The page renders full-screen and is accessible even when             */}
          {/* must_change_password=true (otherwise there is no escape route).      */}
          <Route path="/app/change-password" element={<ChangePasswordPage />} />

          {/* ── Authenticated app shell ───────────────────────────────────── */}
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<Navigate to="/app/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="economics" element={<DashboardPage />} />
            <Route
              path="economics/costs"
              element={
                <ComingSoonPage
                  title="Economics Costs"
                  description="Detailed cost analysis with advanced filters will be connected here."
                />
              }
            />
            <Route
              path="economics/usage"
              element={
                <ComingSoonPage
                  title="Economics Usage"
                  description="Usage and efficiency analytics per service and team will be connected here."
                />
              }
            />
            <Route
              path="economics/skus"
              element={<EconomicsSkusPage />}
            />
            <Route
              path="economics/reports"
              element={<EconomicsReportsPage />}
            />
            <Route path="opportunities" element={<OpportunitiesPage />} />
            <Route path="intel" element={<OpportunitiesPage />} />
            <Route path="initiatives" element={<InitiativesPage />} />
            <Route path="experiments" element={<ExperimentsPage />} />
            <Route path="lab" element={<ExperimentsPage />} />
            <Route path="risk-budgets" element={<RiskBudgetsPage />} />
            <Route path="change-events" element={<ChangeEventsPage />} />
            <Route path="executive" element={<ExecutivePage />} />
            <Route
              path="notifications"
              element={
                <ComingSoonPage
                  title="Notifications"
                  description="Centralized alert management and notification preferences will be connected here."
                />
              }
            />
            <Route
              path="gov"
              element={
                <ComingSoonPage
                  title="PulseGov"
                  description="Governance and compliance controls for resources will be connected here."
                />
              }
            />
            <Route
              path="green"
              element={
                <ComingSoonPage
                  title="PulseGreen"
                  description="Sustainability and carbon analytics will be connected here."
                />
              }
            />
            <Route path="members" element={<MembersPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="settings/team" element={<SettingsPage />} />
            <Route path="settings/cloud" element={<SettingsPage />} />
            <Route path="settings/security" element={<SettingsPage />} />
            <Route path="platform/workspaces" element={<WorkspacesPage />} />
            <Route path="platform/sync" element={<SyncStatusPage />} />
          </Route>

          {/* ── Fallback: redirect bare / and unmatched paths ─────────────── */}
          <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
