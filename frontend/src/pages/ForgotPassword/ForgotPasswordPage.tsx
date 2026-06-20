import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle } from 'lucide-react'
import { authApi } from '../../api/auth'
import { useI18n } from '../../contexts/I18nContext'

// CauSium Enterprise Logo SVG
function CausiumLogo() {
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
          fill="#0d9488"
          opacity="0.9"
        />
        <rect x="1.5" y="19" width="2" height="6" rx="0.5" fill="#0d9488" opacity="0.7" />
        <rect x="5" y="20" width="1.5" height="5" rx="0.5" fill="#0d9488" opacity="0.6" />
        <rect x="8" y="19" width="2" height="6" rx="0.5" fill="#0d9488" opacity="0.7" />
      </g>
      <text x="22" y="21" fontFamily="system-ui, -apple-system, sans-serif" fontSize="18" fontWeight="600" fill="#0f172a">
        CauSium
      </text>
    </svg>
  )
}

export function ForgotPasswordPage() {
  const { t } = useI18n()
  const fp = t.forgotPassword
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.forgotPassword(email)
      setSubmitted(true)
    } catch {
      // Não revela se o e-mail existe ou não por segurança
      setSubmitted(true)
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
              <CausiumLogo />
            </div>

            {/* Headline */}
            <h1 className="text-3xl xl:text-4xl font-semibold text-white leading-tight mb-6">
              Recupere o acesso
              <br />
              com <span className="text-teal-400">segurança</span>.
            </h1>

            {/* Subtitle */}
            <p className="text-slate-300 text-base xl:text-lg leading-relaxed">
              Redefinição de senha protegida por tokens de uso único e políticas de segurança enterprise.
            </p>
          </div>
        </div>

        {/* RIGHT COLUMN - Form */}
        <div className="flex w-full lg:w-1/2 xl:w-[45%] flex-col justify-center px-6 py-12 sm:px-8 lg:px-16 xl:px-20">
          <div className="w-full max-w-md mx-auto">
            {/* Mobile logo */}
            <div className="lg:hidden mb-8 text-center">
              <CausiumLogo />
            </div>

            {/* Header */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-slate-900 mb-2">
                {fp.title}
              </h2>
              <p className="text-slate-500 text-sm">
                Insira o e-mail associado à sua conta e enviaremos um link seguro para redefinir sua senha.
              </p>
            </div>

            {/* Success state */}
            {submitted ? (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
                <div className="mx-auto w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
                  <CheckCircle className="w-6 h-6 text-emerald-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  {fp.successTitle}
                </h3>
                <p className="text-sm text-slate-600 mb-6">
                  {fp.successMessage.replace('{{email}}', email)}
                </p>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 text-sm font-medium text-teal-600 hover:text-teal-700 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  {fp.backToSignIn}
                </Link>
              </div>
            ) : (
              <>
                {error && (
                  <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {error}
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                  {/* Email */}
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
                      {fp.emailLabel}
                    </label>
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      autoComplete="email"
                      placeholder={fp.emailPlaceholder}
                      className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                    />
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full rounded-lg bg-[#0f172a] py-3 text-sm font-medium text-white transition-colors hover:bg-[#1e293b] focus:outline-none focus:ring-2 focus:ring-[#0f172a]/50 disabled:opacity-60"
                  >
                    {loading ? fp.submitting : fp.submit}
                  </button>
                </form>

                {/* Back to login */}
                <div className="mt-6 text-center">
                  <Link
                    to="/login"
                    className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    {fp.backToSignIn}
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
