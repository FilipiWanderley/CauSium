import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, TrendingUp } from 'lucide-react'
import { ledgerApi } from '../../api/ledger'
import { useI18n } from '../../contexts/I18nContext'
import { usePersistentNumber } from '../../hooks/usePersistentBoolean'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { ExplainTooltip } from '../../components/UX/ExplainTooltip'
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'

const numberFmt = new Intl.NumberFormat('en-US')

export function EconomicsUsagePage() {
  const { t } = useI18n()
  const eu = t.economicsUsage
  const ux = t.ux

  const [days, setDays] = usePersistentNumber('sp.economicsUsage.days', 30, [30, 60, 90, 180])

  const trendQuery = useQuery({
    queryKey: ['economics-usage-trend', days],
    queryFn: () => ledgerApi.costTrend(days).then((r) => r.data),
  })

  const dashboardQuery = useQuery({
    queryKey: ['economics-usage-dashboard'],
    queryFn: () => ledgerApi.dashboard().then((r) => r.data),
  })

  const reservationCoverageQuery = useQuery({
    queryKey: ['economics-reservation-coverage', days],
    queryFn: () => ledgerApi.reservationCoverage(days).then((r) => r.data),
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

    return {
      dailyAvg: avg,
      peak,
      volatility,
    }
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{eu.title}</h1>
        <p className="mt-1 text-sm text-gray-500">{eu.subtitle}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
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
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <label className="text-sm text-gray-600">
          {eu.timeWindow}
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="mt-1 w-full max-w-xs rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          >
            <option value={30}>{eu.last30}</option>
            <option value={60}>{eu.last60}</option>
            <option value={90}>{eu.last90}</option>
            <option value={180}>{eu.last180}</option>
          </select>
        </label>
      </div>

      <div className="space-y-4">
        <SectionIntro
          title={eu.operationsTitle}
          subtitle={eu.operationsSubtitle}
          freshness={ux.freshnessRefreshes}
          badges={[
            { label: eu.operationalMetric, tone: 'operational' },
            { label: eu.organizationWide, tone: 'organization' },
          ]}
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <UsageCard
            title={eu.dailyAvg}
            value={numberFmt.format(Math.round(usageSignals.dailyAvg))}
            subtitle={eu.dailyAvgDesc}
            icon={<Activity className="h-4 w-4" />}
            emphasis="primary"
          />
          <UsageCard
            title={eu.peakDay}
            value={numberFmt.format(Math.round(usageSignals.peak))}
            subtitle={eu.peakDayDesc}
            icon={<TrendingUp className="h-4 w-4" />}
          />
          <UsageCard
            title={eu.volatility}
            value={numberFmt.format(Math.round(usageSignals.volatility))}
            subtitle={eu.volatilityDesc}
            icon={<Activity className="h-4 w-4" />}
            tooltip={ux.tooltipVolatility}
          />
          <UsageCard
            title={eu.efficiencyScore}
            value={`${efficiencyScore}`}
            subtitle={eu.efficiencyScoreDesc}
            icon={<TrendingUp className="h-4 w-4" />}
            tooltip={ux.tooltipEfficiencyScore}
          />
        </div>
      </div>

      <div className="space-y-4">
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
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">
            {eu.reservationCoverage}
          </h2>
          {reservationCoverageQuery.isLoading ? (
            <div className="py-8 text-center text-sm text-gray-500">{eu.reservationCoverageLoading}</div>
          ) : !reservationCoverageQuery.data ? (
            <div className="py-8 text-center text-sm text-gray-500">{eu.reservationCoverageEmpty}</div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                <UsageCard
                  title={eu.computeSpendBasis}
                  value={formatMoney(reservationCoverageQuery.data.total_compute_cost_usd)}
                  subtitle={eu.organizationWide}
                  icon={<Activity className="h-4 w-4" />}
                />
                <UsageCard
                  title={eu.reservedSpendBasis}
                  value={formatMoney(reservationCoverageQuery.data.total_reserved_cost_usd)}
                  subtitle={eu.organizationWide}
                  icon={<TrendingUp className="h-4 w-4" />}
                />
                <UsageCard
                  title={eu.uncoveredSpendBasis}
                  value={formatMoney(reservationCoverageQuery.data.uncovered_compute_cost_usd)}
                  subtitle={eu.organizationWide}
                  icon={<Activity className="h-4 w-4" />}
                />
                <UsageCard
                  title={eu.coveragePct}
                  value={`${reservationCoverageQuery.data.coverage_pct}%`}
                  subtitle={reservationCoverageQuery.data.has_active_reservations ? eu.reservationsDetected : eu.noReservationsDetected}
                  icon={<TrendingUp className="h-4 w-4" />}
                  tooltip={ux.tooltipReservationCoverage}
                />
              </div>

              <div className="rounded border border-blue-100 bg-blue-50 px-3 py-2 text-sm text-blue-800">
                {reservationCoverageQuery.data.recommendation}
              </div>

              {!!reservationCoverageQuery.data.services.length && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs font-medium text-gray-500">
                        <th className="pb-2 pr-3">{eu.serviceColumn}</th>
                        <th className="pb-2 pr-3">{eu.computeSpendBasis}</th>
                        <th className="pb-2 pr-3">{eu.reservedSpendBasis}</th>
                        <th className="pb-2 pr-3">{eu.uncoveredSpendBasis}</th>
                        <th className="pb-2">{eu.coveragePct}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {reservationCoverageQuery.data.services.slice(0, 8).map((row) => (
                        <tr key={row.service}>
                          <td className="py-2 pr-3 text-gray-700">{row.service}</td>
                          <td className="py-2 pr-3 text-gray-900">{formatMoney(row.compute_cost_usd)}</td>
                          <td className="py-2 pr-3 text-gray-900">{formatMoney(row.reserved_cost_usd)}</td>
                          <td className="py-2 pr-3 text-gray-900">{formatMoney(row.uncovered_cost_usd)}</td>
                          <td className="py-2 text-gray-900">{row.coverage_pct}%</td>
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

      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-900">
          {eu.timeline.replace('{{days}}', String(days))}
        </h2>
        {trendQuery.isLoading ? (
          <div className="py-8 text-center text-sm text-gray-500">{eu.loadingTimeline}</div>
        ) : !(trendQuery.data ?? []).length ? (
          <div className="py-8 text-center text-sm text-gray-500">{eu.noData}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs font-medium text-gray-500">
                  <th className="pb-2 pr-3">{eu.colDate}</th>
                  <th className="pb-2">{eu.colValue}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {trendQuery.data?.map((point) => (
                  <tr key={point.date}>
                    <td className="py-2 pr-3 text-gray-700">{new Date(point.date).toLocaleDateString()}</td>
                    <td className="py-2 text-gray-900">{numberFmt.format(Math.round(point.cost_usd))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function UsageCard({
  title,
  value,
  subtitle,
  icon,
  emphasis = 'default',
  tooltip,
}: {
  title: string
  value: string
  subtitle: string
  icon: React.ReactNode
  emphasis?: 'default' | 'primary'
  tooltip?: string
}) {
  return (
    <div className={`rounded-xl border p-4 shadow-sm ${emphasis === 'primary' ? 'border-slate-900 bg-slate-900 text-white' : 'border-gray-200 bg-white'}`}>
      <div className="flex items-center justify-between">
        <div className={`text-xs uppercase tracking-wide ${emphasis === 'primary' ? 'text-slate-300' : 'text-gray-500'}`}>
          {title}
          {tooltip && <ExplainTooltip text={tooltip} className="ml-1.5 align-middle" />}
        </div>
        <div className={emphasis === 'primary' ? 'text-slate-300' : 'text-gray-500'}>{icon}</div>
      </div>
      <div className={`mt-2 text-2xl font-semibold ${emphasis === 'primary' ? 'text-white' : 'text-gray-900'}`}>{value}</div>
      <div className={`mt-1 text-xs ${emphasis === 'primary' ? 'text-slate-300' : 'text-gray-500'}`}>{subtitle}</div>
    </div>
  )
}
