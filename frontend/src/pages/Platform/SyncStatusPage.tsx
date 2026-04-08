import { useMemo } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, RefreshCw, ServerCog } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'
import { cloudAccountsApi } from '../../api/cloudAccounts'
import type { ConnectorStatus } from '../../types'

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

export function SyncStatusPage() {
  const { user } = useAuth()

  if (user?.role !== 'platform_admin') {
    return <Navigate to="/app/dashboard" replace />
  }

  const { data, isLoading, isRefetching, refetch } = useQuery({
    queryKey: ['platform-sync-status'],
    queryFn: () => cloudAccountsApi.syncStatus().then((r) => r.data),
    refetchInterval: 30000,
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
          <span className="text-sm font-semibold text-gray-700">Connector Operations</span>
        </div>

        {isLoading ? (
          <div className="py-12 text-center text-sm text-gray-400">Loading sync status...</div>
        ) : !data?.length ? (
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
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((item) => (
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
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
