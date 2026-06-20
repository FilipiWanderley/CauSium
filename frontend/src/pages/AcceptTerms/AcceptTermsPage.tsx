import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText } from 'lucide-react'
import { authApi } from '../../api/auth'
import { useAuth } from '../../hooks/useAuth'

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

export function AcceptTermsPage() {
  const { refreshUser } = useAuth()
  const navigate = useNavigate()

  const [accepted, setAccepted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!accepted) return
    setError('')
    setLoading(true)
    try {
      const { data: updatedUser } = await authApi.acceptTerms()
      await refreshUser(updatedUser)
      navigate('/app/dashboard', { replace: true })
    } catch {
      setError('Could not record your acceptance. Please try again.')
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
              <FileText className="w-8 h-8 text-teal-400" />
            </div>

            {/* Headline */}
            <h1 className="text-3xl xl:text-4xl font-semibold text-white leading-tight mb-6">
              Termos de uso
              <br />
              <span className="text-teal-400">atualizados</span>.
            </h1>

            {/* Subtitle */}
            <p className="text-slate-300 text-base xl:text-lg leading-relaxed">
              Revise os termos legais atualizados e confirme a aceitação antes de continuar ao seu workspace.
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

            {/* Header */}
            <div className="mb-8">
              <div className="w-12 h-12 rounded-xl bg-[#0d9488]/10 flex items-center justify-center mb-4">
                <FileText className="w-6 h-6 text-teal-600" />
              </div>
              <h2 className="text-2xl font-semibold text-slate-900 mb-2">
                Terms of Service Updated
              </h2>
              <p className="text-slate-500 text-sm">
                Review the updated legal terms and confirm acceptance before continuing to your workspace.
              </p>
            </div>

            {/* Info box */}
            <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50 p-4">
              <p className="text-sm font-medium text-blue-900 mb-2">What changed</p>
              <ul className="text-sm text-blue-800 space-y-1.5 list-disc list-inside">
                <li>Updated data processing terms in accordance with LGPD requirements</li>
                <li>Clarified data retention and anonymization policies</li>
                <li>Added details about your data protection rights</li>
              </ul>
              <p className="mt-3 text-sm text-blue-800">
                Full terms are available at{' '}
                <a href="/legal/terms" className="text-blue-700 underline hover:text-blue-900">
                  /legal/terms
                </a>
                . For data protection inquiries, contact our DPO at{' '}
                <a href="/legal/dpo-contact" className="text-blue-700 underline hover:text-blue-900">
                  /legal/dpo-contact
                </a>
                .
              </p>
            </div>

            {error && (
              <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Checkbox */}
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={accepted}
                  onChange={(e) => setAccepted(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                />
                <span className="text-sm text-slate-600 leading-relaxed">
                  I have read and accept the updated Terms of Service and Privacy Policy. I understand
                  that CauSium processes my data in accordance with LGPD (Lei nº 13.709/2018).
                </span>
              </label>

              {/* Submit */}
              <button
                type="submit"
                disabled={!accepted || loading}
                className="w-full rounded-lg bg-[#0f172a] py-3 text-sm font-medium text-white transition-colors hover:bg-[#1e293b] focus:outline-none focus:ring-2 focus:ring-[#0f172a]/50 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? 'Processing...' : 'Accept and continue'}
              </button>
            </form>

            {/* Footer */}
            <p className="mt-6 text-center text-xs text-slate-400">
              CauSium is a decision support system. Your data rights remain protected under LGPD.
            </p>

            {/* Back to login */}
            <div className="mt-4 text-center">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to sign in
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
