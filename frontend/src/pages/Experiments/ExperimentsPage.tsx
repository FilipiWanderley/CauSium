import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, FlaskConical, ChevronRight, X } from 'lucide-react'
import { useState } from 'react'
import { experimentsApi } from '../../api/experiments'
import { useI18n } from '../../contexts/I18nContext'
import type { Experiment, ExperimentStatus } from '../../types'
import clsx from 'clsx'

const NEXT_STATUS: Partial<Record<ExperimentStatus, ExperimentStatus>> = {
  draft: 'hypothesis',
  hypothesis: 'simulating',
  simulating: 'approved',
  approved: 'running',
  running: 'measuring',
  measuring: 'concluded',
}

const OUTCOME_BADGE: Record<string, string> = {
  improved: 'bg-green-100 text-green-700',
  regressed: 'bg-red-100 text-red-700',
  inconclusive: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-gray-100 text-gray-500',
}

function fmt(n: number | null | undefined, prefix = '$') {
  if (n == null) return '—'
  return `${prefix}${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
}

function ExperimentCard({
  exp,
  onAdvance,
  onCancel,
}: {
  exp: Experiment
  onAdvance: (id: string, to: ExperimentStatus) => void
  onCancel: (id: string) => void
}) {
  const { t } = useI18n()
  const e = t.experiments
  const next = NEXT_STATUS[exp.status]

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm space-y-2">
      <p className="text-sm font-medium text-gray-800 leading-snug">{exp.title}</p>

      {exp.simulated_savings_usd != null && (
        <p className="text-xs text-gray-500">
          {e.simSavings}{' '}
          <span className="font-semibold text-green-600">{fmt(exp.simulated_savings_usd)}</span>
          {exp.simulated_confidence != null && (
            <span className="ml-1 text-gray-400">
              ({Math.round(exp.simulated_confidence * 100)}% conf)
            </span>
          )}
        </p>
      )}

      {exp.actual_savings_usd != null && (
        <p className="text-xs text-gray-500">
          {e.actualSavings}{' '}
          <span className="font-semibold text-green-700">{fmt(exp.actual_savings_usd)}</span>
        </p>
      )}

      {exp.outcome && (
        <span
          className={clsx(
            'inline-block rounded-full px-2 py-0.5 text-xs font-medium',
            OUTCOME_BADGE[exp.outcome] ?? 'bg-gray-100 text-gray-600'
          )}
        >
          {(e as Record<string, string>)[exp.outcome] ?? exp.outcome}
        </span>
      )}

      {exp.status !== 'concluded' && exp.status !== 'cancelled' && (
        <div className="flex gap-1 pt-1">
          {next && (
            <button
              onClick={() => onAdvance(exp.id, next)}
              className="flex items-center gap-1 rounded px-2 py-1 text-xs bg-brand-600 text-white hover:bg-brand-700 transition-colors"
            >
              <ChevronRight className="h-3 w-3" />
              {next.charAt(0).toUpperCase() + next.slice(1)}
            </button>
          )}
          <button
            onClick={() => onCancel(exp.id)}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs bg-gray-100 text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors"
          >
            <X className="h-3 w-3" />
            {t.common.cancel}
          </button>
        </div>
      )}
    </div>
  )
}

export function ExperimentsPage() {
  const { t } = useI18n()
  const e = t.experiments
  const queryClient = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newHypothesis, setNewHypothesis] = useState('')

  const columns: { key: ExperimentStatus; label: string; color: string; dot: string }[] = [
    { key: 'draft', label: e.draft, color: 'bg-gray-50 border-gray-200', dot: 'bg-gray-400' },
    { key: 'hypothesis', label: e.hypothesis, color: 'bg-blue-50 border-blue-200', dot: 'bg-blue-400' },
    { key: 'simulating', label: e.simulating, color: 'bg-purple-50 border-purple-200', dot: 'bg-purple-400' },
    { key: 'approved', label: e.approved, color: 'bg-indigo-50 border-indigo-200', dot: 'bg-indigo-400' },
    { key: 'running', label: e.running, color: 'bg-yellow-50 border-yellow-200', dot: 'bg-yellow-400' },
    { key: 'measuring', label: e.measuring, color: 'bg-orange-50 border-orange-200', dot: 'bg-orange-400' },
    { key: 'concluded', label: e.concluded, color: 'bg-green-50 border-green-200', dot: 'bg-green-500' },
  ]

  const { data: experiments = [], isLoading } = useQuery({
    queryKey: ['experiments'],
    queryFn: () => experimentsApi.list({ limit: 200 }).then((r) => r.data.items),
  })

  const { data: summary } = useQuery({
    queryKey: ['experiments', 'summary'],
    queryFn: () => experimentsApi.summary().then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: { title: string; hypothesis?: string }) =>
      experimentsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
      setCreating(false)
      setNewTitle('')
      setNewHypothesis('')
    },
  })

  const transitionMutation = useMutation({
    mutationFn: ({ id, to_status }: { id: string; to_status: ExperimentStatus }) =>
      experimentsApi.transition(id, to_status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['experiments'] }),
  })

  const byStatus = columns.reduce(
    (acc, col) => {
      acc[col.key] = experiments.filter((ex) => ex.status === col.key)
      return acc
    },
    {} as Record<ExperimentStatus, Experiment[]>
  )

  return (
    <div className="flex h-full flex-col gap-4 p-6 overflow-hidden">
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <FlaskConical className="h-6 w-6 text-brand-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">{e.title}</h1>
            <p className="text-sm text-gray-500">
              {summary
                ? `${summary.total} experiments · $${(summary.total_actual_savings_usd ?? 0).toLocaleString()} realized`
                : e.subtitle}
            </p>
          </div>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          {e.newExperiment}
        </button>
      </div>

      {creating && (
        <div className="shrink-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-3">
          <p className="text-sm font-semibold text-gray-700">{e.newExperiment}</p>
          <input
            autoFocus
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder={e.titleLabel}
            value={newTitle}
            onChange={(ev) => setNewTitle(ev.target.value)}
          />
          <textarea
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder={e.hypothesis}
            rows={2}
            value={newHypothesis}
            onChange={(ev) => setNewHypothesis(ev.target.value)}
          />
          <div className="flex gap-2">
            <button
              disabled={newTitle.trim().length < 3 || createMutation.isPending}
              onClick={() =>
                createMutation.mutate({
                  title: newTitle.trim(),
                  hypothesis: newHypothesis.trim() || undefined,
                })
              }
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? `${e.create}…` : e.create}
            </button>
            <button
              onClick={() => { setCreating(false); setNewTitle(''); setNewHypothesis('') }}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              {e.cancel}
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center text-gray-400">{e.loading}</div>
      ) : (
        <div className="flex flex-1 gap-3 overflow-x-auto pb-2">
          {columns.map((col) => (
            <div
              key={col.key}
              className={clsx('flex w-56 shrink-0 flex-col rounded-xl border p-3 gap-2', col.color)}
            >
              <div className="flex items-center gap-2 shrink-0">
                <span className={clsx('h-2 w-2 rounded-full', col.dot)} />
                <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  {col.label}
                </span>
                <span className="ml-auto text-xs text-gray-400">
                  {byStatus[col.key]?.length ?? 0}
                </span>
              </div>
              <div className="flex flex-col gap-2 overflow-y-auto">
                {(byStatus[col.key] ?? []).map((exp) => (
                  <ExperimentCard
                    key={exp.id}
                    exp={exp}
                    onAdvance={(id, to_status) => transitionMutation.mutate({ id, to_status })}
                    onCancel={(id) => transitionMutation.mutate({ id, to_status: 'cancelled' })}
                  />
                ))}
                {(byStatus[col.key] ?? []).length === 0 && (
                  <p className="text-center text-xs text-gray-400 py-4">{e.noExperiments}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
