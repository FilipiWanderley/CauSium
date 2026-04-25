import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, AlertCircle } from 'lucide-react'
import { useState } from 'react'
import { initiativesApi } from '../../api/initiatives'
import { useI18n } from '../../contexts/I18nContext'
import type { Initiative, InitiativeStatus } from '../../types'
import clsx from 'clsx'

const STATUS_TRANSITIONS: Record<InitiativeStatus, InitiativeStatus | null> = {
  backlog: 'planned',
  planned: 'in_progress',
  in_progress: 'review',
  review: 'done',
  done: null,
  cancelled: null,
}

export function InitiativesPage() {
  const { t } = useI18n()
  const i = t.initiatives
  const queryClient = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newSla, setNewSla] = useState('')

  const columns: { key: InitiativeStatus; label: string; color: string }[] = [
    { key: 'backlog', label: i.backlog, color: 'bg-gray-100' },
    { key: 'planned', label: i.planned, color: 'bg-blue-50' },
    { key: 'in_progress', label: i.inProgress, color: 'bg-yellow-50' },
    { key: 'review', label: i.review, color: 'bg-purple-50' },
    { key: 'done', label: i.done, color: 'bg-green-50' },
  ]

  const { data: board, isLoading } = useQuery({
    queryKey: ['initiatives', 'board'],
    queryFn: () => initiativesApi.board().then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: { title: string; sla_date?: string }) =>
      initiativesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['initiatives'] })
      setCreating(false)
      setNewTitle('')
      setNewSla('')
    },
  })

  const transitionMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      initiativesApi.transition(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['initiatives'] }),
  })

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{i.title}</h1>
          <p className="text-sm text-gray-500 mt-1">{i.subtitle}</p>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          <Plus className="h-4 w-4" /> {i.newInitiative}
        </button>
      </div>

      {creating && (
        <div className="rounded-xl border border-brand-200 bg-blue-50 p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3">{i.createInitiative}</h3>
          <div className="flex gap-3">
            <input
              autoFocus
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder={i.titlePlaceholder}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
            <div className="flex flex-col gap-1">
              <label htmlFor="initiative-sla-date" className="text-xs font-medium text-gray-600">
                {i.sla.replace('{{date}}', '').trim()}
              </label>
              <input
                id="initiative-sla-date"
                type="date"
                value={newSla}
                onChange={(e) => setNewSla(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
            </div>
            <button
              onClick={() => createMutation.mutate({ title: newTitle, sla_date: newSla || undefined })}
              disabled={!newTitle}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {i.create}
            </button>
            <button
              onClick={() => setCreating(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              {i.cancel}
            </button>
          </div>
        </div>
      )}

      <div className="flex gap-4 overflow-x-auto pb-4">
        {columns.map(({ key, label, color }) => {
          const items = board?.[key] ?? []
          return (
            <div key={key} className="flex-shrink-0 w-72">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700">{label}</span>
                <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-600">
                  {items.length}
                </span>
              </div>
              <div className={clsx('rounded-xl p-2 space-y-2 min-h-32', color)}>
                {items.map((item) => (
                  <InitiativeCard
                    key={item.id}
                    initiative={item}
                    nextStatus={STATUS_TRANSITIONS[item.status]}
                    onAdvance={(id, status) => transitionMutation.mutate({ id, status })}
                  />
                ))}
                {items.length === 0 && (
                  <p className="py-4 text-center text-xs text-gray-400">{i.empty}</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function InitiativeCard({
  initiative,
  nextStatus,
  onAdvance,
}: {
  initiative: Initiative
  nextStatus: InitiativeStatus | null
  onAdvance: (id: string, status: string) => void
}) {
  const { t } = useI18n()
  const i = t.initiatives
  const statusLabel: Partial<Record<InitiativeStatus, string>> = {
    backlog: i.backlog,
    planned: i.planned,
    in_progress: i.inProgress,
    review: i.review,
    done: i.done,
  }
  return (
    <div className="rounded-lg border border-white bg-white p-3 shadow-sm">
      <div className="flex items-start gap-2">
        {initiative.is_overdue && (
          <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-500 mt-0.5" />
        )}
        <p className="text-sm font-medium text-gray-900 flex-1 leading-snug">{initiative.title}</p>
      </div>
      {initiative.sla_date && (
        <p className={clsx('mt-1 text-xs', initiative.is_overdue ? 'text-red-500 font-medium' : 'text-gray-400')}>
          {i.sla.replace('{{date}}', initiative.sla_date)}
          {initiative.is_overdue && ` · ${i.overdue}`}
        </p>
      )}
      {nextStatus && (
        <button
          onClick={() => onAdvance(initiative.id, nextStatus)}
          className="mt-2 w-full rounded bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 border border-gray-200 transition-colors"
        >
          {i.moveTo.replace('{{status}}', statusLabel[nextStatus] ?? nextStatus.replace('_', ' '))}
        </button>
      )}
    </div>
  )
}
