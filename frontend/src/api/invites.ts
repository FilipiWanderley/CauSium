import { apiClient } from './client'

export type InviteStatus = 'pending' | 'accepted' | 'expired' | 'revoked'
export type InviteRole = 'admin' | 'engineer' | 'finops' | 'executive' | 'viewer'

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
}

export const invitesApi = {
  preview: (token: string) => apiClient.get<InvitePreview>(`/invites/${token}/preview`),

  accept: (token: string, payload: InviteAcceptPayload) =>
    apiClient.post('/invites/' + token + '/accept', payload),
}
