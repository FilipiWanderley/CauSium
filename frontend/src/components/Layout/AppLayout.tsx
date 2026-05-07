import { useEffect, useState } from 'react'
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
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

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
      <div className="hidden lg:flex">
        <Sidebar />
      </div>

      <div className="lg:hidden">
        {sidebarOpen && (
          <div className="fixed inset-0 z-40">
            <button
              type="button"
              className="absolute inset-0 bg-black/50"
              aria-label={t.common.close}
              onClick={() => setSidebarOpen(false)}
            />
            <div className="absolute inset-y-0 left-0 w-60 flex flex-col">
              <Sidebar onNavigate={() => setSidebarOpen(false)} />
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col overflow-hidden">
        <Header onOpenSidebar={() => setSidebarOpen(true)} />
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-2.5 lg:px-6">
          <p className="text-xs font-semibold text-amber-900">{t.platform.readOnlyBannerTitle}</p>
          <p className="mt-0.5 text-xs text-amber-800">{t.platform.readOnlyBannerBody}</p>
        </div>
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
