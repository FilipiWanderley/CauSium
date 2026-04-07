import { apiClient } from './client'
import type { DashboardMetrics, CostTrend, ServiceBreakdown } from '../types'

export const ledgerApi = {
  dashboard: () => apiClient.get<DashboardMetrics>('/ledger/dashboard'),

  costTrend: (days = 30) =>
    apiClient.get<CostTrend[]>(`/ledger/costs/trend?days=${days}`),

  topServices: (days = 30) =>
    apiClient.get<ServiceBreakdown[]>(`/ledger/costs/services?days=${days}`),

  topTeams: (days = 30) =>
    apiClient.get<ServiceBreakdown[]>(`/ledger/costs/teams?days=${days}`),

  ingest: (account_id: string, start_date: string, end_date: string) =>
    apiClient.post('/ledger/ingest', { account_id, start_date, end_date }),
}
