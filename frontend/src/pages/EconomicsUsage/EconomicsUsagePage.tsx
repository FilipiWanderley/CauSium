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

      <Panel>
        <PanelHeader
          title="Command bar"
          subtitle="Adjust the reporting window while keeping operational and financial usage diagnostics aligned."
        />
        <div className="mt-4">
          <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
            {eu.timeWindow}
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="mt-1.5 block w-full max-w-xs rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            >
              <option value={30}>{eu.last30}</option>
              <option value={60}>{eu.last60}</option>
              <option value={90}>{eu.last90}</option>
              <option value={180}>{eu.last180}</option>
            </select>
          </label>
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
            subtitle="Track reserved and uncovered compute cost using the tenant-aware billing currency."
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
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-100 text-left">
                          <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.serviceColumn}</th>
                          <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.computeSpendBasis}</th>
                          <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.reservedSpendBasis}</th>
                          <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.uncoveredSpendBasis}</th>
                          <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.coveragePct}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {reservationCoverageQuery.data.services.slice(0, 8).map((row) => (
                          <tr key={row.service} className="transition hover:bg-gray-50/50">
                            <td className="py-3 pr-4 font-medium text-gray-900">{row.service}</td>
                            <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{formatMoney(row.compute_cost_usd)}</td>
                            <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{formatMoney(row.reserved_cost_usd)}</td>
                            <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{formatMoney(row.uncovered_cost_usd)}</td>
                            <td className="py-3 text-right tabular-nums text-gray-700">{row.coverage_pct}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
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
          subtitle="Review daily usage movement for the selected reporting window."
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.colDate}</th>
                    <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{eu.colValue}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {trendQuery.data?.map((point) => (
                    <tr key={point.date} className="transition hover:bg-gray-50/50">
                      <td className="py-2.5 pr-4 text-gray-700">{formatDateShort(point.date)}</td>
                      <td className="py-2.5 text-right tabular-nums font-medium text-gray-900">{numberFmt.format(Math.round(point.cost_usd))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Panel>
    </div>
  )
}


