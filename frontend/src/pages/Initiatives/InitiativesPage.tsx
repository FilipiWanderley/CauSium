import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  AlertCircle,
  ArrowRight,
  ExternalLink,
  CalendarClock,
  User,
  ShieldAlert,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { initiativesApi } from '../../api/initiatives'
import { opportunitiesApi } from '../../api/opportunities'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import type { Initiative, InitiativeStatus, Opportunity, RiskLevel } from '../../types'
import clsx from 'clsx'
import { usePersistentString } from '../../hooks/usePersistentBoolean'
import { PageHeader } from '../../components/Layout/PageHeader'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { KpiCard } from '../../components/Cards/KpiCard'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { SkeletonMetricCards, SkeletonSection, SkeletonTable } from '../../components/UX/Skeleton'
import { formatCurrency } from '../../utils/currency'

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
const ACTIVE_STATUSES: InitiativeStatus[] = ['planned', 'in_progress', 'review']
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

const STATUS_BADGES: Record<InitiativeStatus, string> = {
  backlog: 'bg-slate-100 text-slate-700',
  planned: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  review: 'bg-violet-100 text-violet-700',
  done: 'bg-emerald-100 text-emerald-700',
  cancelled: 'bg-gray-100 text-gray-600',
}

function formatUsd(value: number) {
  return formatCurrency(value, 'USD')
}

function formatDateTime(value: string | null) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function formatDateOnly(value: string | null) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
  }).format(date)
}

function truncateId(value: string, max = 10) {
  return value.length <= max ? value : `${value.slice(0, max)}…`
}

function progressBarClass(status: InitiativeStatus) {
  if (status === 'done') return 'bg-emerald-500'
  if (status === 'review') return 'bg-violet-500'
  if (status === 'in_progress') return 'bg-amber-500'
  if (status === 'planned') return 'bg-blue-500'
  return 'bg-slate-500'
}

export function InitiativesPage() {
  usePageTitle('Initiatives')
  const { t } = useI18n()
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

  const { data: board, isLoading, isError, refetch } = useQuery({
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
    const activeCount = allInitiatives.filter((initiative) => ACTIVE_STATUSES.includes(initiative.status)).length
    const completedCount = allInitiatives.filter((initiative) => initiative.status === 'done').length
    return {
      total: allInitiatives.length,
      linkedCount,
      estimatedSavings,
      realizedSavings,
      overdueCount,
      activeCount,
      completedCount,
    }
  }, [allInitiatives, opportunityById])

  if (isLoading) {
    return (
      <div className="page-container">
        <PageHeader
          title={i.title}
          subtitle={i.subtitle}
          actions={
            <div className="flex items-center gap-2">
              <div className="inline-flex rounded-md border border-slate-200 bg-slate-50 p-0.5">
                <span className="rounded px-2.5 py-1 text-xs font-medium text-slate-500">{i.viewTable}</span>
                <span className="rounded px-2.5 py-1 text-xs font-medium text-slate-500">{i.viewBoard}</span>
              </div>
              <button
                type="button"
                disabled
                className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white opacity-70"
              >
                <Plus className="h-4 w-4" /> {i.newInitiative}
              </button>
            </div>
          }
          meta={
            <>
              <span>Execution workspace</span>
              <span>Expected and realized value shown as USD</span>
            </>
          }
        />
        <SectionIntro
          title="Execution workspace"
          subtitle="Track workload, ownership, urgency, expected value, realized value, and next actions without changing the existing initiative workflow."
          badges={[
            { label: 'Workflow preserved', tone: 'secondary' },
            { label: 'Board and table parity', tone: 'operational' },
            { label: 'USD-backed savings fields', tone: 'billing' },
          ]}
          compact
        />
        <SkeletonMetricCards count={4} />
        <SkeletonSection lines={3} />
        <SkeletonTable rows={6} columns={7} />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="page-container">
        <PageHeader
          title={i.title}
          subtitle={i.subtitle}
          meta={
            <>
              <span>Execution workspace</span>
              <span>Expected and realized value shown as USD</span>
            </>
          }
        />
        <SectionIntro
          title="Execution workspace"
          subtitle="Track workload, ownership, urgency, expected value, realized value, and next actions without changing the existing initiative workflow."
          badges={[
            { label: 'Workflow preserved', tone: 'secondary' },
            { label: 'Board and table parity', tone: 'operational' },
            { label: 'USD-backed savings fields', tone: 'billing' },
          ]}
          compact
        />
        <ErrorState
          title="Could not load initiatives"
          description="The execution workspace is temporarily unavailable. Please try again."
          onRetry={() => refetch()}
          retryLabel="Retry"
        />
      </div>
    )
  }

  return (
    <div className="page-container">
      <PageHeader
        title={i.title}
        subtitle={i.subtitle}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-md border border-slate-200 bg-slate-50 p-0.5">
              <button
                type="button"
                onClick={() => setViewModeRaw('table')}
                className={clsx(
                  'rounded px-2.5 py-1 text-xs font-medium transition-all',
                  viewMode === 'table'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700',
                )}
              >
                {i.viewTable}
              </button>
              <button
                type="button"
                onClick={() => setViewModeRaw('board')}
                className={clsx(
                  'rounded px-2.5 py-1 text-xs font-medium transition-all',
                  viewMode === 'board'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700',
                )}
              >
                {i.viewBoard}
              </button>
            </div>
            <button
              onClick={() => setCreating(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              <Plus className="h-4 w-4" /> {i.newInitiative}
            </button>
          </div>
        }
        meta={
          <>
            <span>{summary.total} initiatives</span>
            <span>{summary.activeCount} active</span>
            <span>{summary.overdueCount} overdue</span>
            <span>Expected and realized value shown as USD</span>
          </>
        }
      />

      <SectionIntro
        title="Execution workspace"
        subtitle="Review workload, ownership, urgency, expected value, realized value, and next actions from one controlled execution surface."
        badges={[
          { label: 'Workflow preserved', tone: 'secondary' },
          { label: 'Board and table parity', tone: 'operational' },
          { label: 'USD-backed savings fields', tone: 'billing' },
        ]}
        compact
      />

      <div className="kpi-grid">
        <KpiCard
          title="Execution queue"
          value={summary.total}
          tone="neutral"
          footer={<span>{summary.activeCount} active initiatives in flight</span>}
        />
        <KpiCard
          title="Linked value (USD)"
          value={formatUsd(summary.estimatedSavings)}
          tone="positive"
          footer={<span>{summary.linkedCount} linked opportunities contributing expected monthly value</span>}
        />
        <KpiCard
          title="Realized value (USD)"
          value={formatUsd(summary.realizedSavings)}
          tone="positive"
          footer={<span>{summary.completedCount} completed initiatives contributing realized savings to date</span>}
        />
        <KpiCard
          title="Execution risk"
          value={summary.overdueCount}
          tone={summary.overdueCount > 0 ? 'warning' : 'neutral'}
          footer={<span>{summary.overdueCount > 0 ? 'Overdue initiatives need attention' : 'No overdue initiatives right now'}</span>}
        />
      </div>

      {creating && (
        <Panel>
          <PanelHeader
            title={i.createInitiative}
            subtitle="Capture a new execution item without changing the current initiative workflow or board model."
          />
          <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-end">
            <div className="flex-1">
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-400">
                Initiative title
              </label>
              <input
                autoFocus
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder={i.titlePlaceholder}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none"
              />
            </div>
            <div className="lg:w-56">
              <label htmlFor="initiative-sla-date" className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-400">
                Due date
              </label>
              <input
                id="initiative-sla-date"
                type="date"
                value={newSla}
                onChange={(e) => setNewSla(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => createMutation.mutate({ title: newTitle, sla_date: newSla || undefined })}
                disabled={!newTitle || createMutation.isPending}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {createMutation.isPending ? 'Creating...' : i.create}
              </button>
              <button
                onClick={() => setCreating(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
              >
                {i.cancel}
              </button>
            </div>
          </div>
        </Panel>
      )}

      {!allInitiatives.length ? (
        <EmptyState
          icon="document"
          title={i.emptyWorkspaceTitle}
          description={i.emptyWorkspaceBody}
          action={{ label: i.newInitiative, onClick: () => setCreating(true) }}
        />
      ) : viewMode === 'table' ? (
        <Panel flush className="overflow-hidden">
          <div className="border-b border-slate-100 p-5">
            <PanelHeader
              title="Execution table"
              subtitle="Scan ownership, urgency, value delivery, and the next workflow action across the full initiative queue."
              actions={
                <div className="text-right text-xs text-slate-500">
                  <div className="font-medium text-slate-700">{summary.activeCount} active</div>
                  <div>{summary.overdueCount} overdue</div>
                </div>
              }
            />
          </div>
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
                    <tr
                      key={initiative.id}
                      className={clsx(
                        'hover:bg-slate-50',
                        initiative.is_overdue && 'bg-rose-50/40',
                      )}
                    >
                      <td className="px-4 py-3 align-top">
                        <div className="min-w-[240px]">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-medium text-gray-900">{initiative.title}</p>
                            {initiative.is_overdue && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-700">
                                <AlertCircle className="h-3 w-3" />
                                {i.summaryOverdue}
                              </span>
                            )}
                          </div>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
                            <span>{initiative.external_ref ?? `${i.initiativeIdPrefix} ${truncateId(initiative.id, 8)}`}</span>
                            <span className="text-gray-300">â€¢</span>
                            <span className="inline-flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {ownerLabel}
                            </span>
                            <span className="text-gray-300">â€¢</span>
                            <span className={clsx('inline-flex items-center gap-1', initiative.is_overdue ? 'text-rose-700' : '')}>
                              <CalendarClock className="h-3 w-3" />
                              {formatDateOnly(initiative.sla_date) ?? i.noDueDate}
                            </span>
                          </div>
                          {initiative.description && (
                            <p className="mt-2 line-clamp-1 text-xs text-gray-500">{initiative.description}</p>
                          )}
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
                            <div className="font-semibold text-emerald-700">{formatUsd(estimatedSavings)}</div>
                            <div className="mt-1 text-xs text-gray-400">Monthly value (USD)</div>
                            <div className="mt-1 text-xs text-slate-500">
                              Realized: {formatUsd(initiative.realized_savings_usd ?? 0)}
                            </div>
                          </div>
                        ) : (
                          <span className="text-gray-400">{i.notAvailable}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <span className={clsx(
                          'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                          STATUS_BADGES[initiative.status],
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
                        {formatDateOnly(initiative.sla_date) ?? i.noDueDate}
                      </td>
                      <td className="hidden px-4 py-3 align-top text-gray-500 xl:table-cell">
                        {formatDateTime(initiative.updated_at) ?? i.notAvailable}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="min-w-[132px]">
                          <div className="flex items-center justify-between text-xs text-gray-500">
                            <span>{phaseLabels[initiative.status]}</span>
                            <span>{progress}%</span>
                          </div>
                          <div className="mt-2 h-2 rounded-full bg-gray-100">
                            <div
                              className={clsx('h-2 rounded-full', progressBarClass(initiative.status))}
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
                            className="inline-flex items-center gap-1 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
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
        </Panel>
      ) : (
        <Panel>
          <PanelHeader
            title="Execution board"
            subtitle="Review work by delivery phase while keeping ownership, urgency, value, and next action visible on every card."
            actions={
              <div className="text-right text-xs text-slate-500">
                <div className="font-medium text-slate-700">{summary.total} total</div>
                <div>{summary.overdueCount} overdue</div>
              </div>
            }
          />
          <div className="mt-4 flex gap-4 overflow-x-auto pb-2">
            {columns.map(({ key, label, color }) => {
              const items = board?.[key] ?? []
              return (
                <Panel key={key} compact className={clsx('w-80 flex-shrink-0 space-y-3', color)}>
                  <PanelHeader
                    title={label}
                    subtitle={phaseLabels[key]}
                    badge={
                      <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                        {items.length}
                      </span>
                    }
                  />
                  <div className="space-y-3">
                    {items.map((item) => (
                      <InitiativeCard
                        key={item.id}
                        initiative={item}
                        linkedOpportunity={item.opportunity_id ? opportunityById.get(item.opportunity_id) : undefined}
                        nextStatus={STATUS_TRANSITIONS[item.status]}
                        onAdvance={(id, status) => transitionMutation.mutate({ id, status })}
                        statusLabel={statusLabels[item.status]}
                        phaseLabel={phaseLabels[item.status]}
                      />
                    ))}
                    {items.length === 0 && (
                      <EmptyState
                        icon="document"
                        title={i.emptyPhaseTitle.replace('{{phase}}', label)}
                        description={i.emptyPhaseBody}
                        className="bg-white/80 py-8"
                      />
                    )}
                  </div>
                </Panel>
              )
            })}
          </div>
        </Panel>
      )}

      <p className="text-center text-[10px] text-slate-400">
        Execution tracking workspace - workflow states and initiative values remain unchanged.
      </p>
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
}: {
  initiative: Initiative
  linkedOpportunity?: Opportunity
  nextStatus: InitiativeStatus | null
  onAdvance: (id: string, status: string) => void
  statusLabel: string
  phaseLabel: string
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
  const dueDateLabel = formatDateOnly(initiative.sla_date)
  const lastActivityLabel = formatDateTime(initiative.updated_at)
  const risk = linkedOpportunity?.risk_level

  return (
    <div className="rounded-xl border border-white bg-white p-3.5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold leading-snug text-gray-900">{initiative.title}</p>
            {initiative.is_overdue && (
              <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-700">
                <AlertCircle className="h-3 w-3" />
                {i.summaryOverdue}
              </span>
            )}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
            <span>{phaseLabel}</span>
            <span className="text-gray-300">â€¢</span>
            <span className="inline-flex items-center gap-1">
              <User className="h-3 w-3" />
              {ownerLabel}
            </span>
          </div>
        </div>
        <span className={clsx('rounded-full px-2 py-0.5 text-[11px] font-medium', STATUS_BADGES[initiative.status])}>
          {statusLabel}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="text-slate-400">Expected value (USD)</p>
          <p className="mt-1 font-semibold text-emerald-700">
            {linkedOpportunity ? formatUsd(linkedOpportunity.estimated_monthly_savings_usd) : i.notAvailable}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="text-slate-400">Realized value (USD)</p>
          <p className="mt-1 font-semibold text-slate-800">{formatUsd(initiative.realized_savings_usd ?? 0)}</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="inline-flex items-center gap-1 text-slate-400">
            <CalendarClock className="h-3 w-3" />
            {i.colDueDate}
          </p>
          <p className={clsx('mt-1 font-medium', initiative.is_overdue ? 'text-rose-700' : 'text-slate-700')}>
            {dueDateLabel ?? i.noDueDate}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="inline-flex items-center gap-1 text-slate-400">
            <ShieldAlert className="h-3 w-3" />
            {i.colRisk}
          </p>
          <p className="mt-1">
            {risk ? (
              <span className={clsx('inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium', RISK_COLORS[risk])}>
                {i[`risk${risk.charAt(0).toUpperCase() + risk.slice(1)}` as 'riskLow' | 'riskMedium' | 'riskHigh']}
              </span>
            ) : (
              <span className="text-slate-500">{i.notAvailable}</span>
            )}
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
            className={clsx('h-1.5 rounded-full', progressBarClass(initiative.status))}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {nextStatus ? (
        <button
          onClick={() => onAdvance(initiative.id, nextStatus)}
          className="mt-3 inline-flex w-full items-center justify-center gap-1 rounded-lg bg-slate-900 px-2.5 py-2 text-xs font-medium text-white transition-colors hover:bg-slate-800"
        >
          <ArrowRight className="h-3.5 w-3.5" />
          {i.moveTo.replace('{{status}}', statusLabels[nextStatus] ?? nextStatus.replace('_', ' '))}
        </button>
      ) : initiative.external_url ? (
        <a
          href={initiative.external_url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex w-full items-center justify-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-100"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          {i.openExternal}
        </a>
      ) : null}
    </div>
  )
}


