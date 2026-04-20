import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../hooks/useAuth'
import { playCriticalNotificationSound } from './notificationSound'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

function buildNotificationsWsUrl(): string {
  const source = API_BASE_URL || window.location.origin
  const wsBase = source.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:')
  return `${wsBase}/api/v1/notifications/stream`
}

export function NotificationsRealtimeBridge() {
  const { isAuthenticated, user } = useAuth()
  const queryClient = useQueryClient()
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<number | null>(null)
  const stoppedRef = useRef(false)

  useEffect(() => {
    if (!isAuthenticated || !user) return

    stoppedRef.current = false
    let retryMs = 1000

    const connect = () => {
      if (stoppedRef.current) return
      const ws = new WebSocket(buildNotificationsWsUrl())
      socketRef.current = ws

      ws.onopen = () => {
        retryMs = 1000
      }

      ws.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data) as {
            type?: string
            notification?: { severity?: string; status?: string }
          }
          if (!payload?.type || payload.type === 'heartbeat') return
          if (
            payload.type === 'notification.created' &&
            payload.notification?.severity === 'critical' &&
            payload.notification?.status === 'unread'
          ) {
            playCriticalNotificationSound()
          }
        } catch {
          // Non-JSON messages are ignored.
        }

        queryClient.invalidateQueries({ queryKey: ['notifications'] })
        queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] })
      }

      ws.onclose = () => {
        if (stoppedRef.current) return
        if (reconnectRef.current) window.clearTimeout(reconnectRef.current)
        reconnectRef.current = window.setTimeout(connect, retryMs)
        retryMs = Math.min(retryMs * 2, 15_000)
      }

      ws.onerror = () => {
        try {
          ws.close()
        } catch {
          // no-op
        }
      }
    }

    connect()

    return () => {
      stoppedRef.current = true
      if (reconnectRef.current) window.clearTimeout(reconnectRef.current)
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
    }
  }, [isAuthenticated, queryClient, user])

  return null
}
