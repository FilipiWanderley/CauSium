import { apiClient } from './client'

export interface AuditEventItem {
  id: string
  org_id: string
  actor_user_id: string | null
  event_type: string
  entity_type: string
  entity_id: string
  payload: Record<string, unknown>
  prev_hash: string
  event_hash: string
  created_at: string
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export const auditChainApi = {
  listAuthEvents: (orgId: string, pageSize = 100) =>
    apiClient.get<Page<AuditEventItem>>('/audit-chain/events/auth', {
      params: {
        org_id: orgId,
        page: 1,
        page_size: pageSize,
      },
    }),
}
