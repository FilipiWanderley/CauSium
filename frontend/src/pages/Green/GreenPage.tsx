import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Leaf, TrendingDown, TrendingUp } from 'lucide-react'
import {
  greenApi,
  type BreakdownDimension,
  type EmissionsBreakdownRow,
  type EmissionsMonthRow,
} from '../../api/green'

const fmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })
const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

function DeltaBadge({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-gray-400 text-xs">—</span>
  const up = pct > 0
  return (
    <span
      className={`flex items-center gap-0.5 text-xs font-medium ${
        up ? 'text-red-600' : 'text-emerald-600'
      }`}
    >
      {up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
      {up ? '+' : ''}
      {pct.toFixed(1)}%
    </span>
  )
}

const BREAKDOWN_LABELS: Record<BreakdownDimension, string> = {
  service: 'Service',
  region: 'Region',
  environment: 'Environment',
  owner_team: 'Team',
}

export function GreenPage() {
  const [months, setMonths] = useState(6)
  const [by, setBy] = useState<BreakdownDimension>('service')
  const [days, setDays] = useState(30)

  const summaryQ = useQuery({
    queryKey: ['green-summary', months],
    queryFn: () => greenApi.getSummary(months),
  })

  const emissionsQ = useQuery({
    queryKey: ['green-emissions', months],
    queryFn: () => greenApi.getEmissions(months),
  })

  const breakdownQ = useQuery({
    queryKey: ['green-breakdown', by, days],
    queryFn: () => greenApi.getBreakdown(by, days),
  })

  const s = summaryQ.data
  const trend = emissionsQ.data ?? []
  const breakdown = breakdownQ.data ?? []
  const maxKg = Math.max(...breakdown.map((r) => r.kg_co2e), 1)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Leaf className="h-6 w-6 text-emerald-500" />
            PulseGreen
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Estimated carbon footprint derived from cloud spend and regional grid intensity.
          </p>
        </div>

        <select
          value={months}
          onChange={(e) => setMonths(Number(e.target.value))}
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value={3}>Last 3 months</option>
          <option value={6}>Last 6 months</option>
          <option value={12}>Last 12 months</option>
        </select>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-emerald-600">
            Total CO₂e
          </p>
          <p className="mt-1 text-2xl font-bold text-emerald-800">
            {s ? `${fmt.format(s.total_kg_co2e)} kg` : '—'}
          </p>
          <p className="text-xs text-emerald-600">
            {s ? `${fmt.format(s.total_kg_co2e / 1000)} tCO₂e` : ''}
          </p>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Cloud Spend</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {s ? money.format(s.total_cost_usd) : '—'}
          </p>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Intensity (gCO₂e/$)
          </p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {s ? fmt.format(s.intensity_avg) : '—'}
          </p>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">MoM Delta</p>
          <div className="mt-1">
            {s ? (
              <DeltaBadge pct={s.mom_delta_pct} />
            ) : (
              <p className="text-2xl font-bold text-gray-900">—</p>
            )}
          </div>
        </div>
      </div>

      {/* Monthly trend table */}
      <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
        <div className="border-b border-gray-100 px-5 py-3">
          <h2 className="text-sm font-semibold text-gray-700">Monthly Emissions Trend</h2>
        </div>
        {emissionsQ.isPending ? (
          <div className="p-6 space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-gray-100" />
            ))}
          </div>
        ) : trend.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">
            No emissions data available for this period.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                {['Month', 'kgCO₂e', 'tCO₂e', 'Cloud Cost', 'MoM'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {[...(trend as EmissionsMonthRow[])].reverse().map((row, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{row.month}</td>
                  <td className="px-4 py-3 text-gray-700">{fmt.format(row.kg_co2e)}</td>
                  <td className="px-4 py-3 text-gray-500">{(row.kg_co2e / 1000).toFixed(3)}</td>
                  <td className="px-4 py-3 text-gray-700">{money.format(row.cost_usd)}</td>
                  <td className="px-4 py-3">
                    <DeltaBadge pct={row.delta_pct} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Breakdown */}
      <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-3">
          <h2 className="text-sm font-semibold text-gray-700">Emissions Breakdown</h2>
          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="rounded border border-gray-200 px-2 py-1 text-xs text-gray-600 focus:outline-none"
            >
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
            <select
              value={by}
              onChange={(e) => setBy(e.target.value as BreakdownDimension)}
              className="rounded border border-gray-200 px-2 py-1 text-xs text-gray-600 focus:outline-none"
            >
              {(Object.keys(BREAKDOWN_LABELS) as BreakdownDimension[]).map((k) => (
                <option key={k} value={k}>
                  By {BREAKDOWN_LABELS[k]}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="p-5">
          {breakdownQ.isPending ? (
            <div className="space-y-3">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-8 animate-pulse rounded bg-gray-100" />
              ))}
            </div>
          ) : breakdown.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">No breakdown data available.</p>
          ) : (
            <div className="space-y-3">
              {(breakdown as EmissionsBreakdownRow[]).map((row, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span
                      className="max-w-[200px] truncate font-medium text-gray-800"
                      title={row.dimension}
                    >
                      {row.dimension}
                    </span>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span>{fmt.format(row.kg_co2e)} kg</span>
                      <span className="font-semibold text-emerald-600">{row.share_pct}%</span>
                    </div>
                  </div>
                  <div className="h-2 w-full rounded-full bg-gray-100">
                    <div
                      className="h-2 rounded-full bg-emerald-400"
                      style={{ width: `${(row.kg_co2e / maxKg) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Data disclaimer */}
      {s?.note && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-700">
          <Leaf className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{s.note}</span>
        </div>
      )}
    </div>
  )
}
