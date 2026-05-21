import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Download } from 'lucide-react'
import { ledgerApi, type ExportJob } from '../../api/ledger'
import type {
  PageResponse,
  ServiceBreakdown,
  DetailedCostRow,
  ReservationEfficiencyAction,
  ReservationEfficiencyByFamily,
  SubscriptionCostSummary,
} from '../../types'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { usePersistentBoolean, usePersistentNumber, usePersistentString } from '../../hooks/usePersistentBoolean'
import { KpiCard } from '../../components/Cards/KpiCard'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { PageHeader } from '../../components/Layout/PageHeader'
import { DataTable } from '../../components/Tables/DataTable'
import type { DataTableColumn } from '../../components/Tables/DataTable'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'
import clsx from 'clsx'

const DAYS_OPTIONS = [30, 60, 90, 180] as const

type ExportFormat = 'csv' | 'xlsx'
type ExportState =
  | { phase: 'idle' }
  | { phase: 'submitting' }
  | { phase: 'polling'; jobId: string; job: ExportJob }
  | { phase: 'ready'; job: ExportJob }
  | { phase: 'error'; message: string }

// ─── Main Component ──────────────────────────────────────────────────────────

export function EconomicsCostsPage() {
  const { t } = useI18n()
  usePageTitle('Economics — Costs')
  const ec = t.economicsCosts
  const ux = t.ux
  const currencyCode = DEFAULT_DISPLAY_CURRENCY
  const formatMoney = (value: number) => formatCurrency(value, currencyCode)

  const [days, setDays] = usePersistentNumber('sp.economicsCosts.days', 30, [...DAYS_OPTIONS])
  const [serviceQuery, setServiceQuery] = usePersistentString('sp.economicsCosts.filters.service', '')
  const [providerQuery, setProviderQuery] = usePersistentString('sp.economicsCosts.filters.provider', '')
  const [teamQuery, setTeamQuery] = usePersistentString('sp.economicsCosts.filters.team', '')
  const [subscriptionFilter, setSubscriptionFilter] = useState('')
  const [servicePage, setServicePage] = useState(1)
  const [teamPage, setTeamPage] = useState(1)
  const [page, setPage] = useState(1)
  const [criticalOnly, setCriticalOnly] = usePersistentBoolean('sp.reservations.criticalOnly', false)
  const [filtersExpanded, setFiltersExpanded] = useState(false)
  const [exportFormat, setExportFormat] = useState<ExportFormat>('csv')
  const [exportState, setExportState] = useState<ExportState>({ phase: 'idle' })
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearPoll = () => { if (pollRef.current) { clearTimeout(pollRef.current); pollRef.current = null } }
  useEffect(() => () => clearPoll(), [])

  const poll = useCallback(async (jobId: string) => {
    try {
      const resp = await ledgerApi.getExportJob(jobId)
      const job = resp.data
      if (job.status === 'completed') setExportState({ phase: 'ready', job })
      else if (job.status === 'failed') setExportState({ phase: 'error', message: job.error_message ?? 'Export failed.' })
      else { setExportState({ phase: 'polling', jobId, job }); pollRef.current = setTimeout(() => poll(jobId), 2500) }
    } catch { setExportState({ phase: 'error', message: 'Could not check export status.' }) }
  }, [])

  const handleExport = async () => {
    clearPoll(); setExportState({ phase: 'submitting' })
    try {
      const filters: Record<string, unknown> = {}
      if (serviceQuery) filters.service = serviceQuery
      if (providerQuery) filters.provider = providerQuery
      if (teamQuery) filters.owner_team = teamQuery
      const resp = await ledgerApi.createExportJob({ report_type: 'summary', file_format: exportFormat, window_days: days, filters: Object.keys(filters).length ? filters : undefined })
      const job = resp.data
      if (job.status === 'completed') setExportState({ phase: 'ready', job })
      else { setExportState({ phase: 'polling', jobId: job.id, job }); pollRef.current = setTimeout(() => poll(job.id), 2500) }
    } catch { setExportState({ phase: 'error', message: 'Could not start export.' }) }
  }

  // ─── Queries ─────────────────────────────────────────────────────────────────

  const subscriptionsQuery = useQuery<SubscriptionCostSummary>({
    queryKey: ['ledger', 'subscriptions', days],
    queryFn: () => ledgerApi.subscriptionCostSummary(days).then((r) => r.data),
    staleTime: 30_000, retry: 2,
  })
  const hasMultipleSubscriptions = (subscriptionsQuery.data?.subscription_count ?? 0) > 1
  const getSubName = (name: string | null | undefined, key: string | null | undefined) => {
    const n = name?.trim(); return n || (key ? `${key.slice(0, 8)}…` : ec.subscriptionNone)
  }
  const singleSubscriptionName = getSubName(subscriptionsQuery.data?.items[0]?.subscription_name, subscriptionsQuery.data?.items[0]?.subscription_id)

  const servicesQuery = useQuery<PageResponse<ServiceBreakdown>>({
    queryKey: ['economics-costs-services', days, servicePage],
    queryFn: () => ledgerApi.topServicesPaginated(days, servicePage, 20).then((r) => r.data),
    placeholderData: (prev) => prev, staleTime: 30_000, retry: 2,
  })
  const teamsQuery = useQuery<PageResponse<ServiceBreakdown>>({
    queryKey: ['economics-costs-teams', days, teamPage],
    queryFn: () => ledgerApi.topTeamsPaginated(days, teamPage, 20).then((r) => r.data),
    placeholderData: (prev) => prev, staleTime: 30_000, retry: 2,
  })
  const detailedCostsQuery = useQuery<PageResponse<DetailedCostRow>>({
    queryKey: ['economics-costs-detailed', days, serviceQuery, providerQuery, teamQuery, subscriptionFilter, page],
    queryFn: () => ledgerApi.detailedCosts({ days, service: serviceQuery || undefined, provider: providerQuery || undefined, owner_team: teamQuery || undefined, subscription_id: subscriptionFilter || undefined, page, page_size: 20 }).then((r) => r.data),
    staleTime: 30_000, retry: 2,
  })
  const reservationQuery = useQuery({
    queryKey: ['economics-reservation-efficiency', days],
    queryFn: () => ledgerApi.reservationEfficiency(days).then((r) => r.data),
    staleTime: 30_000, retry: 2,
  })

  // ─── Derived ─────────────────────────────────────────────────────────────────

  const serviceItems = servicesQuery.data?.items ?? []
  const filteredServices = serviceQuery ? serviceItems.filter((i) => i.service.toLowerCase().includes(serviceQuery.trim().toLowerCase())) : serviceItems
  const totalFilteredCost = filteredServices.reduce((s, i) => s + i.cost_usd, 0)
  const prioritizedFamilies = [...(reservationQuery.data?.families ?? [])].sort((a, b) => b.action_priority - a.action_priority || b.waste_cost_usd - a.waste_cost_usd)
  const highPriorityCount = prioritizedFamilies.filter((i) => i.action_priority >= 4).length
  const visibleFamilies = criticalOnly ? prioritizedFamilies.filter((i) => i.action_priority >= 4) : prioritizedFamilies
  const hasTextFilters = Boolean(serviceQuery || providerQuery || teamQuery || subscriptionFilter)
  const clearTextFilters = () => { setServiceQuery(''); setProviderQuery(''); setTeamQuery(''); setSubscriptionFilter(''); setServicePage(1); setTeamPage(1); setPage(1) }
  const exportBusy = exportState.phase === 'submitting' || exportState.phase === 'polling'

  const actionLabel: Record<ReservationEfficiencyAction, string> = { keep: ec.actionKeep, resize_resource: ec.actionResize, schedule_stop: ec.actionScheduleStop, exchange_reservation: ec.actionExchange, do_not_renew: ec.actionDoNotRenew }

  // ─── DataTable columns for detailed costs ────────────────────────────────────

  const detailedColumns: DataTableColumn<DetailedCostRow>[] = [
    { key: 'date', header: ec.colDate, render: (r) => <span className="text-slate-600 tabular-nums">{r.date}</span>, sortFn: (a, b) => a.date.localeCompare(b.date) },
    { key: 'provider', header: ec.colProvider, hideBelow: 'md', render: (r) => <span className="text-slate-600">{r.provider}</span> },
    { key: 'service', header: ec.colService, render: (r) => <span className="font-medium text-slate-800">{r.service ?? '-'}</span> },
    { key: 'resource', header: ec.colResource, hideBelow: 'lg', render: (r) => <span className="text-slate-700">{r.resource_name ?? '-'}</span> },
    { key: 'team', header: ec.colTeam, hideBelow: 'lg', render: (r) => <span className="text-slate-600">{r.owner_team ?? '-'}</span> },
    { key: 'region', header: ec.colRegion, hideBelow: 'xl', render: (r) => <span className="text-slate-500">{r.region ?? '-'}</span> },
    { key: 'cost', header: ec.colCost, align: 'right', sortFn: (a, b) => a.cost_usd - b.cost_usd, render: (r) => <span className="font-semibold tabular-nums text-slate-800">{formatMoney(r.cost_usd)}</span> },
  ]

  // ─── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="page-container">
      {/* ═══ A. Page Header ═══ */}
      <PageHeader
        title={ec.title}
        subtitle={ec.subtitle}
        actions={
          <div className="flex items-center gap-2">
            <select value={days} onChange={(e) => setDays(Number(e.target.value))}
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:border-brand-500 focus:outline-none">
              <option value={30}>{ec.last30}</option>
              <option value={60}>{ec.last60}</option>
              <option value={90}>{ec.last90}</option>
              <option value={180}>{ec.last180}</option>
            </select>
            <select value={hasMultipleSubscriptions ? subscriptionFilter : ''} onChange={(e) => { setSubscriptionFilter(e.target.value); setPage(1) }}
              disabled={!hasMultipleSubscriptions || subscriptionsQuery.isLoading || subscriptionsQuery.isError}
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:border-brand-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400">
              {subscriptionsQuery.isLoading ? <option value="">{ec.subscriptionLoading}</option>
                : subscriptionsQuery.isError ? <option value="">{ec.subscriptionUnavailable}</option>
                : hasMultipleSubscriptions ? (<><option value="">{ec.allSubscriptionsCount.replace('{{count}}', String(subscriptionsQuery.data?.subscription_count ?? 0))}</option>{subscriptionsQuery.data?.items.map((s) => <option key={s.subscription_id} value={s.subscription_id}>{s.subscription_name || `${s.subscription_id.slice(0, 8)}…`}</option>)}</>)
                : <option value="">{singleSubscriptionName}</option>}
            </select>
            <div className="hidden sm:block h-5 w-px bg-slate-200" />
            {/* Export */}
            <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value as ExportFormat)} disabled={exportBusy}
              className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 focus:outline-none disabled:opacity-50">
              <option value="csv">{ec.csv}</option>
              <option value="xlsx">{ec.excel}</option>
            </select>
            <button type="button" onClick={handleExport} disabled={exportBusy}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50">
              {exportBusy ? <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" /> : <Download className="h-3 w-3" />}
              {exportState.phase === 'submitting' ? ec.requesting : exportState.phase === 'polling' ? ec.generating : t.common.export}
            </button>
          </div>
        }
        meta={
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {exportState.phase === 'ready' && (
              <a href={ledgerApi.downloadExportUrl(exportState.job.id)} download={exportState.job.file_name ?? `report.${exportFormat}`}
                className="text-xs font-medium text-brand-600 hover:underline">
                <Download className="inline h-3 w-3 mr-0.5" />{ec.downloadFile.replace('{{filename}}', exportState.job.file_name ?? `report.${exportFormat}`)}
              </a>
            )}
            {exportState.phase === 'error' && <span className="text-xs text-rose-600">{exportState.message}</span>}
            {exportState.phase !== 'idle' && exportState.phase !== 'submitting' && (
              <button type="button" onClick={() => { clearPoll(); setExportState({ phase: 'idle' }) }} className="text-[10px] text-slate-400 hover:text-slate-600 underline">{ec.reset}</button>
            )}
          </div>
        }
      />

      {/* ═══ B. KPI Row ═══ */}
      <div className="kpi-grid">
        <KpiCard
          title={ec.visibleCost}
          value={formatMoney(totalFilteredCost)}
          tone={hasTextFilters ? 'info' : 'neutral'}
          footer={<span>{hasTextFilters ? ec.filtered : ec.detailedCostsDesc}</span>}
        />
        <KpiCard
          title={ec.avgUtilization}
          value={reservationQuery.data ? `${reservationQuery.data.avg_utilization_pct.toFixed(1)}%` : '—'}
          tone={reservationQuery.data && reservationQuery.data.avg_utilization_pct < 60 ? 'warning' : 'neutral'}
          loading={reservationQuery.isLoading}
        />
        <KpiCard
          title={ec.totalWaste}
          value={formatMoney(reservationQuery.data?.total_waste_cost_usd ?? 0)}
          tone={(reservationQuery.data?.total_waste_cost_usd ?? 0) > 0 ? 'negative' : 'neutral'}
          loading={reservationQuery.isLoading}
        />
        <KpiCard
          title={ec.totalReserved}
          value={(reservationQuery.data?.total_reserved_capacity_units ?? 0).toLocaleString()}
          tone="neutral"
          loading={reservationQuery.isLoading}
          footer={<span>{ec.reservationEfficiency}</span>}
        />
      </div>

      {/* ═══ C. Filter Bar (progressive disclosure) ═══ */}
      <div className="rounded-panel border border-slate-200 bg-white px-3 py-2.5 shadow-panel">
        <div className="flex flex-wrap items-center gap-2.5">
          <button type="button" onClick={() => setFiltersExpanded((v) => !v)} className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-800">
            <ChevronRight className={clsx('h-3 w-3 transition-transform', filtersExpanded && 'rotate-90')} />
            {ec.serviceFilter}
          </button>
          {hasTextFilters && (
            <>
              <span className="h-3.5 w-px bg-slate-200" />
              <span className="text-[10px] text-slate-500">{ec.filtered}</span>
              <button type="button" onClick={clearTextFilters} className="text-[10px] text-brand-600 hover:underline">{t.common.reset}</button>
            </>
          )}
        </div>
        {filtersExpanded && (
          <div className="mt-2.5 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4 border-t border-slate-100 pt-2.5">
            <input type="text" value={serviceQuery} onChange={(e) => { setServiceQuery(e.target.value); setPage(1) }} placeholder={ec.serviceFilterPlaceholder}
              className="rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-xs text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none" />
            <input type="text" value={providerQuery} onChange={(e) => { setProviderQuery(e.target.value); setPage(1) }} placeholder={ec.providerFilterPlaceholder}
              className="rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-xs text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none" />
            <input type="text" value={teamQuery} onChange={(e) => { setTeamQuery(e.target.value); setPage(1) }} placeholder={ec.teamFilterPlaceholder}
              className="rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-xs text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none" />
            <button type="button" onClick={clearTextFilters} disabled={!hasTextFilters}
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40">{t.common.reset}</button>
          </div>
        )}
      </div>

      {/* ═══ D. Cost Decomposition ═══ */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* By Service */}
        <Panel compact>
          <PanelHeader title={ec.costByService} actions={
            <Paginator page={servicesQuery.data?.page ?? servicePage} total={Math.max(1, Math.ceil((servicesQuery.data?.total ?? 0) / (servicesQuery.data?.page_size ?? 20)))}
              hasNext={!!servicesQuery.data?.has_next} fetching={servicesQuery.isFetching}
              onPrev={() => setServicePage((p) => Math.max(1, p - 1))} onNext={() => setServicePage((p) => p + 1)} ec={ec} />
          } />
          {servicesQuery.isLoading ? (
            <div className="flex h-32 items-center justify-center"><div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" /></div>
          ) : !filteredServices.length ? (
            <EmptyState icon="search" title={ec.noServiceData} />
          ) : (
            <div className="mt-3 space-y-1.5">
              {filteredServices.map((row) => (
                <div key={row.service} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-slate-700 truncate">{row.service}</span>
                      <span className="text-xs font-semibold tabular-nums text-slate-600 shrink-0">{formatMoney(row.cost_usd)}</span>
                    </div>
                    <div className="mt-1 h-1 rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${row.percentage}%` }} />
                    </div>
                  </div>
                  <span className="text-[10px] tabular-nums text-slate-400 w-10 text-right shrink-0">{row.percentage.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}
        </Panel>

        {/* By Team */}
        <Panel compact>
          <PanelHeader title={ec.costByTeam} actions={
            <Paginator page={teamsQuery.data?.page ?? teamPage} total={Math.max(1, Math.ceil((teamsQuery.data?.total ?? 0) / (teamsQuery.data?.page_size ?? 20)))}
              hasNext={!!teamsQuery.data?.has_next} fetching={teamsQuery.isFetching}
              onPrev={() => setTeamPage((p) => Math.max(1, p - 1))} onNext={() => setTeamPage((p) => p + 1)} ec={ec} />
          } />
          {teamsQuery.isLoading ? (
            <div className="flex h-32 items-center justify-center"><div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" /></div>
          ) : !(teamsQuery.data?.items ?? []).length ? (
            <EmptyState icon="search" title={ec.noTeamData} />
          ) : (
            <div className="mt-3 space-y-1.5">
              {(teamsQuery.data?.items ?? []).map((row) => (
                <div key={row.service} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-slate-700 truncate">{row.service}</span>
                      <span className="text-xs font-semibold tabular-nums text-slate-600 shrink-0">{formatMoney(row.cost_usd)}</span>
                    </div>
                    <div className="mt-1 h-1 rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-cyan-500 transition-all" style={{ width: `${row.percentage}%` }} />
                    </div>
                  </div>
                  <span className="text-[10px] tabular-nums text-slate-400 w-10 text-right shrink-0">{row.percentage.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* ═══ E. Detailed Cost DataTable ═══ */}
      <Panel>
        <PanelHeader
          title={ec.detailedCosts}
          subtitle={ec.detailedCostsDesc}
          actions={<span className="text-[10px] text-slate-400">{ec.totalRows.replace('{{count}}', String(detailedCostsQuery.data?.total ?? 0))}</span>}
        />
        <div className="mt-4">
          {detailedCostsQuery.isLoading ? (
            <DataTable<DetailedCostRow> columns={detailedColumns} data={[]} getRowKey={(r) => `${r.date}-${r.provider}-loading`} loading loadingRows={8} />
          ) : detailedCostsQuery.isError ? (
            <ErrorState title={ec.noRows} onRetry={() => detailedCostsQuery.refetch()} retryLabel={t.common.reset} compact />
          ) : !(detailedCostsQuery.data?.items.length ?? 0) ? (
            <EmptyState icon="search" title={ec.noRows} />
          ) : (
            <>
              <DataTable<DetailedCostRow>
                columns={detailedColumns}
                data={detailedCostsQuery.data?.items ?? []}
                getRowKey={(r) => `${r.date}-${r.provider}-${r.resource_name ?? ''}-${r.cost_usd}`}
                density="compact"
                stickyHeader
                defaultSortKey="cost"
                defaultSortDir="desc"
              />
              <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                <span>{ec.pageOf.replace('{{page}}', String(detailedCostsQuery.data?.page ?? page)).replace('{{total}}', String(Math.max(1, Math.ceil((detailedCostsQuery.data?.total ?? 0) / (detailedCostsQuery.data?.page_size ?? 20)))))}</span>
                <div className="flex gap-1.5">
                  <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1 || detailedCostsQuery.isFetching}
                    className="rounded border border-slate-200 px-2.5 py-1 text-xs disabled:opacity-40">{ec.previous}</button>
                  <button onClick={() => { if (detailedCostsQuery.data?.has_next) setPage((p) => p + 1) }} disabled={!detailedCostsQuery.data?.has_next || detailedCostsQuery.isFetching}
                    className="rounded border border-slate-200 px-2.5 py-1 text-xs disabled:opacity-40">{ec.next}</button>
                </div>
              </div>
            </>
          )}
        </div>
      </Panel>

      {/* ═══ F. Reservation Efficiency (lower priority) ═══ */}
      {(reservationQuery.data?.families.length ?? 0) > 0 && (
        <Panel compact>
          <PanelHeader
            title={ec.reservationEfficiency}
            badge={highPriorityCount > 0 ? <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-semibold text-rose-700">{ec.reservationHighBadge.replace('{{count}}', String(highPriorityCount))}</span> : undefined}
            actions={
              <button type="button" className="text-[10px] text-brand-600 hover:underline" onClick={() => setCriticalOnly((v) => !v)}>
                {criticalOnly ? ec.reservationShowAll : ec.reservationCriticalOnly}
              </button>
            }
          />
          {reservationQuery.data?.recommendation && <p className="mt-2 text-xs text-slate-600">{reservationQuery.data.recommendation}</p>}
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  <th className="px-2 py-2">{ec.colFamily}</th>
                  <th className="px-2 py-2">{ec.colPriority}</th>
                  <th className="px-2 py-2 text-right">{ec.colUtilization}</th>
                  <th className="px-2 py-2 text-right">{ec.colWaste}</th>
                  <th className="px-2 py-2">{ec.colAction}</th>
                  <th className="hidden px-2 py-2 md:table-cell">{ec.colRenewal}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {visibleFamilies.map((row) => (
                  <tr key={row.family} className="hover:bg-slate-50/60">
                    <td className="px-2 py-2 font-medium text-slate-800">{row.family}</td>
                    <td className="px-2 py-2">
                      <span className={clsx('rounded-full px-1.5 py-0.5 text-[10px] font-medium', row.action_priority >= 4 ? 'bg-rose-50 text-rose-700' : row.action_priority >= 2 ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600')}>
                        P{row.action_priority}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-right tabular-nums text-slate-700">{row.utilization_pct.toFixed(1)}%</td>
                    <td className="px-2 py-2 text-right tabular-nums text-rose-600">{formatMoney(row.waste_cost_usd)}</td>
                    <td className="px-2 py-2">
                      <span className="rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">{actionLabel[row.recommended_action]}</span>
                    </td>
                    <td className="hidden px-2 py-2 text-slate-500 md:table-cell">{row.renewal_window_days != null ? `${row.renewal_window_days}d` : ec.noRenewalWindow}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* ═══ G. Billing Context (low-noise) ═══ */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-diagnostic px-1">
        <span>{ux.billingCurrency.replace('{{currency}}', currencyCode)}</span>
        <span>{ux.costBasisActualPreTax}</span>
        <span>{ec.billingContext}</span>
        {subscriptionsQuery.data && <span>{ec.allSubscriptionsCount.replace('{{count}}', String(subscriptionsQuery.data.subscription_count))}</span>}
      </div>
    </div>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function Paginator({ page, total, hasNext, fetching, onPrev, onNext, ec }: {
  page: number; total: number; hasNext: boolean; fetching: boolean
  onPrev: () => void; onNext: () => void; ec: { pageOf: string; previous: string; next: string }
}) {
  return (
    <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
      <span>{ec.pageOf.replace('{{page}}', String(page)).replace('{{total}}', String(total))}</span>
      <button onClick={onPrev} disabled={page <= 1 || fetching} className="rounded border border-slate-200 px-1.5 py-0.5 disabled:opacity-40">{ec.previous}</button>
      <button onClick={onNext} disabled={!hasNext || fetching} className="rounded border border-slate-200 px-1.5 py-0.5 disabled:opacity-40">{ec.next}</button>
    </div>
  )
}
