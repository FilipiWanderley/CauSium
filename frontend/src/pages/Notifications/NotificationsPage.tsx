import { type ComponentType, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  Archive,
  Bell,
  CheckCheck,
  Filter,
  Pencil,
  RefreshCw,
  ShieldAlert,
  Trash2,
  Volume2,
  VolumeX,
} from 'lucide-react'
import {
  type AlertCategory,
  type AlertRecord,
  type AlertStatus,
  notificationsApi,
} from '../../api/notifications'
import { useI18n } from '../../contexts/I18nContext'
import {
  isNotificationSoundEnabled,
  setNotificationSoundEnabled,
} from '../../realtime/notificationSound'

type NotificationKind = 'activity' | 'created' | 'updated' | 'deleted' | 'sync' | 'security'

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

const KIND_COLORS: Record<NotificationKind, string> = {
  activity: 'bg-gray-100 text-gray-700',
  created: 'bg-emerald-100 text-emerald-700',
  updated: 'bg-sky-100 text-sky-700',
  deleted: 'bg-rose-100 text-rose-700',
  sync: 'bg-indigo-100 text-indigo-700',
  security: 'bg-red-100 text-red-700',
}

const KIND_ICONS: Record<NotificationKind, ComponentType<{ className?: string }>> = {
  activity: Activity,
  created: Activity,
  updated: Pencil,
  deleted: Trash2,
  sync: RefreshCw,
  security: ShieldAlert,
}

const SEVERITY_RANK: Record<AlertRecord['severity'], number> = {
  critical: 3,
  warning: 2,
  info: 1,
}

const STATUS_RANK: Record<AlertRecord['status'], number> = {
  unread: 3,
  read: 2,
  archived: 1,
}

function classifyNotificationKind(alert: AlertRecord): NotificationKind {
  const sourceType = (alert.source_type ?? '').toLowerCase()
  const blob = `${alert.title} ${alert.body ?? ''} ${sourceType}`.toLowerCase()

  if (alert.category === 'security' || sourceType.includes('worker_failure')) return 'security'
  if (sourceType.includes('cloud_account_sync') || blob.includes('sync')) return 'sync'
  if (blob.includes('created') || blob.includes('.created')) return 'created'
  if (blob.includes('updated') || blob.includes('.updated') || blob.includes('changed')) return 'updated'
  if (
    blob.includes('deleted') ||
    blob.includes('.deleted') ||
    blob.includes('removed') ||
    blob.includes('revoked') ||
    blob.includes('deactivated')
  ) {
    return 'deleted'
  }
  return 'activity'
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
  labelMarkRead,
  labelArchive,
  labelViewDetails,
  categoryLabel,
  kindLabel,
}: {
  alert: AlertRecord
  onMarkRead: (id: string) => void
  onArchive: (id: string) => void
  labelMarkRead: string
  labelArchive: string
  labelViewDetails: string
  categoryLabel: string
  kindLabel: string
}) {
  const isUnread = alert.status === 'unread'
  const kind = classifyNotificationKind(alert)
  const KindIcon = KIND_ICONS[kind]

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
              {categoryLabel}
            </span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${KIND_COLORS[kind]}`}>
              <KindIcon className="mr-1 inline h-3 w-3" />
              {kindLabel}
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
              {labelViewDetails} →
            </a>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-shrink-0 items-center gap-1">
          {isUnread && (
            <button
              onClick={() => onMarkRead(alert.id)}
              title={labelMarkRead}
              className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <CheckCheck className="h-4 w-4" />
            </button>
          )}
          {alert.status !== 'archived' && (
            <button
              onClick={() => onArchive(alert.id)}
              title={labelArchive}
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
  const { t } = useI18n()
  const n = t.notifications

  const CATEGORY_LABELS: Record<AlertCategory, string> = {
    financial:    n.financial,
    optimization: n.optimization,
    governance:   n.governance,
    activity:     n.activity,
    security:     n.security,
  }

  const qc = useQueryClient()

  const [categoryFilter, setCategoryFilter] = useState<AlertCategory | ''>('')
  const [statusFilter, setStatusFilter] = useState<AlertStatus | ''>('')
  const [typeFilter, setTypeFilter] = useState<NotificationKind | ''>('')
  const [soundEnabled, setSoundEnabled] = useState<boolean>(() => isNotificationSoundEnabled())

  const TYPE_LABELS: Record<NotificationKind, string> = {
    activity: n.typeActivity,
    created: n.typeCreated,
    updated: n.typeUpdated,
    deleted: n.typeDeleted,
    sync: n.typeSync,
    security: n.typeSecurity,
  }

  const listQuery = useQuery({
    queryKey: ['notifications', categoryFilter, statusFilter],
    queryFn: () =>
      notificationsApi.list({
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
      }),
  })

  const countQuery = useQuery({
    queryKey: ['notifications-unread-count', categoryFilter],
    queryFn: () => notificationsApi.getUnreadCount({ category: categoryFilter || undefined }),
    refetchInterval: 30_000,
  })

  const patchMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: AlertStatus }) =>
      notificationsApi.patchStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] })
    },
  })

  const markAllMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] })
    },
  })

  const alertsRaw = listQuery.data?.items ?? []
  const alerts = alertsRaw
    .filter((alert) => {
      if (!typeFilter) return true
      return classifyNotificationKind(alert) === typeFilter
    })
    .sort((a, b) => {
      const severityDiff = SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity]
      if (severityDiff !== 0) return severityDiff

      const statusDiff = STATUS_RANK[b.status] - STATUS_RANK[a.status]
      if (statusDiff !== 0) return statusDiff

      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  const unread = countQuery.data?.unread ?? 0
  const critical = countQuery.data?.critical ?? 0
  const totalVisible = alerts.length
  const criticalUnread = alerts.filter((a) => a.severity === 'critical' && a.status === 'unread')

  const listIsPending = listQuery.isPending
  const listIsError = listQuery.isError

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Bell className="h-6 w-6 text-brand-500" />
            {n.title}
            {unread > 0 && (
              <span className="ml-1 rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white">
                {unread}
              </span>
            )}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {n.subtitle}
          </p>
        </div>

        {unread > 0 && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const next = !soundEnabled
                setSoundEnabled(next)
                setNotificationSoundEnabled(next)
              }}
              className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-600 shadow-sm hover:bg-gray-50"
              title={soundEnabled ? n.soundDisable : n.soundEnable}
            >
              {soundEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
              {soundEnabled ? n.soundOn : n.soundOff}
            </button>
            <button
              onClick={() => markAllMutation.mutate()}
              disabled={markAllMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 shadow-sm hover:bg-gray-50 disabled:opacity-50"
            >
              <CheckCheck className="h-4 w-4" />
              {n.markAllRead}
            </button>
          </div>
        )}
      </div>

      {criticalUnread.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-red-600" />
              <div>
                <p className="text-sm font-semibold text-red-700">
                  {n.immediateActionTitle}
                </p>
                <p className="text-xs text-red-600">
                  {n.immediateActionDesc.replace('{{count}}', String(criticalUnread.length))}
                </p>
              </div>
            </div>
            <button
              onClick={() => {
                setStatusFilter('unread')
                setTypeFilter('security')
              }}
              className="rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100"
            >
              {n.focusCritical}
            </button>
          </div>
        </div>
      )}

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">{n.unread}</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{unread}</p>
        </div>
        <div className="rounded-xl border border-red-100 bg-red-50 p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-red-400">{n.critical}</p>
          <p className="mt-1 text-3xl font-bold text-red-600">{critical}</p>
        </div>
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">{n.totalVisible}</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{totalVisible ?? '—'}</p>
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
          <option value="">{n.allCategories}</option>
          {(Object.keys(CATEGORY_LABELS) as AlertCategory[]).map((c) => (
            <option key={c} value={c}>
              {CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as NotificationKind | '')}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">{n.allTypes}</option>
          {(Object.keys(TYPE_LABELS) as NotificationKind[]).map((k) => (
            <option key={k} value={k}>
              {TYPE_LABELS[k]}
            </option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as AlertStatus | '')}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">{n.allStatuses}</option>
          <option value="unread">{n.statusUnread}</option>
          <option value="read">{n.statusRead}</option>
          <option value="archived">{n.statusArchived}</option>
        </select>
      </div>

      {/* List */}
      {listIsPending ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : listIsError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-600">
          {n.error}
        </div>
      ) : alerts.length === 0 ? (
        <div className="rounded-xl border border-gray-100 bg-white p-12 text-center shadow-sm">
          <Bell className="mx-auto mb-3 h-10 w-10 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">{n.noNotifications}</p>
          <p className="mt-1 text-xs text-gray-400">
            {n.emptyHint}
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
              labelMarkRead={n.markRead}
              labelArchive={n.archive}
              labelViewDetails={n.viewDetails}
              categoryLabel={CATEGORY_LABELS[alert.category]}
              kindLabel={TYPE_LABELS[classifyNotificationKind(alert)]}
            />
          ))}
        </div>
      )}
    </div>
  )
}
