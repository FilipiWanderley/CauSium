import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle, Info, ShieldAlert } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { usePageTitle } from '../../hooks/usePageTitle'
import { ledgerApi } from '../../api/ledger'
import type { ReconciliationReport, ReconciliationSubscriptionRow } from '../../types'
import clsx from 'clsx'
import { Navigate } from 'react-router-dom'
import { formatCurrency } from '../../utils/currency'

// ── helpers ───────────────────────────────────────────────────────────────────

const ALLOWED_ROLES = new Set(['platform_admin'])

const PLACEHOLDER_SUBSCRIPTION = 'aaaaaaaa-0000-0000-0000-aaaaaaaaaaaa'

function fmtCost(n: number, currency?: string) {
  return formatCurrency(n, currency, { maximumFractionDigits: 2 })
}

function fmtDate(d: string | null | undefined) {
  if (!d) return '—'
  return String(d).slice(0, 10)
}

function truncSub(id: string) {
  if (!id) return '—'
  return id.length > 12 ? id.slice(0, 8) + '…' : id
}

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

function monthStartISO() {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
}

// ── sub-components ────────────────────────────────────────────────────────────

function SummaryCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-gray-900 truncate">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400 truncate">{sub}</p>}
    </div>
  )
}

function WarningBanner({ report }: { report: ReconciliationReport }) {
  const w = report.warnings
  const items: { key: string; label: string; level: 'warn' | 'info' }[] = []

  if (w.no_data)
    items.push({ key: 'no_data', label: 'No cost data found for the selected filters and period.', level: 'warn' })
  if (w.mixed_currency)
    items.push({ key: 'mixed_currency', label: `Mixed currencies detected: ${report.currencies.join(', ')}. Totals may not be directly comparable.`, level: 'warn' })
  if (w.partial_range)
    items.push({ key: 'partial_range', label: `Data only available up to ${fmtDate(report.max_date)}, not the full requested range.`, level: 'info' })
  if (w.missing_subscription_id)
    items.push({ key: 'missing_sub', label: 'Some records have no subscription ID. They appear in totals but not in the subscription breakdown.', level: 'info' })
  if (w.account_mismatch)
    items.push({ key: 'mismatch', label: 'Some subscription IDs in cost data do not match any connected cloud account.', level: 'warn' })
  if (w.orphan_records > 0)
    items.push({ key: 'orphan', label: `${w.orphan_records.toLocaleString()} records reference an account ID not found in connected accounts.`, level: 'warn' })

  if (items.length === 0) return null

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.key}
          className={clsx(
            'flex items-start gap-3 rounded-lg border px-4 py-3 text-sm',
            item.level === 'warn'
              ? 'border-amber-200 bg-amber-50 text-amber-800'
              : 'border-blue-200 bg-blue-50 text-blue-800',
          )}
        >
          {item.level === 'warn' ? (
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  )
}

function SubscriptionTable({ rows, currency }: { rows: ReconciliationSubscriptionRow[]; currency: string }) {
  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
        No subscription breakdown available.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
            <th className="px-4 py-3">Subscription ID</th>
            <th className="px-4 py-3">Display Name</th>
            <th className="px-4 py-3">Provider</th>
            <th className="px-4 py-3">Account ID</th>
            <th className="px-4 py-3 text-right">Total Cost</th>
            <th className="px-4 py-3">Currency</th>
            <th className="px-4 py-3 text-right">Records</th>
            <th className="px-4 py-3">Min Date</th>
            <th className="px-4 py-3">Max Date</th>
            <th className="px-4 py-3">Match</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {rows.map((row, idx) => (
            <tr key={idx} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-gray-600" title={row.subscription_id}>
                {truncSub(row.subscription_id)}
              </td>
              <td className="px-4 py-3 text-gray-700">{row.display_name ?? '—'}</td>
              <td className="px-4 py-3 text-gray-500 uppercase text-xs">{row.provider ?? '—'}</td>
              <td className="px-4 py-3 font-mono text-xs text-gray-400" title={row.account_id ?? ''}>
                {row.account_id ? truncSub(row.account_id) : '—'}
              </td>
              <td className="px-4 py-3 text-right font-medium text-gray-900">
                {fmtCost(row.total_cost, row.currency ?? currency)}
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">{row.currency ?? '—'}</td>
              <td className="px-4 py-3 text-right text-gray-600">{row.records_count.toLocaleString()}</td>
              <td className="px-4 py-3 text-gray-500 text-xs">{fmtDate(row.min_date)}</td>
              <td className="px-4 py-3 text-gray-500 text-xs">{fmtDate(row.max_date)}</td>
              <td className="px-4 py-3">
                {row.external_id_match ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                    <CheckCircle className="h-3 w-3" /> Match
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                    <AlertTriangle className="h-3 w-3" /> No Match
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── main page ─────────────────────────────────────────────────────────────────

export function ReconciliationPage() {
  usePageTitle('Cost Data Reconciliation')
  const { user } = useAuth()

  // Role guard — redirect non-admin/engineer users
  if (user && !ALLOWED_ROLES.has(user.role)) {
    return <Navigate to="/app/dashboard" replace />
  }

  const [provider, setProvider] = useState('')
  const [subscriptionId, setSubscriptionId] = useState('')
  const [accountId, setAccountId] = useState('')
  const [startDate, setStartDate] = useState(monthStartISO())
  const [endDate, setEndDate] = useState(todayISO())

  const queryParams = {
    provider: provider || undefined,
    subscription_id: subscriptionId || undefined,
    account_id: accountId || undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  }

  const { data, isLoading, isError, refetch } = useQuery<ReconciliationReport>({
    queryKey: ['ledger', 'reconciliation', queryParams],
    queryFn: () => ledgerApi.reconciliation(queryParams).then((r) => r.data),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })

  const currency = data?.dominant_currency ?? 'USD'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-bold text-gray-900 sm:text-2xl">Cost Reconciliation</h1>
            <span className="inline-flex items-center gap-1 rounded-full border border-violet-200 bg-violet-50 px-2.5 py-0.5 text-xs font-semibold text-violet-700">
              <ShieldAlert className="h-3 w-3" />
              Platform admin only
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Validate imported cost data against dashboard totals.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isLoading}
          className="rounded-md border border-gray-300 bg-white px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {/* Filters */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Filters</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="text-xs text-gray-600">
            Provider
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none"
            >
              <option value="">All providers</option>
              <option value="azure">Azure</option>
              <option value="aws">AWS</option>
              <option value="gcp">GCP</option>
            </select>
          </label>
          <label className="text-xs text-gray-600">
            Subscription ID
            <input
              type="text"
              value={subscriptionId}
              onChange={(e) => setSubscriptionId(e.target.value)}
              placeholder="xxxxxxxx-…"
              className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none"
            />
          </label>
          <label className="text-xs text-gray-600">
            Account ID
            <input
              type="text"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              placeholder="UUID"
              className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none"
            />
          </label>
          <label className="text-xs text-gray-600">
            Start Date
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none"
            />
          </label>
          <label className="text-xs text-gray-600">
            End Date
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none"
            />
          </label>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex h-40 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not load reconciliation data. Check your access and try again.
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <>
          {/* Warnings */}
          <WarningBanner report={data} />

          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            <SummaryCard
              label="Total Cost"
              value={fmtCost(data.total_cost, currency)}
              sub={`${data.start_date} → ${data.end_date}`}
            />
            <SummaryCard
              label="Dashboard Equivalent"
              value={fmtCost(data.dashboard_equivalent_total, currency)}
              sub="Same filters, month-based"
            />
            <SummaryCard
              label="Difference"
              value={fmtCost(data.difference, currency)}
              sub={`${data.difference_pct > 0 ? '+' : ''}${data.difference_pct}%`}
            />
            <SummaryCard
              label="Records"
              value={data.records_count.toLocaleString()}
              sub={`${data.distinct_services} services · ${data.distinct_resources} resources`}
            />
            <SummaryCard
              label="Currency"
              value={data.dominant_currency}
              sub={data.mixed_currency ? `Mixed: ${data.currencies.join(', ')}` : 'Single currency'}
            />
            <SummaryCard
              label="Subscriptions"
              value={data.subscription_count}
            />
            <SummaryCard
              label="Min Date"
              value={fmtDate(data.min_date)}
            />
            <SummaryCard
              label="Max Date"
              value={fmtDate(data.max_date)}
            />
          </div>

          {/* By subscription table */}
          <div>
            <h2 className="mb-3 text-sm font-semibold text-gray-900">By Subscription</h2>
            <SubscriptionTable
              rows={data.by_subscription.filter(
                (row) => row.subscription_id !== PLACEHOLDER_SUBSCRIPTION
              )}
              currency={currency}
            />
          </div>

          {/* Disclaimer */}
          <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-xs text-gray-500">
            {data.note}
          </div>
        </>
      )}
    </div>
  )
}
