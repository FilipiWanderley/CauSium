import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { adminApi } from '../../api/admin'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { KpiCard } from '../../components/Cards/KpiCard'
import { PageHeader } from '../../components/Layout/PageHeader'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { ResponsivePrimaryCell } from '../../components/Tables/cells'
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
    <div className="page-container">
      <PageHeader
        title={p.sloTitle}
        subtitle={p.sloSubtitle}
        meta={
          <>
            <span>Platform health</span>
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
              footer={<span>Total observed API requests across the current monitoring window.</span>}
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

          <Panel className="border-slate-200 bg-slate-50/60">
            <PanelHeader
              title="Reliability posture"
              subtitle="Use this surface to confirm service reliability, identify burn-rate risk, and prioritize the most urgent operational follow-up."
            />
            <div className="mt-4 grid gap-3 lg:grid-cols-3">
              <div className="rounded-xl border border-white bg-white px-4 py-3 shadow-sm">
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">API reliability</div>
                <p className="mt-2 text-sm font-medium text-slate-900">
                  API error rate is {data.global_sli.api_error_rate_pct.toFixed(3)}% against a target of {data.targets.api_error_budget_pct.toFixed(2)}%.
                </p>
              </div>
              <div className="rounded-xl border border-white bg-white px-4 py-3 shadow-sm">
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Burn rate</div>
                <p className="mt-2 text-sm font-medium text-slate-900">
                  Error budget burn is running at {data.global_sli.error_budget_burn_rate.toFixed(2)}x the planned pace.
                </p>
              </div>
              <div className="rounded-xl border border-white bg-white px-4 py-3 shadow-sm">
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Alert pressure</div>
                <p className="mt-2 text-sm font-medium text-slate-900">
                  {criticalAlerts} critical and {warningAlerts} warning alert{alerts.length === 1 ? '' : 's'} are currently open.
                </p>
              </div>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Start with burn-rate and open alerts, then use the API and worker tables below to locate the exact surface driving the current reliability posture.
            </p>
          </Panel>

          <Panel flush className="overflow-hidden">
            <div className="border-b border-slate-100 px-5 py-4">
              <PanelHeader
                title={p.sloApiPathsTitle}
                subtitle="Track API request volume, error rate, and latency on the most visible customer-facing paths."
              />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColPath}</th>
                    <th className="hidden px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400 sm:table-cell">{p.sloColReq}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColErrorPct}</th>
                    <th className="hidden px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400 sm:table-cell">{p.sloColP95}</th>
                    <th className="hidden px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400 md:table-cell">{p.sloColAvg}</th>
                    <th className="hidden px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400 lg:table-cell">{p.sloColMax}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {data.api_paths.slice(0, 10).map((row) => (
                    <tr key={row.path} className="align-top hover:bg-gray-50/50 transition-colors">
                      <td className="px-5 py-3.5">
                        <ResponsivePrimaryCell
                          title={<span className="font-mono text-xs text-gray-700">{row.path}</span>}
                          meta={[
                            { label: p.sloColReq, value: row.requests.toLocaleString() },
                            { label: p.sloColP95, value: row.p95_latency_ms.toFixed(2) },
                            { label: p.sloColAvg, value: row.avg_latency_ms.toFixed(2), valueClassName: 'text-slate-500' },
                            { label: p.sloColMax, value: row.max_latency_ms.toFixed(2), valueClassName: 'text-slate-500' },
                          ]}
                        />
                      </td>
                      <td className="hidden px-4 py-3.5 tabular-nums text-gray-700 sm:table-cell">{row.requests}</td>
                      <td className="px-4 py-3.5 tabular-nums text-gray-700">{row.error_rate_pct.toFixed(3)}%</td>
                      <td className="hidden px-4 py-3.5 tabular-nums text-gray-700 sm:table-cell">{row.p95_latency_ms.toFixed(2)}</td>
                      <td className="hidden px-4 py-3.5 tabular-nums text-gray-700 md:table-cell">{row.avg_latency_ms.toFixed(2)}</td>
                      <td className="hidden px-4 py-3.5 tabular-nums text-gray-700 lg:table-cell">{row.max_latency_ms.toFixed(2)}</td>
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
                subtitle="Review worker execution reliability, retry pressure, and failure rate across the operational pipeline."
              />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColWorker}</th>
                    <th className="hidden px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400 sm:table-cell">{p.sloColTotal}</th>
                    <th className="hidden px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400 md:table-cell">{p.sloColSuccess}</th>
                    <th className="hidden px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400 sm:table-cell">{p.sloColRetry}</th>
                    <th className="hidden px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400 sm:table-cell">{p.sloColFailed}</th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{p.sloColErrorPct}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {data.workers.map((w) => (
                    <tr key={w.worker} className="align-top hover:bg-gray-50/50 transition-colors">
                      <td className="px-5 py-3.5">
                        <ResponsivePrimaryCell
                          title={w.worker}
                          meta={[
                            { label: p.sloColTotal, value: w.total.toLocaleString() },
                            { label: p.sloColSuccess, value: w.success.toLocaleString(), valueClassName: 'text-emerald-700' },
                            { label: p.sloColRetry, value: w.retry.toLocaleString(), valueClassName: 'text-amber-700' },
                            { label: p.sloColFailed, value: w.failed.toLocaleString(), valueClassName: 'text-rose-700' },
                          ]}
                        />
                      </td>
                      <td className="hidden px-4 py-3.5 tabular-nums text-gray-700 sm:table-cell">{w.total}</td>
                      <td className="hidden px-4 py-3.5 tabular-nums text-green-700 md:table-cell">{w.success}</td>
                      <td className="hidden px-4 py-3.5 tabular-nums text-amber-700 sm:table-cell">{w.retry}</td>
                      <td className="hidden px-4 py-3.5 tabular-nums text-red-700 sm:table-cell">{w.failed}</td>
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
                subtitle="Surface the most urgent reliability issues and clarify the next recommended operational action."
              />
            </div>
            {!alerts.length ? (
              <div className="p-5">
                <EmptyState
                  icon="lightbulb"
                  title={p.sloNoAlerts}
                  description="No reliability follow-up is currently required across the monitored API and worker surfaces."
                />
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
