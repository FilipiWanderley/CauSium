import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, AlertCircle, ArrowRight, ExternalLink } from 'lucide-react'
import { useMemo, useState } from 'react'
import { initiativesApi } from '../../api/initiatives'
import { opportunitiesApi } from '../../api/opportunities'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import type { Initiative, InitiativeStatus, Opportunity, RiskLevel } from '../../types'
import clsx from 'clsx'
import { usePersistentString } from '../../hooks/usePersistentBoolean'

const STATUS_TRANSITIONS: Record<InitiativeStatus, InitiativeStatus | null> = {
  backlog: 'planned',
  planned: 'in_progress',
  in_progress: 'review',
  review: 'done',
  done: null,
  cancelled: null,
}

type InitiativeViewMode = 'table' | 'board'

const VIEW_MODES: InitiativeViewMode[] = ['table', 'board']

const STATUS_ORDER: InitiativeStatus[] = ['backlog', 'planned', 'in_progress', 'review', 'done', 'cancelled']

const STATUS_PROGRESS: Record<InitiativeStatus, number> = {
  backlog: 10,
  planned: 30,
  in_progress: 60,
  review: 85,
  done: 100,
  cancelled: 0,
}

const RISK_COLORS: Record<RiskLevel, string> = {
  low: 'bg-emerald-50 text-emerald-700',
  medium: 'bg-amber-50 text-amber-700',
  high: 'bg-red-50 text-red-700',
}

function formatMoney(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDateTime(value: string | null, lang: 'pt' | 'en') {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(lang === 'pt' ? 'pt-BR' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function formatDateOnly(value: string | null, lang: 'pt' | 'en') {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(lang === 'pt' ? 'pt-BR' : 'en-US', {
    dateStyle: 'medium',
  }).format(date)
}

function truncateId(value: string, max = 10) {
  return value.length <= max ? value : `${value.slice(0, max)}…`
}

export function InitiativesPage() {
  usePageTitle('Initiatives')
  const { t, lang } = useI18n()
  const i = t.initiatives
  const queryClient = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newSla, setNewSla] = useState('')
  const [viewModeRaw, setViewModeRaw] = usePersistentString('sp.initiatives.view', 'table')
  const viewMode: InitiativeViewMode = VIEW_MODES.includes(viewModeRaw as InitiativeViewMode)
    ? (viewModeRaw as InitiativeViewMode)
    : 'table'

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
  const { data: opportunities = [] } = useQuery({
    queryKey: ['initiatives', 'opportunities-context'],
    queryFn: () => opportunitiesApi.list({ limit: 200, offset: 0 }).then((r) => r.data.items),
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

  const opportunityById = useMemo(
    () => new Map(opportunities.map((op) => [op.id, op] as const)),
    [opportunities],
  )

  const allInitiatives = useMemo(() => {
    if (!board) return []
    return STATUS_ORDER.flatMap((status) => board[status] ?? [])
  }, [board])

  const statusLabels: Record<InitiativeStatus, string> = {
    backlog: i.backlog,
    planned: i.planned,
    in_progress: i.inProgress,
    review: i.review,
    done: i.done,
    cancelled: i.cancelled,
  }

  const phaseLabels: Record<InitiativeStatus, string> = {
    backlog: i.phaseIntake,
    planned: i.phasePlanning,
    in_progress: i.phaseExecution,
    review: i.phaseValidation,
    done: i.phaseCompleted,
    cancelled: i.phaseCancelled,
  }

  const summary = useMemo(() => {
    const linkedOpportunities = allInitiatives
      .map((initiative) => initiative.opportunity_id)
      .filter((value): value is string => Boolean(value))
    const linkedCount = new Set(linkedOpportunities).size
    const estimatedSavings = allInitiatives.reduce((sum, initiative) => {
      const opportunity = initiative.opportunity_id ? opportunityById.get(initiative.opportunity_id) : undefined
      return sum + (opportunity?.estimated_monthly_savings_usd ?? 0)
    }, 0)
    const realizedSavings = allInitiatives.reduce((sum, initiative) => sum + (initiative.realized_savings_usd ?? 0), 0)
    const overdueCount = allInitiatives.filter((initiative) => initiative.is_overdue).length
    const activeCount = allInitiatives.filter((initiative) =>
      ['planned', 'in_progress', 'review'].includes(initiative.status)
    ).length
    return {
      total: allInitiatives.length,
      linkedCount,
      estimatedSavings,
      realizedSavings,
      overdueCount,
      activeCount,
    }
  }, [allInitiatives, opportunityById])

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{i.title}</h1>
          <p className="text-sm text-gray-500 mt-1">{i.subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 shadow-sm">
            <button
              type="button"
              onClick={() => setViewModeRaw('table')}
              className={clsx(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                viewMode === 'table'
                  ? 'bg-slate-900 text-white'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
              )}
            >
              {i.viewTable}
            </button>
            <button
              type="button"
              onClick={() => setViewModeRaw('board')}
              className={clsx(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                viewMode === 'board'
                  ? 'bg-slate-900 text-white'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
              )}
            >
              {i.viewBoard}
            </button>
          </div>
          <button
            onClick={() => setCreating(true)}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            <Plus className="h-4 w-4" /> {i.newInitiative}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <ExecutionSummaryCard
          label={i.summaryExecutionQueue}
          value={summary.total.toString()}
          subtitle={i.summaryActive.replace('{{count}}', String(summary.activeCount))}
        />
        <ExecutionSummaryCard
          label={i.summaryLinkedOpportunities}
          value={summary.linkedCount.toString()}
          subtitle={i.summaryEstimatedSavings.replace('{{amount}}', formatMoney(summary.estimatedSavings))}
        />
        <ExecutionSummaryCard
          label={i.summaryRealizedSavings}
          value={formatMoney(summary.realizedSavings)}
          subtitle={i.summaryCompleted.replace(
            '{{count}}',
            String(allInitiatives.filter((initiative) => initiative.status === 'done').length),
          )}
        />
        <ExecutionSummaryCard
          label={i.summaryExecutionRisk}
          value={summary.overdueCount.toString()}
          subtitle={summary.overdueCount > 0 ? i.summaryOverdue : i.summaryOnTrack}
          tone={summary.overdueCount > 0 ? 'warning' : 'default'}
        />
      </div>

      {creating && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3">
            <h3 className="text-sm font-semibold text-gray-900">{i.createInitiative}</h3>
            <p className="mt-1 text-xs text-gray-500">{i.createInitiativeHint}</p>
          </div>
          <div className="flex flex-col gap-3 lg:flex-row">
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
            <div className="flex gap-3">
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
        </div>
      )}

      {!allInitiatives.length ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 bg-white p-12 text-center">
          <p className="text-sm font-medium text-gray-700">{i.emptyWorkspaceTitle}</p>
          <p className="mt-1 text-xs text-gray-500">{i.emptyWorkspaceBody}</p>
        </div>
      ) : viewMode === 'table' ? (
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  <th className="px-4 py-3">{i.colInitiative}</th>
                  <th className="hidden px-4 py-3 md:table-cell">{i.colOwner}</th>
                  <th className="hidden px-4 py-3 lg:table-cell">{i.colRelatedOpportunities}</th>
                  <th className="px-4 py-3">{i.colEstimatedSavings}</th>
                  <th className="px-4 py-3">{i.colStatus}</th>
                  <th className="hidden px-4 py-3 lg:table-cell">{i.colPhase}</th>
                  <th className="hidden px-4 py-3 md:table-cell">{i.colRisk}</th>
                  <th className="hidden px-4 py-3 xl:table-cell">{i.colDueDate}</th>
                  <th className="hidden px-4 py-3 xl:table-cell">{i.colLastActivity}</th>
                  <th className="px-4 py-3">{i.colProgress}</th>
                  <th className="px-4 py-3 text-right">{i.colAction}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {allInitiatives.map((initiative) => {
                  const linkedOpportunity = initiative.opportunity_id
                    ? opportunityById.get(initiative.opportunity_id)
                    : undefined
                  const progress = STATUS_PROGRESS[initiative.status]
                  const nextStatus = STATUS_TRANSITIONS[initiative.status]
                  const ownerLabel = initiative.owner_id
                    ? `${i.ownerIdPrefix} ${truncateId(initiative.owner_id, 8)}`
                    : i.ownerUnassigned
                  const estimatedSavings = linkedOpportunity?.estimated_monthly_savings_usd ?? null
                  const risk = linkedOpportunity?.risk_level ?? null

                  return (
                    <tr key={initiative.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 align-top">
                        <div className="min-w-[220px]">
                          <p className="font-medium text-gray-900">{initiative.title}</p>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
                            <span>{initiative.external_ref ?? `${i.initiativeIdPrefix} ${truncateId(initiative.id, 8)}`}</span>
                            {initiative.description && (
                              <>
                                <span className="text-gray-300">•</span>
                                <span className="line-clamp-1">{initiative.description}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 align-top text-gray-700 md:table-cell">{ownerLabel}</td>
                      <td className="hidden px-4 py-3 align-top lg:table-cell">
                        {linkedOpportunity ? (
                          <div className="min-w-[180px]">
                            <p className="text-gray-800">{linkedOpportunity.title}</p>
                            <p className="mt-1 text-xs text-gray-500">{linkedOpportunity.category}</p>
                          </div>
                        ) : (
                          <span className="text-gray-400">{i.noLinkedOpportunity}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-top">
                        {estimatedSavings != null ? (
                          <div>
                            <div className="font-semibold text-emerald-700">{formatMoney(estimatedSavings)}</div>
                            <div className="mt-1 text-xs text-gray-400">{i.estimatedMonthly}</div>
                          </div>
                        ) : (
                          <span className="text-gray-400">{i.notAvailable}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <span className={clsx(
                          'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                          initiative.status === 'done'
                            ? 'bg-emerald-100 text-emerald-700'
                            : initiative.status === 'review'
                              ? 'bg-violet-100 text-violet-700'
                              : initiative.status === 'in_progress'
                                ? 'bg-amber-100 text-amber-700'
                                : initiative.status === 'planned'
                                  ? 'bg-blue-100 text-blue-700'
                                  : initiative.status === 'cancelled'
                                    ? 'bg-gray-100 text-gray-600'
                                    : 'bg-slate-100 text-slate-700',
                        )}>
                          {statusLabels[initiative.status]}
                        </span>
                      </td>
                      <td className="hidden px-4 py-3 align-top text-gray-700 lg:table-cell">
                        {phaseLabels[initiative.status]}
                      </td>
                      <td className="hidden px-4 py-3 align-top md:table-cell">
                        {risk ? (
                          <span className={clsx('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', RISK_COLORS[risk])}>
                            {i[`risk${risk.charAt(0).toUpperCase() + risk.slice(1)}` as 'riskLow' | 'riskMedium' | 'riskHigh']}
                          </span>
                        ) : (
                          <span className="text-gray-400">{i.notAvailable}</span>
                        )}
                      </td>
                      <td className="hidden px-4 py-3 align-top text-gray-500 xl:table-cell">
                        {formatDateOnly(initiative.sla_date, lang === 'pt' ? 'pt' : 'en') ?? i.noDueDate}
                      </td>
                      <td className="hidden px-4 py-3 align-top text-gray-500 xl:table-cell">
                        {formatDateTime(initiative.updated_at, lang === 'pt' ? 'pt' : 'en') ?? i.notAvailable}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="min-w-[120px]">
                          <div className="flex items-center justify-between text-xs text-gray-500">
                            <span>{phaseLabels[initiative.status]}</span>
                            <span>{progress}%</span>
                          </div>
                          <div className="mt-2 h-2 rounded-full bg-gray-100">
                            <div
                              className={clsx(
                                'h-2 rounded-full',
                                initiative.status === 'done'
                                  ? 'bg-emerald-500'
                                  : initiative.status === 'review'
                                    ? 'bg-violet-500'
                                    : initiative.status === 'in_progress'
                                      ? 'bg-amber-500'
                                      : 'bg-slate-500',
                              )}
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top text-right">
                        {nextStatus ? (
                          <button
                            type="button"
                            onClick={() => transitionMutation.mutate({ id: initiative.id, status: nextStatus })}
                            className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:border-gray-400 hover:bg-gray-50"
                          >
                            <ArrowRight className="h-3.5 w-3.5" />
                            {i.advanceAction.replace('{{status}}', statusLabels[nextStatus])}
                          </button>
                        ) : initiative.external_url ? (
                          <a
                            href={initiative.external_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:border-gray-400 hover:bg-gray-50"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            {i.openExternal}
                          </a>
                        ) : (
                          <span className="text-gray-400">{i.noAction}</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {columns.map(({ key, label, color }) => {
            const items = board?.[key] ?? []
            return (
              <div key={key} className="flex-shrink-0 w-80">
                <div className="mb-2 flex items-center justify-between">
                  <div>
                    <span className="text-sm font-semibold text-gray-800">{label}</span>
                    <p className="mt-0.5 text-[11px] text-gray-400">{phaseLabels[key]}</p>
                  </div>
                  <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-600">
                    {items.length}
                  </span>
                </div>
                <div className={clsx('rounded-xl border border-gray-200 p-2.5 space-y-2 min-h-40', color)}>
                  {items.map((item) => (
                    <InitiativeCard
                      key={item.id}
                      initiative={item}
                      linkedOpportunity={item.opportunity_id ? opportunityById.get(item.opportunity_id) : undefined}
                      nextStatus={STATUS_TRANSITIONS[item.status]}
                      onAdvance={(id, status) => transitionMutation.mutate({ id, status })}
                      statusLabel={statusLabels[item.status]}
                      phaseLabel={phaseLabels[item.status]}
                      lang={lang === 'pt' ? 'pt' : 'en'}
                    />
                  ))}
                  {items.length === 0 && (
                    <div className="rounded-lg border border-dashed border-gray-200 bg-white/60 px-3 py-6 text-center">
                      <p className="text-xs font-medium text-gray-500">{i.emptyPhaseTitle.replace('{{phase}}', label)}</p>
                      <p className="mt-1 text-[11px] text-gray-400">{i.emptyPhaseBody}</p>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function ExecutionSummaryCard({
  label,
  value,
  subtitle,
  tone = 'default',
}: {
  label: string
  value: string
  subtitle: string
  tone?: 'default' | 'warning'
}) {
  return (
    <div className={clsx(
      'rounded-xl border bg-white p-4 shadow-sm',
      tone === 'warning' ? 'border-amber-200' : 'border-gray-200',
    )}>
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className={clsx('mt-2 text-2xl font-semibold', tone === 'warning' ? 'text-amber-700' : 'text-gray-900')}>
        {value}
      </p>
      <p className="mt-1 text-xs text-gray-500">{subtitle}</p>
    </div>
  )
}

function InitiativeCard({
  initiative,
  linkedOpportunity,
  nextStatus,
  onAdvance,
  statusLabel,
  phaseLabel,
  lang,
}: {
  initiative: Initiative
  linkedOpportunity?: Opportunity
  nextStatus: InitiativeStatus | null
  onAdvance: (id: string, status: string) => void
  statusLabel: string
  phaseLabel: string
  lang: 'pt' | 'en'
}) {
  const { t } = useI18n()
  const i = t.initiatives
  const statusLabels: Partial<Record<InitiativeStatus, string>> = {
    backlog: i.backlog,
    planned: i.planned,
    in_progress: i.inProgress,
    review: i.review,
    done: i.done,
    cancelled: i.cancelled,
  }
  const progress = STATUS_PROGRESS[initiative.status]
  const ownerLabel = initiative.owner_id ? `${i.ownerIdPrefix} ${truncateId(initiative.owner_id, 8)}` : i.ownerUnassigned
  const dueDateLabel = formatDateOnly(initiative.sla_date, lang)
  const lastActivityLabel = formatDateTime(initiative.updated_at, lang)
  return (
    <div className="rounded-xl border border-white bg-white p-3.5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2 min-w-0">
        {initiative.is_overdue && (
          <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-500 mt-0.5" />
        )}
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-900 leading-snug">{initiative.title}</p>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
              <span>{phaseLabel}</span>
              <span className="text-gray-300">•</span>
              <span>{ownerLabel}</span>
            </div>
          </div>
        </div>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
          {statusLabel}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-gray-50 px-3 py-2">
          <p className="text-gray-400">{i.colEstimatedSavings}</p>
          <p className="mt-1 font-semibold text-emerald-700">
            {linkedOpportunity ? formatMoney(linkedOpportunity.estimated_monthly_savings_usd) : i.notAvailable}
          </p>
        </div>
        <div className="rounded-lg bg-gray-50 px-3 py-2">
          <p className="text-gray-400">{i.colDueDate}</p>
          <p className={clsx('mt-1 font-medium', initiative.is_overdue ? 'text-red-600' : 'text-gray-700')}>
            {dueDateLabel ?? i.noDueDate}
          </p>
        </div>
      </div>

      <div className="mt-3 space-y-1.5 text-[11px] text-gray-500">
        <div className="flex items-center justify-between gap-3">
          <span>{i.colRelatedOpportunities}</span>
          <span className="truncate text-right text-gray-700">
            {linkedOpportunity?.title ?? i.noLinkedOpportunity}
          </span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span>{i.colLastActivity}</span>
          <span className="text-gray-700">{lastActivityLabel ?? i.notAvailable}</span>
        </div>
      </div>

      <div className="mt-3">
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{i.colProgress}</span>
          <span>{progress}%</span>
        </div>
        <div className="mt-1.5 h-1.5 rounded-full bg-gray-100">
          <div
            className={clsx(
              'h-1.5 rounded-full',
              initiative.status === 'done'
                ? 'bg-emerald-500'
                : initiative.status === 'review'
                  ? 'bg-violet-500'
                  : initiative.status === 'in_progress'
                    ? 'bg-amber-500'
                    : 'bg-slate-500',
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {nextStatus && (
        <button
          onClick={() => onAdvance(initiative.id, nextStatus)}
          className="mt-3 inline-flex w-full items-center justify-center gap-1 rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
        >
          <ArrowRight className="h-3.5 w-3.5" />
          {i.moveTo.replace('{{status}}', statusLabels[nextStatus] ?? nextStatus.replace('_', ' '))}
        </button>
      )}
    </div>
  )
}
