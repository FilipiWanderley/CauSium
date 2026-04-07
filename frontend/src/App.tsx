import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/Layout/AppLayout'
import { LoginPage } from './pages/Login/LoginPage'
import { ForgotPasswordPage } from './pages/ForgotPassword/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/ResetPassword/ResetPasswordPage'
import { ChangePasswordPage } from './pages/ChangePassword/ChangePasswordPage'
import { DashboardPage } from './pages/Dashboard/DashboardPage'
import { OpportunitiesPage } from './pages/Opportunities/OpportunitiesPage'
import { InitiativesPage } from './pages/Initiatives/InitiativesPage'
import { ExperimentsPage } from './pages/Experiments/ExperimentsPage'
import { RiskBudgetsPage } from './pages/RiskBudgets/RiskBudgetsPage'
import { ChangeEventsPage } from './pages/ChangeEvents/ChangeEventsPage'
import { ExecutivePage } from './pages/Executive/ExecutivePage'
import { SettingsPage } from './pages/Settings/SettingsPage'
import { WorkspacesPage } from './pages/Platform/WorkspacesPage'

export default function App() {
  return (
    <BrowserRouter>
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
        </Route>

        {/* ── Fallback: redirect bare / and unmatched paths ─────────────── */}
        <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
