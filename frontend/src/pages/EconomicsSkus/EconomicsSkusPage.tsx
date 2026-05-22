import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Boxes, Info } from 'lucide-react'
import { ledgerApi } from '../../api/ledger'
import type { ServiceBreakdown } from '../../types'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { KpiCard } from '../../components/Cards/KpiCard'
import { PageHeader } from '../../components/Layout/PageHeader'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
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

  const [days, setDays] = useState(30)
  const [limit, setLimit] = useState(20)

  const dashboardQuery = useQuery({
    queryKey: ['economics-skus-dashboard'],
    queryFn: () => ledgerApi.dashboard().then((r) => r.data),
    staleTime: 30_000,
    retry: 2,
  })

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
  const displayCurrency = dashboardQuery.data?.currency ?? DEFAULT_DISPLAY_CURRENCY
  const formatMoney = (value: number) => formatCurrency(value, displayCurrency)

  return (
    <div className="page-container">
      <PageHeader
        title={es.title}
        subtitle={es.subtitle}
        meta={
          <>
            <span>Billing currency values</span>
            <span>Consolidated SKU concentration</span>
          </>
        }
      />

      <Panel compact className="border-amber-200 bg-amber-50/60 shadow-none">
        <div className="flex items-start gap-3">
          <Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
          <p className="text-sm leading-relaxed text-amber-800">{es.note}</p>
        </div>
      </Panel>

      <section className="section-group">
        <SectionIntro
          title={es.overviewTitle}
          subtitle={es.overviewSubtitle}
          freshness={ux.freshnessSnapshot}
          badges={[
            { label: 'Billing currency values', tone: 'billing' },
            { label: es.consolidated, tone: 'organization' },
          ]}
        />
        <Panel>
          <PanelHeader
            title="Command bar"
            subtitle="Adjust the reporting window and SKU depth without leaving the overview."
          />
          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[220px_220px_minmax(0,1fr)_minmax(0,1fr)]">
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

            <KpiCard
              title={es.totalCost}
              value={formatMoney(summary.totalCost)}
              icon={<Boxes className="h-4 w-4" />}
              compact
              footer={<span>Visible SKU cost for the current selection.</span>}
            />

            <KpiCard
              title={es.top3Share}
              value={`${summary.top3Share.toFixed(1)}%`}
              icon={<Info className="h-4 w-4" />}
              compact
              tone={
                summary.concentrationRisk === 'high'
                  ? 'negative'
                  : summary.concentrationRisk === 'medium'
                    ? 'warning'
                    : 'positive'
              }
              footer={
                <div className="flex items-center gap-2">
                  <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${riskColor}`}>
                    {summary.concentrationRisk}
                  </span>
                  <span className="text-slate-500">
                    {ux.tooltipConcentrationRisk}
                  </span>
                </div>
              }
            />
          </div>
        </Panel>
      </section>

      <Panel>
        <PanelHeader
          title={es.breakdown}
          subtitle="Review ranked SKU concentration and share of spend for the selected window."
          actions={<span className="text-xs text-slate-400">{skus.length} items</span>}
        />
        <div className="mt-4">
          {isLoading ? (
            <SkeletonTable rows={6} columns={4} />
          ) : isError ? (
            <ErrorState
              title={es.noData}
              description="SKU breakdown data is temporarily unavailable for the selected time window."
              onRetry={() => refetch()}
              retryLabel={t.common.reset}
              compact
            />
          ) : !skus.length ? (
            <EmptyState
              icon="lightbulb"
              title={es.noData}
              description="No SKU cost rows are available for the selected time window."
              action={days !== 30 ? { label: es.last30, onClick: () => setDays(30) } : undefined}
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
      </Panel>
    </div>
  )
}


