import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { adminApi } from '../../api/admin'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { KpiCard } from '../../components/Cards/KpiCard'
import { PageHeader } from '../../components/Layout/PageHeader'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { SkeletonMetricCards, SkeletonTable } from '../../components/UX/Skeleton'

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
  usePageTitle('SLO')
  const { t } = useI18n()
  const p = t.platform

  const { data, isLoading, isError, isRefetching, refetch } = useQuery({
    queryKey: ['platform-slo-overview'],
    queryFn: () => adminApi.getSloOverview().then((r) => r.data),
    refetchInterval: 30000,
  })

  const alerts = data?.alerts ?? []
  const criticalAlerts = alerts.filter((a) => a.severity === 'critical').length
  const warningAlerts = alerts.filter((a) => a.severity === 'warning').length

  return (
    <div className="page-container max-w-7xl">
      <PageHeader
        title={p.sloTitle}
        subtitle={p.sloSubtitle}
        meta={
          <>
            <span>Platform administration</span>
            <span>Reliability overview</span>
          </>
        }
        actions={
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
          >
            <RefreshCw className={clsx('h-4 w-4', isRefetching && 'animate-spin')} />
            {p.refresh}
          </button>
        }
      />

      {isLoading ? (
        <div className="space-y-4">
          <SkeletonMetricCards count={4} />
          <SkeletonTable rows={8} columns={6} />
        </div>
      ) : isError || !data ? (
        <ErrorState
          title="Could not load SLO overview"
          description="Service reliability data is temporarily unavailable. Please try again."
          onRetry={() => refetch()}
          retryLabel="Retry"
        />
      ) : (
        <>
          <div className="kpi-grid">
            <KpiCard
              title={p.sloRequests}
              value={data.global_sli.requests_total}
              compact
              footer={<span>Total observed API requests.</span>}
            />
            <KpiCard
              title={p.sloErrorRate}
              value={`${data.global_sli.api_error_rate_pct.toFixed(3)}%`}
              compact
              tone={data.global_sli.api_error_rate_pct > data.targets.api_error_budget_pct ? 'negative' : 'positive'}
              footer={<span>{p.sloTarget.replace('{{value}}', data.targets.api_error_budget_pct.toFixed(2))}</span>}
            />
            <KpiCard
              title={p.sloBurnRate}
              value={`${data.global_sli.error_budget_burn_rate.toFixed(2)}x`}
              compact
              tone={data.global_sli.error_budget_burn_rate > 1 ? 'warning' : 'neutral'}
              footer={<span>{p.sloBurnDesc}</span>}
            />
            <KpiCard
              title={p.sloAlerts}
              value={alerts.length}
              compact
              tone={criticalAlerts > 0 ? 'negative' : warningAlerts > 0 ? 'warning' : 'positive'}
              footer={
                <span>
                  {p.sloCriticalWarning
                    .replace('{{c}}', String(criticalAlerts))
                    .replace('{{w}}', String(warningAlerts))}
                </span>
              }
            />
          </div>

          <Panel flush className="overflow-hidden">
            <div className="border-b border-slate-100 px-5 py-4">
              <PanelHeader
                title={p.sloApiPathsTitle}
                subtitle="Track API request volume, error rate, and latency on the most visible paths."
              />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColPath}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColReq}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColErrorPct}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColP95}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColAvg}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColMax}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {data.api_paths.slice(0, 10).map((row) => (
                    <tr key={row.path} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-5 py-3.5 font-mono text-xs text-gray-700">{row.path}</td>
                      <td className="px-4 py-3.5 tabular-nums text-gray-700">{row.requests}</td>
                      <td className="px-4 py-3.5 tabular-nums text-gray-700">{row.error_rate_pct.toFixed(3)}%</td>
                      <td className="px-4 py-3.5 tabular-nums text-gray-700">{row.p95_latency_ms.toFixed(2)}</td>
                      <td className="px-4 py-3.5 tabular-nums text-gray-700">{row.avg_latency_ms.toFixed(2)}</td>
                      <td className="px-4 py-3.5 tabular-nums text-gray-700">{row.max_latency_ms.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel flush className="overflow-hidden">
            <div className="border-b border-slate-100 px-5 py-4">
              <PanelHeader
                title={p.sloWorkerTitle}
                subtitle="Review worker execution reliability, retry pressure, and failure rate."
              />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColWorker}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColTotal}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColSuccess}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColRetry}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColFailed}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColErrorPct}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {data.workers.map((w) => (
                    <tr key={w.worker} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-5 py-3.5 font-medium text-gray-900">{w.worker}</td>
                      <td className="px-4 py-3.5 tabular-nums text-gray-700">{w.total}</td>
                      <td className="px-4 py-3.5 tabular-nums text-green-700">{w.success}</td>
                      <td className="px-4 py-3.5 tabular-nums text-amber-700">{w.retry}</td>
                      <td className="px-4 py-3.5 tabular-nums text-red-700">{w.failed}</td>
                      <td className="px-4 py-3.5 tabular-nums text-gray-700">{w.error_rate_pct.toFixed(3)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel flush className="overflow-hidden">
            <div className="border-b border-slate-100 px-5 py-4">
              <PanelHeader
                title={p.sloAlertsTitle}
                subtitle="Surface recommended follow-up for the most urgent reliability issues."
              />
            </div>
            {!alerts.length ? (
              <div className="p-5">
                <EmptyState icon="lightbulb" title={p.sloNoAlerts} />
              </div>
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
          </Panel>
        </>
      )}
    </div>
  )
}


