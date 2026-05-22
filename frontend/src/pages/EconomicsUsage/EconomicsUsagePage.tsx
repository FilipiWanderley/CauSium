import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, TrendingUp } from 'lucide-react'
import { ledgerApi } from '../../api/ledger'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { formatDateShort } from '../../utils/format'
import { usePersistentNumber } from '../../hooks/usePersistentBoolean'
import { KpiCard } from '../../components/Cards/KpiCard'
import { PageHeader } from '../../components/Layout/PageHeader'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { SkeletonMetricCards, SkeletonTable } from '../../components/UX/Skeleton'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'

const numberFmt = new Intl.NumberFormat('en-US')

export function EconomicsUsagePage() {
  usePageTitle('Economics — Usage')
  const { t } = useI18n()
  const eu = t.economicsUsage
  const ux = t.ux

  const [days, setDays] = usePersistentNumber('sp.economicsUsage.days', 30, [30, 60, 90, 180])

  const trendQuery = useQuery({
    queryKey: ['economics-usage-trend', days],
    queryFn: () => ledgerApi.costTrend(days).then((r) => r.data),
    staleTime: 30_000,
    retry: 2,
  })

  const dashboardQuery = useQuery({
    queryKey: ['economics-usage-dashboard'],
    queryFn: () => ledgerApi.dashboard().then((r) => r.data),
    staleTime: 30_000,
    retry: 2,
  })

  const reservationCoverageQuery = useQuery({
    queryKey: ['economics-reservation-coverage', days],
    queryFn: () => ledgerApi.reservationCoverage(days).then((r) => r.data),
    staleTime: 30_000,
    retry: 2,
  })

  const usageSignals = useMemo(() => {
    const points = trendQuery.data ?? []
    if (!points.length) {
      return { dailyAvg: 0, peak: 0, volatility: 0 }
    }

    const costs = points.map((p) => p.cost_usd)
    const avg = costs.reduce((sum, c) => sum + c, 0) / costs.length
    const peak = Math.max(...costs)
    const variance = costs.reduce((sum, c) => sum + (c - avg) ** 2, 0) / costs.length
    const volatility = Math.sqrt(variance)

    return { dailyAvg: avg, peak, volatility }
  }, [trendQuery.data])

  const efficiencyScore = useMemo(() => {
    const mom = Math.abs(dashboardQuery.data?.mom_change_pct ?? 0)
    const normalizedVolatility = usageSignals.dailyAvg > 0 ? usageSignals.volatility / usageSignals.dailyAvg : 0
    const raw = 100 - mom * 1.2 - normalizedVolatility * 100
    return Math.max(0, Math.min(100, Math.round(raw)))
  }, [dashboardQuery.data?.mom_change_pct, usageSignals.dailyAvg, usageSignals.volatility])

  const displayCurrency = dashboardQuery.data?.currency ?? DEFAULT_DISPLAY_CURRENCY
  const formatMoney = (value: number) => formatCurrency(value, displayCurrency)
  const momChange = dashboardQuery.data?.mom_change_pct ?? 0
  const currentMonthCost = dashboardQuery.data?.current_month_cost ?? 0
  const previousMonthCost = dashboardQuery.data?.previous_month_cost ?? 0
  const activeAccounts = dashboardQuery.data?.active_accounts ?? 0
  const recentEvents = dashboardQuery.data?.event_count_7d ?? 0
  const dataCoverageLabel =
    dashboardQuery.data?.data_min_date && dashboardQuery.data?.data_max_date
      ? `${formatDateShort(dashboardQuery.data.data_min_date)} to ${formatDateShort(dashboardQuery.data.data_max_date)}`
      : 'Coverage updates automatically as new billing data arrives.'
  const usagePostureTone =
    efficiencyScore >= 70 ? 'positive' : efficiencyScore >= 40 ? 'warning' : 'negative'
  const usagePostureLabel =
    efficiencyScore >= 70 ? 'Stable usage posture' : efficiencyScore >= 40 ? 'Mixed usage posture' : 'Volatile usage posture'
  const usagePostureSummary =
    momChange > 10
      ? 'Usage spend is accelerating faster than the prior month and needs closer review.'
      : momChange < -5
        ? 'Usage spend is moderating versus the prior month while core activity remains in range.'
        : 'Usage spend is tracking close to the prior month with no major directional break.'

  return (
    <div className="page-container">
      <PageHeader
        title={eu.title}
        subtitle={eu.subtitle}
        meta={
          <>
            <span>{eu.operationalMetric}</span>
            <span>{eu.organizationWide}</span>
            <span>Billing currency values</span>
          </>
        }
      />

      <Panel flush className="overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <PanelHeader
            title="Usage command center"
            subtitle="Set the reporting window and keep operational usage diagnostics aligned with the current billing view."
          />
        </div>
        <div className="space-y-4 px-5 py-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
              <label className="block min-w-[220px] flex-1 text-xs font-medium uppercase tracking-wide text-gray-500 sm:max-w-sm">
                {eu.timeWindow}
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                >
                  <option value={30}>{eu.last30}</option>
                  <option value={60}>{eu.last60}</option>
                  <option value={90}>{eu.last90}</option>
                  <option value={180}>{eu.last180}</option>
                </select>
              </label>
              <div className="min-w-[220px] rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 text-sm text-slate-600">
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Coverage</div>
                <div className="mt-1 text-sm font-medium text-slate-800">{dataCoverageLabel}</div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-600">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1">
                {activeAccounts.toLocaleString()} active accounts
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1">
                {recentEvents.toLocaleString()} events in the last 7 days
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1">
                Billing currency: {displayCurrency}
              </span>
            </div>
          </div>
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,1fr)]">
            <div className="rounded-xl border border-slate-200 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 px-5 py-4 text-white">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">Usage posture</div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span
                  className={
                    usagePostureTone === 'positive'
                      ? 'inline-flex items-center rounded-full bg-emerald-400/15 px-2.5 py-1 text-xs font-semibold text-emerald-200'
                      : usagePostureTone === 'warning'
                        ? 'inline-flex items-center rounded-full bg-amber-400/15 px-2.5 py-1 text-xs font-semibold text-amber-200'
                        : 'inline-flex items-center rounded-full bg-rose-400/15 px-2.5 py-1 text-xs font-semibold text-rose-200'
                  }
                >
                  {usagePostureLabel}
                </span>
                <span className="text-xs text-slate-300">
                  {momChange >= 0 ? '+' : ''}
                  {momChange.toFixed(1)}% vs prior month
                </span>
              </div>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-100">
                {usagePostureSummary}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Current month</div>
                <div className="mt-2 text-lg font-semibold text-slate-900">{formatMoney(currentMonthCost)}</div>
                <p className="mt-1 text-xs text-slate-500">Current spend tracked in billing currency.</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Previous month</div>
                <div className="mt-2 text-lg font-semibold text-slate-900">{formatMoney(previousMonthCost)}</div>
                <p className="mt-1 text-xs text-slate-500">Baseline used for month-over-month movement.</p>
              </div>
            </div>
          </div>
        </div>
      </Panel>

      <Panel className="border-slate-200 bg-slate-50/60">
        <PanelHeader
          title="Usage interpretation"
          subtitle="Use the current usage posture, volatility, and coverage trend to decide where to review reservation exposure and day-by-day movement next."
        />
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          <div className="rounded-xl border border-white bg-white px-4 py-3 shadow-sm">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Daily average</div>
            <div className="mt-2 text-lg font-semibold text-slate-900">{numberFmt.format(Math.round(usageSignals.dailyAvg))}</div>
            <p className="mt-1 text-xs text-slate-500">Average daily usage cost across the selected reporting window.</p>
          </div>
          <div className="rounded-xl border border-white bg-white px-4 py-3 shadow-sm">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Peak usage day</div>
            <div className="mt-2 text-lg font-semibold text-slate-900">{numberFmt.format(Math.round(usageSignals.peak))}</div>
            <p className="mt-1 text-xs text-slate-500">Highest single-day usage cost observed in the current window.</p>
          </div>
          <div className="rounded-xl border border-white bg-white px-4 py-3 shadow-sm">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Volatility signal</div>
            <div className="mt-2 text-lg font-semibold text-slate-900">{numberFmt.format(Math.round(usageSignals.volatility))}</div>
            <p className="mt-1 text-xs text-slate-500">Higher values indicate less predictable day-to-day usage.</p>
          </div>
        </div>
      </Panel>

      <section className="section-group">
        <SectionIntro
          title={eu.operationsTitle}
          subtitle={eu.operationsSubtitle}
          freshness={ux.freshnessRefreshes}
          badges={[
            { label: eu.operationalMetric, tone: 'operational' },
            { label: eu.organizationWide, tone: 'organization' },
          ]}
        />
        <div className="kpi-grid">
          <KpiCard
            title={eu.dailyAvg}
            value={numberFmt.format(Math.round(usageSignals.dailyAvg))}
            icon={<Activity className="h-4 w-4" />}
            compact
            footer={<span>{eu.dailyAvgDesc}</span>}
          />
          <KpiCard
            title={eu.peakDay}
            value={numberFmt.format(Math.round(usageSignals.peak))}
            icon={<TrendingUp className="h-4 w-4" />}
            compact
            footer={<span>{eu.peakDayDesc}</span>}
          />
          <KpiCard
            title={eu.volatility}
            value={numberFmt.format(Math.round(usageSignals.volatility))}
            icon={<Activity className="h-4 w-4" />}
            compact
            footer={<span>{eu.volatilityDesc}. {ux.tooltipVolatility}</span>}
          />
          <KpiCard
            title={eu.efficiencyScore}
            value={`${efficiencyScore}`}
            icon={<TrendingUp className="h-4 w-4" />}
            compact
            tone={efficiencyScore >= 70 ? 'positive' : efficiencyScore >= 40 ? 'warning' : 'negative'}
            footer={<span>{eu.efficiencyScoreDesc}. {ux.tooltipEfficiencyScore}</span>}
          />
        </div>
      </section>

      <section>
        <SectionIntro
          title={eu.financialTitle}
          subtitle={eu.financialSubtitle}
          freshness={ux.freshnessSnapshot}
          badges={[
            { label: eu.financialValuesBrl, tone: 'billing' },
            { label: eu.organizationWide, tone: 'organization' },
          ]}
          compact
        />
        <Panel>
          <PanelHeader
            title={eu.reservationCoverage}
            subtitle="Track reserved and uncovered compute cost with the same billing-currency context used across the economics surfaces."
          />
          <div className="mt-4">
            {reservationCoverageQuery.isLoading ? (
              <SkeletonMetricCards count={4} />
            ) : reservationCoverageQuery.isError ? (
              <ErrorState
                title={eu.reservationCoverageEmpty}
                description="Reservation coverage diagnostics are temporarily unavailable for the selected window."
                onRetry={() => reservationCoverageQuery.refetch()}
                retryLabel={t.common.reset}
                compact
              />
            ) : !reservationCoverageQuery.data ? (
              <EmptyState
                icon="lightbulb"
                title={eu.reservationCoverageEmpty}
                description="Try a shorter window or validate reservation telemetry for this workspace."
                action={days !== 30 ? { label: eu.last30, onClick: () => setDays(30) } : undefined}
              />
            ) : (
              <div className="space-y-5">
                <div className="kpi-grid">
                  <KpiCard
                    title={eu.computeSpendBasis}
                    value={formatMoney(reservationCoverageQuery.data.total_compute_cost_usd)}
                    icon={<Activity className="h-4 w-4" />}
                    compact
                    footer={<span>{eu.organizationWide}</span>}
                  />
                  <KpiCard
                    title={eu.reservedSpendBasis}
                    value={formatMoney(reservationCoverageQuery.data.total_reserved_cost_usd)}
                    icon={<TrendingUp className="h-4 w-4" />}
                    compact
                    footer={<span>{eu.organizationWide}</span>}
                  />
                  <KpiCard
                    title={eu.uncoveredSpendBasis}
                    value={formatMoney(reservationCoverageQuery.data.uncovered_compute_cost_usd)}
                    icon={<Activity className="h-4 w-4" />}
                    compact
                    footer={<span>{eu.organizationWide}</span>}
                  />
                  <KpiCard
                    title={eu.coveragePct}
                    value={`${reservationCoverageQuery.data.coverage_pct}%`}
                    icon={<TrendingUp className="h-4 w-4" />}
                    compact
                    tone={
                      reservationCoverageQuery.data.coverage_pct >= 70
                        ? 'positive'
                        : reservationCoverageQuery.data.coverage_pct >= 40
                          ? 'warning'
                          : 'negative'
                    }
                    footer={
                      <span>
                        {reservationCoverageQuery.data.has_active_reservations ? eu.reservationsDetected : eu.noReservationsDetected}. {ux.tooltipReservationCoverage}
                      </span>
                    }
                  />
                </div>

                <div className="flex items-start gap-3 rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3">
                  <TrendingUp className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-600" />
                  <p className="text-sm leading-relaxed text-blue-800">
                    {reservationCoverageQuery.data.recommendation}
                  </p>
                </div>

                {!!reservationCoverageQuery.data.services.length && (
                  <div className="overflow-hidden rounded-xl border border-slate-200">
                    <div className="border-b border-slate-100 bg-slate-50 px-4 py-3">
                      <p className="text-sm font-medium text-slate-800">Top uncovered services</p>
                      <p className="mt-1 text-xs text-slate-500">Use this table to identify which services are carrying the largest uncovered compute spend.</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-100 text-left">
                            <th className="pb-3 pr-4 pl-4 pt-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.serviceColumn}</th>
                            <th className="pb-3 pr-4 pt-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.computeSpendBasis}</th>
                            <th className="pb-3 pr-4 pt-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.reservedSpendBasis}</th>
                            <th className="pb-3 pr-4 pt-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.uncoveredSpendBasis}</th>
                            <th className="pb-3 pr-4 pt-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.coveragePct}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                          {reservationCoverageQuery.data.services.slice(0, 8).map((row) => (
                            <tr key={row.service} className="transition hover:bg-gray-50/50">
                              <td className="py-3 pr-4 pl-4 font-medium text-gray-900">{row.service}</td>
                              <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{formatMoney(row.compute_cost_usd)}</td>
                              <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{formatMoney(row.reserved_cost_usd)}</td>
                              <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{formatMoney(row.uncovered_cost_usd)}</td>
                              <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{row.coverage_pct}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </Panel>
      </section>

      <Panel>
        <PanelHeader
          title={eu.timeline.replace('{{days}}', String(days))}
          subtitle="Review day-by-day usage movement and compare outlier days against the current operating window."
        />
        <div className="mt-4">
          {trendQuery.isLoading ? (
            <SkeletonTable rows={7} columns={2} />
          ) : trendQuery.isError ? (
            <ErrorState
              title={eu.noData}
              description="Daily usage timeline data is temporarily unavailable for the selected window."
              onRetry={() => trendQuery.refetch()}
              retryLabel={t.common.reset}
              compact
            />
          ) : !(trendQuery.data ?? []).length ? (
            <EmptyState
              icon="lightbulb"
              title={eu.noData}
              description="No daily usage rows are available for the selected period."
              action={days !== 30 ? { label: eu.last30, onClick: () => setDays(30) } : undefined}
            />
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-200">
              <div className="border-b border-slate-100 bg-slate-50 px-4 py-3">
                <p className="text-sm font-medium text-slate-800">Daily usage ledger</p>
                <p className="mt-1 text-xs text-slate-500">Track daily usage cost for the current reporting window and use spikes to validate workload behavior or reservation coverage gaps.</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-left">
                      <th className="pb-3 pr-4 pl-4 pt-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.colDate}</th>
                      <th className="pb-3 pr-4 pt-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.colValue}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {trendQuery.data?.map((point) => (
                      <tr key={point.date} className="transition hover:bg-gray-50/50">
                        <td className="py-2.5 pr-4 pl-4 text-gray-700">{formatDateShort(point.date)}</td>
                        <td className="py-2.5 pr-4 text-right tabular-nums font-medium text-gray-900">{numberFmt.format(Math.round(point.cost_usd))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </Panel>
    </div>
  )
}
