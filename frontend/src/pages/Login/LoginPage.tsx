import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { Cloud } from 'lucide-react'
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
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 text-white">
            <Cloud className="h-8 w-8 text-brand-500" />
            <span className="text-2xl font-bold">StratoPulse</span>
          </div>
          <p className="mt-2 text-sm text-gray-400">
            Cloud efficiency platform — from detection to action
          </p>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Sign in to your workspace</h2>

          {error && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {resetSuccess && (
            <div className="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
              Password updated successfully. Sign in with your new password.
            </div>
          )}

          {activationSuccess && (
            <div className="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
              Invite accepted successfully. Sign in with your new account.
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="you@company.com"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">Password</label>
                <Link
                  to="/forgot-password"
                  className="text-xs font-medium text-brand-600 hover:text-brand-700"
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
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60 transition-colors"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
            <button
              type="button"
              onClick={handlePasskeyLogin}
              disabled={passkeyLoading}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-60 transition-colors"
            >
              {passkeyLoading ? 'Validating passkey...' : 'Sign in with Passkey'}
            </button>
            <button
              type="button"
              onClick={handleMicrosoftLogin}
              disabled={oidcLoading}
              className="w-full rounded-lg border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-60 transition-colors"
            >
              {oidcLoading ? 'Redirecting to Microsoft...' : 'Sign in with Microsoft'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
