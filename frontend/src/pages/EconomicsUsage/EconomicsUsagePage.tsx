import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, TrendingUp } from 'lucide-react'
import { ledgerApi } from '../../api/ledger'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { formatDateShort } from '../../utils/format'
import { usePersistentNumber } from '../../hooks/usePersistentBoolean'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { ExplainTooltip } from '../../components/UX/ExplainTooltip'
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
    <div className="space-y-8">
      {/* Page header */}
      <header>
        <h1 className="text-2xl font-semibold text-gray-900">{eu.title}</h1>
        <p className="mt-1.5 text-sm leading-relaxed text-gray-500">{eu.subtitle}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-blue-50 px-2.5 py-1 font-medium text-blue-700">
            {eu.operationalMetric}
          </span>
          <span className="rounded-full bg-gray-100 px-2.5 py-1 font-medium text-gray-700">
            {eu.organizationWide}
          </span>
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">
            {eu.financialValuesBrl}
          </span>
        </div>
      </header>

      {/* Time window control */}
      <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
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

      {/* Operational signals */}
      <section>
        <SectionIntro
          title={eu.operationsTitle}
          subtitle={eu.operationsSubtitle}
          freshness={ux.freshnessRefreshes}
          badges={[
            { label: eu.operationalMetric, tone: 'operational' },
            { label: eu.organizationWide, tone: 'organization' },
          ]}
        />
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-4">
          <KpiCard
            title={eu.dailyAvg}
            value={numberFmt.format(Math.round(usageSignals.dailyAvg))}
            subtitle={eu.dailyAvgDesc}
            icon={<Activity className="h-4 w-4" />}
            emphasis="primary"
          />
          <KpiCard
            title={eu.peakDay}
            value={numberFmt.format(Math.round(usageSignals.peak))}
            subtitle={eu.peakDayDesc}
            icon={<TrendingUp className="h-4 w-4" />}
          />
          <KpiCard
            title={eu.volatility}
            value={numberFmt.format(Math.round(usageSignals.volatility))}
            subtitle={eu.volatilityDesc}
            icon={<Activity className="h-4 w-4" />}
            tooltip={ux.tooltipVolatility}
          />
          <KpiCard
            title={eu.efficiencyScore}
            value={`${efficiencyScore}`}
            subtitle={eu.efficiencyScoreDesc}
            icon={<TrendingUp className="h-4 w-4" />}
            tooltip={ux.tooltipEfficiencyScore}
            valueColor={efficiencyScore >= 70 ? 'text-emerald-600' : efficiencyScore >= 40 ? 'text-amber-600' : 'text-red-600'}
          />
        </div>
      </section>

      {/* Reservation coverage */}
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
        <div className="mt-4 rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-5 py-4">
            <h2 className="text-sm font-semibold text-gray-900">{eu.reservationCoverage}</h2>
          </div>
          <div className="p-5">
            {reservationCoverageQuery.isLoading ? (
              <SkeletonMetricCards count={4} />
            ) : reservationCoverageQuery.isError ? (
              <ErrorState
                title={eu.reservationCoverageEmpty}
                onRetry={() => reservationCoverageQuery.refetch()}
                retryLabel={t.common.reset}
                compact
              />
            ) : !reservationCoverageQuery.data ? (
              <EmptyState icon="lightbulb" title={eu.reservationCoverageEmpty} />
            ) : (
              <div className="space-y-5">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                  <KpiCard
                    title={eu.computeSpendBasis}
                    value={formatMoney(reservationCoverageQuery.data.total_compute_cost_usd)}
                    subtitle={eu.organizationWide}
                    icon={<Activity className="h-4 w-4" />}
                  />
                  <KpiCard
                    title={eu.reservedSpendBasis}
                    value={formatMoney(reservationCoverageQuery.data.total_reserved_cost_usd)}
                    subtitle={eu.organizationWide}
                    icon={<TrendingUp className="h-4 w-4" />}
                  />
                  <KpiCard
                    title={eu.uncoveredSpendBasis}
                    value={formatMoney(reservationCoverageQuery.data.uncovered_compute_cost_usd)}
                    subtitle={eu.organizationWide}
                    icon={<Activity className="h-4 w-4" />}
                  />
                  <KpiCard
                    title={eu.coveragePct}
                    value={`${reservationCoverageQuery.data.coverage_pct}%`}
                    subtitle={reservationCoverageQuery.data.has_active_reservations ? eu.reservationsDetected : eu.noReservationsDetected}
                    icon={<TrendingUp className="h-4 w-4" />}
                    tooltip={ux.tooltipReservationCoverage}
                    valueColor={
                      reservationCoverageQuery.data.coverage_pct >= 70
                        ? 'text-emerald-600'
                        : reservationCoverageQuery.data.coverage_pct >= 40
                          ? 'text-amber-600'
                          : undefined
                    }
                  />
                </div>

                {/* Recommendation callout */}
                <div className="flex items-start gap-3 rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3">
                  <TrendingUp className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-600" />
                  <p className="text-sm leading-relaxed text-blue-800">
                    {reservationCoverageQuery.data.recommendation}
                  </p>
                </div>

                {/* Service breakdown table */}
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
        </div>
      </section>

      {/* Daily cost timeline */}
      <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-gray-900">
            {eu.timeline.replace('{{days}}', String(days))}
          </h2>
        </div>
        <div className="p-5">
          {trendQuery.isLoading ? (
            <SkeletonTable rows={7} columns={2} />
          ) : trendQuery.isError ? (
            <ErrorState
              title={eu.noData}
              onRetry={() => trendQuery.refetch()}
              retryLabel={t.common.reset}
              compact
            />
          ) : !(trendQuery.data ?? []).length ? (
            <EmptyState icon="lightbulb" title={eu.noData} />
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
      </section>
    </div>
  )
}

// ─── Shared KPI Card ─────────────────────────────────────────────────────────

function KpiCard({
  title,
  value,
  subtitle,
  icon,
  emphasis = 'default',
  tooltip,
  valueColor,
}: {
  title: string
  value: string
  subtitle: string
  icon: React.ReactNode
  emphasis?: 'default' | 'primary'
  tooltip?: string
  valueColor?: string
}) {
  const isPrimary = emphasis === 'primary'

  return (
    <div className={`rounded-xl border p-4 shadow-sm transition ${
      isPrimary ? 'border-slate-800 bg-slate-900' : 'border-gray-200 bg-white'
    }`}>
      <div className="flex items-center justify-between">
        <div className={`text-[11px] font-medium uppercase tracking-wider ${isPrimary ? 'text-slate-400' : 'text-gray-500'}`}>
          {title}
          {tooltip && <ExplainTooltip text={tooltip} className="ml-1.5 align-middle" />}
        </div>
        <div className={isPrimary ? 'text-slate-400' : 'text-gray-400'}>{icon}</div>
      </div>
      <div className={`mt-2 text-2xl font-bold tabular-nums ${
        isPrimary ? 'text-white' : valueColor ?? 'text-gray-900'
      }`}>
        {value}
      </div>
      <div className={`mt-1 text-xs leading-relaxed ${isPrimary ? 'text-slate-400' : 'text-gray-500'}`}>
        {subtitle}
      </div>
    </div>
  )
}
