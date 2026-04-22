import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Activity, Cloud, DollarSign, TrendingUp, AlertTriangle, RefreshCw, Settings, Zap, Lightbulb } from 'lucide-react'
import { MetricCard } from '../../components/Cards/MetricCard'
import { BudgetWidget } from '../../components/Cards/BudgetWidget'
import { CostTrendChart } from '../../components/Charts/CostTrendChart'
import { ledgerApi } from '../../api/ledger'
import { cloudAccountsApi } from '../../api/cloudAccounts'
import { opportunitiesApi } from '../../api/opportunities'
import { changeEventsApi } from '../../api/changeEvents'
import { useI18n } from '../../contexts/I18nContext'
import type { ChangeEvent, ChangeEventType, ReservationEfficiencyAction } from '../../types'
import clsx from 'clsx'

const fmt = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

const EVENT_ICON: Record<ChangeEventType, React.ElementType> = {
  incident: AlertTriangle,
  cost_anomaly: DollarSign,
  deploy: RefreshCw,
  config_change: Settings,
  scaling: TrendingUp,
  policy_change: Zap,
}

const EVENT_COLOR: Record<ChangeEventType, string> = {
  incident: 'text-red-500 bg-red-50',
  cost_anomaly: 'text-orange-500 bg-orange-50',
  deploy: 'text-blue-500 bg-blue-50',
  config_change: 'text-purple-500 bg-purple-50',
  scaling: 'text-cyan-500 bg-cyan-50',
  policy_change: 'text-gray-500 bg-gray-100',
}

const ACTION_COLOR: Record<ReservationEfficiencyAction, string> = {
  keep: 'bg-green-50 text-green-700',
  resize_resource: 'bg-blue-50 text-blue-700',
  schedule_stop: 'bg-amber-50 text-amber-700',
  exchange_reservation: 'bg-purple-50 text-purple-700',
  do_not_renew: 'bg-red-50 text-red-700',
}

function EventFeedRow({ ev, eventLabels }: { ev: ChangeEvent; eventLabels: Record<ChangeEventType, string> }) {
  const Icon = EVENT_ICON[ev.event_type]
  const color = EVENT_COLOR[ev.event_type]

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-gray-50 last:border-0">
      <div className={clsx('rounded-lg p-1.5 shrink-0', color)}>
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium text-gray-800 truncate">{ev.title}</p>
          {ev.cost_impact_usd != null && (
            <span
              className={clsx(
                'text-xs font-semibold shrink-0',
                ev.cost_impact_usd > 0 ? 'text-red-600' : 'text-green-600'
              )}
            >
              {ev.cost_impact_usd > 0 ? '+' : ''}$
              {Math.abs(ev.cost_impact_usd).toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-gray-400">{eventLabels[ev.event_type]}</span>
          {ev.service && <span className="text-xs text-gray-400">· {ev.service}</span>}
          <span className="text-xs text-gray-300">·</span>
          <span className="text-xs text-gray-400">
            {new Date(ev.occurred_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
          </span>
          {ev.causal_confidence != null && (
            <>
              <span className="text-xs text-gray-300">·</span>
              <span className="text-xs text-gray-400">
                {Math.round(ev.causal_confidence * 100)}% causal
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export function DashboardPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const d = t.dashboard
  const ce = t.changeEvents
  const [criticalOnly, setCriticalOnly] = useState(false)

  const eventLabels: Record<ChangeEventType, string> = {
    incident: ce.incident,
    cost_anomaly: ce.costAnomaly,
    deploy: ce.deploy,
    config_change: ce.configChange,
    scaling: ce.scaling,
    policy_change: ce.policyChange,
  }

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => ledgerApi.dashboard().then((r) => r.data),
  })

  const { data: accounts } = useQuery({
    queryKey: ['cloud-accounts'],
    queryFn: () => cloudAccountsApi.list().then((r) => r.data.items),
  })

  const { data: summary } = useQuery({
    queryKey: ['opportunities', 'summary'],
    queryFn: () => opportunitiesApi.summary().then((r) => r.data),
  })

  const { data: recentEvents = [] } = useQuery({
    queryKey: ['change-events', 'dashboard'],
    queryFn: () => changeEventsApi.list({ limit: 50 }).then((r) => r.data.items),
  })

  const { data: reservationEfficiency } = useQuery({
    queryKey: ['dashboard', 'reservation-efficiency'],
    queryFn: () => ledgerApi.reservationEfficiency(30).then((r) => r.data),
  })

  if (metricsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  const openCount = summary?.open ?? 0
  const totalConnected = accounts?.length ?? 0

  // Events sorted by occurred_at desc, show last 8 in feed
  const feedEvents = [...recentEvents]
    .sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime())
    .slice(0, 8)
  const topReservationFamilies = [...(reservationEfficiency?.families ?? [])]
    .sort((a, b) => b.action_priority - a.action_priority || b.waste_cost_usd - a.waste_cost_usd)
    .slice(0, 3)
  const highPriorityCount = (reservationEfficiency?.families ?? []).filter((item) => item.action_priority >= 4).length
  const visibleReservationFamilies = criticalOnly
    ? topReservationFamilies.filter((item) => item.action_priority >= 4)
    : topReservationFamilies

  const actionLabel: Record<ReservationEfficiencyAction, string> = {
    keep: d.resActionKeep,
    resize_resource: d.resActionResize,
    schedule_stop: d.resActionScheduleStop,
    exchange_reservation: d.resActionExchange,
    do_not_renew: d.resActionDoNotRenew,
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{d.title}</h1>
        <p className="text-sm text-gray-500 mt-1">{d.subtitle}</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title={d.currentMonthCost}
          value={fmt(metrics?.current_month_cost ?? 0)}
          change={metrics?.mom_change_pct}
          changeLabel={d.vsLastMonth}
          icon={<DollarSign className="h-5 w-5" />}
          variant={(metrics?.mom_change_pct ?? 0) > 10 ? 'warning' : 'default'}
        />
        <MetricCard
          title={d.potentialSavings}
          value={fmt(summary?.total_potential_savings_usd ?? 0)}
          subtitle={d.openOpportunities.replace('{{count}}', String(openCount))}
          icon={<TrendingUp className="h-5 w-5" />}
          variant="success"
        />
        <MetricCard
          title={d.activeAccounts}
          value={accounts?.filter((a) => a.status === 'active').length ?? 0}
          subtitle={d.totalConnected.replace('{{count}}', String(totalConnected))}
          icon={<Cloud className="h-5 w-5" />}
        />
        <MetricCard
          title={d.events7d}
          value={(metrics?.event_count_7d ?? 0).toLocaleString()}
          subtitle={d.cloudActivityEvents}
          icon={<Activity className="h-5 w-5" />}
        />
      </div>

      {/* Budget widget — SP-EC01 */}
      <BudgetWidget />

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">        {/* Cost trend + change events overlay */}
        <div className="col-span-2 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900">{d.costTrend}</h2>
            {recentEvents.length > 0 && (
              <span className="text-xs text-gray-400">
                {d.changeEventsOverlaid
                  .replace('{{count}}', String(recentEvents.length))
                  .replace('{{s}}', recentEvents.length !== 1 ? 's' : '')}
              </span>
            )}
          </div>
          {metrics?.daily_trend && metrics.daily_trend.length > 0 ? (
            <CostTrendChart data={metrics.daily_trend} events={recentEvents} />
          ) : (
            <div className="flex h-48 items-center justify-center text-sm text-gray-400">
              {d.noCostData}
            </div>
          )}
        </div>

        {/* Top services */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900">{d.topServices}</h2>
          {metrics?.top_services && metrics.top_services.length > 0 ? (
            <ul className="space-y-3">
              {metrics.top_services.slice(0, 6).map((s) => (
                <li key={s.service} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{s.service}</p>
                    <div className="mt-1 h-1.5 rounded-full bg-gray-100">
                      <div
                        className="h-full rounded-full bg-brand-500"
                        style={{ width: `${s.percentage}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-sm font-semibold text-gray-700 flex-shrink-0">
                    {s.percentage.toFixed(1)}%
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex h-48 items-center justify-center text-sm text-gray-400">
              {d.noServiceData}
            </div>
          )}
        </div>
      </div>

      {/* Change events feed + Accounts table */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <div className="col-span-1 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              <h2 className="text-sm font-semibold text-gray-900">{d.reservationsTitle}</h2>
              {highPriorityCount > 0 && (
                <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                  {d.reservationsHighBadge.replace('{{count}}', String(highPriorityCount))}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="text-xs text-gray-600 hover:underline"
                onClick={() => setCriticalOnly((prev) => !prev)}
              >
                {criticalOnly ? d.reservationsShowAll : d.reservationsCriticalOnly}
              </button>
              <button
                type="button"
                className="text-xs text-brand-600 hover:underline"
                onClick={() => navigate('/app/economics/costs')}
              >
                {d.reservationsViewAll}
              </button>
            </div>
          </div>
          {visibleReservationFamilies.length > 0 ? (
            <div className="space-y-3">
              {visibleReservationFamilies.map((item) => (
                <div key={item.family} className="rounded-lg border border-gray-100 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-gray-900">{item.family}</p>
                    <span
                      className={clsx(
                        'rounded-full px-2 py-0.5 text-xs font-medium',
                        ACTION_COLOR[item.recommended_action],
                      )}
                    >
                      {actionLabel[item.recommended_action]}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {d.reservationsPriority.replace('{{priority}}', String(item.action_priority))}
                    {' · '}
                    {d.reservationsWaste.replace('{{waste}}', fmt(item.waste_cost_usd))}
                  </div>
                  <p className="mt-2 text-xs text-gray-600 line-clamp-2">{item.reason}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex h-32 items-center justify-center text-sm text-gray-400">
              {d.reservationsEmpty}
            </div>
          )}
        </div>

        {/* Recent change events feed */}
        <div className="col-span-1 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-900">{d.recentChanges}</h2>
            <button
              type="button"
              className="text-xs text-brand-600 hover:underline"
              onClick={() => navigate('/app/change-events')}
            >
              {d.viewAll}
            </button>
          </div>
          {feedEvents.length > 0 ? (
            <div>
              {feedEvents.map((ev) => (
                <EventFeedRow key={ev.id} ev={ev} eventLabels={eventLabels} />
              ))}
            </div>
          ) : (
            <div className="flex h-32 items-center justify-center text-sm text-gray-400">
              {d.noChangeEvents}
            </div>
          )}
        </div>

        {/* Accounts table */}
        <div className="col-span-2 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900">{d.connectedAccounts}</h2>
          {accounts && accounts.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs font-medium text-gray-500">
                    <th className="pb-3 pr-4">{d.colAccount}</th>
                    <th className="pb-3 pr-4">{d.colProvider}</th>
                    <th className="pb-3 pr-4">{d.colStatus}</th>
                    <th className="pb-3">{d.colLastSync}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {accounts.map((a) => (
                    <tr key={a.id}>
                      <td className="py-3 pr-4 font-medium text-gray-900">{a.display_name}</td>
                      <td className="py-3 pr-4 text-gray-500 uppercase text-xs">{a.provider}</td>
                      <td className="py-3 pr-4">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            a.status === 'active'
                              ? 'bg-green-100 text-green-700'
                              : a.status === 'error'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {a.status}
                        </span>
                      </td>
                      <td className="py-3 text-gray-500 text-xs">
                        {a.last_sync_at ? new Date(a.last_sync_at).toLocaleString() : d.never}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex h-32 items-center justify-center text-sm text-gray-400">
              {d.noAccounts}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
