import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Cpu } from 'lucide-react'
import { invitesApi } from '../../api/invites'

const STATUS_LABEL: Record<string, string> = {
  pending: 'Invite pending',
  accepted: 'Invite already accepted',
  expired: 'Invite expired',
  revoked: 'Invite revoked',
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
            Back to sign in
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
              Activate invite
            </h1>
            <p
              className="mx-auto mt-2 max-w-sm text-[13px] leading-relaxed tracking-wide text-gray-200"
              style={{ textShadow: '0 1px 8px rgba(0,0,0,0.95)' }}
            >
              Define your name and password to finish workspace access.
            </p>
          </div>

          <div className="login-glass-card w-full rounded-[20px] p-8 sm:p-9">
            <p className="mb-6 text-[13px] text-gray-300">
              Review the invite details, accept the required terms, and activate your account.
            </p>

          {error && (
            <div className="mb-4 rounded-lg border border-red-300/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!tokenFromUrl && (
              <div>
                <label className="mb-1.5 block text-[13px] font-medium text-white">Invite token</label>
                <input
                  type="text"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  required
                  placeholder="Paste the invite token"
                  className="login-glass-input w-full rounded-xl px-4 py-3 font-mono text-sm placeholder-gray-400 outline-none transition-all duration-300"
                />
              </div>
            )}

            {previewLoading && resolvedToken && (
              <div className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-gray-300">
                Validating invite...
              </div>
            )}

            {preview && (
              <div className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-gray-200">
                <p>
                  Workspace: <span className="font-semibold text-white">{preview.org_name}</span>
                </p>
                <p>
                  Email: <span className="font-semibold text-white">{preview.invited_email}</span>
                </p>
                <p>
                  Role: <span className="font-semibold text-white">{preview.role}</span>
                </p>
                <p>
                  Status: <span className="font-semibold text-white">{STATUS_LABEL[preview.status] ?? preview.status}</span>
                </p>
              </div>
            )}

            <div>
              <label className="mb-1.5 block text-[13px] font-medium text-white">Full name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                minLength={2}
                className="login-glass-input w-full rounded-xl px-4 py-3 text-sm placeholder-gray-400 outline-none transition-all duration-300"
                placeholder="Your full name"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-[13px] font-medium text-white">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="login-glass-input w-full rounded-xl px-4 py-3 text-sm placeholder-gray-400 outline-none transition-all duration-300"
                placeholder="Minimum 8 characters"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-[13px] font-medium text-white">Confirm password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                className="login-glass-input w-full rounded-xl px-4 py-3 text-sm placeholder-gray-400 outline-none transition-all duration-300"
                placeholder="Repeat your password"
              />
            </div>

            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-white/20 bg-white/10 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-xs leading-relaxed text-gray-300">
                I have read and accept the{' '}
                <a href="/terms" target="_blank" rel="noopener noreferrer" className="text-violet-300 underline">
                  Terms of Service and Privacy Policy
                </a>{' '}
                required to activate this workspace account.
              </span>
            </label>

            <button
              type="submit"
              disabled={submitting || !resolvedToken || !canAccept || !termsAccepted}
              className="mt-2 w-full rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 py-3.5 text-sm font-medium text-white transition-all duration-300 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] disabled:opacity-60"
            >
              {submitting ? 'Activating access...' : 'Activate access'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-400 transition-colors hover:text-gray-200"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
    </div>
  )
}
