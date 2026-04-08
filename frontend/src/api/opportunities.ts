import { apiClient } from './client'
import type { Opportunity, OpportunitySummary } from '../types'

interface ApiPage<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export const opportunitiesApi = {
  list: (params?: {
    status?: string
    category?: string
    owner_team?: string
    limit?: number
    offset?: number
  }) => apiClient.get<ApiPage<Opportunity>>('/opportunities', { params }),

  summary: () => apiClient.get<OpportunitySummary>('/opportunities/summary'),

  get: (id: string) => apiClient.get<Opportunity>(`/opportunities/${id}`),

  updateStatus: (id: string, status: string) =>
    apiClient.patch<Opportunity>(`/opportunities/${id}/status`, { status }),

  generate: (accountId: string) =>
    apiClient.post<Opportunity[]>(`/opportunities/generate/${accountId}`),
}
