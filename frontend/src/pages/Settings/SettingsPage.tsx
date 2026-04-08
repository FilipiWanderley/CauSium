import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cloudAccountsApi } from '../../api/cloudAccounts'
import { ledgerApi } from '../../api/ledger'
import { opportunitiesApi } from '../../api/opportunities'
import { authApi } from '../../api/auth'
import { invitesApi, type InviteOut, type InviteRole } from '../../api/invites'
import { Plus, Trash2, RefreshCw, Activity, Zap } from 'lucide-react'
import { format, subDays } from 'date-fns'
import type { CloudAccount } from '../../types'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'

export function SettingsPage() {
  const { user, registerCurrentPasskey } = useAuth()
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [form, setForm] = useState({ external_id: '', display_name: '', tenant_id: '' })
  const [syncingId, setSyncingId] = useState<string | null>(null)
  const [generatingId, setGeneratingId] = useState<string | null>(null)
  const [registeringPasskey, setRegisteringPasskey] = useState(false)
  const [passkeyMessage, setPasskeyMessage] = useState<string | null>(null)
  const [inviteForm, setInviteForm] = useState({ email: '', role: 'viewer' as InviteRole, expiresInDays: 7 })
  const [inviteFeedback, setInviteFeedback] = useState<string | null>(null)

  const { data: accounts, isLoading } = useQuery({
    queryKey: ['cloud-accounts'],
    queryFn: () => cloudAccountsApi.list().then((r) => r.data),
  })

  const { data: passkeys } = useQuery({
    queryKey: ['auth-passkeys'],
    queryFn: () => authApi.listPasskeys().then((r) => r.data),
  })

  const { data: invitesPage } = useQuery({
    queryKey: ['workspace-invites'],
    queryFn: () => invitesApi.list(1, 50).then((r) => r.data),
    enabled: user?.role === 'admin' || user?.role === 'platform_admin',
  })

  const createMutation = useMutation({
    mutationFn: () =>
      cloudAccountsApi.create({
        provider: 'azure',
        external_id: form.external_id,
        display_name: form.display_name,
        tenant_id: form.tenant_id || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cloud-accounts'] })
      setShowAddForm(false)
      setForm({ external_id: '', display_name: '', tenant_id: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: cloudAccountsApi.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cloud-accounts'] }),
  })

  const healthMutation = useMutation({
    mutationFn: cloudAccountsApi.healthCheck,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cloud-accounts'] }),
  })

  const revokePasskeyMutation = useMutation({
    mutationFn: authApi.revokePasskey,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['auth-passkeys'] })
      const me = await authApi.me()
      queryClient.setQueryData(['auth-user'], me.data)
      setPasskeyMessage('Passkey revogada com sucesso')
    },
  })

  const createInviteMutation = useMutation({
    mutationFn: () =>
      invitesApi.create({
        email: inviteForm.email.trim().toLowerCase(),
        role: inviteForm.role,
        expires_in_days: inviteForm.expiresInDays,
      }),
    onSuccess: async ({ data }) => {
      await queryClient.invalidateQueries({ queryKey: ['workspace-invites'] })
      setInviteForm({ email: '', role: 'viewer', expiresInDays: 7 })
      const link = `${window.location.origin}/activate?token=${data.token}`
      setInviteFeedback(`Invite created for ${data.invited_email}. Activation link: ${link}`)
    },
    onError: (error) => {
      setInviteFeedback((error as Error)?.message ?? 'Could not create invite')
    },
  })

  const revokeInviteMutation = useMutation({
    mutationFn: (inviteId: string) => invitesApi.revoke(inviteId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['workspace-invites'] })
      setInviteFeedback('Invite revoked successfully')
    },
    onError: (error) => {
      setInviteFeedback((error as Error)?.message ?? 'Could not revoke invite')
    },
  })

  const handleSync = async (account: CloudAccount) => {
    setSyncingId(account.id)
    try {
      const end = format(new Date(), 'yyyy-MM-dd')
      const start = format(subDays(new Date(), 30), 'yyyy-MM-dd')
      await ledgerApi.ingest(account.id, start, end).then((r) => r.data)
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    } finally {
      setSyncingId(null)
    }
  }

  const handleGenerate = async (accountId: string) => {
    setGeneratingId(accountId)
    try {
      await opportunitiesApi.generate(accountId)
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    } finally {
      setGeneratingId(null)
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

  const copyInviteLink = async (invite: InviteOut) => {
    const link = `${window.location.origin}/activate?token=${invite.token}`
    try {
      await navigator.clipboard.writeText(link)
      setInviteFeedback(`Activation link copied for ${invite.invited_email}`)
    } catch {
      setInviteFeedback(`Copy failed. Link: ${link}`)
    }
  }

  const invites = invitesPage?.items ?? []
  const isAdmin = user?.role === 'admin' || user?.role === 'platform_admin'

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Manage cloud accounts and connector configuration</p>
      </div>

      {/* Cloud Accounts */}
      {isAdmin && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Member Invites</h2>
              <p className="text-xs text-gray-500 mt-1">
                Create and manage activation links for new workspace members.
              </p>
            </div>
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
              {invites.length} invites
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            <input
              type="email"
              value={inviteForm.email}
              onChange={(e) => setInviteForm((prev) => ({ ...prev, email: e.target.value }))}
              placeholder="member@company.com"
              className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
            <select
              value={inviteForm.role}
              onChange={(e) => setInviteForm((prev) => ({ ...prev, role: e.target.value as InviteRole }))}
              className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            >
              <option value="viewer">viewer</option>
              <option value="executive">executive</option>
              <option value="finops">finops</option>
              <option value="engineer">engineer</option>
              <option value="admin">admin</option>
            </select>
            <select
              value={inviteForm.expiresInDays}
              onChange={(e) => setInviteForm((prev) => ({ ...prev, expiresInDays: Number(e.target.value) }))}
              className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            >
              <option value={3}>3 days</option>
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days</option>
            </select>
            <button
              onClick={() => createInviteMutation.mutate()}
              disabled={!inviteForm.email.trim() || createInviteMutation.isPending}
              className="rounded bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {createInviteMutation.isPending ? 'Creating...' : 'Create Invite'}
            </button>
          </div>

          {inviteFeedback && (
            <div className="mt-3 rounded border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
              {inviteFeedback}
            </div>
          )}

          <div className="mt-4 space-y-2">
            {!invites.length ? (
              <div className="text-xs text-gray-500">No invites created yet.</div>
            ) : (
              invites.map((invite) => (
                <div
                  key={invite.id}
                  className="flex items-center justify-between rounded border border-gray-200 px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-800">{invite.invited_email}</div>
                    <div className="text-xs text-gray-500">
                      {invite.role} · {invite.status} · expires {new Date(invite.expires_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="ml-3 flex items-center gap-2">
                    <button
                      onClick={() => copyInviteLink(invite)}
                      className="rounded border border-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Copy Link
                    </button>
                    <button
                      onClick={() => revokeInviteMutation.mutate(invite.id)}
                      disabled={invite.status !== 'pending' || revokeInviteMutation.isPending}
                      className="rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-60"
                    >
                      Revoke
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Autenticação Passwordless</h2>
            <p className="text-xs text-gray-500 mt-1">
              Cadastre uma passkey para login sem senha.
            </p>
          </div>
          <button
            onClick={handleRegisterPasskey}
            disabled={registeringPasskey}
            className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-60"
          >
            {registeringPasskey ? 'Registrando...' : 'Registrar Passkey'}
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-600">
          Status atual: {user?.passkey_enabled ? 'passkey ativa' : 'sem passkey cadastrada'}
        </div>
        {passkeyMessage && <div className="mt-2 text-xs text-brand-700">{passkeyMessage}</div>}
        <div className="mt-3 space-y-2">
          {!passkeys?.length ? (
            <div className="text-xs text-gray-500">Nenhuma passkey cadastrada</div>
          ) : (
            passkeys.map((p) => (
              <div key={p.id} className="flex items-center justify-between rounded border border-gray-200 px-3 py-2">
                <div className="text-xs text-gray-700">
                  {p.credential_id.slice(0, 10)}... · usos: {p.sign_count}
                </div>
                <button
                  onClick={() => revokePasskeyMutation.mutate(p.id)}
                  className="rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50"
                >
                  Revogar
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-900">Cloud Accounts</h2>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700"
          >
            <Plus className="h-4 w-4" /> Add Account
          </button>
        </div>

        {showAddForm && (
          <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3">
            <h3 className="text-sm font-semibold text-gray-800">Add Azure Account</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Subscription ID *</label>
                <input
                  value={form.external_id}
                  onChange={(e) => setForm({ ...form, external_id: e.target.value })}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Display Name *</label>
                <input
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  placeholder="Production Azure Sub"
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Tenant ID (optional)</label>
                <input
                  value={form.tenant_id}
                  onChange={(e) => setForm({ ...form, tenant_id: e.target.value })}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                />
              </div>
            </div>
            <p className="text-xs text-gray-500">
              Service Principal credentials are read from environment variables (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET).
              If not set, the mock connector is used.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => createMutation.mutate()}
                disabled={!form.external_id || !form.display_name || createMutation.isPending}
                className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {createMutation.isPending ? 'Adding...' : 'Add Account'}
              </button>
              <button
                onClick={() => setShowAddForm(false)}
                className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="py-8 text-center text-sm text-gray-400">Loading accounts...</div>
        ) : !accounts?.length ? (
          <div className="rounded-lg border-2 border-dashed border-gray-200 py-8 text-center">
            <p className="text-sm text-gray-500">No accounts connected yet.</p>
            <p className="mt-1 text-xs text-gray-400">Add an Azure subscription to start ingesting data.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {accounts.map((account) => (
              <AccountRow
                key={account.id}
                account={account}
                syncing={syncingId === account.id}
                generating={generatingId === account.id}
                onHealthCheck={() => healthMutation.mutate(account.id)}
                onSync={() => handleSync(account)}
                onGenerate={() => handleGenerate(account.id)}
                onDelete={() => {
                  if (confirm(`Delete account "${account.display_name}"?`)) {
                    deleteMutation.mutate(account.id)
                  }
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Connector note */}
      <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4">
        <h3 className="text-sm font-semibold text-yellow-800 mb-1">Azure Service Principal Setup</h3>
        <p className="text-xs text-yellow-700">
          Set <code className="font-mono bg-yellow-100 px-1 rounded">AZURE_TENANT_ID</code>,{' '}
          <code className="font-mono bg-yellow-100 px-1 rounded">AZURE_CLIENT_ID</code>,{' '}
          <code className="font-mono bg-yellow-100 px-1 rounded">AZURE_CLIENT_SECRET</code> in your{' '}
          <code className="font-mono bg-yellow-100 px-1 rounded">.env</code> file to use real Azure data.
          Without these variables, the mock connector generates realistic synthetic data.
        </p>
      </div>
    </div>
  )
}

function AccountRow({
  account,
  syncing,
  generating,
  onHealthCheck,
  onSync,
  onGenerate,
  onDelete,
}: {
  account: CloudAccount
  syncing: boolean
  generating: boolean
  onHealthCheck: () => void
  onSync: () => void
  onGenerate: () => void
  onDelete: () => void
}) {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-gray-200 p-3">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900">{account.display_name}</p>
        <p className="text-xs text-gray-500 font-mono">{account.external_id}</p>
        <p className="text-xs text-gray-400 mt-0.5">
          {account.last_sync_at
            ? `Last sync: ${new Date(account.last_sync_at).toLocaleString()}`
            : 'Never synced'}
        </p>
      </div>
      <span
        className={clsx(
          'rounded-full px-2.5 py-0.5 text-xs font-medium',
          account.status === 'active' ? 'bg-green-100 text-green-700' :
          account.status === 'error' ? 'bg-red-100 text-red-700' :
          account.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
          'bg-gray-100 text-gray-600'
        )}
      >
        {account.status}
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={onHealthCheck}
          title="Health Check"
          className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <Activity className="h-4 w-4" />
        </button>
        <button
          onClick={onSync}
          disabled={syncing}
          title="Sync data (last 30 days)"
          className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-brand-600 hover:bg-blue-50 disabled:opacity-60"
        >
          <RefreshCw className={clsx('h-3.5 w-3.5', syncing && 'animate-spin')} />
          {syncing ? 'Syncing...' : 'Sync'}
        </button>
        <button
          onClick={onGenerate}
          disabled={generating}
          title="Generate opportunities from data"
          className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-yellow-600 hover:bg-yellow-50 disabled:opacity-60"
        >
          <Zap className={clsx('h-3.5 w-3.5', generating && 'animate-pulse')} />
          {generating ? 'Generating...' : 'Generate'}
        </button>
        <button
          onClick={onDelete}
          title="Delete account"
          className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
