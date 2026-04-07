import { apiClient } from './client'
import type { Comment, Initiative, InitiativeBoard } from '../types'

export const initiativesApi = {
  list: (params?: { status?: string; owner_id?: string }) =>
    apiClient.get<Initiative[]>('/initiatives', { params }),

  board: () => apiClient.get<InitiativeBoard>('/initiatives/board'),

  get: (id: string) => apiClient.get<Initiative>(`/initiatives/${id}`),

  create: (data: {
    title: string
    description?: string
    opportunity_id?: string
    owner_id?: string
    sla_date?: string
  }) => apiClient.post<Initiative>('/initiatives', data),

  update: (id: string, data: Partial<Initiative>) =>
    apiClient.patch<Initiative>(`/initiatives/${id}`, data),

  transition: (id: string, status: string) =>
    apiClient.post<Initiative>(`/initiatives/${id}/transition`, { status }),

  listComments: (id: string) =>
    apiClient.get<Comment[]>(`/initiatives/${id}/comments`),

  addComment: (id: string, body: string) =>
    apiClient.post<Comment>(`/initiatives/${id}/comments`, { body }),
}
