import { apiClient } from './client'
import type { ChangeEvent, ChangeEventType } from '../types'

export const changeEventsApi = {
  list: (params?: {
    event_type?: ChangeEventType
    environment?: string
    limit?: number
    offset?: number
  }) => apiClient.get<ChangeEvent[]>('/change-events', { params }),

  get: (id: string) => apiClient.get<ChangeEvent>(`/change-events/${id}`),

  create: (data: {
    event_type: ChangeEventType
    title: string
    occurred_at: string
    description?: string
    service?: string
    environment?: string
    cost_impact_usd?: number
    causal_confidence?: number
    owner_team?: string
    region?: string
  }) => apiClient.post<ChangeEvent>('/change-events', data),
}
