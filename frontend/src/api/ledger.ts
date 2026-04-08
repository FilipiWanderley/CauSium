import { apiClient } from './client'
import type { DashboardMetrics, CostTrend, ServiceBreakdown } from '../types'

export const ledgerApi = {
  dashboard: () => apiClient.get<DashboardMetrics>('/ledger/dashboard'),

  costTrend: (days = 30) =>
    apiClient.get<CostTrend[]>(`/ledger/costs/trend?days=${days}`),

  topServices: (days = 30) =>
    apiClient.get<ServiceBreakdown[]>(`/ledger/costs/services?days=${days}`),

  topServicesWithLimit: (days = 30, limit = 10) =>
    apiClient.get<ServiceBreakdown[]>(`/ledger/costs/services?days=${days}&limit=${limit}`),

  // Temporary SKU view based on service-level aggregation until provider SKU ingestion is available.
  topSkus: (days = 30, limit = 20) =>
    apiClient.get<ServiceBreakdown[]>(`/ledger/costs/services?days=${days}&limit=${limit}`),

  topTeams: (days = 30) =>
    apiClient.get<ServiceBreakdown[]>(`/ledger/costs/teams?days=${days}`),

  topTeamsWithLimit: (days = 30, limit = 10) =>
    apiClient.get<ServiceBreakdown[]>(`/ledger/costs/teams?days=${days}&limit=${limit}`),

  ingest: (account_id: string, start_date: string, end_date: string) =>
    apiClient.post('/ledger/ingest', { account_id, start_date, end_date }),
}
