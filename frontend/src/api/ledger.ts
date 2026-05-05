import { apiClient } from './client'
import type {
  DashboardMetrics,
  CostTrend,
  DetailedCostRow,
  PageResponse,
  ReservationCoverageSummary,
  ReservationEfficiencySummary,
  ServiceBreakdown,
  SubscriptionCostSummary,
} from '../types'

export interface ExportJob {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  file_format: 'csv' | 'xlsx'
  report_type: string
  window_days: number
  file_name: string | null
  error_message: string | null
  download_ready: boolean
  created_at: string
  completed_at: string | null
  expires_at: string | null
}

export const ledgerApi = {
  dashboard: (provider?: string) =>
    apiClient.get<DashboardMetrics>('/ledger/dashboard', { params: { provider } }),

  costTrend: (days = 30) =>
    apiClient.get<CostTrend[]>(`/ledger/costs/trend?days=${days}`),

  reservationCoverage: (days = 30) =>
    apiClient.get<ReservationCoverageSummary>(`/ledger/reservations/coverage?days=${days}`),

  reservationEfficiency: (days = 30, provider?: string) =>
    apiClient.get<ReservationEfficiencySummary>('/ledger/reservations/efficiency', {
      params: { days, provider },
    }),

  topServicesPaginated: (days = 30, page = 1, page_size = 50) =>
    apiClient.get<PageResponse<ServiceBreakdown>>(`/ledger/costs/services`, { params: { days, page, page_size } }),

  topTeamsPaginated: (days = 30, page = 1, page_size = 50) =>
    apiClient.get<PageResponse<ServiceBreakdown>>(`/ledger/costs/teams`, { params: { days, page, page_size } }),

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
    subscription_id?: string
    page?: number
    page_size?: number
  }) =>
    apiClient.get<PageResponse<DetailedCostRow>>('/ledger/costs', { params }),

  ingest: (account_id: string, start_date: string, end_date: string) =>
    apiClient.post('/ledger/ingest', { account_id, start_date, end_date }),

  // SP-EC03: async export
  createExportJob: (params: {
    report_type?: 'summary'
    file_format?: 'csv' | 'xlsx'
    window_days?: number
    filters?: Record<string, unknown>
  }) => apiClient.post<ExportJob>('/economics/reports/export', params),

  getExportJob: (jobId: string) =>
    apiClient.get<ExportJob>(`/economics/reports/export/${jobId}`),

  downloadExportUrl: (jobId: string) =>
    `/api/v1/economics/reports/export/${jobId}/download`,

  subscriptionCostSummary: (days = 30) =>
    apiClient.get<SubscriptionCostSummary>('/ledger/costs/subscriptions', { params: { days } }),
}
