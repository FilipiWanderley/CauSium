import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { cloudAccountsApi } from '../../api/cloudAccounts'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'
import { MfaTotpSettings } from './MfaTotpSettings'
import { AuditLog } from './AuditLog'

const defaultCloudForm = {
  provider: 'azure',
  external_id: '',
  display_name: '',
  tenant_id: '',
  client_id: '',
  client_secret: '',
  storage_account: '',
  container: '',
  cost_export_prefix: '',
  cost_export_format: 'auto' as 'auto' | 'csv' | 'parquet',
}

type ValidationCheckState = 'idle' | 'ok' | 'error'

export function SettingsPage() {
  const { t } = useI18n()
  const s = t.settings
  const { user, registerCurrentPasskey, logoutAll } = useAuth()
  const queryClient = useQueryClient()
  const { pathname } = useLocation()

  const [logoutAllState, setLogoutAllState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [registeringPasskey, setRegisteringPasskey] = useState(false)
  const [passkeyMessage, setPasskeyMessage] = useState<string | null>(null)
  const [passkeySuccess, setPasskeySuccess] = useState(false)
  const [isScriptExpanded, setIsScriptExpanded] = useState(false)
  const [cloudForm, setCloudForm] = useState(defaultCloudForm)
  const [validationChecks, setValidationChecks] = useState<{
    credentials: ValidationCheckState
    subscription: ValidationCheckState
    cost: ValidationCheckState
    storage: ValidationCheckState
  }>({
    credentials: 'idle',
    subscription: 'idle',
    cost: 'idle',
    storage: 'idle',
  })
  const [validationMessage, setValidationMessage] = useState<string | null>(null)
  const [cloudActionFeedback, setCloudActionFeedback] = useState<{
    tone: 'success' | 'error'
    message: string
  } | null>(null)

  const isAdmin = user?.role === 'admin' || user?.role === 'platform_admin'
  const section =
    pathname.endsWith('/settings/cloud')
      ? 'cloud'
      : pathname.endsWith('/settings/team')
        ? 'team'
        : pathname.endsWith('/settings/security')
          ? 'security'
          : 'general'

  const { data: passkeys } = useQuery({
    queryKey: ['auth-passkeys'],
    queryFn: () => authApi.listPasskeys().then((r) => r.data),
  })
  const { data: cloudAccounts } = useQuery({
    queryKey: ['cloud-accounts-settings'],
    queryFn: () => cloudAccountsApi.list(1, 100).then((r) => r.data.items),
    enabled: isAdmin,
  })

  const revokePasskeyMutation = useMutation({
    mutationFn: (passkeyId: string) => authApi.revokePasskey(passkeyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['auth-passkeys'] }),
  })
  const createCloudAccountMutation = useMutation({
    mutationFn: () => {
      const provider = cloudForm.provider.trim().toLowerCase()
      const subscriptionId = cloudForm.external_id.trim()
      const tenantId = cloudForm.tenant_id.trim()
      const storageAccount = cloudForm.storage_account.trim()
      const storageAccountUrl = storageAccount ? `https://${storageAccount}.blob.core.windows.net` : undefined

      return cloudAccountsApi.create({
        provider,
        external_id: subscriptionId,
        display_name: cloudForm.display_name.trim(),
        tenant_id: tenantId || undefined,
        azure_credentials:
          provider === 'azure'
            ? {
                tenant_id: tenantId,
                client_id: cloudForm.client_id.trim(),
                client_secret: cloudForm.client_secret.trim(),
                subscription_id: subscriptionId,
                storage_account_url: storageAccountUrl,
                cost_export_container: cloudForm.container.trim(),
                cost_export_prefix: cloudForm.cost_export_prefix.trim(),
                cost_export_format: cloudForm.cost_export_format,
              }
            : undefined,
      })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cloud-accounts-settings'] })
      setCloudForm(defaultCloudForm)
    },
  })
  const validateCloudAccountMutation = useMutation({
    mutationFn: (accountId: string) => cloudAccountsApi.validate(accountId),
  })
  const syncCloudAccountMutation = useMutation({
    mutationFn: (accountId: string) => cloudAccountsApi.sync(accountId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cloud-accounts-settings'] }),
        queryClient.invalidateQueries({ queryKey: ['platform-sync-status'] }),
      ])
      setCloudActionFeedback({ tone: 'success', message: 'Sincronizacao enfileirada com sucesso.' })
    },
    onError: (error) => {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Falha ao enfileirar sincronizacao. Verifique permissao e tente novamente.'
      setCloudActionFeedback({ tone: 'error', message: detail })
    },
  })
  const deleteCloudAccountMutation = useMutation({
    mutationFn: (accountId: string) => cloudAccountsApi.delete(accountId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cloud-accounts-settings'] })
      setCloudActionFeedback({ tone: 'success', message: 'Conta removida com sucesso.' })
    },
    onError: (error) => {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Falha ao excluir conta cloud.'
      setCloudActionFeedback({ tone: 'error', message: detail })
    },
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
      setPasskeyMessage(s.passkeySuccess)
      setPasskeySuccess(true)
    } catch (error) {
      const message = error instanceof Error ? error.message : s.passkeyError
      setPasskeyMessage(message)
      setPasskeySuccess(false)
    } finally {
      setRegisteringPasskey(false)
    }
  }

  if (section === 'team') {
    return (
      <div className="space-y-6 max-w-3xl">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Equipe</h2>
          <p className="text-sm text-gray-600">
            O gerenciamento de membros fica na tela de membros do workspace.
          </p>
          <Link
            to="/app/members"
            className="inline-flex rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Abrir Membros
          </Link>
        </div>
      </div>
    )
  }

  const handleValidateAndSave = async () => {
    setValidationMessage(null)
    setValidationChecks({
      credentials: 'idle',
      subscription: 'idle',
      cost: 'idle',
      storage: 'idle',
    })

    try {
      const storageAccountName = cloudForm.storage_account.trim()
      if (
        storageAccountName.includes('://') ||
        storageAccountName.includes('/') ||
        storageAccountName.includes('.')
      ) {
        setValidationMessage('Informe somente o nome do Storage Account (sem URL).')
        setValidationChecks({
          credentials: 'error',
          subscription: 'idle',
          cost: 'idle',
          storage: 'idle',
        })
        return
      }

      const createdAccount = await createCloudAccountMutation.mutateAsync()
      setValidationChecks((prev) => ({ ...prev, credentials: 'ok' }))

      const validation = await validateCloudAccountMutation.mutateAsync(createdAccount.data.id)
      const scopes = validation.data.validated_scopes || []

      setValidationChecks({
        credentials: scopes.includes('CredentialsValid') ? 'ok' : 'idle',
        subscription: scopes.includes('CostManagementReaderOrHigher') ? 'ok' : 'error',
        cost: scopes.includes('CostManagementReaderOrHigher') ? 'ok' : 'error',
        storage:
          cloudForm.storage_account || cloudForm.container
            ? (scopes.includes('StorageBlobDataReader') ? 'ok' : 'error')
            : 'idle',
      })
      setValidationMessage(validation.data.message || 'Credencial validada com sucesso.')
    } catch (error) {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Falha ao validar credencial. Revise os dados e permissões.'
      setValidationMessage(detail)
      setValidationChecks((prev) => ({
        credentials: prev.credentials === 'ok' ? 'ok' : 'error',
        subscription: 'error',
        cost: 'error',
        storage: (cloudForm.storage_account || cloudForm.container) ? 'error' : 'idle',
      }))
    }
  }

  if (section === 'cloud') {
    const isBusy = createCloudAccountMutation.isPending || validateCloudAccountMutation.isPending
    const isFormValid =
      !!cloudForm.external_id &&
      !!cloudForm.display_name &&
      !!cloudForm.tenant_id &&
      !!cloudForm.client_id &&
      !!cloudForm.client_secret &&
      !!cloudForm.storage_account &&
      !!cloudForm.container &&
      !!cloudForm.cost_export_prefix

    const statusText = (state: ValidationCheckState, label: string) => {
      if (state === 'ok') return `OK: ${label}`
      if (state === 'error') return `Erro: ${label}`
      return `Pendente: ${label}`
    }

    const tenantId = cloudForm.tenant_id.trim() || '<TENANT_ID>'
    const subscriptionId = cloudForm.external_id.trim() || '<SUBSCRIPTION_ID>'
    const appName = cloudForm.display_name.trim() || 'StratoPulse-Cost-Collector'
    const storageAccountName = cloudForm.storage_account.trim() || '<STORAGE_ACCOUNT_NAME>'
    const containerName = cloudForm.container.trim() || '<CONTAINER_NAME>'
    const exportPrefix = cloudForm.cost_export_prefix.trim() || '<COST_EXPORT_PREFIX>'
    const azureSetupScript = [
      '# Azure setup for StratoPulse (Service Principal + RBAC)',
      '# Run in PowerShell with Az module installed',
      '',
      `$TenantId = "${tenantId}"`,
      `$SubscriptionId = "${subscriptionId}"`,
      `$AppName = "${appName}"`,
      `$StorageAccountName = "${storageAccountName}"`,
      `$ContainerName = "${containerName}"`,
      `$ExportPrefix = "${exportPrefix}"`,
      '',
      'Connect-AzAccount -Tenant $TenantId',
      'Set-AzContext -SubscriptionId $SubscriptionId',
      '',
      '# Create service principal',
      '$sp = New-AzADServicePrincipal -DisplayName $AppName',
      'Start-Sleep -Seconds 20',
      '',
      '# Assign required roles on subscription',
      '$subscriptionScope = "/subscriptions/$SubscriptionId"',
      'New-AzRoleAssignment -ApplicationId $sp.AppId -RoleDefinitionName "Reader" -Scope $subscriptionScope',
      'New-AzRoleAssignment -ApplicationId $sp.AppId -RoleDefinitionName "Cost Management Reader" -Scope $subscriptionScope',
      '',
      '# Resolve storage account and grant data-plane read',
      '$storage = Get-AzStorageAccount | Where-Object { $_.StorageAccountName -eq $StorageAccountName } | Select-Object -First 1',
      'if (-not $storage) { throw "Storage Account not found: $StorageAccountName" }',
      'New-AzRoleAssignment -ApplicationId $sp.AppId -RoleDefinitionName "Storage Blob Data Reader" -Scope $storage.Id',
      '',
      '# Ensure container exists',
      '$ctx = $storage.Context',
      'if (-not (Get-AzStorageContainer -Context $ctx -Name $ContainerName -ErrorAction SilentlyContinue)) {',
      '  New-AzStorageContainer -Context $ctx -Name $ContainerName | Out-Null',
      '}',
      '',
      '# Create app secret (1 year)',
      '$secret = New-AzADAppCredential -ApplicationId $sp.AppId -EndDate (Get-Date).AddYears(1)',
      '',
      'Write-Host ""',
      'Write-Host "Use these values in StratoPulse Cloud Settings:" -ForegroundColor Green',
      'Write-Host ("Tenant ID: " + $TenantId)',
      'Write-Host ("Subscription ID: " + $SubscriptionId)',
      'Write-Host ("Client ID (Application ID): " + $sp.AppId)',
      'Write-Host ("Client Secret (Value): " + $secret.SecretText)',
      'Write-Host ("Storage Account: " + $StorageAccountName)',
      'Write-Host ("Container: " + $ContainerName)',
      'Write-Host ("Prefixo: " + $ExportPrefix)',
    ].join('\n')
    const syncingAccountId = syncCloudAccountMutation.isPending ? syncCloudAccountMutation.variables : null
    const deletingAccountId = deleteCloudAccountMutation.isPending ? deleteCloudAccountMutation.variables : null
    const formatSyncDate = (value: string | null) =>
      value ? new Date(value).toLocaleString() : 'Nunca sincronizado'

    return (
      <div className="mx-auto w-full max-w-6xl space-y-8 px-2 md:px-4">
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.9fr)]">
          <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">Nova Credencial</h2>
              <p className="text-sm text-gray-600">Conecte Azure com segurança e valide antes de salvar.</p>
            </div>

            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => setIsScriptExpanded((prev) => !prev)}
                  className="inline-flex items-center gap-2 text-sm text-gray-700 font-medium"
                  aria-expanded={isScriptExpanded}
                >
                  <span>{isScriptExpanded ? '▼' : '▶'}</span>
                  <span>Script de configuração Azure (PowerShell)</span>
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(azureSetupScript)
                      setValidationMessage('Script copiado para a area de transferencia.')
                    } catch {
                      setValidationMessage('Nao foi possivel copiar o script automaticamente.')
                    }
                  }}
                  className="rounded border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
                >
                  Copiar script
                </button>
              </div>
              {isScriptExpanded && (
                <pre className="max-h-72 overflow-auto rounded bg-gray-900 p-3 text-[11px] leading-5 text-gray-100">
                  <code>{azureSetupScript}</code>
                </pre>
              )}
            </div>
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
              Use apenas credenciais de Service Principal (App Registration). Nao use login pessoal do cliente.
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm md:col-span-2"
                placeholder="Nome da credencial"
                value={cloudForm.display_name}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, display_name: e.target.value }))}
              />
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm"
                placeholder="Tenant ID"
                value={cloudForm.tenant_id}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, tenant_id: e.target.value }))}
              />
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm"
                placeholder="Subscription ID"
                value={cloudForm.external_id}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, external_id: e.target.value }))}
              />
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm"
                placeholder="Client ID (Service Principal / Application ID)"
                value={cloudForm.client_id}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, client_id: e.target.value }))}
              />
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm"
                type="password"
                placeholder="Client Secret (Service Principal)"
                autoComplete="new-password"
                value={cloudForm.client_secret}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, client_secret: e.target.value }))}
              />
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm"
                placeholder="Storage Account"
                value={cloudForm.storage_account}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, storage_account: e.target.value }))}
              />
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm"
                placeholder="Container"
                value={cloudForm.container}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, container: e.target.value }))}
              />
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm"
                placeholder="Prefixo"
                value={cloudForm.cost_export_prefix}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, cost_export_prefix: e.target.value }))}
              />
              <select
                className="rounded border border-gray-300 px-3 py-2 text-sm"
                value={cloudForm.cost_export_format}
                onChange={(e) =>
                  setCloudForm((prev) => ({
                    ...prev,
                    cost_export_format: e.target.value as 'auto' | 'csv' | 'parquet',
                  }))
                }
              >
                <option value="auto">Formato: auto</option>
                <option value="csv">Formato: csv</option>
                <option value="parquet">Formato: parquet</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setCloudForm(defaultCloudForm)
                  setValidationMessage(null)
                  setValidationChecks({
                    credentials: 'idle',
                    subscription: 'idle',
                    cost: 'idle',
                    storage: 'idle',
                  })
                }}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleValidateAndSave}
                disabled={isBusy || !isFormValid}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white font-medium hover:bg-blue-700 disabled:opacity-60"
              >
                {isBusy ? 'Validando...' : 'Validar e Salvar'}
              </button>
            </div>
            {validationMessage && (
              <p className="text-xs text-gray-700">{validationMessage}</p>
            )}
          </div>

          <div className="space-y-4 lg:sticky lg:top-6">
            <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm space-y-2">
              <h3 className="text-sm font-semibold text-gray-700">Status da Validação</h3>
              <p className="text-xs text-gray-600">{statusText(validationChecks.credentials, 'Credenciais válidas')}</p>
              <p className="text-xs text-gray-600">{statusText(validationChecks.subscription, "Permissão na subscription")}</p>
              <p className="text-xs text-gray-600">{statusText(validationChecks.cost, 'Acesso ao Cost Management')}</p>
              <p className="text-xs text-gray-600">{statusText(validationChecks.storage, 'Acesso ao Storage Blob')}</p>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm space-y-2">
              <h3 className="text-sm font-semibold text-gray-700">Precisa de ajuda?</h3>
              <p className="text-xs text-gray-600">
                Garanta permissões de Reader na subscription e Storage Blob Data Reader no container.
              </p>
              <a
                href="https://learn.microsoft.com/azure/cost-management-billing/costs/assign-access-acm-data"
                target="_blank"
                rel="noreferrer"
                className="inline-block rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Ver documentação Microsoft
              </a>
            </div>
          </div>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm space-y-3">
          <h3 className="text-sm font-semibold text-gray-700">Contas Cadastradas</h3>
          {cloudActionFeedback && (
            <div
              className={`rounded border px-3 py-2 text-xs ${
                cloudActionFeedback.tone === 'success'
                  ? 'border-green-200 bg-green-50 text-green-700'
                  : 'border-red-200 bg-red-50 text-red-700'
              }`}
            >
              {cloudActionFeedback.message}
            </div>
          )}
          {cloudAccounts && cloudAccounts.length > 0 ? (
            <ul className="space-y-2">
              {cloudAccounts.map((acc) => (
                <li key={acc.id} className="rounded border border-gray-200 p-3 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="font-medium text-gray-800">{acc.display_name}</div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        acc.status === 'active'
                          ? 'bg-green-100 text-green-700'
                          : acc.status === 'error'
                            ? 'bg-red-100 text-red-700'
                            : acc.status === 'pending'
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {acc.status}
                    </span>
                  </div>
                  <div className="text-gray-600">{acc.provider} · {acc.external_id}</div>
                  <div className="text-xs text-gray-500">Ultimo sync: {formatSyncDate(acc.last_sync_at)}</div>
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() => {
                        setCloudActionFeedback(null)
                        syncCloudAccountMutation.mutate(acc.id)
                      }}
                      disabled={syncCloudAccountMutation.isPending || deleteCloudAccountMutation.isPending}
                      className="rounded bg-emerald-600 px-2.5 py-1 text-xs text-white hover:bg-emerald-700 disabled:opacity-60"
                    >
                      {syncingAccountId === acc.id ? 'Queueing...' : 'Sync'}
                    </button>
                    <button
                      onClick={() => {
                        setCloudActionFeedback(null)
                        deleteCloudAccountMutation.mutate(acc.id)
                      }}
                      disabled={syncCloudAccountMutation.isPending || deleteCloudAccountMutation.isPending}
                      className="rounded bg-red-600 px-2.5 py-1 text-xs text-white hover:bg-red-700 disabled:opacity-60"
                    >
                      {deletingAccountId === acc.id ? 'Excluindo...' : 'Excluir'}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">Nenhuma conta cloud cadastrada.</p>
          )}
        </div>
      </div>
    )
  }

  if (section === 'security') {
    return (
      <div className="space-y-6 max-w-3xl">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
          <MfaTotpSettings />
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">{s.passkeys}</h2>
          {passkeys && passkeys.length > 0 ? (
            <ul className="space-y-2">
              {passkeys.map((pk: { id: string; created_at: string }) => (
                <li key={pk.id} className="flex items-center justify-between text-sm text-gray-600">
                  <span>{s.registeredAt.replace('{{date}}', new Date(pk.created_at).toLocaleDateString())}</span>
                  <button
                    onClick={() => revokePasskeyMutation.mutate(pk.id)}
                    disabled={revokePasskeyMutation.isPending}
                    className="text-red-600 hover:underline text-xs disabled:opacity-50"
                  >
                    {s.revoke}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">{s.noPasskeys}</p>
          )}
          <button
            onClick={handleRegisterPasskey}
            disabled={registeringPasskey}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {registeringPasskey ? s.registering : s.registerPasskey}
          </button>
          {passkeyMessage && (
            <p className={`text-xs ${passkeySuccess ? 'text-green-600' : 'text-red-600'}`}>
              {passkeyMessage}
            </p>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">{s.sessions}</h2>
          <div className="flex flex-col gap-2">
            <button
              onClick={handleLogoutAll}
              className="w-fit rounded bg-red-600 px-4 py-2 text-white font-semibold shadow hover:bg-red-700 disabled:opacity-60"
              disabled={logoutAllState === 'loading'}
            >
              {logoutAllState === 'loading' ? s.loggingOut : s.logoutAll}
            </button>
            {logoutAllState === 'done' && (
              <span className="text-green-600 text-xs">{s.logoutSuccess}</span>
            )}
            {logoutAllState === 'error' && (
              <span className="text-red-600 text-xs">{s.logoutError}</span>
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

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Configurações</h2>
        <p className="text-sm text-gray-600">
          Escolha uma seção específica para configurar seu workspace.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/app/settings/cloud"
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Cloud
          </Link>
          <Link
            to="/app/settings/security"
            className="rounded bg-gray-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-900"
          >
            Segurança
          </Link>
          <Link
            to="/app/settings/team"
            className="rounded bg-gray-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-700"
          >
            Time
          </Link>
        </div>
      </div>
    </div>
  )
}
