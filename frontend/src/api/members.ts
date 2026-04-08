import { apiClient } from './client'
import type { UserRole } from '../types'

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
  list: () => apiClient.get<MemberItem[]>('/auth/users'),

  create: (payload: MemberCreatePayload) => apiClient.post<MemberItem>('/auth/users', payload),
}
