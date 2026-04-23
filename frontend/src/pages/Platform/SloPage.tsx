import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, RefreshCw, Siren, Timer } from 'lucide-react'
import clsx from 'clsx'
import { adminApi } from '../../api/admin'
import { useI18n } from '../../contexts/I18nContext'

function SeverityBadge({ severity }: { severity: string }) {
  const className =
    severity === 'critical'
      ? 'bg-red-100 text-red-700'
      : severity === 'warning'
        ? 'bg-amber-100 text-amber-800'
        : 'bg-green-100 text-green-700'

  return <span className={clsx('rounded-full px-2 py-0.5 text-xs font-semibold', className)}>{severity}</span>
}

export function SloPage() {
  const { t } = useI18n()
  const p = t.platform

  const { data, isLoading, isRefetching, refetch } = useQuery({
    queryKey: ['platform-slo-overview'],
    queryFn: () => adminApi.getSloOverview().then((r) => r.data),
    refetchInterval: 30000,
  })

  const alerts = data?.alerts ?? []
  const criticalAlerts = alerts.filter((a) => a.severity === 'critical').length
  const warningAlerts = alerts.filter((a) => a.severity === 'warning').length

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Siren className="h-6 w-6 text-brand-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{p.sloTitle}</h1>
            <p className="text-sm text-gray-500 mt-0.5">{p.sloSubtitle}</p>
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

      {isLoading || !data ? (
        <div className="rounded-xl border border-gray-200 bg-white p-10 text-center text-sm text-gray-500">
          {p.sloLoading}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{p.sloRequests}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">{data.global_sli.requests_total}</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{p.sloErrorRate}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">{data.global_sli.api_error_rate_pct.toFixed(3)}%</p>
              <p className="mt-1 text-xs text-gray-500">
                {p.sloTarget.replace('{{value}}', data.targets.api_error_budget_pct.toFixed(2))}
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{p.sloBurnRate}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">{data.global_sli.error_budget_burn_rate.toFixed(2)}x</p>
              <p className="mt-1 text-xs text-gray-500">{p.sloBurnDesc}</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{p.sloAlerts}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">{alerts.length}</p>
              <p className="mt-1 text-xs text-gray-500">
                {p.sloCriticalWarning
                  .replace('{{c}}', String(criticalAlerts))
                  .replace('{{w}}', String(warningAlerts))}
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-gray-100 flex items-center gap-2">
              <Timer className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-semibold text-gray-700">{p.sloApiPathsTitle}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    <th className="px-5 py-3">{p.sloColPath}</th>
                    <th className="px-4 py-3">{p.sloColReq}</th>
                    <th className="px-4 py-3">{p.sloColErrorPct}</th>
                    <th className="px-4 py-3">{p.sloColP95}</th>
                    <th className="px-4 py-3">{p.sloColAvg}</th>
                    <th className="px-4 py-3">{p.sloColMax}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.api_paths.slice(0, 10).map((row) => (
                    <tr key={row.path} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-3.5 font-mono text-xs text-gray-700">{row.path}</td>
                      <td className="px-4 py-3.5 text-gray-700">{row.requests}</td>
                      <td className="px-4 py-3.5 text-gray-700">{row.error_rate_pct.toFixed(3)}%</td>
                      <td className="px-4 py-3.5 text-gray-700">{row.p95_latency_ms.toFixed(2)}</td>
                      <td className="px-4 py-3.5 text-gray-700">{row.avg_latency_ms.toFixed(2)}</td>
                      <td className="px-4 py-3.5 text-gray-700">{row.max_latency_ms.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-gray-100 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-semibold text-gray-700">{p.sloWorkerTitle}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    <th className="px-5 py-3">{p.sloColWorker}</th>
                    <th className="px-4 py-3">{p.sloColTotal}</th>
                    <th className="px-4 py-3">{p.sloColSuccess}</th>
                    <th className="px-4 py-3">{p.sloColRetry}</th>
                    <th className="px-4 py-3">{p.sloColFailed}</th>
                    <th className="px-4 py-3">{p.sloColErrorPct}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.workers.map((w) => (
                    <tr key={w.worker} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-3.5 font-medium text-gray-900">{w.worker}</td>
                      <td className="px-4 py-3.5 text-gray-700">{w.total}</td>
                      <td className="px-4 py-3.5 text-green-700">{w.success}</td>
                      <td className="px-4 py-3.5 text-amber-700">{w.retry}</td>
                      <td className="px-4 py-3.5 text-red-700">{w.failed}</td>
                      <td className="px-4 py-3.5 text-gray-700">{w.error_rate_pct.toFixed(3)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-gray-100 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-semibold text-gray-700">{p.sloAlertsTitle}</span>
            </div>
            {!alerts.length ? (
              <div className="p-6 text-sm text-green-700 bg-green-50">{p.sloNoAlerts}</div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {alerts.map((alert, idx) => (
                  <li key={`${alert.scope}-${alert.title}-${idx}`} className="p-5 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={alert.severity} />
                      <span className="text-sm font-semibold text-gray-900">{alert.title}</span>
                    </div>
                    <p className="text-sm text-gray-600">{alert.detail}</p>
                    <p className="text-sm text-gray-800">
                      <span className="font-semibold">{p.sloAlertAction}</span> {alert.recommended_action}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  )
}
