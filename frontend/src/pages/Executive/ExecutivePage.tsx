import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { executiveApi } from '../../api/executive'
import { ledgerApi } from '../../api/ledger'
import { MetricCard } from '../../components/Cards/MetricCard'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { FreshnessIndicator } from '../../components/UX/FreshnessIndicator'
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
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'

export function ExecutivePage() {
  const { t } = useI18n()
  const e = t.executive
  const ux = t.ux
  const formatMoney = (value: number) => formatCurrency(value, DEFAULT_DISPLAY_CURRENCY)

  const [subscriptionId, setSubscriptionId] = useState<string>('')

  const { data: subscriptionSummary } = useQuery({
    queryKey: ['ledger', 'subscriptions', 30],
    queryFn: () => ledgerApi.subscriptionCostSummary(30).then((r) => r.data),
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
  const selectedSubscriptionScope =
    subscriptionSummary?.items.find((s) => s.subscription_id === subscriptionId)?.subscription_name ||
    `${subscriptionId.slice(0, 8)}…`

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
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">
            {e.financialValuesBrl}
          </span>
          <span className="rounded-full bg-gray-100 px-2.5 py-1 font-medium text-gray-700">
            {e.organizationWide}
          </span>
          <span className="rounded-full bg-blue-50 px-2.5 py-1 font-medium text-blue-700">
            {subscriptionId ? e.filtered : e.consolidated}
          </span>
          <span className="rounded-full bg-amber-50 px-2.5 py-1 font-medium text-amber-700">
            {e.financialMetric}
          </span>
        </div>
      </div>

      {/* Subscription filter */}
      {subscriptionSummary && subscriptionSummary.subscription_count > 1 && (
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">{e.subscriptionLabel}</label>
          <select
            value={subscriptionId}
            onChange={(ev) => setSubscriptionId(ev.target.value)}
            className="rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none"
          >
            <option value="">{e.allSubscriptionsConsolidated}</option>
            {subscriptionSummary.items.map((item) => (
              <option key={item.subscription_id} value={item.subscription_id}>
                {item.subscription_name || item.subscription_id.slice(0, 8) + '…'}
              </option>
            ))}
          </select>
          <span className="text-xs text-gray-400">
            {subscriptionId
              ? e.subscriptionViewing.replace('{{scope}}', selectedSubscriptionScope)
              : e.consolidatedAcross.replace('{{count}}', String(subscriptionSummary.subscription_count))}
          </span>
        </div>
      )}

      {/* Multi-subscription scope card */}
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
                {e.azureSubscriptionsConnected.replace('{{count}}', String(subscriptionSummary.subscription_count))}
              </p>
              <p className="text-xs text-blue-700">
                {formatMoney(subscriptionSummary.total_cost_usd)}{' '}
                {e.monitoredHistoricalDays.replace('{{days}}', String(subscriptionSummary.days))}
              </p>
            </div>
          </div>
          <div className="text-xs text-blue-500 hidden sm:block">{e.azureLabel}</div>
        </div>
      )}

      <div className="space-y-4">
        <SectionIntro
          title={e.overviewTitle}
          subtitle={e.overviewSubtitle}
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
            title={e.ytdSpend}
            value={formatMoney(summary?.ytd_cost_usd ?? 0)}
            subtitle={subscriptionId
              ? e.filteredScope.replace('{{scope}}', selectedSubscriptionScope)
              : e.ytdDesc}
            emphasis="secondary"
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
        </div>

        {/* Billing transparency context */}
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
          title={e.optimizationTitle}
          subtitle={e.optimizationSubtitle}
          freshness={ux.freshnessRefreshes}
          badges={[
            { label: e.financialMetric, tone: 'financial' },
            { label: subscriptionId ? e.subscriptionScoped : e.organizationWide, tone: subscriptionId ? 'subscription' : 'organization' },
          ]}
          compact
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <MetricCard title={e.inProgress} value={summary?.in_progress_initiatives ?? 0} subtitle={subscriptionId ? e.organizationWide : e.initiatives} />
          <MetricCard title={e.completed} value={summary?.completed_initiatives ?? 0} subtitle={subscriptionId ? e.organizationWide : e.initiatives} variant="success" />
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-gray-500">
              {e.forecastNextMonth}
              <ExplainTooltip text={ux.tooltipForecast} className="ml-1.5 align-middle" />
            </p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {formatMoney(summary?.forecast_next_month_usd ?? 0)}
            </p>
            <p className="mt-1 text-xs text-gray-400">
              {e.confidence}: {summary?.forecast_confidence ?? e.na} · {e.linearProjection}
            </p>
            {subscriptionId && (
              <p className="mt-1 text-xs text-brand-500">
                {e.filteredScope.replace('{{scope}}', selectedSubscriptionScope)}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Team scorecard */}
      {scorecard && scorecard.teams.length > 0 && (
        <div className="space-y-4">
          <SectionIntro
            title={e.operationsTitle}
            subtitle={e.operationsSubtitle}
            freshness={ux.freshnessRecent}
            badges={[
              { label: e.operationalMetric, tone: 'operational' },
              { label: e.organizationWide, tone: 'organization' },
            ]}
            compact
          />
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900">{e.teamScorecard}</h2>
              <span className="text-sm font-bold text-brand-600">
                {e.orgScore.replace('{{score}}', String(scorecard.org_efficiency_score))}
              </span>
            </div>

            <div className="mb-5 h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={scorecard.teams.slice(0, 8)} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
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
                  <th className="pb-2 pr-4">{e.mom}</th>
                  <th className="pb-2 pr-4">{e.openOpps}</th>
                  <th className="pb-2">{e.efficiency}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {scorecard.teams.map((row) => (
                  <tr key={row.team}>
                    <td className="py-2 pr-4 font-medium text-gray-900">{row.team}</td>
                    <td className="py-2 pr-4 text-gray-700">{formatMoney(row.current_month_cost_usd)}</td>
                    <td className={clsx('py-2 pr-4 text-xs font-medium', row.mom_change_pct > 0 ? 'text-red-600' : 'text-green-600')}>
                      {row.mom_change_pct > 0 ? '+' : ''}{row.mom_change_pct.toFixed(1)}%
                    </td>
                    <td className="py-2 pr-4 text-gray-600">{row.open_opportunities}</td>
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 rounded-full bg-gray-100">
                          <div
                            className={clsx(
                              'h-full rounded-full',
                              row.efficiency_score >= 70 ? 'bg-green-500' :
                              row.efficiency_score >= 40 ? 'bg-yellow-500' : 'bg-red-400'
                            )}
                            style={{ width: `${row.efficiency_score}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold text-gray-700 w-8">
                          {row.efficiency_score}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Top savings */}
      {summary?.top_savings && summary.top_savings.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900">{e.topSavings}</h2>
          <ul className="space-y-3">
            {summary.top_savings.map((s) => (
              <li key={s.initiative_id} className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">{s.title}</p>
                  {s.completed_at && (
                    <p className="text-xs text-gray-400">
                      {e.completedDate.replace('{{date}}', new Date(s.completed_at).toLocaleDateString())}
                    </p>
                  )}
                </div>
                <span className="text-sm font-bold text-green-600">
                  {formatMoney(s.realized_savings_usd)}{e.perMonth}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
