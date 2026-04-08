import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { ledgerApi } from '../../api/ledger'

const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

function escapeCsv(value: string | number) {
  const normalized = String(value ?? '')
  if (normalized.includes(',') || normalized.includes('"') || normalized.includes('\n')) {
    return `"${normalized.split('"').join('""')}"`
  }
  return normalized
}

export function EconomicsReportsPage() {
  const [days, setDays] = useState(30)
  const [isExporting, setIsExporting] = useState(false)

  const dashboardQuery = useQuery({
    queryKey: ['economics-reports-dashboard'],
    queryFn: () => ledgerApi.dashboard().then((r) => r.data),
  })

  const servicesQuery = useQuery({
    queryKey: ['economics-reports-services', days],
    queryFn: () => ledgerApi.topServicesWithLimit(days, 15).then((r) => r.data),
  })

  const teamsQuery = useQuery({
    queryKey: ['economics-reports-teams', days],
    queryFn: () => ledgerApi.topTeamsWithLimit(days, 15).then((r) => r.data),
  })

  const csvContent = useMemo(() => {
    if (!dashboardQuery.data) return ''

    const lines: string[] = []
    lines.push('section,key,value')
    lines.push(`summary,current_month_cost,${escapeCsv(dashboardQuery.data.current_month_cost)}`)
    lines.push(`summary,previous_month_cost,${escapeCsv(dashboardQuery.data.previous_month_cost)}`)
    lines.push(`summary,mom_change_pct,${escapeCsv(dashboardQuery.data.mom_change_pct)}`)
    lines.push(`summary,event_count_7d,${escapeCsv(dashboardQuery.data.event_count_7d)}`)
    lines.push(`summary,active_accounts,${escapeCsv(dashboardQuery.data.active_accounts)}`)

    servicesQuery.data?.forEach((item, index) => {
      lines.push(`top_services_${index + 1},service,${escapeCsv(item.service)}`)
      lines.push(`top_services_${index + 1},cost_usd,${escapeCsv(item.cost_usd)}`)
      lines.push(`top_services_${index + 1},percentage,${escapeCsv(item.percentage)}`)
    })

    teamsQuery.data?.forEach((item, index) => {
      lines.push(`top_teams_${index + 1},team,${escapeCsv(item.service)}`)
      lines.push(`top_teams_${index + 1},cost_usd,${escapeCsv(item.cost_usd)}`)
      lines.push(`top_teams_${index + 1},percentage,${escapeCsv(item.percentage)}`)
    })

    return lines.join('\n')
  }, [dashboardQuery.data, servicesQuery.data, teamsQuery.data])

  const handleExport = async () => {
    if (!csvContent) return
    setIsExporting(true)
    try {
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `economics-report-${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } finally {
      setIsExporting(false)
    }
  }

  const isLoading = dashboardQuery.isLoading || servicesQuery.isLoading || teamsQuery.isLoading

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Economics Reports</h1>
        <p className="mt-1 text-sm text-gray-500">
          Generate operational snapshots from key financial indicators and export them as CSV.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <label className="text-sm text-gray-600">
            Report window
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            >
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </label>

          <button
            onClick={handleExport}
            disabled={!csvContent || isLoading || isExporting}
            className="inline-flex items-center gap-2 rounded bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <Download className="h-4 w-4" />
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricCard title="Current Month" value={money.format(dashboardQuery.data?.current_month_cost ?? 0)} />
        <MetricCard title="Previous Month" value={money.format(dashboardQuery.data?.previous_month_cost ?? 0)} />
        <MetricCard title="MoM Change" value={`${(dashboardQuery.data?.mom_change_pct ?? 0).toFixed(1)}%`} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <BreakdownCard title="Top Services" rows={servicesQuery.data ?? []} loading={servicesQuery.isLoading} />
        <BreakdownCard title="Top Teams" rows={teamsQuery.data ?? []} loading={teamsQuery.isLoading} />
      </div>
    </div>
  )
}

function MetricCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="text-xs uppercase tracking-wide text-gray-500">{title}</div>
      <div className="mt-1 text-xl font-semibold text-gray-900">{value}</div>
    </div>
  )
}

function BreakdownCard({
  title,
  rows,
  loading,
}: {
  title: string
  rows: Array<{ service: string; cost_usd: number; percentage: number }>
  loading: boolean
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-gray-900">{title}</h2>
      {loading ? (
        <div className="py-8 text-center text-sm text-gray-500">Loading...</div>
      ) : !rows.length ? (
        <div className="py-8 text-center text-sm text-gray-500">No data available.</div>
      ) : (
        <div className="space-y-2">
          {rows.map((row) => (
            <div key={`${title}-${row.service}`} className="flex items-center justify-between rounded border border-gray-100 px-3 py-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-gray-800">{row.service}</div>
                <div className="text-xs text-gray-500">{money.format(row.cost_usd)}</div>
              </div>
              <div className="text-sm font-semibold text-gray-700">{row.percentage.toFixed(1)}%</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
