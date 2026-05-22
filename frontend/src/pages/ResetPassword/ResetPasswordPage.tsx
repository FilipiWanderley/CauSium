import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Cpu, Eye, EyeOff } from 'lucide-react'
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
    <div className="relative min-h-screen w-full overflow-hidden bg-[#020202] text-white">
      <style>{`
        .login-app-container { isolation: isolate; }
        .login-tech-grid {
          background-image:
            linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
          background-size: 60px 60px;
          background-position: center;
          mask-image: radial-gradient(ellipse 100% 100% at 50% 50%, black 10%, transparent 80%);
          -webkit-mask-image: radial-gradient(ellipse 100% 100% at 50% 50%, black 10%, transparent 80%);
        }
        .login-beam {
          position: absolute;
          width: 1px;
          background: linear-gradient(to bottom, transparent, rgba(70, 75, 140, 0.4), transparent);
          box-shadow: 0 0 20px rgba(70, 75, 140, 0.2);
          animation: loginBeamDrop linear infinite;
          opacity: 0;
          will-change: transform, opacity;
        }
        .login-beam-purple {
          background: linear-gradient(to bottom, transparent, rgba(95, 75, 140, 0.4), transparent);
          box-shadow: 0 0 20px rgba(95, 75, 140, 0.2);
        }
        .login-beam-1 { left: 20%; animation-duration: 8s; animation-delay: 1s; height: 180px; }
        .login-beam-2 { left: 35%; animation-duration: 11s; animation-delay: 4s; height: 260px; }
        .login-beam-3 { left: 50%; animation-duration: 7s; animation-delay: 0.5s; height: 140px; }
        .login-beam-4 { left: 68%; animation-duration: 9s; animation-delay: 3s; height: 220px; }
        .login-beam-5 { left: 85%; animation-duration: 6.5s; animation-delay: 2s; height: 190px; }
        @keyframes loginBeamDrop {
          0% { transform: translateY(-20vh); opacity: 0; }
          20% { opacity: 1; }
          80% { opacity: 1; }
          100% { transform: translateY(120vh); opacity: 0; }
        }
        .login-glass-card {
          background: rgba(6, 6, 18, 0.84);
          backdrop-filter: blur(28px);
          -webkit-backdrop-filter: blur(28px);
          border: 1px solid rgba(255, 255, 255, 0.12);
          box-shadow: 0 32px 64px -16px rgba(0, 0, 0, 0.7), 0 0 40px rgba(99, 102, 241, 0.08), inset 0 1px 0 rgba(255,255,255,0.06);
        }
        .login-glass-input {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.16);
          color: white;
        }
        .login-glass-input:hover {
          border-color: rgba(255, 255, 255, 0.26);
        }
        .login-glass-input:focus {
          background: rgba(255, 255, 255, 0.09);
          border-color: #8b5cf6;
          box-shadow: 0 0 0 1px #8b5cf6, 0 0 18px rgba(139, 92, 246, 0.25);
        }
      `}</style>

      <div className="login-app-container flex min-h-screen flex-col items-center justify-center">
        <div className="absolute inset-0 -z-20 bg-[#020202]" />
        <div className="login-tech-grid pointer-events-none absolute inset-0 z-0" />
        <div className="pointer-events-none absolute inset-0 z-0">
          <div className="login-beam login-beam-1" />
          <div className="login-beam login-beam-2 login-beam-purple" />
          <div className="login-beam login-beam-3" />
          <div className="login-beam login-beam-4 login-beam-purple" />
          <div className="login-beam login-beam-5" />
        </div>
        <div className="pointer-events-none absolute inset-0 z-0 bg-[#020202]/40" />

        <div className="relative z-10 flex w-full max-w-lg flex-col items-center px-6">
          <Link
            to="/login"
            className="fixed left-8 top-8 inline-flex items-center gap-2 text-sm text-gray-400 transition-colors hover:text-white group"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
            {rp.backToSignIn}
          </Link>

          <div className="mb-9 w-full text-center">
            <div
              className="absolute left-1/2 -z-[1] h-64 w-96 -translate-x-1/2 -translate-y-8 rounded-full"
              style={{ background: 'radial-gradient(ellipse at center, rgba(2,2,8,0.75) 0%, transparent 72%)' }}
            />
            <div className="mb-4 inline-flex items-center gap-3 rounded-full border border-white/15 bg-black/40 px-4 py-2 backdrop-blur-sm">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/20 bg-white/[0.08]">
                <Cpu className="h-4.5 w-4.5 text-white" strokeWidth={1.5} />
              </span>
              <span className="text-sm font-semibold uppercase tracking-[0.18em] text-white">CauSium</span>
            </div>
            <h1 className="text-[25px] font-semibold tracking-tight text-white" style={{ textShadow: '0 2px 16px rgba(0,0,0,0.9)' }}>
              {rp.title}
            </h1>
            <p
              className="mx-auto mt-2 max-w-sm text-[13px] leading-relaxed tracking-wide text-gray-200"
              style={{ textShadow: '0 1px 8px rgba(0,0,0,0.95)' }}
            >
              {rp.subtitle}
            </p>
          </div>

          <div className="login-glass-card w-full rounded-[20px] p-8 sm:p-9">
            <p className="mb-6 text-[13px] text-gray-300">
              Use the secure reset link to define a new password for your workspace account.
            </p>

          {success ? (
            <div className="mb-4 rounded-lg border border-emerald-300/30 bg-emerald-500/10 px-4 py-4 text-sm text-emerald-200">
              <p className="font-semibold">Password updated successfully.</p>
              <p className="mt-1">Redirecting to sign in in {redirectCountdown}s...</p>
              <div className="mt-3">
                <Link
                  to="/login?reset=success"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-200 transition-colors hover:text-white"
                >
                  <ArrowLeft className="h-4 w-4" />
                  {rp.backToSignIn}
                </Link>
              </div>
            </div>
          ) : (
            <>
              {error && (
                <div
                  className={`mb-4 rounded-lg border px-4 py-3 text-sm ${
                    isTokenIssue
                      ? 'border-amber-300/30 bg-amber-500/10 text-amber-200'
                      : 'border-red-300/30 bg-red-500/10 text-red-200'
                  }`}
                >
                  <p className="font-medium">
                    {isTokenIssue ? 'This reset link is invalid or expired.' : 'Could not reset password.'}
                  </p>
                  <p className="mt-1">{error}</p>
                  {isTokenIssue && (
                    <Link
                      to="/forgot-password"
                      className="mt-2 inline-flex text-sm font-medium text-amber-200 underline-offset-2 hover:underline"
                    >
                      Request a new reset link
                    </Link>
                  )}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                {!tokenFromUrl && (
                  <div>
                    <label className="mb-1.5 block text-[13px] font-medium text-white">{rp.tokenLabel}</label>
                    <input
                      type="text"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      required
                      placeholder={rp.tokenPlaceholder}
                      className="login-glass-input w-full rounded-xl px-4 py-3 font-mono text-sm placeholder-gray-400 outline-none transition-all duration-300"
                    />
                  </div>
                )}

                <div>
                  <label className="mb-1.5 block text-[13px] font-medium text-white">{rp.newPasswordLabel}</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      autoComplete="new-password"
                      minLength={8}
                      placeholder={rp.newPasswordPlaceholder}
                      className="login-glass-input w-full rounded-xl px-4 py-3 pr-11 text-sm placeholder-gray-400 outline-none transition-all duration-300"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 transition-colors hover:text-gray-300"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-[13px] font-medium text-white">{rp.confirmPasswordLabel}</label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    placeholder={rp.confirmPasswordPlaceholder}
                    className="login-glass-input w-full rounded-xl px-4 py-3 text-sm placeholder-gray-400 outline-none transition-all duration-300"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || !token.trim()}
                  className="mt-2 w-full rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 py-3.5 text-sm font-medium text-white transition-all duration-300 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] disabled:opacity-60"
                >
                  {loading ? rp.submitting : rp.submit}
                </button>
              </form>
            </>
          )}

          <div className="mt-6 text-center">
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-400 transition-colors hover:text-gray-200"
            >
              <ArrowLeft className="h-4 w-4" />
              {rp.backToSignIn}
            </Link>
          </div>
        </div>
      </div>
    </div>
    </div>
  )
}


