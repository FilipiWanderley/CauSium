import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Filter } from 'lucide-react'
import { OpportunityCard } from '../../components/Cards/OpportunityCard'
import { opportunitiesApi } from '../../api/opportunities'
import { MetricCard } from '../../components/Cards/MetricCard'
import { useI18n } from '../../contexts/I18nContext'
import type { Opportunity, OpportunityStatus } from '../../types'
import { buildAzurePortalResourceUrl, parseAzureResourceId } from '../../utils/azureResource'

const fmt = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

export function OpportunitiesPage() {
  const { t, lang } = useI18n()
  const o = t.opportunities
  const queryClient = useQueryClient()
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<OpportunityStatus | 'all'>('open')
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null)
  const [explainOpp, setExplainOpp] = useState<Opportunity | null>(null)

  const categories = [
    { value: '', label: o.allCategories },
    { value: 'rightsizing', label: o.rightsizing },
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

  const openExplain = (op: Opportunity) => {
    setExplainOpp(op)
    explainMutation.reset()
    explainMutation.mutate({ id: op.id, language: lang === 'pt' ? 'pt' : 'en' })
  }

  const selectedParsedResource = parseAzureResourceId(selectedOpp?.resource_id)
  const selectedAzurePortalUrl = buildAzurePortalResourceUrl(selectedOpp?.resource_id)
  const selectedMachineName = selectedParsedResource?.resourceName ?? o.unknownResource
  const selectedResourceGroup =
    selectedParsedResource?.resourceGroup ?? selectedOpp?.resource_name ?? o.unknownResource
  const selectedMachineSku = selectedOpp?.sku_name ?? o.unknownResource
  const selectedMachineFamily = selectedOpp?.machine_family ?? o.unknownResource
  const selectedEvidence = selectedOpp?.decision_evidence
  const selectedIsAksEvidence =
    selectedEvidence?.resource_type === 'aks_node_pool' ||
    !!selectedEvidence?.node_pool ||
    selectedEvidence?.current_node_count != null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{o.title}</h1>
          <p className="text-sm text-gray-500 mt-1">{o.subtitle}</p>
        </div>
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
        <p className="text-sm font-semibold text-amber-900">{o.readOnlyNoticeTitle}</p>
        <p className="mt-1 text-sm text-amber-800">{o.readOnlyNoticeDesc}</p>
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
      </div>

      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : !opportunities?.length ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">{o.noOpportunities}</p>
          <p className="mt-1 text-xs text-gray-400">{o.noOpportunitiesHint}</p>
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
                <div className="mt-3 inline-flex rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">
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

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-green-50 p-3">
                  <p className="text-xs text-gray-500">{o.monthlySavings}</p>
                  <p className="text-lg font-bold text-green-700">
                    {fmt(selectedOpp.estimated_monthly_savings_usd)}
                  </p>
                </div>
                <div className="rounded-lg bg-blue-50 p-3">
                  <p className="text-xs text-gray-500">{o.compositeScore}</p>
                  <p className="text-lg font-bold text-blue-700">
                    {selectedOpp.composite_score.toFixed(1)}/100
                  </p>
                </div>
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
                        <strong>{fmt(selectedEvidence.estimated_savings ?? selectedOpp.estimated_monthly_savings_usd)}</strong>
                        {'  '}·{'  '}
                        {o.savingsPctLabel}: <strong>{selectedEvidence.estimated_savings_pct ?? '-'}%</strong>
                      </p>
                      <p>
                        {o.confidenceLabel}: <strong>{Math.round((selectedEvidence.confidence ?? 0) * 100)}%</strong>
                        {'  '}·{'  '}
                        {o.riskLabel}: <strong>{selectedEvidence.risk_level ?? selectedOpp.risk_level}</strong>
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
                      <p>
                        {o.nodesLabel}: <strong>{selectedEvidence.current_node_count ?? '-'}</strong>
                        {'  '}→{'  '}
                        {o.recommendedLabel}: <strong>{selectedEvidence.recommended_node_count ?? '-'}</strong>
                      </p>
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
                        <strong>{fmt(selectedEvidence.estimated_savings ?? selectedOpp.estimated_monthly_savings_usd)}</strong>
                        {'  '}·{'  '}
                        {o.savingsPctLabel}: <strong>{selectedEvidence.estimated_savings_pct ?? '-'}%</strong>
                      </p>
                      <p>
                        {o.confidenceLabel}: <strong>{Math.round((selectedEvidence.confidence ?? 0) * 100)}%</strong>
                        {'  '}·{'  '}
                        {o.riskLabel}: <strong>{selectedEvidence.risk_level ?? selectedOpp.risk_level}</strong>
                      </p>
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
