import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Filter, Search, X } from 'lucide-react'
import clsx from 'clsx'
import { OpportunityCard } from '../../components/Cards/OpportunityCard'
import { KpiCard } from '../../components/Cards/KpiCard'
import { Panel, PanelHeader } from '../../components/Layout/Panel'
import { PageHeader } from '../../components/Layout/PageHeader'
import { DataTable } from '../../components/Tables/DataTable'
import type { DataTableColumn } from '../../components/Tables/DataTable'
import { BadgeCell, SavingsCell, TruncatedCell, TimestampCell } from '../../components/Tables/cells'
import { opportunitiesApi } from '../../api/opportunities'
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import type { ConfidenceTier, Opportunity, OpportunityStatus, RiskLevel } from '../../types'
import { buildAzurePortalResourceUrl, parseAzureResourceId } from '../../utils/azureResource'
import { usePersistentString } from '../../hooks/usePersistentBoolean'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { formatCurrency } from '../../utils/currency'

// ─── Utilities ───────────────────────────────────────────────────────────────

const fmt = (n: number) => formatCurrency(n, undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

type OpportunityViewMode = 'table' | 'cards'
type ProviderKey = 'azure' | 'aws' | 'gcp' | 'unknown'
type SortKey = 'savings_desc' | 'score_desc' | 'risk_desc' | 'newest'

const VIEW_MODES: OpportunityViewMode[] = ['table', 'cards']
const RISK_ORDER: Record<RiskLevel, number> = { high: 3, medium: 2, low: 1 }

const STATUS_COLORS: Record<OpportunityStatus, string> = {
  open: 'bg-sky-50 text-sky-700 border-sky-200',
  in_progress: 'bg-amber-50 text-amber-700 border-amber-200',
  resolved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  dismissed: 'bg-slate-50 text-slate-500 border-slate-200',
  validated: 'bg-blue-50 text-blue-700 border-blue-200',
}
const RISK_COLORS: Record<RiskLevel, string> = {
  low: 'bg-emerald-50 text-emerald-700',
  medium: 'bg-amber-50 text-amber-700',
  high: 'bg-rose-50 text-rose-700',
}
const CONFIDENCE_COLORS: Record<ConfidenceTier, string> = {
  high: 'bg-slate-100 text-slate-700',
  medium: 'bg-slate-50 text-slate-600',
  low: 'bg-amber-50 text-amber-700',
  insufficient: 'bg-slate-50 text-slate-400',
}

function humanizeToken(value: string) {
  return value.split('_').filter(Boolean).map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(' ')
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
  return new Intl.DateTimeFormat(lang === 'pt' ? 'pt-BR' : 'en-US', { dateStyle: 'medium' }).format(date)
}
function formatPercent(value: number) { return `${Math.round(value * 100)}%` }

function getFallbackConfidenceTier(value: number | null | undefined): ConfidenceTier {
  if (value == null) return 'insufficient'
  if (value >= 0.8) return 'high'
  if (value >= 0.55) return 'medium'
  return 'low'
}
function getOpportunityConfidenceTier(opportunity: Opportunity): ConfidenceTier {
  return opportunity.savings_evidence?.confidence_tier ?? getFallbackConfidenceTier(opportunity.savings_evidence?.savings_confidence ?? opportunity.decision_evidence?.confidence)
}
function getOpportunityConfidenceScore(opportunity: Opportunity) {
  return opportunity.savings_evidence?.savings_confidence ?? opportunity.decision_evidence?.confidence ?? null
}
function getOpportunityRiskLevel(opportunity: Opportunity): RiskLevel {
  return opportunity.savings_evidence?.risk_level ?? opportunity.decision_evidence?.risk_level ?? opportunity.risk_level
}
function normalizeProviderKey(value: string | null | undefined): ProviderKey {
  const n = value?.trim().toLowerCase()
  if (n === 'azure') return 'azure'
  if (n === 'aws') return 'aws'
  if (n === 'gcp' || n === 'google' || n === 'google_cloud') return 'gcp'
  return 'unknown'
}
function inferOpportunityProvider(opportunity: Opportunity): ProviderKey {
  const ctx = normalizeProviderKey(opportunity.resource_context?.provider)
  if (ctx !== 'unknown') return ctx
  const rid = opportunity.resource_id?.toLowerCase() ?? ''
  const svc = opportunity.service?.toLowerCase() ?? ''
  const rt = opportunity.decision_evidence?.resource_type?.toLowerCase() ?? ''
  if (rid.startsWith('/subscriptions/') || rt.includes('aks') || opportunity.category === 'aks_autoscaler_recommendation' || opportunity.category === 'aks_nodepool_rightsizing') return 'azure'
  if (rid.startsWith('arn:') || svc.includes('amazon') || svc.includes('aws')) return 'aws'
  if (rid.startsWith('projects/') || svc.includes('google') || svc.includes('gcp')) return 'gcp'
  return 'unknown'
}
function getOpportunityScope(opportunity: Opportunity, unknownLabel: string) {
  const rc = opportunity.resource_context
  const parsed = parseAzureResourceId(opportunity.resource_id)
  return {
    primary: rc?.resource_name ?? parsed?.resourceName ?? opportunity.resource_name ?? opportunity.service ?? unknownLabel,
    secondary: rc?.subscription_name ?? rc?.resource_group ?? parsed?.resourceGroup ?? opportunity.environment ?? (opportunity.resource_id ? truncateMiddle(opportunity.resource_id) : null),
    resourceGroup: rc?.resource_group ?? parsed?.resourceGroup ?? null,
    resourceType: rc?.resource_type ?? opportunity.decision_evidence?.resource_type ?? null,
    subscription: rc?.subscription_name ?? null,
    sku: rc?.sku ?? opportunity.sku_name ?? null,
  }
}
function buildOpportunitiesExportFileName() {
  return `causium-opportunities-export-${new Date().toISOString().slice(0, 10)}.csv`
}
async function getExportErrorMessage(error: unknown, fallback: string) {
  const rd = (error as { response?: { data?: Blob | { detail?: string; message?: string } } })?.response?.data
  if (rd instanceof Blob) { try { const t = await rd.text(); const p = JSON.parse(t) as { detail?: string; message?: string }; return p.detail || p.message || fallback } catch { return fallback } }
  if (rd && typeof rd === 'object') return rd.detail || rd.message || fallback
  return fallback
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function OpportunitiesPage() {
  const { t, lang } = useI18n()
  usePageTitle('Opportunities')
  const o = t.opportunities
  const queryClient = useQueryClient()
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<OpportunityStatus | 'all'>('open')
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null)
  const [explainOpp, setExplainOpp] = useState<Opportunity | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('savings_desc')
  const [viewModeRaw, setViewModeRaw] = usePersistentString('sp.opportunities.view', 'table')
  const viewMode: OpportunityViewMode = VIEW_MODES.includes(viewModeRaw as OpportunityViewMode) ? (viewModeRaw as OpportunityViewMode) : 'table'

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
    open: o.statusOpenSuggestion, in_progress: o.statusInProgressReview,
    resolved: o.statusResolvedApproved, dismissed: o.statusDismissed, validated: o.statusValidated,
  }
  const categoryLabels: Record<string, string> = {
    rightsizing: o.rightsizing, aks_autoscaler_recommendation: o.aksAutoscalerRecommendation,
    idle_resources: o.idleResources, reserved_instances: o.reservedInstances,
    storage_optimization: o.storage, network_optimization: o.network,
  }
  const riskLabels: Record<RiskLevel, string> = { low: o.riskLow, medium: o.riskMedium, high: o.riskHigh }
  const confidenceTierLabels: Record<ConfidenceTier, string> = { high: o.confidenceHigh, medium: o.confidenceMedium, low: o.confidenceLow, insufficient: o.confidenceInsufficient }
  const providerLabels: Record<ProviderKey, string> = { azure: o.providerAzure, aws: o.providerAws, gcp: o.providerGcp, unknown: o.providerUnknown }
  const granularityLabels = { resource: o.granularityResource, service: o.granularityCluster, subscription: o.granularitySubscription, unknown: o.granularityUnknown } as const

  // ─── Queries ─────────────────────────────────────────────────────────────────

  const { data: summary } = useQuery({
    queryKey: ['opportunities', 'summary'],
    queryFn: () => opportunitiesApi.summary().then((r) => r.data),
    staleTime: 30_000, retry: 2,
  })
  const { data: opportunities, isLoading, isError, refetch } = useQuery({
    queryKey: ['opportunities', selectedCategory, selectedStatus],
    queryFn: () => opportunitiesApi.list({ category: selectedCategory || undefined, status: selectedStatus === 'all' ? undefined : selectedStatus }).then((r) => r.data.items),
    staleTime: 30_000, retry: 2,
  })

  // ─── Filtering & Sorting ─────────────────────────────────────────────────────

  const filteredOpportunities = useMemo(() => {
    if (!opportunities) return []
    if (!searchQuery.trim()) return opportunities
    const q = searchQuery.toLowerCase().trim()
    return opportunities.filter((op) =>
      op.title.toLowerCase().includes(q) || op.description.toLowerCase().includes(q) ||
      (op.resource_name ?? '').toLowerCase().includes(q) || (op.service ?? '').toLowerCase().includes(q) ||
      (op.owner_team ?? '').toLowerCase().includes(q) || (op.resource_id ?? '').toLowerCase().includes(q),
    )
  }, [opportunities, searchQuery])

  const sortedOpportunities = useMemo(() => {
    const items = [...filteredOpportunities]
    switch (sortKey) {
      case 'savings_desc': return items.sort((a, b) => b.estimated_monthly_savings_usd - a.estimated_monthly_savings_usd)
      case 'score_desc': return items.sort((a, b) => b.composite_score - a.composite_score)
      case 'risk_desc': return items.sort((a, b) => RISK_ORDER[b.risk_level] - RISK_ORDER[a.risk_level])
      case 'newest': return items.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      default: return items
    }
  }, [filteredOpportunities, sortKey])

  const hasActiveFilters = selectedCategory !== '' || selectedStatus !== 'open' || searchQuery.trim() !== ''
  const clearAllFilters = () => { setSelectedCategory(''); setSelectedStatus('open'); setSearchQuery('') }

  // ─── Mutations ───────────────────────────────────────────────────────────────

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: OpportunityStatus }) => opportunitiesApi.updateStatus(id, status),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['opportunities'] }); setSelectedOpp(null) },
  })
  const explainMutation = useMutation({
    mutationFn: ({ id, language }: { id: string; language: 'pt' | 'en' }) => opportunitiesApi.explain(id, language).then((r) => r.data),
  })
  const exportCsvMutation = useMutation({
    mutationFn: async () => {
      setExportError(null)
      try { return await opportunitiesApi.exportCsv({ category: selectedCategory || undefined, status: selectedStatus === 'all' ? undefined : selectedStatus, owner_team: undefined }) }
      catch (error) { throw new Error(await getExportErrorMessage(error, o.exportCsvError)) }
    },
    onSuccess: (response) => {
      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a'); link.href = url; link.download = buildOpportunitiesExportFileName()
      document.body.appendChild(link); link.click(); link.remove(); window.URL.revokeObjectURL(url)
    },
    onError: (error) => { setExportError(error instanceof Error ? error.message : o.exportCsvError) },
  })

  const openExplain = (op: Opportunity) => { setExplainOpp(op); explainMutation.reset(); explainMutation.mutate({ id: op.id, language: lang === 'pt' ? 'pt' : 'en' }) }

  // ─── Detail drawer data ──────────────────────────────────────────────────────

  const selectedParsedResource = parseAzureResourceId(selectedOpp?.resource_id)
  const selectedAzurePortalUrl = buildAzurePortalResourceUrl(selectedOpp?.resource_id)
  const selectedResourceContext = selectedOpp?.resource_context
  const selectedMachineName = selectedParsedResource?.resourceName ?? o.unknownResource
  const selectedResourceGroup = selectedParsedResource?.resourceGroup ?? selectedOpp?.resource_name ?? o.unknownResource
  const selectedMachineSku = selectedOpp?.sku_name ?? o.unknownResource
  const selectedMachineFamily = selectedOpp?.machine_family ?? o.unknownResource
  const selectedEvidence = selectedOpp?.decision_evidence
  const selectedSavingsEvidence = selectedOpp?.savings_evidence
  const selectedIsAksAutoscaler = selectedOpp?.category === 'aks_autoscaler_recommendation'
  const selectedIsAksEvidence = selectedEvidence?.resource_type === 'aks_node_pool' || !!selectedEvidence?.node_pool || selectedEvidence?.current_node_count != null
  const selectedProviderKey = normalizeProviderKey(selectedResourceContext?.provider)
  const selectedProviderLabel = providerLabels[selectedProviderKey === 'unknown' ? (selectedOpp ? inferOpportunityProvider(selectedOpp) : 'unknown') : selectedProviderKey]

  // ─── Distribution analytics ──────────────────────────────────────────────────

  const riskDistribution = useMemo(() => {
    if (!sortedOpportunities.length) return null
    const counts = { low: 0, medium: 0, high: 0 }
    sortedOpportunities.forEach((op) => { counts[getOpportunityRiskLevel(op)]++ })
    return counts
  }, [sortedOpportunities])

  const confidenceDistribution = useMemo(() => {
    if (!sortedOpportunities.length) return null
    const counts = { high: 0, medium: 0, low: 0, insufficient: 0 }
    sortedOpportunities.forEach((op) => { counts[getOpportunityConfidenceTier(op)]++ })
    return counts
  }, [sortedOpportunities])

  // ─── Table columns ─────────────────────────────────────────────────────────

  const tableColumns: DataTableColumn<Opportunity>[] = useMemo(() => [
    {
      key: 'opportunity',
      header: o.colOpportunity,
      width: 'w-[280px]',
      sortFn: (a, b) => a.title.localeCompare(b.title),
      render: (op) => {
        const catLabel = categoryLabels[op.category] ?? humanizeToken(op.category)
        const provider = inferOpportunityProvider(op)
        return (
          <div className="min-w-0">
            <TruncatedCell primary={op.title} secondary={op.description} />
            <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-400 lg:hidden">
              <span>{catLabel}</span><span>·</span><span>{providerLabels[provider]}</span>
            </div>
          </div>
        )
      },
    },
    {
      key: 'category',
      header: o.colCategory,
      hideBelow: 'lg',
      render: (op) => <span className="text-slate-600">{categoryLabels[op.category] ?? humanizeToken(op.category)}</span>,
    },
    {
      key: 'provider',
      header: o.colProvider,
      hideBelow: 'md',
      render: (op) => <BadgeCell label={providerLabels[inferOpportunityProvider(op)]} />,
    },
    {
      key: 'savings',
      header: o.colEstimatedMonthlySavings,
      align: 'right',
      sortFn: (a, b) => (a.savings_evidence?.estimated_monthly_savings ?? a.estimated_monthly_savings_usd) - (b.savings_evidence?.estimated_monthly_savings ?? b.estimated_monthly_savings_usd),
      render: (op) => {
        const monthly = op.savings_evidence?.estimated_monthly_savings ?? op.estimated_monthly_savings_usd
        return <SavingsCell monthly={monthly} annual={monthly * 12} formatter={fmt} />
      },
    },
    {
      key: 'confidence',
      header: o.colConfidence,
      hideBelow: 'lg',
      sortFn: (a, b) => {
        const order: Record<ConfidenceTier, number> = { high: 4, medium: 3, low: 2, insufficient: 1 }
        return order[getOpportunityConfidenceTier(a)] - order[getOpportunityConfidenceTier(b)]
      },
      render: (op) => {
        const tier = getOpportunityConfidenceTier(op)
        return <span className={clsx('rounded-full px-1.5 py-0.5 text-[10px] font-medium', CONFIDENCE_COLORS[tier])}>{confidenceTierLabels[tier]}</span>
      },
    },
    {
      key: 'risk',
      header: o.colRisk,
      hideBelow: 'md',
      sortFn: (a, b) => RISK_ORDER[getOpportunityRiskLevel(a)] - RISK_ORDER[getOpportunityRiskLevel(b)],
      render: (op) => {
        const level = getOpportunityRiskLevel(op)
        return <span className={clsx('rounded-full px-1.5 py-0.5 text-[10px] font-medium', RISK_COLORS[level])}>{riskLabels[level]}</span>
      },
    },
    {
      key: 'status',
      header: o.colStatus,
      render: (op) => <span className={clsx('rounded-full border px-1.5 py-0.5 text-[10px] font-medium', STATUS_COLORS[op.status])}>{statusLabels[op.status]}</span>,
    },
    {
      key: 'detected',
      header: o.colDetectedAt,
      hideBelow: 'xl',
      sortFn: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      render: (op) => <TimestampCell value={op.created_at} locale={lang === 'pt' ? 'pt-BR' : 'en-US'} />,
    },
  ], [o, categoryLabels, providerLabels, confidenceTierLabels, riskLabels, statusLabels, lang])

  // ─── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="page-container">
      {/* ═══ A. Page Header ═══ */}
      <PageHeader
        title={o.title}
        subtitle={o.subtitle}
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button type="button" onClick={() => exportCsvMutation.mutate()} disabled={exportCsvMutation.isPending}
              className={clsx('inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors',
                exportCsvMutation.isPending ? 'cursor-wait border-slate-200 bg-slate-50 text-slate-400' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50')}>
              {exportCsvMutation.isPending ? <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" /> : <Download className="h-3.5 w-3.5" />}
              <span>{exportCsvMutation.isPending ? o.exportCsvLoading : o.exportCsv}</span>
            </button>
            <div className="inline-flex rounded-md border border-slate-200 bg-slate-50 p-0.5">
              <button type="button" onClick={() => setViewModeRaw('table')} className={clsx('rounded px-2.5 py-1 text-xs font-medium transition-all', viewMode === 'table' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700')}>{o.viewTable}</button>
              <button type="button" onClick={() => setViewModeRaw('cards')} className={clsx('rounded px-2.5 py-1 text-xs font-medium transition-all', viewMode === 'cards' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700')}>{o.viewCards}</button>
            </div>
          </div>
        }
      />

      {/* ═══ B. KPI Summary Row ═══ */}
      {summary && (
        <div className="kpi-grid">
          <KpiCard title={o.totalSavings} value={fmt(summary.total_potential_savings_usd)} tone="positive" footer={<span>{summary.total} {o.summaryOpportunities.replace('{{count}}', String(summary.total)).split(' ').slice(1).join(' ')}</span>} />
          <KpiCard title={o.open} value={String(summary.open)} tone="neutral" footer={<span>{o.statusOpenSuggestion}</span>} />
          <KpiCard title={o.inProgress} value={String(summary.in_progress)} tone="neutral" footer={<span>{o.statusInProgressReview}</span>} />
          <KpiCard title={o.resolved} value={String(summary.resolved)} tone="positive" footer={<span>{o.statusResolvedApproved}</span>} />
        </div>
      )}

      {/* ═══ C. Filter / Action Bar ═══ */}
      <div className="rounded-panel border border-slate-200 bg-white px-3 py-2.5 shadow-panel">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-1 flex-wrap items-center gap-2.5">
            <Filter className="h-3.5 w-3.5 shrink-0 text-slate-400" />
            <select value={selectedCategory} onChange={(ev) => setSelectedCategory(ev.target.value)} aria-label="Filter by category"
              className="rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-xs text-slate-700 focus:border-brand-500 focus:outline-none">
              {categories.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <select value={selectedStatus} onChange={(ev) => setSelectedStatus(ev.target.value as OpportunityStatus | 'all')} aria-label="Filter by status"
              className="rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-xs text-slate-700 focus:border-brand-500 focus:outline-none">
              <option value="all">{o.statusAll}</option>
              <option value="open">{o.statusOpenSuggestion}</option>
              <option value="in_progress">{o.statusInProgressReview}</option>
              <option value="resolved">{o.statusResolvedApproved}</option>
              <option value="dismissed">{o.statusDismissed}</option>
              <option value="validated">{o.statusValidated}</option>
            </select>
            <select value={sortKey} onChange={(ev) => setSortKey(ev.target.value as SortKey)} aria-label="Sort"
              className="rounded-md border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-xs text-slate-700 focus:border-brand-500 focus:outline-none">
              <option value="savings_desc">{o.sortSavingsDesc}</option>
              <option value="score_desc">{o.sortScoreDesc}</option>
              <option value="risk_desc">{o.sortRiskDesc}</option>
              <option value="newest">{o.sortNewest}</option>
            </select>
            <div className="relative min-w-[220px] flex-[1.4_1_280px]">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input type="text" value={searchQuery} onChange={(ev) => setSearchQuery(ev.target.value)} placeholder={o.searchPlaceholder} aria-label={o.searchPlaceholder}
                className="w-full rounded-md border border-slate-200 bg-slate-50/60 py-1.5 pl-8 pr-7 text-xs text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:bg-white focus:outline-none" />
              {searchQuery && <button type="button" onClick={() => setSearchQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600" aria-label={o.searchClear}><X className="h-3 w-3" /></button>}
            </div>
            {hasActiveFilters && (
              <button type="button" onClick={clearAllFilters} className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-medium text-slate-600 hover:bg-slate-50">
                <X className="h-3 w-3" />{o.emptyFilteredAction}
              </button>
            )}
          </div>
          {sortedOpportunities.length > 0 && (
            <div className="flex flex-wrap items-center gap-3 text-xs xl:ml-auto xl:justify-end">
              <span className="font-semibold text-slate-800">{o.summaryOpportunities.replace('{{count}}', String(sortedOpportunities.length))}</span>
              <span className="hidden h-3.5 w-px bg-slate-200 sm:block" />
              <span className="font-semibold tabular-nums text-emerald-700">{o.summaryPerMonth.replace('{{amount}}', fmt(sortedOpportunities.reduce((s, op) => s + op.estimated_monthly_savings_usd, 0)))}</span>
              {sortedOpportunities.some((op) => op.risk_level === 'high') && (
                <>
                  <span className="hidden h-3.5 w-px bg-slate-200 sm:block" />
                  <span className="inline-flex items-center gap-1 font-medium text-rose-700"><span className="h-1.5 w-1.5 rounded-full bg-rose-500" />{o.summaryHighRisk.replace('{{count}}', String(sortedOpportunities.filter((op) => op.risk_level === 'high').length))}</span>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {exportError && <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs text-rose-700">{exportError}</div>}

      {/* ═══ D. Primary Workbench ═══ */}
      {isLoading ? (
        <DataTable<Opportunity> columns={tableColumns} data={[]} getRowKey={(op) => op.id} loading loadingRows={8} />
      ) : isError ? (
        <ErrorState title={o.errorTitle} description={o.errorDescription} onRetry={() => refetch()} retryLabel={o.errorRetry} />
      ) : !sortedOpportunities?.length ? (
        hasActiveFilters
          ? <EmptyState icon="search" title={o.emptyFilteredTitle} description={o.emptyFilteredDescription} action={{ label: o.emptyFilteredAction, onClick: clearAllFilters }} />
          : <EmptyState icon="lightbulb" title={o.noOpportunities} description={o.noOpportunitiesHint} />
      ) : viewMode === 'table' ? (
        <DataTable<Opportunity>
          columns={tableColumns}
          data={sortedOpportunities}
          getRowKey={(op) => op.id}
          onRowClick={setSelectedOpp}
          density="compact"
          stickyHeader
          emptyTitle={o.noOpportunities}
          emptyDescription={o.noOpportunitiesHint}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {sortedOpportunities.map((op) => <OpportunityCard key={op.id} opportunity={op} onClick={() => setSelectedOpp(op)} onExplain={() => openExplain(op)} />)}
        </div>
      )}

      {/* ═══ F. Distribution Analytics ═══ */}
      {sortedOpportunities.length > 0 && (riskDistribution || confidenceDistribution) && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {riskDistribution && (
            <Panel compact>
              <PanelHeader title={(o as Record<string, string>).riskDistribution ?? 'Risk Distribution'} />
              <div className="mt-3 flex items-end gap-1.5 h-10">
                {(['low', 'medium', 'high'] as RiskLevel[]).map((level) => {
                  const count = riskDistribution[level]
                  const pct = (count / sortedOpportunities.length) * 100
                  return (
                    <div key={level} className="flex flex-col items-center gap-1 flex-1">
                      <div className={clsx('w-full rounded-sm transition-all', level === 'low' ? 'bg-emerald-400' : level === 'medium' ? 'bg-amber-400' : 'bg-rose-400')} style={{ height: `${Math.max(4, pct)}%` }} />
                      <span className="text-[9px] text-slate-500">{riskLabels[level]}</span>
                      <span className="text-[10px] font-semibold tabular-nums text-slate-700">{count}</span>
                    </div>
                  )
                })}
              </div>
            </Panel>
          )}
          {confidenceDistribution && (
            <Panel compact>
              <PanelHeader title={(o as Record<string, string>).confidenceDistribution ?? 'Confidence Distribution'} />
              <div className="mt-3 flex items-end gap-1.5 h-10">
                {(['high', 'medium', 'low', 'insufficient'] as ConfidenceTier[]).map((tier) => {
                  const count = confidenceDistribution[tier]
                  const pct = (count / sortedOpportunities.length) * 100
                  return (
                    <div key={tier} className="flex flex-col items-center gap-1 flex-1">
                      <div className={clsx('w-full rounded-sm transition-all', tier === 'high' ? 'bg-slate-600' : tier === 'medium' ? 'bg-slate-400' : tier === 'low' ? 'bg-amber-400' : 'bg-slate-200')} style={{ height: `${Math.max(4, pct)}%` }} />
                      <span className="text-[9px] text-slate-500">{confidenceTierLabels[tier]}</span>
                      <span className="text-[10px] font-semibold tabular-nums text-slate-700">{count}</span>
                    </div>
                  )
                })}
              </div>
            </Panel>
          )}
        </div>
      )}

      {/* DSS notice — minimal footer */}
      <p className="text-center text-[10px] text-slate-400">{o.readOnlyNoticeTitle} — {o.safeDssFooter}</p>

      {/* ═══ Explain Modal ═══ */}
      {explainOpp && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-2xl rounded-panel border border-slate-200 bg-white shadow-panel-elevated">
            <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-5">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{o.explainWithAI}</h2>
                <p className="mt-1 text-sm text-slate-500">{explainOpp.title}</p>
              </div>
              <button type="button" className="rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-50" onClick={() => setExplainOpp(null)}>{t.common.close}</button>
            </div>
            <div className="space-y-4 p-5">
              {explainMutation.isPending && (
                <div className="flex items-center gap-3 text-sm text-slate-600"><div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />{o.explainLoading}</div>
              )}
              {explainMutation.isError && <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{o.explainError}</div>}
              {explainMutation.data && (
                <div className="space-y-3">
                  <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
                    <p className="text-sm font-medium text-slate-900">{o.explainSummary}</p>
                    <p className="mt-1 text-sm text-slate-700">{explainMutation.data.summary}</p>
                    <p className="mt-2 text-diagnostic">{o.confidenceLabel}: {Math.round(explainMutation.data.confidence * 100)}%{explainMutation.data.model ? ` · ${explainMutation.data.model}` : ''}</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-4">
                    <p className="text-sm font-medium text-slate-900">{o.explainWhyNow}</p>
                    <p className="mt-1 text-sm text-slate-700">{explainMutation.data.why_now}</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-4">
                    <p className="text-sm font-medium text-slate-900">{o.explainImpact}</p>
                    <p className="mt-1 text-sm text-slate-700">{explainMutation.data.expected_impact}</p>
                  </div>
                  {explainMutation.data.risks.length > 0 && (
                    <div className="rounded-lg border border-slate-200 p-4">
                      <p className="text-sm font-medium text-slate-900">{o.explainRisks}</p>
                      <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">{explainMutation.data.risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
                    </div>
                  )}
                  {explainMutation.data.recommended_steps.length > 0 && (
                    <div className="rounded-lg border border-slate-200 p-4">
                      <p className="text-sm font-medium text-slate-900">{o.explainSteps}</p>
                      <ol className="mt-2 list-decimal pl-5 text-sm text-slate-700">{explainMutation.data.recommended_steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══ E. Detail Drawer ═══ */}
      {selectedOpp && (
        <div className="fixed inset-0 z-50 flex items-stretch justify-end">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setSelectedOpp(null)} />
          <div className="relative h-full w-full max-w-full overflow-y-auto bg-white shadow-2xl sm:max-w-2xl lg:max-w-lg">
            <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur-sm sm:px-5">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white tabular-nums">{selectedOpp.composite_score.toFixed(0)}</div>
                <div className="min-w-0">
                  <h2 className="text-sm font-semibold text-slate-900">{o.detailTitle}</h2>
                  <p className="text-[10px] text-slate-500">{statusLabels[selectedOpp.status]}</p>
                </div>
              </div>
              <button onClick={() => setSelectedOpp(null)} className="shrink-0 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"><X className="h-4 w-4" /></button>
            </div>
            <div className="space-y-4 p-4 sm:p-5">
              <div>
                <h3 className="text-base font-bold text-slate-900">{selectedOpp.title}</h3>
                <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">{selectedOpp.description}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className={clsx('rounded-full border px-2 py-0.5 text-[10px] font-medium', STATUS_COLORS[selectedOpp.status])}>{statusLabels[selectedOpp.status]}</span>
                  <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-medium', RISK_COLORS[getOpportunityRiskLevel(selectedOpp)])}>{riskLabels[getOpportunityRiskLevel(selectedOpp)]}</span>
                  <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-medium', CONFIDENCE_COLORS[getOpportunityConfidenceTier(selectedOpp)])}>{confidenceTierLabels[getOpportunityConfidenceTier(selectedOpp)]}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">{selectedProviderLabel}</span>
                </div>
              </div>

              {/* Savings + Score */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600">{o.monthlySavings}</p>
                  <p className="mt-1 text-lg font-bold tabular-nums text-emerald-700">{fmt(selectedSavingsEvidence?.estimated_monthly_savings ?? selectedOpp.estimated_monthly_savings_usd)}</p>
                  <p className="mt-0.5 text-[10px] text-emerald-600/70">{fmt((selectedSavingsEvidence?.estimated_monthly_savings ?? selectedOpp.estimated_monthly_savings_usd) * 12)}/yr</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{o.compositeScore}</p>
                  <p className="mt-1 text-lg font-bold tabular-nums text-slate-800">{selectedOpp.composite_score.toFixed(1)}<span className="text-xs font-medium text-slate-400">/100</span></p>
                  <p className="mt-0.5 text-[10px] text-slate-500">{riskLabels[getOpportunityRiskLevel(selectedOpp)]} · {confidenceTierLabels[getOpportunityConfidenceTier(selectedOpp)]}</p>
                </div>
              </div>

              {/* Resource Context */}
              {(selectedResourceContext || selectedOpp.resource_id || selectedOpp.resource_name) && (
                <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <h4 className="text-xs font-semibold text-slate-800">{o.resourceContextTitle}</h4>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">{granularityLabels[selectedResourceContext?.granularity_tier ?? 'unknown']}</span>
                  </div>
                  <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <MetadataField label={o.resourceContextProvider} value={selectedProviderLabel} />
                    <MetadataField label={o.resourceContextSubscription} value={selectedResourceContext?.subscription_name ?? undefined} />
                    <MetadataField label={o.resourceContextResourceGroup} value={selectedResourceContext?.resource_group ?? selectedParsedResource?.resourceGroup ?? undefined} />
                    <MetadataField label={o.resourceContextResource} value={selectedResourceContext?.resource_name ?? selectedMachineName} />
                    <MetadataField label={o.resourceContextResourceType} value={selectedResourceContext?.resource_type ?? selectedEvidence?.resource_type ?? undefined} />
                    <MetadataField label={o.resourceContextSku} value={selectedResourceContext?.sku ?? selectedOpp.sku_name ?? undefined} />
                    <MetadataField label={o.resourceContextRegion} value={selectedResourceContext?.region ?? selectedOpp.region ?? undefined} />
                    <MetadataField label={o.resourceContextOwner} value={selectedResourceContext?.owner ?? undefined} />
                  </div>
                  {selectedAzurePortalUrl && (
                    <a href={selectedAzurePortalUrl} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-[11px] font-medium text-brand-600 hover:underline">{o.openInAzure}</a>
                  )}
                  {selectedResourceContext?.tags_summary && Object.keys(selectedResourceContext.tags_summary).length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-200">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">{o.resourceContextTagsSummary}</p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {Object.entries(selectedResourceContext.tags_summary).map(([k, v]) => <span key={`${k}-${v}`} className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] text-slate-600">{k}: {v}</span>)}
                      </div>
                    </div>
                  )}
                  {selectedResourceContext?.data_sources.length ? (
                    <div className="mt-3 pt-3 border-t border-slate-200">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">{o.resourceContextDataSources}</p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {selectedResourceContext.data_sources.map((s) => <span key={s} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">{humanizeToken(s)}</span>)}
                      </div>
                    </div>
                  ) : null}
                </div>
              )}

              {/* Savings Evidence */}
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
                <div className="flex items-start justify-between gap-3">
                  <h4 className="text-xs font-semibold text-slate-800">{o.savingsEvidenceTitle}</h4>
                  {selectedSavingsEvidence && <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-medium', CONFIDENCE_COLORS[getOpportunityConfidenceTier(selectedOpp)])}>{confidenceTierLabels[getOpportunityConfidenceTier(selectedOpp)]}</span>}
                </div>
                {selectedSavingsEvidence ? (
                  <div className="mt-3 space-y-3">
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <EvidenceMetric label={o.currentMonthlyCostEstimate} value={fmt(selectedSavingsEvidence.current_monthly_cost_estimate)} />
                      <EvidenceMetric label={o.projectedMonthlyCostEstimate} value={selectedSavingsEvidence.projected_monthly_cost_estimate != null ? fmt(selectedSavingsEvidence.projected_monthly_cost_estimate) : o.notAvailable} />
                      <EvidenceMetric label={o.estimatedSavingsEvidence} value={fmt(selectedSavingsEvidence.estimated_monthly_savings)} />
                      <EvidenceMetric label={o.riskLevelEvidence} value={riskLabels[selectedSavingsEvidence.risk_level]} />
                    </div>
                    {selectedSavingsEvidence.evidence_summary && (
                      <div className="border-t border-slate-200 pt-3">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">{o.evidenceSummaryLabel}</p>
                        <p className="mt-1 text-xs text-slate-700 leading-relaxed">{selectedSavingsEvidence.evidence_summary}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="mt-3 text-xs text-slate-400">{o.savingsEvidenceUnavailable}</p>
                )}
              </div>

              {/* Decision Evidence */}
              {selectedEvidence && (
                <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
                  <h4 className="text-[10px] font-semibold uppercase tracking-wider text-blue-700">{selectedIsAksEvidence ? o.aksEvidenceTitle : o.rightsizingEvidenceTitle}</h4>
                  <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {!selectedIsAksEvidence && (
                      <>
                        <EvidenceMetric label={o.currentLabel} value={selectedEvidence.current_sku ?? selectedMachineSku} />
                        <EvidenceMetric label={o.recommendedLabel} value={selectedEvidence.recommended_sku ?? o.unknownResource} />
                        <EvidenceMetric label="CPU p95" value={`${selectedEvidence.cpu_p95 ?? '-'}%`} />
                        <EvidenceMetric label={o.memoryP95Label} value={`${selectedEvidence.memory_p95 ?? '-'}%`} />
                      </>
                    )}
                    {selectedIsAksEvidence && (
                      <>
                        <EvidenceMetric label={o.clusterLabel} value={selectedEvidence.cluster_name ?? o.unknownResource} />
                        <EvidenceMetric label={o.nodePoolLabel} value={selectedEvidence.node_pool ?? o.unknownResource} />
                        <EvidenceMetric label={o.skuLabel} value={selectedEvidence.node_sku ?? selectedMachineSku} />
                        <EvidenceMetric label="CPU p95" value={`${selectedEvidence.cpu_p95 ?? '-'}%`} />
                        {!selectedIsAksAutoscaler && <EvidenceMetric label={o.nodesLabel} value={String(selectedEvidence.current_node_count ?? '-')} />}
                        {selectedIsAksAutoscaler && <EvidenceMetric label={o.recommendedLabel} value={`min=${selectedEvidence.recommended_min_count ?? '-'}, max=${selectedEvidence.recommended_max_count ?? '-'}`} />}
                      </>
                    )}
                  </div>
                  {selectedEvidence.reason && <p className="mt-3 text-xs text-slate-600"><span className="font-medium">{o.reasonLabel}:</span> {selectedEvidence.reason}</p>}
                  <button type="button" onClick={() => openExplain(selectedOpp)} className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-brand-200 bg-white px-3 py-1.5 text-[11px] font-semibold text-brand-700 hover:bg-brand-50">{o.explainWithAI}</button>
                </div>
              )}

              {/* Playbook */}
              {selectedOpp.playbook && (
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <h4 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{o.playbook}</h4>
                  <pre className="mt-2 text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">{selectedOpp.playbook}</pre>
                </div>
              )}

              {/* Status Actions */}
              <div className="border-t border-slate-200 pt-4 space-y-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{o.currentStatus}</p>
                <div className="flex flex-wrap gap-2 sm:gap-2.5">
                  <button onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'in_progress' })} disabled={updateStatus.isPending || selectedOpp.status === 'in_progress'}
                    className="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40">{o.markInReview}</button>
                  <button onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'resolved' })} disabled={updateStatus.isPending || selectedOpp.status === 'resolved'}
                    className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40">{o.markApproved}</button>
                  <button onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'validated' })} disabled={updateStatus.isPending || selectedOpp.status === 'validated'}
                    className="rounded-md border border-blue-200 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-40">{o.markValidated}</button>
                  <button onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'dismissed' })} disabled={updateStatus.isPending || selectedOpp.status === 'dismissed'}
                    className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40">{o.markDismissed}</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function EvidenceMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-2.5 py-2">
      <p className="text-[9px] font-medium uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-0.5 break-words text-xs font-semibold text-slate-800">{value}</p>
    </div>
  )
}

function MetadataField({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return (
    <div className="rounded-md border border-slate-200 bg-white px-2.5 py-2">
      <p className="text-[9px] font-medium uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-0.5 break-words text-xs font-medium text-slate-800">{value}</p>
    </div>
  )
}

