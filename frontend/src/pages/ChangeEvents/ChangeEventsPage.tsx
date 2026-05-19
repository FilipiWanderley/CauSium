import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Activity, AlertTriangle, TrendingUp, Zap, Settings, RefreshCw, DollarSign } from 'lucide-react'
import { useState } from 'react'
import { changeEventsApi } from '../../api/changeEvents'
import type { ChangeEvent, ChangeEventType } from '../../types'
import clsx from 'clsx'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { formatDateFull } from '../../utils/format'

const ALL_TYPES: ChangeEventType[] = [
  'deploy',
  'config_change',
  'scaling',
  'incident',
  'cost_anomaly',
  'policy_change',
]

function formatDate(iso: string) {
  return formatDateFull(iso)
}

function EventRow({ ev, typeMeta }: {
  ev: ChangeEvent
  typeMeta: { label: string; color: string; Icon: React.ElementType }
}) {
  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3 whitespace-nowrap">
        <span className={clsx('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium', typeMeta.color)}>
          <typeMeta.Icon className="h-3 w-3" />
          {typeMeta.label}
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
  usePageTitle('Change Events')
  const { t } = useI18n()
  const ce = t.changeEvents
  const common = t.common

  const EVENT_TYPE_META: Record<ChangeEventType, { label: string; color: string; Icon: React.ElementType }> = {
    deploy: { label: ce.deploy, color: 'bg-blue-100 text-blue-700', Icon: RefreshCw },
    config_change: { label: ce.configChange, color: 'bg-purple-100 text-purple-700', Icon: Settings },
    scaling: { label: ce.scaling, color: 'bg-indigo-100 text-indigo-700', Icon: TrendingUp },
    incident: { label: ce.incident, color: 'bg-red-100 text-red-700', Icon: AlertTriangle },
    cost_anomaly: { label: ce.costAnomaly, color: 'bg-orange-100 text-orange-700', Icon: DollarSign },
    policy_change: { label: ce.policyChange, color: 'bg-gray-100 text-gray-700', Icon: Zap },
  }

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
        .then((r) => r.data.items),
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
            <h1 className="text-xl font-bold text-gray-900">{ce.title}</h1>
            <p className="text-sm text-gray-500">
              {events.length} {ce.subtitle}
            </p>
          </div>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          {ce.logEvent}
        </button>
      </div>

      {/* Create form */}
      {creating && (
        <div className="shrink-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-3">
          <p className="text-sm font-semibold text-gray-700">{ce.logEventTitle}</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">{ce.type} *</label>
              <select
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.event_type}
                onChange={(e) => setForm({ ...form, event_type: e.target.value as ChangeEventType })}
              >
                {ALL_TYPES.map((tp) => (
                  <option key={tp} value={tp}>
                    {EVENT_TYPE_META[tp].label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{ce.environment}</label>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.environment}
                onChange={(e) => setForm({ ...form, environment: e.target.value })}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">{ce.titleLabel} *</label>
              <input
                autoFocus
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder={ce.titleDesc}
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{ce.service}</label>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder={ce.servicePlaceholder}
                value={form.service}
                onChange={(e) => setForm({ ...form, service: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{ce.costImpact}</label>
              <input
                type="number"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder={ce.costImpactPlaceholder}
                value={form.cost_impact_usd}
                onChange={(e) => setForm({ ...form, cost_impact_usd: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{ce.occurredAt} *</label>
              <input
                type="datetime-local"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.occurred_at}
                onChange={(e) => setForm({ ...form, occurred_at: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{ce.description}</label>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder={ce.descriptionPlaceholder}
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
              {createMutation.isPending ? `${ce.saveEvent}…` : ce.saveEvent}
            </button>
            <button
              onClick={() => setCreating(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              {common.cancel}
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
          {ce.all}
        </button>
        {ALL_TYPES.map((tp) => (
          <button
            key={tp}
            onClick={() => setFilterType(filterType === tp ? '' : tp)}
            className={clsx(
              'rounded-full px-3 py-1 text-xs font-medium border transition-colors',
              filterType === tp
                ? 'bg-brand-600 text-white border-brand-600'
                : 'border-gray-300 text-gray-600 hover:bg-gray-50'
            )}
          >
            {EVENT_TYPE_META[tp].label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center text-gray-400">{common.loading}…</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-gray-400">
          <Activity className="h-10 w-10 opacity-30" />
          <p className="text-sm">{ce.noEvents}</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">{ce.colType}</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">{ce.colTitle}</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">{ce.colService}</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">{ce.colEnv}</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">{ce.colCostImpact}</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">{ce.colCausalConf}</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">{ce.colOccurred}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((ev) => (
                <EventRow key={ev.id} ev={ev} typeMeta={EVENT_TYPE_META[ev.event_type]} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
