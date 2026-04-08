import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, Bell, CheckCheck, Filter } from 'lucide-react'
import {
  type AlertCategory,
  type AlertRecord,
  type AlertStatus,
  notificationsApi,
} from '../../api/notifications'

const CATEGORY_LABELS: Record<AlertCategory, string> = {
  financial: 'Financial',
  optimization: 'Optimization',
  governance: 'Governance',
  activity: 'Activity',
  security: 'Security',
}

const SEVERITY_COLORS: Record<string, string> = {
  info: 'bg-blue-50 text-blue-700 border-blue-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  critical: 'bg-red-50 text-red-700 border-red-200',
}

const CATEGORY_COLORS: Record<AlertCategory, string> = {
  financial: 'bg-emerald-100 text-emerald-700',
  optimization: 'bg-violet-100 text-violet-700',
  governance: 'bg-sky-100 text-sky-700',
  activity: 'bg-gray-100 text-gray-600',
  security: 'bg-red-100 text-red-700',
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function AlertCard({
  alert,
  onMarkRead,
  onArchive,
}: {
  alert: AlertRecord
  onMarkRead: (id: string) => void
  onArchive: (id: string) => void
}) {
  const isUnread = alert.status === 'unread'

  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        isUnread ? 'border-brand-200 bg-white shadow-sm' : 'border-gray-100 bg-gray-50'
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Unread dot */}
        <div className="mt-1.5 flex-shrink-0">
          {isUnread ? (
            <span className="block h-2.5 w-2.5 rounded-full bg-brand-500" />
          ) : (
            <span className="block h-2.5 w-2.5 rounded-full bg-gray-300" />
          )}
        </div>

        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                CATEGORY_COLORS[alert.category]
              }`}
            >
              {CATEGORY_LABELS[alert.category]}
            </span>
            <span
              className={`rounded border px-2 py-0.5 text-xs font-semibold capitalize ${
                SEVERITY_COLORS[alert.severity] ?? SEVERITY_COLORS.info
              }`}
            >
              {alert.severity}
            </span>
            <span className="ml-auto text-xs text-gray-400">{timeAgo(alert.created_at)}</span>
          </div>

          <p className={`text-sm font-medium ${isUnread ? 'text-gray-900' : 'text-gray-600'}`}>
            {alert.title}
          </p>

          {alert.body && <p className="line-clamp-2 text-xs text-gray-500">{alert.body}</p>}

          {alert.action_url && (
            <a
              href={alert.action_url}
              className="text-xs text-brand-600 hover:underline"
              rel="noreferrer"
            >
              View details →
            </a>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-shrink-0 items-center gap-1">
          {isUnread && (
            <button
              onClick={() => onMarkRead(alert.id)}
              title="Mark as read"
              className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <CheckCheck className="h-4 w-4" />
            </button>
          )}
          {alert.status !== 'archived' && (
            <button
              onClick={() => onArchive(alert.id)}
              title="Archive"
              className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <Archive className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function NotificationsPage() {
  const qc = useQueryClient()

  const [categoryFilter, setCategoryFilter] = useState<AlertCategory | ''>('')
  const [statusFilter, setStatusFilter] = useState<AlertStatus | ''>('')

  const listQuery = useQuery({
    queryKey: ['notifications', categoryFilter, statusFilter],
    queryFn: () =>
      notificationsApi.list({
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
      }),
  })

  const countQuery = useQuery({
    queryKey: ['notifications-count'],
    queryFn: notificationsApi.getUnreadCount,
    refetchInterval: 30_000,
  })

  const patchMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: AlertStatus }) =>
      notificationsApi.patchStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['notifications-count'] })
    },
  })

  const markAllMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['notifications-count'] })
    },
  })

  const alerts = listQuery.data?.items ?? []
  const unread = countQuery.data?.unread ?? 0
  const critical = countQuery.data?.critical ?? 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Bell className="h-6 w-6 text-brand-500" />
            Notifications
            {unread > 0 && (
              <span className="ml-1 rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white">
                {unread}
              </span>
            )}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Workspace-wide alerts, budget breaches, and optimization signals.
          </p>
        </div>

        {unread > 0 && (
          <button
            onClick={() => markAllMutation.mutate()}
            disabled={markAllMutation.isPending}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 shadow-sm hover:bg-gray-50 disabled:opacity-50"
          >
            <CheckCheck className="h-4 w-4" />
            Mark all read
          </button>
        )}
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Unread</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{unread}</p>
        </div>
        <div className="rounded-xl border border-red-100 bg-red-50 p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-red-400">Critical</p>
          <p className="mt-1 text-3xl font-bold text-red-600">{critical}</p>
        </div>
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Total Visible</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{listQuery.data?.total ?? '—'}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
        <Filter className="h-4 w-4 text-gray-400" />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value as AlertCategory | '')}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All categories</option>
          {(Object.keys(CATEGORY_LABELS) as AlertCategory[]).map((c) => (
            <option key={c} value={c}>
              {CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as AlertStatus | '')}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All statuses</option>
          <option value="unread">Unread</option>
          <option value="read">Read</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {/* List */}
      {listQuery.isPending ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : listQuery.isError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-600">
          Failed to load notifications. The backend service may still be initializing.
        </div>
      ) : alerts.length === 0 ? (
        <div className="rounded-xl border border-gray-100 bg-white p-12 text-center shadow-sm">
          <Bell className="mx-auto mb-3 h-10 w-10 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No notifications match your filters.</p>
          <p className="mt-1 text-xs text-gray-400">
            Alerts are generated from risk budget breaches, optimization signals, and workspace
            events.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onMarkRead={(id) => patchMutation.mutate({ id, status: 'read' })}
              onArchive={(id) => patchMutation.mutate({ id, status: 'archived' })}
            />
          ))}
        </div>
      )}
    </div>
  )
}
