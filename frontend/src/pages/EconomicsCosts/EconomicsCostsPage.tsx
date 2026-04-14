import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Filter } from 'lucide-react'
import { ledgerApi, type ExportJob } from '../../api/ledger'
import type { PageResponse, ServiceBreakdown, DetailedCostRow } from '../../types'

const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

// ─── Export panel ────────────────────────────────────────────────────────────

type ExportFormat = 'csv' | 'xlsx'
type ExportState =
  | { phase: 'idle' }
  | { phase: 'submitting' }
  | { phase: 'polling'; jobId: string; job: ExportJob }
  | { phase: 'ready'; job: ExportJob }
  | { phase: 'error'; message: string }

function ExportPanel({ days, filters }: { days: number; filters: Record<string, string | undefined> }) {
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
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <Download className="h-4 w-4 text-gray-600" />
        <h2 className="text-sm font-semibold text-gray-900">Export Report</h2>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-gray-600">
          Format
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
            disabled={busy}
            className="mt-1 block rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none disabled:opacity-50"
          >
            <option value="csv">CSV</option>
            <option value="xlsx">Excel (.xlsx)</option>
          </select>
        </label>

        <button
          onClick={handleExport}
          disabled={busy}
          className="rounded bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {state.phase === 'submitting'
            ? 'Requesting…'
            : state.phase === 'polling'
              ? 'Generating…'
              : 'Export'}
        </button>

        {state.phase === 'polling' && (
          <span className="text-xs text-gray-500 animate-pulse">
            Building {format.toUpperCase()} — please wait…
          </span>
        )}

        {state.phase === 'ready' && (
          <a
            href={ledgerApi.downloadExportUrl(state.job.id)}
            download={state.job.file_name ?? `report.${format}`}
            className="inline-flex items-center gap-1.5 rounded border border-brand-300 bg-brand-50 px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-100"
          >
            <Download className="h-3.5 w-3.5" />
            Download {state.job.file_name ?? `report.${format}`}
          </a>
        )}

        {state.phase === 'error' && (
          <span className="text-xs text-red-600">{state.message}</span>
        )}
      </div>

      {state.phase !== 'idle' && state.phase !== 'submitting' && (
        <button
          onClick={() => { clearPoll(); setState({ phase: 'idle' }) }}
          className="mt-2 text-xs text-gray-400 hover:text-gray-600 underline"
        >
          Reset
        </button>
      )}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function EconomicsCostsPage() {
  const [days, setDays] = useState(30)
  const [serviceQuery, setServiceQuery] = useState('')
  const [providerQuery, setProviderQuery] = useState('')
  const [teamQuery, setTeamQuery] = useState('')
  const [servicePage, setServicePage] = useState(1)
  const [teamPage, setTeamPage] = useState(1)
  const [page, setPage] = useState(1)

  const servicesQuery = useQuery<PageResponse<ServiceBreakdown>>({
    queryKey: ['economics-costs-services', days, servicePage],
    queryFn: () => ledgerApi.topServicesPaginated(days, servicePage, 20).then((r) => r.data),
    placeholderData: (prev) => prev,
  })

  const teamsQuery = useQuery<PageResponse<ServiceBreakdown>>({
    queryKey: ['economics-costs-teams', days, teamPage],
    queryFn: () => ledgerApi.topTeamsPaginated(days, teamPage, 20).then((r) => r.data),
    placeholderData: (prev) => prev,
  })

  const detailedCostsQuery = useQuery<PageResponse<DetailedCostRow>>({
    queryKey: ['economics-costs-detailed', days, serviceQuery, providerQuery, teamQuery, page],
    queryFn: () =>
      ledgerApi
        .detailedCosts({
          days,
          service: serviceQuery || undefined,
          provider: providerQuery || undefined,
          owner_team: teamQuery || undefined,
          page,
          page_size: 20,
        })
        .then((r) => r.data),
  })

  const serviceItems = servicesQuery.data?.items ?? []
  const filteredServices = serviceQuery
    ? serviceItems.filter((item) => item.service.toLowerCase().includes(serviceQuery.trim().toLowerCase()))
    : serviceItems
  const totalFilteredCost = filteredServices.reduce((sum, item) => sum + item.cost_usd, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Economics Costs</h1>
        <p className="mt-1 text-sm text-gray-500">
          Explore detailed cost distribution by service and team using interactive filters.
        </p>
      </div>

      {/* Filters */}
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
              onChange={(e) => { setServiceQuery(e.target.value); setPage(1) }}
              placeholder="Filter service name"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
          </label>

          <label className="text-sm text-gray-600">
            Provider filter
            <input
              type="text"
              value={providerQuery}
              onChange={(e) => { setProviderQuery(e.target.value); setPage(1) }}
              placeholder="azure, aws, gcp"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
          </label>

          <label className="text-sm text-gray-600">
            Team filter
            <input
              type="text"
              value={teamQuery}
              onChange={(e) => { setTeamQuery(e.target.value); setPage(1) }}
              placeholder="owner team"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
          </label>

          <div className="rounded-lg border border-gray-200 px-3 py-2">
            <div className="text-xs uppercase tracking-wide text-gray-500">Visible Cost</div>
            <div className="mt-1 text-xl font-semibold text-gray-900">{money.format(totalFilteredCost)}</div>
          </div>
        </div>
      </div>

      {/* Export panel (SP-EC03) */}
      <ExportPanel
        days={days}
        filters={{ service: serviceQuery || undefined, provider: providerQuery || undefined, owner_team: teamQuery || undefined }}
      />

      {/* Detailed costs table */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Detailed Costs</h2>
            <p className="mt-1 text-xs text-gray-500">
              Detailed rows from the ledger with combined filters and pagination.
            </p>
          </div>
          <div className="text-xs text-gray-500">Total rows: {detailedCostsQuery.data?.total ?? 0}</div>
        </div>
        {detailedCostsQuery.isLoading ? (
          <div className="py-8 text-center text-sm text-gray-500">Loading detailed costs...</div>
        ) : !(detailedCostsQuery.data?.items.length ?? 0) ? (
          <div className="py-8 text-center text-sm text-gray-500">No cost rows for current filters.</div>
        ) : (
          <>
            <DetailedCostsTable rows={detailedCostsQuery.data?.items ?? []} />
            <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
              <span>
                Page {detailedCostsQuery.data?.page ?? page} of{' '}
                {Math.max(1, Math.ceil((detailedCostsQuery.data?.total ?? 0) / (detailedCostsQuery.data?.page_size ?? 20)))}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1 || detailedCostsQuery.isFetching}
                  className="rounded border border-gray-300 px-3 py-1 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => { if (detailedCostsQuery.data?.has_next) setPage((p) => p + 1) }}
                  disabled={!detailedCostsQuery.data?.has_next || detailedCostsQuery.isFetching}
                  className="rounded border border-gray-300 px-3 py-1 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Service + Team breakdowns */}
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
            <>
              <BreakdownTable rows={filteredServices} label="Service" />
              <div className="mt-2 flex items-center justify-between text-xs text-gray-600">
                <span>
                  Page {servicesQuery.data?.page ?? servicePage} of{' '}
                  {Math.max(1, Math.ceil((servicesQuery.data?.total ?? 0) / (servicesQuery.data?.page_size ?? 20)))}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setServicePage((p) => Math.max(1, p - 1))}
                    disabled={servicePage <= 1 || servicesQuery.isFetching}
                    className="rounded border border-gray-300 px-2 py-1 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => { if (servicesQuery.data?.has_next) setServicePage((p) => p + 1) }}
                    disabled={!servicesQuery.data?.has_next || servicesQuery.isFetching}
                    className="rounded border border-gray-300 px-2 py-1 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">Cost by Team</h2>
          {teamsQuery.isLoading ? (
            <div className="py-8 text-center text-sm text-gray-500">Loading teams...</div>
          ) : !(teamsQuery.data?.items ?? []).length ? (
            <div className="py-8 text-center text-sm text-gray-500">No team data available.</div>
          ) : (
            <>
              <BreakdownTable rows={teamsQuery.data?.items ?? []} label="Team" />
              <div className="mt-2 flex items-center justify-between text-xs text-gray-600">
                <span>
                  Page {teamsQuery.data?.page ?? teamPage} of{' '}
                  {Math.max(1, Math.ceil((teamsQuery.data?.total ?? 0) / (teamsQuery.data?.page_size ?? 20)))}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setTeamPage((p) => Math.max(1, p - 1))}
                    disabled={teamPage <= 1 || teamsQuery.isFetching}
                    className="rounded border border-gray-300 px-2 py-1 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => { if (teamsQuery.data?.has_next) setTeamPage((p) => p + 1) }}
                    disabled={!teamsQuery.data?.has_next || teamsQuery.isFetching}
                    className="rounded border border-gray-300 px-2 py-1 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function BreakdownTable({ rows, label }: { rows: ServiceBreakdown[]; label: string }) {
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

function DetailedCostsTable({ rows }: { rows: DetailedCostRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs font-medium text-gray-500">
            <th className="pb-2 pr-3">Date</th>
            <th className="pb-2 pr-3">Provider</th>
            <th className="pb-2 pr-3">Service</th>
            <th className="pb-2 pr-3">Resource</th>
            <th className="pb-2 pr-3">Team</th>
            <th className="pb-2 pr-3">Environment</th>
            <th className="pb-2 pr-3">Region</th>
            <th className="pb-2">Cost</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row, index) => (
            <tr key={`${row.date}-${row.provider}-${row.resource_name ?? 'resource'}-${index}`}>
              <td className="py-2 pr-3 text-gray-700">{row.date}</td>
              <td className="py-2 pr-3 text-gray-700">{row.provider}</td>
              <td className="py-2 pr-3 text-gray-700">{row.service ?? '-'}</td>
              <td className="py-2 pr-3 font-medium text-gray-800">{row.resource_name ?? '-'}</td>
              <td className="py-2 pr-3 text-gray-700">{row.owner_team ?? '-'}</td>
              <td className="py-2 pr-3 text-gray-700">{row.environment ?? '-'}</td>
              <td className="py-2 pr-3 text-gray-700">{row.region ?? '-'}</td>
              <td className="py-2 text-gray-700">{money.format(row.cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
