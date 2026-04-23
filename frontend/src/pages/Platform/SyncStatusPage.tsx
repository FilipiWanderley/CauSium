import { useMemo } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, RefreshCw, ServerCog } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'
import { cloudAccountsApi } from '../../api/cloudAccounts'
import type { CloudProvider, ConnectorStatus } from '../../types'
import { useI18n } from '../../contexts/I18nContext'

const STATUS_BADGE: Record<ConnectorStatus, string> = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-700',
  error: 'bg-red-100 text-red-700',
  pending: 'bg-yellow-100 text-yellow-700',
}

type AttentionFilter = 'all' | 'needs_attention' | 'healthy'
type SortKey = 'attention_first' | 'open_dlq_desc' | 'last_sync_desc' | 'name_asc'
type PageSize = 10 | 25 | 50

const DEFAULT_PROVIDER: CloudProvider | 'all' = 'all'
const DEFAULT_STATUS: ConnectorStatus | 'all' = 'all'
const DEFAULT_ATTENTION: AttentionFilter = 'all'
const DEFAULT_SORT: SortKey = 'attention_first'
const DEFAULT_PAGE_SIZE: PageSize = 25

const PROVIDER_OPTIONS: Array<CloudProvider | 'all'> = ['all', 'azure', 'aws', 'gcp']
const STATUS_OPTIONS: Array<ConnectorStatus | 'all'> = ['all', 'active', 'pending', 'inactive', 'error']
const ATTENTION_OPTIONS: AttentionFilter[] = ['all', 'needs_attention', 'healthy']
const SORT_OPTIONS: SortKey[] = ['attention_first', 'open_dlq_desc', 'last_sync_desc', 'name_asc']
const PAGE_SIZE_OPTIONS: PageSize[] = [10, 25, 50]

function isInOptions<T extends string>(value: string | null, options: readonly T[]): value is T {
  return value !== null && options.includes(value as T)
}

export function SyncStatusPage() {
  const { user } = useAuth()
  const { t, lang } = useI18n()
  const p = t.platform
  const locale = lang === 'pt' ? 'pt-BR' : 'en-US'
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  const formatDate = (value: string | null) =>
    value ? new Date(value).toLocaleString(locale) : t.dashboard.never

  const providerRaw = searchParams.get('provider')
  const statusRaw = searchParams.get('status')
  const attentionRaw = searchParams.get('attention')
  const sortRaw = searchParams.get('sort')

  const providerFilter = isInOptions(providerRaw, PROVIDER_OPTIONS) ? providerRaw : DEFAULT_PROVIDER
  const statusFilter = isInOptions(statusRaw, STATUS_OPTIONS) ? statusRaw : DEFAULT_STATUS
  const attentionFilter = isInOptions(attentionRaw, ATTENTION_OPTIONS) ? attentionRaw : DEFAULT_ATTENTION
  const sortKey = isInOptions(sortRaw, SORT_OPTIONS) ? sortRaw : DEFAULT_SORT

  const pageSizeRaw = Number(searchParams.get('pageSize'))
  const pageSize: PageSize = PAGE_SIZE_OPTIONS.includes(pageSizeRaw as PageSize)
    ? (pageSizeRaw as PageSize)
    : DEFAULT_PAGE_SIZE

  const pageRaw = Number(searchParams.get('page'))
  const page = Number.isInteger(pageRaw) && pageRaw > 0 ? pageRaw : 1

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
      if (sortKey === 'open_dlq_desc') return b.open_dlq_count - a.open_dlq_count
      if (sortKey === 'last_sync_desc') {
        const aTs = a.last_sync_at ? new Date(a.last_sync_at).getTime() : 0
        const bTs = b.last_sync_at ? new Date(b.last_sync_at).getTime() : 0
        return bTs - aTs
      }
      if (sortKey === 'name_asc') return a.display_name.localeCompare(b.display_name)
      if (a.needs_attention !== b.needs_attention) return a.needs_attention ? -1 : 1
      return b.open_dlq_count - a.open_dlq_count
    })

    return items
  }, [data, providerFilter, statusFilter, attentionFilter, sortKey])

  const totalPages = Math.max(1, Math.ceil(filteredData.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredData.slice(start, start + pageSize)
  }, [filteredData, currentPage, pageSize])

  const syncingAccountId = syncMutation.isPending ? syncMutation.variables : null

  const updateParams = (
    updates: Partial<Record<'provider' | 'status' | 'attention' | 'sort' | 'pageSize' | 'page', string>>
  ) => {
    const next = new URLSearchParams(searchParams)
    const merged = {
      provider: updates.provider ?? providerFilter,
      status: updates.status ?? statusFilter,
      attention: updates.attention ?? attentionFilter,
      sort: updates.sort ?? sortKey,
      pageSize: updates.pageSize ?? String(pageSize),
      page: updates.page ?? String(page),
    }

    if (merged.provider === DEFAULT_PROVIDER) next.delete('provider')
    else next.set('provider', merged.provider)

    if (merged.status === DEFAULT_STATUS) next.delete('status')
    else next.set('status', merged.status)

    if (merged.attention === DEFAULT_ATTENTION) next.delete('attention')
    else next.set('attention', merged.attention)

    if (merged.sort === DEFAULT_SORT) next.delete('sort')
    else next.set('sort', merged.sort)

    if (Number(merged.pageSize) === DEFAULT_PAGE_SIZE) next.delete('pageSize')
    else next.set('pageSize', merged.pageSize)

    if (Number(merged.page) <= 1) next.delete('page')
    else next.set('page', merged.page)

    setSearchParams(next)
  }

  const handleTriggerSync = (accountId: string) => {
    if (!syncMutation.isPending) syncMutation.mutate(accountId)
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <ServerCog className="h-6 w-6 text-brand-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{p.syncTitle}</h1>
            <p className="text-sm text-gray-500 mt-0.5">{p.syncSubtitle}</p>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
        >
          <RefreshCw className={clsx('h-4 w-4', isRefetching && 'animate-spin')} />
          {p.refresh}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{p.syncAccounts}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{summary.total}</p>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-xs text-red-700 uppercase tracking-wide">{p.syncNeedsAttention}</p>
          <p className="mt-1 text-2xl font-bold text-red-800">{summary.attention}</p>
        </div>
        <div className="rounded-xl border border-green-200 bg-green-50 p-4">
          <p className="text-xs text-green-700 uppercase tracking-wide">{p.syncHealthy}</p>
          <p className="mt-1 text-2xl font-bold text-green-800">{summary.healthy}</p>
        </div>
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-xs text-amber-700 uppercase tracking-wide">{p.syncOpenDlq}</p>
          <p className="mt-1 text-2xl font-bold text-amber-800">{summary.openDlq}</p>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-gray-100">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <span className="text-sm font-semibold text-gray-700">{p.syncConnectorOps}</span>
            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={providerFilter}
                onChange={(e) => updateParams({ provider: e.target.value, page: '1' })}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="all">{p.syncAllProviders}</option>
                <option value="azure">Azure</option>
                <option value="aws">AWS</option>
                <option value="gcp">GCP</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => updateParams({ status: e.target.value, page: '1' })}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="all">{p.syncAllStatus}</option>
                <option value="active">{p.syncStatusActive}</option>
                <option value="pending">{p.syncStatusPending}</option>
                <option value="inactive">{p.syncStatusInactive}</option>
                <option value="error">{p.syncStatusError}</option>
              </select>

              <select
                value={attentionFilter}
                onChange={(e) => updateParams({ attention: e.target.value, page: '1' })}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="all">{p.syncAllAttention}</option>
                <option value="needs_attention">{p.syncNeedsAttentionFilter}</option>
                <option value="healthy">{p.syncHealthyOnly}</option>
              </select>

              <select
                value={sortKey}
                onChange={(e) => updateParams({ sort: e.target.value, page: '1' })}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="attention_first">{p.syncSortAttentionFirst}</option>
                <option value="open_dlq_desc">{p.syncSortDlqDesc}</option>
                <option value="last_sync_desc">{p.syncSortLatestSync}</option>
                <option value="name_asc">{p.syncSortNameAsc}</option>
              </select>

              <select
                value={pageSize}
                onChange={(e) => updateParams({ pageSize: e.target.value, page: '1' })}
                className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {p.syncPerPage.replace('{{n}}', String(n))}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {syncMutation.isError && (
          <div className="mx-5 mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {p.syncErrorMsg}
          </div>
        )}

        {syncMutation.isSuccess && (
          <div className="mx-5 mt-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
            {p.syncSuccessMsg}
          </div>
        )}

        {isLoading ? (
          <div className="py-12 text-center text-sm text-gray-400">{t.common.loading}</div>
        ) : !filteredData.length ? (
          <div className="py-12 text-center text-sm text-gray-500">{p.syncNoAccounts}</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-5 py-3">{p.syncColAccount}</th>
                <th className="px-4 py-3">{p.syncColProvider}</th>
                <th className="px-4 py-3">{p.syncColStatus}</th>
                <th className="px-4 py-3">{p.syncColLastSync}</th>
                <th className="px-4 py-3">{p.syncColLastHealth}</th>
                <th className="px-4 py-3">{p.syncColOpenDlq}</th>
                <th className="px-4 py-3 text-center">{p.syncColAttention}</th>
                <th className="px-4 py-3 text-right">{p.syncColAction}</th>
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
                        item.open_dlq_count > 0 ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'
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
                          {p.syncAttentionYes}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-700">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          {p.syncAttentionOk}
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
                          className={clsx('h-3.5 w-3.5', syncingAccountId === item.account_id && 'animate-spin')}
                        />
                        {syncingAccountId === item.account_id ? p.syncQueueing : p.syncTrigger}
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
              {p.syncShowing
                .replace('{{from}}', String((currentPage - 1) * pageSize + 1))
                .replace('{{to}}', String(Math.min(currentPage * pageSize, filteredData.length)))
                .replace('{{total}}', String(filteredData.length))}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => updateParams({ page: String(Math.max(1, currentPage - 1)) })}
                disabled={currentPage <= 1}
                className="rounded p-1 text-gray-400 hover:bg-gray-100 disabled:opacity-40"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span>
                {p.syncPage
                  .replace('{{current}}', String(currentPage))
                  .replace('{{total}}', String(totalPages))}
              </span>
              <button
                onClick={() => updateParams({ page: String(Math.min(totalPages, currentPage + 1)) })}
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
