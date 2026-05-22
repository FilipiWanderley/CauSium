import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { executiveApi } from '../../api/executive'
import { ledgerApi } from '../../api/ledger'
import { opportunitiesApi } from '../../api/opportunities'
import { initiativesApi } from '../../api/initiatives'
import { KpiCard } from '../../components/Cards/KpiCard'
import { ChartPanel } from '../../components/Charts/ChartPanel'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { PageHeader } from '../../components/Layout/PageHeader'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { ExplainTooltip } from '../../components/UX/ExplainTooltip'
import { SkeletonMetricCards, SkeletonPrioritizedList, SkeletonSection } from '../../components/UX/Skeleton'
import { axisStyle, gridStyle, tooltipStyle, barDefaults, chartMargin, chartFill } from '../../components/Charts/chartTheme'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import clsx from 'clsx'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'
import type { ConfidenceTier, InitiativeBoard, Opportunity, RiskLevel } from '../../types'

// ─── Utilities ────────────────────────────────────────────────────────────────

const INITIATIVE_COLUMNS: Array<keyof InitiativeBoard> = ['backlog', 'planned', 'in_progress', 'review', 'done', 'cancelled']

function getOpportunitySavings(o: Opportunity) {
  return o.savings_evidence?.estimated_monthly_savings ?? o.estimated_monthly_savings_usd
}
function getOpportunityConfidenceTier(o: Opportunity): ConfidenceTier {
  if (o.savings_evidence?.confidence_tier) return o.savings_evidence.confidence_tier
  const f = o.savings_evidence?.savings_confidence ?? o.decision_evidence?.confidence ?? null
  if (f == null) return 'insufficient'
  if (f >= 0.8) return 'high'
  if (f >= 0.55) return 'medium'
  return 'low'
}
function getOpportunityRiskLevel(o: Opportunity): RiskLevel {
  return o.savings_evidence?.risk_level ?? o.decision_evidence?.risk_level ?? o.risk_level
}
function formatCoverage(count: number, total: number) {
  if (!total) return '0%'
  return `${Math.round((count / total) * 100)}%`
}
function formatDate(value: string | null, locale: string) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(date)
}
function capConfidence(v: ConfidenceTier) { return (v.charAt(0).toUpperCase() + v.slice(1)) as 'High' | 'Medium' | 'Low' | 'Insufficient' }
function capRisk(v: RiskLevel) { return (v.charAt(0).toUpperCase() + v.slice(1)) as 'High' | 'Medium' | 'Low' }

// ─── Main Component ───────────────────────────────────────────────────────────

export function ExecutivePage() {
  usePageTitle('Executive')
  const { t, lang } = useI18n()
  const e = t.executive
  const ux = t.ux
  const [subscriptionId, setSubscriptionId] = useState<string>('')

  // ─── Queries ────────────────────────────────────────────────────────────────

  const { data: subscriptionSummary, isLoading: subscriptionSummaryLoading, isError: subscriptionSummaryError } = useQuery({
    queryKey: ['ledger', 'subscriptions', 90],
    queryFn: () => ledgerApi.subscriptionCostSummary(90).then((r) => r.data),
  })

  const { data: dashboardMeta } = useQuery({
    queryKey: ['ledger', 'dashboard', 'meta', subscriptionId],
    queryFn: () => ledgerApi.dashboard(undefined, subscriptionId || undefined).then((r) => r.data),
    select: (d) => ({ data_min_date: d.data_min_date, data_max_date: d.data_max_date, subscriptions_included: d.subscriptions_included, billing_currency: d.billing_currency }),
  })

  const { data: summary, isLoading: summaryLoading, isError: summaryError, refetch: refetchSummary } = useQuery({
    queryKey: ['executive', 'summary', subscriptionId],
    queryFn: () => executiveApi.summary(subscriptionId || undefined).then((r) => r.data),
  })

  const { data: scorecard } = useQuery({
    queryKey: ['executive', 'scorecard'],
    queryFn: () => executiveApi.scorecard().then((r) => r.data),
  })

  const { data: opportunities = [] } = useQuery({
    queryKey: ['executive', 'opportunities-reporting'],
    queryFn: () => opportunitiesApi.list({ limit: 100, offset: 0 }).then((r) => r.data.items),
  })

  const { data: initiativesBoard } = useQuery({
    queryKey: ['executive', 'initiatives-board'],
    queryFn: () => initiativesApi.board().then((r) => r.data),
  })

  // ─── Derived data ───────────────────────────────────────────────────────────

  const displayCurrency = dashboardMeta?.billing_currency || DEFAULT_DISPLAY_CURRENCY
  const formatMoney = (value: number) => formatCurrency(value, displayCurrency)
  const hasMultipleSubscriptions = (subscriptionSummary?.subscription_count ?? 0) > 1
  const getSubName = (name: string | null | undefined, key: string | null | undefined) => {
    const n = name?.trim()
    return n || (key ? `${key.slice(0, 8)}…` : e.subscriptionNone)
  }
  const singleSubscriptionName = getSubName(subscriptionSummary?.items[0]?.subscription_name, subscriptionSummary?.items[0]?.subscription_id)

  const allInitiatives = useMemo(() => INITIATIVE_COLUMNS.flatMap((col) => initiativesBoard?.[col] ?? []), [initiativesBoard])
  const topOpportunities = useMemo(() => [...opportunities].sort((a, b) => getOpportunitySavings(b) - getOpportunitySavings(a)).slice(0, 5), [opportunities])
  const bestEvidenceRecs = useMemo(() =>
    [...opportunities]
      .filter((o) => o.savings_evidence || o.resource_context)
      .sort((a, b) => {
        const order: Record<ConfidenceTier, number> = { high: 4, medium: 3, low: 2, insufficient: 1 }
        const d = order[getOpportunityConfidenceTier(b)] - order[getOpportunityConfidenceTier(a)]
        return d !== 0 ? d : getOpportunitySavings(b) - getOpportunitySavings(a)
      })
      .slice(0, 5),
    [opportunities],
  )
  const priorityWatchlist = useMemo(() => {
    const risky = opportunities.filter((o) => getOpportunityRiskLevel(o) === 'high').sort((a, b) => getOpportunitySavings(b) - getOpportunitySavings(a)).slice(0, 3)
      .map((o) => ({ id: `opp-${o.id}`, title: o.title, detail: e.watchlistOpportunity.replace('{{value}}', formatMoney(getOpportunitySavings(o))), badge: e.watchlistHighRisk }))
    const overdue = allInitiatives.filter((i) => i.is_overdue).slice(0, 3)
      .map((i) => ({ id: `ini-${i.id}`, title: i.title, detail: i.sla_date ? e.watchlistInitiativeDue.replace('{{date}}', formatDate(i.sla_date, lang === 'pt' ? 'pt-BR' : 'en-US') ?? i.sla_date) : e.watchlistInitiativeNoDate, badge: e.watchlistExecutionRisk }))
    return [...risky, ...overdue].slice(0, 5)
  }, [allInitiatives, e, formatMoney, lang, opportunities])

  const highRiskCount = opportunities.filter((o) => getOpportunityRiskLevel(o) === 'high').length
  const lowConfidenceCount = opportunities.filter((o) => { const t = getOpportunityConfidenceTier(o); return t === 'low' || t === 'insufficient' }).length
  const highConfidenceCount = opportunities.filter((o) => getOpportunityConfidenceTier(o) === 'high').length
  const mediumConfidenceCount = opportunities.filter((o) => getOpportunityConfidenceTier(o) === 'medium').length
  const evidenceCoverageCount = opportunities.filter((o) => !!o.savings_evidence).length
  const resourceContextCount = opportunities.filter((o) => !!o.resource_context).length
  const dataSourceCount = opportunities.filter((o) => (o.resource_context?.data_sources.length ?? 0) > 0).length
  const overdueCount = allInitiatives.filter((i) => i.is_overdue).length
  const topImpactTeams = [...(scorecard?.teams ?? [])].sort((a, b) => b.current_month_cost_usd - a.current_month_cost_usd).slice(0, 6)
  const topImpactLead = topImpactTeams[0]
  const averageEfficiencyScore = topImpactTeams.length
    ? Math.round(topImpactTeams.reduce((sum, row) => sum + row.efficiency_score, 0) / topImpactTeams.length)
    : 0
  const totalVisibleTeamCost = topImpactTeams.reduce((sum, row) => sum + row.current_month_cost_usd, 0)
  const topTeamCostShare = totalVisibleTeamCost > 0 && topImpactLead
    ? Math.round((topImpactLead.current_month_cost_usd / totalVisibleTeamCost) * 100)
    : 0
  const highestOpportunityTeam = [...topImpactTeams].sort((a, b) => b.open_opportunities - a.open_opportunities)[0]
  const topImpactChartData = topImpactTeams.map((row, index) => ({
    ...row,
    team_label: row.team.length > 18 ? `${row.team.slice(0, 18)}...` : row.team,
    fill: index === 0 ? chartFill.primary : chartFill.primaryLight,
  }))

  if (summaryLoading || subscriptionSummaryLoading) {
    return (
      <div className="page-container">
        <PageHeader title={e.title} subtitle={e.subtitle} />
        <SkeletonMetricCards count={4} />
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.3fr_1fr]">
          <SkeletonSection lines={7} />
          <SkeletonPrioritizedList items={4} />
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1.5fr]">
          <SkeletonSection lines={5} />
          <SkeletonSection lines={6} />
        </div>
      </div>
    )
  }

  if (summaryError) {
    return (
      <div className="page-container">
        <PageHeader title={e.title} subtitle={e.subtitle} />
        <ErrorState
          title="Could not load executive summary"
          description="Executive reporting is temporarily unavailable. Please try again."
          onRetry={() => refetchSummary()}
          retryLabel="Retry"
        />
      </div>
    )
  }

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="page-container">
      {/* ═══ A. Page Header ═══ */}
      <PageHeader
        title={e.title}
        subtitle={e.subtitle}
        actions={
          <div className="flex items-center gap-3">
            <select value={hasMultipleSubscriptions ? subscriptionId : ''} onChange={(ev) => setSubscriptionId(ev.target.value)}
              disabled={!hasMultipleSubscriptions || subscriptionSummaryLoading || subscriptionSummaryError}
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:border-brand-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400">
              {subscriptionSummaryLoading ? <option value="">{e.subscriptionLoading}</option>
                : subscriptionSummaryError ? <option value="">{e.subscriptionUnavailable}</option>
                : hasMultipleSubscriptions ? (<><option value="">{e.allSubscriptionsConsolidated}</option>{subscriptionSummary?.items.map((s) => <option key={s.subscription_id} value={s.subscription_id}>{s.subscription_name || `${s.subscription_id.slice(0, 8)}…`}</option>)}</>)
                : <option value="">{singleSubscriptionName}</option>}
            </select>
            {scorecard && (
              <div className="hidden sm:flex items-center gap-1.5 rounded-md border border-brand-200 bg-brand-50 px-2.5 py-1.5">
                <span className="text-xs font-medium text-brand-700">{e.orgScore.replace('{{score}}', String(scorecard.org_efficiency_score))}</span>
              </div>
            )}
          </div>
        }
        meta={
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>{subscriptionId ? e.filtered : e.consolidated}</span>
            {dashboardMeta?.billing_currency && <span>{ux.billingCurrency.replace('{{currency}}', dashboardMeta.billing_currency)}</span>}
            {dashboardMeta?.data_max_date && <span>{ux.integrityDataThrough.replace('{{date}}', dashboardMeta.data_max_date)}</span>}
          </div>
        }
      />

      {/* ═══ B. Executive KPI Row ═══ */}
      <div className="kpi-grid">
        <KpiCard
          title={e.currentMonthCost}
          value={formatMoney(summary?.current_month_cost_usd ?? 0)}
          delta={summary?.mom_change_pct}
          deltaLabel={e.mom}
          tone={(summary?.mom_change_pct ?? 0) > 10 ? 'warning' : (summary?.mom_change_pct ?? 0) < -5 ? 'positive' : 'neutral'}
        />
        <KpiCard
          title={e.forecastNextMonth}
          value={formatMoney(summary?.forecast_next_month_usd ?? 0)}
          tone="neutral"
          footer={<span className="text-diagnostic">{e.confidence}: {summary?.forecast_confidence ?? e.na}</span>}
        />
        <KpiCard
          title={e.potentialSavings}
          value={formatMoney(summary?.total_potential_savings_usd ?? 0)}
          tone="positive"
          footer={<span>{e.openOpportunities.replace('{{count}}', String(summary?.open_opportunities ?? 0))}</span>}
        />
        <KpiCard
          title={e.realizedSavings}
          value={formatMoney(summary?.total_realized_savings_usd ?? 0)}
          tone="positive"
          footer={<span>{e.realizedDesc.replace('{{amount}}', formatMoney(summary?.savings_this_month_usd ?? 0))}</span>}
        />
      </div>

      {/* ═══ C. Savings Accountability: Estimated vs Realized ═══ */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.3fr_1fr]">
        {/* Top Opportunities (estimated) */}
        <Panel>
          <PanelHeader title={e.topOpportunitiesTitle} subtitle={e.topOpportunitiesSubtitle} />
          {!topOpportunities.length ? (
            <EmptyState
              icon="lightbulb"
              title={e.noTopOpportunitiesTitle}
              description={e.noTopOpportunitiesBody}
              className="mt-4"
            />
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    <th className="px-0 py-2">{e.colRecommendation}</th>
                    <th className="px-3 py-2 text-right">{e.colSavings}</th>
                    <th className="hidden px-3 py-2 md:table-cell">{e.confidence}</th>
                    <th className="hidden px-3 py-2 md:table-cell">{e.riskTableLabel}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {topOpportunities.map((o) => (
                    <tr key={o.id}>
                      <td className="px-0 py-2.5 align-top">
                        <p className="text-xs font-medium text-slate-800">{o.title}</p>
                        <p className="text-[10px] text-slate-400">{o.category.replace(/_/g, ' ')}</p>
                      </td>
                      <td className="px-3 py-2.5 align-top text-right font-semibold tabular-nums text-emerald-700 text-xs">{formatMoney(getOpportunitySavings(o))}</td>
                      <td className="hidden px-3 py-2.5 align-top md:table-cell">
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                          {e[`confidence${capConfidence(getOpportunityConfidenceTier(o))}` as 'confidenceHigh' | 'confidenceMedium' | 'confidenceLow' | 'confidenceInsufficient']}
                        </span>
                      </td>
                      <td className="hidden px-3 py-2.5 align-top md:table-cell">
                        <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-medium',
                          getOpportunityRiskLevel(o) === 'high' ? 'bg-rose-50 text-rose-700' : getOpportunityRiskLevel(o) === 'medium' ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700')}>
                          {e[`risk${capRisk(getOpportunityRiskLevel(o))}` as 'riskHigh' | 'riskMedium' | 'riskLow']}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        {/* Realized Savings (proven value) */}
        <Panel>
          <PanelHeader title={e.topSavingsTitle} subtitle={e.topSavingsSubtitle} />
          {summary?.top_savings && summary.top_savings.length > 0 ? (
            <ul className="mt-4 space-y-3">
              {summary.top_savings.map((s) => (
                <li key={s.initiative_id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-50 px-3 py-2.5">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-800 truncate">{s.title}</p>
                    <p className="text-[10px] text-slate-400">
                      {s.completed_at ? e.completedDate.replace('{{date}}', formatDate(s.completed_at, lang === 'pt' ? 'pt-BR' : 'en-US') ?? s.completed_at) : e.realizedAwaitingDate}
                    </p>
                  </div>
                  <span className="text-xs font-bold tabular-nums text-emerald-700 shrink-0">{formatMoney(s.realized_savings_usd)}{e.perMonth}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon="lightbulb"
              title={e.noTopSavingsTitle}
              description={e.noTopSavingsBody}
              className="mt-4"
            />
          )}

          {/* Savings summary bar */}
          <div className="mt-4 rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">{e.potentialSavings}</span>
              <span className="font-semibold tabular-nums text-slate-700">{formatMoney(summary?.total_potential_savings_usd ?? 0)}</span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all"
                style={{ width: `${Math.min(100, ((summary?.total_realized_savings_usd ?? 0) / Math.max(1, summary?.total_potential_savings_usd ?? 1)) * 100)}%` }}
              />
            </div>
            <div className="mt-1 flex items-center justify-between text-[10px] text-slate-400">
              <span>{e.realizedSavings}: {formatMoney(summary?.total_realized_savings_usd ?? 0)}</span>
              <span>{Math.round(((summary?.total_realized_savings_usd ?? 0) / Math.max(1, summary?.total_potential_savings_usd ?? 1)) * 100)}% {e.completed.toLowerCase()}</span>
            </div>
          </div>
        </Panel>
      </div>

      {/* ═══ D. Optimization Funnel ═══ */}
      <Panel>
        <PanelHeader
          title={e.optimizationProgressTitle}
          subtitle={e.optimizationProgressSubtitle}
          actions={<ExplainTooltip text={ux.tooltipForecast} />}
        />
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <FunnelStep label={e.identifiedRecommendations} value={summary?.open_opportunities ?? 0} color="bg-slate-500" />
          <FunnelStep label={e.inProgress} value={summary?.in_progress_initiatives ?? 0} color="bg-blue-500" />
          <FunnelStep label={e.completed} value={summary?.completed_initiatives ?? 0} color="bg-emerald-500" />
          <FunnelStep label={e.overdueInitiatives} value={overdueCount} color={overdueCount > 0 ? 'bg-amber-500' : 'bg-slate-300'} warning={overdueCount > 0} />
        </div>
        {/* Funnel progress bar */}
        <div className="mt-4 flex h-3 rounded-full overflow-hidden bg-slate-100">
          {(() => {
            const total = (summary?.open_opportunities ?? 0) + (summary?.in_progress_initiatives ?? 0) + (summary?.completed_initiatives ?? 0)
            if (!total) return null
            const completedPct = ((summary?.completed_initiatives ?? 0) / total) * 100
            const inProgressPct = ((summary?.in_progress_initiatives ?? 0) / total) * 100
            return (
              <>
                <div className="bg-emerald-500 transition-all" style={{ width: `${completedPct}%` }} />
                <div className="bg-blue-400 transition-all" style={{ width: `${inProgressPct}%` }} />
              </>
            )
          })()}
        </div>
        <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
          <span>{e.completed}: {summary?.completed_initiatives ?? 0}</span>
          <span>{e.inProgress}: {summary?.in_progress_initiatives ?? 0}</span>
          <span>{e.identifiedRecommendations}: {summary?.open_opportunities ?? 0}</span>
        </div>
      </Panel>

      {/* ═══ E. Risk & Governance ═══ */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1.5fr]">
        {/* Risk KPIs */}
        <Panel compact>
          <PanelHeader title={e.riskGovernanceTitle} subtitle={e.riskGovernanceSubtitle} />
          <div className="mt-3 space-y-2.5">
            <RiskRow label={e.highRiskRecommendations} value={highRiskCount} warning={highRiskCount > 0} />
            <RiskRow label={e.lowConfidenceRecommendations} value={lowConfidenceCount} warning={lowConfidenceCount > 0} />
            <RiskRow label={e.overdueInitiatives} value={overdueCount} warning={overdueCount > 0} />
          </div>
          {/* Coverage summary */}
          <div className="mt-4 pt-3 border-t border-slate-100">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">{e.coverageEvidenceTitle}</p>
            <div className="grid grid-cols-2 gap-2">
              <CoverageCell label={e.evidenceCoverageTitle} value={formatCoverage(evidenceCoverageCount, opportunities.length)} />
              <CoverageCell label={e.highConfidenceCoverageTitle} value={formatCoverage(highConfidenceCount, opportunities.length)} />
              <CoverageCell label={e.resourceContextCoverageTitle} value={formatCoverage(resourceContextCount, opportunities.length)} />
              <CoverageCell label={e.dataSourceCoverageTitle} value={formatCoverage(dataSourceCount, opportunities.length)} />
            </div>
          </div>
        </Panel>

        {/* Priority Watchlist */}
        <Panel compact>
          <PanelHeader title={e.priorityWatchlistTitle} subtitle={e.priorityWatchlistSubtitle} />
          {priorityWatchlist.length > 0 ? (
            <div className="mt-3 space-y-2">
              {priorityWatchlist.map((item) => (
                <div key={item.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-100 px-3 py-2.5">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-800">{item.title}</p>
                    <p className="text-[10px] text-slate-400">{item.detail}</p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 shrink-0">{item.badge}</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="lightbulb"
              title={e.noPriorityWatchlistTitle}
              description={e.noPriorityWatchlistBody}
              className="mt-3"
            />
          )}
        </Panel>
      </div>

      {/* ═══ F. Team Accountability ═══ */}
      {topImpactTeams.length > 0 && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.35fr_1fr]">
          <ChartPanel
            title={e.topImpactAreasTitle}
            subtitle={e.topImpactAreasSubtitle}
            height={320}
            actions={
              <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-semibold text-brand-700">
                {e.scoreLabel}
              </span>
            }
          >
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Largest cost area</p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{topImpactLead?.team ?? e.na}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {topImpactLead ? `${formatMoney(topImpactLead.current_month_cost_usd)} · ${topTeamCostShare}% of visible spend` : e.na}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Average efficiency</p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{averageEfficiencyScore}/100</p>
                  <p className="mt-1 text-xs text-slate-500">{topImpactTeams.length} teams in view</p>
                </div>
                <div className="rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Most open opportunities</p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{highestOpportunityTeam?.team ?? e.na}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {highestOpportunityTeam ? `${highestOpportunityTeam.open_opportunities} ${e.openOpps.toLowerCase()}` : e.na}
                  </p>
                </div>
              </div>
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topImpactChartData} layout="vertical" margin={chartMargin.withLabels}>
                    <CartesianGrid horizontal={false} {...gridStyle} />
                    <XAxis
                      type="number"
                      tick={axisStyle}
                      tickFormatter={(value: number) => formatMoney(value)}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      dataKey="team_label"
                      type="category"
                      tick={axisStyle}
                      width={110}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      {...tooltipStyle}
                      formatter={(_, __, item) => {
                        const row = item?.payload
                        if (!row) return []
                        return [
                          `${formatMoney(row.current_month_cost_usd)} · ${row.efficiency_score}/100 ${e.scoreLabel.toLowerCase()} · ${row.open_opportunities} ${e.openOpps.toLowerCase()}`,
                          row.team,
                        ]
                      }}
                    />
                    <Bar dataKey="current_month_cost_usd" radius={barDefaults.radius} maxBarSize={22}>
                      {topImpactChartData.map((row) => (
                        <Cell key={row.team} fill={row.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2.5">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Executive readout</p>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">
                  {topImpactLead
                    ? `${topImpactLead.team} currently carries the largest visible monthly cost footprint at ${formatMoney(topImpactLead.current_month_cost_usd)}. Use the accountability table to compare efficiency score and open opportunity volume before prioritizing follow-up.`
                    : 'Use the accountability table to compare monthly cost, efficiency score, and open opportunity volume.'}
                </p>
              </div>
            </div>
          </ChartPanel>
          <Panel>
            <PanelHeader
              title={e.team}
              subtitle="Supporting accountability detail"
            />
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    <th className="pb-2 pr-3">{e.team}</th>
                    <th className="pb-2 pr-3 text-right">{e.currentMonth}</th>
                    <th className="pb-2 pr-3 text-right">{e.openOpps}</th>
                    <th className="pb-2 text-right">{e.efficiency}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {topImpactTeams.map((row) => (
                    <tr key={row.team}>
                      <td className="py-2.5 pr-3 font-medium text-slate-800">{row.team}</td>
                      <td className="py-2.5 pr-3 text-right tabular-nums text-slate-600">{formatMoney(row.current_month_cost_usd)}</td>
                      <td className="py-2.5 pr-3 text-right text-slate-600">{row.open_opportunities}</td>
                      <td className="py-2.5 text-right">
                        <span className={clsx('font-semibold tabular-nums', row.efficiency_score >= 70 ? 'text-emerald-700' : row.efficiency_score >= 40 ? 'text-amber-700' : 'text-rose-700')}>
                          {row.efficiency_score}/100
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      )}

      {/* ═══ G. Supporting Metadata ═══ */}
      {dashboardMeta && (dashboardMeta.data_min_date || dashboardMeta.data_max_date) && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-diagnostic px-1">
          {dashboardMeta.data_min_date && dashboardMeta.data_max_date && (
            <span>{ux.billingDataRange.replace('{{start}}', dashboardMeta.data_min_date).replace('{{end}}', dashboardMeta.data_max_date)}</span>
          )}
          {(dashboardMeta.subscriptions_included ?? 0) > 0 && (
            <span>{ux.billingSubscriptions.replace('{{count}}', String(dashboardMeta.subscriptions_included))}</span>
          )}
          <span>{ux.costBasisActualPreTax}</span>
          <span>{e.confidenceCoverageSubtitle.replace('{{high}}', String(highConfidenceCount)).replace('{{medium}}', String(mediumConfidenceCount))}</span>
        </div>
      )}
    </div>
  )
}

function FunnelStep({ label, value, color, warning = false }: { label: string; value: number; color: string; warning?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3 text-center">
      <div className={clsx('mx-auto mb-2 h-1.5 w-8 rounded-full', color)} />
      <p className={clsx('text-xl font-bold tabular-nums', warning ? 'text-amber-700' : 'text-slate-900')}>{value}</p>
      <p className="mt-0.5 text-[10px] text-slate-500 leading-tight">{label}</p>
    </div>
  )
}

function RiskRow({ label, value, warning = false }: { label: string; value: number; warning?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 px-3 py-2">
      <span className="text-xs text-slate-600">{label}</span>
      <span className={clsx('text-sm font-bold tabular-nums', warning ? 'text-amber-700' : 'text-slate-800')}>{value}</span>
    </div>
  )
}

function CoverageCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center rounded-md bg-slate-50/80 px-2 py-1.5">
      <p className="text-sm font-bold tabular-nums text-slate-800">{value}</p>
      <p className="text-[9px] text-slate-400 leading-tight mt-0.5">{label}</p>
    </div>
  )
}



