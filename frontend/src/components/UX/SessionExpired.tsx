import { useCallback } from 'react'
import { LogIn } from 'lucide-react'

interface SessionExpiredProps {
  title?: string
  description?: string
}

export function SessionExpired({
  title = 'Session expired',
  description = 'Your session has ended. Please sign in again to continue.',
}: SessionExpiredProps) {
  const handleLogin = useCallback(() => {
    window.location.href = '/login'
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
      <div className="w-full max-w-sm text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-100">
          <LogIn className="h-7 w-7 text-brand-600" />
        </div>
        <h1 className="mt-5 text-lg font-semibold text-gray-900">{title}</h1>
        <p className="mt-2 text-sm text-gray-600">{description}</p>
        <button
          type="button"
          onClick={handleLogin}
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
        >
          <LogIn className="h-4 w-4" />
          Sign in
        </button>
        <p className="mt-6 text-xs text-gray-400">
          CauSium — Decision Support System
        </p>
      </div>
    </div>
  )
}
