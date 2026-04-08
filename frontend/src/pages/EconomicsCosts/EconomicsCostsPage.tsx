import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Filter } from 'lucide-react'
import { ledgerApi } from '../../api/ledger'

const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

export function EconomicsCostsPage() {
  const [days, setDays] = useState(30)
  const [serviceQuery, setServiceQuery] = useState('')

  const servicesQuery = useQuery({
    queryKey: ['economics-costs-services', days],
    queryFn: () => ledgerApi.topServicesWithLimit(days, 50).then((r) => r.data),
  })

  const teamsQuery = useQuery({
    queryKey: ['economics-costs-teams', days],
    queryFn: () => ledgerApi.topTeamsWithLimit(days, 50).then((r) => r.data),
  })

  const filteredServices = useMemo(() => {
    const q = serviceQuery.trim().toLowerCase()
    if (!q) return servicesQuery.data ?? []
    return (servicesQuery.data ?? []).filter((item) => item.service.toLowerCase().includes(q))
  }, [serviceQuery, servicesQuery.data])

  const totalFilteredCost = filteredServices.reduce((sum, item) => sum + item.cost_usd, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Economics Costs</h1>
        <p className="mt-1 text-sm text-gray-500">
          Explore detailed cost distribution by service and team using interactive filters.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <label className="text-sm text-gray-600">
            Time window
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
            Service filter
            <input
              type="text"
              value={serviceQuery}
              onChange={(e) => setServiceQuery(e.target.value)}
              placeholder="Filter service name"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
          </label>

          <div className="rounded-lg border border-gray-200 px-3 py-2">
            <div className="text-xs uppercase tracking-wide text-gray-500">Visible Cost</div>
            <div className="mt-1 text-xl font-semibold text-gray-900">{money.format(totalFilteredCost)}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-600" />
            <h2 className="text-sm font-semibold text-gray-900">Cost by Service</h2>
          </div>
          {servicesQuery.isLoading ? (
            <div className="py-8 text-center text-sm text-gray-500">Loading services...</div>
          ) : !filteredServices.length ? (
            <div className="py-8 text-center text-sm text-gray-500">No service data for current filter.</div>
          ) : (
            <BreakdownTable rows={filteredServices} label="Service" />
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">Cost by Team</h2>
          {teamsQuery.isLoading ? (
            <div className="py-8 text-center text-sm text-gray-500">Loading teams...</div>
          ) : !(teamsQuery.data ?? []).length ? (
            <div className="py-8 text-center text-sm text-gray-500">No team data available.</div>
          ) : (
            <BreakdownTable rows={teamsQuery.data ?? []} label="Team" />
          )}
        </div>
      </div>
    </div>
  )
}

function BreakdownTable({ rows, label }: { rows: Array<{ service: string; cost_usd: number; percentage: number }>; label: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs font-medium text-gray-500">
            <th className="pb-2 pr-3">{label}</th>
            <th className="pb-2 pr-3">Cost</th>
            <th className="pb-2">Share</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row) => (
            <tr key={`${label}-${row.service}`}>
              <td className="py-2 pr-3 font-medium text-gray-800">{row.service}</td>
              <td className="py-2 pr-3 text-gray-700">{money.format(row.cost_usd)}</td>
              <td className="py-2 text-gray-700">{row.percentage.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
