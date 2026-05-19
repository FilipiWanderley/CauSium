import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { executiveApi } from '../../api/executive'
import { ledgerApi } from '../../api/ledger'
import { opportunitiesApi } from '../../api/opportunities'
import { initiativesApi } from '../../api/initiatives'
import { MetricCard } from '../../components/Cards/MetricCard'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { ExplainTooltip } from '../../components/UX/ExplainTooltip'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import clsx from 'clsx'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'
import type { ConfidenceTier, Initiative, InitiativeBoard, Opportunity, RiskLevel } from '../../types'

const INITIATIVE_COLUMNS: Array<keyof InitiativeBoard> = ['backlog', 'planned', 'in_progress', 'review', 'done', 'cancelled']

function getOpportunitySavings(opportunity: Opportunity) {
  return opportunity.savings_evidence?.estimated_monthly_savings ?? opportunity.estimated_monthly_savings_usd
}

function getOpportunityConfidenceTier(opportunity: Opportunity): ConfidenceTier {
  if (opportunity.savings_evidence?.confidence_tier) return opportunity.savings_evidence.confidence_tier
  const fallback = opportunity.savings_evidence?.savings_confidence ?? opportunity.decision_evidence?.confidence ?? null
  if (fallback == null) return 'insufficient'
  if (fallback >= 0.8) return 'high'
  if (fallback >= 0.55) return 'medium'
  return 'low'
}

function getOpportunityRiskLevel(opportunity: Opportunity): RiskLevel {
  return opportunity.savings_evidence?.risk_level ?? opportunity.decision_evidence?.risk_level ?? opportunity.risk_level
}

function formatPercent(value: number) {
  return `${Math.round(value)}%`
}

function formatCoverage(count: number, total: number) {
  if (!total) return '0%'
  return formatPercent((count / total) * 100)
}

function formatDate(value: string | null, locale: string) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(date)
}

export function ExecutivePage() {
  usePageTitle('Executive')
  const { t, lang } = useI18n()
  const e = t.executive
  const ux = t.ux

  const [subscriptionId, setSubscriptionId] = useState<string>('')

  const {
    data: subscriptionSummary,
    isLoading: subscriptionSummaryLoading,
    isError: subscriptionSummaryError,
  } = useQuery({
    queryKey: ['ledger', 'subscriptions', 90],
    queryFn: () => ledgerApi.subscriptionCostSummary(90).then((r) => r.data),
  })

  const { data: dashboardMeta } = useQuery({
    queryKey: ['ledger', 'dashboard', 'meta', subscriptionId],
    queryFn: () => ledgerApi.dashboard(undefined, subscriptionId || undefined).then((r) => r.data),
    select: (d) => ({
      data_min_date: d.data_min_date,
      data_max_date: d.data_max_date,
      subscriptions_included: d.subscriptions_included,
      billing_currency: d.billing_currency,
    }),
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
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

  const displayCurrency = dashboardMeta?.billing_currency || DEFAULT_DISPLAY_CURRENCY
  const formatMoney = (value: number) => formatCurrency(value, displayCurrency)
  const hasMultipleSubscriptions = (subscriptionSummary?.subscription_count ?? 0) > 1
  const getSubscriptionDisplayName = (subscriptionName: string | null | undefined, subscriptionKey: string | null | undefined) => {
    const normalizedName = subscriptionName?.trim()
    if (normalizedName) return normalizedName
    return subscriptionKey ? `${subscriptionKey.slice(0, 8)}…` : e.subscriptionNone
  }
  const singleSubscriptionName =
    getSubscriptionDisplayName(subscriptionSummary?.items[0]?.subscription_name, subscriptionSummary?.items[0]?.subscription_id)
  const selectedSubscription = subscriptionSummary?.items.find((s) => s.subscription_id === subscriptionId)
  const selectedSubscriptionScope = getSubscriptionDisplayName(selectedSubscription?.subscription_name, subscriptionId)
  const subscriptionContextMessage = subscriptionSummaryLoading
    ? e.subscriptionLoading
    : subscriptionSummaryError
      ? e.subscriptionUnavailable
      : subscriptionId
        ? e.subscriptionViewing.replace('{{scope}}', selectedSubscriptionScope)
        : hasMultipleSubscriptions
          ? e.consolidatedAcross.replace('{{count}}', String(subscriptionSummary?.subscription_count ?? 0))
          : singleSubscriptionName
            ? e.subscriptionSingleScope.replace('{{scope}}', singleSubscriptionName)
            : e.subscriptionNone
  const allInitiatives = useMemo(
    () => INITIATIVE_COLUMNS.flatMap((column) => initiativesBoard?.[column] ?? []),
    [initiativesBoard],
  )
  const topOpportunities = useMemo(
    () => [...opportunities].sort((a, b) => getOpportunitySavings(b) - getOpportunitySavings(a)).slice(0, 5),
    [opportunities],
  )
  const bestEvidenceRecommendations = useMemo(
    () =>
      [...opportunities]
        .filter((opportunity) => opportunity.savings_evidence || opportunity.resource_context)
        .sort((a, b) => {
          const confidenceOrder: Record<ConfidenceTier, number> = {
            high: 4,
            medium: 3,
            low: 2,
            insufficient: 1,
          }
          const confidenceDelta =
            confidenceOrder[getOpportunityConfidenceTier(b)] - confidenceOrder[getOpportunityConfidenceTier(a)]
          if (confidenceDelta !== 0) return confidenceDelta
          return getOpportunitySavings(b) - getOpportunitySavings(a)
        })
        .slice(0, 5),
    [opportunities],
  )
  const priorityWatchlist = useMemo(() => {
    const riskyOpportunities = opportunities
      .filter((opportunity) => getOpportunityRiskLevel(opportunity) === 'high')
      .sort((a, b) => getOpportunitySavings(b) - getOpportunitySavings(a))
      .slice(0, 3)
      .map((opportunity) => ({
        id: `opportunity-${opportunity.id}`,
        title: opportunity.title,
        detail: e.watchlistOpportunity.replace('{{value}}', formatMoney(getOpportunitySavings(opportunity))),
        badge: e.watchlistHighRisk,
      }))

    const overdueInitiatives = allInitiatives
      .filter((initiative) => initiative.is_overdue)
      .slice(0, 3)
      .map((initiative) => ({
        id: `initiative-${initiative.id}`,
        title: initiative.title,
        detail: initiative.sla_date
          ? e.watchlistInitiativeDue.replace('{{date}}', formatDate(initiative.sla_date, lang === 'pt' ? 'pt-BR' : 'en-US') ?? initiative.sla_date)
          : e.watchlistInitiativeNoDate,
        badge: e.watchlistExecutionRisk,
      }))

    return [...riskyOpportunities, ...overdueInitiatives].slice(0, 5)
  }, [allInitiatives, e.watchlistExecutionRisk, e.watchlistHighRisk, e.watchlistInitiativeDue, e.watchlistInitiativeNoDate, e.watchlistOpportunity, formatMoney, lang, opportunities])

  const highRiskRecommendations = opportunities.filter((opportunity) => getOpportunityRiskLevel(opportunity) === 'high').length
  const lowConfidenceRecommendations = opportunities.filter((opportunity) => {
    const tier = getOpportunityConfidenceTier(opportunity)
    return tier === 'low' || tier === 'insufficient'
  }).length
  const highConfidenceRecommendations = opportunities.filter((opportunity) => getOpportunityConfidenceTier(opportunity) === 'high').length
  const mediumConfidenceRecommendations = opportunities.filter((opportunity) => getOpportunityConfidenceTier(opportunity) === 'medium').length
  const evidenceCoverageCount = opportunities.filter((opportunity) => !!opportunity.savings_evidence).length
  const resourceContextCoverageCount = opportunities.filter((opportunity) => !!opportunity.resource_context).length
  const dataSourceCoverageCount = opportunities.filter(
    (opportunity) => (opportunity.resource_context?.data_sources.length ?? 0) > 0,
  ).length
  const overdueInitiativesCount = allInitiatives.filter((initiative) => initiative.is_overdue).length
  const topImpactTeams = [...(scorecard?.teams ?? [])].sort((a, b) => b.current_month_cost_usd - a.current_month_cost_usd).slice(0, 6)
  const organizationWideOperationalNote = subscriptionId ? e.operationalScopeNote : e.organizationWide

  if (summaryLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{e.title}</h1>
        <p className="text-sm text-gray-500 mt-1">{e.subtitle}</p>
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
          <span>{e.financialValuesBrl}</span>
          <span>{subscriptionId ? e.filtered : e.consolidated}</span>
          <span>{e.executiveReady}</span>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-semibold text-gray-900">{e.exportReadinessTitle}</p>
            <p className="mt-1 text-sm text-gray-500">{e.exportReadinessSubtitle}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <DisabledActionChip label={e.exportCsvReady} />
            <DisabledActionChip label={e.exportPdfReady} />
            <DisabledActionChip label={e.executiveSnapshotReady} />
            <DisabledActionChip label={e.presentationModeReady} />
          </div>
        </div>
        <div className="mt-3 text-xs text-gray-500">{e.exportReadinessNote}</div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">{e.subscriptionLabel}</label>
        <select
          value={hasMultipleSubscriptions ? subscriptionId : ''}
          onChange={(ev) => setSubscriptionId(ev.target.value)}
          disabled={!hasMultipleSubscriptions || subscriptionSummaryLoading || subscriptionSummaryError}
          className="rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
        >
          {subscriptionSummaryLoading ? (
            <option value="">{e.subscriptionLoading}</option>
          ) : subscriptionSummaryError ? (
            <option value="">{e.subscriptionUnavailable}</option>
          ) : hasMultipleSubscriptions ? (
            <>
              <option value="">{e.allSubscriptionsConsolidated}</option>
              {subscriptionSummary?.items.map((item) => (
                <option key={item.subscription_id} value={item.subscription_id}>
                  {item.subscription_name || item.subscription_id.slice(0, 8) + '…'}
                </option>
              ))}
            </>
          ) : singleSubscriptionName ? (
            <option value="">{singleSubscriptionName}</option>
          ) : (
            <option value="">{e.subscriptionNone}</option>
          )}
        </select>
        <span className="text-xs text-gray-400">{subscriptionContextMessage}</span>
      </div>

      {subscriptionSummary && subscriptionSummary.subscription_count > 0 && (
        <div className="rounded-xl border border-blue-100 bg-blue-50 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100">
              <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 7h18M3 12h18M3 17h18" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-blue-900">
                {e.historicalCostCoverageTitle.replace('{{count}}', String(subscriptionSummary.subscription_count))}
              </p>
              <p className="text-xs text-blue-700">
                {formatMoney(subscriptionSummary.total_cost_usd)}{' '}
                {e.historicalCostCoverageSubtitle.replace('{{days}}', String(subscriptionSummary.days))}
              </p>
              <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-blue-600">
                <span>{e.billingRecordsLabel}</span>
                <span className="text-blue-300">•</span>
                <span>{e.historicalBaselineLabel}</span>
                <span className="text-blue-300">•</span>
                <span>{subscriptionId ? e.subscriptionScoped : e.providerNotFilteredLabel}</span>
              </div>
            </div>
          </div>
          <div className="text-xs text-blue-500 hidden sm:block">
            {subscriptionId ? e.filtered : e.consolidated}
          </div>
        </div>
      )}

      <div className="space-y-4">
        <SectionIntro
          title={e.executiveSummaryTitle}
          subtitle={e.executiveSummarySubtitle}
          freshness={ux.freshnessSnapshot}
          badges={[
            { label: e.financialMetric, tone: 'financial' },
            { label: subscriptionId ? e.subscriptionScoped : e.organizationWide, tone: subscriptionId ? 'subscription' : 'organization' },
            { label: e.billingContext, tone: 'billing' },
          ]}
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            title={e.currentMonthCost}
            value={formatMoney(summary?.current_month_cost_usd ?? 0)}
            change={summary?.mom_change_pct}
            changeLabel={e.mom}
            subtitle={subscriptionId
              ? e.filteredScope.replace('{{scope}}', selectedSubscriptionScope)
              : subscriptionSummary && subscriptionSummary.subscription_count > 1
                ? e.consolidatedScope.replace('{{count}}', String(subscriptionSummary.subscription_count))
                : undefined}
            variant={(summary?.mom_change_pct ?? 0) > 10 ? 'warning' : 'default'}
            emphasis="primary"
          />
          <MetricCard
            title={e.realizedSavings}
            value={formatMoney(summary?.total_realized_savings_usd ?? 0)}
            subtitle={subscriptionId ? e.organizationWide : e.realizedDesc.replace('{{amount}}', formatMoney(summary?.savings_this_month_usd ?? 0))}
            variant="success"
            emphasis="secondary"
          />
          <MetricCard
            title={e.potentialSavings}
            value={formatMoney(summary?.total_potential_savings_usd ?? 0)}
            subtitle={subscriptionId ? e.organizationWide : e.openOpportunities.replace('{{count}}', String(summary?.open_opportunities ?? 0))}
            variant="success"
            tooltip={ux.tooltipPotentialSavings}
          />
          <MetricCard
            title={e.confidenceCoverageTitle}
            value={formatCoverage(highConfidenceRecommendations + mediumConfidenceRecommendations, opportunities.length)}
            subtitle={e.confidenceCoverageSubtitle
              .replace('{{high}}', String(highConfidenceRecommendations))
              .replace('{{medium}}', String(mediumConfidenceRecommendations))
            }
            emphasis="secondary"
          />
        </div>

        {dashboardMeta && (dashboardMeta.data_min_date || dashboardMeta.data_max_date) && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-400 mt-2">
            {dashboardMeta.data_min_date && dashboardMeta.data_max_date && (
              <span>{ux.billingDataRange.replace('{{start}}', dashboardMeta.data_min_date).replace('{{end}}', dashboardMeta.data_max_date)}</span>
            )}
            {(dashboardMeta.subscriptions_included ?? 0) > 0 && (
              <span>{ux.billingSubscriptions.replace('{{count}}', String(dashboardMeta.subscriptions_included))}</span>
            )}
            <span>{ux.costBasisActualPreTax}</span>
            {dashboardMeta.billing_currency && (
              <span>{ux.billingCurrency.replace('{{currency}}', dashboardMeta.billing_currency)}</span>
            )}
          </div>
        )}
      </div>

      <div className="space-y-4">
        <SectionIntro
          title={e.savingsOverviewTitle}
          subtitle={subscriptionId ? e.savingsOverviewFilteredSubtitle : e.savingsOverviewSubtitle}
          freshness={ux.freshnessRecent}
          badges={[
            { label: e.financialMetric, tone: 'financial' },
            { label: organizationWideOperationalNote, tone: 'organization' },
          ]}
          compact
        />
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.3fr_0.9fr]">
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">{e.topOpportunitiesTitle}</h2>
                <p className="mt-1 text-xs text-gray-500">{e.topOpportunitiesSubtitle}</p>
              </div>
              <span className="text-xs text-gray-400">{e.organizationWide}</span>
            </div>

            {!topOpportunities.length ? (
              <EmptyState title={e.noTopOpportunitiesTitle} body={e.noTopOpportunitiesBody} />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                      <th className="px-0 py-2">{e.colRecommendation}</th>
                      <th className="px-3 py-2">{e.colSavings}</th>
                      <th className="hidden px-3 py-2 md:table-cell">{e.confidence}</th>
                      <th className="hidden px-3 py-2 md:table-cell">{e.riskTableLabel}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {topOpportunities.map((opportunity) => (
                      <tr key={opportunity.id}>
                        <td className="px-0 py-3 align-top">
                          <div className="min-w-[240px]">
                            <p className="font-medium text-gray-900">{opportunity.title}</p>
                            <p className="mt-1 text-xs text-gray-500">{opportunity.category.replace(/_/g, ' ')}</p>
                          </div>
                        </td>
                        <td className="px-3 py-3 align-top font-semibold text-emerald-700">
                          {formatMoney(getOpportunitySavings(opportunity))}
                        </td>
                        <td className="hidden px-3 py-3 align-top md:table-cell">
                          <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                            {e[`confidence${capitalizeConfidence(getOpportunityConfidenceTier(opportunity))}` as 'confidenceHigh' | 'confidenceMedium' | 'confidenceLow' | 'confidenceInsufficient']}
                          </span>
                        </td>
                        <td className="hidden px-3 py-3 align-top md:table-cell">
                          <span className={clsx(
                            'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                            getOpportunityRiskLevel(opportunity) === 'high'
                              ? 'bg-red-50 text-red-700'
                              : getOpportunityRiskLevel(opportunity) === 'medium'
                                ? 'bg-amber-50 text-amber-700'
                                : 'bg-emerald-50 text-emerald-700',
                          )}>
                            {e[`risk${capitalizeRisk(getOpportunityRiskLevel(opportunity))}` as 'riskHigh' | 'riskMedium' | 'riskLow']}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="mb-4">
              <h2 className="text-sm font-semibold text-gray-900">{e.topSavingsTitle}</h2>
              <p className="mt-1 text-xs text-gray-500">{e.topSavingsSubtitle}</p>
            </div>
            {summary?.top_savings && summary.top_savings.length > 0 ? (
              <ul className="space-y-3">
                {summary.top_savings.map((saving) => (
                  <li key={saving.initiative_id} className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-900">{saving.title}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {saving.completed_at
                          ? e.completedDate.replace('{{date}}', formatDate(saving.completed_at, lang === 'pt' ? 'pt-BR' : 'en-US') ?? saving.completed_at)
                          : e.realizedAwaitingDate}
                      </p>
                    </div>
                    <span className="text-sm font-bold text-emerald-700">
                      {formatMoney(saving.realized_savings_usd)}{e.perMonth}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title={e.noTopSavingsTitle} body={e.noTopSavingsBody} />
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <SectionIntro
          title={e.optimizationProgressTitle}
          subtitle={e.optimizationProgressSubtitle}
          freshness={ux.freshnessRefreshes}
          badges={[
            { label: e.operationalMetric, tone: 'operational' },
            { label: organizationWideOperationalNote, tone: 'organization' },
          ]}
          compact
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard title={e.identifiedRecommendations} value={summary?.open_opportunities ?? 0} subtitle={organizationWideOperationalNote} />
          <MetricCard title={e.inProgress} value={summary?.in_progress_initiatives ?? 0} subtitle={e.initiatives} />
          <MetricCard title={e.completed} value={summary?.completed_initiatives ?? 0} subtitle={e.initiatives} variant="success" />
          <MetricCard title={e.overdueInitiatives} value={overdueInitiativesCount} subtitle={e.executionRiskSubtitle} variant={overdueInitiativesCount > 0 ? 'warning' : 'default'} />
        </div>

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">{e.forecastNextMonth}</h2>
                <p className="mt-1 text-xs text-gray-500">{e.forecastSubtitle}</p>
              </div>
              <ExplainTooltip text={ux.tooltipForecast} />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <p className="text-3xl font-bold text-gray-900">{formatMoney(summary?.forecast_next_month_usd ?? 0)}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {e.confidence}: {summary?.forecast_confidence ?? e.na} · {e.linearProjection}
                </p>
              </div>
              <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <ProgressRow label={e.identifiedRecommendations} value={summary?.open_opportunities ?? 0} />
                <ProgressRow label={e.inProgress} value={summary?.in_progress_initiatives ?? 0} />
                <ProgressRow label={e.completed} value={summary?.completed_initiatives ?? 0} />
                <ProgressRow label={e.overdueInitiatives} value={overdueInitiativesCount} warning={overdueInitiativesCount > 0} />
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">{e.topImpactAreasTitle}</h2>
                <p className="mt-1 text-xs text-gray-500">{e.topImpactAreasSubtitle}</p>
              </div>
              {scorecard && (
                <span className="text-sm font-bold text-brand-600">
                  {e.orgScore.replace('{{score}}', String(scorecard.org_efficiency_score))}
                </span>
              )}
            </div>

            {topImpactTeams.length > 0 ? (
              <>
                <div className="mb-5 h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={topImpactTeams} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="team" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number) => [`${v}/100`, e.scoreLabel]} />
                      <Bar dataKey="efficiency_score" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs font-medium text-gray-500">
                      <th className="pb-2 pr-4">{e.team}</th>
                      <th className="pb-2 pr-4">{e.currentMonth}</th>
                      <th className="pb-2 pr-4">{e.openOpps}</th>
                      <th className="pb-2">{e.efficiency}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {topImpactTeams.map((row) => (
                      <tr key={row.team}>
                        <td className="py-2 pr-4 font-medium text-gray-900">{row.team}</td>
                        <td className="py-2 pr-4 text-gray-700">{formatMoney(row.current_month_cost_usd)}</td>
                        <td className="py-2 pr-4 text-gray-600">{row.open_opportunities}</td>
                        <td className="py-2 text-xs font-semibold text-gray-700">{row.efficiency_score}/100</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <EmptyState title={e.noImpactAreasTitle} body={e.noImpactAreasBody} />
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <SectionIntro
          title={e.riskGovernanceTitle}
          subtitle={e.riskGovernanceSubtitle}
          freshness={ux.freshnessRecent}
          badges={[
            { label: e.operationalMetric, tone: 'operational' },
            { label: organizationWideOperationalNote, tone: 'organization' },
          ]}
          compact
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <MetricCard title={e.highRiskRecommendations} value={highRiskRecommendations} subtitle={e.highRiskRecommendationsSubtitle} variant={highRiskRecommendations > 0 ? 'warning' : 'default'} />
          <MetricCard title={e.lowConfidenceRecommendations} value={lowConfidenceRecommendations} subtitle={e.lowConfidenceRecommendationsSubtitle} variant={lowConfidenceRecommendations > 0 ? 'warning' : 'default'} />
          <MetricCard title={e.overdueInitiatives} value={overdueInitiativesCount} subtitle={e.overdueInitiativesSubtitle} variant={overdueInitiativesCount > 0 ? 'warning' : 'default'} />
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-gray-900">{e.priorityWatchlistTitle}</h2>
            <p className="mt-1 text-xs text-gray-500">{e.priorityWatchlistSubtitle}</p>
          </div>
          {priorityWatchlist.length > 0 ? (
            <ul className="space-y-3">
              {priorityWatchlist.map((item) => (
                <li key={item.id} className="flex items-start justify-between gap-3 rounded-lg border border-gray-100 px-3 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900">{item.title}</p>
                    <p className="mt-1 text-xs text-gray-500">{item.detail}</p>
                  </div>
                  <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {item.badge}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title={e.noPriorityWatchlistTitle} body={e.noPriorityWatchlistBody} />
          )}
        </div>
      </div>

      <div className="space-y-4">
        <SectionIntro
          title={e.coverageEvidenceTitle}
          subtitle={e.coverageEvidenceSubtitle}
          freshness={ux.freshnessSnapshot}
          badges={[
            { label: e.financialMetric, tone: 'financial' },
            { label: organizationWideOperationalNote, tone: 'organization' },
          ]}
          compact
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <CoverageCard
            title={e.evidenceCoverageTitle}
            value={formatCoverage(evidenceCoverageCount, opportunities.length)}
            subtitle={e.evidenceCoverageSubtitleValue.replace('{{count}}', String(evidenceCoverageCount)).replace('{{total}}', String(opportunities.length))}
          />
          <CoverageCard
            title={e.resourceContextCoverageTitle}
            value={formatCoverage(resourceContextCoverageCount, opportunities.length)}
            subtitle={e.resourceContextCoverageSubtitle.replace('{{count}}', String(resourceContextCoverageCount)).replace('{{total}}', String(opportunities.length))}
          />
          <CoverageCard
            title={e.highConfidenceCoverageTitle}
            value={formatCoverage(highConfidenceRecommendations, opportunities.length)}
            subtitle={e.highConfidenceCoverageSubtitle.replace('{{count}}', String(highConfidenceRecommendations)).replace('{{total}}', String(opportunities.length))}
          />
          <CoverageCard
            title={e.dataSourceCoverageTitle}
            value={formatCoverage(dataSourceCoverageCount, opportunities.length)}
            subtitle={e.dataSourceCoverageSubtitle.replace('{{count}}', String(dataSourceCoverageCount)).replace('{{total}}', String(opportunities.length))}
          />
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-gray-900">{e.bestEvidenceTitle}</h2>
            <p className="mt-1 text-xs text-gray-500">{e.bestEvidenceSubtitle}</p>
          </div>
          {bestEvidenceRecommendations.length > 0 ? (
            <div className="space-y-3">
              {bestEvidenceRecommendations.map((opportunity) => (
                <div key={opportunity.id} className="flex items-start justify-between gap-3 rounded-lg border border-gray-100 px-3 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900">{opportunity.title}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-gray-500">
                      <span>{e.evidenceSavings.replace('{{amount}}', formatMoney(getOpportunitySavings(opportunity)))}</span>
                      <span className="text-gray-300">•</span>
                      <span>{opportunity.savings_evidence ? e.evidenceFinancial : e.evidencePartial}</span>
                      <span className="text-gray-300">•</span>
                      <span>{opportunity.resource_context ? e.evidenceContext : e.evidenceNoContext}</span>
                    </div>
                  </div>
                  <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {e[`confidence${capitalizeConfidence(getOpportunityConfidenceTier(opportunity))}` as 'confidenceHigh' | 'confidenceMedium' | 'confidenceLow' | 'confidenceInsufficient']}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title={e.noBestEvidenceTitle} body={e.noBestEvidenceBody} />
          )}
        </div>
      </div>
    </div>
  )
}

function DisabledActionChip({ label }: { label: string }) {
  return (
    <button
      type="button"
      disabled
      className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-medium text-gray-500 opacity-80"
    >
      {label}
    </button>
  )
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center">
      <p className="text-sm font-medium text-gray-700">{title}</p>
      <p className="mt-1 text-xs text-gray-500">{body}</p>
    </div>
  )
}

function CoverageCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="mt-1 text-xs text-gray-500">{subtitle}</p>
    </div>
  )
}

function ProgressRow({ label, value, warning = false }: { label: string; value: number; warning?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm text-gray-600">{label}</span>
      <span className={clsx('text-sm font-semibold', warning ? 'text-amber-700' : 'text-gray-900')}>{value}</span>
    </div>
  )
}

function capitalizeConfidence(value: ConfidenceTier) {
  return value.charAt(0).toUpperCase() + value.slice(1) as 'High' | 'Medium' | 'Low' | 'Insufficient'
}

function capitalizeRisk(value: RiskLevel) {
  return value.charAt(0).toUpperCase() + value.slice(1) as 'High' | 'Medium' | 'Low'
}
