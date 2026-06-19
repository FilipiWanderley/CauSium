import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from 'recharts'
import {
  AlertTriangle,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  DollarSign,
  Lightbulb,
  RefreshCw,
  Settings,
  TrendingUp,
  Zap,
  Activity,
} from 'lucide-react'
import { KpiCard } from '../../components/Cards/KpiCard'
import { BudgetWidget } from '../../components/Cards/BudgetWidget'
import { CostTrendChart } from '../../components/Charts/CostTrendChart'
import { ChartPanel } from '../../components/Charts/ChartPanel'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { PageHeader } from '../../components/Layout/PageHeader'
import { ReconciliationBadge } from '../../components/UX/ReconciliationBadge'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { SkeletonMetricCards, SkeletonPrioritizedList, SkeletonSection } from '../../components/UX/Skeleton'
import { ledgerApi } from '../../api/ledger'
import { cloudAccountsApi } from '../../api/cloudAccounts'
import { CloudProviderIconBranded } from '../../components/cloud/CloudProviderIcon'
import { opportunitiesApi } from '../../api/opportunities'
import { changeEventsApi } from '../../api/changeEvents'
import { intelApi } from '../../api/intel'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import type {
  ChangeEvent,
  ChangeEventType,
  CloudProvider,
  IntelAnomalySeverity,
  IntelCostAnomaly,
  IntelInsightsResponse,
  ExplainCostChangeRequest,
  ExplainCostChangeResponse,
  ReconciliationStatus,
  SubscriptionCostSummary,
} from '../../types'
import clsx from 'clsx'
import { usePersistentBoolean, usePersistentString } from '../../hooks/usePersistentBoolean'
import { formatCurrency } from '../../utils/currency'

// ─── Utilities ───────────────────────────────────────────────────────────────

const fmt = (n: number, currency = 'USD') => formatCurrency(n, currency)

const USD_VALUE_RE = /(?:US\$|\$)\s*(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?)/g
const USD_LABEL_RE = /\bUSD\b\s*:?\s*(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?)/g

const formatCurrencyText = (text: string | null | undefined, currency: string) => {
  if (!text) return ''
  const replaceAmount = (raw: string) => {
    const value = Number(raw.replace(/,/g, ''))
    return Number.isFinite(value) ? fmt(value, currency) : raw
  }
  return text
    .replace(USD_LABEL_RE, (_, raw: string) => `${currency}: ${replaceAmount(raw)}`)
    .replace(USD_VALUE_RE, (_, raw: string) => replaceAmount(raw))
}

const EVENT_ICON: Record<ChangeEventType, React.ElementType> = {
  incident: AlertTriangle, cost_anomaly: DollarSign, deploy: RefreshCw,
  config_change: Settings, scaling: TrendingUp, policy_change: Zap,
}
const EVENT_COLOR: Record<ChangeEventType, string> = {
  incident: 'text-rose-500 bg-rose-50', cost_anomaly: 'text-orange-500 bg-orange-50',
  deploy: 'text-blue-500 bg-blue-50', config_change: 'text-purple-500 bg-purple-50',
  scaling: 'text-cyan-500 bg-cyan-50', policy_change: 'text-slate-500 bg-slate-100',
}
const ANOMALY_BADGE: Record<IntelAnomalySeverity, string> = {
  low: 'bg-amber-50 text-amber-700', medium: 'bg-orange-50 text-orange-700', high: 'bg-rose-50 text-rose-700',
}

const DASHBOARD_PROVIDERS = ['all', 'azure', 'aws', 'gcp'] as const
type DashboardProviderFilter = (typeof DASHBOARD_PROVIDERS)[number]

const toISODate = (d: Date) => d.toISOString().slice(0, 10)
const shiftDays = (base: Date, days: number) => { const r = new Date(base); r.setDate(r.getDate() + days); return r }

function computeAlert(todayCost: number, avg30d: number, hasData: boolean) {
  if (!hasData || avg30d <= 0 || avg30d < 50) return null
  const delta = ((todayCost - avg30d) / avg30d) * 100
  if (delta < 0) return { severity: 'info' as const, delta, todayCost, avgPrevious30d: avg30d }
  if (Math.abs(delta) >= 20) return { severity: 'warning' as const, delta, todayCost, avgPrevious30d: avg30d }
  if (Math.abs(delta) >= 10 && todayCost > 200) return { severity: 'info' as const, delta, todayCost, avgPrevious30d: avg30d }
  return null
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function ActivityRow({ ev, label, currency }: { ev: ChangeEvent; label: string; currency: string }) {
  const Icon = EVENT_ICON[ev.event_type]
  const color = EVENT_COLOR[ev.event_type]
  return (
    <div className="flex items-center gap-2.5 py-2 border-b border-slate-50 last:border-0">
      <div className={clsx('rounded-md p-1 shrink-0', color)}><Icon className="h-3 w-3" /></div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-700 truncate">{ev.title}</p>
        <p className="text-[10px] text-slate-400">{label}{ev.service ? ` · ${ev.service}` : ''}</p>
      </div>
      {ev.cost_impact_usd != null && (
        <span className={clsx('text-[11px] font-semibold tabular-nums shrink-0', ev.cost_impact_usd > 0 ? 'text-rose-600' : 'text-emerald-600')}>
          {ev.cost_impact_usd > 0 ? '+' : ''}{fmt(Math.abs(ev.cost_impact_usd), currency)}
        </span>
      )}
      <span className="text-[10px] text-slate-400 shrink-0">
        {new Date(ev.occurred_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
      </span>
    </div>
  )
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function DashboardPage() {
  const { t, lang } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const d = t.dashboard
  const ce = t.changeEvents
  const ux = t.ux
  usePageTitle(d.title)
  const [explainOpen, setExplainOpen] = useState(false)
  const budgetSectionRef = useRef<HTMLDivElement | null>(null)
  const [actionMessage, setActionMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const [anomalyHighOnly, setAnomalyHighOnly] = usePersistentBoolean('sp.dashboard.anomalyHighOnly', false)
  const [providerMenuOpen, setProviderMenuOpen] = useState(false)
  const [providerFilterRaw, setProviderFilterRaw] = usePersistentString('sp.dashboard.providerFilter', 'all')
  const providerFilter: DashboardProviderFilter = DASHBOARD_PROVIDERS.includes(providerFilterRaw as DashboardProviderFilter)
    ? (providerFilterRaw as DashboardProviderFilter) : 'all'
  const providerParam: CloudProvider | undefined = providerFilter === 'all' ? undefined : providerFilter
  const providerLabelMap: Record<DashboardProviderFilter, string> = {
    all: d.providerAll, azure: d.providerAzure, aws: d.providerAws, gcp: d.providerGcp,
  }
  const [subscriptionId, setSubscriptionId] = useState<string>('')
  const [dataHealthOpen, setDataHealthOpen] = useState(false)

  const explainWindow = useMemo(() => {
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth(), 1)
    return { start_date: toISODate(start), end_date: toISODate(now) }
  }, [])

  const explainMutation = useMutation({
    mutationFn: async (req: ExplainCostChangeRequest) => (await intelApi.explainCostChange(req)).data,
  })

  const eventLabels: Record<ChangeEventType, string> = {
    incident: ce.incident, cost_anomaly: ce.costAnomaly, deploy: ce.deploy,
    config_change: ce.configChange, scaling: ce.scaling, policy_change: ce.policyChange,
  }

  // ─── Queries ─────────────────────────────────────────────────────────────────

  const { data: accounts } = useQuery({
    queryKey: ['cloud-accounts'],
    queryFn: () => cloudAccountsApi.list().then((r) => r.data.items),
    refetchInterval: ({ state: { data } }) => (data ?? []).some((a) => a.status === 'pending') ? 5000 : 30000,
  })

  const { data: subscriptionsData, isLoading: subscriptionsLoading, isError: subscriptionsError } = useQuery<SubscriptionCostSummary>({
    queryKey: ['ledger', 'subscriptions', 90],
    queryFn: () => ledgerApi.subscriptionCostSummary(90).then((r) => r.data),
  })

  const hasMultipleSubscriptions = (subscriptionsData?.subscription_count ?? 0) > 1
  const getSubName = (name: string | null | undefined, key: string | null | undefined) => {
    const n = name?.trim()
    if (n) return n
    return key ? `${key.slice(0, 8)}…` : d.subscriptionNone
  }
  const singleSubscriptionName = getSubName(subscriptionsData?.items[0]?.subscription_name, subscriptionsData?.items[0]?.subscription_id)

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['dashboard', providerFilter, subscriptionId],
    queryFn: () => ledgerApi.dashboard(providerParam, subscriptionId || undefined).then((r) => r.data),
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
        queryClient.invalidateQueries({ queryKey: ['intel'] }),
      ])
    },
    onSuccess: () => setActionMessage({ kind: 'success', text: d.refreshSuccess }),
    onError: () => setActionMessage({ kind: 'error', text: d.actionError }),
  })

  const queueIngestionMutation = useMutation({
    mutationFn: async () => {
      const targets = (accounts ?? []).filter((a) => a.status === 'active' && (providerParam ? a.provider === providerParam : true))
      if (targets.length === 0) throw new Error('NO_ACTIVE_ACCOUNTS')
      await Promise.all(targets.map((a) => cloudAccountsApi.sync(a.id, 30)))
      return targets.length
    },
    onSuccess: async (count) => {
      setActionMessage({ kind: 'success', text: d.ingestQueuedSuccess.replace('{{count}}', String(count)) })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cloud-accounts'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['opportunities', 'summary'] }),
        queryClient.invalidateQueries({ queryKey: ['change-events', 'dashboard'] }),
      ])
    },
    onError: (err) => {
      setActionMessage({ kind: 'error', text: err instanceof Error && err.message === 'NO_ACTIVE_ACCOUNTS' ? d.ingestNoAccounts : d.actionError })
    },
  })

  useEffect(() => {
    if (!accounts || accounts.length === 0 || providerFilter === 'all') return
    const connected = new Set(accounts.map((a) => a.provider).filter((p): p is CloudProvider => p === 'azure' || p === 'aws' || p === 'gcp'))
    if (connected.has(providerFilter)) return
    setProviderFilterRaw(connected.size === 1 ? [...connected][0] : 'all')
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

  const { data: intelInsights, isLoading: intelInsightsLoading, isError: intelInsightsError } = useQuery({
    queryKey: ['intel', 'insights', lang],
    queryFn: () => intelApi.insights(lang).then((r) => r.data),
    refetchInterval: 30000,
  })

  const { data: intelAnomaliesPage, isLoading: intelAnomaliesLoading } = useQuery({
    queryKey: ['intel', 'cost-anomalies', providerFilter],
    queryFn: () => intelApi.listCostAnomalies({ page: 1, page_size: 8, ...(providerParam ? { provider: providerParam } : {}) }).then((r) => r.data),
    refetchInterval: 30000,
  })

  const { data: integrityData } = useQuery({
    queryKey: ['ledger', 'integrity-metadata'],
    queryFn: () => ledgerApi.integrityMetadata().then((r) => r.data),
    refetchInterval: 60000,
  })

  const clientReconciliationStatus: ReconciliationStatus = useMemo(() => {
    if (!metrics?.data_max_date) return 'warning'
    const gap = Math.floor((Date.now() - new Date(metrics.data_max_date).getTime()) / 86400000)
    if (gap <= 2) return 'healthy'
    if (gap <= 5) return 'delayed'
    return 'partial'
  }, [metrics?.data_max_date])
  const reconciliationStatus = integrityData?.reconciliation_status ?? clientReconciliationStatus

  // ─── Derived data ────────────────────────────────────────────────────────────

  if (metricsLoading) {
    return (
      <div className="page-container">
        <PageHeader title={d.title} subtitle={d.operationsSection} />
        <SkeletonMetricCards count={4} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.6fr_1fr]">
          <SkeletonSection lines={8} />
          <SkeletonSection lines={6} />
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <SkeletonPrioritizedList items={4} />
          <SkeletonSection lines={5} />
          <SkeletonSection lines={5} />
        </div>
      </div>
    )
  }

  const openCount = summary?.open ?? 0
  const filteredAccounts = (accounts ?? []).filter((a) => providerParam ? a.provider === providerParam : true)
  const feedEvents = [...recentEvents].sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()).slice(0, 6)

  const effectiveCurrency = metrics?.billing_currency ?? metrics?.currency ?? 'USD'
  const fmtCost = (n: number) => fmt(n, effectiveCurrency)
  const anomalyItems: IntelCostAnomaly[] = intelAnomaliesPage?.items ?? []
  const visibleAnomalies = anomalyHighOnly ? anomalyItems.filter((i) => i.severity === 'high') : anomalyItems
  const anomalySeverityLabel: Record<IntelAnomalySeverity, string> = { low: d.anomalySeverityLow, medium: d.anomalySeverityMedium, high: d.anomalySeverityHigh }

  const dailyTrend = metrics?.daily_trend ?? []
  const costByDate = new Map(dailyTrend.map((p) => [String(p.date).slice(0, 10), p.cost_usd ?? 0]))
  const todayKey = toISODate(new Date())
  const todayCost = costByDate.get(todayKey) ?? 0
  const todayHasData = costByDate.has(todayKey)
  let previous30Sum = 0
  for (let offset = -30; offset <= -1; offset += 1) previous30Sum += costByDate.get(toISODate(shiftDays(new Date(), offset))) ?? 0
  const avgPrevious30d = previous30Sum / 30
  const deltaTodayVsAvg = todayHasData && avgPrevious30d > 0 ? ((todayCost - avgPrevious30d) / avgPrevious30d) * 100 : null
  const costAlert = computeAlert(todayCost, avgPrevious30d, todayHasData)

  const momChangeLabel = metrics?.mom_change_pct == null ? null : `${metrics.mom_change_pct > 0 ? '+' : ''}${metrics.mom_change_pct.toFixed(1)}%`

  // Explain cost data
  const explainFallback: ExplainCostChangeResponse | undefined = metrics ? {
    summary: momChangeLabel
      ? d.explainCostFallbackSummaryWithChange.replace('{{start}}', explainWindow.start_date).replace('{{end}}', explainWindow.end_date).replace('{{cost}}', fmtCost(metrics.current_month_cost ?? 0)).replace('{{change}}', momChangeLabel)
      : d.explainCostFallbackSummaryWithoutChange.replace('{{start}}', explainWindow.start_date).replace('{{end}}', explainWindow.end_date).replace('{{cost}}', fmtCost(metrics.current_month_cost ?? 0)),
    causes: [
      { cause: d.billingContext, evidence: [`${d.currentMonthCost}: ${fmtCost(metrics.current_month_cost ?? 0)}`, ux.billingCurrency.replace('{{currency}}', effectiveCurrency)], estimated_impact_usd: metrics.current_month_cost ?? 0 },
      { cause: d.insightsTrend, evidence: [momChangeLabel ? `${d.vsLastMonth}: ${momChangeLabel}` : d.explainCostFallbackSummaryWithoutChange.replace('{{start}}', explainWindow.start_date).replace('{{end}}', explainWindow.end_date).replace('{{cost}}', fmtCost(metrics.current_month_cost ?? 0)), metrics.data_max_date ? ux.integrityDataThrough.replace('{{date}}', metrics.data_max_date) : `${explainWindow.start_date} → ${explainWindow.end_date}`], estimated_impact_usd: null },
    ],
    impact: metrics.data_max_date ? ux.integrityDataThrough.replace('{{date}}', metrics.data_max_date) : `${explainWindow.start_date} → ${explainWindow.end_date}`,
    recommendation: d.explainCostFallbackRecommendation.replace('{{currency}}', effectiveCurrency),
    confidence: 0.45, model: 'rule-based',
  } : undefined

  const explainData = explainMutation.data
  const explainDisplayData: ExplainCostChangeResponse | undefined = (() => {
    if (!explainData && !explainFallback) return undefined
    if (!explainData) return explainFallback
    return {
      ...explainData,
      summary: formatCurrencyText(explainData.summary, effectiveCurrency) || explainFallback?.summary || '',
      causes: explainData.causes.length > 0
        ? explainData.causes.map((c) => ({ ...c, cause: formatCurrencyText(c.cause, effectiveCurrency), evidence: c.evidence.map((e) => formatCurrencyText(e, effectiveCurrency)) }))
        : explainFallback?.causes || [],
      impact: formatCurrencyText(explainData.impact, effectiveCurrency) || explainFallback?.impact || '',
      recommendation: formatCurrencyText(explainData.recommendation, effectiveCurrency) || explainFallback?.recommendation || '',
      confidence: explainData.confidence ?? explainFallback?.confidence ?? 0.45,
      model: explainData.model ?? explainFallback?.model,
    }
  })()

  const insightsDisplayData: IntelInsightsResponse | undefined = intelInsights ? {
    ...intelInsights,
    top_saving_opportunity: formatCurrencyText(intelInsights.top_saving_opportunity, effectiveCurrency),
    main_risk: formatCurrencyText(intelInsights.main_risk, effectiveCurrency),
    cost_trend_summary: formatCurrencyText(intelInsights.cost_trend_summary, effectiveCurrency),
    recommended_action: formatCurrencyText(intelInsights.recommended_action, effectiveCurrency),
  } : undefined

  // Build sparkline from daily trend (last 14 days)
  const sparklineData = dailyTrend.slice(-14).map((p) => ({ value: p.cost_usd ?? 0 }))

  // ─── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="page-container">
      {/* ═══ Explain Cost Modal ═══ */}
      {explainOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-2xl rounded-panel border border-slate-200 bg-white shadow-panel-elevated">
            <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-5">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{d.explainCostTitle}</h2>
                <p className="mt-1 text-sm text-slate-500">{explainWindow.start_date} → {explainWindow.end_date}</p>
              </div>
              <button type="button" className="rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-50" onClick={() => setExplainOpen(false)}>{t.common.close}</button>
            </div>
            <div className="p-5 space-y-4">
              {explainMutation.isPending && (
                <div className="flex items-center gap-3 text-sm text-slate-600">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                  {d.explainCostLoading}
                </div>
              )}
              {explainMutation.isError && !explainDisplayData && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{d.explainCostError}</div>
              )}
              {explainDisplayData && (
                <div className="space-y-4">
                  <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
                    <p className="text-sm font-medium text-slate-900">{d.explainCostSummary}</p>
                    <p className="mt-2 text-sm text-slate-700">{explainDisplayData.summary}</p>
                    <div className="mt-3 text-diagnostic">
                      {d.explainCostConfidence}: {Math.round(explainDisplayData.confidence * 100)}%
                      {explainDisplayData.model && !['mock', 'rules', 'rule-based'].includes(explainDisplayData.model) ? ` · ${explainDisplayData.model}` : ` · ${d.explainCostModelRuleBased}`}
                    </div>
                  </div>
                  {explainDisplayData.causes.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-slate-900">{d.explainCostCauses}</p>
                      {explainDisplayData.causes.map((c, idx) => (
                        <div key={idx} className="rounded-lg border border-slate-200 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-medium text-slate-900">{c.cause}</p>
                            {c.estimated_impact_usd != null && <span className="text-xs font-semibold tabular-nums text-slate-600">{fmtCost(c.estimated_impact_usd)}</span>}
                          </div>
                          {c.evidence.length > 0 && <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">{c.evidence.slice(0, 4).map((e, i) => <li key={i}>{e}</li>)}</ul>}
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="rounded-lg border border-slate-200 p-4">
                    <p className="text-sm font-medium text-slate-900">{d.explainCostRecommendation}</p>
                    <p className="mt-2 text-sm text-slate-700">{explainDisplayData.recommendation}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══ A. Toolbar - Filters & Actions ═══ */}
			<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
				{/* Left: Title + Action message */}
				<div className="flex flex-wrap items-center gap-2 gap-x-3">
					<h1 className="text-sm font-semibold text-navy">{d.title}</h1>
					{actionMessage && (
						<span className={clsx(
							'inline-flex items-center rounded-md px-2 py-1 text-xs font-medium',
							actionMessage.kind === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
						)}>
							{actionMessage.text}
						</span>
					)}
				</div>

				{/* Right: Filter controls */}
				<div className="flex flex-wrap items-center gap-2">
					{/* Provider filter */}
					<div className="relative">
						<button
							type="button"
							onClick={() => setProviderMenuOpen((v) => !v)}
							aria-haspopup="menu"
							aria-expanded={providerMenuOpen}
							aria-label={`Filter by provider. Current: ${providerLabelMap[providerFilter]}`}
							className="inline-flex items-center gap-2 rounded-lg border border-gray-light bg-white px-3 py-2 text-xs font-medium text-navy shadow-card-premium transition-all hover:border-teal-400 hover:shadow-panel-hover focus:outline-none focus:ring-2 focus:ring-teal-500/30"
						>
							<CloudProviderIconBranded provider={providerFilter === 'all' ? 'azure' : providerFilter as CloudProvider} size={16} />
							<span className="hidden sm:inline">{providerLabelMap[providerFilter]}</span>
							<span className="sm:hidden">{providerFilter === 'all' ? 'All' : providerFilter}</span>
							<ChevronDown className={clsx('h-3 w-3 text-gray-cool transition-transform', providerMenuOpen && 'rotate-180')} />
						</button>
						{providerMenuOpen && (
							<div
								role="menu"
								className="absolute right-0 z-20 mt-1 w-44 rounded-lg border border-gray-light bg-white p-1 shadow-panel-elevated"
							>
								{DASHBOARD_PROVIDERS.map((opt) => (
									<button
										key={opt}
										type="button"
										role="menuitem"
										onClick={() => { setProviderFilterRaw(opt); setProviderMenuOpen(false) }}
										className={clsx(
											'flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors',
											opt === providerFilter ? 'bg-teal-50 text-teal-700' : 'text-slate-700 hover:bg-gray-light/50'
										)}
									>
										<CloudProviderIconBranded provider={opt === 'all' ? 'azure' : opt as CloudProvider} size={16} />
										<span>{providerLabelMap[opt]}</span>
									</button>
								))}
							</div>
						)}
					</div>

					{/* Subscription filter */}
					<select
						value={hasMultipleSubscriptions ? subscriptionId : ''}
						onChange={(e) => setSubscriptionId(e.target.value)}
						disabled={!hasMultipleSubscriptions || subscriptionsLoading || subscriptionsError}
						aria-label="Filter by subscription"
						className="rounded-lg border border-gray-light bg-white px-3 py-2 text-xs font-medium text-navy shadow-card-premium focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-500/30 disabled:cursor-not-allowed disabled:bg-gray-light/50 disabled:text-gray-cool"
					>
						{subscriptionsLoading ? <option value="">{d.subscriptionLoading}</option>
							: subscriptionsError ? <option value="">{d.subscriptionUnavailable}</option>
							: hasMultipleSubscriptions ? (<><option value="">{d.allSubscriptionsConsolidated}</option>{subscriptionsData?.items.map((s) => <option key={s.subscription_id} value={s.subscription_id}>{s.subscription_name || `${s.subscription_id.slice(0, 8)}…`}</option>)}</>)
							: <option value="">{singleSubscriptionName}</option>}
					</select>

					{/* Divider */}
					<div className="hidden sm:block h-6 w-px bg-gray-light" />

					{/* Sync button */}
					<button
						type="button"
						onClick={() => queueIngestionMutation.mutate()}
						disabled={queueIngestionMutation.isPending || !accounts}
						aria-label="Sync cloud data"
						className="inline-flex items-center gap-1.5 rounded-lg border border-gray-light bg-white px-3 py-2 text-xs font-medium text-navy shadow-card-premium transition-all hover:border-teal-400 hover:shadow-panel-hover disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-gray-light disabled:hover:shadow-card-premium"
					>
						<RefreshCw className={clsx('h-3.5 w-3.5', queueIngestionMutation.isPending && 'animate-spin')} />
						<span className="hidden sm:inline">{queueIngestionMutation.isPending ? d.queueingIngestion : d.queueIngestion}</span>
					</button>

					{/* Refresh button */}
					<button
						type="button"
						onClick={() => refreshDashboardMutation.mutate()}
						disabled={refreshDashboardMutation.isPending}
						aria-label={d.refreshData}
						className="inline-flex items-center gap-1.5 rounded-lg border border-gray-light bg-white px-3 py-2 text-xs font-medium text-navy shadow-card-premium transition-all hover:border-teal-400 hover:shadow-panel-hover disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-gray-light disabled:hover:shadow-card-premium"
					>
						<RefreshCw className={clsx('h-3.5 w-3.5', refreshDashboardMutation.isPending && 'animate-spin')} />
					</button>
				</div>
			</div>

      {/* ═══ Connect prompt ═══ */}
      {accounts?.length === 0 && (
        <Panel compact>
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-slate-700">{d.connectFirstAccountMessage}</p>
            <button type="button" onClick={() => navigate('/app/settings/platform')} className="rounded-md bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700">{d.connectFirstAccountCta}</button>
          </div>
        </Panel>
      )}

      {/* ═══ Cost Alert Banner ═══ */}
      {costAlert && (
        <div className={clsx('rounded-panel border px-4 py-3 text-sm', costAlert.severity === 'warning' ? 'border-amber-300 bg-amber-50 text-amber-900' : 'border-blue-200 bg-blue-50 text-blue-900')}>
          <div className="flex items-center gap-2 font-medium">
            <AlertTriangle className={clsx('h-4 w-4 shrink-0', costAlert.severity === 'warning' ? 'text-amber-500' : 'text-blue-400')} />
            {costAlert.delta > 0 ? d.alertCostSpike.replace('{{delta}}', Math.abs(costAlert.delta).toFixed(1)) : d.alertCostDrop.replace('{{delta}}', Math.abs(costAlert.delta).toFixed(1))}
          </div>
          <p className="mt-1 text-xs opacity-80">{d.alertCostDetail.replace('{{today}}', fmtCost(costAlert.todayCost)).replace('{{avg}}', fmtCost(costAlert.avgPrevious30d)).replace('{{diff}}', `${costAlert.delta > 0 ? '+' : ''}${fmtCost(costAlert.todayCost - costAlert.avgPrevious30d)}`)}</p>
        </div>
      )}

      {/* ═══ B. Provider Status Cards ═══ */}
      {filteredAccounts.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {(['azure', 'aws', 'gcp'] as const).map((provider) => {
            const providerAccounts = filteredAccounts.filter((a) => a.provider === provider)
            if (providerAccounts.length === 0) return null

            const providerColors = {
              azure: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: '#0078D4' },
              aws: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', icon: '#FF9900' },
              gcp: { bg: 'bg-slate-100', border: 'border-slate-300', text: 'text-slate-700', icon: '#4285F4' },
            }
            const colors = providerColors[provider]

            return (
              <div
                key={provider}
                className={clsx(
                  'flex items-center gap-3 rounded-panel border bg-white p-4 shadow-card-premium transition-all hover:shadow-panel-hover',
                  colors.border
                )}
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-sm">
                  <CloudProviderIconBranded provider={provider} size={28} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={clsx('text-sm font-semibold capitalize', colors.text)}>{provider}</p>
                  <p className="text-xs text-gray-cool">
                    {providerAccounts.length} account{providerAccounts.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className={clsx('rounded-full px-2.5 py-1 text-xs font-bold', colors.bg, colors.text)}>
                  {providerAccounts.length}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ═══ C. KPI Row ═══ */}
      <div className="kpi-grid">
        <KpiCard
          title={d.currentMonthCost}
          value={fmtCost(metrics?.current_month_cost ?? 0)}
          delta={metrics?.mom_change_pct}
          deltaLabel={d.vsLastMonth}
          tone={(metrics?.mom_change_pct ?? 0) > 10 ? 'warning' : (metrics?.mom_change_pct ?? 0) < -5 ? 'positive' : 'neutral'}
          sparkline={sparklineData}
          icon={<DollarSign className="h-5 w-5" />}
          footer={
            <button type="button" className="inline-flex items-center gap-1.5 text-xs font-medium text-teal-700 hover:text-teal-900"
              onClick={() => { setExplainOpen(true); explainMutation.mutate({ start_date: explainWindow.start_date, end_date: explainWindow.end_date, language: lang, ...(providerParam ? { provider: providerParam } : {}) }) }}>
              <Lightbulb className="h-3 w-3" />{d.explainCostCta}
            </button>
          }
        />
        <KpiCard
          title={d.potentialSavings}
          value={fmtCost(summary?.total_potential_savings_usd ?? 0)}
          tone="positive"
          icon={<TrendingUp className="h-5 w-5" />}
          footer={<span>{d.openOpportunities.replace('{{count}}', String(openCount))}</span>}
        />
        <KpiCard
          title={d.todayCost}
          value={fmtCost(todayCost)}
          delta={deltaTodayVsAvg ?? undefined}
          deltaLabel={d.avgPrevious30d}
          tone={deltaTodayVsAvg != null && deltaTodayVsAvg > 15 ? 'warning' : 'neutral'}
          footer={!todayHasData ? <span className="text-amber-600">{d.billingProcessingPending}</span> : undefined}
        />
        <KpiCard
          title={d.events7d}
          value={(metrics?.event_count_7d ?? 0).toLocaleString()}
          tone={anomalyItems.filter((a) => a.severity === 'high').length > 0 ? 'negative' : 'neutral'}
          icon={<Activity className="h-5 w-5" />}
          footer={anomalyItems.length > 0 ? <span>{anomalyItems.length} {d.anomaliesTitle.toLowerCase()}</span> : undefined}
        />
      </div>

      {/* ═══ C. Main Row: Cost Trend + Next Best Action ═══ */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.6fr_1fr]">
        {/* Cost Pulse — dominant chart */}
        <ChartPanel
          title={d.costTrend}
          subtitle={recentEvents.length > 0 ? d.changeEventsOverlaid.replace('{{count}}', String(recentEvents.length)).replace('{{s}}', recentEvents.length !== 1 ? 's' : '') : undefined}
          empty={!metrics?.daily_trend || metrics.daily_trend.length === 0}
          emptyMessage={d.noCostData}
          height={300}
        >
          {metrics?.daily_trend && metrics.daily_trend.length > 0 && (
            <CostTrendChart data={metrics.daily_trend} events={recentEvents} currency={effectiveCurrency} height={300} />
          )}
        </ChartPanel>

        {/* Next Best Action / Intelligence Panel */}
        <Panel className="flex flex-col">
          <PanelHeader
            title={d.insightsTitle}
            badge={insightsDisplayData ? (
              <span className="rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-semibold text-teal-700">AI</span>
            ) : undefined}
          />
          {intelInsightsLoading ? (
            <div className="mt-4">
              <SkeletonSection lines={4} />
            </div>
          ) : intelInsightsError ? (
            <ErrorState
              className="mt-4"
              title={d.insightsUnavailable}
              description="Insight generation is temporarily unavailable. Refresh the workspace to try again."
            />
          ) : !insightsDisplayData ? (
            <EmptyState
              className="mt-4 py-10"
              icon="lightbulb"
              title={d.insightsUnavailable}
              description={d.insightsAction}
            />
          ) : (
            <div className="mt-4 flex flex-1 flex-col gap-3">
              <div className="rounded-lg border border-teal-200 bg-teal-50/60 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-teal-600">{d.insightsAction}</p>
                <p className="mt-1 text-sm font-medium text-teal-900">{insightsDisplayData.recommended_action}</p>
              </div>
              <div className="rounded-lg border border-gray-light bg-gray-light/30 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-cool">{d.insightsTopSaving}</p>
                <p className="mt-1 text-xs text-slate-700">{insightsDisplayData.top_saving_opportunity}</p>
              </div>
              <div className="rounded-lg border border-gray-light bg-gray-light/30 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-cool">{d.insightsMainRisk}</p>
                <p className="mt-1 text-xs text-slate-700">{insightsDisplayData.main_risk}</p>
              </div>
              <div className="mt-auto pt-2 border-t border-slate-100">
                <p className="text-diagnostic">
                  {d.insightsConfidence}: {Math.round(insightsDisplayData.confidence * 100)}%
                  {insightsDisplayData.model && !['mock', 'rules', 'rule-based'].includes(insightsDisplayData.model) ? ` · ${insightsDisplayData.model}` : ` · ${d.insightsModelRuleBased}`}
                </p>
              </div>
            </div>
          )}
        </Panel>
      </div>

      {/* ═══ D. Secondary Row: Anomalies + Budget + Top Services ═══ */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Anomalies */}
        <Panel compact>
          <PanelHeader
            title={d.anomaliesTitle}
            badge={anomalyItems.filter((a) => a.severity === 'high').length > 0 ? (
              <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-semibold text-rose-700">
                {anomalyItems.filter((a) => a.severity === 'high').length} high
              </span>
            ) : undefined}
            actions={
              <button type="button" className="text-[11px] text-brand-600 hover:underline" onClick={() => setAnomalyHighOnly((v) => !v)}>
                {anomalyHighOnly ? d.anomalyShowAll : d.anomalyCriticalOnly}
              </button>
            }
          />
          {intelAnomaliesLoading ? (
            <div className="mt-3">
              <SkeletonPrioritizedList items={4} />
            </div>
          ) : visibleAnomalies.length > 0 ? (
            <div className="mt-3 space-y-2">
              {visibleAnomalies.slice(0, 4).map((item) => (
                <div key={item.id} className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-800 truncate">{item.service}</p>
                    <p className="text-[10px] text-slate-400">{item.provider} · z:{item.z_score.toFixed(1)}{item.deviation_pct != null ? ` · +${item.deviation_pct.toFixed(0)}%` : ''}</p>
                  </div>
                  <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-semibold shrink-0', ANOMALY_BADGE[item.severity])}>
                    {anomalySeverityLabel[item.severity]}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              className="mt-3 py-10"
              icon="lightbulb"
              title={ux.emptyNoAnomalies}
              description={d.anomalyShowAll}
            />
          )}
        </Panel>

        {/* Budget & Risk */}
        <div ref={budgetSectionRef}>
          <BudgetWidget />
        </div>

        {/* Top Services Composition with Donut */}
        <Panel compact>
          <PanelHeader title={d.topServices} />
          {metrics?.top_services && metrics.top_services.length > 0 ? (
            <div className="mt-3">
              {/* Desktop: Donut + List side by side */}
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
                {/* Donut Chart */}
                <div className="flex-shrink-0 mx-auto sm:mx-0">
                  <ResponsiveContainer width={140} height={140}>
                    <PieChart>
                      <Pie
                        data={metrics.top_services.slice(0, 5).map((s) => ({
                          name: s.service,
                          value: s.percentage,
                        }))}
                        cx="50%"
                        cy="50%"
                        innerRadius={42}
                        outerRadius={60}
                        paddingAngle={2}
                        dataKey="value"
                        strokeWidth={0}
                      >
                        {metrics.top_services.slice(0, 5).map((_, i) => (
                          <Cell
                            key={`cell-${i}`}
                            fill={i === 0 ? '#0FA287' : i === 1 ? '#0FA287cc' : i === 2 ? '#0FA28788' : '#64748Baa'}
                          />
                        ))}
                      </Pie>
                      <RechartsTooltip
                        formatter={(value: number) => [`${value.toFixed(1)}%`, 'Share']}
                        contentStyle={{
                          background: 'white',
                          border: '1px solid #E5E7EB',
                          borderRadius: '8px',
                          fontSize: '12px',
                          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                        }}
                      />
                      {/* Center label */}
                      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" className="fill-navy" style={{ fontSize: '14px', fontWeight: 600 }}>
                        {metrics.top_services.length > 0 ? `${metrics.top_services.length}` : '5'}
                      </text>
                      <text x="50%" y="58%" textAnchor="middle" dominantBaseline="middle" className="fill-gray-cool" style={{ fontSize: '10px' }}>
                        services
                      </text>
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                {/* Service List with Bars */}
                <div className="flex-1 min-w-0 space-y-2.5">
                  {metrics.top_services.slice(0, 5).map((s, i) => (
                    <div key={s.service} className="group">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <span
                            className="h-2 w-2 rounded-full shrink-0"
                            style={{
                              backgroundColor: i === 0 ? '#0FA287' : i === 1 ? '#0FA287cc' : i === 2 ? '#0FA28788' : '#64748Baa'
                            }}
                          />
                          <p className="text-xs font-medium text-slate-700 truncate">{s.service}</p>
                        </div>
                        <span className="text-xs font-bold tabular-nums text-navy shrink-0">{s.percentage.toFixed(1)}%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden ml-4">
                        <div
                          className="h-full rounded-full transition-all duration-500 ease-out group-hover:opacity-80"
                          style={{
                            width: `${s.percentage}%`,
                            backgroundColor: i === 0 ? '#0FA287' : i === 1 ? '#0FA287cc' : i === 2 ? '#0FA28788' : '#64748Baa'
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex h-36 items-center justify-center text-xs text-slate-400">{d.noServiceData}</div>
          )}
        </Panel>
      </div>

      {/* ═══ E. Compact Activity Feed ═══ */}
      <Panel compact>
        <PanelHeader
          title={d.recentChanges}
          actions={
            <button type="button" className="inline-flex items-center gap-1 text-[11px] font-medium text-brand-600 hover:underline" onClick={() => navigate('/app/change-events')}>
              {d.viewAll} <ArrowRight className="h-3 w-3" />
            </button>
          }
        />
        {feedEvents.length > 0 ? (
          <div className="mt-2">
            {feedEvents.map((ev) => <ActivityRow key={ev.id} ev={ev} label={eventLabels[ev.event_type]} currency={effectiveCurrency} />)}
          </div>
        ) : (
          <div className="flex h-20 items-center justify-center text-xs text-slate-400">{ux.emptyNoRecentEvents}</div>
        )}
      </Panel>

      {/* ═══ F. Data Health (low priority, collapsible) ═══ */}
      <div className="rounded-panel border border-slate-200 bg-white shadow-panel">
        <button type="button" onClick={() => setDataHealthOpen((v) => !v)} className="flex w-full items-center justify-between px-5 py-3 text-left">
          <div className="flex items-center gap-3">
            <ReconciliationBadge status={reconciliationStatus} />
            <div>
              <h3 className="text-xs font-semibold text-slate-700">{ux.integrityDiagnosticsTitle}</h3>
              {metrics?.data_max_date && <p className="text-[10px] text-slate-400">{ux.integrityDataThrough.replace('{{date}}', metrics.data_max_date)}</p>}
            </div>
          </div>
          <ChevronRight className={clsx('h-4 w-4 text-slate-400 transition-transform', dataHealthOpen && 'rotate-90')} />
        </button>
        {dataHealthOpen && (
          <div className="border-t border-slate-100 px-5 py-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              <DataHealthCell label="Subscriptions" value={String(integrityData?.subscriptions_active ?? metrics?.subscriptions_included ?? 0)} />
              <DataHealthCell label="Currency" value={metrics?.billing_currency ?? '—'} />
              <DataHealthCell label="Provider" value={providerLabelMap[providerFilter]} />
              <DataHealthCell label="Data Coverage" value={`${metrics?.data_min_date ?? '—'} → ${metrics?.data_max_date ?? '—'}`} />
              <DataHealthCell label="Ingestion Gap" value={integrityData ? `${integrityData.ingestion_gap_days}d` : '—'} />
              <DataHealthCell label={ux.exportBasisLabel.replace('{{basis}}', '')} value={integrityData?.cost_basis_explanation || '—'} />
              <DataHealthCell label="Accounts" value={`${filteredAccounts.filter((a) => a.status === 'active').length} active / ${filteredAccounts.length} total`} />
              <DataHealthCell label="Events (7d)" value={String(metrics?.event_count_7d ?? 0)} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function DataHealthCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 text-xs font-medium text-slate-800 truncate">{value}</div>
    </div>
  )
}
