import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Cloud, ArrowLeft } from 'lucide-react'
import { authApi } from '../../api/auth'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [resetToken, setResetToken] = useState<string | null>(null)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await authApi.forgotPassword(email)
      setResetToken(data.token)
      setSubmitted(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 text-white">
            <Cloud className="h-8 w-8 text-brand-500" />
            <span className="text-2xl font-bold">StratoPulse</span>
          </div>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-2xl">
          {submitted ? (
            <div className="text-center space-y-4">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Check your instructions</h2>
              <p className="text-sm text-gray-500">
                If <span className="font-medium text-gray-700">{email}</span> is registered, you
                will receive password reset instructions.
              </p>

              {resetToken && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-left">
                  <p className="text-xs font-semibold text-blue-700 mb-1">
                    Dev mode — reset link:
                  </p>
                  <Link
                    to={`/reset-password?token=${resetToken}`}
                    className="text-xs text-blue-600 underline break-all"
                  >
                    /reset-password?token={resetToken}
                  </Link>
                  <p className="mt-2 text-xs text-blue-500">
                    In production, this token would be emailed instead of shown here.
                  </p>
                </div>
              )}

              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:text-brand-700"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to sign in
              </Link>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <h2 className="text-xl font-semibold text-gray-900">Reset your password</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Enter your email and we'll send you reset instructions.
                </p>
              </div>

              {error && (
                <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  {error}
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
                    placeholder="you@company.com"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60 transition-colors"
                >
                  {loading ? 'Sending…' : 'Send reset instructions'}
                </button>
              </form>

              <div className="mt-5 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-700"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back to sign in
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
