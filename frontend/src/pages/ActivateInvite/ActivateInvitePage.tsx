import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Cloud } from 'lucide-react'
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
      setError('Informe o token de convite.')
      return
    }
    if (fullName.trim().length < 2) {
      setError('Informe seu nome completo.')
      return
    }
    if (password.length < 8) {
      setError('A senha deve ter ao menos 8 caracteres.')
      return
    }
    if (password !== confirmPassword) {
      setError('As senhas nao coincidem.')
      return
    }
    if (!canAccept) {
      setError('Este convite nao pode mais ser aceito.')
      return
    }
    if (!termsAccepted) {
      setError('Você precisa aceitar os Termos de Uso para continuar.')
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
        'Nao foi possivel ativar o convite. Verifique se o token ainda e valido.'
      setError(detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 text-white">
            <Cloud className="h-8 w-8 text-brand-500" />
            <span className="text-2xl font-bold">CauSium</span>
          </div>
          <p className="mt-2 text-sm text-gray-400">Ative seu acesso ao workspace</p>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Ativar convite</h2>
          <p className="text-sm text-gray-500 mb-6">Defina seu nome e senha para concluir o acesso.</p>

          {error && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!tokenFromUrl && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Token de convite</label>
                <input
                  type="text"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  required
                  placeholder="Cole o token recebido"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono"
                />
              </div>
            )}

            {previewLoading && resolvedToken && (
              <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-600">
                Validando convite...
              </div>
            )}

            {preview && (
              <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-700">
                <p>
                  Workspace: <span className="font-semibold">{preview.org_name}</span>
                </p>
                <p>
                  E-mail: <span className="font-semibold">{preview.invited_email}</span>
                </p>
                <p>
                  Perfil: <span className="font-semibold">{preview.role}</span>
                </p>
                <p>
                  Status: <span className="font-semibold">{STATUS_LABEL[preview.status] ?? preview.status}</span>
                </p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome completo</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                minLength={2}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="Seu nome"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="Min. 8 caracteres"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar senha</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="Repita a senha"
              />
            </div>

            <label className="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-xs text-gray-600">
                Li e aceito os{' '}
                <a href="/terms" target="_blank" rel="noopener noreferrer" className="text-brand-600 underline">
                  Termos de Uso e Política de Privacidade
                </a>{' '}
                (obrigatório — LGPD)
              </span>
            </label>

            <button
              type="submit"
              disabled={submitting || !resolvedToken || !canAccept || !termsAccepted}
              className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60 transition-colors"
            >
              {submitting ? 'Ativando...' : 'Ativar acesso'}
            </button>
          </form>

          <div className="mt-5 text-center">
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="h-4 w-4" />
              Voltar para login
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
