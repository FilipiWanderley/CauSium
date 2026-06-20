import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'

// CauSium Enterprise Logo SVG - Navy/Teal variant
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
      {/* Cloud/Gov symbol - simplified */}
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
      {/* Text */}
      <text x="22" y="21" fontFamily="system-ui, -apple-system, sans-serif" fontSize="18" fontWeight="600" fill={textColor}>
        CauSium
      </text>
    </svg>
  )
}

// Icon components
function CloudIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
    </svg>
  )
}

function ShieldIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  )
}

function LockIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  )
}

// Enterprise illustration - Control Tower / Cloud connections
function EnterpriseIllustration() {
  return (
    <svg width="280" height="200" viewBox="0 0 280 200" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-auto max-w-[280px] mx-auto">
      {/* Central hub */}
      <circle cx="140" cy="100" r="30" fill="#0d9488" opacity="0.15" />
      <circle cx="140" cy="100" r="20" fill="#0d9488" opacity="0.25" />
      <circle cx="140" cy="100" r="10" fill="#0d9488" />

      {/* AWS */}
      <circle cx="50" cy="60" r="18" fill="#1e3a5f" opacity="0.8" />
      <text x="50" y="64" textAnchor="middle" fill="white" fontSize="8" fontWeight="600">AWS</text>

      {/* Azure */}
      <circle cx="230" cy="60" r="18" fill="#0078d4" opacity="0.8" />
      <text x="230" y="64" textAnchor="middle" fill="white" fontSize="8" fontWeight="600">Azure</text>

      {/* GCP */}
      <circle cx="50" cy="150" r="18" fill="#4285f4" opacity="0.8" />
      <text x="50" y="154" textAnchor="middle" fill="white" fontSize="8" fontWeight="600">GCP</text>

      {/* Security shield */}
      <circle cx="230" cy="150" r="18" fill="#0f172a" opacity="0.8" />
      <text x="230" y="154" textAnchor="middle" fill="#0d9488" fontSize="8" fontWeight="600">LGPD</text>

      {/* Connection lines */}
      <line x1="68" y1="60" x2="120" y2="95" stroke="#0d9488" strokeWidth="1" strokeDasharray="4 2" opacity="0.5" />
      <line x1="212" y1="60" x2="160" y2="95" stroke="#0d9488" strokeWidth="1" strokeDasharray="4 2" opacity="0.5" />
      <line x1="68" y1="150" x2="120" y2="105" stroke="#0d9488" strokeWidth="1" strokeDasharray="4 2" opacity="0.5" />
      <line x1="212" y1="150" x2="160" y2="105" stroke="#0d9488" strokeWidth="1" strokeDasharray="4 2" opacity="0.5" />

      {/* Data flow dots */}
      <circle cx="94" cy="77" r="2" fill="#0d9488" opacity="0.8">
        <animate attributeName="cx" values="94;140;94" dur="3s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.8;0.2;0.8" dur="3s" repeatCount="indefinite" />
      </circle>
      <circle cx="186" cy="77" r="2" fill="#0d9488" opacity="0.8">
        <animate attributeName="cx" values="186;140;186" dur="3s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.8;0.2;0.8" dur="3s" repeatCount="indefinite" />
      </circle>
      <circle cx="94" cy="123" r="2" fill="#0d9488" opacity="0.8">
        <animate attributeName="cx" values="94;140;94" dur="3.5s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.8;0.2;0.8" dur="3.5s" repeatCount="indefinite" />
      </circle>
      <circle cx="186" cy="123" r="2" fill="#0d9488" opacity="0.8">
        <animate attributeName="cx" values="186;140;186" dur="3.5s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.8;0.2;0.8" dur="3.5s" repeatCount="indefinite" />
      </circle>
    </svg>
  )
}

export function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()
  const lg = t.login
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [resetSuccess, setResetSuccess] = useState(false)
  const [activationSuccess, setActivationSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('reset') === 'success') {
      setResetSuccess(true)
      setError('')
    }
    if (params.get('activated') === 'success') {
      setActivationSuccess(true)
      setError('')
    }
  }, [])

  if (isAuthenticated) return <Navigate to="/app/dashboard" replace />

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/app/dashboard')
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

  return (
    <div className="min-h-screen w-full bg-slate-50">
      <div className="flex min-h-screen">
        {/* LEFT COLUMN - Enterprise branding (hidden on mobile) */}
        <div className="hidden lg:flex lg:w-1/2 xl:w-[55%] flex-col justify-between bg-[#0f172a] p-10 xl:p-16 relative overflow-hidden">
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
          <div className="relative z-10">
            {/* Logo */}
            <div className="mb-12">
              <CausiumLogo variant="light" />
            </div>

            {/* Headline */}
            <h1 className="text-3xl xl:text-4xl font-semibold text-white leading-tight mb-6">
              Govern cloud with confidence.
              <br />
              Optimize with <span className="text-teal-400">control</span>.
            </h1>

            {/* Subtitle */}
            <p className="text-slate-300 text-base xl:text-lg leading-relaxed max-w-lg mb-10">
              Enterprise FinOps and cloud governance for multi-cloud visibility, auditability, and secure access.
            </p>

            {/* Benefits */}
            <div className="space-y-5">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[#0d9488]/15 flex items-center justify-center text-teal-400">
                  <CloudIcon />
                </div>
                <div>
                  <h3 className="text-white font-medium text-sm mb-1">Multi-cloud visibility</h3>
                  <p className="text-slate-400 text-sm">Unified view across AWS, Azure, and GCP.</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[#0d9488]/15 flex items-center justify-center text-teal-400">
                  <ShieldIcon />
                </div>
                <div>
                  <h3 className="text-white font-medium text-sm mb-1">Governed and auditable</h3>
                  <p className="text-slate-400 text-sm">Policy-driven guardrails and full audit trails.</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[#0d9488]/15 flex items-center justify-center text-teal-400">
                  <LockIcon />
                </div>
                <div>
                  <h3 className="text-white font-medium text-sm mb-1">Secure enterprise access</h3>
                  <p className="text-slate-400 text-sm">Role-based access with controlled authentication.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Illustration */}
          <div className="relative z-10 my-8">
            <EnterpriseIllustration />
          </div>

          {/* Footer badges */}
          <div className="relative z-10 mt-auto">
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-3">
              Enterprise-grade security and compliance
            </p>
            <div className="flex items-center gap-4 text-slate-500 text-xs">
              <span className="flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <path d="M9 12l2 2 4-4" />
                </svg>
                SOC 2 Type II
              </span>
              <span className="text-slate-600">·</span>
              <span>ISO 27001</span>
              <span className="text-slate-600">·</span>
              <span className="text-teal-400/80">LGPD Ready</span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN - Login form */}
        <div className="flex w-full lg:w-1/2 xl:w-[45%] flex-col justify-center px-6 py-12 sm:px-8 lg:px-16 xl:px-20">
          <div className="w-full max-w-md mx-auto">
            {/* Mobile logo */}
            <div className="lg:hidden mb-8 text-center">
              <div className="inline-flex items-center gap-2">
                <CausiumLogo variant="dark" />
              </div>
            </div>

            {/* Header */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-slate-900 mb-2">
                {lg.welcomeBack}
              </h2>
              <p className="text-slate-500 text-sm">
                Securely access your enterprise dashboard.
              </p>
            </div>

            {/* Success/Error messages */}
            {error && (
              <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}
            {resetSuccess && (
              <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                Password updated successfully. Sign in with your new password.
              </div>
            )}
            {activationSuccess && (
              <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                Invite accepted successfully. Sign in with your new account.
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
                  {lg.emailLabel}
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  placeholder={lg.emailPlaceholder}
                  className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                />
              </div>

              {/* Password */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label htmlFor="password" className="block text-sm font-medium text-slate-700">
                    {lg.passwordLabel}
                  </label>
                  <Link
                    to="/forgot-password"
                    className="text-sm text-teal-600 hover:text-teal-700 transition-colors"
                  >
                    {lg.forgotPassword}
                  </Link>
                </div>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    placeholder={lg.passwordPlaceholder}
                    className="w-full rounded-lg border border-slate-300 px-4 py-3 pr-11 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    tabIndex={-1}
                    aria-label={showPassword ? lg.hidePassword : lg.showPassword}
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              {/* Submit button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-[#0f172a] py-3 text-sm font-medium text-white transition-colors hover:bg-[#1e293b] focus:outline-none focus:ring-2 focus:ring-[#0f172a]/50 disabled:opacity-60"
              >
                {loading ? lg.signingIn : lg.signIn}
              </button>
            </form>

            {/* Admin message */}
            <p className="mt-6 text-center text-sm text-slate-500">
              {lg.firstAccessHint}
            </p>

            {/* Security note */}
            <div className="mt-8 pt-6 border-t border-slate-200">
              <div className="flex items-center gap-2 text-xs text-slate-400 justify-center">
                <LockIcon />
                <span>Your access is protected with encrypted credentials, role-based permissions and enterprise audit controls.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
