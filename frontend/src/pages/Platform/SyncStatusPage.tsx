import { useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, RefreshCw, ServerCog } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'
import { cloudAccountsApi } from '../../api/cloudAccounts'
import type { CloudProvider, ConnectorStatus } from '../../types'

const STATUS_BADGE: Record<ConnectorStatus, string> = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-700',
  error: 'bg-red-100 text-red-700',
  pending: 'bg-yellow-100 text-yellow-700',
}

function formatDate(value: string | null): string {
  if (!value) return 'Never'
  return new Date(value).toLocaleString()
}

type AttentionFilter = 'all' | 'needs_attention' | 'healthy'
type SortKey = 'attention_first' | 'open_dlq_desc' | 'last_sync_desc' | 'name_asc'
type PageSize = 10 | 25 | 50

export function SyncStatusPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [providerFilter, setProviderFilter] = useState<CloudProvider | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<ConnectorStatus | 'all'>('all')
  const [attentionFilter, setAttentionFilter] = useState<AttentionFilter>('all')
  const [sortKey, setSortKey] = useState<SortKey>('attention_first')
  const [pageSize, setPageSize] = useState<PageSize>(25)
  const [page, setPage] = useState(1)

  if (user?.role !== 'platform_admin') {
    return <Navigate to="/app/dashboard" replace />
  }

  const { data, isLoading, isRefetching, refetch } = useQuery({
    queryKey: ['platform-sync-status'],
    queryFn: () => cloudAccountsApi.syncStatus().then((r) => r.data),
    refetchInterval: 30000,
  })

  const syncMutation = useMutation({
    mutationFn: (accountId: string) => cloudAccountsApi.sync(accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform-sync-status'] })
    },
  })

  const summary = useMemo(() => {
    const items = data ?? []
    return {
      total: items.length,
      attention: items.filter((item) => item.needs_attention).length,
      healthy: items.filter((item) => item.connector_status === 'active' && item.open_dlq_count === 0).length,
      openDlq: items.reduce((acc, item) => acc + item.open_dlq_count, 0),
    }
  }, [data])

  const filteredData = useMemo(() => {
    const items = [...(data ?? [])]
      .filter((item) => (providerFilter === 'all' ? true : item.provider === providerFilter))
      .filter((item) => (statusFilter === 'all' ? true : item.connector_status === statusFilter))
      .filter((item) => {
        if (attentionFilter === 'all') return true
        if (attentionFilter === 'needs_attention') return item.needs_attention
        return !item.needs_attention
      })

    items.sort((a, b) => {
      if (sortKey === 'open_dlq_desc') {
        return b.open_dlq_count - a.open_dlq_count
      }

      if (sortKey === 'last_sync_desc') {
        const aTs = a.last_sync_at ? new Date(a.last_sync_at).getTime() : 0
        const bTs = b.last_sync_at ? new Date(b.last_sync_at).getTime() : 0
        return bTs - aTs
      }

      if (sortKey === 'name_asc') {
        return a.display_name.localeCompare(b.display_name)
      }

      if (a.needs_attention !== b.needs_attention) {
        return a.needs_attention ? -1 : 1
      }
      return b.open_dlq_count - a.open_dlq_count
    })

    return items
  }, [data, providerFilter, statusFilter, attentionFilter, sortKey])

  useEffect(() => {
    setPage(1)
  }, [providerFilter, statusFilter, attentionFilter, sortKey, pageSize])

  const totalPages = Math.max(1, Math.ceil(filteredData.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredData.slice(start, start + pageSize)
  }, [filteredData, currentPage, pageSize])

  const syncingAccountId = syncMutation.isPending ? syncMutation.variables : null

  const handleTriggerSync = (accountId: string) => {
    if (!syncMutation.isPending) {
      syncMutation.mutate(accountId)
    }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <ServerCog className="h-6 w-6 text-brand-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Platform Sync Status</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Operational visibility for connector health and ingestion backlog.
            </p>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
        >
          <RefreshCw className={clsx('h-4 w-4', isRefetching && 'animate-spin')} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Accounts</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{summary.total}</p>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-xs text-red-700 uppercase tracking-wide">Needs Attention</p>
          <p className="mt-1 text-2xl font-bold text-red-800">{summary.attention}</p>
        </div>
        <div className="rounded-xl border border-green-200 bg-green-50 p-4">
          <p className="text-xs text-green-700 uppercase tracking-wide">Healthy</p>
          <p className="mt-1 text-2xl font-bold text-green-800">{summary.healthy}</p>
        </div>
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-xs text-amber-700 uppercase tracking-wide">Open DLQ</p>
          <p className="mt-1 text-2xl font-bold text-amber-800">{summary.openDlq}</p>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-gray-100">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <span className="text-sm font-semibold text-gray-700">Connector Operations</span>
            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={providerFilter}
                onChange={(e) => setProviderFilter(e.target.value as CloudProvider | 'all')}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="all">All providers</option>
                <option value="azure">Azure</option>
                <option value="aws">AWS</option>
                <option value="gcp">GCP</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as ConnectorStatus | 'all')}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="all">All status</option>
                <option value="active">Active</option>
                <option value="pending">Pending</option>
                <option value="inactive">Inactive</option>
                <option value="error">Error</option>
              </select>

              <select
                value={attentionFilter}
                onChange={(e) => setAttentionFilter(e.target.value as AttentionFilter)}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="all">All attention</option>
                <option value="needs_attention">Needs attention</option>
                <option value="healthy">Healthy only</option>
              </select>

              <select
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as SortKey)}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="attention_first">Sort: Attention first</option>
                <option value="open_dlq_desc">Sort: DLQ high to low</option>
                <option value="last_sync_desc">Sort: Latest sync</option>
                <option value="name_asc">Sort: Name A-Z</option>
              </select>

              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value) as PageSize)}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value={10}>10 / page</option>
                <option value={25}>25 / page</option>
                <option value={50}>50 / page</option>
              </select>
            </div>
          </div>
        </div>

        {syncMutation.isError && (
          <div className="mx-5 mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            Could not trigger sync for this account. Please try again.
          </div>
        )}

        {syncMutation.isSuccess && (
          <div className="mx-5 mt-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
            Sync job queued successfully.
          </div>
        )}

        {isLoading ? (
          <div className="py-12 text-center text-sm text-gray-400">Loading sync status...</div>
        ) : !filteredData.length ? (
          <div className="py-12 text-center text-sm text-gray-500">No cloud accounts found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-5 py-3">Account</th>
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Last Sync</th>
                <th className="px-4 py-3">Last Health Check</th>
                <th className="px-4 py-3">Open DLQ</th>
                <th className="px-4 py-3 text-center">Attention</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {paginatedData.map((item) => (
                <tr key={item.account_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3.5">
                    <p className="font-semibold text-gray-900">{item.display_name}</p>
                    <p className="text-xs text-gray-400 font-mono">{item.account_id}</p>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 uppercase">
                      {item.provider}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span
                      className={clsx(
                        'rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase',
                        STATUS_BADGE[item.connector_status] ?? 'bg-gray-100 text-gray-600'
                      )}
                    >
                      {item.connector_status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-gray-600">{formatDate(item.last_sync_at)}</td>
                  <td className="px-4 py-3.5 text-gray-600">{formatDate(item.last_health_check_at)}</td>
                  <td className="px-4 py-3.5">
                    <span
                      className={clsx(
                        'rounded-full px-2.5 py-0.5 text-xs font-semibold',
                        item.open_dlq_count > 0
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-gray-100 text-gray-600'
                      )}
                    >
                      {item.open_dlq_count}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex justify-center">
                      {item.needs_attention ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          Yes
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-700">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          OK
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex justify-end">
                      <button
                        onClick={() => handleTriggerSync(item.account_id)}
                        disabled={syncMutation.isPending}
                        className="inline-flex items-center gap-1 rounded-lg border border-brand-200 bg-brand-50 px-2.5 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-100 disabled:opacity-60"
                      >
                        <RefreshCw
                          className={clsx(
                            'h-3.5 w-3.5',
                            syncingAccountId === item.account_id && 'animate-spin'
                          )}
                        />
                        {syncingAccountId === item.account_id ? 'Queueing...' : 'Trigger Sync'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {!isLoading && filteredData.length > 0 && (
          <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3 text-xs text-gray-500">
            <span>
              Showing {(currentPage - 1) * pageSize + 1}-
              {Math.min(currentPage * pageSize, filteredData.length)} of {filteredData.length}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                className="rounded p-1 text-gray-400 hover:bg-gray-100 disabled:opacity-40"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span>
                Page {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className="rounded p-1 text-gray-400 hover:bg-gray-100 disabled:opacity-40"
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
