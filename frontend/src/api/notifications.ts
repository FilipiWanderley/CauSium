import { apiClient } from './client'

export type AlertCategory = 'financial' | 'optimization' | 'governance' | 'activity' | 'security'
export type AlertSeverity = 'info' | 'warning' | 'critical'
export type AlertStatus = 'unread' | 'read' | 'archived'

export interface AlertRecord {
  id: string
  org_id: string
  user_id: string | null
  category: AlertCategory
  severity: AlertSeverity
  status: AlertStatus
  title: string
  body: string | null
  action_url: string | null
  source_type: string | null
  source_id: string | null
  read_at: string | null
  archived_at: string | null
  created_at: string
}

export interface UnreadCount {
  unread: number
  critical: number
}

export interface NotificationsPage {
  items: AlertRecord[]
  total: number
  page: number
  page_size: number
}

export const notificationsApi = {
  getUnreadCount: (): Promise<UnreadCount> =>
    apiClient.get('/notifications/unread-count').then((r) => r.data),

  list: (params?: {
    category?: AlertCategory
    status?: AlertStatus
    page?: number
    page_size?: number
  }): Promise<NotificationsPage> =>
    apiClient
      .get('/notifications', { params: { page: 1, page_size: 50, ...params } })
      .then((r) => r.data),

  patchStatus: (id: string, status: AlertStatus): Promise<AlertRecord> =>
    apiClient.patch(`/notifications/${id}`, { status }).then((r) => r.data),

  markAllRead: (): Promise<{ marked_read: number }> =>
    apiClient.patch('/notifications/mark-all-read').then((r) => r.data),
}
