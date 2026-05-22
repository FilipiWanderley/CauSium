import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { FileSpreadsheet, FileText } from 'lucide-react'
import { economicsApi } from '../../api/economics'
import { ledgerApi } from '../../api/ledger'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { usePersistentNumber } from '../../hooks/usePersistentBoolean'
import { KpiCard } from '../../components/Cards/KpiCard'
import { PageHeader } from '../../components/Layout/PageHeader'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { SkeletonMetricCards, SkeletonPrioritizedList, SkeletonTable } from '../../components/UX/Skeleton'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'

export function EconomicsReportsPage() {
  usePageTitle('Economics — Reports')
  const { t } = useI18n()
  const er = t.economicsReports
  const ux = t.ux

  const [days, setDays] = usePersistentNumber('sp.economicsReports.days', 30, [30, 60, 90])
  const [exportJobId, setExportJobId] = useState<string | null>(null)
  const [downloadedJobId, setDownloadedJobId] = useState<string | null>(null)

  const dashboardQuery = useQuery({
    queryKey: ['economics-reports-dashboard'],
    queryFn: () => ledgerApi.dashboard().then((r) => r.data),
    staleTime: 30_000,
    retry: 2,
  })

  const servicesQuery = useQuery({
    queryKey: ['economics-reports-services', days],
    queryFn: () => ledgerApi.topServicesPaginated(days, 1, 15).then((r) => r.data.items),
    staleTime: 30_000,
    retry: 2,
  })

  const teamsQuery = useQuery({
    queryKey: ['economics-reports-teams', days],
    queryFn: () => ledgerApi.topTeamsPaginated(days, 1, 15).then((r) => r.data.items),
    staleTime: 30_000,
    retry: 2,
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
  const isError = dashboardQuery.isError || servicesQuery.isError || teamsQuery.isError
  const exportStatus = exportJobQuery.data?.status
  const isExporting = createExportMutation.isPending || exportStatus === 'queued' || exportStatus === 'running'
  const displayCurrency = dashboardQuery.data?.currency ?? DEFAULT_DISPLAY_CURRENCY
  const formatMoney = (value: number) => formatCurrency(value, displayCurrency)

  function handleExport(fileFormat: 'csv' | 'xlsx') {
    createExportMutation.mutate(fileFormat)
  }

  function renderExportStatus() {
    if (createExportMutation.isError) {
      return <span className="text-red-600">{er.errorEnqueue}</span>
    }
    if (!exportJobQuery.data) {
      return <span className="text-gray-400">{er.asyncNote}</span>
    }
    if (exportJobQuery.data.status === 'queued') {
      return <span className="animate-pulse text-amber-600">{er.queued}</span>
    }
    if (exportJobQuery.data.status === 'running') {
      return <span className="animate-pulse text-blue-600">{er.running}</span>
    }
    if (exportJobQuery.data.status === 'completed') {
      return <span className="text-emerald-600">{downloadedJobId === exportJobId ? er.completedDownload : er.completed}</span>
    }
    return <span className="text-red-600">{exportJobQuery.data.error_message || 'Export failed.'}</span>
  }

  const momPct = dashboardQuery.data?.mom_change_pct ?? 0

  return (
    <div className="page-container">
      <PageHeader
        title={er.title}
        subtitle={er.subtitle}
        meta={
          <>
            <span>Billing currency values</span>
            <span>Consolidated reporting view</span>
          </>
        }
      />

      <Panel>
        <PanelHeader
          title="Export & reporting window"
          subtitle="Adjust the reporting window and trigger summary exports from the same command surface."
        />
        <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
            {er.reportWindow}
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500 md:w-48"
            >
              <option value={30}>{er.last30}</option>
              <option value={60}>{er.last60}</option>
              <option value={90}>{er.last90}</option>
            </select>
          </label>

          <div className="flex flex-col gap-2 md:items-end">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleExport('csv')}
                disabled={isLoading || isExporting}
                className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
              >
                <FileText className="h-4 w-4" />
                {isExporting ? er.processing : er.exportCsv}
              </button>
              <button
                onClick={() => handleExport('xlsx')}
                disabled={isLoading || isExporting}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm transition hover:border-gray-400 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
              >
                <FileSpreadsheet className="h-4 w-4" />
                {isExporting ? er.processing : er.exportExcel}
              </button>
            </div>
            <div className="text-right text-xs">{renderExportStatus()}</div>
          </div>
        </div>
      </Panel>

      <section className="section-group">
        <SectionIntro
          title={er.overviewTitle}
          subtitle={er.overviewSubtitle}
          freshness={ux.freshnessSnapshot}
          badges={[
            { label: 'Billing currency values', tone: 'billing' },
            { label: er.consolidated, tone: 'organization' },
          ]}
        />
        <div className="mt-4">
          {isLoading ? (
            <SkeletonMetricCards count={3} />
          ) : isError ? (
            <ErrorState
              title={er.noData}
              description="Could not load report data."
              onRetry={() => { dashboardQuery.refetch(); servicesQuery.refetch(); teamsQuery.refetch() }}
              retryLabel={t.common.reset}
              compact
            />
          ) : (
            <div className="kpi-grid">
              <KpiCard
                title={er.currentMonth}
                value={formatMoney(dashboardQuery.data?.current_month_cost ?? 0)}
                compact
                tone="neutral"
                footer={<span>Current billing window summary.</span>}
              />
              <KpiCard
                title={er.previousMonth}
                value={formatMoney(dashboardQuery.data?.previous_month_cost ?? 0)}
                compact
                footer={<span>Prior billing window summary.</span>}
              />
              <KpiCard
                title={er.momChange}
                value={`${momPct > 0 ? '+' : ''}${momPct.toFixed(1)}%`}
                compact
                tone={momPct > 0 ? 'negative' : momPct < 0 ? 'positive' : 'neutral'}
                footer={
                  <span>
                    {momPct > 0 ? 'Cost increase' : momPct < 0 ? 'Cost reduction' : 'No change'}
                  </span>
                }
              />
            </div>
          )}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <BreakdownCard
          title={er.topServices}
          rows={servicesQuery.data ?? []}
          loading={servicesQuery.isLoading}
          noDataLabel={er.noData}
          currency={displayCurrency}
        />
        <BreakdownCard
          title={er.topTeams}
          rows={teamsQuery.data ?? []}
          loading={teamsQuery.isLoading}
          noDataLabel={er.noData}
          currency={displayCurrency}
        />
      </div>
    </div>
  )
}

// ─── Breakdown Card ───────────────────────────────────────────────────────────

function BreakdownCard({
  title,
  rows,
  loading,
  noDataLabel,
  currency,
}: {
  title: string
  rows: Array<{ service: string; cost_usd: number; percentage: number }>
  loading: boolean
  noDataLabel: string
  currency: string
}) {
  const formatMoney = (value: number) => formatCurrency(value, currency)

  return (
    <Panel>
      <PanelHeader
        title={title}
        subtitle="Prioritized contribution to the reporting window."
      />
      <div className="mt-4">
        {loading ? (
          <SkeletonPrioritizedList items={5} />
        ) : !rows.length ? (
          <EmptyState
            icon="document"
            title={noDataLabel}
            description="No report rows are available for the selected reporting window."
          />
        ) : (
          <div className="space-y-2.5">
            {rows.map((row) => (
              <div key={`${title}-${row.service}`} className="rounded-lg border border-gray-100 px-4 py-3 transition hover:border-gray-200 hover:bg-gray-50/50">
                <div className="flex items-center justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-gray-900">{row.service}</div>
                    <div className="mt-0.5 text-xs tabular-nums text-gray-500">{formatMoney(row.cost_usd)}</div>
                  </div>
                  <div className="ml-3 text-sm font-semibold tabular-nums text-gray-700">{row.percentage.toFixed(1)}%</div>
                </div>
                <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                  <div
                    className="h-full rounded-full bg-brand-500 transition-all"
                    style={{ width: `${Math.max(0, Math.min(100, row.percentage))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Panel>
  )
}


