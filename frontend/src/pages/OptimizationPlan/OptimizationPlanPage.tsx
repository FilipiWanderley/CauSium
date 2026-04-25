import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { intelApi } from '../../api/intel'
import { useI18n } from '../../contexts/I18nContext'
import type { ExecutionPlanStatus } from '../../types'

export function OptimizationPlanPage() {
  const { t, language } = useI18n()
  const queryClient = useQueryClient()
  const [reviewComment, setReviewComment] = useState('')
  const [scheduledFor, setScheduledFor] = useState('')
  const [maintenanceWindow, setMaintenanceWindow] = useState('')
  const [targetEnvironment, setTargetEnvironment] = useState('production')
  const [targetCriticality, setTargetCriticality] = useState('medium')
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['optimization-plan', language],
    queryFn: async () => {
      const response = await intelApi.optimizationPlan({
        language: language === 'pt' ? 'pt' : 'en',
        include_ai_summary: true,
      })
      return response.data
    },
  })

  const { data: executionPlanPage } = useQuery({
    queryKey: ['execution-plan', 'latest'],
    queryFn: async () => {
      const response = await intelApi.listExecutionPlans({ page: 1, page_size: 1 })
      return response.data
    },
  })

  const latestExecutionPlan = executionPlanPage?.items?.[0] ?? null
  const { data: executionStatus } = useQuery({
    queryKey: ['execution-plan', latestExecutionPlan?.execution_plan_id, 'execution-status'],
    queryFn: async () => {
      if (!latestExecutionPlan) {
        return null
      }
      const response = await intelApi.getExecutionPlanExecutionStatus(latestExecutionPlan.execution_plan_id)
      return response.data
    },
    enabled: !!latestExecutionPlan?.pulselab_experiment_id,
  })

  const canApprove = latestExecutionPlan?.status === 'review_required'
  const canReject =
    latestExecutionPlan?.status === 'review_required' || latestExecutionPlan?.status === 'blocked'
  const canSchedule = latestExecutionPlan?.status === 'approved'
  const canHandoff =
    (latestExecutionPlan?.status === 'approved' || latestExecutionPlan?.status === 'scheduled') &&
    !latestExecutionPlan?.pulselab_experiment_id

  const statusMutation = useMutation({
    mutationFn: async (status: 'approved' | 'rejected') => {
      if (!latestExecutionPlan) {
        return
      }
      const comment = reviewComment.trim()
      await intelApi.updateExecutionPlanStatus(latestExecutionPlan.execution_plan_id, {
        status,
        comment: comment.length > 0 ? comment : undefined,
      })
    },
    onSuccess: async (_, status) => {
      setStatusMessage(
        status === 'approved'
          ? t.optimizationPlan.statusUpdateSuccessApproved
          : t.optimizationPlan.statusUpdateSuccessRejected
      )
      setReviewComment('')
      await queryClient.invalidateQueries({ queryKey: ['execution-plan'] })
    },
    onError: () => {
      setStatusMessage(t.optimizationPlan.statusUpdateError)
    },
  })

  const scheduleMutation = useMutation({
    mutationFn: async () => {
      if (!latestExecutionPlan) {
        return
      }
      await intelApi.scheduleExecutionPlan(latestExecutionPlan.execution_plan_id, {
        scheduled_for: new Date(scheduledFor).toISOString(),
        maintenance_window: maintenanceWindow.trim(),
        comment: reviewComment.trim().length > 0 ? reviewComment.trim() : undefined,
      })
    },
    onSuccess: async () => {
      setStatusMessage(t.optimizationPlan.scheduleUpdateSuccess)
      setReviewComment('')
      await queryClient.invalidateQueries({ queryKey: ['execution-plan'] })
    },
    onError: () => {
      setStatusMessage(t.optimizationPlan.scheduleUpdateError)
    },
  })

  const handoffMutation = useMutation({
    mutationFn: async () => {
      if (!latestExecutionPlan) {
        return
      }
      return intelApi.createExecutionPlanHandoff(latestExecutionPlan.execution_plan_id, {
        comment: reviewComment.trim().length > 0 ? reviewComment.trim() : undefined,
        target_environment: targetEnvironment,
        target_criticality: targetCriticality,
      })
    },
    onSuccess: async (response) => {
      const experimentId = response?.data?.pulselab_experiment_id
      setStatusMessage(
        experimentId
          ? `${t.optimizationPlan.handoffSuccess} ${experimentId}`
          : t.optimizationPlan.handoffSuccess
      )
      await queryClient.invalidateQueries({ queryKey: ['execution-plan'] })
    },
    onError: () => {
      setStatusMessage(t.optimizationPlan.handoffError)
    },
  })

  const timelineItems = useMemo(
    () => [
      {
        key: 'review_required',
        label: t.optimizationPlan.timelineReviewRequired,
        active: !!latestExecutionPlan,
        current: latestExecutionPlan?.status === 'review_required',
      },
      {
        key: 'blocked',
        label: t.optimizationPlan.timelineBlocked,
        active: latestExecutionPlan?.status === 'blocked',
        current: latestExecutionPlan?.status === 'blocked',
      },
      {
        key: 'approved',
        label: t.optimizationPlan.timelineApproved,
        active: latestExecutionPlan?.status === 'approved',
        current: latestExecutionPlan?.status === 'approved',
      },
      {
        key: 'scheduled',
        label: t.optimizationPlan.timelineScheduled,
        active: latestExecutionPlan?.status === 'scheduled',
        current: latestExecutionPlan?.status === 'scheduled',
      },
      {
        key: 'rejected',
        label: t.optimizationPlan.timelineRejected,
        active: latestExecutionPlan?.status === 'rejected',
        current: latestExecutionPlan?.status === 'rejected',
      },
    ],
    [latestExecutionPlan, t]
  )

  const currency = useMemo(
    () =>
      new Intl.NumberFormat(language === 'pt' ? 'pt-BR' : 'en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
      }),
    [language]
  )

  if (isLoading) {
    return <div className="p-6 text-sm text-gray-400">{t.common.loading}</div>
  }
  if (isError || !data) {
    return <div className="p-6 text-sm text-red-400">{t.optimizationPlan.error}</div>
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">{t.optimizationPlan.title}</h1>
        <p className="text-sm text-gray-400">{t.optimizationPlan.subtitle}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label={t.optimizationPlan.adjustedMonthly}
          value={currency.format(data.total_savings_monthly_adjusted_usd)}
        />
        <MetricCard
          label={t.optimizationPlan.adjustedAnnual}
          value={currency.format(data.total_savings_annual_adjusted_usd)}
        />
        <MetricCard
          label={t.optimizationPlan.quickWins}
          value={String(data.quick_wins.length)}
        />
        <MetricCard
          label={t.optimizationPlan.conflicts}
          value={String(data.conflict_hints.length)}
        />
      </div>

      <section className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-medium text-gray-200">{t.optimizationPlan.governanceTitle}</div>
            <p className="mt-1 text-xs text-gray-400">{t.optimizationPlan.governanceSubtitle}</p>
          </div>
          {latestExecutionPlan ? (
            <span className={statusBadgeClassName(latestExecutionPlan.status)}>
              {statusLabel(latestExecutionPlan.status, t)}
            </span>
          ) : null}
        </div>

        {!latestExecutionPlan ? (
          <p className="mt-3 text-sm text-gray-400">{t.optimizationPlan.noExecutionPlan}</p>
        ) : (
          <div className="mt-4 space-y-4">
            <div className="text-xs text-gray-400">
              {t.optimizationPlan.latestPlanId}: {latestExecutionPlan.execution_plan_id}
            </div>

            <label className="block">
              <div className="mb-1 text-xs text-gray-300">{t.optimizationPlan.reviewComment}</div>
              <textarea
                value={reviewComment}
                onChange={(event) => setReviewComment(event.target.value)}
                placeholder={t.optimizationPlan.reviewCommentPlaceholder}
                className="h-24 w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-brand-500"
              />
            </label>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="block">
                <div className="mb-1 text-xs text-gray-300">{t.optimizationPlan.scheduledFor}</div>
                <input
                  type="datetime-local"
                  value={scheduledFor}
                  onChange={(event) => setScheduledFor(event.target.value)}
                  className="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-brand-500"
                />
              </label>
              <label className="block">
                <div className="mb-1 text-xs text-gray-300">{t.optimizationPlan.maintenanceWindow}</div>
                <input
                  type="text"
                  value={maintenanceWindow}
                  onChange={(event) => setMaintenanceWindow(event.target.value)}
                  placeholder={t.optimizationPlan.maintenanceWindowPlaceholder}
                  className="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-brand-500"
                />
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="block">
                <div className="mb-1 text-xs text-gray-300">{t.optimizationPlan.targetEnvironment}</div>
                <input
                  type="text"
                  value={targetEnvironment}
                  onChange={(event) => setTargetEnvironment(event.target.value)}
                  className="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-brand-500"
                />
              </label>
              <label className="block">
                <div className="mb-1 text-xs text-gray-300">{t.optimizationPlan.targetCriticality}</div>
                <input
                  type="text"
                  value={targetCriticality}
                  onChange={(event) => setTargetCriticality(event.target.value)}
                  className="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-brand-500"
                />
              </label>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={!canApprove || statusMutation.isPending}
                onClick={() => statusMutation.mutate('approved')}
                className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {statusMutation.isPending
                  ? t.optimizationPlan.updatingStatus
                  : t.optimizationPlan.approvePlan}
              </button>
              <button
                type="button"
                disabled={!canReject || statusMutation.isPending}
                onClick={() => statusMutation.mutate('rejected')}
                className="rounded-lg bg-rose-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {statusMutation.isPending ? t.optimizationPlan.updatingStatus : t.optimizationPlan.rejectPlan}
              </button>
              <button
                type="button"
                disabled={
                  !canSchedule ||
                  scheduleMutation.isPending ||
                  scheduledFor.trim().length === 0 ||
                  maintenanceWindow.trim().length === 0
                }
                onClick={() => scheduleMutation.mutate()}
                className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {scheduleMutation.isPending
                  ? t.optimizationPlan.updatingStatus
                  : t.optimizationPlan.schedulePlan}
              </button>
              <button
                type="button"
                disabled={
                  !canHandoff ||
                  handoffMutation.isPending ||
                  targetEnvironment.trim().length === 0 ||
                  targetCriticality.trim().length === 0
                }
                onClick={() => handoffMutation.mutate()}
                className="rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {handoffMutation.isPending
                  ? t.optimizationPlan.updatingStatus
                  : t.optimizationPlan.sendToPulseLab}
              </button>
            </div>

            {latestExecutionPlan.pulselab_experiment_id ? (
              <div className="text-xs text-violet-300">
                {t.optimizationPlan.handoffExperimentId}: {latestExecutionPlan.pulselab_experiment_id}
              </div>
            ) : null}

            {executionStatus ? (
              <div className="rounded-lg border border-violet-900/50 bg-violet-900/10 p-3">
                <div className="text-xs font-medium uppercase tracking-wide text-violet-300">
                  {t.optimizationPlan.executionTrackingTitle}
                </div>
                <div className="mt-1 text-xs text-gray-400">{t.optimizationPlan.executionTrackingSubtitle}</div>
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  <div className="text-xs text-gray-300">
                    {t.optimizationPlan.experimentStatusLabel}:{' '}
                    {executionStatusLabel(executionStatus.status, t)}
                  </div>
                  <div className="text-xs text-gray-300">
                    {t.optimizationPlan.executionOutcomeLabel}:{' '}
                    {executionOutcomeLabel(executionStatus.outcome, t)}
                  </div>
                  <div className="text-xs text-gray-300">
                    {t.optimizationPlan.expectedSavingsLabel}:{' '}
                    {currency.format(executionStatus.expected_savings)}
                  </div>
                  <div className="text-xs text-gray-300">
                    {t.optimizationPlan.actualSavingsLabel}: {currency.format(executionStatus.actual_savings)}
                  </div>
                  <div className="text-xs text-gray-300">
                    {t.optimizationPlan.deltaSavingsLabel}:{' '}
                    <span className={executionStatus.delta >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
                      {currency.format(executionStatus.delta)}
                    </span>
                  </div>
                </div>
              </div>
            ) : null}

            {statusMessage ? <div className="text-xs text-gray-300">{statusMessage}</div> : null}

            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
                {t.optimizationPlan.timeline}
              </div>
              <ul className="space-y-2 text-sm">
                {timelineItems.map((item) => (
                  <li key={item.key} className="flex items-center gap-2 text-gray-300">
                    <span
                      className={`h-2.5 w-2.5 rounded-full ${
                        item.current
                          ? 'bg-brand-400'
                          : item.active
                            ? 'bg-emerald-400'
                            : 'bg-gray-600'
                      }`}
                    />
                    <span>{item.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <div className="text-sm font-medium text-gray-200">{t.optimizationPlan.summary}</div>
        <p className="mt-2 text-sm text-gray-300">{data.summary}</p>
      </section>

      {data.conflict_hints.length > 0 && (
        <section className="rounded-xl border border-amber-700/60 bg-amber-900/10 p-4">
          <div className="text-sm font-medium text-amber-300">{t.optimizationPlan.conflictHints}</div>
          <ul className="mt-2 space-y-1 text-sm text-amber-100">
            {data.conflict_hints.map((hint) => (
              <li key={hint}>- {hint}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-xl border border-gray-800 bg-gray-900">
        <div className="border-b border-gray-800 px-4 py-3 text-sm font-medium text-gray-200">
          {t.optimizationPlan.prioritized}
        </div>
        <div className="divide-y divide-gray-800">
          {data.prioritized.map((item) => (
            <article key={item.opportunity_id} className="space-y-1 px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-medium text-white">
                  #{item.rank} {item.title}
                </div>
                <div className="text-xs text-gray-300">
                  {t.optimizationPlan.score}: {item.priority_score.toFixed(3)}
                </div>
              </div>
              <div className="text-xs text-gray-400">
                {t.optimizationPlan.savings}: {currency.format(item.estimated_monthly_savings_usd)} / {t.common.monthly}
              </div>
              <div className="text-xs text-gray-500">{item.why_now}</div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      <div className="text-xs uppercase tracking-wide text-gray-400">{label}</div>
      <div className="mt-1 text-xl font-semibold text-white">{value}</div>
    </div>
  )
}

function statusLabel(status: ExecutionPlanStatus, t: ReturnType<typeof useI18n>['t']): string {
  if (status === 'review_required') return t.optimizationPlan.statusReviewRequired
  if (status === 'blocked') return t.optimizationPlan.statusBlocked
  if (status === 'approved') return t.optimizationPlan.statusApproved
  if (status === 'scheduled') return t.optimizationPlan.statusScheduled
  if (status === 'rejected') return t.optimizationPlan.statusRejected
  return t.optimizationPlan.statusUnknown
}

function statusBadgeClassName(status: ExecutionPlanStatus): string {
  if (status === 'approved') {
    return 'inline-flex rounded-full bg-emerald-900/50 px-2.5 py-1 text-xs font-medium text-emerald-300'
  }
  if (status === 'rejected') {
    return 'inline-flex rounded-full bg-rose-900/50 px-2.5 py-1 text-xs font-medium text-rose-300'
  }
  if (status === 'blocked') {
    return 'inline-flex rounded-full bg-amber-900/50 px-2.5 py-1 text-xs font-medium text-amber-300'
  }
  if (status === 'scheduled') {
    return 'inline-flex rounded-full bg-indigo-900/50 px-2.5 py-1 text-xs font-medium text-indigo-300'
  }
  return 'inline-flex rounded-full bg-sky-900/50 px-2.5 py-1 text-xs font-medium text-sky-300'
}

function executionStatusLabel(
  status: 'running' | 'completed' | 'failed',
  t: ReturnType<typeof useI18n>['t']
): string {
  if (status === 'running') return t.optimizationPlan.executionStatusRunning
  if (status === 'completed') return t.optimizationPlan.executionStatusCompleted
  return t.optimizationPlan.executionStatusFailed
}

function executionOutcomeLabel(
  outcome: 'success' | 'partial' | 'failed',
  t: ReturnType<typeof useI18n>['t']
): string {
  if (outcome === 'success') return t.optimizationPlan.executionOutcomeSuccess
  if (outcome === 'partial') return t.optimizationPlan.executionOutcomePartial
  return t.optimizationPlan.executionOutcomeFailed
}
