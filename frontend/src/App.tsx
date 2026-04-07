import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/Layout/AppLayout'
import { LoginPage } from './pages/Login/LoginPage'
import { DashboardPage } from './pages/Dashboard/DashboardPage'
import { OpportunitiesPage } from './pages/Opportunities/OpportunitiesPage'
import { InitiativesPage } from './pages/Initiatives/InitiativesPage'
import { ExperimentsPage } from './pages/Experiments/ExperimentsPage'
import { RiskBudgetsPage } from './pages/RiskBudgets/RiskBudgetsPage'
import { ChangeEventsPage } from './pages/ChangeEvents/ChangeEventsPage'
import { ExecutivePage } from './pages/Executive/ExecutivePage'
import { SettingsPage } from './pages/Settings/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/opportunities" element={<OpportunitiesPage />} />
          <Route path="/initiatives" element={<InitiativesPage />} />
          <Route path="/experiments" element={<ExperimentsPage />} />
          <Route path="/risk-budgets" element={<RiskBudgetsPage />} />
          <Route path="/change-events" element={<ChangeEventsPage />} />
          <Route path="/executive" element={<ExecutivePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
