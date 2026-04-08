import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, ShieldAlert, Trash2, ToggleLeft, ToggleRight, AlertTriangle } from 'lucide-react'
import { useState } from 'react'
import { riskBudgetsApi } from '../../api/riskBudgets'
import type { RiskBudget, BudgetType, BudgetPeriod } from '../../types'
import clsx from 'clsx'

// ── Meta ──────────────────────────────────────────────────────────────────────

const BUDGET_TYPE_META: Record<BudgetType, { label: string; unit: string; description: string }> = {
  blast_radius: {
    label: 'Blast Radius',
    unit: '%',
    description: '% max of services affected by a change',
  },
  cost_variance: {
    label: 'Cost Variance',
    unit: '%',
    description: 'Max allowed cost increase per period',
  },
  error_rate: {
    label: 'Error Rate',
    unit: '%',
    description: 'Max allowed error rate after a deploy',
  },
  change_frequency: {
    label: 'Change Frequency',
    unit: 'deploys',
    description: 'Max number of changes per period',
  },
}

const PERIOD_LABEL: Record<BudgetPeriod, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
}

const BUDGET_TYPES: BudgetType[] = ['blast_radius', 'cost_variance', 'error_rate', 'change_frequency']
const PERIODS: BudgetPeriod[] = ['daily', 'weekly', 'monthly']
const ENVS = ['production', 'staging', 'development', 'unknown']

// ── Gauge ────────────────────────────────────────────────────────────────────

function UsageGauge({ current, limit }: { current: number | null; limit: number }) {
  if (current == null) {
    return <span className="text-xs text-gray-400">No data yet</span>
  }
  const pct = Math.min((current / limit) * 100, 100)
  const color =
    pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-400' : 'bg-green-500'

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-500">
        <span>
          {current.toLocaleString(undefined, { maximumFractionDigits: 1 })} /{' '}
          {limit.toLocaleString(undefined, { maximumFractionDigits: 1 })}
        </span>
        <span className={clsx('font-semibold', pct >= 90 ? 'text-red-600' : pct >= 70 ? 'text-yellow-600' : 'text-green-600')}>
          {Math.round(pct)}%
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-100">
        <div className={clsx('h-2 rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
      </div>
      {pct >= 90 && (
        <div className="flex items-center gap-1 text-xs text-red-600">
          <AlertTriangle className="h-3 w-3" />
          Budget exceeded
        </div>
      )}
    </div>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────

function BudgetCard({
  budget,
  onToggle,
  onDelete,
}: {
  budget: RiskBudget
  onToggle: (id: string, active: boolean) => void
  onDelete: (id: string) => void
}) {
  const meta = BUDGET_TYPE_META[budget.budget_type]

  return (
    <div
      className={clsx(
        'rounded-xl border bg-white p-4 shadow-sm space-y-3 transition-opacity',
        !budget.is_active && 'opacity-50'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-gray-800 text-sm leading-tight">{budget.name}</p>
          <p className="text-xs text-gray-400 mt-0.5">{meta.description}</p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            title={budget.is_active ? 'Deactivate' : 'Activate'}
            onClick={() => onToggle(budget.id, !budget.is_active)}
            className="rounded p-1 hover:bg-gray-100 transition-colors text-gray-400"
          >
            {budget.is_active ? (
              <ToggleRight className="h-5 w-5 text-brand-600" />
            ) : (
              <ToggleLeft className="h-5 w-5" />
            )}
          </button>
          <button
            title="Delete"
            onClick={() => onDelete(budget.id)}
            className="rounded p-1 hover:bg-red-50 hover:text-red-500 transition-colors text-gray-400"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5">
        <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
          {meta.label}
        </span>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          {budget.domain}
        </span>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          {budget.environment}
        </span>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          {PERIOD_LABEL[budget.period]}
        </span>
      </div>

      {/* Limit */}
      <div className="text-xs text-gray-500">
        Limit:{' '}
        <span className="font-semibold text-gray-800">
          {budget.limit_value.toLocaleString(undefined, { maximumFractionDigits: 1 })} {meta.unit}
        </span>
      </div>

      {/* Gauge */}
      <UsageGauge current={budget.current_value} limit={budget.limit_value} />
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

const EMPTY_FORM = {
  name: '',
  domain: '',
  environment: 'production',
  budget_type: 'cost_variance' as BudgetType,
  period: 'weekly' as BudgetPeriod,
  limit_value: '',
}

export function RiskBudgetsPage() {
  const queryClient = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [activeOnly, setActiveOnly] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)

  const { data: budgets = [], isLoading } = useQuery({
    queryKey: ['risk-budgets', activeOnly],
    queryFn: () => riskBudgetsApi.list({ active_only: activeOnly }).then((r) => r.data.items),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      riskBudgetsApi.create({
        name: form.name.trim(),
        domain: form.domain.trim(),
        environment: form.environment,
        budget_type: form.budget_type,
        period: form.period,
        limit_value: parseFloat(form.limit_value),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk-budgets'] })
      setCreating(false)
      setForm(EMPTY_FORM)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { is_active: boolean } }) =>
      riskBudgetsApi.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['risk-budgets'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => riskBudgetsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['risk-budgets'] }),
  })

  const meta = BUDGET_TYPE_META[form.budget_type]
  const canCreate =
    form.name.trim().length >= 2 &&
    form.domain.trim().length >= 1 &&
    !isNaN(parseFloat(form.limit_value)) &&
    parseFloat(form.limit_value) > 0

  // Summary counts
  const exceeded = budgets.filter(
    (b) => b.is_active && b.current_value != null && b.current_value >= b.limit_value
  ).length
  const active = budgets.filter((b) => b.is_active).length

  return (
    <div className="flex flex-col gap-4 p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <ShieldAlert className="h-6 w-6 text-brand-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">Risk Budgets</h1>
            <p className="text-sm text-gray-500">
              {active} active · {exceeded > 0 ? `${exceeded} exceeded` : 'all within limits'}
            </p>
          </div>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Budget
        </button>
      </div>

      {/* Create form */}
      {creating && (
        <div className="shrink-0 rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
          <p className="text-sm font-semibold text-gray-700">New Risk Budget</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Name *</label>
              <input
                autoFocus
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g. Payments squad cost variance"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">Domain / Team *</label>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g. payments, api-gateway"
                value={form.domain}
                onChange={(e) => setForm({ ...form, domain: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">Environment</label>
              <select
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.environment}
                onChange={(e) => setForm({ ...form, environment: e.target.value })}
              >
                {ENVS.map((e) => (
                  <option key={e} value={e}>
                    {e}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">Budget Type</label>
              <select
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.budget_type}
                onChange={(e) => setForm({ ...form, budget_type: e.target.value as BudgetType })}
              >
                {BUDGET_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {BUDGET_TYPE_META[t].label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-400 mt-1">{meta.description}</p>
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">Period</label>
              <select
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.period}
                onChange={(e) => setForm({ ...form, period: e.target.value as BudgetPeriod })}
              >
                {PERIODS.map((p) => (
                  <option key={p} value={p}>
                    {PERIOD_LABEL[p]}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Limit ({meta.unit}) *
              </label>
              <input
                type="number"
                min={0.1}
                step={0.1}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder={form.budget_type === 'change_frequency' ? 'e.g. 10' : 'e.g. 20'}
                value={form.limit_value}
                onChange={(e) => setForm({ ...form, limit_value: e.target.value })}
              />
            </div>
          </div>

          <div className="flex gap-2 pt-1">
            <button
              disabled={!canCreate || createMutation.isPending}
              onClick={() => createMutation.mutate()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? 'Creating…' : 'Create Budget'}
            </button>
            <button
              onClick={() => {
                setCreating(false)
                setForm(EMPTY_FORM)
              }}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-3 shrink-0">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            checked={activeOnly}
            onChange={(e) => setActiveOnly(e.target.checked)}
          />
          <span className="text-sm text-gray-600">Active only</span>
        </label>
        {exceeded > 0 && (
          <div className="flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            {exceeded} budget{exceeded > 1 ? 's' : ''} exceeded
          </div>
        )}
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center text-gray-400">Loading…</div>
      ) : budgets.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-gray-400">
          <ShieldAlert className="h-12 w-12 opacity-20" />
          <p className="text-sm">No risk budgets yet.</p>
          <p className="text-xs text-gray-400 max-w-xs text-center">
            Create a budget to define safe thresholds for deployments, cost variance, and error
            rates per domain and environment.
          </p>
          <button
            onClick={() => setCreating(true)}
            className="mt-2 flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create first budget
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {budgets.map((b) => (
            <BudgetCard
              key={b.id}
              budget={b}
              onToggle={(id, active) => updateMutation.mutate({ id, data: { is_active: active } })}
              onDelete={(id) => {
                if (confirm('Delete this risk budget?')) deleteMutation.mutate(id)
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
