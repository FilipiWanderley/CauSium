import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'

export function LoginPage() {
  const { login, loginWithPasskey, isAuthenticated } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [resetSuccess, setResetSuccess] = useState(false)
  const [activationSuccess, setActivationSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const [passkeyLoading, setPasskeyLoading] = useState(false)
  const [oidcLoading, setOidcLoading] = useState(false)
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || '', [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const oidcError = params.get('oidc_error')
    if (oidcError) setError(`OIDC falhou: ${oidcError}`)
    if (params.get('reset') === 'success') {
      setResetSuccess(true)
      setError('')
    }
    if (params.get('activated') === 'success') {
      setActivationSuccess(true)
      setError('')
    }
  }, [])

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
    } catch {
      setError('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  const handlePasskeyLogin = async () => {
    if (!email) {
      setError('Informe seu e-mail para login com passkey')
      return
    }
    setError('')
    setPasskeyLoading(true)
    try {
      await loginWithPasskey(email)
    } catch {
      setError('Falha no login com passkey. Verifique se já cadastrou sua chave.')
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
          background: rgba(255, 255, 255, 0.08);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.2);
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 40px rgba(99, 102, 241, 0.05);
        }
        .login-glass-input {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .login-glass-input:focus {
          background: rgba(255, 255, 255, 0.05);
          border-color: #8b5cf6;
          box-shadow: 0 0 0 1px #8b5cf6, 0 0 15px rgba(139, 92, 246, 0.3);
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

        <div className="relative z-10 flex w-full max-w-md flex-col items-center px-6">
          <Link
            to="/"
            className="fixed left-8 top-8 inline-flex items-center gap-2 text-sm text-gray-400 transition-colors hover:text-white group"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
            Voltar
          </Link>

          <div className="mb-8 w-full text-center">
            <h1 className="mb-2 text-[28px] font-bold tracking-[0.2em] text-white">CAUSIUM</h1>
            <p className="text-[13px] tracking-wide text-gray-400">
              Cloud efficiency platform — from detection to action
            </p>
          </div>

          <div className="login-glass-card w-full rounded-[20px] p-8">
            <h2 className="mb-6 text-[19px] font-medium text-white">Sign in to your workspace</h2>

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
                <label className="mb-1.5 block text-[13px] font-medium text-gray-300">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  className="login-glass-input w-full rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition-all duration-300"
                  placeholder="cliente.demo@causium.io"
                />
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <label className="block text-[13px] font-medium text-gray-300">Password</label>
                  <Link
                    to="/forgot-password"
                    className="text-[13px] text-violet-300 transition-colors hover:text-violet-400"
                  >
                    Forgot password?
                  </Link>
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="login-glass-input w-full rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition-all duration-300"
                  placeholder="••••••••••••"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="mt-2 w-full rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 py-3.5 text-sm font-medium text-white transition-all duration-300 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] disabled:opacity-60"
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>

            <div className="relative my-6 flex items-center">
              <div className="flex-grow border-t border-white/10" />
              <span className="mx-4 flex-shrink-0 text-[13px] text-gray-500">or continue with</span>
              <div className="flex-grow border-t border-white/10" />
            </div>

            <button
              type="button"
              onClick={handlePasskeyLogin}
              disabled={passkeyLoading}
              className="mb-3 flex w-full items-center justify-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.03] py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-white/[0.08] disabled:opacity-60"
            >
              <svg className="h-4 w-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              {passkeyLoading ? 'Validating passkey...' : 'Sign in with Passkey'}
            </button>

            <button
              type="button"
              onClick={handleMicrosoftLogin}
              disabled={oidcLoading}
              className="flex w-full items-center justify-center gap-2.5 rounded-xl border border-white/[0.15] bg-white/[0.06] py-3 text-sm font-medium text-white transition-all duration-300 hover:border-white/[0.25] hover:bg-white/[0.12] disabled:opacity-60"
            >
              <svg className="h-4 w-4" viewBox="0 0 21 21" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 0H0V10H10V0Z" fill="#F25022" />
                <path d="M21 0H11V10H21V0Z" fill="#7FBA00" />
                <path d="M10 11H0V21H10V11Z" fill="#00A4EF" />
                <path d="M21 11H11V21H21V11Z" fill="#FFB900" />
              </svg>
              {oidcLoading ? 'Redirecting to Microsoft...' : 'Sign in with Microsoft'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
