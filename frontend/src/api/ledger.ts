import { apiClient } from './client'
import type { DashboardMetrics, CostTrend, DetailedCostRow, PageResponse, ServiceBreakdown } from '../types'

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

  detailedCosts: (params: {
    days?: number
    service?: string
    provider?: string
    owner_team?: string
    environment?: string
    region?: string
    resource_id?: string
    resource_name?: string
    account_id?: string
    page?: number
    page_size?: number
  }) =>
    apiClient.get<PageResponse<DetailedCostRow>>('/ledger/costs', { params }),

  ingest: (account_id: string, start_date: string, end_date: string) =>
    apiClient.post('/ledger/ingest', { account_id, start_date, end_date }),
}
