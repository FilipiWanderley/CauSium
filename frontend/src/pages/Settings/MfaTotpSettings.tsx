import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { authApi } from '../../api/auth'

type Step = 'status' | 'setup' | 'enable' | 'backup_codes' | 'enabled' | 'disable' | 'regenerate'

export function MfaTotpSettings() {
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')
  const [step, setStep] = useState<Step>('status')
  const [secret, setSecret] = useState('')
  const [otpauthUrl, setOtpauthUrl] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [feedback, setFeedback] = useState<{ text: string; ok: boolean } | null>(null)

  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ['totp-status'],
    queryFn: () => authApi.getTotpStatus().then((r) => r.data),
  })

  const { data: backupCountData, refetch: refetchCount } = useQuery({
    queryKey: ['totp-backup-count'],
    queryFn: () => authApi.getBackupCodesCount().then((r) => r.data),
    enabled: statusData?.enabled === true,
  })

  useEffect(() => {
    if (statusData?.enabled) {
      // Don't interrupt backup_codes display after just enabling MFA
      if (step !== 'backup_codes') setStep('enabled')
    } else if (step !== 'setup' && step !== 'enable' && step !== 'backup_codes') {
      setStep('status')
    }
  }, [statusData?.enabled])

  const setupMutation = useMutation({
    mutationFn: () => authApi.setupTotp().then((r) => r.data),
    onSuccess: (data) => {
      setSecret(data.secret)
      setOtpauthUrl(data.otpauth_url)
      setCode('')
      setStep('enable')
    },
    onError: (e) => setFeedback({ text: (e as Error)?.message ?? 'Erro ao iniciar setup.', ok: false }),
  })

  const enableMutation = useMutation({
    mutationFn: () => authApi.enableTotp({ code }).then((r) => r.data),
    onSuccess: (data) => {
      setBackupCodes(data.backup_codes)
      setCode('')
      setStep('backup_codes')
      refetchStatus()
      queryClient.invalidateQueries({ queryKey: ['totp-backup-count'] })
    },
    onError: (e) => setFeedback({ text: (e as Error)?.message ?? 'Código inválido.', ok: false }),
  })

  const disableMutation = useMutation({
    mutationFn: () => authApi.disableTotp({ code }).then((r) => r.data),
    onSuccess: () => {
      setCode('')
      setFeedback({ text: 'MFA desativado.', ok: true })
      refetchStatus()
      setStep('status')
    },
    onError: (e) => setFeedback({ text: (e as Error)?.message ?? 'Erro ao desativar MFA.', ok: false }),
  })

  const regenerateMutation = useMutation({
    mutationFn: () => authApi.regenerateBackupCodes({ code }).then((r) => r.data),
    onSuccess: (data) => {
      setBackupCodes(data.backup_codes)
      setCode('')
      setStep('backup_codes')
      refetchCount()
    },
    onError: (e) => setFeedback({ text: (e as Error)?.message ?? 'Código inválido.', ok: false }),
  })

  return (
    <div className="space-y-4 max-w-lg">
      <h2 className="text-sm font-semibold text-gray-900">Autenticação em Dois Fatores (MFA TOTP)</h2>

      {feedback && (
        <div className={`text-sm ${feedback.ok ? 'text-green-600' : 'text-red-600'}`}>{feedback.text}</div>
      )}

      {step === 'status' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">MFA TOTP não está ativado. Recomendado para maior segurança.</p>
          <button
            className="rounded bg-brand-600 px-4 py-2 text-sm text-white font-medium hover:bg-brand-700 disabled:opacity-60"
            onClick={() => { setFeedback(null); setupMutation.mutate() }}
            disabled={setupMutation.isPending}
          >
            {setupMutation.isPending ? 'Carregando...' : 'Ativar MFA'}
          </button>
        </div>
      )}

      {step === 'setup' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">Preparando configuração...</p>
        </div>
      )}

      {step === 'enable' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Escaneie o QR code no Google Authenticator, Authy ou similar. Ou insira o segredo manualmente.
          </p>
          <div>
            <QRCodeSVG value={otpauthUrl} size={160} />
          </div>
          <div className="rounded bg-gray-50 border border-gray-200 px-3 py-1.5">
            <span className="font-mono text-xs text-gray-700 break-all">{secret}</span>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Código do app (6 dígitos)"
              className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              maxLength={8}
            />
            <button
              className="rounded bg-brand-600 px-4 py-2 text-sm text-white font-medium hover:bg-brand-700 disabled:opacity-60"
              onClick={() => { setFeedback(null); enableMutation.mutate() }}
              disabled={code.length < 6 || enableMutation.isPending}
            >
              {enableMutation.isPending ? 'Ativando...' : 'Ativar'}
            </button>
          </div>
        </div>
      )}

      {step === 'backup_codes' && (
        <div className="space-y-3">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-semibold text-amber-800 mb-1">Guarde estes códigos de recuperação</p>
            <p className="text-xs text-amber-700 mb-3">
              Cada código pode ser usado uma única vez se você perder acesso ao seu app autenticador.
              Eles não serão mostrados novamente.
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {backupCodes.map((c) => (
                <span key={c} className="font-mono text-sm bg-white border border-amber-200 rounded px-2 py-1 text-center">
                  {c}
                </span>
              ))}
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(backupCodes.join('\n'))}
              className="mt-3 text-xs text-amber-700 underline"
            >
              Copiar todos
            </button>
          </div>
          <button
            className="rounded bg-brand-600 px-4 py-2 text-sm text-white font-medium hover:bg-brand-700"
            onClick={() => { setBackupCodes([]); setStep('enabled') }}
          >
            Confirmar que salvei os códigos
          </button>
        </div>
      )}

      {step === 'enabled' && (
        <div className="space-y-3">
          <p className="text-sm text-green-700 font-medium">MFA TOTP está ativado.</p>
          {backupCountData && (
            <p className="text-xs text-gray-500">
              Códigos de recuperação restantes:{' '}
              <span className={`font-semibold ${backupCountData.backup_codes_remaining === 0 ? 'text-red-600' : 'text-gray-700'}`}>
                {backupCountData.backup_codes_remaining}
              </span>
              {backupCountData.backup_codes_remaining === 0 && (
                <span className="text-red-600"> — regenere agora!</span>
              )}
            </p>
          )}
          <div className="flex gap-2">
            <button
              className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
              onClick={() => { setFeedback(null); setCode(''); setStep('regenerate') }}
            >
              Regenerar códigos de recuperação
            </button>
            <button
              className="rounded border border-red-200 px-3 py-1.5 text-xs text-red-700 hover:bg-red-50"
              onClick={() => { setFeedback(null); setCode(''); setStep('disable') }}
            >
              Desativar MFA
            </button>
          </div>
        </div>
      )}

      {step === 'regenerate' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">Para regenerar, confirme com um código do seu app autenticador:</p>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Código do app"
              className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              maxLength={8}
            />
            <button
              className="rounded bg-brand-600 px-4 py-2 text-sm text-white font-medium hover:bg-brand-700 disabled:opacity-60"
              onClick={() => { setFeedback(null); regenerateMutation.mutate() }}
              disabled={code.length < 6 || regenerateMutation.isPending}
            >
              {regenerateMutation.isPending ? 'Gerando...' : 'Regenerar'}
            </button>
            <button
              className="rounded border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
              onClick={() => setStep('enabled')}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {step === 'disable' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">Para desativar, confirme com um código do seu app autenticador:</p>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Código do app"
              className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              maxLength={8}
            />
            <button
              className="rounded bg-red-600 px-4 py-2 text-sm text-white font-medium hover:bg-red-700 disabled:opacity-60"
              onClick={() => { setFeedback(null); disableMutation.mutate() }}
              disabled={code.length < 6 || disableMutation.isPending}
            >
              {disableMutation.isPending ? 'Desativando...' : 'Desativar'}
            </button>
            <button
              className="rounded border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
              onClick={() => setStep('enabled')}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
