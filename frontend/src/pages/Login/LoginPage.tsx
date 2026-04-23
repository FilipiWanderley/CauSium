import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { ArrowLeft, Cpu, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'

export function LoginPage() {
  const { login, loginWithPasskey, isAuthenticated } = useAuth()
  const { t } = useI18n()
  const lg = t.login
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [resetSuccess, setResetSuccess] = useState(false)
  const [activationSuccess, setActivationSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const [passkeyLoading, setPasskeyLoading] = useState(false)
  const [oidcLoading, setOidcLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || '', [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const oidcError = params.get('oidc_error')
    if (oidcError) setError(lg.oidcFailed.replace('{{error}}', oidcError))
    if (params.get('reset') === 'success') {
      setResetSuccess(true)
      setError('')
    }
    if (params.get('activated') === 'success') {
      setActivationSuccess(true)
      setError('')
    }
  }, [lg.oidcFailed])

  useEffect(() => {
    if ((window as unknown as { UnicornStudio?: { isInitialized?: boolean } }).UnicornStudio?.isInitialized) {
      return
    }
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v1.4.29/dist/unicornStudio.umd.js'
    script.onload = () => {
      const w = window as unknown as {
        UnicornStudio?: { isInitialized?: boolean; init?: () => void }
      }
      if (!w.UnicornStudio?.isInitialized && typeof w.UnicornStudio?.init === 'function') {
        w.UnicornStudio.init()
        w.UnicornStudio.isInitialized = true
      }
    }
    document.head.appendChild(script)
  }, [])

  if (isAuthenticated) return <Navigate to="/app/dashboard" replace />

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 401 || status === 403) {
        setError(lg.invalidCredentials)
      } else if (status && status >= 500) {
        setError(lg.serverError)
      } else {
        setError(lg.networkError)
      }
    } finally {
      setLoading(false)
    }
  }

  const handlePasskeyLogin = async () => {
    setError('')
    setPasskeyLoading(true)
    try {
      await loginWithPasskey(email)
    } catch {
      setError(lg.passkeyFailed)
    } finally {
      setPasskeyLoading(false)
    }
  }

  const handleMicrosoftLogin = () => {
    setOidcLoading(true)
    window.location.href = `${apiBase}/api/v1/auth/oidc/azure/start`
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
        <div data-us-project="guA2nIvok3TuYtPyn8zX" className="absolute left-0 top-0 -z-10 h-full w-full" />
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
          <a
            href="/landing/index.html"
            className="fixed left-8 top-8 inline-flex items-center gap-2 text-sm text-gray-400 transition-colors hover:text-white group"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
            {lg.back}
          </a>

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
              {lg.welcomeBack}
            </h1>
            <p
              className="mx-auto mt-2 max-w-sm text-[13px] leading-relaxed tracking-wide text-gray-200"
              style={{ textShadow: '0 1px 8px rgba(0,0,0,0.95)' }}
            >
              {lg.subtitle}
            </p>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs text-gray-200">
              <span className="rounded-full border border-white/15 bg-black/50 px-3 py-1 backdrop-blur-sm">{lg.badgeMultiCloud}</span>
              <span className="rounded-full border border-white/15 bg-black/50 px-3 py-1 backdrop-blur-sm">{lg.badgeRiskAware}</span>
              <span className="rounded-full border border-white/15 bg-black/50 px-3 py-1 backdrop-blur-sm">{lg.badgeEnterprise}</span>
            </div>
          </div>

          <div className="login-glass-card w-full rounded-[20px] p-8 sm:p-9">
            <p className="mb-6 text-[13px] text-gray-300">{lg.signInContinue}</p>

            {error && (
              <div className="mb-4 rounded-lg border border-red-300/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}
            {resetSuccess && (
              <div className="mb-4 rounded-lg border border-emerald-300/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                Password updated successfully. Sign in with your new password.
              </div>
            )}
            {activationSuccess && (
              <div className="mb-4 rounded-lg border border-emerald-300/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                Invite accepted successfully. Sign in with your new account.
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-[13px] font-medium text-white">{lg.emailLabel}</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  className="login-glass-input w-full rounded-xl px-4 py-3 text-sm text-white placeholder-gray-400 outline-none transition-all duration-300"
                  placeholder={lg.emailPlaceholder}
                />
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <label className="block text-[13px] font-medium text-white">{lg.passwordLabel}</label>
                  <Link
                    to="/forgot-password"
                    className="text-[13px] text-violet-300 transition-colors hover:text-violet-400"
                  >
                    {lg.forgotPassword}
                  </Link>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    className="login-glass-input w-full rounded-xl px-4 py-3 pr-11 text-sm text-white placeholder-gray-400 outline-none transition-all duration-300"
                    placeholder={lg.passwordPlaceholder}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                    tabIndex={-1}
                    aria-label={showPassword ? lg.hidePassword : lg.showPassword}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="mt-2 w-full rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 py-3.5 text-sm font-medium text-white transition-all duration-300 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] disabled:opacity-60"
              >
                {loading ? lg.signingIn : lg.signIn}
              </button>
            </form>

            <div className="relative my-6 flex items-center">
              <div className="flex-grow border-t border-white/10" />
              <span className="mx-4 flex-shrink-0 text-[13px] text-gray-400">{lg.orContinueWith}</span>
              <div className="flex-grow border-t border-white/10" />
            </div>

            <button
              type="button"
              onClick={handlePasskeyLogin}
              disabled={!email || passkeyLoading}
              title={!email ? lg.enterEmailFirst : undefined}
              className="relative mb-3 flex w-full cursor-pointer items-center justify-center gap-3 rounded-xl border border-violet-500/40 bg-violet-500/[0.08] py-3 text-sm font-medium text-white transition-all duration-150 hover:border-violet-400/70 hover:bg-violet-500/25 hover:shadow-[0_0_16px_rgba(139,92,246,0.2)] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <svg className="h-4 w-4 text-violet-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              {passkeyLoading ? lg.passkeyValidating : lg.passkeySignIn}
            </button>

            <button
              type="button"
              onClick={handleMicrosoftLogin}
              disabled={oidcLoading}
              className="flex w-full cursor-pointer items-center justify-center gap-4 rounded-xl border border-white/20 bg-white/[0.07] py-3 text-sm font-medium text-white transition-all duration-150 hover:border-white/40 hover:bg-white/20 hover:shadow-[0_0_12px_rgba(255,255,255,0.06)] active:scale-[0.99] disabled:opacity-60"
            >
              <svg className="h-4 w-4" viewBox="0 0 21 21" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 0H0V10H10V0Z" fill="#F25022" />
                <path d="M21 0H11V10H21V0Z" fill="#7FBA00" />
                <path d="M10 11H0V21H10V11Z" fill="#00A4EF" />
                <path d="M21 11H11V21H21V11Z" fill="#FFB900" />
              </svg>
              {oidcLoading ? lg.microsoftRedirecting : lg.microsoftSignIn}
            </button>

            <p className="mt-6 text-center text-[12px] text-gray-600">
              {lg.noAccount}{' '}
              <span className="text-gray-500">{lg.contactAdmin}</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
