import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Boxes, Info } from 'lucide-react'
import { ledgerApi } from '../../api/ledger'
import type { ServiceBreakdown } from '../../types'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { ExplainTooltip } from '../../components/UX/ExplainTooltip'
import { SkeletonTable, SkeletonMetricCards } from '../../components/UX/Skeleton'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'

export function EconomicsSkusPage() {
  usePageTitle('Economics — SKUs')
  const { t } = useI18n()
  const es = t.economicsSkus
  const ux = t.ux
  const formatMoney = (value: number) => formatCurrency(value, DEFAULT_DISPLAY_CURRENCY)

  const [days, setDays] = useState(30)
  const [limit, setLimit] = useState(20)

  const { data: skus = [] as ServiceBreakdown[], isLoading, isError, refetch } = useQuery({
    queryKey: ['economics-skus', days, limit],
    queryFn: () => ledgerApi.topServicesPaginated(days, 1, limit).then((r) => r.data.items),
    staleTime: 30_000,
    retry: 2,
  })

  const summary = useMemo(() => {
    const totalCost = skus.reduce((sum, item) => sum + item.cost_usd, 0)
    const top3Share = skus.slice(0, 3).reduce((sum, item) => sum + item.percentage, 0)
    const concentrationRisk = top3Share >= 65 ? 'high' : top3Share >= 45 ? 'medium' : 'low'
    return { totalCost, top3Share, concentrationRisk }
  }, [skus])

  const riskColor =
    summary.concentrationRisk === 'high'
      ? 'bg-red-50 text-red-700 border-red-200'
      : summary.concentrationRisk === 'medium'
        ? 'bg-amber-50 text-amber-700 border-amber-200'
        : 'bg-emerald-50 text-emerald-700 border-emerald-200'

  return (
    <div className="space-y-8">
      {/* Page header */}
      <header>
        <h1 className="text-2xl font-semibold text-gray-900">{es.title}</h1>
        <p className="mt-1.5 text-sm leading-relaxed text-gray-500">{es.subtitle}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">
            {es.financialValuesBrl}
          </span>
          <span className="rounded-full bg-blue-50 px-2.5 py-1 font-medium text-blue-700">
            {es.consolidated}
          </span>
        </div>
      </header>

      {/* Advisory notice */}
      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
        <Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
        <p className="text-sm leading-relaxed text-amber-800">{es.note}</p>
      </div>

      {/* Controls + KPI strip */}
      <section>
        <SectionIntro
          title={es.overviewTitle}
          subtitle={es.overviewSubtitle}
          freshness={ux.freshnessSnapshot}
          badges={[
            { label: es.financialValuesBrl, tone: 'billing' },
            { label: es.consolidated, tone: 'organization' },
          ]}
        />
        <div className="mt-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            {/* Time window selector */}
            <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
              {es.window}
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              >
                <option value={30}>{es.last30}</option>
                <option value={60}>{es.last60}</option>
                <option value={90}>{es.last90}</option>
                <option value={180}>{es.last180}</option>
              </select>
            </label>

            {/* Row limit selector */}
            <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
              {es.topRows}
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              >
                <option value={10}>{es.top10}</option>
                <option value={20}>{es.top20}</option>
                <option value={30}>{es.top30}</option>
                <option value={50}>{es.top50}</option>
              </select>
            </label>

            {/* Total cost KPI */}
            <div className="flex flex-col justify-center rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 shadow-sm">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{es.totalCost}</div>
              <div className="mt-1 text-xl font-bold tabular-nums text-white">{formatMoney(summary.totalCost)}</div>
            </div>

            {/* Concentration risk KPI */}
            <div className="flex flex-col justify-center rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
              <div className="text-[11px] font-medium uppercase tracking-wider text-gray-500">
                {es.top3Share}
                <ExplainTooltip text={ux.tooltipConcentrationRisk} className="ml-1.5 align-middle" />
              </div>
              <div className="mt-1 flex items-center gap-2">
                <span className="text-xl font-bold tabular-nums text-gray-900">
                  {summary.top3Share.toFixed(1)}%
                </span>
                <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${riskColor}`}>
                  {summary.concentrationRisk}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SKU breakdown table */}
      <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center gap-2.5 border-b border-gray-100 px-5 py-4">
          <Boxes className="h-4 w-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-900">{es.breakdown}</h2>
          <span className="ml-auto text-xs text-gray-400">{skus.length} items</span>
        </div>

        <div className="p-5">
          {isLoading ? (
            <SkeletonTable rows={6} columns={4} />
          ) : isError ? (
            <ErrorState
              title={es.noData}
              description="Could not load SKU breakdown data."
              onRetry={() => refetch()}
              retryLabel={t.common.reset}
              compact
            />
          ) : !skus.length ? (
            <EmptyState
              icon="lightbulb"
              title={es.noData}
              description="No SKU cost data available for the selected time window."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{es.colRank}</th>
                    <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{es.colSku}</th>
                    <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{es.colCost}</th>
                    <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{es.colShare}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {skus.map((item, index) => (
                    <tr key={`${item.service}-${index}`} className="transition hover:bg-gray-50/50">
                      <td className="py-3 pr-4">
                        <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-gray-100 text-xs font-semibold text-gray-600">
                          {index + 1}
                        </span>
                      </td>
                      <td className="py-3 pr-4 font-medium text-gray-900">{item.service}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{formatMoney(item.cost_usd)}</td>
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-gray-100 sm:block">
                            <div
                              className="h-full rounded-full bg-brand-500"
                              style={{ width: `${Math.min(100, item.percentage)}%` }}
                            />
                          </div>
                          <span className="tabular-nums text-gray-700">{item.percentage.toFixed(1)}%</span>
                        </div>
                      </td>
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
