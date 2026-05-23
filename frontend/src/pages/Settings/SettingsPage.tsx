import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { cloudAccountsApi } from '../../api/cloudAccounts'
import type { CloudAccount } from '../../types'
import { useAuth } from '../../hooks/useAuth'
import { usePageTitle } from '../../hooks/usePageTitle'
import { useI18n } from '../../contexts/I18nContext'
import { PageHeader } from '../../components/Layout/PageHeader'
import { Panel, PanelHeader, PanelSection } from '../../components/Layout/Panel'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { SkeletonSection } from '../../components/UX/Skeleton'
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
  aws_access_key_id: '',
  aws_secret_access_key: '',
  aws_session_token: '',
  aws_region: 'us-east-1',
  aws_cur_bucket: '',
  aws_cur_prefix: '',
  gcp_project_id: '',
  gcp_service_account_json: '',
  gcp_use_workload_identity: false,
  gcp_billing_export_table: '',
  gcp_logging_filter: '',
}

type ValidationCheckState = 'idle' | 'ok' | 'error'

export function SettingsPage() {
  const { t } = useI18n()
  usePageTitle(t.nav.settings)
  const s = t.settings
  const p = t.platform
  const { user, registerCurrentPasskey, logoutAll } = useAuth()
  const queryClient = useQueryClient()
  const { pathname } = useLocation()
  const locale = 'en-US'

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
    pathname.endsWith('/settings/cloud') || pathname.endsWith('/cloud')
      ? 'cloud'
      : pathname.endsWith('/settings/team')
        ? 'team'
        : pathname.endsWith('/settings/security')
          ? 'security'
          : 'general'

  const {
    data: passkeys,
    isLoading: passkeysLoading,
    isError: passkeysError,
    refetch: refetchPasskeys,
  } = useQuery({
    queryKey: ['auth-passkeys'],
    queryFn: () => authApi.listPasskeys().then((r) => r.data),
  })
  const {
    data: cloudAccounts,
    isLoading: cloudAccountsLoading,
    isError: cloudAccountsError,
    refetch: refetchCloudAccounts,
  } = useQuery({
    queryKey: ['cloud-accounts-settings'],
    queryFn: () => cloudAccountsApi.list(1, 100).then((r) => r.data.items),
    enabled: isAdmin,
    refetchInterval: (query) => {
      const items = (query.state.data as CloudAccount[] | undefined) ?? []
      return items.some((acc) => acc.status === 'pending') ? 5000 : false
    },
  })

  const revokePasskeyMutation = useMutation({
    mutationFn: (passkeyId: string) => authApi.revokePasskey(passkeyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['auth-passkeys'] }),
  })
  const createCloudAccountMutation = useMutation({
    mutationFn: () => {
      const provider = cloudForm.provider.trim().toLowerCase() as 'azure' | 'aws' | 'gcp'
      const externalId = cloudForm.external_id.trim()
      const tenantId = cloudForm.tenant_id.trim()
      const storageAccount = cloudForm.storage_account.trim()
      const storageAccountUrl = storageAccount ? `https://${storageAccount}.blob.core.windows.net` : undefined

      return cloudAccountsApi.create({
        provider,
        external_id: externalId,
        display_name: cloudForm.display_name.trim(),
        tenant_id: provider === 'azure' ? tenantId || undefined : undefined,
        azure_credentials:
          provider === 'azure'
            ? {
                tenant_id: tenantId,
                client_id: cloudForm.client_id.trim(),
                client_secret: cloudForm.client_secret.trim(),
                subscription_id: externalId,
                storage_account_url: storageAccountUrl,
                cost_export_container: cloudForm.container.trim(),
                cost_export_prefix: cloudForm.cost_export_prefix.trim(),
                cost_export_format: cloudForm.cost_export_format,
              }
            : undefined,
        aws_credentials:
          provider === 'aws'
            ? {
                access_key_id: cloudForm.aws_access_key_id.trim(),
                secret_access_key: cloudForm.aws_secret_access_key.trim(),
                session_token: cloudForm.aws_session_token.trim() || undefined,
                region: cloudForm.aws_region.trim() || 'us-east-1',
                cur_bucket: cloudForm.aws_cur_bucket.trim() || undefined,
                cur_prefix: cloudForm.aws_cur_prefix.trim() || undefined,
              }
            : undefined,
        gcp_credentials:
          provider === 'gcp'
            ? {
                project_id: cloudForm.gcp_project_id.trim(),
                service_account_json: cloudForm.gcp_use_workload_identity
                  ? undefined
                  : cloudForm.gcp_service_account_json.trim(),
                use_workload_identity: cloudForm.gcp_use_workload_identity,
                billing_export_table: cloudForm.gcp_billing_export_table.trim() || undefined,
                logging_filter: cloudForm.gcp_logging_filter.trim() || undefined,
              }
            : undefined,
      })
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
      setCloudActionFeedback({ tone: 'success', message: p.syncSuccessMsg })
    },
    onError: (error) => {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        p.syncErrorMsg
      setCloudActionFeedback({ tone: 'error', message: detail })
    },
  })
  const deleteCloudAccountMutation = useMutation({
    mutationFn: (accountId: string) => cloudAccountsApi.delete(accountId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cloud-accounts-settings'] })
      setCloudActionFeedback({ tone: 'success', message: 'Cloud account removed from this workspace.' })
    },
    onError: (error) => {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Could not remove the cloud account.'
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
      <div className="page-container">
        <PageHeader
          title={t.nav.settingsTeam}
          subtitle="Review workspace access governance from the dedicated member administration surface."
          meta={
            <>
            <span>Workspace administration</span>
            <span>Access governance</span>
            </>
          }
        />
        <SectionIntro
          title="Workspace access governance"
          subtitle="Role changes, recovery actions, and offboarding stay together in the dedicated Members surface."
          badges={[
            { label: 'Access governance', tone: 'organization' },
            { label: 'Dedicated workflow', tone: 'secondary' },
          ]}
          compact
        />
        <Panel>
          <PanelHeader
            title={t.nav.settingsTeam}
          subtitle="Workspace membership is managed from the Members page so access governance stays in one place."
          />
          <div className="mt-4">
            <Link
              to="/app/members"
              className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            >
              Open Workspace Access
            </Link>
          </div>
        </Panel>
      </div>
    )
  }

  const handleValidateAndSave = async () => {
    const provider = cloudForm.provider.trim().toLowerCase() as 'azure' | 'aws' | 'gcp'
    setValidationMessage(null)
    setValidationChecks({
      credentials: 'idle',
      subscription: 'idle',
      cost: 'idle',
      storage: 'idle',
    })

    try {
      if (provider === 'azure') {
        const storageAccountName = cloudForm.storage_account.trim()
        if (
          storageAccountName.includes('://') ||
          storageAccountName.includes('/') ||
          storageAccountName.includes('.')
        ) {
          setValidationMessage('Enter only the Storage Account name, without a URL.')
          setValidationChecks({
            credentials: 'error',
            subscription: 'idle',
            cost: 'idle',
            storage: 'idle',
          })
          return
        }
      }

      const createdAccount = await createCloudAccountMutation.mutateAsync()
      setValidationChecks((prev) => ({ ...prev, credentials: 'ok' }))

      const validation = await validateCloudAccountMutation.mutateAsync(createdAccount.data.id)
      const scopes = validation.data.validated_scopes || []
      const hasCredentials = scopes.includes('CredentialsValid')
      const hasCostScope =
        scopes.includes('CostManagementReaderOrHigher') ||
        scopes.includes('CostExplorerRead') ||
        scopes.includes('BillingExportRead')
      const hasStorageScope = scopes.includes('StorageBlobDataReader') || scopes.includes('CurBucketRead')

      setValidationChecks({
        credentials: hasCredentials ? 'ok' : 'idle',
        subscription: hasCostScope ? 'ok' : 'error',
        cost: hasCostScope ? 'ok' : 'error',
        storage: hasStorageScope ? 'ok' : 'idle',
      })
      setValidationMessage(validation.data.message || 'Credential validated successfully.')
      await queryClient.invalidateQueries({ queryKey: ['cloud-accounts-settings'] })
      setCloudForm(defaultCloudForm)
    } catch (error) {
      const responseData = (error as { response?: { status?: number; data?: unknown } })?.response?.data
      const status = (error as { response?: { status?: number } })?.response?.status
      const detail =
        (typeof responseData === 'string' && responseData.trim()) ||
        ((responseData as { detail?: string })?.detail?.trim?.() as string | undefined) ||
        (error as Error)?.message ||
        'Credential validation failed. Review the fields and permissions.'
      setValidationMessage(status ? `(${status}) ${detail}` : detail)
      setValidationChecks((prev) => ({
        credentials: prev.credentials === 'ok' ? 'ok' : 'error',
        subscription: 'error',
        cost: 'error',
        storage: (cloudForm.storage_account || cloudForm.container) ? 'error' : 'idle',
      }))
    }
  }

  const handleProviderTabChange = (provider: 'azure' | 'aws' | 'gcp') => {
    setCloudForm((prev) => ({ ...prev, provider }))
    setValidationMessage(null)
    setValidationChecks({
      credentials: 'idle',
      subscription: 'idle',
      cost: 'idle',
      storage: 'idle',
    })
  }

  if (section === 'cloud') {
    const provider = cloudForm.provider as 'azure' | 'aws' | 'gcp'
    const isBusy = createCloudAccountMutation.isPending || validateCloudAccountMutation.isPending
    const isFormValid = (() => {
      if (!cloudForm.external_id || !cloudForm.display_name) return false
      if (provider === 'azure') {
        return (
          !!cloudForm.tenant_id &&
          !!cloudForm.client_id &&
          !!cloudForm.client_secret &&
          !!cloudForm.storage_account &&
          !!cloudForm.container &&
          !!cloudForm.cost_export_prefix
        )
      }
      if (provider === 'aws') {
        return !!cloudForm.aws_access_key_id && !!cloudForm.aws_secret_access_key
      }
      if (provider === 'gcp') {
        if (!cloudForm.gcp_project_id) return false
        if (cloudForm.gcp_use_workload_identity) return true
        return !!cloudForm.gcp_service_account_json
      }
      return false
    })()

    const statusText = (state: ValidationCheckState, label: string) => {
      if (state === 'ok') return `OK: ${label}`
      if (state === 'error') return `Error: ${label}`
      return `Pending: ${label}`
    }

    const tenantId = cloudForm.tenant_id.trim() || '<TENANT_ID>'
    const subscriptionId = cloudForm.external_id.trim() || '<SUBSCRIPTION_ID>'
    const appName = cloudForm.display_name.trim() || 'CauSium-Cost-Collector'
    const storageAccountName = cloudForm.storage_account.trim() || '<STORAGE_ACCOUNT_NAME>'
    const containerName = cloudForm.container.trim() || '<CONTAINER_NAME>'
    const exportPrefix = cloudForm.cost_export_prefix.trim() || '<COST_EXPORT_PREFIX>'
    const azureSetupScript = [
      '# Azure setup for CauSium cloud cost ingestion (Service Principal + RBAC)',
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
      'Write-Host "Use these values in CauSium Cloud Account Settings:" -ForegroundColor Green',
      'Write-Host ("Tenant ID: " + $TenantId)',
      'Write-Host ("Subscription ID: " + $SubscriptionId)',
      'Write-Host ("Client ID (Application ID): " + $sp.AppId)',
      'Write-Host ("Client Secret (Value): " + $secret.SecretText)',
      'Write-Host ("Storage Account: " + $StorageAccountName)',
      'Write-Host ("Container: " + $ContainerName)',
      'Write-Host ("Prefix: " + $ExportPrefix)',
    ].join('\n')
    const syncingAccountId = syncCloudAccountMutation.isPending ? syncCloudAccountMutation.variables : null
    const deletingAccountId = deleteCloudAccountMutation.isPending ? deleteCloudAccountMutation.variables : null
    const formatSyncDate = (value: string | null) =>
      value ? new Date(value).toLocaleString() : 'Never synced'

    return (
      <div className="page-container">
        <PageHeader
          title={t.nav.settingsCloud}
          subtitle="Connect, validate, and maintain cloud account access for spend ingestion and FinOps readiness."
          meta={
            <>
              <span>Workspace administration</span>
              <span>Cloud account access</span>
            </>
          }
        />
        <SectionIntro
          title="Cloud account access"
          subtitle="Configure provider credentials, validate access, and manage connected cloud accounts without leaving workspace administration."
          badges={[
            { label: 'Provider-aware setup', tone: 'organization' },
            { label: 'Validated before save', tone: 'secondary' },
          ]}
          compact
        />
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.9fr)]">
          <Panel className="space-y-5">
            <PanelHeader
              title="Add cloud account"
              subtitle={
                provider === 'azure'
                  ? 'Connect Azure securely and validate access before saving the cloud account.'
                  : provider === 'aws'
                    ? 'Connect AWS with IAM credentials and validate access before saving the cloud account.'
                    : 'Connect GCP with a service account key or Workload Identity.'
              }
            />

            {provider === 'azure' && (
              <>
                <PanelSection title="Azure setup guide" className="mt-0 border-t-0 pt-0">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => setIsScriptExpanded((prev) => !prev)}
                      className="inline-flex items-center gap-2 text-sm text-gray-700 font-medium"
                      aria-expanded={isScriptExpanded}
                    >
                      <span>{isScriptExpanded ? '▼' : '▶'}</span>
                      <span>Azure setup script (PowerShell)</span>
                    </button>
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(azureSetupScript)
                          setValidationMessage('Setup script copied to the clipboard.')
                        } catch {
                          setValidationMessage('Could not copy the setup script automatically.')
                        }
                      }}
                      className="rounded border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
                    >
                      Copy script
                    </button>
                  </div>
                  {isScriptExpanded && (
                    <pre className="max-h-72 overflow-auto rounded bg-gray-900 p-3 text-[11px] leading-5 text-gray-100">
                      <code>{azureSetupScript}</code>
                    </pre>
                  )}
                  </div>
                </PanelSection>
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  Use only service principal credentials for Azure onboarding. Do not use a personal sign-in.
                </div>
              </>
            )}

            <PanelSection title="Provider">
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-2">
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => handleProviderTabChange('azure')}
                  className={`rounded px-3 py-2 text-sm font-medium transition ${
                    provider === 'azure'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Azure
                </button>
                <button
                  type="button"
                  onClick={() => handleProviderTabChange('aws')}
                  className={`rounded px-3 py-2 text-sm font-medium transition ${
                    provider === 'aws'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  AWS
                </button>
                <button
                  type="button"
                  onClick={() => handleProviderTabChange('gcp')}
                  className={`rounded px-3 py-2 text-sm font-medium transition ${
                    provider === 'gcp'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  GCP
                </button>
              </div>
              <p className="mt-2 text-xs text-gray-600">
                Select a provider to show only the fields required for that cloud account setup flow.
              </p>
            </div>
            </PanelSection>

            <PanelSection title="Connection details">
            <p className="mb-3 text-xs text-slate-500">
              Start with the cloud account identity, then complete only the provider-specific credentials and export fields required for validation.
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm md:col-span-2"
                placeholder="Cloud account name"
                value={cloudForm.display_name}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, display_name: e.target.value }))}
              />
              <input
                className="rounded border border-gray-300 px-3 py-2 text-sm"
                placeholder={provider === 'azure' ? 'Subscription ID' : provider === 'aws' ? 'AWS Account ID' : 'GCP Project ID'}
                value={cloudForm.external_id}
                onChange={(e) => setCloudForm((prev) => ({ ...prev, external_id: e.target.value }))}
              />
              {provider === 'azure' && (
                <>
                  <div className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2 text-xs text-slate-600 md:col-span-2">
                    Provide service principal access first, then the storage location that hosts the billing export used for spend ingestion.
                  </div>
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm"
                    placeholder="Tenant ID"
                    value={cloudForm.tenant_id}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, tenant_id: e.target.value }))}
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
                    placeholder="Prefix"
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
                    <option value="auto">Format: auto</option>
                    <option value="csv">Format: csv</option>
                    <option value="parquet">Format: parquet</option>
                  </select>
                </>
              )}
              {provider === 'aws' && (
                <>
                  <div className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2 text-xs text-slate-600 md:col-span-2">
                    Use IAM credentials for validation. CUR export fields are optional and can be added only when needed.
                  </div>
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm"
                    placeholder="Access Key ID"
                    value={cloudForm.aws_access_key_id}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, aws_access_key_id: e.target.value }))}
                  />
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm"
                    type="password"
                    placeholder="Secret Access Key"
                    autoComplete="new-password"
                    value={cloudForm.aws_secret_access_key}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, aws_secret_access_key: e.target.value }))}
                  />
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm"
                    placeholder="Session token (optional)"
                    value={cloudForm.aws_session_token}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, aws_session_token: e.target.value }))}
                  />
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm"
                    placeholder="Region (ex: us-east-1)"
                    value={cloudForm.aws_region}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, aws_region: e.target.value }))}
                  />
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm"
                    placeholder="CUR bucket (optional)"
                    value={cloudForm.aws_cur_bucket}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, aws_cur_bucket: e.target.value }))}
                  />
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm"
                    placeholder="CUR prefix (optional)"
                    value={cloudForm.aws_cur_prefix}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, aws_cur_prefix: e.target.value }))}
                  />
                </>
              )}
              {provider === 'gcp' && (
                <>
                  <div className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2 text-xs text-slate-600 md:col-span-2">
                    Choose Workload Identity when available. Otherwise provide a service account key and any optional billing export fields below.
                  </div>
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm"
                    placeholder="Project ID"
                    value={cloudForm.gcp_project_id}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, gcp_project_id: e.target.value }))}
                  />
                  <label className="flex items-center gap-2 rounded border border-gray-300 px-3 py-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={cloudForm.gcp_use_workload_identity}
                      onChange={(e) => setCloudForm((prev) => ({ ...prev, gcp_use_workload_identity: e.target.checked }))}
                    />
                    Use Workload Identity (ADC)
                  </label>
                  {!cloudForm.gcp_use_workload_identity && (
                    <textarea
                      className="rounded border border-gray-300 px-3 py-2 text-sm md:col-span-2 min-h-36"
                      placeholder="Service account JSON"
                      value={cloudForm.gcp_service_account_json}
                      onChange={(e) => setCloudForm((prev) => ({ ...prev, gcp_service_account_json: e.target.value }))}
                    />
                  )}
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm md:col-span-2"
                    placeholder="Billing export table (optional)"
                    value={cloudForm.gcp_billing_export_table}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, gcp_billing_export_table: e.target.value }))}
                  />
                  <input
                    className="rounded border border-gray-300 px-3 py-2 text-sm md:col-span-2"
                    placeholder="Logging filter (optional)"
                    value={cloudForm.gcp_logging_filter}
                    onChange={(e) => setCloudForm((prev) => ({ ...prev, gcp_logging_filter: e.target.value }))}
                  />
                </>
              )}
            </div>
            </PanelSection>

            <PanelSection title="Validation">
            <div className="flex flex-wrap gap-2">
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
                Cancel
              </button>
              <button
                onClick={handleValidateAndSave}
                disabled={isBusy || !isFormValid}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white font-medium hover:bg-blue-700 disabled:opacity-60"
              >
                {isBusy ? 'Validating...' : 'Validate and save'}
              </button>
            </div>
            {validationMessage && (
              <p className="text-xs text-gray-700">{validationMessage}</p>
            )}
            </PanelSection>
          </Panel>

          <div className="space-y-4 lg:sticky lg:top-6">
            <Panel compact className="space-y-2">
              <PanelHeader
                title="Validation status"
                subtitle="Track credential, scope, cost, and storage checks before saving the cloud account."
              />
              <div className="mt-3 space-y-2">
              <p className="text-xs text-gray-600">{statusText(validationChecks.credentials, 'Valid credentials')}</p>
              <p className="text-xs text-gray-600">{statusText(validationChecks.subscription, 'Subscription access')}</p>
              <p className="text-xs text-gray-600">{statusText(validationChecks.cost, 'Cost Management access')}</p>
              <p className="text-xs text-gray-600">{statusText(validationChecks.storage, 'Storage Blob access')}</p>
              </div>
            </Panel>
            <Panel compact className="space-y-2">
              <PanelHeader
                title="Setup guidance"
                subtitle="Use the provider-specific guidance below without leaving the current cloud account setup flow."
              />
              <div className="mt-3 space-y-2">
              {provider === 'azure' ? (
                <>
                  <p className="text-xs text-gray-600">
                    Ensure the credential has Reader on the subscription and Storage Blob Data Reader on the container.
                  </p>
                  <a
                    href="https://learn.microsoft.com/azure/cost-management-billing/costs/assign-access-acm-data"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Open Microsoft documentation
                  </a>
                </>
              ) : provider === 'aws' ? (
                <>
                  <p className="text-xs text-gray-600">
                    Ensure access to `sts:GetCallerIdentity` and `ce:GetCostAndUsage`. CUR in S3 is optional.
                  </p>
                  <a
                    href="https://docs.aws.amazon.com/cost-management/latest/userguide/ce-api-best-practices.html"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Open AWS documentation
                  </a>
                </>
              ) : (
                <>
                  <p className="text-xs text-gray-600">
                    Ensure project access and, when used, read access to the billing export table in BigQuery.
                  </p>
                  <a
                    href="https://cloud.google.com/billing/docs/how-to/export-data-bigquery"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Open GCP documentation
                  </a>
                </>
              )}
              </div>
            </Panel>
          </div>
        </div>
        <Panel className="space-y-3">
          <PanelHeader
            title="Connected cloud accounts"
            subtitle="Review existing cloud accounts and keep sync and lifecycle actions in the same settings view."
          />
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
          {cloudAccountsLoading ? (
            <SkeletonSection lines={4} />
          ) : cloudAccountsError ? (
            <ErrorState
              title="Could not load cloud accounts"
              description="Cloud account settings are temporarily unavailable. Please try again."
              onRetry={() => refetchCloudAccounts()}
              retryLabel={p.refresh}
              compact
            />
          ) : cloudAccounts && cloudAccounts.length > 0 ? (
            <ul className="space-y-2">
              {cloudAccounts.map((acc) => (
                <li key={acc.id} className="rounded-xl border border-slate-200 p-3 text-sm shadow-sm">
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
                  <div className="text-xs text-gray-500">Last sync: {formatSyncDate(acc.last_sync_at)}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
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
                      {deletingAccountId === acc.id ? 'Removing...' : 'Remove'}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon="document"
              title="No cloud accounts connected."
              description="Add a validated cloud account to start data sync and FinOps readiness coverage for this workspace."
            />
          )}
        </Panel>
      </div>
    )
  }

  if (section === 'security') {
    return (
      <div className="page-container">
        <PageHeader
          title={t.nav.settingsSecurity}
          subtitle="Manage authentication, passkeys, sessions, and access audit visibility from one security surface."
          meta={
            <>
              <span>Workspace administration</span>
              <span>Authentication & audit</span>
            </>
          }
        />
        <SectionIntro
          title="Security controls"
          subtitle="Manage authentication strength, account recovery, session control, and access audit visibility from one settings surface."
          badges={[
            { label: 'Authentication', tone: 'organization' },
            { label: 'Auditable controls', tone: 'secondary' },
          ]}
          compact
        />

        <Panel className="space-y-4">
          <PanelHeader
            title="Authentication"
            subtitle="Configure multi-factor authentication without changing the current sign-in workflow."
          />
          <div className="mt-4">
          <MfaTotpSettings />
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            title={s.passkeys}
            subtitle="Review registered passkeys and add a new one when needed."
          />
          <div className="mt-4 space-y-4">
          {passkeysLoading ? (
            <SkeletonSection lines={3} />
          ) : passkeysError ? (
            <ErrorState
              title="Could not load passkeys"
              description="Passkey information is temporarily unavailable. Please try again."
              onRetry={() => refetchPasskeys()}
              retryLabel="Retry"
              compact
            />
          ) : passkeys && passkeys.length > 0 ? (
            <ul className="space-y-2">
              {passkeys.map((pk: { id: string; created_at: string }) => (
                <li key={pk.id} className="flex items-center justify-between text-sm text-gray-600">
                  <span>{s.registeredAt.replace('{{date}}', new Date(pk.created_at).toLocaleDateString(locale))}</span>
                  <button
                    onClick={() => revokePasskeyMutation.mutate(pk.id)}
                    disabled={revokePasskeyMutation.isPending}
                    className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    {s.revoke}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon="document"
              title={s.noPasskeys}
              description="Register a passkey to strengthen sign-in and reduce password friction for this workspace."
              action={{
                label: s.registerPasskey,
                onClick: handleRegisterPasskey,
              }}
            />
          )}
          <button
            onClick={handleRegisterPasskey}
            disabled={registeringPasskey}
            className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
          >
            {registeringPasskey ? s.registering : s.registerPasskey}
          </button>
          {passkeyMessage && (
            <p className={`text-xs ${passkeySuccess ? 'text-green-600' : 'text-red-600'}`}>
              {passkeyMessage}
            </p>
          )}
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            title={s.sessions}
            subtitle="End all active sessions without changing the current account security flow."
          />
          <div className="mt-4">
          <div className="flex flex-col gap-2">
            <button
              onClick={handleLogoutAll}
              className="w-fit rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700 transition hover:bg-red-100 disabled:opacity-60"
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
        </Panel>

        {isAdmin && (
          <Panel>
            <PanelHeader
              title="Access audit visibility"
            subtitle="Review recent security activity and trace important access events from the same security surface."
            />
            <div className="mt-4">
            <AuditLog />
            </div>
          </Panel>
        )}
      </div>
    )
  }

  return (
    <div className="page-container">
      <PageHeader
        title={t.nav.settings}
        subtitle="Choose an administration area to manage workspace access, security, or cloud account connectivity."
        meta={
          <>
            <span>Workspace administration</span>
            <span>Access, security & cloud accounts</span>
          </>
        }
      />
      <Panel>
        <PanelHeader
          title="Workspace administration"
          subtitle="Open the administration area you want to manage while staying inside one consistent workspace experience."
        />
        <div className="mt-4 space-y-4">
          <SectionIntro
            title="Choose an administration area"
            subtitle="Each area keeps a specific responsibility together so workspace administration stays clear, auditable, and easy to navigate."
            compact
          />
          <div className="grid gap-3 md:grid-cols-3">
            <Link
              to="/app/settings/cloud"
              className="rounded-xl border border-slate-200 bg-white px-4 py-4 text-left shadow-sm transition hover:border-brand-200 hover:bg-brand-50/40 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            >
              <span className="block text-sm font-semibold text-slate-900">{t.nav.settingsCloud}</span>
              <span className="mt-1 block text-xs text-slate-500">Manage cloud accounts, validation, and sync readiness.</span>
            </Link>
            <Link
              to="/app/settings/security"
              className="rounded-xl border border-slate-200 bg-white px-4 py-4 text-left shadow-sm transition hover:border-brand-200 hover:bg-brand-50/40 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            >
              <span className="block text-sm font-semibold text-slate-900">{t.nav.settingsSecurity}</span>
              <span className="mt-1 block text-xs text-slate-500">Manage MFA, passkeys, sessions, and audit visibility.</span>
            </Link>
            <Link
              to="/app/settings/team"
              className="rounded-xl border border-slate-200 bg-white px-4 py-4 text-left shadow-sm transition hover:border-brand-200 hover:bg-brand-50/40 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            >
              <span className="block text-sm font-semibold text-slate-900">{t.nav.settingsTeam}</span>
              <span className="mt-1 block text-xs text-slate-500">Open the dedicated workspace access governance surface.</span>
            </Link>
          </div>
        </div>
      </Panel>
    </div>
  )
}
