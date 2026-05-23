import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight, Info, Shield } from 'lucide-react'
import clsx from 'clsx'
import { intelApi } from '../../api/intel'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { MetricCard } from '../../components/Cards/MetricCard'
import { SkeletonMetricCards, SkeletonPrioritizedList, SkeletonSection } from '../../components/UX/Skeleton'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import type { ExecutionPlanStatus, OptimizationPlanRecommendation } from '../../types'
import { formatCurrency } from '../../utils/currency'

const CATEGORY_COLORS: Record<string, string> = {
  rightsizing: 'bg-blue-50 text-blue-700',
  aks_nodepool_rightsizing: 'bg-indigo-50 text-indigo-700',
  aks_autoscaler_recommendation: 'bg-violet-50 text-violet-700',
  idle_resources: 'bg-amber-50 text-amber-700',
  reserved_instances: 'bg-emerald-50 text-emerald-700',
  storage_optimization: 'bg-cyan-50 text-cyan-700',
  network_optimization: 'bg-slate-100 text-slate-700',
}

const RISK_COLORS: Record<string, string> = {
  low: 'bg-emerald-50 text-emerald-700',
  medium: 'bg-amber-50 text-amber-700',
  high: 'bg-red-50 text-red-700',
}

const RANK_COLORS = ['bg-emerald-600', 'bg-emerald-500', 'bg-blue-500', 'bg-blue-400', 'bg-gray-400']

function getRankColor(rank: number) {
  if (rank <= 1) return RANK_COLORS[0]
  if (rank <= 2) return RANK_COLORS[1]
  if (rank <= 3) return RANK_COLORS[2]
  if (rank <= 5) return RANK_COLORS[3]
  return RANK_COLORS[4]
}

function humanizeCategory(value: string) {
  return value.split('_').filter(Boolean).map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(' ')
}

const fmt = (n: number) => formatCurrency(n, undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function OptimizationPlanPage() {
  const { t, lang } = useI18n()
  usePageTitle(t.optimizationPlan.title)
  const queryClient = useQueryClient()
  const [reviewComment, setReviewComment] = useState('')
  const [scheduledFor, setScheduledFor] = useState('')
  const [maintenanceWindow, setMaintenanceWindow] = useState('')
  const [targetEnvironment, setTargetEnvironment] = useState('production')
  const [targetCriticality, setTargetCriticality] = useState('medium')
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [showConfirmDialog, setShowConfirmDialog] = useState<'approve' | 'reject' | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['optimization-plan', lang],
    queryFn: async () => {
      const response = await intelApi.optimizationPlan({
        language: lang === 'pt' ? 'pt' : 'en',
        include_ai_summary: true,
      })
      return response.data
    },
    staleTime: 30_000,
    retry: 2,
  })

  const { data: executionPlanPage } = useQuery({
    queryKey: ['execution-plan', 'latest'],
    queryFn: async () => {
      const response = await intelApi.listExecutionPlans({ page: 1, page_size: 1 })
      return response.data
    },
    staleTime: 30_000,
    retry: 2,
  })

  const latestExecutionPlan = executionPlanPage?.items?.[0] ?? null
  const { data: executionStatus } = useQuery({
    queryKey: ['execution-plan', latestExecutionPlan?.execution_plan_id, 'execution-status'],
    queryFn: async () => {
      if (!latestExecutionPlan) return null
      const response = await intelApi.getExecutionPlanExecutionStatus(latestExecutionPlan.execution_plan_id)
      return response.data
    },
    enabled: !!latestExecutionPlan?.pulselab_experiment_id,
  })

  const canApprove = latestExecutionPlan?.status === 'review_required'
  const canReject = latestExecutionPlan?.status === 'review_required' || latestExecutionPlan?.status === 'blocked'
  const canSchedule = latestExecutionPlan?.status === 'approved'
  const canHandoff =
    (latestExecutionPlan?.status === 'approved' || latestExecutionPlan?.status === 'scheduled') &&
    !latestExecutionPlan?.pulselab_experiment_id

  const statusMutation = useMutation({
    mutationFn: async (status: 'approved' | 'rejected') => {
      if (!latestExecutionPlan) return
      const comment = reviewComment.trim()
      await intelApi.updateExecutionPlanStatus(latestExecutionPlan.execution_plan_id, {
        status,
        comment: comment.length > 0 ? comment : undefined,
      })
    },
    onSuccess: async (_, status) => {
      setStatusMessage({
        text: status === 'approved' ? t.optimizationPlan.statusUpdateSuccessApproved : t.optimizationPlan.statusUpdateSuccessRejected,
        type: 'success',
      })
      setReviewComment('')
      setShowConfirmDialog(null)
      await queryClient.invalidateQueries({ queryKey: ['execution-plan'] })
    },
    onError: () => {
      setStatusMessage({ text: t.optimizationPlan.statusUpdateError, type: 'error' })
      setShowConfirmDialog(null)
    },
  })

  const scheduleMutation = useMutation({
    mutationFn: async () => {
      if (!latestExecutionPlan) return
      await intelApi.scheduleExecutionPlan(latestExecutionPlan.execution_plan_id, {
        scheduled_for: new Date(scheduledFor).toISOString(),
        maintenance_window: maintenanceWindow.trim(),
        comment: reviewComment.trim().length > 0 ? reviewComment.trim() : undefined,
      })
    },
    onSuccess: async () => {
      setStatusMessage({ text: t.optimizationPlan.scheduleUpdateSuccess, type: 'success' })
      setReviewComment('')
      await queryClient.invalidateQueries({ queryKey: ['execution-plan'] })
    },
    onError: () => {
      setStatusMessage({ text: t.optimizationPlan.scheduleUpdateError, type: 'error' })
    },
  })

  const handoffMutation = useMutation({
    mutationFn: async () => {
      if (!latestExecutionPlan) return
      return intelApi.createExecutionPlanHandoff(latestExecutionPlan.execution_plan_id, {
        comment: reviewComment.trim().length > 0 ? reviewComment.trim() : undefined,
        target_environment: targetEnvironment,
        target_criticality: targetCriticality,
      })
    },
    onSuccess: async (response) => {
      const experimentId = response?.data?.pulselab_experiment_id
      setStatusMessage({
        text: experimentId ? `${t.optimizationPlan.handoffSuccess} ${experimentId}` : t.optimizationPlan.handoffSuccess,
        type: 'success',
      })
      await queryClient.invalidateQueries({ queryKey: ['execution-plan'] })
    },
    onError: () => {
      setStatusMessage({ text: t.optimizationPlan.handoffError, type: 'error' })
    },
  })

  const toggleExpanded = (id: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const currency = useMemo(() => (value: number) => fmt(value), [])

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <div className="h-7 w-48 animate-pulse rounded bg-gray-200" />
          <div className="mt-2 h-4 w-72 animate-pulse rounded bg-gray-100" />
        </div>
        <SkeletonMetricCards count={4} />
        <SkeletonSection lines={3} />
        <SkeletonPrioritizedList items={5} />
      </div>
    )
  }

  // Error state
  if (isError || !data) {
    return (
      <div className="p-6">
        <ErrorState
          title={t.optimizationPlan.error}
          description="Could not load the savings plan. Please check your connection and try again."
          onRetry={() => refetch()}
          retryLabel={t.optimizationPlan.errorRetry}
        />
      </div>
    )
  }

  // Empty state
  if (data.total_recommendations === 0) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{t.optimizationPlan.title}</h1>
          <p className="text-sm text-gray-500">{t.optimizationPlan.subtitle}</p>
        </div>
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-start gap-3">
            <Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-600" />
            <p className="text-sm text-blue-800">{t.optimizationPlan.safeDssNotice}</p>
          </div>
        </div>
        <EmptyState
          icon="lightbulb"
          title={t.optimizationPlan.emptyTitle}
          description={t.optimizationPlan.emptyDescription}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">{t.optimizationPlan.title}</h1>
        <p className="text-sm text-gray-500">{t.optimizationPlan.subtitle}</p>
      </div>

      {/* SAFE DSS Notice */}
      <div className="rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50/50 p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-blue-100">
            <Shield className="h-3.5 w-3.5 text-blue-700" />
          </div>
          <div>
            <p className="text-sm font-semibold text-blue-900">{t.optimizationPlan.title}</p>
            <p className="mt-0.5 text-xs text-blue-700/80">{t.optimizationPlan.safeDssNotice}</p>
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          title={t.optimizationPlan.adjustedMonthly}
          value={currency(data.total_savings_monthly_adjusted_usd)}
          subtitle={`${currency(data.total_savings_annual_adjusted_usd)}/yr`}
          variant="success"
          emphasis="primary"
          tooltip={t.optimizationPlan.adjustedMonthly}
        />
        <MetricCard
          title={t.optimizationPlan.prioritized}
          value={String(data.prioritized.length)}
          subtitle={`${t.optimizationPlan.score}: ${data.confidence_global != null ? `${Math.round(data.confidence_global * 100)}%` : '-'}`}
        />
        <MetricCard
          title={t.optimizationPlan.quickWins}
          value={String(data.quick_wins.length)}
          subtitle={t.optimizationPlan.quickWinsSubtitle}
          variant={data.quick_wins.length > 0 ? 'success' : 'default'}
        />
        <MetricCard
          title={t.optimizationPlan.conflicts}
          value={String(data.conflict_hints.length)}
          subtitle={data.conflict_hints.length > 0 ? t.optimizationPlan.conflictHints : undefined}
          variant={data.conflict_hints.length > 0 ? 'warning' : 'default'}
        />
      </div>

      {/* Summary */}
      <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-gray-900">{t.optimizationPlan.summary}</div>
          {data.summary_source === 'ai' && (
            <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-700">
              AI-generated
            </span>
          )}
        </div>
        <p className="mt-3 text-sm leading-relaxed text-gray-700">{data.summary}</p>
        {data.ai_summary && data.summary_source === 'ai' && data.ai_model && (
          <p className="mt-2 text-[11px] text-gray-400">Model: {data.ai_model}</p>
        )}
      </section>

      {/* Conflict Hints */}
      {data.conflict_hints.length > 0 && (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <span className="text-sm font-semibold text-amber-800">{t.optimizationPlan.conflictHints}</span>
          </div>
          <ul className="mt-2 space-y-1 text-sm text-amber-800">
            {data.conflict_hints.map((hint) => (
              <li key={hint} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-amber-400" />
                {hint}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Quick Wins */}
      {data.quick_wins.length > 0 && (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50/50">
          <div className="border-b border-emerald-200 px-5 py-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <span className="text-sm font-semibold text-emerald-900">{t.optimizationPlan.quickWinsTitle}</span>
            </div>
            <p className="mt-1 text-xs text-emerald-700">{t.optimizationPlan.quickWinsSubtitle}</p>
          </div>
          <div className="divide-y divide-emerald-100">
            {data.quick_wins.map((item) => (
              <QuickWinItem key={item.opportunity_id} item={item} currency={currency} t={t} />
            ))}
          </div>
        </section>
      )}

      {/* Prioritized Recommendations */}
      <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-5 py-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold text-gray-900">{t.optimizationPlan.prioritized}</span>
              <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">{data.prioritized.length}</span>
            </div>
            <p className="text-xs text-gray-500">{t.optimizationPlan.subtitle}</p>
          </div>
        </div>
        <div className="divide-y divide-gray-100">
          {data.prioritized.map((item) => (
            <PrioritizedItem
              key={item.opportunity_id}
              item={item}
              currency={currency}
              expanded={expandedItems.has(item.opportunity_id)}
              onToggle={() => toggleExpanded(item.opportunity_id)}
              t={t}
            />
          ))}
        </div>
      </section>

      {/* Governance Section */}
      <GovernanceSection
        latestExecutionPlan={latestExecutionPlan}
        executionStatus={executionStatus}
        canApprove={canApprove}
        canReject={canReject}
        canSchedule={canSchedule}
        canHandoff={canHandoff}
        reviewComment={reviewComment}
        setReviewComment={setReviewComment}
        scheduledFor={scheduledFor}
        setScheduledFor={setScheduledFor}
        maintenanceWindow={maintenanceWindow}
        setMaintenanceWindow={setMaintenanceWindow}
        targetEnvironment={targetEnvironment}
        setTargetEnvironment={setTargetEnvironment}
        targetCriticality={targetCriticality}
        setTargetCriticality={setTargetCriticality}
        statusMutation={statusMutation}
        scheduleMutation={scheduleMutation}
        handoffMutation={handoffMutation}
        statusMessage={statusMessage}
        setStatusMessage={setStatusMessage}
        showConfirmDialog={showConfirmDialog}
        setShowConfirmDialog={setShowConfirmDialog}
        currency={currency}
        t={t}
      />
    </div>
  )
}

// --- Sub-components ---

function QuickWinItem({
  item,
  currency,
  t,
}: {
  item: OptimizationPlanRecommendation
  currency: (value: number) => string
  t: ReturnType<typeof useI18n>['t']
}) {
  return (
    <div className="px-5 py-3.5 transition-colors hover:bg-emerald-50/30">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={clsx('rounded-full px-2 py-0.5 text-[11px] font-medium', CATEGORY_COLORS[item.category] ?? 'bg-gray-100 text-gray-600')}>
              {humanizeCategory(item.category)}
            </span>
            <span className={clsx('rounded-full px-2 py-0.5 text-[11px] font-medium', RISK_COLORS[item.risk_level])}>
              {item.risk_level} {t.optimizationPlan.riskLabel.toLowerCase()}
            </span>
            <span className="text-[11px] text-gray-500">
              {Math.round(item.confidence * 100)}% {t.optimizationPlan.confidenceLabel.toLowerCase()}
            </span>
          </div>
          <p className="mt-1.5 text-sm font-medium text-gray-900">{item.title}</p>
          <p className="mt-1 text-xs text-gray-500 leading-relaxed">{item.next_step}</p>
        </div>
        <div className="flex-shrink-0 text-right">
          <p className="text-sm font-bold tabular-nums text-emerald-700">{currency(item.estimated_monthly_savings_usd)}</p>
          <p className="text-[11px] text-gray-400">{t.common.monthly}</p>
        </div>
      </div>
    </div>
  )
}

function PrioritizedItem({
  item,
  currency,
  expanded,
  onToggle,
  t,
}: {
  item: OptimizationPlanRecommendation
  currency: (value: number) => string
  expanded: boolean
  onToggle: () => void
  t: ReturnType<typeof useI18n>['t']
}) {
  return (
    <article className="px-5 py-4 transition-colors hover:bg-gray-50/50">
      <div className="flex items-start gap-3 cursor-pointer" onClick={onToggle} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onToggle() }}>
        {/* Rank badge */}
        <div className={clsx('flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl text-xs font-bold text-white shadow-sm', getRankColor(item.rank))}>
          #{item.rank}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-900">{item.title}</span>
            <span className={clsx('rounded-full px-2 py-0.5 text-[11px] font-medium', CATEGORY_COLORS[item.category] ?? 'bg-gray-100 text-gray-600')}>
              {humanizeCategory(item.category)}
            </span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
            <span className="font-bold tabular-nums text-emerald-700">{currency(item.estimated_monthly_savings_usd)}/mo</span>
            <span className="h-3 w-px bg-gray-200" />
            <span className={clsx('inline-flex rounded-full px-1.5 py-0.5 font-medium', RISK_COLORS[item.risk_level])}>{item.risk_level} risk</span>
            <span className="h-3 w-px bg-gray-200" />
            <span className="text-gray-600">{t.optimizationPlan.confidenceLabel}: <strong>{Math.round(item.confidence * 100)}%</strong></span>
            <span className="h-3 w-px bg-gray-200" />
            <span className="text-gray-600">{t.optimizationPlan.score}: <strong className="tabular-nums">{item.priority_score.toFixed(2)}</strong></span>
          </div>
        </div>

        <button type="button" className="flex-shrink-0 rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600" aria-label="Toggle details">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 ml-12 space-y-3 rounded-xl border border-gray-100 bg-gray-50/50 p-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">{t.optimizationPlan.whyNow}</p>
            <p className="mt-1.5 text-sm leading-relaxed text-gray-700">{item.why_now}</p>
          </div>
          <div className="border-t border-gray-100 pt-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">{t.optimizationPlan.nextStep}</p>
            <p className="mt-1.5 text-sm leading-relaxed text-gray-700">{item.next_step}</p>
          </div>
          {item.conflict_hints.length > 0 && (
            <div className="border-t border-gray-100 pt-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-600">{t.optimizationPlan.conflictHints}</p>
              <ul className="mt-1.5 space-y-1.5">
                {item.conflict_hints.map((hint) => (
                  <li key={hint} className="flex items-start gap-2 text-xs text-amber-700">
                    <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
                    <span>{hint}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </article>
  )
}

function GovernanceSection({
  latestExecutionPlan,
  executionStatus,
  canApprove,
  canReject,
  canSchedule,
  canHandoff,
  reviewComment,
  setReviewComment,
  scheduledFor,
  setScheduledFor,
  maintenanceWindow,
  setMaintenanceWindow,
  targetEnvironment,
  setTargetEnvironment,
  targetCriticality,
  setTargetCriticality,
  statusMutation,
  scheduleMutation,
  handoffMutation,
  statusMessage,
  setStatusMessage,
  showConfirmDialog,
  setShowConfirmDialog,
  currency,
  t,
}: {
  latestExecutionPlan: { execution_plan_id: string; status: ExecutionPlanStatus; pulselab_experiment_id?: string | null; gates_triggered?: string[] } | null
  executionStatus: { status: 'running' | 'completed' | 'failed'; outcome: 'success' | 'partial' | 'failed'; expected_savings: number; actual_savings: number; delta: number } | null | undefined
  canApprove: boolean
  canReject: boolean
  canSchedule: boolean
  canHandoff: boolean
  reviewComment: string
  setReviewComment: (v: string) => void
  scheduledFor: string
  setScheduledFor: (v: string) => void
  maintenanceWindow: string
  setMaintenanceWindow: (v: string) => void
  targetEnvironment: string
  setTargetEnvironment: (v: string) => void
  targetCriticality: string
  setTargetCriticality: (v: string) => void
  statusMutation: { mutate: (s: 'approved' | 'rejected') => void; isPending: boolean }
  scheduleMutation: { mutate: () => void; isPending: boolean }
  handoffMutation: { mutate: () => void; isPending: boolean }
  statusMessage: { text: string; type: 'success' | 'error' } | null
  setStatusMessage: (v: { text: string; type: 'success' | 'error' } | null) => void
  showConfirmDialog: 'approve' | 'reject' | null
  setShowConfirmDialog: (v: 'approve' | 'reject' | null) => void
  currency: (value: number) => string
  t: ReturnType<typeof useI18n>['t']
}) {
  const STATUS_ORDER: ExecutionPlanStatus[] = ['review_required', 'approved', 'scheduled']
  const currentStatusIndex = latestExecutionPlan ? STATUS_ORDER.indexOf(latestExecutionPlan.status) : -1
  const isTerminalState = latestExecutionPlan?.status === 'blocked' || latestExecutionPlan?.status === 'rejected'
  const hasHandoff = !!latestExecutionPlan?.pulselab_experiment_id

  return (
    <section className="space-y-4">
      {/* Governance Header Card */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900">
              <Shield className="h-4 w-4 text-white" />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900">{t.optimizationPlan.governanceTitle}</div>
              <p className="mt-0.5 text-xs text-gray-500">{t.optimizationPlan.governanceSubtitle}</p>
            </div>
          </div>
          {latestExecutionPlan && (
            <span className={statusBadgeClassName(latestExecutionPlan.status)}>
              {statusLabel(latestExecutionPlan.status, t)}
            </span>
          )}
        </div>

        {!latestExecutionPlan ? (
          <div className="mt-5 rounded-xl border-2 border-dashed border-gray-200 bg-gray-50/50 p-6 text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
              <Info className="h-5 w-5 text-gray-400" />
            </div>
            <p className="mt-3 text-sm font-medium text-gray-700">{t.optimizationPlan.noExecutionPlan}</p>
            <p className="mt-1 text-xs text-gray-400">{t.optimizationPlan.generateExecutionPlanSoon}</p>
          </div>
        ) : (
          <div className="mt-5 space-y-5">
            {/* Timeline Progress */}
            <div className="rounded-lg border border-gray-100 bg-gray-50/50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-3">{t.optimizationPlan.timeline}</p>
              <div className="flex items-center">
                {STATUS_ORDER.map((key, idx) => {
                  const isCurrent = latestExecutionPlan.status === key
                  const isPast = currentStatusIndex > idx
                  const label = key === 'review_required' ? t.optimizationPlan.timelineReviewRequired : key === 'approved' ? t.optimizationPlan.timelineApproved : t.optimizationPlan.timelineScheduled
                  return (
                    <div key={key} className="flex items-center flex-1 last:flex-none">
                      <div className="flex flex-col items-center gap-1.5">
                        <div className={clsx(
                          'flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold transition-colors',
                          isCurrent ? 'bg-brand-600 text-white shadow-sm' : isPast ? 'bg-emerald-500 text-white' : 'bg-gray-200 text-gray-400',
                        )}>
                          {isPast ? <CheckCircle2 className="h-3.5 w-3.5" /> : idx + 1}
                        </div>
                        <span className={clsx('text-[11px] text-center whitespace-nowrap', isCurrent ? 'font-semibold text-gray-900' : isPast ? 'font-medium text-emerald-700' : 'text-gray-400')}>
                          {label}
                        </span>
                      </div>
                      {idx < STATUS_ORDER.length - 1 && (
                        <div className={clsx('mx-2 h-0.5 flex-1 rounded-full', isPast ? 'bg-emerald-300' : 'bg-gray-200')} />
                      )}
                    </div>
                  )
                })}
              </div>
              {isTerminalState && (
                <div className={clsx('mt-3 flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium', latestExecutionPlan.status === 'rejected' ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700')}>
                  <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
                  {latestExecutionPlan.status === 'rejected' ? t.optimizationPlan.timelineRejected : t.optimizationPlan.timelineBlocked}
                </div>
              )}
            </div>

            {/* Plan Metadata */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-500">
              <span>{t.optimizationPlan.latestPlanId}: <span className="font-mono font-medium text-gray-700">{latestExecutionPlan.execution_plan_id.slice(0, 8)}</span></span>
              {latestExecutionPlan.gates_triggered && latestExecutionPlan.gates_triggered.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <AlertTriangle className="h-3 w-3 text-amber-500" />
                  <span className="font-medium text-amber-700">{t.optimizationPlan.gatesTriggered}:</span>
                  {latestExecutionPlan.gates_triggered.map((gate) => (
                    <span key={gate} className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">{gate}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Approval & Actions Card */}
      {latestExecutionPlan && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-4">{t.optimizationPlan.reviewComment}</p>
          <textarea
            value={reviewComment}
            onChange={(e) => setReviewComment(e.target.value)}
            placeholder={t.optimizationPlan.reviewCommentPlaceholder}
            className="h-20 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm text-gray-900 outline-none transition focus:border-brand-500 focus:bg-white focus:ring-1 focus:ring-brand-500"
          />

          {/* Schedule fields */}
          {canSchedule && (
            <div className="mt-4 rounded-lg border border-gray-100 bg-gray-50/50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-3">{t.optimizationPlan.schedulePlan}</p>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="block">
                  <div className="mb-1.5 text-xs font-medium text-gray-700">{t.optimizationPlan.scheduledFor}</div>
                  <input
                    type="datetime-local"
                    value={scheduledFor}
                    onChange={(e) => setScheduledFor(e.target.value)}
                    className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                  />
                </label>
                <label className="block">
                  <div className="mb-1.5 text-xs font-medium text-gray-700">{t.optimizationPlan.maintenanceWindow}</div>
                  <input
                    type="text"
                    value={maintenanceWindow}
                    onChange={(e) => setMaintenanceWindow(e.target.value)}
                    placeholder={t.optimizationPlan.maintenanceWindowPlaceholder}
                    className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                  />
                </label>
              </div>
            </div>
          )}

          {/* Handoff fields */}
          {canHandoff && (
            <div className="mt-4 rounded-lg border border-violet-100 bg-violet-50/30 p-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="flex h-5 w-5 items-center justify-center rounded bg-violet-100">
                  <span className="text-[9px] font-bold text-violet-700">IMP</span>
                </div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-700">{t.optimizationPlan.sendToPulseLab}</p>
              </div>
              <p className="text-xs text-gray-500 mb-3">{t.optimizationPlan.handoffNotice}</p>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="block">
                  <div className="mb-1.5 text-xs font-medium text-gray-700">{t.optimizationPlan.targetEnvironment}</div>
                  <input
                    type="text"
                    value={targetEnvironment}
                    onChange={(e) => setTargetEnvironment(e.target.value)}
                    className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                  />
                </label>
                <label className="block">
                  <div className="mb-1.5 text-xs font-medium text-gray-700">{t.optimizationPlan.targetCriticality}</div>
                  <input
                    type="text"
                    value={targetCriticality}
                    onChange={(e) => setTargetCriticality(e.target.value)}
                    className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                  />
                </label>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-4">
            <button
              type="button"
              disabled={!canApprove || statusMutation.isPending}
              onClick={() => setShowConfirmDialog('approve')}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {statusMutation.isPending && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />}
              {t.optimizationPlan.approvePlan}
            </button>
            <button
              type="button"
              disabled={!canReject || statusMutation.isPending}
              onClick={() => setShowConfirmDialog('reject')}
              className="inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-white px-4 py-2.5 text-sm font-medium text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {t.optimizationPlan.rejectPlan}
            </button>
            {canSchedule && (
              <button
                type="button"
                disabled={scheduleMutation.isPending || scheduledFor.trim().length === 0 || maintenanceWindow.trim().length === 0}
                onClick={() => scheduleMutation.mutate()}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {scheduleMutation.isPending && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />}
                {t.optimizationPlan.schedulePlan}
              </button>
            )}
            {canHandoff && (
              <button
                type="button"
                disabled={handoffMutation.isPending || targetEnvironment.trim().length === 0 || targetCriticality.trim().length === 0}
                onClick={() => handoffMutation.mutate()}
                className="inline-flex items-center gap-2 rounded-lg border border-violet-200 bg-white px-4 py-2.5 text-sm font-medium text-violet-700 transition hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {handoffMutation.isPending && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />}
                {t.optimizationPlan.sendToPulseLab}
              </button>
            )}
          </div>
        </div>
      )}

      {/* PulseLab Handoff & Tracking Card */}
      {latestExecutionPlan && hasHandoff && (
        <div className="rounded-xl border border-violet-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-100">
                <span className="text-[10px] font-bold text-violet-700">IMP</span>
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-900">{t.optimizationPlan.handoffExperimentId}</div>
                <p className="mt-0.5 font-mono text-xs text-violet-700">{latestExecutionPlan.pulselab_experiment_id}</p>
              </div>
            </div>
            {executionStatus && (
              <span className={clsx(
                'inline-flex rounded-full px-2.5 py-1 text-xs font-medium',
                executionStatus.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                executionStatus.status === 'running' ? 'bg-blue-100 text-blue-700' :
                'bg-red-100 text-red-700',
              )}>
                {executionStatusLabel(executionStatus.status, t)}
              </span>
            )}
          </div>

          {executionStatus ? (
            <div className="mt-4 rounded-lg border border-gray-100 bg-gray-50/50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-3">{t.optimizationPlan.executionTrackingTitle}</p>
              <p className="text-xs text-gray-500 mb-4">{t.optimizationPlan.executionTrackingSubtitle}</p>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <div className="rounded-lg border border-gray-200 bg-white p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">{t.optimizationPlan.executionOutcomeLabel}</p>
                  <p className={clsx('mt-1 text-sm font-bold', executionStatus.outcome === 'success' ? 'text-emerald-700' : executionStatus.outcome === 'partial' ? 'text-amber-700' : 'text-red-700')}>
                    {executionOutcomeLabel(executionStatus.outcome, t)}
                  </p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">{t.optimizationPlan.expectedSavingsLabel}</p>
                  <p className="mt-1 text-sm font-bold tabular-nums text-gray-900">{currency(executionStatus.expected_savings)}</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">{t.optimizationPlan.actualSavingsLabel}</p>
                  <p className="mt-1 text-sm font-bold tabular-nums text-gray-900">{currency(executionStatus.actual_savings)}</p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2.5">
                <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">{t.optimizationPlan.deltaSavingsLabel}</p>
                <p className={clsx('ml-auto text-sm font-bold tabular-nums', executionStatus.delta >= 0 ? 'text-emerald-700' : 'text-rose-700')}>
                  {executionStatus.delta >= 0 ? '+' : ''}{currency(executionStatus.delta)}
                </p>
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-lg border border-dashed border-violet-200 bg-violet-50/30 p-4 text-center">
              <p className="text-sm text-violet-700">{t.optimizationPlan.executionStatusRunning}</p>
              <p className="mt-1 text-xs text-gray-500">{t.optimizationPlan.executionTrackingSubtitle}</p>
            </div>
          )}
        </div>
      )}

      {/* Status message toast */}
      {statusMessage && (
        <div className={clsx(
          'flex items-center justify-between rounded-xl border px-4 py-3 shadow-sm',
          statusMessage.type === 'success' ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50',
        )}>
          <div className="flex items-center gap-2">
            {statusMessage.type === 'success' ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <AlertTriangle className="h-4 w-4 text-red-500" />}
            <p className={clsx('text-sm font-medium', statusMessage.type === 'success' ? 'text-emerald-700' : 'text-red-700')}>{statusMessage.text}</p>
          </div>
          <button type="button" onClick={() => setStatusMessage(null)} className="ml-3 rounded-md p-1 text-gray-400 transition hover:bg-white hover:text-gray-600">
            <span className="text-xs">✕</span>
          </button>
        </div>
      )}

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-2xl">
            <div className="flex items-start gap-3">
              <div className={clsx('flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl', showConfirmDialog === 'approve' ? 'bg-emerald-100' : 'bg-rose-100')}>
                {showConfirmDialog === 'approve' ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <AlertTriangle className="h-4 w-4 text-rose-600" />}
              </div>
              <div>
                <h3 className="text-base font-semibold text-gray-900">
                  {showConfirmDialog === 'approve' ? t.optimizationPlan.confirmApproveTitle : t.optimizationPlan.confirmRejectTitle}
                </h3>
                <p className="mt-1.5 text-sm text-gray-600">
                  {showConfirmDialog === 'approve' ? t.optimizationPlan.confirmApproveDesc : t.optimizationPlan.confirmRejectDesc}
                </p>
              </div>
            </div>
            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowConfirmDialog(null)}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
              >
                {t.common.cancel}
              </button>
              <button
                type="button"
                disabled={statusMutation.isPending}
                onClick={() => statusMutation.mutate(showConfirmDialog === 'approve' ? 'approved' : 'rejected')}
                className={clsx(
                  'inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm transition disabled:opacity-50',
                  showConfirmDialog === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700',
                )}
              >
                {statusMutation.isPending && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />}
                {showConfirmDialog === 'approve' ? t.optimizationPlan.approvePlan : t.optimizationPlan.rejectPlan}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

// --- Helpers ---

function statusLabel(status: ExecutionPlanStatus, t: ReturnType<typeof useI18n>['t']): string {
  if (status === 'review_required') return t.optimizationPlan.statusReviewRequired
  if (status === 'blocked') return t.optimizationPlan.statusBlocked
  if (status === 'approved') return t.optimizationPlan.statusApproved
  if (status === 'scheduled') return t.optimizationPlan.statusScheduled
  if (status === 'rejected') return t.optimizationPlan.statusRejected
  return t.optimizationPlan.statusUnknown
}

function statusBadgeClassName(status: ExecutionPlanStatus): string {
  if (status === 'approved') return 'inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700'
  if (status === 'rejected') return 'inline-flex rounded-full bg-rose-100 px-2.5 py-1 text-xs font-medium text-rose-700'
  if (status === 'blocked') return 'inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700'
  if (status === 'scheduled') return 'inline-flex rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-medium text-indigo-700'
  return 'inline-flex rounded-full bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700'
}

function executionStatusLabel(status: 'running' | 'completed' | 'failed', t: ReturnType<typeof useI18n>['t']): string {
  if (status === 'running') return t.optimizationPlan.executionStatusRunning
  if (status === 'completed') return t.optimizationPlan.executionStatusCompleted
  return t.optimizationPlan.executionStatusFailed
}

function executionOutcomeLabel(outcome: 'success' | 'partial' | 'failed', t: ReturnType<typeof useI18n>['t']): string {
  if (outcome === 'success') return t.optimizationPlan.executionOutcomeSuccess
  if (outcome === 'partial') return t.optimizationPlan.executionOutcomePartial
  return t.optimizationPlan.executionOutcomeFailed
}
