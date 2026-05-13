import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Filter } from 'lucide-react'
import clsx from 'clsx'
import { OpportunityCard } from '../../components/Cards/OpportunityCard'
import { opportunitiesApi } from '../../api/opportunities'
import { MetricCard } from '../../components/Cards/MetricCard'
import { useI18n } from '../../contexts/I18nContext'
import type { ConfidenceTier, Opportunity, OpportunityStatus, RiskLevel } from '../../types'
import { buildAzurePortalResourceUrl, parseAzureResourceId } from '../../utils/azureResource'
import { usePersistentString } from '../../hooks/usePersistentBoolean'

const fmt = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

type OpportunityViewMode = 'table' | 'cards'
type ProviderKey = 'azure' | 'aws' | 'gcp' | 'unknown'

const VIEW_MODES: OpportunityViewMode[] = ['table', 'cards']

const STATUS_COLORS: Record<OpportunityStatus, string> = {
  open: 'bg-sky-100 text-sky-700',
  in_progress: 'bg-amber-100 text-amber-700',
  resolved: 'bg-emerald-100 text-emerald-700',
  dismissed: 'bg-gray-100 text-gray-700',
  validated: 'bg-blue-100 text-blue-700',
}

const RISK_COLORS: Record<RiskLevel, string> = {
  low: 'bg-emerald-50 text-emerald-700',
  medium: 'bg-amber-50 text-amber-700',
  high: 'bg-red-50 text-red-700',
}

const CONFIDENCE_COLORS: Record<ConfidenceTier, string> = {
  high: 'bg-slate-100 text-slate-700',
  medium: 'bg-slate-50 text-slate-600',
  low: 'bg-amber-50 text-amber-700',
  insufficient: 'bg-gray-100 text-gray-600',
}

function humanizeToken(value: string) {
  return value
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function truncateMiddle(value: string, maxLength = 30) {
  if (value.length <= maxLength) return value
  const head = Math.max(8, Math.floor((maxLength - 1) / 2))
  const tail = Math.max(8, maxLength - head - 1)
  return `${value.slice(0, head)}…${value.slice(-tail)}`
}

function formatOpportunityTimestamp(value: string, lang: 'pt' | 'en') {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(lang === 'pt' ? 'pt-BR' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`
}

function getFallbackConfidenceTier(value: number | null | undefined): ConfidenceTier {
  if (value == null) return 'insufficient'
  if (value >= 0.8) return 'high'
  if (value >= 0.55) return 'medium'
  return 'low'
}

function getOpportunityConfidenceTier(opportunity: Opportunity): ConfidenceTier {
  return (
    opportunity.savings_evidence?.confidence_tier ??
    getFallbackConfidenceTier(opportunity.savings_evidence?.savings_confidence ?? opportunity.decision_evidence?.confidence)
  )
}

function getOpportunityConfidenceScore(opportunity: Opportunity) {
  return opportunity.savings_evidence?.savings_confidence ?? opportunity.decision_evidence?.confidence ?? null
}

function getOpportunityRiskLevel(opportunity: Opportunity): RiskLevel {
  return opportunity.savings_evidence?.risk_level ?? opportunity.decision_evidence?.risk_level ?? opportunity.risk_level
}

function normalizeProviderKey(value: string | null | undefined): ProviderKey {
  const normalized = value?.trim().toLowerCase()
  if (normalized === 'azure') return 'azure'
  if (normalized === 'aws') return 'aws'
  if (normalized === 'gcp' || normalized === 'google' || normalized === 'google_cloud') return 'gcp'
  return 'unknown'
}

function inferOpportunityProvider(opportunity: Opportunity): ProviderKey {
  const contextProvider = normalizeProviderKey(opportunity.resource_context?.provider)
  if (contextProvider !== 'unknown') return contextProvider
  const resourceId = opportunity.resource_id?.toLowerCase() ?? ''
  const service = opportunity.service?.toLowerCase() ?? ''
  const resourceType = opportunity.decision_evidence?.resource_type?.toLowerCase() ?? ''

  if (
    resourceId.startsWith('/subscriptions/') ||
    resourceType.includes('aks') ||
    opportunity.category === 'aks_autoscaler_recommendation' ||
    opportunity.category === 'aks_nodepool_rightsizing'
  ) {
    return 'azure'
  }
  if (resourceId.startsWith('arn:') || service.includes('amazon') || service.includes('aws')) {
    return 'aws'
  }
  if (resourceId.startsWith('projects/') || service.includes('google') || service.includes('gcp')) {
    return 'gcp'
  }
  return 'unknown'
}

function getOpportunityScope(opportunity: Opportunity, unknownLabel: string) {
  const resourceContext = opportunity.resource_context
  const parsedResource = parseAzureResourceId(opportunity.resource_id)
  return {
    primary:
      resourceContext?.resource_name ??
      parsedResource?.resourceName ??
      opportunity.resource_name ??
      opportunity.service ??
      unknownLabel,
    secondary:
      resourceContext?.subscription_name ??
      resourceContext?.resource_group ??
      parsedResource?.resourceGroup ??
      opportunity.environment ??
      (opportunity.resource_id ? truncateMiddle(opportunity.resource_id) : null),
    resourceGroup: resourceContext?.resource_group ?? parsedResource?.resourceGroup ?? null,
    resourceType: resourceContext?.resource_type ?? opportunity.decision_evidence?.resource_type ?? null,
    subscription: resourceContext?.subscription_name ?? null,
    sku: resourceContext?.sku ?? opportunity.sku_name ?? null,
  }
}

function buildOpportunitiesExportFileName() {
  return `causium-opportunities-export-${new Date().toISOString().slice(0, 10)}.csv`
}

async function getExportErrorMessage(error: unknown, fallback: string) {
  const responseData = (error as { response?: { data?: Blob | { detail?: string; message?: string } } })?.response?.data

  if (responseData instanceof Blob) {
    try {
      const text = await responseData.text()
      const parsed = JSON.parse(text) as { detail?: string; message?: string }
      return parsed.detail || parsed.message || fallback
    } catch {
      return fallback
    }
  }

  if (responseData && typeof responseData === 'object') {
    return responseData.detail || responseData.message || fallback
  }

  return fallback
}

export function OpportunitiesPage() {
  const { t, lang } = useI18n()
  const o = t.opportunities
  const queryClient = useQueryClient()
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<OpportunityStatus | 'all'>('open')
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null)
  const [explainOpp, setExplainOpp] = useState<Opportunity | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const [viewModeRaw, setViewModeRaw] = usePersistentString('sp.opportunities.view', 'table')
  const viewMode: OpportunityViewMode = VIEW_MODES.includes(viewModeRaw as OpportunityViewMode)
    ? (viewModeRaw as OpportunityViewMode)
    : 'table'

  const categories = [
    { value: '', label: o.allCategories },
    { value: 'rightsizing', label: o.rightsizing },
    { value: 'aks_autoscaler_recommendation', label: o.aksAutoscalerRecommendation },
    { value: 'idle_resources', label: o.idleResources },
    { value: 'reserved_instances', label: o.reservedInstances },
    { value: 'storage_optimization', label: o.storage },
    { value: 'network_optimization', label: o.network },
  ]
  const statusLabels: Record<OpportunityStatus, string> = {
    open: o.statusOpenSuggestion,
    in_progress: o.statusInProgressReview,
    resolved: o.statusResolvedApproved,
    dismissed: o.statusDismissed,
    validated: o.statusValidated,
  }

  const { data: summary } = useQuery({
    queryKey: ['opportunities', 'summary'],
    queryFn: () => opportunitiesApi.summary().then((r) => r.data),
  })

  const { data: opportunities, isLoading } = useQuery({
    queryKey: ['opportunities', selectedCategory, selectedStatus],
    queryFn: () =>
      opportunitiesApi
        .list({
          category: selectedCategory || undefined,
          status: selectedStatus === 'all' ? undefined : selectedStatus,
        })
        .then((r) => r.data.items),
  })

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: OpportunityStatus }) =>
      opportunitiesApi.updateStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      setSelectedOpp(null)
    },
  })
  const explainMutation = useMutation({
    mutationFn: ({ id, language }: { id: string; language: 'pt' | 'en' }) =>
      opportunitiesApi.explain(id, language).then((r) => r.data),
  })
  const exportCsvMutation = useMutation({
    mutationFn: async () => {
      setExportError(null)
      try {
        return await opportunitiesApi.exportCsv({
          category: selectedCategory || undefined,
          status: selectedStatus === 'all' ? undefined : selectedStatus,
          owner_team: undefined,
        })
      } catch (error) {
        throw new Error(await getExportErrorMessage(error, o.exportCsvError))
      }
    },
    onSuccess: (response) => {
      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = buildOpportunitiesExportFileName()
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    },
    onError: (error) => {
      setExportError(error instanceof Error ? error.message : o.exportCsvError)
    },
  })

  const openExplain = (op: Opportunity) => {
    setExplainOpp(op)
    explainMutation.reset()
    explainMutation.mutate({ id: op.id, language: lang === 'pt' ? 'pt' : 'en' })
  }

  const selectedParsedResource = parseAzureResourceId(selectedOpp?.resource_id)
  const selectedAzurePortalUrl = buildAzurePortalResourceUrl(selectedOpp?.resource_id)
  const selectedResourceContext = selectedOpp?.resource_context
  const selectedMachineName = selectedParsedResource?.resourceName ?? o.unknownResource
  const selectedResourceGroup =
    selectedParsedResource?.resourceGroup ?? selectedOpp?.resource_name ?? o.unknownResource
  const selectedMachineSku = selectedOpp?.sku_name ?? o.unknownResource
  const selectedMachineFamily = selectedOpp?.machine_family ?? o.unknownResource
  const selectedEvidence = selectedOpp?.decision_evidence
  const selectedSavingsEvidence = selectedOpp?.savings_evidence
  const selectedIsAksAutoscaler = selectedOpp?.category === 'aks_autoscaler_recommendation'
  const selectedIsAksEvidence =
    selectedEvidence?.resource_type === 'aks_node_pool' ||
    !!selectedEvidence?.node_pool ||
    selectedEvidence?.current_node_count != null
  const categoryLabels: Record<string, string> = {
    rightsizing: o.rightsizing,
    aks_autoscaler_recommendation: o.aksAutoscalerRecommendation,
    idle_resources: o.idleResources,
    reserved_instances: o.reservedInstances,
    storage_optimization: o.storage,
    network_optimization: o.network,
  }
  const riskLabels: Record<RiskLevel, string> = {
    low: o.riskLow,
    medium: o.riskMedium,
    high: o.riskHigh,
  }
  const confidenceTierLabels: Record<ConfidenceTier, string> = {
    high: o.confidenceHigh,
    medium: o.confidenceMedium,
    low: o.confidenceLow,
    insufficient: o.confidenceInsufficient,
  }
  const providerLabels: Record<ProviderKey, string> = {
    azure: o.providerAzure,
    aws: o.providerAws,
    gcp: o.providerGcp,
    unknown: o.providerUnknown,
  }
  const granularityLabels = {
    resource: o.granularityResource,
    service: o.granularityCluster,
    subscription: o.granularitySubscription,
    unknown: o.granularityUnknown,
  } as const
  const selectedProviderKey = normalizeProviderKey(selectedResourceContext?.provider)
  const selectedProviderLabel =
    providerLabels[selectedProviderKey === 'unknown' ? (selectedOpp ? inferOpportunityProvider(selectedOpp) : 'unknown') : selectedProviderKey]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{o.title}</h1>
          <p className="text-sm text-gray-500 mt-1">{o.subtitle}</p>
        </div>
      </div>

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
        <p className="text-sm font-semibold text-blue-800">{o.readOnlyNoticeTitle}</p>
        <p className="mt-1 text-sm text-blue-800">{o.readOnlyNoticeDesc}</p>
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard title={o.open} value={summary.open} />
          <MetricCard title={o.inProgress} value={summary.in_progress} />
          <MetricCard title={o.resolved} value={summary.resolved} />
          <MetricCard
            title={o.totalSavings}
            value={fmt(summary.total_potential_savings_usd)}
            variant="success"
          />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Filter className="h-4 w-4 text-gray-400" />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 focus:border-brand-500 focus:outline-none"
        >
          {categories.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value as OpportunityStatus | 'all')}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 focus:border-brand-500 focus:outline-none"
        >
          <option value="all">{o.statusAll}</option>
          <option value="open">{o.statusOpenSuggestion}</option>
          <option value="in_progress">{o.statusInProgressReview}</option>
          <option value="resolved">{o.statusResolvedApproved}</option>
          <option value="dismissed">{o.statusDismissed}</option>
          <option value="validated">{o.statusValidated}</option>
        </select>
        <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => exportCsvMutation.mutate()}
            disabled={exportCsvMutation.isPending}
            className={clsx(
              'inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium shadow-sm transition-colors',
              exportCsvMutation.isPending
                ? 'cursor-wait border-gray-200 bg-gray-50 text-gray-400'
                : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400 hover:bg-gray-50',
            )}
          >
            {exportCsvMutation.isPending ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            <span>{exportCsvMutation.isPending ? o.exportCsvLoading : o.exportCsv}</span>
          </button>
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
            {o.viewTable}
          </button>
          <button
            type="button"
            onClick={() => setViewModeRaw('cards')}
            className={clsx(
              'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
              viewMode === 'cards'
                ? 'bg-slate-900 text-white'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
            )}
          >
            {o.viewCards}
          </button>
          </div>
        </div>
      </div>

      {exportError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {exportError}
        </div>
      )}

      {opportunities && opportunities.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
          <span className="font-medium text-gray-600">
            {o.summaryOpportunities.replace('{{count}}', String(opportunities.length))}
          </span>
          <span className="font-medium text-gray-600">
            {o.summaryPerMonth.replace(
              '{{amount}}',
              fmt(opportunities.reduce((s, op) => s + op.estimated_monthly_savings_usd, 0))
            )}
          </span>
          {opportunities.some((op) => op.risk_level === 'high') && (
            <span className="font-medium text-red-700">
              {o.summaryHighRisk.replace(
                '{{count}}',
                String(opportunities.filter((op) => op.risk_level === 'high').length)
              )}
            </span>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : !opportunities?.length ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 bg-white p-12 text-center">
          <p className="text-sm font-medium text-gray-700">{o.noOpportunities}</p>
          <p className="mt-1 text-xs text-gray-500">{o.noOpportunitiesHint}</p>
        </div>
      ) : viewMode === 'table' ? (
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  <th className="px-4 py-3">{o.colOpportunity}</th>
                  <th className="hidden px-4 py-3 lg:table-cell">{o.colCategory}</th>
                  <th className="hidden px-4 py-3 md:table-cell">{o.colProvider}</th>
                  <th className="hidden px-4 py-3 xl:table-cell">{o.colResourceScope}</th>
                  <th className="px-4 py-3">{o.colEstimatedMonthlySavings}</th>
                  <th className="hidden px-4 py-3 lg:table-cell">{o.colConfidence}</th>
                  <th className="hidden px-4 py-3 md:table-cell">{o.colRisk}</th>
                  <th className="px-4 py-3">{o.colStatus}</th>
                  <th className="hidden px-4 py-3 xl:table-cell">{o.colDetectedAt}</th>
                  <th className="px-4 py-3 text-right">{o.colAction}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {opportunities.map((op) => {
                  const provider = inferOpportunityProvider(op)
                  const scope = getOpportunityScope(op, o.unknownResource)
                  const confidenceScore = getOpportunityConfidenceScore(op)
                  const confidenceTier = getOpportunityConfidenceTier(op)
                  const riskLevel = getOpportunityRiskLevel(op)
                  const categoryLabel = categoryLabels[op.category] ?? humanizeToken(op.category)
                  const savingsEvidence = op.savings_evidence

                  return (
                    <tr
                      key={op.id}
                      className="cursor-pointer transition-colors hover:bg-slate-50"
                      onClick={() => setSelectedOpp(op)}
                    >
                      <td className="px-4 py-3 align-top">
                        <div className="min-w-[220px]">
                          <p className="font-medium text-gray-900">{op.title}</p>
                          <p className="mt-1 line-clamp-2 text-xs text-gray-500">{op.description}</p>
                          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-gray-500 lg:hidden">
                            <span>{categoryLabel}</span>
                            <span className="text-gray-300">•</span>
                            <span>{providerLabels[provider]}</span>
                            <span className="text-gray-300">•</span>
                            <span>{riskLabels[riskLevel]}</span>
                          </div>
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 align-top text-gray-600 lg:table-cell">{categoryLabel}</td>
                      <td className="hidden px-4 py-3 align-top md:table-cell">
                        <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                          {providerLabels[provider]}
                        </span>
                      </td>
                      <td className="hidden px-4 py-3 align-top xl:table-cell">
                        <div className="min-w-[240px]">
                          <p className="text-gray-900">{scope.primary}</p>
                          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-gray-500">
                            {scope.subscription && <span>{scope.subscription}</span>}
                            {scope.subscription && scope.resourceGroup && <span className="text-gray-300">•</span>}
                            {scope.resourceGroup && <span>{scope.resourceGroup}</span>}
                          </div>
                          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-gray-500">
                            {scope.resourceType && <span>{scope.resourceType}</span>}
                            {scope.resourceType && scope.sku && <span className="text-gray-300">•</span>}
                            {scope.sku && <span>{scope.sku}</span>}
                            {!scope.resourceType && !scope.sku && scope.secondary && <span>{scope.secondary}</span>}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="font-semibold text-emerald-700">
                          {fmt(savingsEvidence?.estimated_monthly_savings ?? op.estimated_monthly_savings_usd)}
                        </div>
                        {savingsEvidence?.current_monthly_cost_estimate != null && savingsEvidence.projected_monthly_cost_estimate != null ? (
                          <div className="mt-1 text-xs text-gray-400">
                            {fmt(savingsEvidence.current_monthly_cost_estimate)} {'->'} {fmt(savingsEvidence.projected_monthly_cost_estimate)}
                          </div>
                        ) : (
                          <div className="mt-1 text-xs text-gray-400">
                            {fmt(op.estimated_annual_savings_usd)}/yr
                          </div>
                        )}
                      </td>
                      <td className="hidden px-4 py-3 align-top lg:table-cell">
                        <div className="flex min-w-[120px] flex-col gap-1">
                          <span className={clsx('inline-flex w-fit rounded-full px-2 py-0.5 text-xs font-medium', CONFIDENCE_COLORS[confidenceTier])}>
                            {confidenceTierLabels[confidenceTier]}
                          </span>
                          <span className="text-xs text-gray-500">
                            {confidenceScore != null ? formatPercent(confidenceScore) : o.notAvailable}
                          </span>
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 align-top md:table-cell">
                        <span className={clsx('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', RISK_COLORS[riskLevel])}>
                          {riskLabels[riskLevel]}
                        </span>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <span className={clsx('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', STATUS_COLORS[op.status])}>
                          {statusLabels[op.status]}
                        </span>
                      </td>
                      <td className="hidden px-4 py-3 align-top text-gray-500 xl:table-cell">
                        {formatOpportunityTimestamp(op.created_at, lang === 'pt' ? 'pt' : 'en')}
                      </td>
                      <td className="px-4 py-3 align-top text-right">
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation()
                            setSelectedOpp(op)
                          }}
                          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:border-gray-400 hover:bg-gray-50"
                        >
                          {o.openDetail}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {opportunities.map((op) => (
            <OpportunityCard
              key={op.id}
              opportunity={op}
              onClick={() => setSelectedOpp(op)}
              onExplain={() => openExplain(op)}
            />
          ))}
        </div>
      )}

      {explainOpp && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-2xl rounded-xl border border-gray-200 bg-white shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b border-gray-100 p-5">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">{o.explainWithAI}</h2>
                <p className="mt-1 text-sm text-gray-500">{explainOpp.title}</p>
              </div>
              <button
                type="button"
                className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-50"
                onClick={() => setExplainOpp(null)}
              >
                {t.common.close}
              </button>
            </div>
            <div className="space-y-4 p-5">
              {explainMutation.isPending && (
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                  {o.explainLoading}
                </div>
              )}
              {explainMutation.isError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                  {o.explainError}
                </div>
              )}
              {explainMutation.data && (
                <div className="space-y-3">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <p className="text-sm font-medium text-gray-900">{o.explainSummary}</p>
                    <p className="mt-1 text-sm text-gray-700">{explainMutation.data.summary}</p>
                    <p className="mt-2 text-xs text-gray-500">
                      {o.confidenceLabel}: {Math.round(explainMutation.data.confidence * 100)}%
                      {explainMutation.data.model ? ` · ${explainMutation.data.model}` : ''}
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-4">
                    <p className="text-sm font-medium text-gray-900">{o.explainWhyNow}</p>
                    <p className="mt-1 text-sm text-gray-700">{explainMutation.data.why_now}</p>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-4">
                    <p className="text-sm font-medium text-gray-900">{o.explainImpact}</p>
                    <p className="mt-1 text-sm text-gray-700">{explainMutation.data.expected_impact}</p>
                  </div>
                  {explainMutation.data.risks.length > 0 && (
                    <div className="rounded-lg border border-gray-200 p-4">
                      <p className="text-sm font-medium text-gray-900">{o.explainRisks}</p>
                      <ul className="mt-2 list-disc pl-5 text-sm text-gray-700">
                        {explainMutation.data.risks.map((risk, idx) => (
                          <li key={`${risk}-${idx}`}>{risk}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {explainMutation.data.recommended_steps.length > 0 && (
                    <div className="rounded-lg border border-gray-200 p-4">
                      <p className="text-sm font-medium text-gray-900">{o.explainSteps}</p>
                      <ol className="mt-2 list-decimal pl-5 text-sm text-gray-700">
                        {explainMutation.data.recommended_steps.map((step, idx) => (
                          <li key={`${step}-${idx}`}>{step}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {selectedOpp && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={() => setSelectedOpp(null)} />
          <div className="relative w-full max-w-lg bg-white shadow-2xl overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">{o.detailTitle}</h2>
              <button onClick={() => setSelectedOpp(null)} className="text-gray-400 hover:text-gray-600">
                ✕
              </button>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <h3 className="text-lg font-bold text-gray-900">{selectedOpp.title}</h3>
                <p className="mt-2 text-sm text-gray-600">{selectedOpp.description}</p>
                <div className="mt-3 text-xs font-medium text-gray-500">
                  {o.currentStatus}: {statusLabels[selectedOpp.status]}
                </div>
              </div>

              {(selectedOpp.resource_id || selectedOpp.resource_name) && (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <h4 className="text-sm font-semibold text-gray-700">{o.targetResource}</h4>
                  <p className="mt-2 text-xs text-gray-700">
                    {o.machineName}: <strong>{selectedMachineName}</strong>
                  </p>
                  <p className="mt-1 text-xs text-gray-700">
                    {o.resourceGroup}: <strong>{selectedResourceGroup}</strong>
                  </p>
                  <p className="mt-1 text-xs text-gray-700">
                    {o.machineSku}: <strong>{selectedMachineSku}</strong>
                  </p>
                  <p className="mt-1 text-xs text-gray-700">
                    {o.machineFamily}: <strong>{selectedMachineFamily}</strong>
                  </p>
                  {selectedOpp.resource_id && (
                    <p className="mt-1 break-all text-xs text-gray-500">
                      {o.resourceId}: {selectedOpp.resource_id}
                    </p>
                  )}
                  {selectedAzurePortalUrl && (
                    <a
                      href={selectedAzurePortalUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex text-xs font-medium text-brand-600 hover:text-brand-700 hover:underline"
                    >
                      {o.openInAzure}
                    </a>
                  )}
                </div>
              )}

              {(selectedResourceContext || selectedOpp.resource_id || selectedOpp.resource_name) && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h4 className="text-sm font-semibold text-gray-900">{o.resourceContextTitle}</h4>
                      <p className="mt-1 text-xs text-gray-500">{o.resourceContextSubtitle}</p>
                    </div>
                    <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {granularityLabels[selectedResourceContext?.granularity_tier ?? 'unknown']}
                    </span>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <MetadataField
                      label={o.resourceContextProvider}
                      value={selectedProviderLabel}
                    />
                    <MetadataField
                      label={o.resourceContextSubscription}
                      value={selectedResourceContext?.subscription_name ?? undefined}
                    />
                    <MetadataField
                      label={o.resourceContextResourceGroup}
                      value={selectedResourceContext?.resource_group ?? selectedParsedResource?.resourceGroup ?? undefined}
                    />
                    <MetadataField
                      label={o.resourceContextResource}
                      value={selectedResourceContext?.resource_name ?? selectedMachineName}
                    />
                    <MetadataField
                      label={o.resourceContextResourceType}
                      value={selectedResourceContext?.resource_type ?? selectedEvidence?.resource_type ?? undefined}
                    />
                    <MetadataField
                      label={o.resourceContextSku}
                      value={selectedResourceContext?.sku ?? selectedOpp.sku_name ?? undefined}
                    />
                    <MetadataField
                      label={o.resourceContextRegion}
                      value={selectedResourceContext?.region ?? selectedOpp.region ?? undefined}
                    />
                    <MetadataField
                      label={o.resourceContextWorkload}
                      value={selectedResourceContext?.workload ?? undefined}
                    />
                    <MetadataField
                      label={o.resourceContextEnvironment}
                      value={selectedResourceContext?.environment ?? selectedOpp.environment ?? undefined}
                    />
                    <MetadataField
                      label={o.resourceContextOwner}
                      value={selectedResourceContext?.owner ?? undefined}
                    />
                  </div>

                  {(selectedResourceContext?.tags_summary && Object.keys(selectedResourceContext.tags_summary).length > 0) ||
                  selectedResourceContext?.data_sources.length ? (
                    <div className="mt-4 space-y-3 border-t border-slate-200 pt-4">
                      {selectedResourceContext?.tags_summary && Object.keys(selectedResourceContext.tags_summary).length > 0 && (
                        <div>
                          <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">
                            {o.resourceContextTagsSummary}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {Object.entries(selectedResourceContext.tags_summary).map(([key, value]) => (
                              <span
                                key={`${key}-${value}`}
                                className="inline-flex rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] text-gray-600"
                              >
                                {key}: {value}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {selectedResourceContext?.data_sources.length ? (
                        <div>
                          <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">
                            {o.resourceContextDataSources}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {selectedResourceContext.data_sources.map((source) => (
                              <span
                                key={source}
                                className="inline-flex rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-700"
                              >
                                {humanizeToken(source)}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-green-50 p-3">
                  <p className="text-xs text-gray-500">{o.monthlySavings}</p>
                  <p className="text-lg font-bold text-green-700">
                    {fmt(selectedSavingsEvidence?.estimated_monthly_savings ?? selectedOpp.estimated_monthly_savings_usd)}
                  </p>
                </div>
                <div className="rounded-lg bg-blue-50 p-3">
                  <p className="text-xs text-gray-500">{o.compositeScore}</p>
                  <p className="text-lg font-bold text-blue-700">
                    {selectedOpp.composite_score.toFixed(1)}/100
                  </p>
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900">{o.savingsEvidenceTitle}</h4>
                    <p className="mt-1 text-xs text-gray-500">{o.savingsEvidenceSubtitle}</p>
                  </div>
                  {selectedSavingsEvidence && (
                    <span
                      className={clsx(
                        'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                        CONFIDENCE_COLORS[getOpportunityConfidenceTier(selectedOpp)],
                      )}
                    >
                      {confidenceTierLabels[getOpportunityConfidenceTier(selectedOpp)]}
                    </span>
                  )}
                </div>

                {selectedSavingsEvidence ? (
                  <div className="mt-4 space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <EvidenceMetric
                        label={o.currentMonthlyCostEstimate}
                        value={fmt(selectedSavingsEvidence.current_monthly_cost_estimate)}
                      />
                      <EvidenceMetric
                        label={o.projectedMonthlyCostEstimate}
                        value={
                          selectedSavingsEvidence.projected_monthly_cost_estimate != null
                            ? fmt(selectedSavingsEvidence.projected_monthly_cost_estimate)
                            : o.notAvailable
                        }
                      />
                      <EvidenceMetric
                        label={o.estimatedSavingsEvidence}
                        value={fmt(selectedSavingsEvidence.estimated_monthly_savings)}
                      />
                      <EvidenceMetric
                        label={o.confidenceTierLabel}
                        value={`${confidenceTierLabels[selectedSavingsEvidence.confidence_tier]}${
                          selectedSavingsEvidence.savings_confidence != null
                            ? ` · ${formatPercent(selectedSavingsEvidence.savings_confidence)}`
                            : ''
                        }`}
                      />
                      <EvidenceMetric
                        label={o.riskLevelEvidence}
                        value={riskLabels[selectedSavingsEvidence.risk_level]}
                      />
                      <EvidenceMetric
                        label={o.evidenceWindowLabel}
                        value={
                          selectedSavingsEvidence.evidence_window_days != null
                            ? o.evidenceWindowDays.replace('{{days}}', String(selectedSavingsEvidence.evidence_window_days))
                            : o.notAvailable
                        }
                      />
                    </div>

                    <div className="space-y-3 border-t border-slate-200 pt-4">
                      <EvidenceBlock
                        label={o.calculationBasisLabel}
                        value={selectedSavingsEvidence.calculation_basis}
                      />
                      <EvidenceBlock
                        label={o.evidenceSummaryLabel}
                        value={selectedSavingsEvidence.evidence_summary}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 rounded-lg border border-dashed border-slate-200 bg-white p-3 text-sm text-gray-500">
                    {o.savingsEvidenceUnavailable}
                  </div>
                )}
              </div>

              {selectedOpp.score_rationale && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">{o.scoreRationale}</h4>
                  <p className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 leading-relaxed">
                    {selectedOpp.score_rationale}
                  </p>
                </div>
              )}

              {selectedOpp.playbook && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">{o.playbook}</h4>
                  <pre className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap font-sans">
                    {selectedOpp.playbook}
                  </pre>
                </div>
              )}

              <div className="border-t pt-4 space-y-2">
                <p className="text-xs text-gray-500">{o.executionOwnershipHint}</p>
              </div>

              {selectedEvidence && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                  <h4 className="text-sm font-semibold text-gray-800">
                    {selectedIsAksEvidence ? o.aksEvidenceTitle : o.rightsizingEvidenceTitle}
                  </h4>
                  {!selectedIsAksEvidence && (
                    <div className="mt-2 space-y-1 text-xs text-gray-700">
                      <p>
                        {o.currentLabel}: <strong>{selectedEvidence.current_sku ?? selectedMachineSku}</strong>
                        {'  '}→{'  '}
                        {o.recommendedLabel}: <strong>{selectedEvidence.recommended_sku ?? o.unknownResource}</strong>
                      </p>
                      <p>
                        CPU p95: <strong>{selectedEvidence.cpu_p95 ?? '-'}%</strong>
                        {'  '}·{'  '}
                        {o.memoryP95Label}: <strong>{selectedEvidence.memory_p95 ?? '-'}%</strong>
                      </p>
                      <p>
                        {o.monthlySavingsLabel}:{' '}
                        <strong>{fmt(selectedEvidence.estimated_savings ?? selectedSavingsEvidence?.estimated_monthly_savings ?? selectedOpp.estimated_monthly_savings_usd)}</strong>
                        {'  '}·{'  '}
                        {o.savingsPctLabel}: <strong>{selectedEvidence.estimated_savings_pct ?? '-'}%</strong>
                      </p>
                      <p>
                        {o.confidenceLabel}: <strong>{Math.round((selectedEvidence.confidence ?? selectedSavingsEvidence?.savings_confidence ?? 0) * 100)}%</strong>
                        {'  '}·{'  '}
                        {o.riskLabel}: <strong>{selectedEvidence.risk_level ?? selectedSavingsEvidence?.risk_level ?? selectedOpp.risk_level}</strong>
                      </p>
                      {selectedEvidence.reason && (
                        <p>
                          {o.reasonLabel}: <strong>{selectedEvidence.reason}</strong>
                        </p>
                      )}
                    </div>
                  )}
                  {selectedIsAksEvidence && (
                    <div className="mt-2 space-y-1 text-xs text-gray-700">
                      <p>
                        {o.clusterLabel}: <strong>{selectedEvidence.cluster_name ?? o.unknownResource}</strong>
                        {'  '}·{'  '}
                        {o.nodePoolLabel}: <strong>{selectedEvidence.node_pool ?? o.unknownResource}</strong>
                      </p>
                      {!selectedIsAksAutoscaler && (
                        <p>
                          {o.nodesLabel}: <strong>{selectedEvidence.current_node_count ?? '-'}</strong>
                          {'  '}→{'  '}
                          {o.recommendedLabel}: <strong>{selectedEvidence.recommended_node_count ?? '-'}</strong>
                        </p>
                      )}
                      {selectedIsAksAutoscaler && (
                        <p>
                          {o.currentLabel}: <strong>{selectedEvidence.current_node_count ?? '-'} nodes fixos</strong>
                          {'  '}·{'  '}
                          {o.recommendedLabel}:{' '}
                          <strong>
                            min={selectedEvidence.recommended_min_count ?? '-'}, max={selectedEvidence.recommended_max_count ?? '-'}
                          </strong>
                        </p>
                      )}
                      <p>
                        {o.skuLabel}: <strong>{selectedEvidence.node_sku ?? selectedMachineSku}</strong>
                      </p>
                      <p>
                        CPU p95: <strong>{selectedEvidence.cpu_p95 ?? '-'}%</strong>
                        {'  '}·{'  '}
                        {o.memoryP95Label}: <strong>{selectedEvidence.memory_p95 ?? '-'}%</strong>
                      </p>
                      <p>
                        {o.monthlySavingsLabel}:{' '}
                        <strong>{fmt(selectedEvidence.estimated_savings ?? selectedSavingsEvidence?.estimated_monthly_savings ?? selectedOpp.estimated_monthly_savings_usd)}</strong>
                        {'  '}·{'  '}
                        {o.savingsPctLabel}: <strong>{selectedEvidence.estimated_savings_pct ?? '-'}%</strong>
                      </p>
                      <p>
                        {o.confidenceLabel}: <strong>{Math.round((selectedEvidence.confidence ?? selectedSavingsEvidence?.savings_confidence ?? 0) * 100)}%</strong>
                        {'  '}·{'  '}
                        {o.riskLabel}: <strong>{selectedEvidence.risk_level ?? selectedSavingsEvidence?.risk_level ?? selectedOpp.risk_level}</strong>
                      </p>
                      {selectedIsAksAutoscaler && (
                        <p>
                          Variability: <strong>{selectedEvidence.variability_score ?? '-'}</strong>
                        </p>
                      )}
                      {selectedEvidence.reason && (
                        <p>
                          {o.reasonLabel}: <strong>{selectedEvidence.reason}</strong>
                        </p>
                      )}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => openExplain(selectedOpp)}
                    className="mt-3 rounded-lg border border-brand-300 bg-white px-3 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-50"
                  >
                    {o.explainWithAI}
                  </button>
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'in_progress' })}
                  className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
                >
                  {o.markInReview}
                </button>
                <button
                  onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'resolved' })}
                  className="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700"
                >
                  {o.markApproved}
                </button>
                <button
                  onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'validated' })}
                  className="rounded-lg border border-blue-300 px-4 py-2 text-sm text-blue-700 hover:bg-blue-50"
                >
                  {o.markValidated}
                </button>
                <button
                  onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'dismissed' })}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  {o.markDismissed}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function EvidenceMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-gray-900">{value}</p>
    </div>
  )
}

function EvidenceBlock({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-sm leading-relaxed text-gray-700">{value}</p>
    </div>
  )
}

function MetadataField({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-medium text-gray-900">{value}</p>
    </div>
  )
}
