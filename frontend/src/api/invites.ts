import { apiClient } from './client'

export type InviteStatus = 'pending' | 'accepted' | 'expired' | 'revoked'
export type InviteRole = 'admin' | 'engineer' | 'finops' | 'executive' | 'viewer'

interface ApiPage<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export interface InvitePreview {
  org_name: string
  invited_email: string
  role: InviteRole
  expires_at: string
  status: InviteStatus
}

export interface InviteAcceptPayload {
  full_name: string
  password: string
  terms_accepted: boolean
}

export interface InviteCreatePayload {
  email: string
  role: InviteRole
  expires_in_days: number
}

export interface InviteOut {
  id: string
  org_id: string
  invited_email: string
  invited_by_user_id: string
  role: InviteRole
  token: string
  expires_at: string
  accepted_at: string | null
  status: InviteStatus
  created_at: string
}

export const invitesApi = {
  preview: (token: string) => apiClient.get<InvitePreview>(`/invites/${token}/preview`),

  accept: (token: string, payload: InviteAcceptPayload) =>
    apiClient.post('/invites/' + token + '/accept', payload),

  list: (
    page = 1,
    pageSize = 20,
    filters?: {
      status?: InviteStatus
      q?: string
    }
  ) =>
    apiClient.get<ApiPage<InviteOut>>('/invites', {
      params: {
        page,
        page_size: pageSize,
        status: filters?.status,
        q: filters?.q?.trim() || undefined,
      },
    }),

  create: (payload: InviteCreatePayload) => apiClient.post<InviteOut>('/invites', payload),

  revoke: (inviteId: string) => apiClient.delete(`/invites/${inviteId}`),
}
