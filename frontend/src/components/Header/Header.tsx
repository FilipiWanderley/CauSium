import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bell, LogOut, Menu } from 'lucide-react'
import { Link } from 'react-router-dom'
import { notificationsApi } from '../../api/notifications'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'
import { UserAvatar } from '../Avatar/UserAvatar'
import { preloadRoute } from '../../routes/lazyPages'

type HeaderProps = {
  onOpenSidebar?: () => void
}

export function Header({ onOpenSidebar }: HeaderProps) {
  const { user, logout } = useAuth()
  const { t } = useI18n()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)
  const { data: unreadCount } = useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => notificationsApi.getUnreadCount(),
    enabled: !!user,
    refetchInterval: 30_000,
  })
  const unread = unreadCount?.unread ?? 0
  const handleLogout = async () => {
    setLogoutError(null)
    setIsLoggingOut(true)
    try {
      await logout()
    } catch (error) {
      console.error('Logout failed:', error)
      setLogoutError('Failed to sign out. Please try again.')
    } finally {
      setIsLoggingOut(false)
    }
  }

  return (
    <header className="flex items-center justify-between border-b bg-white px-4 py-3 shadow-sm lg:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          onClick={onOpenSidebar}
          className="rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900 lg:hidden"
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      <div className="flex min-w-0 items-center gap-2 md:gap-4">
        {/* User + org */}
        {user && (
          <div className="flex min-w-0 items-center gap-2.5">
            <UserAvatar name={user.full_name} />
            <div className="min-w-0 leading-tight hidden sm:block">
              <p className="truncate text-sm font-medium text-gray-900">{user.full_name}</p>
              <p className="truncate text-xs text-gray-400">{user.org_name}</p>
            </div>
            <span className="hidden rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500 md:inline-flex">
              {user.role}
            </span>
          </div>
        )}

        <Link
          to="/app/notifications"
          onMouseEnter={() => preloadRoute('/app/notifications')}
          onFocus={() => preloadRoute('/app/notifications')}
          onPointerDown={() => preloadRoute('/app/notifications')}
          className="relative rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900"
          title="Notificações"
          aria-label="Abrir notificações"
        >
          <Bell className="h-5 w-5" />
          {unread > 0 && (
            <span className="absolute -right-1 -top-1 rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </Link>

        <button
          onClick={() => {
            void handleLogout()
          }}
          disabled={isLoggingOut}
          className="flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-900 disabled:opacity-60"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">{t.header.logout}</span>
        </button>
        {logoutError && <span className="text-xs text-red-600">{logoutError}</span>}
      </div>
    </header>
  )
}
