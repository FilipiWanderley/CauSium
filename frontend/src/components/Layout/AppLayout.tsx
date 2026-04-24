import { Outlet, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'
import { Sidebar } from '../Sidebar/Sidebar'
import { Header } from '../Header/Header'
import { NotificationsRealtimeBridge } from '../../realtime/NotificationsRealtimeBridge'

export function AppLayout() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const { t } = useI18n()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />

  // SP-A01: Block access to all app routes until the forced password change is satisfied.
  if (user?.must_change_password && location.pathname !== '/app/change-password') {
    return <Navigate to="/app/change-password" replace />
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <NotificationsRealtimeBridge />
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <div className="border-b border-amber-200 bg-amber-50 px-6 py-2.5">
          <p className="text-xs font-semibold text-amber-900">{t.platform.readOnlyBannerTitle}</p>
          <p className="mt-0.5 text-xs text-amber-800">{t.platform.readOnlyBannerBody}</p>
        </div>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
