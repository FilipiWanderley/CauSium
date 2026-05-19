import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Cloud, FileText } from 'lucide-react'
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
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-lg space-y-6">
        <div className="flex flex-col items-center gap-2">
          <Cloud className="h-10 w-10 text-brand-600" />
          <h1 className="text-2xl font-semibold text-gray-900">Terms of Service Updated</h1>
          <p className="text-center text-sm text-gray-600">
            We have updated our Terms of Service and Privacy Policy. Please review and accept the
            updated terms to continue using CauSium.
          </p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-start gap-3 rounded-lg border border-blue-100 bg-blue-50 p-4">
            <FileText className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
            <div className="text-sm text-blue-800">
              <p className="font-medium">What changed:</p>
              <ul className="mt-1 list-disc pl-4 space-y-1">
                <li>Updated data processing terms in accordance with LGPD requirements</li>
                <li>Clarified data retention and anonymization policies</li>
                <li>Added details about your data protection rights</li>
              </ul>
              <p className="mt-2">
                Full terms are available at{' '}
                <a href="/legal/terms" className="underline hover:text-blue-900">
                  /legal/terms
                </a>
                . For data protection inquiries, contact our DPO at{' '}
                <a href="/legal/dpo-contact" className="underline hover:text-blue-900">
                  /legal/dpo-contact
                </a>
                .
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-sm text-gray-700">
                I have read and accept the updated Terms of Service and Privacy Policy. I understand
                that CauSium processes my data in accordance with LGPD (Lei nº 13.709/2018).
              </span>
            </label>

            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}

            <button
              type="submit"
              disabled={!accepted || loading}
              className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Processing...' : 'Accept and Continue'}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-gray-500">
          CauSium — Decision Support System. Your data rights are protected under LGPD.
        </p>
      </div>
    </div>
  )
}
