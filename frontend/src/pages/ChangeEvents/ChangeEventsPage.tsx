import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Activity, AlertTriangle, TrendingUp, Zap, Settings, RefreshCw, DollarSign } from 'lucide-react'
import { useState } from 'react'
import { changeEventsApi } from '../../api/changeEvents'
import type { ChangeEvent, ChangeEventType } from '../../types'
import clsx from 'clsx'

const EVENT_TYPE_META: Record<
  ChangeEventType,
  { label: string; color: string; Icon: React.ElementType }
> = {
  deploy: { label: 'Deploy', color: 'bg-blue-100 text-blue-700', Icon: RefreshCw },
  config_change: { label: 'Config Change', color: 'bg-purple-100 text-purple-700', Icon: Settings },
  scaling: { label: 'Scaling', color: 'bg-indigo-100 text-indigo-700', Icon: TrendingUp },
  incident: { label: 'Incident', color: 'bg-red-100 text-red-700', Icon: AlertTriangle },
  cost_anomaly: { label: 'Cost Anomaly', color: 'bg-orange-100 text-orange-700', Icon: DollarSign },
  policy_change: { label: 'Policy Change', color: 'bg-gray-100 text-gray-700', Icon: Zap },
}

const ALL_TYPES: ChangeEventType[] = [
  'deploy',
  'config_change',
  'scaling',
  'incident',
  'cost_anomaly',
  'policy_change',
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function EventRow({ ev }: { ev: ChangeEvent }) {
  const meta = EVENT_TYPE_META[ev.event_type]

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3 whitespace-nowrap">
        <span className={clsx('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium', meta.color)}>
          <meta.Icon className="h-3 w-3" />
          {meta.label}
        </span>
      </td>
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-gray-800">{ev.title}</p>
        {ev.description && (
          <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{ev.description}</p>
        )}
      </td>
      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">{ev.service ?? '—'}</td>
      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">{ev.environment}</td>
      <td className="px-4 py-3 whitespace-nowrap text-sm">
        {ev.cost_impact_usd != null ? (
          <span className={clsx('font-semibold', ev.cost_impact_usd > 0 ? 'text-red-600' : 'text-green-600')}>
            {ev.cost_impact_usd > 0 ? '+' : ''}${ev.cost_impact_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
      <td className="px-4 py-3 whitespace-nowrap text-sm">
        {ev.causal_confidence != null ? (
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-16 rounded-full bg-gray-200">
              <div
                className="h-1.5 rounded-full bg-brand-500"
                style={{ width: `${Math.round(ev.causal_confidence * 100)}%` }}
              />
            </div>
            <span className="text-xs text-gray-500">{Math.round(ev.causal_confidence * 100)}%</span>
          </div>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-400">
        {formatDate(ev.occurred_at)}
      </td>
    </tr>
  )
}

export function ChangeEventsPage() {
  const queryClient = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [filterType, setFilterType] = useState<ChangeEventType | ''>('')
  const [form, setForm] = useState({
    event_type: 'deploy' as ChangeEventType,
    title: '',
    service: '',
    environment: 'production',
    occurred_at: new Date().toISOString().slice(0, 16),
    cost_impact_usd: '',
    description: '',
  })

  const { data: events = [], isLoading } = useQuery({
    queryKey: ['change-events', filterType],
    queryFn: () =>
      changeEventsApi
        .list({ event_type: filterType || undefined, limit: 200 })
        .then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      changeEventsApi.create({
        event_type: form.event_type,
        title: form.title.trim(),
        service: form.service.trim() || undefined,
        environment: form.environment,
        occurred_at: new Date(form.occurred_at).toISOString(),
        cost_impact_usd: form.cost_impact_usd ? parseFloat(form.cost_impact_usd) : undefined,
        description: form.description.trim() || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['change-events'] })
      setCreating(false)
      setForm({ ...form, title: '', service: '', description: '', cost_impact_usd: '' })
    },
  })

  const filtered = filterType ? events.filter((e) => e.event_type === filterType) : events

  return (
    <div className="flex flex-col gap-4 p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Activity className="h-6 w-6 text-brand-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">Change Events</h1>
            <p className="text-sm text-gray-500">
              {events.length} events — deploy, config, incidents, cost anomalies
            </p>
          </div>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Log Event
        </button>
      </div>

      {/* Create form */}
      {creating && (
        <div className="shrink-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-3">
          <p className="text-sm font-semibold text-gray-700">Log Change Event</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Type *</label>
              <select
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.event_type}
                onChange={(e) => setForm({ ...form, event_type: e.target.value as ChangeEventType })}
              >
                {ALL_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {EVENT_TYPE_META[t].label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Environment</label>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.environment}
                onChange={(e) => setForm({ ...form, environment: e.target.value })}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Title *</label>
              <input
                autoFocus
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="Describe what changed"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Service</label>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g. api-gateway"
                value={form.service}
                onChange={(e) => setForm({ ...form, service: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Cost Impact (USD)</label>
              <input
                type="number"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g. 1500 or -500"
                value={form.cost_impact_usd}
                onChange={(e) => setForm({ ...form, cost_impact_usd: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Occurred At *</label>
              <input
                type="datetime-local"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.occurred_at}
                onChange={(e) => setForm({ ...form, occurred_at: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Description</label>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="Optional notes"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-2 pt-1">
            <button
              disabled={form.title.trim().length < 3 || createMutation.isPending}
              onClick={() => createMutation.mutate()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? 'Saving…' : 'Save Event'}
            </button>
            <button
              onClick={() => setCreating(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2 shrink-0">
        <button
          onClick={() => setFilterType('')}
          className={clsx(
            'rounded-full px-3 py-1 text-xs font-medium border transition-colors',
            filterType === ''
              ? 'bg-brand-600 text-white border-brand-600'
              : 'border-gray-300 text-gray-600 hover:bg-gray-50'
          )}
        >
          All
        </button>
        {ALL_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => setFilterType(filterType === t ? '' : t)}
            className={clsx(
              'rounded-full px-3 py-1 text-xs font-medium border transition-colors',
              filterType === t
                ? 'bg-brand-600 text-white border-brand-600'
                : 'border-gray-300 text-gray-600 hover:bg-gray-50'
            )}
          >
            {EVENT_TYPE_META[t].label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center text-gray-400">Loading…</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-gray-400">
          <Activity className="h-10 w-10 opacity-30" />
          <p className="text-sm">No change events yet. Log the first one.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Type</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Title</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Service</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Env</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Cost Impact</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Causal Conf.</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Occurred</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((ev) => (
                <EventRow key={ev.id} ev={ev} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
