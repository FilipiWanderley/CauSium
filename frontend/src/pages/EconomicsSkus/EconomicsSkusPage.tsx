import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Boxes } from 'lucide-react'
import { ledgerApi } from '../../api/ledger'
import type { ServiceBreakdown } from '../../types'

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

export function EconomicsSkusPage() {
  const [days, setDays] = useState(30)
  const [limit, setLimit] = useState(20)

  const { data: skus = [] as ServiceBreakdown[], isLoading } = useQuery({
    queryKey: ['economics-skus', days, limit],
    queryFn: () => ledgerApi.topServicesPaginated(days, 1, limit).then((r) => r.data.items),
  })

  const summary = useMemo(() => {
    const totalCost = skus.reduce((sum, item) => sum + item.cost_usd, 0)
    const top3Share = skus.slice(0, 3).reduce((sum, item) => sum + item.percentage, 0)
    const concentrationRisk = top3Share >= 65 ? 'high' : top3Share >= 45 ? 'medium' : 'low'
    return { totalCost, top3Share, concentrationRisk }
  }, [skus])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Economics SKUs</h1>
        <p className="mt-1 text-sm text-gray-500">
          Track spending concentration by SKU dimension to prioritize optimization efforts.
        </p>
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        SKU view is currently mapped from service-level billing dimension. Provider-native SKU ingestion will be
        connected in a follow-up increment.
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <label className="text-sm text-gray-600">
            Window
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            >
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
              <option value={90}>Last 90 days</option>
              <option value={180}>Last 180 days</option>
            </select>
          </label>

          <label className="text-sm text-gray-600">
            Top rows
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            >
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
              <option value={30}>Top 30</option>
              <option value={50}>Top 50</option>
            </select>
          </label>

          <div className="rounded-lg border border-gray-200 px-3 py-2">
            <div className="text-xs uppercase tracking-wide text-gray-500">Total Cost</div>
            <div className="mt-1 text-lg font-semibold text-gray-900">{currency.format(summary.totalCost)}</div>
          </div>

          <div className="rounded-lg border border-gray-200 px-3 py-2">
            <div className="text-xs uppercase tracking-wide text-gray-500">Top 3 Share</div>
            <div className="mt-1 flex items-center gap-2 text-lg font-semibold text-gray-900">
              {summary.top3Share.toFixed(1)}%
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  summary.concentrationRisk === 'high'
                    ? 'bg-red-100 text-red-700'
                    : summary.concentrationRisk === 'medium'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-green-100 text-green-700'
                }`}
              >
                {summary.concentrationRisk}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center gap-2">
          <Boxes className="h-4 w-4 text-gray-600" />
          <h2 className="text-sm font-semibold text-gray-900">SKU Breakdown</h2>
        </div>

        {isLoading ? (
          <div className="py-8 text-center text-sm text-gray-500">Loading SKU breakdown...</div>
        ) : !skus.length ? (
          <div className="py-8 text-center text-sm text-gray-500">No SKU data available for the selected window.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs font-medium text-gray-500">
                  <th className="pb-2 pr-3">#</th>
                  <th className="pb-2 pr-3">SKU</th>
                  <th className="pb-2 pr-3">Cost</th>
                  <th className="pb-2">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {skus.map((item, index) => (
                  <tr key={`${item.service}-${index}`}>
                    <td className="py-2 pr-3 text-gray-500">{index + 1}</td>
                    <td className="py-2 pr-3 font-medium text-gray-800">{item.service}</td>
                    <td className="py-2 pr-3 text-gray-700">{currency.format(item.cost_usd)}</td>
                    <td className="py-2 text-gray-700">{item.percentage.toFixed(1)}%</td>
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
