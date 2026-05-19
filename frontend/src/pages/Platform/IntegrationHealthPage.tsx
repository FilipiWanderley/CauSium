import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, XCircle, ServerCog, Activity, Database, Cpu, HardDrive } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../hooks/useAuth'
import { usePageTitle } from '../../hooks/usePageTitle'
import { integrationHealthApi } from '../../api/integrationHealth'
import type { FinOpsReadinessResponse, RecommendationReadiness } from '../../api/integrationHealth'
import { useI18n } from '../../contexts/I18nContext'
import { ErrorState } from '../../components/UX/ErrorState'
import { SkeletonMetricCards } from '../../components/UX/Skeleton'

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
    warning: 'Warning',
    blocked: 'Blocked',
    not_configured: 'Not Configured',
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
    <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm">
      <span className="text-sm text-gray-700">{label}</span>
      {ready ? (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700">
          <CheckCircle2 className="h-3.5 w-3.5" /> Ready
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600">
          <XCircle className="h-3.5 w-3.5" /> Not Ready
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
    <div className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
      <div className="flex items-center gap-2">
        <span className={clsx('h-2 w-2 rounded-full', dot[status])} />
        <span className="text-sm text-gray-600">{label}</span>
      </div>
      <span className="text-sm font-medium tabular-nums text-gray-900">{value}</span>
    </div>
  )
}

function SummaryBanner({ data }: { data: FinOpsReadinessResponse }) {
  const status = getOverallStatus(data)
  const messages: Record<HealthStatus, string> = {
    healthy: 'All readiness checks are passing. Telemetry coverage is sufficient for the recommendation engines.',
    warning: 'Readiness is partial. Some telemetry coverage is limited.',
    blocked: 'Readiness is blocked. Critical telemetry data is missing.',
    not_configured: 'No cloud integration is configured for this workspace yet.',
  }
  const bannerColors: Record<HealthStatus, string> = {
    healthy: 'bg-green-50 border-green-200 text-green-900',
    warning: 'bg-amber-50 border-amber-200 text-amber-900',
    blocked: 'bg-red-50 border-red-200 text-red-900',
    not_configured: 'bg-gray-50 border-gray-200 text-gray-700',
  }
  return (
    <div className={clsx('rounded-xl border px-4 py-3', bannerColors[status])}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusBadge status={status} />
          <span className="text-sm">{messages[status]}</span>
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
          <h4 className="text-sm font-medium text-red-800 mb-2">Blockers</h4>
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
          <h4 className="text-sm font-medium text-amber-800 mb-2">Warnings</h4>
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
  usePageTitle('Integration Health')
  const { user } = useAuth()
  const { t } = useI18n()

  if (user?.role !== 'platform_admin') {
    return <Navigate to="/app/dashboard" replace />
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ['finops-readiness'],
    queryFn: () => integrationHealthApi.getReadiness().then((r) => r.data),
    refetchInterval: 60000,
    retry: 2,
  })

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
          <div className="h-6 w-56 rounded bg-gray-200 animate-pulse" />
          <div className="mt-2 h-4 w-96 rounded bg-gray-100 animate-pulse" />
        </div>
        <SkeletonMetricCards count={4} />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-gray-900">{t.platform.integrationHealthTitle}</h1>
          <p className="mt-1.5 text-sm leading-relaxed text-gray-500">{t.platform.integrationHealthSubtitle}</p>
        </header>
        <ErrorState
          title="Could not load integration health"
          description="Diagnostics are temporarily unavailable for this workspace. Please try again."
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

  const formatCurrency = (val: number) =>
    val.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-gray-900">{t.platform.integrationHealthTitle}</h1>
        <p className="mt-1.5 text-sm leading-relaxed text-gray-500">{t.platform.integrationHealthSubtitle}</p>
      </header>

      {/* Summary Banner */}
      <SummaryBanner data={data} />

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Cost Coverage */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4">
            <Database className="h-4 w-4 text-gray-500" />
            <h3 className="text-sm font-semibold text-gray-900">Cost Coverage</h3>
            <StatusBadge status={costStatus} />
          </div>
          <div className="px-5 py-4">
            <MetricRow
              label="Cost records (30d)"
              value={data.cost_coverage.total_cost_facts_30d.toLocaleString()}
              status={data.cost_coverage.total_cost_facts_30d > 0 ? 'healthy' : 'not_configured'}
            />
            <MetricRow
              label="Monthly cost"
              value={formatCurrency(data.cost_coverage.total_cost_30d_usd)}
              status={data.cost_coverage.total_cost_30d_usd > 500 ? 'healthy' : 'warning'}
            />
            <MetricRow
              label="Providers"
              value={data.cost_coverage.providers.length > 0 ? data.cost_coverage.providers.join(', ') : 'None'}
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
        </div>

        {/* Usage Coverage */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4">
            <Activity className="h-4 w-4 text-gray-500" />
            <h3 className="text-sm font-semibold text-gray-900">Usage Coverage</h3>
            <StatusBadge status={usageStatus} />
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
        </div>

        {/* Recommendation Readiness */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4">
            <Cpu className="h-4 w-4 text-gray-500" />
            <h3 className="text-sm font-semibold text-gray-900">Recommendation Engines</h3>
          </div>
          <div className="p-5 space-y-2">
            <ReadinessIndicator ready={data.recommendation_readiness.vm_rightsizing_ready} label="VM Rightsizing" />
            <ReadinessIndicator ready={data.recommendation_readiness.aks_rightsizing_ready} label="AKS Nodepool Rightsizing" />
            <ReadinessIndicator ready={data.recommendation_readiness.autoscaler_ready} label="AKS Autoscaler" />
          </div>
        </div>

        {/* Opportunities & Export */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4">
            <HardDrive className="h-4 w-4 text-gray-500" />
            <h3 className="text-sm font-semibold text-gray-900">Opportunities & Export</h3>
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
        </div>
      </div>

      {/* Guidance */}
      <GuidanceSection readiness={data.recommendation_readiness} />

      {/* Footer */}
      <p className="text-xs text-gray-400 text-right">
        Last assessed: {new Date(data.assessed_at).toLocaleString()}
      </p>
    </div>
  )
}
