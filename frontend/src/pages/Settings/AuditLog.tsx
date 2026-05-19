import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { AxiosResponse } from 'axios'
import { auditChainApi } from '../../api/auditChain'
import type { AuditEventItem, Page } from '../../api/auditChain'
import { useAuth } from '../../hooks/useAuth'
import { useI18n } from '../../contexts/I18nContext'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { SkeletonTable } from '../../components/UX/Skeleton'

const PAGE_SIZE = 25

const EVENT_TYPE_OPTIONS = [
  '',
  'auth.password.login',
  'auth.password.changed',
  'auth.password.admin_reset',
  'auth.mfa.totp.enabled',
  'auth.mfa.totp.disabled',
  'auth.mfa.admin_reset',
  'auth.passkey.registered',
  'auth.passkey.login',
  'auth.passkey.revoked',
  'auth.user.deactivated',
  'auth.user.updated',
  'auth.user.deleted',
  'invite.created',
  'opportunity.recommendation.generated',
  'opportunity.decision.recorded',
]

export function AuditLog() {
  const { t, lang } = useI18n()
  const { user } = useAuth()
  const orgId = user?.org_id
  const locale = lang === 'pt' ? 'pt-BR' : 'en-US'

  const [page, setPage] = useState(1)
  const [eventTypeFilter, setEventTypeFilter] = useState('')
  const [createdAfter, setCreatedAfter] = useState('')

  const { data, isLoading, error, refetch } = useQuery<AxiosResponse<Page<AuditEventItem>>>({
    queryKey: ['audit-events', orgId, page, eventTypeFilter, createdAfter],
    queryFn: () =>
      auditChainApi.listAuthEvents(orgId!, page, PAGE_SIZE, {
        eventType: eventTypeFilter || undefined,
        createdAfter: createdAfter || undefined,
      }),
    enabled: !!orgId,
  })

  if (!orgId) {
    return <EmptyState icon="document" title="Audit log unavailable" description="Organization context is not available for this session." />
  }

  const items = data?.data.items ?? []
  const total = data?.data.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const resetFilters = () => {
    setEventTypeFilter('')
    setCreatedAfter('')
    setPage(1)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Audit log</h2>
        <span className="text-xs text-gray-400 tabular-nums">{total.toLocaleString(locale)} events</span>
      </div>

      <div className="rounded-xl border border-blue-100 bg-blue-50/60 px-4 py-3">
        <p className="text-xs font-semibold text-blue-900">SAFE DSS posture</p>
        <p className="mt-1 text-xs text-blue-800">
          CauSium provides decision support only. Approvals, dismissals, and operational validation remain explicit human decisions and are auditable.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <select
          value={eventTypeFilter}
          onChange={(e) => { setEventTypeFilter(e.target.value); setPage(1) }}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        >
          <option value="">{t.common.all}</option>
          {EVENT_TYPE_OPTIONS.filter(Boolean).map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <input
          type="datetime-local"
          value={createdAfter}
          onChange={(e) => { setCreatedAfter(e.target.value); setPage(1) }}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        />

        <button
          onClick={resetFilters}
          className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
        >
          {t.common.reset}
        </button>
      </div>

      {isLoading ? (
        <SkeletonTable rows={8} columns={6} />
      ) : error ? (
        <ErrorState
          title="Could not load audit events"
          description="The audit log is temporarily unavailable. Please try again."
          onRetry={() => refetch()}
          retryLabel="Retry"
        />
      ) : items.length === 0 ? (
        <EmptyState icon="document" title="No events found" description="No audit events match the current filters." />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left">
                <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400 whitespace-nowrap">Time (UTC)</th>
                <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400 whitespace-nowrap">Event</th>
                <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Entity</th>
                <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Entity ID</th>
                <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Actor</th>
                <th className="pb-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((ev) => (
                <tr key={ev.id} className="transition hover:bg-gray-50/50">
                  <td className="py-3 pr-4 whitespace-nowrap tabular-nums text-gray-700">
                    {new Date(ev.created_at).toISOString().replace('T', ' ').slice(0, 19)} UTC
                  </td>
                  <td className="py-3 pr-4 font-mono text-xs whitespace-nowrap text-gray-700">{ev.event_type}</td>
                  <td className="py-3 pr-4 text-gray-700">{ev.entity_type}</td>
                  <td className="py-3 pr-4 font-mono text-xs text-gray-500 max-w-[10rem] truncate" title={ev.entity_id}>
                    {ev.entity_id}
                  </td>
                  <td className="py-3 pr-4 font-mono text-xs text-gray-500 max-w-[10rem] truncate" title={ev.actor_user_id ?? ''}>
                    {ev.actor_user_id ?? '—'}
                  </td>
                  <td className="py-3 text-gray-600 max-w-[28rem] truncate" title={JSON.stringify(ev.payload)}>
                    {JSON.stringify(ev.payload)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm text-gray-600">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-lg border border-gray-300 px-4 py-2 hover:bg-gray-50 disabled:opacity-50"
          >
            {t.common.previous}
          </button>
          <span className="text-xs text-gray-500 tabular-nums">Page {page} / {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-lg border border-gray-300 px-4 py-2 hover:bg-gray-50 disabled:opacity-50"
          >
            {t.common.next}
          </button>
        </div>
      )}
    </div>
  )
}
