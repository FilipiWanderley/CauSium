import { Suspense, lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/Layout/AppLayout'

const LoginPage = lazy(() => import('./pages/Login/LoginPage').then((m) => ({ default: m.LoginPage })))
const ForgotPasswordPage = lazy(() =>
  import('./pages/ForgotPassword/ForgotPasswordPage').then((m) => ({ default: m.ForgotPasswordPage }))
)
const ResetPasswordPage = lazy(() =>
  import('./pages/ResetPassword/ResetPasswordPage').then((m) => ({ default: m.ResetPasswordPage }))
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
const WorkspacesPage = lazy(() =>
  import('./pages/Platform/WorkspacesPage').then((m) => ({ default: m.WorkspacesPage }))
)
const SyncStatusPage = lazy(() =>
  import('./pages/Platform/SyncStatusPage').then((m) => ({ default: m.SyncStatusPage }))
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

          {/* ── SP-A01: Change-password — authenticated but outside AppLayout ── */}
          {/* The page renders full-screen and is accessible even when             */}
          {/* must_change_password=true (otherwise there is no escape route).      */}
          <Route path="/app/change-password" element={<ChangePasswordPage />} />

          {/* ── Authenticated app shell ───────────────────────────────────── */}
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<Navigate to="/app/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="opportunities" element={<OpportunitiesPage />} />
            <Route path="initiatives" element={<InitiativesPage />} />
            <Route path="experiments" element={<ExperimentsPage />} />
            <Route path="risk-budgets" element={<RiskBudgetsPage />} />
            <Route path="change-events" element={<ChangeEventsPage />} />
            <Route path="executive" element={<ExecutivePage />} />
            <Route path="settings" element={<SettingsPage />} />
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
