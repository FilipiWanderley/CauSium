import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Eye, EyeOff } from 'lucide-react'
import { authApi } from '../../api/auth'
import { useI18n } from '../../contexts/I18nContext'

// CauSium Enterprise Logo SVG
function CausiumLogo({ variant = 'dark' }: { variant?: 'dark' | 'light' }) {
  const textColor = variant === 'dark' ? '#0f172a' : '#ffffff'
  const accentColor = '#0d9488'

  return (
    <svg
      width="130"
      height="30"
      viewBox="0 0 130 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="CauSium"
    >
      <g transform="translate(0, 2)">
        <path
          d="M4 18C2 18 0.5 16.5 0.5 14.5C0.5 12.8 1.6 11.4 3.1 11C3 10.6 2.95 10.2 2.95 9.75C2.95 7.4 4.85 5.5 7.2 5.5C9.55 5.5 11.45 7.4 11.45 9.75C11.45 10.2 11.4 10.6 11.3 11C12.8 11.4 13.9 12.8 13.9 14.5C13.9 16.5 12.4 18 10.4 18H4Z"
          fill={accentColor}
          opacity="0.9"
        />
        <rect x="1.5" y="19" width="2" height="6" rx="0.5" fill={accentColor} opacity="0.7" />
        <rect x="5" y="20" width="1.5" height="5" rx="0.5" fill={accentColor} opacity="0.6" />
        <rect x="8" y="19" width="2" height="6" rx="0.5" fill={accentColor} opacity="0.7" />
      </g>
      <text x="22" y="21" fontFamily="system-ui, -apple-system, sans-serif" fontSize="18" fontWeight="600" fill={textColor}>
        CauSium
      </text>
    </svg>
  )
}

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
  const [success, setSuccess] = useState(false)
  const [redirectCountdown, setRedirectCountdown] = useState(3)

  const isTokenIssue = useMemo(() => {
    const normalized = error.toLowerCase()
    return normalized.includes('token') || normalized.includes('expired') || normalized.includes('invalid')
  }, [error])

  useEffect(() => {
    if (!success) return
    setRedirectCountdown(3)
    const interval = window.setInterval(() => {
      setRedirectCountdown((prev) => (prev > 1 ? prev - 1 : prev))
    }, 1000)
    const timeout = window.setTimeout(() => {
      navigate('/login?reset=success', { replace: true })
    }, 3000)
    return () => {
      window.clearInterval(interval)
      window.clearTimeout(timeout)
    }
  }, [success, navigate])

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
      setSuccess(true)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? rp.errorInvalidOrExpiredLink)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full bg-slate-50">
      <div className="flex min-h-screen">
        {/* LEFT COLUMN - Enterprise branding (hidden on mobile) */}
        <div className="hidden lg:flex lg:w-1/2 xl:w-[55%] flex-col justify-center bg-[#0f172a] p-10 xl:p-16 relative overflow-hidden">
          {/* Background gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#0f172a] via-[#1e293b] to-[#0f172a]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-[#0d9488]/10 via-transparent to-transparent" />

          {/* Grid pattern */}
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
              backgroundSize: '60px 60px',
            }}
          />

          {/* Content */}
          <div className="relative z-10 max-w-md">
            {/* Logo */}
            <div className="mb-10">
              <CausiumLogo variant="light" />
            </div>

            {/* Icon */}
            <div className="w-16 h-16 rounded-2xl bg-[#0d9488]/15 flex items-center justify-center mb-6">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-teal-400">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>

            {/* Headline */}
            <h1 className="text-3xl xl:text-4xl font-semibold text-white leading-tight mb-6">
              Crie uma nova
              <br />
              <span className="text-teal-400">senha segura</span>.
            </h1>

            {/* Subtitle */}
            <p className="text-slate-300 text-base xl:text-lg leading-relaxed">
              Use o link seguro enviado para seu e-mail para redefinir sua senha.
            </p>
          </div>
        </div>

        {/* RIGHT COLUMN - Form */}
        <div className="flex w-full lg:w-1/2 xl:w-[45%] flex-col justify-center px-6 py-12 sm:px-8 lg:px-16 xl:px-20">
          <div className="w-full max-w-md mx-auto">
            {/* Mobile logo */}
            <div className="lg:hidden mb-8 text-center">
              <CausiumLogo variant="dark" />
            </div>

            {/* Success state */}
            {success ? (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
                <div className="mx-auto w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  Password updated successfully.
                </h3>
                <p className="text-sm text-slate-600 mb-4">
                  Redirecting to sign in in {redirectCountdown}s...
                </p>
                <Link
                  to="/login?reset=success"
                  className="inline-flex items-center gap-2 text-sm font-medium text-teal-600 hover:text-teal-700 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  {rp.backToSignIn}
                </Link>
              </div>
            ) : (
              <>
                {/* Header */}
                <div className="mb-8">
                  <h2 className="text-2xl font-semibold text-slate-900 mb-2">
                    {rp.title}
                  </h2>
                  <p className="text-slate-500 text-sm">
                    {rp.subtitle}
                  </p>
                </div>

                {/* Error state */}
                {error && (
                  <div
                    className={`mb-6 rounded-lg border px-4 py-3 text-sm ${
                      isTokenIssue
                        ? 'border-amber-200 bg-amber-50 text-amber-800'
                        : 'border-red-200 bg-red-50 text-red-700'
                    }`}
                  >
                    <p className="font-medium">
                      {isTokenIssue ? 'This reset link is invalid or expired.' : 'Could not reset password.'}
                    </p>
                    <p className="mt-1">{error}</p>
                    {isTokenIssue && (
                      <Link
                        to="/forgot-password"
                        className="mt-2 inline-flex text-sm font-medium text-amber-700 underline-offset-2 hover:underline"
                      >
                        Request a new reset link
                      </Link>
                    )}
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                  {/* Token */}
                  {!tokenFromUrl && (
                    <div>
                      <label htmlFor="token" className="block text-sm font-medium text-slate-700 mb-1.5">
                        {rp.tokenLabel}
                      </label>
                      <input
                        id="token"
                        type="text"
                        value={token}
                        onChange={(e) => setToken(e.target.value)}
                        required
                        placeholder={rp.tokenPlaceholder}
                        className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 font-mono outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                      />
                    </div>
                  )}

                  {/* New password */}
                  <div>
                    <label htmlFor="new-password" className="block text-sm font-medium text-slate-700 mb-1.5">
                      {rp.newPasswordLabel}
                    </label>
                    <div className="relative">
                      <input
                        id="new-password"
                        type={showPassword ? 'text' : 'password'}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                        autoComplete="new-password"
                        minLength={8}
                        placeholder={rp.newPasswordPlaceholder}
                        className="w-full rounded-lg border border-slate-300 px-4 py-3 pr-11 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                      </button>
                    </div>
                  </div>

                  {/* Confirm password */}
                  <div>
                    <label htmlFor="confirm-password" className="block text-sm font-medium text-slate-700 mb-1.5">
                      {rp.confirmPasswordLabel}
                    </label>
                    <input
                      id="confirm-password"
                      type={showPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      autoComplete="new-password"
                      placeholder={rp.confirmPasswordPlaceholder}
                      className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                    />
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={loading || !token.trim()}
                    className="w-full rounded-lg bg-[#0f172a] py-3 text-sm font-medium text-white transition-colors hover:bg-[#1e293b] focus:outline-none focus:ring-2 focus:ring-[#0f172a]/50 disabled:opacity-60"
                  >
                    {loading ? rp.submitting : rp.submit}
                  </button>
                </form>

                {/* Back to login */}
                <div className="mt-6 text-center">
                  <Link
                    to="/login"
                    className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    {rp.backToSignIn}
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
