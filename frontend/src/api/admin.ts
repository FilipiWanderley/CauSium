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

export interface AdminResetMFAResponse {
  revoked_passkeys: number
  user: {
    id: string
    org_id: string
    email: string
    full_name: string
    role: string
    is_active: boolean
    passkey_enabled: boolean
    must_change_password: boolean
    created_at: string
    org_name: string
  }
}

export interface AdminResetPasswordResponse {
  temporary_password: string
  user: {
    id: string
    org_id: string
    email: string
    full_name: string
    role: string
    is_active: boolean
    passkey_enabled: boolean
    must_change_password: boolean
    created_at: string
    org_name: string
  }
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface SloTargets {
  api_error_budget_pct: number
  api_p95_latency_ms: number
}

export interface SloGlobal {
  requests_total: number
  errors_5xx_total: number
  api_error_rate_pct: number
  api_success_rate_pct: number
  error_budget_burn_rate: number
}

export interface SloApiPath {
  path: string
  requests: number
  errors_5xx: number
  error_rate_pct: number
  avg_latency_ms: number
  p95_latency_ms: number
  max_latency_ms: number
}

export interface SloWorker {
  worker: string
  success: number
  retry: number
  failed: number
  locked: number
  total: number
  error_rate_pct: number
}

export interface SloWorkerLifecycle {
  worker: string
  event: string
  count: number
}

export interface SloAlert {
  scope: string
  severity: string
  title: string
  detail: string
  recommended_action: string
}

export interface SloOverview {
  targets: SloTargets
  global_sli: SloGlobal
  api_paths: SloApiPath[]
  workers: SloWorker[]
  worker_lifecycle: SloWorkerLifecycle[]
  alerts: SloAlert[]
}

export const adminApi = {
  listOrgs: (
    page = 1,
    pageSize = 20,
    filters?: {
      q?: string
      lifecycle_state?: 'active' | 'suspended' | 'archived'
    }
  ) =>
    apiClient.get<Page<AdminOrgListItem>>('/admin/orgs', {
      params: {
        page,
        page_size: pageSize,
        q: filters?.q || undefined,
        lifecycle_state: filters?.lifecycle_state || undefined,
      },
    }),

  getOrg: (orgId: string) => apiClient.get<AdminOrgDetail>(`/admin/orgs/${orgId}`),

  listOrgUsers: (orgId: string, page = 1, pageSize = 20) =>
    apiClient.get<Page<AdminUserItem>>(`/admin/orgs/${orgId}/users`, {
      params: { page, page_size: pageSize },
    }),

  getSloOverview: () => apiClient.get<SloOverview>('/admin/observability/slo'),

  suspendOrg: (orgId: string, reason: string) =>
    apiClient.post<AdminOrgDetail>(`/admin/orgs/${orgId}/suspend`, { reason }),

  restoreOrg: (orgId: string, reason: string) =>
    apiClient.post<AdminOrgDetail>(`/admin/orgs/${orgId}/restore`, { reason }),

  archiveOrg: (orgId: string, reason: string) =>
    apiClient.post<AdminOrgDetail>(`/admin/orgs/${orgId}/archive`, { reason }),

  resetUserPassword: (userId: string) =>
    apiClient.post<AdminResetPasswordResponse>(`/auth/users/${userId}/reset-password`),

  resetUserMfa: (userId: string) =>
    apiClient.post<AdminResetMFAResponse>(`/auth/users/${userId}/reset-mfa`),

  deactivateUser: (userId: string, reason: string) =>
    apiClient.patch<AdminUserItem>(`/auth/users/${userId}/deactivate`, { reason }),
}
