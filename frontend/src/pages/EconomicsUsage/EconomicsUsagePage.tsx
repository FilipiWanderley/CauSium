import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, TrendingUp } from 'lucide-react'
import { ledgerApi } from '../../api/ledger'

const numberFmt = new Intl.NumberFormat('en-US')

export function EconomicsUsagePage() {
  const [days, setDays] = useState(30)

  const trendQuery = useQuery({
    queryKey: ['economics-usage-trend', days],
    queryFn: () => ledgerApi.costTrend(days).then((r) => r.data),
  })

  const dashboardQuery = useQuery({
    queryKey: ['economics-usage-dashboard'],
    queryFn: () => ledgerApi.dashboard().then((r) => r.data),
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Economics Usage</h1>
        <p className="mt-1 text-sm text-gray-500">
          Monitor usage behavior, identify volatility and track efficiency stability over time.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <label className="text-sm text-gray-600">
          Time window
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="mt-1 w-full max-w-xs rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          >
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 60 days</option>
            <option value={90}>Last 90 days</option>
            <option value={180}>Last 180 days</option>
          </select>
        </label>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <UsageCard
          title="Daily Average"
          value={numberFmt.format(Math.round(usageSignals.dailyAvg))}
          subtitle="Cost units / day"
          icon={<Activity className="h-4 w-4" />}
        />
        <UsageCard
          title="Peak Day"
          value={numberFmt.format(Math.round(usageSignals.peak))}
          subtitle="Highest observed day"
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <UsageCard
          title="Volatility"
          value={numberFmt.format(Math.round(usageSignals.volatility))}
          subtitle="Standard deviation"
          icon={<Activity className="h-4 w-4" />}
        />
        <UsageCard
          title="Efficiency Score"
          value={`${efficiencyScore}`}
          subtitle="Stability and MoM impact"
          icon={<TrendingUp className="h-4 w-4" />}
        />
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-900">Usage Timeline ({days} days)</h2>
        {trendQuery.isLoading ? (
          <div className="py-8 text-center text-sm text-gray-500">Loading usage timeline...</div>
        ) : !(trendQuery.data ?? []).length ? (
          <div className="py-8 text-center text-sm text-gray-500">No usage data available for this period.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs font-medium text-gray-500">
                  <th className="pb-2 pr-3">Date</th>
                  <th className="pb-2">Usage Value</th>
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

function UsageCard({ title, value, subtitle, icon }: { title: string; value: string; subtitle: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wide text-gray-500">{title}</div>
        <div className="text-gray-500">{icon}</div>
      </div>
      <div className="mt-2 text-2xl font-semibold text-gray-900">{value}</div>
      <div className="mt-1 text-xs text-gray-500">{subtitle}</div>
    </div>
  )
}
