import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Filter, RefreshCw } from 'lucide-react'
import { OpportunityCard } from '../../components/Cards/OpportunityCard'
import { opportunitiesApi } from '../../api/opportunities'
import { MetricCard } from '../../components/Cards/MetricCard'
import type { Opportunity, OpportunityStatus } from '../../types'

const CATEGORIES = [
  { value: '', label: 'All categories' },
  { value: 'rightsizing', label: 'Rightsizing' },
  { value: 'idle_resources', label: 'Idle Resources' },
  { value: 'reserved_instances', label: 'Reserved Instances' },
  { value: 'storage_optimization', label: 'Storage' },
  { value: 'network_optimization', label: 'Network' },
]

const fmt = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

export function OpportunitiesPage() {
  const queryClient = useQueryClient()
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null)

  const { data: summary } = useQuery({
    queryKey: ['opportunities', 'summary'],
    queryFn: () => opportunitiesApi.summary().then((r) => r.data),
  })

  const { data: opportunities, isLoading } = useQuery({
    queryKey: ['opportunities', selectedCategory],
    queryFn: () =>
      opportunitiesApi
        .list({ category: selectedCategory || undefined, status: 'open' })
        .then((r) => r.data),
  })

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: OpportunityStatus }) =>
      opportunitiesApi.updateStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      setSelectedOpp(null)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Opportunities</h1>
          <p className="text-sm text-gray-500 mt-1">
            Prioritized by composite score — financial impact × risk × effort
          </p>
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard title="Open" value={summary.open} />
          <MetricCard title="In Progress" value={summary.in_progress} />
          <MetricCard title="Resolved" value={summary.resolved} />
          <MetricCard
            title="Total Potential Savings"
            value={fmt(summary.total_potential_savings_usd)}
            variant="success"
          />
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter className="h-4 w-4 text-gray-400" />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 focus:border-brand-500 focus:outline-none"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : !opportunities?.length ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">No opportunities found.</p>
          <p className="mt-1 text-xs text-gray-400">
            Sync a cloud account and generate opportunities to see results here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {opportunities.map((op) => (
            <OpportunityCard
              key={op.id}
              opportunity={op}
              onClick={() => setSelectedOpp(op)}
            />
          ))}
        </div>
      )}

      {/* Detail drawer */}
      {selectedOpp && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={() => setSelectedOpp(null)} />
          <div className="relative w-full max-w-lg bg-white shadow-2xl overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">Opportunity Detail</h2>
              <button
                onClick={() => setSelectedOpp(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <h3 className="text-lg font-bold text-gray-900">{selectedOpp.title}</h3>
                <p className="mt-2 text-sm text-gray-600">{selectedOpp.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-green-50 p-3">
                  <p className="text-xs text-gray-500">Monthly Savings</p>
                  <p className="text-lg font-bold text-green-700">
                    {fmt(selectedOpp.estimated_monthly_savings_usd)}
                  </p>
                </div>
                <div className="rounded-lg bg-blue-50 p-3">
                  <p className="text-xs text-gray-500">Composite Score</p>
                  <p className="text-lg font-bold text-blue-700">
                    {selectedOpp.composite_score.toFixed(1)}/100
                  </p>
                </div>
              </div>

              {selectedOpp.score_rationale && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Score Rationale</h4>
                  <p className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 leading-relaxed">
                    {selectedOpp.score_rationale}
                  </p>
                </div>
              )}

              {selectedOpp.playbook && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Playbook</h4>
                  <pre className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap font-sans">
                    {selectedOpp.playbook}
                  </pre>
                </div>
              )}

              <div className="border-t pt-4 flex gap-3">
                <button
                  onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'in_progress' })}
                  className="flex-1 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
                >
                  Create Initiative
                </button>
                <button
                  onClick={() => updateStatus.mutate({ id: selectedOpp.id, status: 'dismissed' })}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
