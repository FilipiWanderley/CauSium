import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { economicsApi } from '../../api/economics'
import { ledgerApi } from '../../api/ledger'

const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

export function EconomicsReportsPage() {
  const [days, setDays] = useState(30)
  const [exportJobId, setExportJobId] = useState<string | null>(null)
  const [downloadedJobId, setDownloadedJobId] = useState<string | null>(null)

  const dashboardQuery = useQuery({
    queryKey: ['economics-reports-dashboard'],
    queryFn: () => ledgerApi.dashboard().then((r) => r.data),
  })

  const servicesQuery = useQuery({
    queryKey: ['economics-reports-services', days],
    queryFn: () => ledgerApi.topServicesPaginated(days, 1, 15).then((r) => r.data.items),
  })

  const teamsQuery = useQuery({
    queryKey: ['economics-reports-teams', days],
    queryFn: () => ledgerApi.topTeamsPaginated(days, 1, 15).then((r) => r.data.items),
  })

  const exportJobQuery = useQuery({
    queryKey: ['economics-report-export', exportJobId],
    queryFn: () => economicsApi.getReportExport(exportJobId as string).then((r) => r.data),
    enabled: !!exportJobId,
    refetchInterval: (query) => {
      const exportStatus = query.state.data?.status
      return exportStatus === 'queued' || exportStatus === 'running' ? 2000 : false
    },
  })

  const createExportMutation = useMutation({
    mutationFn: (fileFormat: 'csv' | 'xlsx') =>
      economicsApi
        .createReportExport({
          report_type: 'summary',
          file_format: fileFormat,
          window_days: days,
        })
        .then((r) => r.data),
    onSuccess: (job) => {
      setExportJobId(job.id)
      setDownloadedJobId(null)
    },
  })

  useEffect(() => {
    const job = exportJobQuery.data
    if (!exportJobId || !job || job.status !== 'completed' || downloadedJobId === exportJobId) {
      return
    }
    const currentJobId: string = exportJobId
    const completedJob = job

    let cancelled = false

    async function downloadExport() {
      const response = await economicsApi.downloadReportExport(currentJobId)
      if (cancelled) return
      const blob = response.data
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download =
        completedJob.file_name ||
        `economics-report-${new Date().toISOString().slice(0, 10)}.${completedJob.file_format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      setDownloadedJobId(currentJobId)
    }

    void downloadExport()

    return () => {
      cancelled = true
    }
  }, [downloadedJobId, exportJobId, exportJobQuery.data])

  const isLoading = dashboardQuery.isLoading || servicesQuery.isLoading || teamsQuery.isLoading
  const exportStatus = exportJobQuery.data?.status
  const isExporting = createExportMutation.isPending || exportStatus === 'queued' || exportStatus === 'running'

  function handleExport(fileFormat: 'csv' | 'xlsx') {
    createExportMutation.mutate(fileFormat)
  }

  function renderExportStatus() {
    if (createExportMutation.isError) {
      return 'Failed to enqueue the export job.'
    }
    if (!exportJobQuery.data) {
      return 'Exports are generated asynchronously on the backend and downloaded when ready.'
    }
    if (exportJobQuery.data.status === 'queued') {
      return 'Export queued. Waiting for worker pickup.'
    }
    if (exportJobQuery.data.status === 'running') {
      return 'Export running. The download will start automatically.'
    }
    if (exportJobQuery.data.status === 'completed') {
      return downloadedJobId === exportJobId
        ? 'Export completed and downloaded.'
        : 'Export completed. Starting download.'
    }
    return exportJobQuery.data.error_message || 'Export failed.'
  }

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

          <div className="flex flex-col gap-2 md:items-end">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleExport('csv')}
                disabled={isLoading || isExporting}
                className="inline-flex items-center gap-2 rounded bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                <Download className="h-4 w-4" />
                {isExporting ? 'Processing...' : 'Export CSV'}
              </button>
              <button
                onClick={() => handleExport('xlsx')}
                disabled={isLoading || isExporting}
                className="inline-flex items-center gap-2 rounded border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:border-gray-400 disabled:opacity-60"
              >
                <Download className="h-4 w-4" />
                {isExporting ? 'Processing...' : 'Export Excel'}
              </button>
            </div>
            <div className="text-right text-xs text-gray-500">{renderExportStatus()}</div>
          </div>
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
