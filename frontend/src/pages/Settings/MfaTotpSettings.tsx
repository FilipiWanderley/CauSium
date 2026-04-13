import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { authApi } from '../../api/auth'

export function MfaTotpSettings() {
  const [code, setCode] = useState('')
  const [step, setStep] = useState<'status' | 'setup' | 'verify' | 'enabled' | 'disable'>('status')
  const [secret, setSecret] = useState('')
  const [otpauthUrl, setOtpauthUrl] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)
  const { data: status, refetch } = useQuery({
    queryKey: ['totp-status'],
    queryFn: () => authApi.getTotpStatus().then((r) => r.data),
  })

  const setupMutation = useMutation({
    mutationFn: () => authApi.setupTotp().then((r) => r.data),
    onSuccess: (data) => {
      setSecret(data.secret)
      setOtpauthUrl(data.otpauth_url)
      setStep('verify')
    },
    onError: (e) => setFeedback((e as Error)?.message ?? 'Erro ao iniciar setup.'),
  })

  const verifyMutation = useMutation({
    mutationFn: () => authApi.verifyTotp({ code }).then((r) => r.data),
    onSuccess: (data) => {
      if (data.valid) {
        setStep('enabled')
        setFeedback('MFA ativado com sucesso!')
        refetch()
      } else {
        setFeedback('Código inválido. Tente novamente.')
      }
    },
    onError: (e) => setFeedback((e as Error)?.message ?? 'Erro ao validar código.'),
  })

  const disableMutation = useMutation({
    mutationFn: () => authApi.disableTotp({ code }).then((r) => r.data),
    onSuccess: () => {
      setStep('status')
      setFeedback('MFA desativado.')
      setCode('')
      refetch()
    },
    onError: (e) => setFeedback((e as Error)?.message ?? 'Erro ao desativar MFA.'),
  })

  useEffect(() => {
    if (status?.enabled) setStep('enabled')
    else setStep('status')
  }, [status])

  return (
    <div className="space-y-4 max-w-lg">
      <h2 className="text-lg font-semibold">Autenticação em Dois Fatores (MFA TOTP)</h2>
      {feedback && <div className="text-sm text-red-600">{feedback}</div>}
      {step === 'status' && (
        <div>
          <p className="mb-2">
            {status?.enabled
              ? 'MFA TOTP está ativado para sua conta.'
              : 'MFA TOTP não está ativado. Recomendado para maior segurança.'}
          </p>
          {status?.enabled ? (
            <button
              className="rounded bg-red-600 px-4 py-2 text-white"
              onClick={() => setStep('disable')}
            >
              Desativar MFA
            </button>
          ) : (
            <button
              className="rounded bg-brand-600 px-4 py-2 text-white"
              onClick={() => setupMutation.mutate()}
              disabled={setupMutation.isPending}
            >
              {setupMutation.isPending ? 'Carregando...' : 'Ativar MFA'}
            </button>
          )}
        </div>
      )}
      {step === 'verify' && (
        <div>
          <p className="mb-2">Escaneie o QR code abaixo no seu app autenticador (Google Authenticator, Authy, etc) ou insira o segredo manualmente.</p>
          <div className="mb-2">
            <QRCodeSVG value={otpauthUrl} size={180} />
          </div>
          <div className="mb-2">
            <span className="font-mono bg-gray-100 px-2 py-1 rounded">{secret}</span>
          </div>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Código do app autenticador"
            className="rounded border px-3 py-2 text-sm"
          />
          <button
            className="ml-2 rounded bg-brand-600 px-4 py-2 text-white"
            onClick={() => verifyMutation.mutate()}
            disabled={verifyMutation.isPending}
          >
            {verifyMutation.isPending ? 'Validando...' : 'Validar Código'}
          </button>
        </div>
      )}
      {step === 'enabled' && (
        <div>
          <p className="mb-2 text-green-700">MFA TOTP está ativado!</p>
          <button
            className="rounded bg-red-600 px-4 py-2 text-white"
            onClick={() => setStep('disable')}
          >
            Desativar MFA
          </button>
        </div>
      )}
      {step === 'disable' && (
        <div>
          <p className="mb-2">Para desativar, digite um código válido do seu app autenticador:</p>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Código do app autenticador"
            className="rounded border px-3 py-2 text-sm"
          />
          <button
            className="ml-2 rounded bg-red-600 px-4 py-2 text-white"
            onClick={() => disableMutation.mutate()}
            disabled={disableMutation.isPending}
          >
            {disableMutation.isPending ? 'Desativando...' : 'Desativar'}
          </button>
        </div>
      )}
    </div>
  )
}
