import { apiClient } from './client'
import type {
  CloudAccount,
  ConnectorHealth,
  ConnectorSyncStatus,
  PageResponse,
  ScopeValidation,
} from '../types'

export const cloudAccountsApi = {
  list: (page = 1, page_size = 100) =>
    apiClient.get<PageResponse<CloudAccount>>('/cloud-accounts', { params: { page, page_size } }),

  get: (id: string) => apiClient.get<CloudAccount>(`/cloud-accounts/${id}`),

  create: (data: {
    provider: string
    external_id: string
    display_name: string
    tenant_id?: string
    azure_credentials?: {
      tenant_id: string
      client_id: string
      client_secret: string
      subscription_id: string
      storage_account_url?: string
      cost_export_container?: string
      cost_export_prefix?: string
      cost_export_format?: 'auto' | 'csv' | 'parquet'
    }
    aws_credentials?: {
      access_key_id: string
      secret_access_key: string
      session_token?: string
      region?: string
      cur_bucket?: string
      cur_prefix?: string
    }
    gcp_credentials?: {
      service_account_json?: string
      project_id: string
      use_workload_identity?: boolean
      billing_export_table?: string
      logging_filter?: string
    }
  }) => apiClient.post<CloudAccount>('/cloud-accounts', data),

  delete: (id: string) => apiClient.delete(`/cloud-accounts/${id}`),

  healthCheck: (id: string) =>
    apiClient.post<ConnectorHealth>(`/cloud-accounts/${id}/health-check`),

  healthHistory: (id: string) =>
    apiClient.get<ConnectorHealth[]>(`/cloud-accounts/${id}/health`),

  syncStatus: () =>
    apiClient.get<ConnectorSyncStatus[]>('/cloud-accounts/sync-status'),

  sync: (id: string, lookback_days = 90) =>
    apiClient.post(`/cloud-accounts/${id}/sync`, undefined, {
      params: { lookback_days },
    }),

  validate: (id: string) =>
    apiClient.post<ScopeValidation>(`/cloud-accounts/${id}/validate`),
}
