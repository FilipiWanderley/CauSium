import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, XCircle, ServerCog, Activity, Database, Cpu, HardDrive } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'
import { usePageTitle } from '../../hooks/usePageTitle'
import { integrationHealthApi } from '../../api/integrationHealth'
import type { FinOpsReadinessResponse, RecommendationReadiness } from '../../api/integrationHealth'
import { useI18n } from '../../contexts/I18nContext'
import { KpiCard } from '../../components/Cards/KpiCard'
import { PageHeader } from '../../components/Layout/PageHeader'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { ErrorState } from '../../components/UX/ErrorState'
import { SkeletonMetricCards, SkeletonSection } from '../../components/UX/Skeleton'

type HealthStatus = 'healthy' | 'warning' | 'blocked' | 'not_configured'

function getOverallStatus(data: FinOpsReadinessResponse): HealthStatus {
  const r = data.recommendation_readiness
  if (r.blockers.length === 0 && r.vm_rightsizing_ready && r.aks_rightsizing_ready) return 'healthy'
  if (r.blockers.length > 0 && data.cost_coverage.total_cost_facts_30d === 0) return 'not_configured'
  if (r.blockers.length > 0) return 'blocked'
  return 'warning'
}

function StatusBadge({ status }: { status: HealthStatus }) {
  const colors: Record<HealthStatus, string> = {
    healthy: 'bg-green-100 text-green-800 border-green-200',
    warning: 'bg-amber-50 text-amber-800 border-amber-200',
    blocked: 'bg-red-50 text-red-800 border-red-200',
    not_configured: 'bg-gray-100 text-gray-600 border-gray-200',
  }
  const labels: Record<HealthStatus, string> = {
    healthy: 'Healthy',
    warning: 'Needs follow-up',
    blocked: 'Blocked',
    not_configured: 'Not configured',
  }
  return (
    <span className={clsx('inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium', colors[status])}>
      {status === 'healthy' && <CheckCircle2 className="h-3 w-3" />}
      {status === 'warning' && <AlertTriangle className="h-3 w-3" />}
      {status === 'blocked' && <XCircle className="h-3 w-3" />}
      {status === 'not_configured' && <ServerCog className="h-3 w-3" />}
      {labels[status]}
    </span>
  )
}

function ReadinessIndicator({ ready, label }: { ready: boolean; label: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50/70 px-4 py-3">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {ready ? (
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
          <CheckCircle2 className="h-3.5 w-3.5" /> Ready
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700">
          <XCircle className="h-3.5 w-3.5" /> Action needed
        </span>
      )}
    </div>
  )
}

function MetricRow({ label, value, status }: { label: string; value: string; status: HealthStatus }) {
  const dot: Record<HealthStatus, string> = {
    healthy: 'bg-green-500',
    warning: 'bg-amber-500',
    blocked: 'bg-red-500',
    not_configured: 'bg-gray-400',
  }
  return (
    <div className="flex items-start justify-between gap-3 border-b border-slate-100 py-2 last:border-0">
      <div className="flex min-w-0 items-center gap-2">
        <span className={clsx('h-2 w-2 rounded-full', dot[status])} />
        <span className="text-sm text-slate-600">{label}</span>
      </div>
      <span className="text-right text-sm font-semibold tabular-nums text-slate-900">{value}</span>
    </div>
  )
}

function SummaryBanner({ data }: { data: FinOpsReadinessResponse }) {
  const status = getOverallStatus(data)
  const blockerCount = data.recommendation_readiness.blockers.length
  const warningCount = data.recommendation_readiness.warnings.length
  const messages: Record<HealthStatus, string> = {
    healthy: 'Cost, usage, and recommendation telemetry are aligned for this workspace.',
    warning: 'Core integrations are online, but some FinOps readiness signals still need attention.',
    blocked: 'Key telemetry is missing, so recommendation coverage is not fully ready yet.',
    not_configured: 'No cloud account is configured for this workspace yet.',
  }
  const bannerColors: Record<HealthStatus, string> = {
    healthy: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    warning: 'border-amber-200 bg-amber-50 text-amber-900',
    blocked: 'border-rose-200 bg-rose-50 text-rose-900',
    not_configured: 'border-slate-200 bg-slate-50 text-slate-700',
  }
  return (
    <div className={clsx('rounded-xl border px-4 py-3', bannerColors[status])}>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <StatusBadge status={status} />
          <div className="space-y-1">
            <p className="text-sm font-semibold">
              {status === 'healthy' && 'FinOps readiness is on track'}
              {status === 'warning' && 'FinOps readiness needs follow-up'}
              {status === 'blocked' && 'FinOps readiness is blocked'}
              {status === 'not_configured' && 'FinOps readiness has not started'}
            </p>
            <p className="text-sm/6">{messages[status]}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium">
          <span className="rounded-full border border-current/10 bg-white/70 px-2.5 py-1">
            {blockerCount} blocking gap{blockerCount === 1 ? '' : 's'}
          </span>
          <span className="rounded-full border border-current/10 bg-white/70 px-2.5 py-1">
            {warningCount} watch item{warningCount === 1 ? '' : 's'}
          </span>
        </div>
      </div>
    </div>
  )
}

function GuidanceSection({ readiness }: { readiness: RecommendationReadiness }) {
  if (readiness.blockers.length === 0 && readiness.warnings.length === 0) return null

  const guidanceMap: Record<string, string> = {
    'Missing CPU metrics in usage_facts': 'Enable Azure Monitor CPU metrics on your virtual machines.',
    'Missing Memory metrics in usage_facts': 'Enable Azure Monitor memory metrics (guest metrics) on your virtual machines.',
    'No AKS agentPool metrics found in usage_facts': 'Enable Container Insights on your AKS clusters to collect node pool metrics.',
    'No cost data in last 30 days': 'Verify your cloud account connection and ensure cost export is configured.',
  }

  return (
    <div className="space-y-3">
      {readiness.blockers.length > 0 && (
        <div className="rounded-xl border border-red-100 bg-red-50 p-4">
          <h4 className="mb-2 text-sm font-semibold text-red-900">Blocking readiness gaps</h4>
          <ul className="space-y-2">
            {readiness.blockers.map((b, i) => (
              <li key={i} className="flex items-start gap-2">
                <XCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                <div>
                  <span className="text-sm text-red-700">{b}</span>
                  {guidanceMap[b] && (
                    <p className="text-xs text-red-600 mt-0.5">{guidanceMap[b]}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      {readiness.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-100 bg-amber-50 p-4">
          <h4 className="mb-2 text-sm font-semibold text-amber-900">Watch items</h4>
          <ul className="space-y-2">
            {readiness.warnings.map((w, i) => (
              <li key={i} className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                <span className="text-sm text-amber-700">{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export function IntegrationHealthPage() {
  const { user } = useAuth()
  const { t } = useI18n()
  usePageTitle(t.platform.integrationHealthTitle)

  if (user?.role !== 'platform_admin') {
    return <Navigate to="/app/dashboard" replace />
  }

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['finops-readiness'],
    queryFn: () => integrationHealthApi.getReadiness().then((r) => r.data),
    refetchInterval: 60000,
    retry: 2,
  })

  if (isLoading) {
    return (
      <div className="page-container">
        <SkeletonSection lines={2} />
        <SkeletonMetricCards count={4} />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="page-container">
        <PageHeader
          title={t.platform.integrationHealthTitle}
          subtitle={t.platform.integrationHealthSubtitle}
          meta={
            <>
              <span>FinOps readiness</span>
              <span>Telemetry coverage</span>
            </>
          }
        />
        <ErrorState
          title="Could not load FinOps readiness"
          description="FinOps readiness signals are temporarily unavailable for this workspace. Please try again."
          onRetry={() => refetch()}
          retryLabel="Retry"
        />
      </div>
    )
  }

  const costStatus: HealthStatus = data.cost_coverage.total_cost_facts_30d > 0
    ? (data.data_freshness.cost_data_stale ? 'warning' : 'healthy')
    : 'not_configured'

  const usageStatus: HealthStatus = data.usage_coverage.has_cpu_metric && data.usage_coverage.has_memory_metric
    ? (data.usage_coverage.observation_days >= 7 ? 'healthy' : 'warning')
    : (data.usage_coverage.total_usage_facts_30d > 0 ? 'blocked' : 'not_configured')

  const formatUsd = (val: number) =>
    val.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

  const overallStatus = getOverallStatus(data)
  const summaryCards = [
    {
      title: 'Cost coverage',
      value: data.cost_coverage.total_cost_facts_30d.toLocaleString(),
      tone: costStatus === 'healthy' ? 'positive' : costStatus === 'warning' ? 'warning' : 'neutral',
      footer: <span>{data.data_freshness.cost_data_stale ? 'Cost coverage is stale and should be refreshed.' : 'Cost coverage is current.'}</span>,
    },
    {
      title: 'Usage coverage',
      value: data.usage_coverage.total_usage_facts_30d.toLocaleString(),
      tone: usageStatus === 'healthy' ? 'positive' : usageStatus === 'warning' ? 'warning' : 'negative',
      footer: <span>{`${data.usage_coverage.observation_days} day observation window available.`}</span>,
    },
    {
      title: 'Recommendation coverage',
      value: data.opportunities.open_opportunities,
      tone: data.opportunities.open_opportunities > 0 ? 'positive' : 'neutral',
      footer: <span>{`${data.opportunities.generated_recently_count} recommendations generated in the last 7 days.`}</span>,
    },
    {
      title: 'FinOps readiness',
      value: overallStatus === 'not_configured' ? 'Not configured' : overallStatus.replace('_', ' '),
      tone: overallStatus === 'healthy' ? 'positive' : overallStatus === 'warning' ? 'warning' : overallStatus === 'blocked' ? 'negative' : 'neutral',
      footer: <span>{`Assessed ${new Date(data.assessed_at).toLocaleString()}.`}</span>,
    },
  ] as const

  return (
    <div className="page-container">
      <PageHeader
        title={t.platform.integrationHealthTitle}
        subtitle={t.platform.integrationHealthSubtitle}
        meta={
          <>
            <span>FinOps readiness</span>
            <span>Telemetry coverage</span>
          </>
        }
      />

      <SummaryBanner data={data} />

      <div className="kpi-grid">
        {summaryCards.map((card) => (
          <KpiCard
            key={card.title}
            title={card.title}
            value={card.value}
            tone={card.tone}
            compact
            footer={card.footer}
          />
        ))}
      </div>

      <p className="text-xs text-slate-500">
        Read the FinOps readiness posture from top to bottom: confirm overall state first, then validate cost and usage coverage before reviewing recommendation output and next steps.
      </p>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <Panel flush className="overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4">
            <PanelHeader
              title="Cost data coverage"
              subtitle="Confirm that normalized billing data is present, current, and broad enough to support customer-facing spend reporting."
              badge={<StatusBadge status={costStatus} />}
            />
          </div>
          <div className="px-5 py-4">
            <MetricRow
              label="Cost records (30d)"
              value={data.cost_coverage.total_cost_facts_30d.toLocaleString()}
              status={data.cost_coverage.total_cost_facts_30d > 0 ? 'healthy' : 'not_configured'}
            />
            <MetricRow
              label="Monthly cost (USD normalized)"
              value={formatUsd(data.cost_coverage.total_cost_30d_usd)}
              status={data.cost_coverage.total_cost_30d_usd > 500 ? 'healthy' : 'warning'}
            />
            <MetricRow
              label="Providers"
              value={data.cost_coverage.providers.length > 0 ? data.cost_coverage.providers.join(', ') : 'No providers'}
              status={data.cost_coverage.providers.length > 0 ? 'healthy' : 'not_configured'}
            />
            <MetricRow
              label="Subscriptions"
              value={String(data.cost_coverage.subscriptions_count)}
              status={data.cost_coverage.subscriptions_count > 0 ? 'healthy' : 'not_configured'}
            />
            <MetricRow
              label="Data freshness"
              value={data.data_freshness.cost_data_stale ? 'Stale' : 'Fresh'}
              status={data.data_freshness.cost_data_stale ? 'warning' : 'healthy'}
            />
          </div>
        </Panel>

        <Panel flush className="overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4">
            <PanelHeader
              title="Usage telemetry coverage"
              subtitle="Confirm that compute and cluster telemetry is complete enough for analytics and recommendation workflows."
              badge={<StatusBadge status={usageStatus} />}
            />
          </div>
          <div className="px-5 py-4">
            <MetricRow
              label="Usage records (30d)"
              value={data.usage_coverage.total_usage_facts_30d.toLocaleString()}
              status={data.usage_coverage.total_usage_facts_30d > 0 ? 'healthy' : 'not_configured'}
            />
            <MetricRow
              label="CPU metrics"
              value={data.usage_coverage.has_cpu_metric ? 'Available' : 'Missing'}
              status={data.usage_coverage.has_cpu_metric ? 'healthy' : 'blocked'}
            />
            <MetricRow
              label="Memory metrics"
              value={data.usage_coverage.has_memory_metric ? 'Available' : 'Missing'}
              status={data.usage_coverage.has_memory_metric ? 'healthy' : 'blocked'}
            />
            <MetricRow
              label="AKS node pool metrics"
              value={data.usage_coverage.has_aks_agentpool_metrics
                ? `${data.usage_coverage.agentpool_resource_count} pools`
                : 'Missing'}
              status={data.usage_coverage.has_aks_agentpool_metrics ? 'healthy' : 'blocked'}
            />
            <MetricRow
              label="Observation window"
              value={`${data.usage_coverage.observation_days} days`}
              status={data.usage_coverage.observation_days >= 7 ? 'healthy' : 'warning'}
            />
          </div>
        </Panel>

        <Panel flush className="overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4">
            <PanelHeader
              title="Recommendation readiness"
              subtitle="Track whether each engine has the telemetry it needs to produce customer-safe FinOps recommendations."
            />
          </div>
          <div className="space-y-2 p-5">
            <ReadinessIndicator ready={data.recommendation_readiness.vm_rightsizing_ready} label="VM Rightsizing" />
            <ReadinessIndicator ready={data.recommendation_readiness.aks_rightsizing_ready} label="AKS Nodepool Rightsizing" />
            <ReadinessIndicator ready={data.recommendation_readiness.autoscaler_ready} label="AKS Autoscaler" />
          </div>
        </Panel>

        <Panel flush className="overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4">
            <PanelHeader
              title="Recommendation output coverage"
              subtitle="Validate that recommendations and export volume are available for downstream review and reporting."
            />
          </div>
          <div className="px-5 py-4">
            <MetricRow
              label="Total opportunities"
              value={String(data.opportunities.total_opportunities)}
              status={data.opportunities.total_opportunities > 0 ? 'healthy' : 'not_configured'}
            />
            <MetricRow
              label="Open"
              value={String(data.opportunities.open_opportunities)}
              status={data.opportunities.open_opportunities > 0 ? 'healthy' : 'warning'}
            />
            <MetricRow
              label="Generated recently (7d)"
              value={String(data.opportunities.generated_recently_count)}
              status={data.opportunities.generated_recently_count > 0 ? 'healthy' : 'warning'}
            />
            <MetricRow
              label="CSV export"
              value={data.export_readiness.csv_export_ready ? `${data.export_readiness.csv_export_expected_rows} rows` : 'Empty'}
              status={data.export_readiness.csv_export_ready ? 'healthy' : 'warning'}
            />
          </div>
        </Panel>
      </div>

      <Panel>
        <PanelHeader
          title="Recommended next steps"
          subtitle="Use the current readiness gaps to restore full coverage without leaving this surface."
        />
        <div className="mt-4">
          <GuidanceSection readiness={data.recommendation_readiness} />
        </div>
      </Panel>

      <p className="text-right text-xs text-slate-400">
        Last FinOps readiness assessment: {new Date(data.assessed_at).toLocaleString()}
      </p>
    </div>
  )
}
