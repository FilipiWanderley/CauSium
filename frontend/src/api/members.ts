import { apiClient } from './client'
import type { PageResponse, UserRole } from '../types'

export interface MemberItem {
  id: string
  org_id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  passkey_enabled: boolean
  must_change_password: boolean
  created_at: string
  org_name: string
}

export interface MemberCreatePayload {
  email: string
  full_name: string
  password: string
  role: UserRole
}

export const membersApi = {
  list: (page = 1, page_size = 50) =>
    apiClient.get<PageResponse<MemberItem>>('/auth/users', { params: { page, page_size } }),

  create: (payload: MemberCreatePayload) => apiClient.post<MemberItem>('/auth/users', payload),
  
  update: (id: string, payload: Partial<Pick<MemberItem, 'full_name' | 'email' | 'role'>>) =>
    apiClient.patch<MemberItem>(`/auth/users/${id}`, payload),

  delete: (id: string, reason: string) =>
    apiClient.delete<MemberItem>(`/auth/users/${id}`, { data: { reason } }),
}
