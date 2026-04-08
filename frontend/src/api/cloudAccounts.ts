import { apiClient } from './client'
import type { CloudAccount, ConnectorHealth, ConnectorSyncStatus } from '../types'

export const cloudAccountsApi = {
  list: () => apiClient.get<CloudAccount[]>('/cloud-accounts'),

  get: (id: string) => apiClient.get<CloudAccount>(`/cloud-accounts/${id}`),

  create: (data: {
    provider: string
    external_id: string
    display_name: string
    tenant_id?: string
  }) => apiClient.post<CloudAccount>('/cloud-accounts', data),

  delete: (id: string) => apiClient.delete(`/cloud-accounts/${id}`),

  healthCheck: (id: string) =>
    apiClient.post<ConnectorHealth>(`/cloud-accounts/${id}/health-check`),

  healthHistory: (id: string) =>
    apiClient.get<ConnectorHealth[]>(`/cloud-accounts/${id}/health`),

  syncStatus: () =>
    apiClient.get<ConnectorSyncStatus[]>('/cloud-accounts/sync-status'),

  sync: (id: string) =>
    apiClient.post(`/cloud-accounts/${id}/sync`),
}
