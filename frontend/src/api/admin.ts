import { apiClient } from './client'

export interface AdminOrgListItem {
  id: string
  name: string
  slug: string
  plan: string
  lifecycle_state: 'active' | 'suspended' | 'archived'
  member_quota: number
  is_active: boolean
  created_at: string
}

export interface AdminOrgDetail {
  id: string
  name: string
  slug: string
  plan: string
  lifecycle_state: 'active' | 'suspended' | 'archived'
  member_quota: number
  suspended_at: string | null
  suspended_reason: string | null
  created_at: string
}

export interface AdminUserItem {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
  last_login: string | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export const adminApi = {
  listOrgs: (page = 1, pageSize = 20) =>
    apiClient.get<Page<AdminOrgListItem>>('/admin/orgs', {
      params: { page, page_size: pageSize },
    }),

  getOrg: (orgId: string) => apiClient.get<AdminOrgDetail>(`/admin/orgs/${orgId}`),

  listOrgUsers: (orgId: string, page = 1, pageSize = 20) =>
    apiClient.get<Page<AdminUserItem>>(`/admin/orgs/${orgId}/users`, {
      params: { page, page_size: pageSize },
    }),

  suspendOrg: (orgId: string, reason: string) =>
    apiClient.post<AdminOrgDetail>(`/admin/orgs/${orgId}/suspend`, { reason }),

  restoreOrg: (orgId: string, reason: string) =>
    apiClient.post<AdminOrgDetail>(`/admin/orgs/${orgId}/restore`, { reason }),

  archiveOrg: (orgId: string, reason: string) =>
    apiClient.post<AdminOrgDetail>(`/admin/orgs/${orgId}/archive`, { reason }),
}
