import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Landmark, Tag, AlertTriangle } from 'lucide-react'
import { govApi, type LabelComplianceRow, type UnownedCostRow } from '../../api/gov'

const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

function ComplianceBadge({ pct }: { pct: number }) {
  const color =
    pct >= 90 ? 'bg-emerald-100 text-emerald-700' :
    pct >= 70 ? 'bg-amber-100 text-amber-700' :
                'bg-red-100 text-red-700'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${color}`}>
      {pct.toFixed(1)}%
    </span>
  )
}

function ComplianceBar({ pct }: { pct: number }) {
  const color = pct >= 90 ? 'bg-emerald-500' : pct >= 70 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="h-1.5 w-full rounded-full bg-gray-100">
      <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  )
}

export function GovPage() {
  const [days, setDays] = useState(30)
  const [tab, setTab] = useState<'unowned' | 'compliance'>('unowned')

  const summaryQ = useQuery({
    queryKey: ['gov-summary', days],
    queryFn: () => govApi.getSummary(days),
  })

  const unownedQ = useQuery({
    queryKey: ['gov-unowned', days],
    queryFn: () => govApi.getUnownedCosts(days, 50),
    enabled: tab === 'unowned',
  })

  const complianceQ = useQuery({
    queryKey: ['gov-compliance', days],
    queryFn: () => govApi.getLabelCompliance(days),
    enabled: tab === 'compliance',
  })

  const s = summaryQ.data

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Landmark className="h-6 w-6 text-brand-500" />
            PulseGov
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Resource governance — ownership coverage, label compliance, and untagged cost exposure.
          </p>
        </div>

        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {[
          {
            label: 'Total Resources',
            value: s ? s.total_resources.toLocaleString() : '—',
            color: 'border-gray-100',
          },
          {
            label: 'Unowned',
            value: s ? s.unowned_resources.toLocaleString() : '—',
            color: 'border-amber-100',
            sub: s ? `${s.unowned_pct}%` : undefined,
          },
          {
            label: 'Unowned Cost',
            value: s ? money.format(s.unowned_cost_usd) : '—',
            color: 'border-red-100',
          },
          {
            label: 'Teams Evaluated',
            value: s ? s.teams_evaluated.toLocaleString() : '—',
            color: 'border-gray-100',
          },
          {
            label: 'Avg Compliance',
            value: s ? `${s.avg_compliance_pct}%` : '—',
            color: s && s.avg_compliance_pct >= 90 ? 'border-emerald-100' : 'border-amber-100',
          },
        ].map((k) => (
          <div
            key={k.label}
            className={`rounded-xl border ${k.color} bg-white p-4 shadow-sm`}
          >
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">{k.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{k.value}</p>
            {k.sub && <p className="text-xs text-amber-600">{k.sub} of total</p>}
          </div>
        ))}
      </div>

      {/* Tab switcher */}
      <div className="flex rounded-lg border border-gray-200 bg-white p-1 shadow-sm w-fit">
        {(['unowned', 'compliance'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {t === 'unowned' ? 'Unowned Resources' : 'Label Compliance'}
          </button>
        ))}
      </div>

      {/* Unowned tab */}
      {tab === 'unowned' && (
        <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          {unownedQ.isPending ? (
            <div className="p-6 space-y-3">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded bg-gray-100" />
              ))}
            </div>
          ) : unownedQ.isError ? (
            <div className="p-8 text-center text-sm text-red-500">
              Failed to load unowned costs data.
            </div>
          ) : (unownedQ.data ?? []).length === 0 ? (
            <div className="p-12 text-center">
              <Tag className="mx-auto mb-3 h-10 w-10 text-emerald-400" />
              <p className="text-sm font-medium text-gray-600">All resources have an owner assigned.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {['Service', 'Resource ID', 'Region', 'Environment', 'Days Active', 'Cost (USD)'].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(unownedQ.data as UnownedCostRow[]).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{row.service}</td>
                    <td className="max-w-[200px] truncate px-4 py-3 font-mono text-xs text-gray-500">
                      {row.resource_id}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{row.region}</td>
                    <td className="px-4 py-3 text-gray-600">{row.environment}</td>
                    <td className="px-4 py-3 text-gray-600">{row.days_active}</td>
                    <td className="px-4 py-3 font-semibold text-gray-900">
                      {money.format(row.cost_usd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Compliance tab */}
      {tab === 'compliance' && (
        <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          {complianceQ.isPending ? (
            <div className="p-6 space-y-3">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded bg-gray-100" />
              ))}
            </div>
          ) : complianceQ.isError ? (
            <div className="p-8 text-center text-sm text-red-500">
              Failed to load compliance data.
            </div>
          ) : (complianceQ.data ?? []).length === 0 ? (
            <div className="p-12 text-center">
              <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-gray-300" />
              <p className="text-sm text-gray-500">No compliance data available.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {['Team', 'Total Cost', 'Untagged Cost', 'Compliance', ''].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(complianceQ.data as LabelComplianceRow[]).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{row.team}</td>
                    <td className="px-4 py-3 text-gray-700">{money.format(row.total_cost_usd)}</td>
                    <td className="px-4 py-3 text-gray-500">{money.format(row.untagged_cost_usd)}</td>
                    <td className="px-4 py-3">
                      <ComplianceBadge pct={row.compliance_pct} />
                    </td>
                    <td className="w-32 px-4 py-3">
                      <ComplianceBar pct={row.compliance_pct} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Disclaimer */}
      <p className="text-xs text-gray-400">
        Governance data is derived from cloud cost records. Resource inventory sync via Azure
        Resource Graph is planned for Wave 3 (SP-GV01).
      </p>
    </div>
  )
}
