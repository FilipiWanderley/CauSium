import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Cloud, ArrowLeft, Eye, EyeOff } from 'lucide-react'
import { authApi } from '../../api/auth'
import { useI18n } from '../../contexts/I18nContext'

export function ResetPasswordPage() {
  const { t } = useI18n()
  const rp = t.resetPassword
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const tokenFromUrl = searchParams.get('token') ?? ''

  const [token, setToken] = useState(tokenFromUrl)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError(rp.errorPasswordsMismatch)
      return
    }
    if (newPassword.length < 8) {
      setError(rp.errorPasswordTooShort)
      return
    }

    setLoading(true)
    try {
      await authApi.resetPassword(token, newPassword)
      navigate('/login?reset=success', { replace: true })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? rp.errorInvalidOrExpiredLink)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 text-white">
            <Cloud className="h-8 w-8 text-brand-500" />
            <span className="text-2xl font-bold">CauSium</span>
          </div>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-2xl">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900">{rp.title}</h2>
            <p className="mt-1 text-sm text-gray-500">{rp.subtitle}</p>
          </div>

          {error && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!tokenFromUrl && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">{rp.tokenLabel}</label>
                <input
                  type="text"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  required
                  placeholder={rp.tokenPlaceholder}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono"
                />
              </div>
            )}

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">{rp.newPasswordLabel}</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  minLength={8}
                  placeholder={rp.newPasswordPlaceholder}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">{rp.confirmPasswordLabel}</label>
              <input
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder={rp.confirmPasswordPlaceholder}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !token.trim()}
              className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60 transition-colors"
            >
              {loading ? rp.submitting : rp.submit}
            </button>
          </form>

          <div className="mt-5 text-center">
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="h-4 w-4" />
            {rp.backToSignIn}
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
