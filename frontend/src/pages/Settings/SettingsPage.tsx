import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi } from '../../api/auth'
import { useAuth } from '../../hooks/useAuth'
import { MfaTotpSettings } from './MfaTotpSettings'
import { AuditLog } from './AuditLog'

export function SettingsPage() {
  const { user, registerCurrentPasskey, logoutAll } = useAuth()
  const queryClient = useQueryClient()

  const [logoutAllState, setLogoutAllState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [registeringPasskey, setRegisteringPasskey] = useState(false)
  const [passkeyMessage, setPasskeyMessage] = useState<string | null>(null)

  const isAdmin = user?.role === 'admin' || user?.role === 'platform_admin'

  const { data: passkeys } = useQuery({
    queryKey: ['auth-passkeys'],
    queryFn: () => authApi.listPasskeys().then((r) => r.data),
  })

  const revokePasskeyMutation = useMutation({
    mutationFn: (passkeyId: string) => authApi.revokePasskey(passkeyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['auth-passkeys'] }),
  })

  const handleLogoutAll = async () => {
    setLogoutAllState('loading')
    try {
      await logoutAll()
      setLogoutAllState('done')
      window.location.href = '/login'
    } catch {
      setLogoutAllState('error')
    }
  }

  const handleRegisterPasskey = async () => {
    setPasskeyMessage(null)
    setRegisteringPasskey(true)
    try {
      await registerCurrentPasskey()
      await queryClient.invalidateQueries({ queryKey: ['auth-passkeys'] })
      setPasskeyMessage('Passkey cadastrada com sucesso')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Falha ao cadastrar passkey'
      setPasskeyMessage(message)
    } finally {
      setRegisteringPasskey(false)
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
        <MfaTotpSettings />
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Passkeys</h2>
        {passkeys && passkeys.length > 0 ? (
          <ul className="space-y-2">
            {passkeys.map((pk: { id: string; created_at: string }) => (
              <li key={pk.id} className="flex items-center justify-between text-sm text-gray-600">
                <span>Cadastrada em {new Date(pk.created_at).toLocaleDateString('pt-BR')}</span>
                <button
                  onClick={() => revokePasskeyMutation.mutate(pk.id)}
                  disabled={revokePasskeyMutation.isPending}
                  className="text-red-600 hover:underline text-xs disabled:opacity-50"
                >
                  Revogar
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">Nenhuma passkey cadastrada.</p>
        )}
        <button
          onClick={handleRegisterPasskey}
          disabled={registeringPasskey}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white font-medium hover:bg-blue-700 disabled:opacity-60"
        >
          {registeringPasskey ? 'Cadastrando...' : 'Cadastrar nova passkey'}
        </button>
        {passkeyMessage && (
          <p className={`text-xs ${passkeyMessage.includes('sucesso') ? 'text-green-600' : 'text-red-600'}`}>
            {passkeyMessage}
          </p>
        )}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Sessões</h2>
        <div className="flex flex-col gap-2">
          <button
            onClick={handleLogoutAll}
            className="w-fit rounded bg-red-600 px-4 py-2 text-white font-semibold shadow hover:bg-red-700 disabled:opacity-60"
            disabled={logoutAllState === 'loading'}
          >
            {logoutAllState === 'loading' ? 'Encerrando sessões...' : 'Encerrar todas as sessões (logout global)'}
          </button>
          {logoutAllState === 'done' && (
            <span className="text-green-600 text-xs">Todas as sessões foram encerradas. Faça login novamente.</span>
          )}
          {logoutAllState === 'error' && (
            <span className="text-red-600 text-xs">Erro ao encerrar sessões. Tente novamente.</span>
          )}
        </div>
      </div>

      {isAdmin && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <AuditLog />
        </div>
      )}
    </div>
  )
}
