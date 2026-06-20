import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Eye, EyeOff } from 'lucide-react'
import { invitesApi } from '../../api/invites'

const STATUS_LABEL: Record<string, string> = {
  pending: 'Invite pending',
  accepted: 'Invite already accepted',
  expired: 'Invite expired',
  revoked: 'Invite revoked',
}

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

export function ActivateInvitePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const tokenFromUrl = searchParams.get('token') ?? ''

  const [token, setToken] = useState(tokenFromUrl)
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const resolvedToken = useMemo(() => token.trim(), [token])

  const { data: preview, isLoading: previewLoading } = useQuery({
    queryKey: ['invite-preview', resolvedToken],
    queryFn: () => invitesApi.preview(resolvedToken).then((r) => r.data),
    enabled: resolvedToken.length > 0,
    retry: false,
  })

  const status = preview?.status
  const canAccept = status === 'pending'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!resolvedToken) {
      setError('Enter the invite token.')
      return
    }
    if (fullName.trim().length < 2) {
      setError('Enter your full name.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    if (!canAccept) {
      setError('This invite can no longer be accepted.')
      return
    }
    if (!termsAccepted) {
      setError('You must accept the Terms of Service to continue.')
      return
    }

    setSubmitting(true)
    try {
      await invitesApi.accept(resolvedToken, {
        full_name: fullName.trim(),
        password,
        terms_accepted: true,
      })
      navigate('/login?activated=success', { replace: true })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Could not activate the invite. Verify that the token is still valid.'
      setError(detail)
    } finally {
      setSubmitting(false)
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
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>

            {/* Headline */}
            <h1 className="text-3xl xl:text-4xl font-semibold text-white leading-tight mb-6">
              Bem-vindo à sua
              <br />
              <span className="text-teal-400">nova workspace</span>.
            </h1>

            {/* Subtitle */}
            <p className="text-slate-300 text-base xl:text-lg leading-relaxed">
              Ative seu convite para começar a gerenciar custos cloud com governança enterprise.
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
              <h2 className="text-2xl font-semibold text-slate-900 mb-2">
                Activate invite
              </h2>
              <p className="text-slate-500 text-sm">
                Define your name and password to finish workspace access.
              </p>
            </div>

            {/* Error */}
            {error && (
              <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Invite token */}
              {!tokenFromUrl && (
                <div>
                  <label htmlFor="token" className="block text-sm font-medium text-slate-700 mb-1.5">
                    Invite token
                  </label>
                  <input
                    id="token"
                    type="text"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    required
                    placeholder="Paste the invite token"
                    className="w-full rounded-lg border border-slate-300 px-4 py-3 font-mono text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                  />
                </div>
              )}

              {/* Preview loading */}
              {previewLoading && resolvedToken && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  Validating invite...
                </div>
              )}

              {/* Invite preview */}
              {preview && (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs text-slate-500 mb-0.5">Workspace</p>
                      <p className="font-semibold text-slate-900">{preview.org_name}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 mb-0.5">Email</p>
                      <p className="font-semibold text-slate-900">{preview.invited_email}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 mb-0.5">Role</p>
                      <p className="font-semibold text-slate-900">{preview.role}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 mb-0.5">Status</p>
                      <p className="font-semibold text-slate-900">{STATUS_LABEL[preview.status] ?? preview.status}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Full name */}
              <div>
                <label htmlFor="full-name" className="block text-sm font-medium text-slate-700 mb-1.5">
                  Full name
                </label>
                <input
                  id="full-name"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  minLength={2}
                  placeholder="Your full name"
                  className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                />
              </div>

              {/* Password */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    placeholder="Minimum 8 characters"
                    className="w-full rounded-lg border border-slate-300 px-4 py-3 pr-11 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    tabIndex={-1}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              {/* Confirm password */}
              <div>
                <label htmlFor="confirm-password" className="block text-sm font-medium text-slate-700 mb-1.5">
                  Confirm password
                </label>
                <input
                  id="confirm-password"
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                  placeholder="Repeat your password"
                  className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                />
              </div>

              {/* Terms */}
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                />
                <span className="text-sm text-slate-600 leading-relaxed">
                  I have read and accept the{' '}
                  <a href="/terms" target="_blank" rel="noopener noreferrer" className="text-teal-600 underline hover:text-teal-700">
                    Terms of Service and Privacy Policy
                  </a>{' '}
                  required to activate this workspace account.
                </span>
              </label>

              {/* Submit */}
              <button
                type="submit"
                disabled={submitting || !resolvedToken || !canAccept || !termsAccepted}
                className="w-full rounded-lg bg-[#0f172a] py-3 text-sm font-medium text-white transition-colors hover:bg-[#1e293b] focus:outline-none focus:ring-2 focus:ring-[#0f172a]/50 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {submitting ? 'Activating access...' : 'Activate access'}
              </button>
            </form>

            {/* Back to login */}
            <div className="mt-6 text-center">
              <Link
                to="/login"
                className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to sign in
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}