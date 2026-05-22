import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Cpu, FileText } from 'lucide-react'
import { authApi } from '../../api/auth'
import { useAuth } from '../../hooks/useAuth'

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

        <div className="relative z-10 flex w-full max-w-xl flex-col items-center px-6">
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="fixed left-8 top-8 inline-flex items-center gap-2 text-sm text-gray-400 transition-colors hover:text-white group"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
            Back to sign in
          </button>

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
              Terms of Service Updated
            </h1>
            <p
              className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed tracking-wide text-gray-200"
              style={{ textShadow: '0 1px 8px rgba(0,0,0,0.95)' }}
            >
              Review the updated legal terms and confirm acceptance before continuing to your workspace.
            </p>
          </div>

          <div className="login-glass-card w-full rounded-[20px] p-8 sm:p-9">
            <div className="mb-5 flex items-start gap-3 rounded-xl border border-blue-300/20 bg-blue-500/10 p-4">
              <FileText className="mt-0.5 h-5 w-5 shrink-0 text-blue-200" />
              <div className="text-sm text-blue-100">
                <p className="font-medium">What changed</p>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-blue-100/90">
                  <li>Updated data processing terms in accordance with LGPD requirements</li>
                  <li>Clarified data retention and anonymization policies</li>
                  <li>Added details about your data protection rights</li>
                </ul>
                <p className="mt-3">
                  Full terms are available at{' '}
                  <a href="/legal/terms" className="text-blue-200 underline hover:text-white">
                    /legal/terms
                  </a>
                  . For data protection inquiries, contact our DPO at{' '}
                  <a href="/legal/dpo-contact" className="text-blue-200 underline hover:text-white">
                    /legal/dpo-contact
                  </a>
                  .
                </p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3">
                <input
                  type="checkbox"
                  checked={accepted}
                  onChange={(e) => setAccepted(e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-white/20 bg-white/10 text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm leading-relaxed text-gray-200">
                  I have read and accept the updated Terms of Service and Privacy Policy. I understand
                  that CauSium processes my data in accordance with LGPD (Lei nº 13.709/2018).
                </span>
              </label>

              {error && (
                <div className="rounded-lg border border-red-300/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={!accepted || loading}
                className="mt-2 w-full rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 py-3.5 text-sm font-medium text-white transition-all duration-300 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? 'Processing...' : 'Accept and continue'}
              </button>
            </form>

            <p className="mt-6 text-center text-[12px] text-gray-400">
              CauSium is a decision support system. Your data rights remain protected under LGPD.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}


