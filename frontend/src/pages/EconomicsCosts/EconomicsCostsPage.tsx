import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Filter, Lightbulb, AlertTriangle, CalendarClock } from 'lucide-react'
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
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { FreshnessIndicator } from '../../components/UX/FreshnessIndicator'
import { ExplainTooltip } from '../../components/UX/ExplainTooltip'
import { SkeletonTable, SkeletonMetricCards } from '../../components/UX/Skeleton'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'

const DAYS_OPTIONS = [30, 60, 90, 180] as const

// ─── Export panel ────────────────────────────────────────────────────────────

type ExportFormat = 'csv' | 'xlsx'
type ExportState =
  | { phase: 'idle' }
  | { phase: 'submitting' }
  | { phase: 'polling'; jobId: string; job: ExportJob }
  | { phase: 'ready'; job: ExportJob }
  | { phase: 'error'; message: string }

function ExportPanel({ days, filters }: { days: number; filters: Record<string, string | undefined> }) {
  const { t } = useI18n()
  const ec = t.economicsCosts

  const [format, setFormat] = useState<ExportFormat>('csv')
  const [state, setState] = useState<ExportState>({ phase: 'idle' })
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearPoll = () => {
    if (pollRef.current) {
      clearTimeout(pollRef.current)
      pollRef.current = null
    }
  }

  const poll = useCallback(async (jobId: string) => {
    try {
      const resp = await ledgerApi.getExportJob(jobId)
      const job = resp.data
      if (job.status === 'completed') {
        setState({ phase: 'ready', job })
      } else if (job.status === 'failed') {
        setState({ phase: 'error', message: job.error_message ?? 'Export failed.' })
      } else {
        setState({ phase: 'polling', jobId, job })
        pollRef.current = setTimeout(() => poll(jobId), 2500)
      }
    } catch {
      setState({ phase: 'error', message: 'Could not check export status.' })
    }
  }, [])

  useEffect(() => () => clearPoll(), [])

  const handleExport = async () => {
    clearPoll()
    setState({ phase: 'submitting' })
    try {
      const activeFilters: Record<string, unknown> = {}
      if (filters.service) activeFilters.service = filters.service
      if (filters.provider) activeFilters.provider = filters.provider
      if (filters.owner_team) activeFilters.owner_team = filters.owner_team

      const resp = await ledgerApi.createExportJob({
        report_type: 'summary',
        file_format: format,
        window_days: days,
        filters: Object.keys(activeFilters).length ? activeFilters : undefined,
      })
      const job = resp.data
      if (job.status === 'completed') {
        setState({ phase: 'ready', job })
      } else {
        setState({ phase: 'polling', jobId: job.id, job })
        pollRef.current = setTimeout(() => poll(job.id), 2500)
      }
    } catch {
      setState({ phase: 'error', message: 'Could not start export.' })
    }
  }

  const busy = state.phase === 'submitting' || state.phase === 'polling'

  return (
    <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-3 md:flex-row md:items-end">
          <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
            {ec.format}
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as ExportFormat)}
              disabled={busy}
              className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500 disabled:opacity-50 md:w-48"
            >
              <option value="csv">{ec.csv}</option>
              <option value="xlsx">{ec.excel}</option>
            </select>
          </label>

          <button
            onClick={handleExport}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
          >
            <Download className="h-4 w-4" />
            {state.phase === 'submitting'
              ? ec.requesting
              : state.phase === 'polling'
                ? ec.generating
                : t.common.export}
          </button>
        </div>
        <div className="flex flex-col gap-2 md:items-end">
          {state.phase === 'polling' && (
            <span className="text-xs text-gray-500 animate-pulse">
              {ec.buildingFormat.replace('{{format}}', format.toUpperCase())}
            </span>
          )}

          {state.phase === 'ready' && (
            <a
              href={ledgerApi.downloadExportUrl(state.job.id)}
              download={state.job.file_name ?? `report.${format}`}
              className="inline-flex items-center gap-1.5 rounded-lg border border-brand-300 bg-brand-50 px-4 py-2.5 text-sm font-medium text-brand-700 hover:bg-brand-100"
            >
              <Download className="h-4 w-4" />
              {ec.downloadFile.replace('{{filename}}', state.job.file_name ?? `report.${format}`)}
            </a>
          )}

          {state.phase === 'error' && (
            <span className="text-xs text-red-600">{state.message}</span>
          )}

          {state.phase !== 'idle' && state.phase !== 'submitting' && (
            <button
              onClick={() => { clearPoll(); setState({ phase: 'idle' }) }}
              className="text-xs text-gray-400 hover:text-gray-600 underline"
            >
              {ec.reset}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function EconomicsCostsPage() {
  const { t } = useI18n()
  usePageTitle('Economics — Costs')
  const ec = t.economicsCosts
  const ux = t.ux
  const currencyCode = DEFAULT_DISPLAY_CURRENCY

  const [days, setDays] = usePersistentNumber('sp.economicsCosts.days', 30, [...DAYS_OPTIONS])
  const [serviceQuery, setServiceQuery] = usePersistentString('sp.economicsCosts.filters.service', '')
  const [providerQuery, setProviderQuery] = usePersistentString('sp.economicsCosts.filters.provider', '')
  const [teamQuery, setTeamQuery] = usePersistentString('sp.economicsCosts.filters.team', '')
  const [subscriptionFilter, setSubscriptionFilter] = useState('')
  const [servicePage, setServicePage] = useState(1)
  const [teamPage, setTeamPage] = useState(1)
  const [page, setPage] = useState(1)
  const [criticalOnly, setCriticalOnly] = usePersistentBoolean('sp.reservations.criticalOnly', false)

  const subscriptionsQuery = useQuery<SubscriptionCostSummary>({
    queryKey: ['ledger', 'subscriptions', days],
    queryFn: () => ledgerApi.subscriptionCostSummary(days).then((r) => r.data),
    staleTime: 30_000,
    retry: 2,
  })
  const hasMultipleSubscriptions = (subscriptionsQuery.data?.subscription_count ?? 0) > 1
  const getSubscriptionDisplayName = (subscriptionName: string | null | undefined, subscriptionKey: string | null | undefined) => {
    const normalizedName = subscriptionName?.trim()
    if (normalizedName) return normalizedName
    return subscriptionKey ? `${subscriptionKey.slice(0, 8)}…` : ec.subscriptionNone
  }
  const singleSubscriptionName =
    getSubscriptionDisplayName(subscriptionsQuery.data?.items[0]?.subscription_name, subscriptionsQuery.data?.items[0]?.subscription_id)

  const servicesQuery = useQuery<PageResponse<ServiceBreakdown>>({
    queryKey: ['economics-costs-services', days, servicePage],
    queryFn: () => ledgerApi.topServicesPaginated(days, servicePage, 20).then((r) => r.data),
    placeholderData: (prev) => prev,
    staleTime: 30_000,
    retry: 2,
  })

  const teamsQuery = useQuery<PageResponse<ServiceBreakdown>>({
    queryKey: ['economics-costs-teams', days, teamPage],
    queryFn: () => ledgerApi.topTeamsPaginated(days, teamPage, 20).then((r) => r.data),
    placeholderData: (prev) => prev,
    staleTime: 30_000,
    retry: 2,
  })

  const detailedCostsQuery = useQuery<PageResponse<DetailedCostRow>>({
    queryKey: ['economics-costs-detailed', days, serviceQuery, providerQuery, teamQuery, subscriptionFilter, page],
    queryFn: () =>
      ledgerApi
        .detailedCosts({
          days,
          service: serviceQuery || undefined,
          provider: providerQuery || undefined,
          owner_team: teamQuery || undefined,
          subscription_id: subscriptionFilter || undefined,
          page,
          page_size: 20,
        })
        .then((r) => r.data),
    staleTime: 30_000,
    retry: 2,
  })
  const reservationEfficiencyQuery = useQuery({
    queryKey: ['economics-reservation-efficiency', days],
    queryFn: () => ledgerApi.reservationEfficiency(days).then((r) => r.data),
    staleTime: 30_000,
    retry: 2,
  })

  const serviceItems = servicesQuery.data?.items ?? []
  const filteredServices = serviceQuery
    ? serviceItems.filter((item) => item.service.toLowerCase().includes(serviceQuery.trim().toLowerCase()))
    : serviceItems
  const totalFilteredCost = filteredServices.reduce((sum, item) => sum + item.cost_usd, 0)
  const prioritizedFamilies = [...(reservationEfficiencyQuery.data?.families ?? [])]
    .sort((a, b) => b.action_priority - a.action_priority || b.waste_cost_usd - a.waste_cost_usd)
  const highPriorityCount = prioritizedFamilies.filter((item) => item.action_priority >= 4).length
  const visibleFamilies = criticalOnly
    ? prioritizedFamilies.filter((item) => item.action_priority >= 4)
    : prioritizedFamilies
  const hasTextFilters = Boolean(serviceQuery || providerQuery || teamQuery || subscriptionFilter)
  const formatMoney = (value: number) => formatCurrency(value, currencyCode)

  const clearTextFilters = () => {
    setServiceQuery('')
    setProviderQuery('')
    setTeamQuery('')
    setSubscriptionFilter('')
    setServicePage(1)
    setTeamPage(1)
    setPage(1)
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-gray-900">{ec.title}</h1>
        <p className="mt-1.5 text-sm leading-relaxed text-gray-500">{ec.subtitle}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">
            {ec.financialValuesBrl}
          </span>
          <span className="rounded-full bg-gray-100 px-2.5 py-1 font-medium text-gray-700">
            {ec.billingContext}
          </span>
        </div>
      </header>

      <div className="space-y-4">
        <SectionIntro
          title={ec.overviewTitle}
          subtitle={ec.overviewSubtitle}
          freshness={ux.freshnessSnapshot}
          badges={[{ label: ec.billingContext, tone: 'billing' }]}
        />
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
              {ec.timeWindow}
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              >
                <option value={30}>{ec.last30}</option>
                <option value={60}>{ec.last60}</option>
                <option value={90}>{ec.last90}</option>
                <option value={180}>{ec.last180}</option>
              </select>
            </label>

            <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
              {ec.serviceFilter}
              <input
                type="text"
                value={serviceQuery}
                onChange={(e) => { setServiceQuery(e.target.value); setPage(1) }}
                placeholder={ec.serviceFilterPlaceholder}
                className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </label>

            <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
              {ec.providerFilter}
              <input
                type="text"
                value={providerQuery}
                onChange={(e) => { setProviderQuery(e.target.value); setPage(1) }}
                placeholder={ec.providerFilterPlaceholder}
                className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </label>

            <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
              {ec.teamFilter}
              <input
                type="text"
                value={teamQuery}
                onChange={(e) => { setTeamQuery(e.target.value); setPage(1) }}
                placeholder={ec.teamFilterPlaceholder}
                className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </label>

            <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
              {ec.subscriptionLabel}
              <select
                value={hasMultipleSubscriptions ? subscriptionFilter : ''}
                onChange={(e) => { setSubscriptionFilter(e.target.value); setPage(1) }}
                disabled={!hasMultipleSubscriptions || subscriptionsQuery.isLoading || subscriptionsQuery.isError}
                className="mt-1.5 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
              >
                {subscriptionsQuery.isLoading ? (
                  <option value="">{ec.subscriptionLoading}</option>
                ) : subscriptionsQuery.isError ? (
                  <option value="">{ec.subscriptionUnavailable}</option>
                ) : hasMultipleSubscriptions ? (
                  <>
                    <option value="">
                      {ec.allSubscriptionsCount.replace('{{count}}', String(subscriptionsQuery.data?.subscription_count ?? 0))}
                    </option>
                    {subscriptionsQuery.data?.items.map((s) => (
                      <option key={s.subscription_id} value={s.subscription_id}>
                        {s.subscription_name
                          ? `${s.subscription_name} (${s.subscription_id.slice(0, 8)}…)`
                          : `${s.subscription_id.slice(0, 8)}…`
                        } · {formatMoney(s.total_cost_usd)}
                      </option>
                    ))}
                  </>
                ) : singleSubscriptionName ? (
                  <option value="">{singleSubscriptionName}</option>
                ) : (
                  <option value="">{ec.subscriptionNone}</option>
                )}
              </select>
            </label>

            <div className="flex flex-col justify-center rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 shadow-sm">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{ec.visibleCost}</div>
              <div className="mt-1 text-xl font-bold tabular-nums text-white">{formatMoney(totalFilteredCost)}</div>
              <div className="mt-1 text-xs leading-relaxed text-slate-400">
                {hasTextFilters ? ec.filtered : ec.detailedCostsDesc}
              </div>
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={clearTextFilters}
              disabled={!hasTextFilters}
              className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-700 hover:border-gray-400 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t.common.reset}
            </button>
          </div>
        </div>
      </div>

      {/* Export panel (SP-EC03) */}
      <ExportPanel
        days={days}
        filters={{ service: serviceQuery || undefined, provider: providerQuery || undefined, owner_team: teamQuery || undefined }}
      />

      <div className="space-y-4">
        <SectionIntro
          title={ec.optimizationTitle}
          subtitle={ec.optimizationSubtitle}
          compact
        />
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-5 py-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-amber-500" />
                <h2 className="text-sm font-semibold text-gray-900">{ec.reservationEfficiency}</h2>
                {highPriorityCount > 0 && (
                  <span className="text-xs font-medium text-red-700">
                    {ec.reservationHighBadge.replace('{{count}}', String(highPriorityCount))}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="text-xs text-gray-600 hover:underline"
                  onClick={() => setCriticalOnly((prev) => !prev)}
                >
                  {criticalOnly ? ec.reservationShowAll : ec.reservationCriticalOnly}
                </button>
                <div className="text-xs text-gray-500">
                  {ec.familiesCount.replace('{{count}}', String(visibleFamilies.length))}
                </div>
              </div>
            </div>
          </div>
          <div className="p-5">
            {reservationEfficiencyQuery.isLoading ? (
              <SkeletonMetricCards count={3} />
            ) : reservationEfficiencyQuery.isError ? (
              <ErrorState
                title={ec.noReservationEfficiency}
                onRetry={() => reservationEfficiencyQuery.refetch()}
                retryLabel={t.common.reset}
                compact
              />
            ) : !(reservationEfficiencyQuery.data?.families.length ?? 0) ? (
              <EmptyState icon="lightbulb" title={ec.noReservationEfficiency} />
            ) : (
              <>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3 mb-4">
                  <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-[11px] font-medium uppercase tracking-wider text-gray-500">{ec.avgUtilization}</div>
                    <div className="mt-2 text-lg font-semibold text-gray-900">
                      {reservationEfficiencyQuery.data?.avg_utilization_pct.toFixed(1)}%
                    </div>
                  </div>
                  <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-[11px] font-medium uppercase tracking-wider text-gray-500">{ec.totalWaste}</div>
                    <div className="mt-2 text-lg font-semibold text-red-600">
                      {formatMoney(reservationEfficiencyQuery.data?.total_waste_cost_usd ?? 0)}
                    </div>
                  </div>
                  <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="text-[11px] font-medium uppercase tracking-wider text-gray-500">{ec.totalReserved}</div>
                    <div className="mt-2 text-lg font-semibold text-gray-900">
                      {(reservationEfficiencyQuery.data?.total_reserved_capacity_units ?? 0).toLocaleString()}
                    </div>
                  </div>
                </div>
                <p className="mb-3 text-sm text-gray-600">{reservationEfficiencyQuery.data?.recommendation}</p>
                <ReservationEfficiencyTable rows={visibleFamilies} ec={ec} />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Detailed costs table */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">{ec.detailedCosts}</h2>
            <p className="mt-1 text-xs text-gray-500">{ec.detailedCostsDesc}</p>
          </div>
          <div className="text-xs text-gray-500">
            {ec.totalRows.replace('{{count}}', String(detailedCostsQuery.data?.total ?? 0))}
          </div>
        </div>
        <div className="p-5">
          {detailedCostsQuery.isLoading ? (
            <SkeletonTable rows={8} columns={9} />
          ) : detailedCostsQuery.isError ? (
            <ErrorState
              title={ec.noRows}
              onRetry={() => detailedCostsQuery.refetch()}
              retryLabel={t.common.reset}
              compact
            />
          ) : !(detailedCostsQuery.data?.items.length ?? 0) ? (
            <EmptyState icon="search" title={ec.noRows} />
          ) : (
            <>
              <DetailedCostsTable rows={detailedCostsQuery.data?.items ?? []} ec={ec} />
              <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
                <span>
                  {ec.pageOf
                    .replace('{{page}}', String(detailedCostsQuery.data?.page ?? page))
                    .replace('{{total}}', String(Math.max(1, Math.ceil((detailedCostsQuery.data?.total ?? 0) / (detailedCostsQuery.data?.page_size ?? 20)))))}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1 || detailedCostsQuery.isFetching}
                    className="rounded-lg border border-gray-300 px-4 py-2 disabled:opacity-50"
                  >
                    {ec.previous}
                  </button>
                  <button
                    onClick={() => { if (detailedCostsQuery.data?.has_next) setPage((p) => p + 1) }}
                    disabled={!detailedCostsQuery.data?.has_next || detailedCostsQuery.isFetching}
                    className="rounded-lg border border-gray-300 px-4 py-2 disabled:opacity-50"
                  >
                    {ec.next}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Service + Team breakdowns */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center gap-2.5 border-b border-gray-100 px-5 py-4">
            <Filter className="h-4 w-4 text-gray-500" />
            <h2 className="text-sm font-semibold text-gray-900">{ec.costByService}</h2>
          </div>
          <div className="p-5">
            {servicesQuery.isLoading ? (
              <SkeletonTable rows={5} columns={3} />
            ) : !filteredServices.length ? (
              <EmptyState icon="search" title={ec.noServiceData} />
            ) : (
              <>
                <BreakdownTable rows={filteredServices} label={ec.costByService} ec={ec} />
                <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
                  <span>
                    {ec.pageOf
                      .replace('{{page}}', String(servicesQuery.data?.page ?? servicePage))
                      .replace('{{total}}', String(Math.max(1, Math.ceil((servicesQuery.data?.total ?? 0) / (servicesQuery.data?.page_size ?? 20)))))}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setServicePage((p) => Math.max(1, p - 1))}
                      disabled={servicePage <= 1 || servicesQuery.isFetching}
                      className="rounded-lg border border-gray-300 px-4 py-2 disabled:opacity-50"
                    >
                      {ec.previous}
                    </button>
                    <button
                      onClick={() => { if (servicesQuery.data?.has_next) setServicePage((p) => p + 1) }}
                      disabled={!servicesQuery.data?.has_next || servicesQuery.isFetching}
                      className="rounded-lg border border-gray-300 px-4 py-2 disabled:opacity-50"
                    >
                      {ec.next}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-5 py-4">
            <h2 className="text-sm font-semibold text-gray-900">{ec.costByTeam}</h2>
          </div>
          <div className="p-5">
            {teamsQuery.isLoading ? (
              <SkeletonTable rows={5} columns={3} />
            ) : !(teamsQuery.data?.items ?? []).length ? (
              <EmptyState icon="search" title={ec.noTeamData} />
            ) : (
              <>
                <BreakdownTable rows={teamsQuery.data?.items ?? []} label={ec.costByTeam} ec={ec} />
                <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
                  <span>
                    {ec.pageOf
                      .replace('{{page}}', String(teamsQuery.data?.page ?? teamPage))
                      .replace('{{total}}', String(Math.max(1, Math.ceil((teamsQuery.data?.total ?? 0) / (teamsQuery.data?.page_size ?? 20)))))}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setTeamPage((p) => Math.max(1, p - 1))}
                      disabled={teamPage <= 1 || teamsQuery.isFetching}
                      className="rounded-lg border border-gray-300 px-4 py-2 disabled:opacity-50"
                    >
                      {ec.previous}
                    </button>
                    <button
                      onClick={() => { if (teamsQuery.data?.has_next) setTeamPage((p) => p + 1) }}
                      disabled={!teamsQuery.data?.has_next || teamsQuery.isFetching}
                      className="rounded-lg border border-gray-300 px-4 py-2 disabled:opacity-50"
                    >
                      {ec.next}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

type EcKeys = {
  colService: string
  colCost: string
  colDate: string
  colSubscription: string
  colProvider: string
  colResource: string
  colTeam: string
  colEnvironment: string
  colRegion: string
  colFamily: string
  colShare: string
  colPriority: string
  colUtilization: string
  colAction: string
  colWaste: string
  colRenewal: string
  colAdvisor: string
  reservationEfficiency: string
  familiesCount: string
  loadingReservationEfficiency: string
  noReservationEfficiency: string
  avgUtilization: string
  totalWaste: string
  totalReserved: string
  noRenewalWindow: string
  noAdvisorSignals: string
  actionKeep: string
  actionResize: string
  actionScheduleStop: string
  actionExchange: string
  actionDoNotRenew: string
  reservationHighBadge: string
  reservationCriticalOnly: string
  reservationShowAll: string
}

function BreakdownTable({ rows, label, ec }: { rows: ServiceBreakdown[]; label: string; ec: EcKeys }) {
  const formatMoney = (value: number) => formatCurrency(value, DEFAULT_DISPLAY_CURRENCY)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-left">
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{label}</th>
            <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colCost}</th>
            <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colShare}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {rows.map((row) => (
            <tr key={`${label}-${row.service}`} className="transition hover:bg-gray-50/50">
              <td className="py-3 pr-4 font-medium text-gray-900">{row.service}</td>
              <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{formatMoney(row.cost_usd)}</td>
              <td className="py-3 text-right tabular-nums text-gray-700">{row.percentage.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function DetailedCostsTable({ rows, ec }: { rows: DetailedCostRow[]; ec: EcKeys }) {
  const formatMoney = (value: number) => formatCurrency(value, DEFAULT_DISPLAY_CURRENCY)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-left">
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colDate}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colProvider}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colSubscription}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colService}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colResource}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colTeam}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colEnvironment}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colRegion}</th>
            <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colCost}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {rows.map((row, index) => (
            <tr key={`${row.date}-${row.provider}-${row.resource_name ?? 'resource'}-${index}`} className="transition hover:bg-gray-50/50">
              <td className="py-3 pr-4 text-gray-700">{row.date}</td>
              <td className="py-3 pr-4 text-gray-700">{row.provider}</td>
              <td className="py-3 pr-4 font-mono text-xs text-gray-500">
                {row.subscription_id ? `${row.subscription_id.slice(0, 8)}…` : '-'}
              </td>
              <td className="py-3 pr-4 text-gray-700">{row.service ?? '-'}</td>
              <td className="py-3 pr-4 font-medium text-gray-900">{row.resource_name ?? '-'}</td>
              <td className="py-3 pr-4 text-gray-700">{row.owner_team ?? '-'}</td>
              <td className="py-3 pr-4 text-gray-700">{row.environment ?? '-'}</td>
              <td className="py-3 pr-4 text-gray-700">{row.region ?? '-'}</td>
              <td className="py-3 text-right tabular-nums text-gray-700">{formatMoney(row.cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ReservationEfficiencyTable({ rows, ec }: { rows: ReservationEfficiencyByFamily[]; ec: EcKeys }) {
  const formatMoney = (value: number) => formatCurrency(value, DEFAULT_DISPLAY_CURRENCY)
  const actionLabel: Record<ReservationEfficiencyAction, string> = {
    keep: ec.actionKeep,
    resize_resource: ec.actionResize,
    schedule_stop: ec.actionScheduleStop,
    exchange_reservation: ec.actionExchange,
    do_not_renew: ec.actionDoNotRenew,
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-left">
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colFamily}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colPriority}</th>
            <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colUtilization}</th>
            <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colWaste}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colAction}</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colRenewal}</th>
            <th className="pb-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">{ec.colAdvisor}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {rows.map((row) => (
            <tr key={row.family} className="transition hover:bg-gray-50/50">
              <td className="py-3 pr-4 font-medium text-gray-900">{row.family}</td>
              <td className="py-3 pr-4">
                <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                  <AlertTriangle className="h-3 w-3" />
                  P{row.action_priority}
                </span>
              </td>
              <td className="py-3 pr-4 text-right tabular-nums text-gray-700">{row.utilization_pct.toFixed(1)}%</td>
              <td className="py-3 pr-4 text-right tabular-nums text-red-600">{formatMoney(row.waste_cost_usd)}</td>
              <td className="py-3 pr-4">
                <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                  {actionLabel[row.recommended_action]}
                </span>
              </td>
              <td className="py-3 pr-4 text-gray-700">
                {row.renewal_window_days != null ? (
                  <span className="inline-flex items-center gap-1">
                    <CalendarClock className="h-3 w-3 text-gray-500" />
                    {row.renewal_window_days}d
                  </span>
                ) : ec.noRenewalWindow}
              </td>
              <td className="py-3 text-gray-700">
                {row.advisory_signals.length ? row.advisory_signals[0] : ec.noAdvisorSignals}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
