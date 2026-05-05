import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Activity, Cloud, DollarSign, TrendingUp, AlertTriangle, RefreshCw, Settings, Zap, Lightbulb, ChevronDown } from 'lucide-react'
import { MetricCard } from '../../components/Cards/MetricCard'
import { BudgetWidget } from '../../components/Cards/BudgetWidget'
import { CostTrendChart } from '../../components/Charts/CostTrendChart'
import { ledgerApi } from '../../api/ledger'
import { cloudAccountsApi } from '../../api/cloudAccounts'
import { opportunitiesApi } from '../../api/opportunities'
import { changeEventsApi } from '../../api/changeEvents'
import { intelApi } from '../../api/intel'
import { useI18n } from '../../contexts/I18nContext'
import type {
  ChangeEvent,
  ChangeEventType,
  CloudProvider,
  IntelAnomalySeverity,
  IntelCostAnomaly,
  IntelInsightsResponse,
  ExplainCostChangeRequest,
  ExplainCostChangeResponse,
  ReservationEfficiencyAction,
} from '../../types'
import clsx from 'clsx'
import { usePersistentBoolean, usePersistentString } from '../../hooks/usePersistentBoolean'

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

const ANOMALY_BADGE_CLASS: Record<IntelAnomalySeverity, string> = {
  low: 'bg-yellow-50 text-yellow-700',
  medium: 'bg-orange-50 text-orange-700',
  high: 'bg-red-50 text-red-700',
}

const DASHBOARD_PROVIDERS = ['all', 'azure', 'aws', 'gcp'] as const
type DashboardProviderFilter = (typeof DASHBOARD_PROVIDERS)[number]

const toISODate = (d: Date) => d.toISOString().slice(0, 10)
const shiftDays = (base: Date, days: number) => {
  const d = new Date(base)
  d.setDate(d.getDate() + days)
  return d
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
  const { t, lang } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const d = t.dashboard
  const ce = t.changeEvents
  const [explainOpen, setExplainOpen] = useState(false)
  const budgetSectionRef = useRef<HTMLDivElement | null>(null)
  const [actionMessage, setActionMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const [criticalOnly, setCriticalOnly] = usePersistentBoolean('sp.reservations.criticalOnly', false)
  const [anomalyHighOnly, setAnomalyHighOnly] = usePersistentBoolean('sp.dashboard.anomalyHighOnly', false)
  const [providerMenuOpen, setProviderMenuOpen] = useState(false)
  const [providerFilterRaw, setProviderFilterRaw] = usePersistentString(
    'sp.dashboard.providerFilter',
    'all',
  )
  const providerFilter: DashboardProviderFilter = DASHBOARD_PROVIDERS.includes(
    providerFilterRaw as DashboardProviderFilter,
  )
    ? (providerFilterRaw as DashboardProviderFilter)
    : 'all'
  const providerParam: CloudProvider | undefined =
    providerFilter === 'all' ? undefined : providerFilter
  const providerLabelMap: Record<DashboardProviderFilter, string> = {
    all: d.providerAll,
    azure: d.providerAzure,
    aws: d.providerAws,
    gcp: d.providerGcp,
  }

  const explainWindow = useMemo(() => {
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth(), 1)
    return { start_date: toISODate(start), end_date: toISODate(now) }
  }, [])

  const explainMutation = useMutation({
    mutationFn: async (req: ExplainCostChangeRequest) => {
      const res = await intelApi.explainCostChange(req)
      return res.data
    },
  })

  const eventLabels: Record<ChangeEventType, string> = {
    incident: ce.incident,
    cost_anomaly: ce.costAnomaly,
    deploy: ce.deploy,
    config_change: ce.configChange,
    scaling: ce.scaling,
    policy_change: ce.policyChange,
  }

  const { data: accounts } = useQuery({
    queryKey: ['cloud-accounts'],
    queryFn: () => cloudAccountsApi.list().then((r) => r.data.items),
    refetchInterval: ({ state: { data } }) => {
      const hasPending = (data ?? []).some((a) => a.status === 'pending')
      return hasPending ? 5000 : 30000
    },
  })

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['dashboard', providerFilter],
    queryFn: () => ledgerApi.dashboard(providerParam).then((r) => r.data),
    refetchInterval: 30000,
  })

  const refreshDashboardMutation = useMutation({
    mutationFn: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['cloud-accounts'] }),
        queryClient.invalidateQueries({ queryKey: ['opportunities', 'summary'] }),
        queryClient.invalidateQueries({ queryKey: ['change-events', 'dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['workspace-budget'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard', 'reservation-efficiency'] }),
        queryClient.invalidateQueries({ queryKey: ['intel'] }),
      ])
    },
    onSuccess: () => setActionMessage({ kind: 'success', text: d.refreshSuccess }),
    onError: () => setActionMessage({ kind: 'error', text: d.actionError }),
  })

  const queueIngestionMutation = useMutation({
    mutationFn: async () => {
      const targetAccounts = (accounts ?? []).filter(
        (a) =>
          a.status === 'active' &&
          (providerParam ? a.provider === providerParam : true),
      )
      if (targetAccounts.length === 0) {
        throw new Error('NO_ACTIVE_ACCOUNTS')
      }
      await Promise.all(targetAccounts.map((a) => cloudAccountsApi.sync(a.id, 30)))
      return targetAccounts.length
    },
    onSuccess: async (queuedCount) => {
      setActionMessage({
        kind: 'success',
        text: d.ingestQueuedSuccess.replace('{{count}}', String(queuedCount)),
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cloud-accounts'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['opportunities', 'summary'] }),
        queryClient.invalidateQueries({ queryKey: ['change-events', 'dashboard'] }),
      ])
    },
    onError: (error) => {
      const isNoAccounts = error instanceof Error && error.message === 'NO_ACTIVE_ACCOUNTS'
      setActionMessage({
        kind: 'error',
        text: isNoAccounts ? d.ingestNoAccounts : d.actionError,
      })
    },
  })

  useEffect(() => {
    if (!accounts || accounts.length === 0) return
    if (providerFilter === 'all') return

    const connectedProviders = new Set(
      accounts
        .map((account) => account.provider)
        .filter((provider): provider is CloudProvider => provider === 'azure' || provider === 'aws' || provider === 'gcp'),
    )

    if (connectedProviders.has(providerFilter)) return

    if (connectedProviders.size === 1) {
      const [singleProvider] = [...connectedProviders]
      setProviderFilterRaw(singleProvider)
      return
    }

    setProviderFilterRaw('all')
  }, [accounts, providerFilter, setProviderFilterRaw])

  const { data: summary } = useQuery({
    queryKey: ['opportunities', 'summary'],
    queryFn: () => opportunitiesApi.summary().then((r) => r.data),
    refetchInterval: 30000,
  })

  const { data: recentEvents = [] } = useQuery({
    queryKey: ['change-events', 'dashboard'],
    queryFn: () => changeEventsApi.list({ limit: 50 }).then((r) => r.data.items),
    refetchInterval: 30000,
  })

  const { data: reservationEfficiency } = useQuery({
    queryKey: ['dashboard', 'reservation-efficiency', providerFilter],
    queryFn: () => ledgerApi.reservationEfficiency(30, providerParam).then((r) => r.data),
    refetchInterval: 30000,
  })
  const {
    data: intelInsights,
    isLoading: intelInsightsLoading,
    isError: intelInsightsError,
  } = useQuery({
    queryKey: ['intel', 'insights', lang],
    queryFn: () => intelApi.insights(lang).then((r) => r.data),
    refetchInterval: 30000,
  })

  const { data: intelAnomaliesPage, isLoading: intelAnomaliesLoading } = useQuery({
    queryKey: ['intel', 'cost-anomalies', providerFilter],
    queryFn: () =>
      intelApi
        .listCostAnomalies({
          page: 1,
          page_size: 8,
          ...(providerParam ? { provider: providerParam } : {}),
        })
        .then((r) => r.data),
    refetchInterval: 30000,
  })

  if (metricsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  const openCount = summary?.open ?? 0
  const filteredAccounts = (accounts ?? []).filter((a) =>
    providerParam ? a.provider === providerParam : true,
  )
  const totalConnected = filteredAccounts.length

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

  const explainData: ExplainCostChangeResponse | undefined = explainMutation.data
  const insightsData: IntelInsightsResponse | undefined = intelInsights
  const anomalyItems: IntelCostAnomaly[] = intelAnomaliesPage?.items ?? []
  const visibleAnomalies = anomalyHighOnly
    ? anomalyItems.filter((item) => item.severity === 'high')
    : anomalyItems
  const anomalySeverityLabel: Record<IntelAnomalySeverity, string> = {
    low: d.anomalySeverityLow,
    medium: d.anomalySeverityMedium,
    high: d.anomalySeverityHigh,
  }
  const todayKey = toISODate(new Date())
  const dailyTrend = metrics?.daily_trend ?? []
  const costByDate = new Map(
    dailyTrend.map((point) => [String(point.date).slice(0, 10), point.cost_usd ?? 0]),
  )
  const todayCost = costByDate.get(todayKey) ?? 0
  const todayHasData = costByDate.has(todayKey)
  let previous30Sum = 0
  for (let offset = -30; offset <= -1; offset += 1) {
    const dayKey = toISODate(shiftDays(new Date(), offset))
    previous30Sum += costByDate.get(dayKey) ?? 0
  }
  const avgPrevious30d = previous30Sum / 30
  const deltaTodayVsAvg =
    todayHasData && avgPrevious30d > 0
      ? ((todayCost - avgPrevious30d) / avgPrevious30d) * 100
      : null

  return (
    <div className="space-y-6">
      {explainOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-2xl rounded-xl border border-gray-200 bg-white shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b border-gray-100 p-5">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">{d.explainCostTitle}</h2>
                <p className="mt-1 text-sm text-gray-500">
                  {explainWindow.start_date} → {explainWindow.end_date}
                </p>
              </div>
              <button
                type="button"
                className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-50"
                onClick={() => setExplainOpen(false)}
              >
                {t.common.close}
              </button>
            </div>
            <div className="p-5 space-y-4">
              {explainMutation.isPending && (
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                  {d.explainCostLoading}
                </div>
              )}

              {explainMutation.isError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                  {d.explainCostError}
                </div>
              )}

              {explainData && (
                <div className="space-y-4">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <p className="text-sm font-medium text-gray-900">{d.explainCostSummary}</p>
                    <p className="mt-2 text-sm text-gray-700">{explainData.summary}</p>
                    <div className="mt-3 text-xs text-gray-500">
                      {d.explainCostConfidence}: {Math.round(explainData.confidence * 100)}%
                      {explainData.model ? ` · ${explainData.model}` : ''}
                    </div>
                  </div>

                  {explainData.causes.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-gray-900">{d.explainCostCauses}</p>
                      <div className="space-y-2">
                        {explainData.causes.map((c, idx) => (
                          <div key={idx} className="rounded-lg border border-gray-200 p-4">
                            <div className="flex items-start justify-between gap-3">
                              <p className="text-sm font-medium text-gray-900">{c.cause}</p>
                              {c.estimated_impact_usd != null && (
                                <span className="text-xs font-semibold text-gray-600">
                                  {fmt(c.estimated_impact_usd)}
                                </span>
                              )}
                            </div>
                            {c.evidence.length > 0 && (
                              <ul className="mt-2 list-disc pl-5 text-sm text-gray-700">
                                {c.evidence.slice(0, 4).map((e, eIdx) => (
                                  <li key={eIdx}>{e}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="rounded-lg border border-gray-200 p-4">
                    <p className="text-sm font-medium text-gray-900">{d.explainCostRecommendation}</p>
                    <p className="mt-2 text-sm text-gray-700">{explainData.recommendation}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{d.title}</h1>
          <p className="text-sm text-gray-500 mt-1">{d.subtitle}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <label className="text-sm text-gray-600">
            {d.providerScope}
            <div className="relative mt-1">
              <button
                type="button"
                onClick={() => setProviderMenuOpen((prev) => !prev)}
                className="inline-flex min-w-44 items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm transition-colors hover:border-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
              >
                <span>{providerLabelMap[providerFilter]}</span>
                <ChevronDown
                  className={clsx(
                    'h-4 w-4 text-gray-400 transition-transform',
                    providerMenuOpen && 'rotate-180',
                  )}
                />
              </button>
              {providerMenuOpen && (
                <div className="absolute right-0 z-20 mt-1 w-44 rounded-md border border-gray-200 bg-white p-1 shadow-lg">
                  {DASHBOARD_PROVIDERS.map((providerOption) => (
                    <button
                      key={providerOption}
                      type="button"
                      onClick={() => {
                        setProviderFilterRaw(providerOption)
                        setProviderMenuOpen(false)
                      }}
                      className={clsx(
                        'w-full rounded px-2 py-1.5 text-left text-sm transition-colors',
                        providerOption === providerFilter
                          ? 'bg-brand-50 text-brand-700'
                          : 'text-gray-700 hover:bg-gray-50',
                      )}
                    >
                      {providerLabelMap[providerOption]}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </label>
          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              onClick={() => refreshDashboardMutation.mutate()}
              disabled={refreshDashboardMutation.isPending}
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {refreshDashboardMutation.isPending ? d.refreshingData : d.refreshData}
            </button>
            <button
              type="button"
              onClick={() => {
                budgetSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50"
            >
              {d.adjustBudget}
            </button>
            <button
              type="button"
              onClick={() => queueIngestionMutation.mutate()}
              disabled={queueIngestionMutation.isPending || !accounts}
              className="rounded-md bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {queueIngestionMutation.isPending ? d.queueingIngestion : d.queueIngestion}
            </button>
          </div>
          {actionMessage && (
            <p
              className={clsx(
                'text-xs',
                actionMessage.kind === 'success' ? 'text-green-700' : 'text-red-700',
              )}
            >
              {actionMessage.text}
            </p>
          )}
        </div>
      </div>

      {accounts?.length === 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-gray-700">{d.connectFirstAccountMessage}</p>
            <button
              type="button"
              onClick={() => navigate('/app/settings/platform')}
              className="rounded-md bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700"
            >
              {d.connectFirstAccountCta}
            </button>
          </div>
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title={d.currentMonthCost}
          value={fmt(metrics?.current_month_cost ?? 0)}
          change={metrics?.mom_change_pct}
          changeLabel={d.vsLastMonth}
          icon={<DollarSign className="h-5 w-5" />}
          variant={(metrics?.mom_change_pct ?? 0) > 10 ? 'warning' : 'default'}
          action={
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-700 hover:bg-violet-100"
              onClick={() => {
                setExplainOpen(true)
                explainMutation.mutate({
                  start_date: explainWindow.start_date,
                  end_date: explainWindow.end_date,
                  language: lang,
                  ...(providerParam ? { provider: providerParam } : {}),
                })
              }}
            >
              <Lightbulb className="h-3.5 w-3.5" />
              {d.explainCostCta}
            </button>
          }
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
            value={filteredAccounts.filter((a) => a.status === 'active').length}
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

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">{d.monitoringVsBaseline}</h2>
            <p className="mt-1 text-xs text-gray-500">{d.partialUntilLastSync}</p>
          </div>
          {!todayHasData && (
            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">
              {d.billingProcessingPending}
            </span>
          )}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
            <div className="text-xs uppercase tracking-wide text-gray-500">{d.todayCost}</div>
            <div className="mt-1 text-xl font-semibold text-gray-900">{fmt(todayCost)}</div>
          </div>
          <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
            <div className="text-xs uppercase tracking-wide text-gray-500">{d.avgPrevious30d}</div>
            <div className="mt-1 text-xl font-semibold text-gray-900">{fmt(avgPrevious30d)}</div>
          </div>
          <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
            <div className="text-xs uppercase tracking-wide text-gray-500">{d.todayVsAvgDelta}</div>
            <div className="mt-1 text-xl font-semibold text-gray-900">
              {deltaTodayVsAvg === null ? '—' : `${deltaTodayVsAvg > 0 ? '+' : ''}${deltaTodayVsAvg.toFixed(1)}%`}
            </div>
          </div>
        </div>
      </div>

      {/* Budget widget — SP-EC01 */}
      <div ref={budgetSectionRef}>
        <BudgetWidget />
      </div>

      {/* AI Insights + Cost Anomalies */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="col-span-2 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-3">
            <h2 className="text-sm font-semibold text-gray-900">{d.insightsTitle}</h2>
            <p className="mt-1 text-xs text-gray-500">{d.insightsSubtitle}</p>
          </div>

          {intelInsightsLoading ? (
            <div className="flex h-40 items-center justify-center">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            </div>
          ) : intelInsightsError || !insightsData ? (
            <div className="flex h-40 items-center justify-center text-sm text-gray-400">
              {d.insightsUnavailable}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-lg border border-gray-200 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {d.insightsTopSaving}
                </p>
                <p className="mt-1 text-sm text-gray-800">{insightsData.top_saving_opportunity}</p>
              </div>
              <div className="rounded-lg border border-gray-200 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {d.insightsMainRisk}
                </p>
                <p className="mt-1 text-sm text-gray-800">{insightsData.main_risk}</p>
              </div>
              <div className="rounded-lg border border-gray-200 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {d.insightsTrend}
                </p>
                <p className="mt-1 text-sm text-gray-800">{insightsData.cost_trend_summary}</p>
              </div>
              <div className="rounded-lg border border-violet-200 bg-violet-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">
                  {d.insightsAction}
                </p>
                <p className="mt-1 text-sm text-violet-900">{insightsData.recommended_action}</p>
                <p className="mt-2 text-xs text-violet-700">
                  {d.insightsConfidence}: {Math.round(insightsData.confidence * 100)}%
                  {insightsData.model ? ` · ${insightsData.model}` : ''}
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">{d.anomaliesTitle}</h2>
              <p className="mt-1 text-xs text-gray-500">{d.anomaliesSubtitle}</p>
            </div>
            <button
              type="button"
              className="text-xs text-brand-600 hover:underline"
              onClick={() => setAnomalyHighOnly((prev) => !prev)}
            >
              {anomalyHighOnly ? d.anomalyShowAll : d.anomalyCriticalOnly}
            </button>
          </div>

          {intelAnomaliesLoading ? (
            <div className="flex h-40 items-center justify-center">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            </div>
          ) : visibleAnomalies.length > 0 ? (
            <div className="space-y-2">
              {visibleAnomalies.slice(0, 5).map((item) => (
                <div key={item.id} className="rounded-lg border border-gray-100 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-gray-900">{item.service}</p>
                    <span
                      className={clsx(
                        'rounded-full px-2 py-0.5 text-xs font-semibold',
                        ANOMALY_BADGE_CLASS[item.severity],
                      )}
                    >
                      {anomalySeverityLabel[item.severity]}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 uppercase">{item.provider}</p>
                  <div className="mt-2 text-xs text-gray-600">
                    z-score {item.z_score.toFixed(2)}
                    {item.deviation_pct != null
                      ? ` · +${item.deviation_pct.toFixed(1)}%`
                      : ''}
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {fmt(item.current_cost_usd)} vs {fmt(item.historical_mean_usd)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex h-40 items-center justify-center text-sm text-gray-400">
              {d.anomaliesNone}
            </div>
          )}
        </div>
      </div>

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
          {filteredAccounts.length > 0 ? (
            <div className="relative overflow-hidden rounded-lg">
              <div className="overflow-x-auto scrollbar-light">
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
                    {filteredAccounts.map((a) => (
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
              {/* Right fade — indicates horizontal overflow */}
              <div className="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-white to-transparent" />
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
