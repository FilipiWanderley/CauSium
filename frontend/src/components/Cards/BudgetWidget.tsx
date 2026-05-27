import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { DollarSign, AlertTriangle, PieChart } from 'lucide-react'
import clsx from 'clsx'
import { economicsApi } from '../../api/economics'
import { useI18n } from '../../contexts/I18nContext'
import { useAuth } from '../../hooks/useAuth'
import type { FinancialBudgetPeriod, WorkspaceBudgetUpsert } from '../../types'
import { formatCurrency } from '../../utils/currency'

const fmt = (n: number) => formatCurrency(n)

const PERIODS: FinancialBudgetPeriod[] = ['monthly', 'quarterly', 'annual']

function ThresholdMarker({ pct }: { pct: number }) {
  return (
    <div
      className="absolute top-0 h-full w-px bg-yellow-400 opacity-70"
      style={{ left: `${pct}%` }}
      title={`${pct}% alert`}
    />
  )
}

function ConfigureForm({
  onClose,
  defaultValues,
}: {
  onClose: () => void
  defaultValues?: Partial<WorkspaceBudgetUpsert>
}) {
  const { t } = useI18n()
  const b = t.budget
  const qc = useQueryClient()

  const [amount, setAmount] = useState(String(defaultValues?.amount_usd ?? ''))
  const [period, setPeriod] = useState<FinancialBudgetPeriod>(
    defaultValues?.period ?? 'monthly'
  )
  const [thresholds, setThresholds] = useState(
    (defaultValues?.alert_thresholds ?? [50, 80, 90]).join(', ')
  )
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (payload: WorkspaceBudgetUpsert) => economicsApi.upsertBudget(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspace-budget'] })
      onClose()
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to save budget'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    const parsedAmount = parseFloat(amount)
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      setError('Amount must be a positive number')
      return
    }
    const parsedThresholds = thresholds
      .split(',')
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n))
    mutation.mutate({ amount_usd: parsedAmount, period, alert_thresholds: parsedThresholds })
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 space-y-3 border-t border-gray-100 pt-4">
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">{b.amount}</label>
        <input
          type="number"
          min="1"
          step="any"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          placeholder="10000"
          required
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">{b.period}</label>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value as FinancialBudgetPeriod)}
          className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {PERIODS.map((p) => (
            <option key={p} value={p}>
              {b[`period_${p}` as keyof typeof b]}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          {b.thresholds}
        </label>
        <input
          type="text"
          value={thresholds}
          onChange={(e) => setThresholds(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          placeholder="50, 80, 90"
        />
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
        >
          {b.cancel}
        </button>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {mutation.isPending ? '…' : b.save}
        </button>
      </div>
    </form>
  )
}

export function BudgetWidget() {
  const { t } = useI18n()
  const b = t.budget
  const { user } = useAuth()
  const [showForm, setShowForm] = useState(false)

  const canManage =
    user?.role === 'admin' ||
    user?.role === 'platform_admin' ||
    user?.role === 'finops'

  const { data: budget, isLoading } = useQuery({
    queryKey: ['workspace-budget'],
    queryFn: () =>
      economicsApi
        .getBudget()
        .then((r) => r.data)
        .catch((err) => {
          if (err?.response?.status === 404) return null
          throw err
        }),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm animate-pulse">
        <div className="h-4 w-32 rounded bg-gray-100" />
      </div>
    )
  }

  const periodLabel = budget
    ? b[`period_${budget.period}` as keyof typeof b] ?? budget.period
    : null

  // Determine progress bar colour based on consumed_pct vs alert thresholds
  const pct = budget?.consumed_pct ?? 0
  const thresholds = budget?.alert_thresholds ?? []
  const maxTriggered = [...thresholds].reverse().find((t) => pct >= t) ?? null
  const barColor =
    maxTriggered === null
      ? 'bg-green-500'
      : maxTriggered >= (thresholds[thresholds.length - 1] ?? 90)
      ? 'bg-red-500'
      : 'bg-yellow-500'

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-brand-500" />
          <h2 className="text-sm font-semibold text-gray-900">
            {b.title}
            {periodLabel && (
              <span className="ml-1.5 text-xs font-normal text-gray-400">
                ({periodLabel})
              </span>
            )}
          </h2>
        </div>
        {canManage && (
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="text-xs text-brand-600 hover:underline"
          >
            {b.configure}
          </button>
        )}
      </div>

      {budget ? (
        <>
          {/* Amount row */}
          <div className="flex items-baseline gap-1 mb-3">
            <span className="text-2xl font-bold text-gray-900">
              {fmt(budget.consumed_usd)}
            </span>
            <span className="text-sm text-gray-400">
              {b.of} {fmt(budget.amount_usd)}
            </span>
          </div>

          {/* Progress bar */}
          <div className="relative h-2.5 rounded-full bg-gray-100 overflow-hidden mb-1">
            <div
              className={clsx('h-full rounded-full transition-all', barColor)}
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
            {thresholds.map((t) => (
              <ThresholdMarker key={t} pct={t} />
            ))}
          </div>

          {/* Stats row */}
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <span>
              <span className="font-semibold text-gray-700">{pct.toFixed(1)}%</span>{' '}
              {b.consumed}
            </span>
            {budget.projected_eom_usd != null && (
              <span className="flex items-center gap-1">
                {budget.projected_eom_usd > budget.amount_usd && (
                  <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                )}
                {b.projectedEom}:{' '}
                <span
                  className={clsx(
                    'font-semibold',
                    budget.projected_eom_usd > budget.amount_usd
                      ? 'text-red-600'
                      : 'text-gray-700'
                  )}
                >
                  {fmt(budget.projected_eom_usd)}
                </span>
              </span>
            )}
            {budget.projected_eom_usd == null && (
              <span className="flex items-center gap-1">
                <PieChart className="h-3.5 w-3.5 text-gray-300" />
                {b.projectedEom}: —
              </span>
            )}
          </div>
        </>
      ) : (
        <p className="text-sm text-gray-400">{b.notConfigured}</p>
      )}

      {showForm && (
        <ConfigureForm
          onClose={() => setShowForm(false)}
          defaultValues={
            budget
              ? {
                  amount_usd: budget.amount_usd,
                  period: budget.period,
                  alert_thresholds: budget.alert_thresholds,
                }
              : undefined
          }
        />
      )}
    </div>
  )
}
