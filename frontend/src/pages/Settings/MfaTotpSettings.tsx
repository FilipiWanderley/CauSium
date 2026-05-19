import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { authApi } from '../../api/auth'
import { useI18n } from '../../contexts/I18nContext'

type Step = 'status' | 'setup' | 'enable' | 'backup_codes' | 'enabled' | 'disable' | 'regenerate'

export function MfaTotpSettings() {
  const { t } = useI18n()
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
    onError: (e) => setFeedback({ text: (e as Error)?.message ?? 'Could not start setup.', ok: false }),
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
    onError: (e) => setFeedback({ text: (e as Error)?.message ?? 'Invalid code.', ok: false }),
  })

  const disableMutation = useMutation({
    mutationFn: () => authApi.disableTotp({ code }).then((r) => r.data),
    onSuccess: () => {
      setCode('')
      setFeedback({ text: 'Two-factor authentication disabled.', ok: true })
      refetchStatus()
      setStep('status')
    },
    onError: (e) => setFeedback({ text: (e as Error)?.message ?? 'Could not disable two-factor authentication.', ok: false }),
  })

  const regenerateMutation = useMutation({
    mutationFn: () => authApi.regenerateBackupCodes({ code }).then((r) => r.data),
    onSuccess: (data) => {
      setBackupCodes(data.backup_codes)
      setCode('')
      setStep('backup_codes')
      refetchCount()
    },
    onError: (e) => setFeedback({ text: (e as Error)?.message ?? 'Invalid code.', ok: false }),
  })

  return (
    <div className="space-y-4 max-w-lg">
      <h2 className="text-sm font-semibold text-gray-900">Two-factor authentication (TOTP)</h2>

      {feedback && (
        <div
          className={`rounded-lg border px-3 py-2 text-sm ${
            feedback.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-700'
          }`}
        >
          {feedback.text}
        </div>
      )}

      {step === 'status' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Two-factor authentication is not enabled. Enable it to strengthen access security.
          </p>
          <button
            className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
            onClick={() => { setFeedback(null); setupMutation.mutate() }}
            disabled={setupMutation.isPending}
          >
            {setupMutation.isPending ? t.common.loading : 'Enable 2FA'}
          </button>
        </div>
      )}

      {step === 'setup' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">Preparing setup…</p>
        </div>
      )}

      {step === 'enable' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Scan this QR code with Google Authenticator, Authy, or a compatible app. You can also enter the secret manually.
          </p>
          <div>
            <QRCodeSVG value={otpauthUrl} size={160} />
          </div>
          <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
            <span className="font-mono text-xs text-gray-700 break-all">{secret}</span>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Authenticator code (6 digits)"
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              maxLength={8}
            />
            <button
              className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
              onClick={() => { setFeedback(null); enableMutation.mutate() }}
              disabled={code.length < 6 || enableMutation.isPending}
            >
              {enableMutation.isPending ? 'Enabling…' : 'Enable'}
            </button>
          </div>
        </div>
      )}

      {step === 'backup_codes' && (
        <div className="space-y-3">
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-semibold text-amber-900 mb-1">Save your recovery codes</p>
            <p className="text-xs text-amber-800 mb-3">
              Each code can be used once if you lose access to your authenticator app. They won’t be shown again.
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
              className="mt-3 text-xs text-amber-800 underline"
            >
              Copy all
            </button>
          </div>
          <button
            className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            onClick={() => { setBackupCodes([]); setStep('enabled') }}
          >
            I saved these codes
          </button>
        </div>
      )}

      {step === 'enabled' && (
        <div className="space-y-3">
          <p className="text-sm text-emerald-700 font-medium">Two-factor authentication is enabled.</p>
          {backupCountData && (
            <p className="text-xs text-gray-500">
              Recovery codes remaining:{' '}
              <span className={`font-semibold ${backupCountData.backup_codes_remaining === 0 ? 'text-red-600' : 'text-gray-700'}`}>
                {backupCountData.backup_codes_remaining}
              </span>
              {backupCountData.backup_codes_remaining === 0 && (
                <span className="text-red-600"> — regenerate now</span>
              )}
            </p>
          )}
          <div className="flex gap-2">
            <button
              className="rounded-lg border border-gray-300 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
              onClick={() => { setFeedback(null); setCode(''); setStep('regenerate') }}
            >
              Regenerate recovery codes
            </button>
            <button
              className="rounded-lg border border-red-200 px-3 py-2 text-xs text-red-700 hover:bg-red-50"
              onClick={() => { setFeedback(null); setCode(''); setStep('disable') }}
            >
              Disable 2FA
            </button>
          </div>
        </div>
      )}

      {step === 'regenerate' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">To regenerate, confirm with a code from your authenticator app:</p>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Authenticator code"
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              maxLength={8}
            />
            <button
              className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
              onClick={() => { setFeedback(null); regenerateMutation.mutate() }}
              disabled={code.length < 6 || regenerateMutation.isPending}
            >
              {regenerateMutation.isPending ? 'Generating…' : 'Regenerate'}
            </button>
            <button
              className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setStep('enabled')}
            >
              {t.common.cancel}
            </button>
          </div>
        </div>
      )}

      {step === 'disable' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">To disable, confirm with a code from your authenticator app:</p>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Authenticator code"
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              maxLength={8}
            />
            <button
              className="inline-flex items-center rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-60"
              onClick={() => { setFeedback(null); disableMutation.mutate() }}
              disabled={code.length < 6 || disableMutation.isPending}
            >
              {disableMutation.isPending ? 'Disabling…' : 'Disable'}
            </button>
            <button
              className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setStep('enabled')}
            >
              {t.common.cancel}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
