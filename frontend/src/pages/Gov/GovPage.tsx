import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Landmark, Tag, AlertTriangle, Lightbulb, Server } from 'lucide-react'
import {
  govApi,
  type LabelComplianceRow,
  type RecommendationRow,
  type ResourceRow,
  type UnownedCostRow,
} from '../../api/gov'

// ── Formatters ────────────────────────────────────────────────────────────────

const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

// ── Small helpers ─────────────────────────────────────────────────────────────

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

function ImpactBadge({ impact }: { impact: string }) {
  const color =
    impact === 'High'   ? 'bg-red-100 text-red-700' :
    impact === 'Medium' ? 'bg-amber-100 text-amber-700' :
                          'bg-gray-100 text-gray-600'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${color}`}>
      {impact}
    </span>
  )
}

function CategoryBadge({ category }: { category: string }) {
  const palette: Record<string, string> = {
    Cost:                  'bg-blue-100 text-blue-700',
    Security:              'bg-red-100 text-red-700',
    Performance:           'bg-purple-100 text-purple-700',
    HighAvailability:      'bg-emerald-100 text-emerald-700',
    OperationalExcellence: 'bg-orange-100 text-orange-700',
  }
  const color = palette[category] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${color}`}>
      {category}
    </span>
  )
}

function StatesBadge({ state }: { state: string }) {
  const color =
    state === 'Succeeded' ? 'bg-emerald-100 text-emerald-700' :
    state === 'Failed'    ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-500'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${color}`}>
      {state || '—'}
    </span>
  )
}

function EmptyState({ icon: Icon, message }: { icon: React.ElementType; message: string }) {
  return (
    <div className="p-12 text-center">
      <Icon className="mx-auto mb-3 h-10 w-10 text-gray-300" />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  )
}

function SkeletonRows() {
  return (
    <div className="p-6 space-y-3">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="h-10 animate-pulse rounded bg-gray-100" />
      ))}
    </div>
  )
}

// ── Tab type ──────────────────────────────────────────────────────────────────

type Tab = 'unowned' | 'compliance' | 'recommendations' | 'inventory'

const TABS: { id: Tab; label: string }[] = [
  { id: 'unowned',         label: 'Unowned Resources' },
  { id: 'compliance',      label: 'Label Compliance'  },
  { id: 'recommendations', label: 'Recommendations'   },
  { id: 'inventory',       label: 'Inventory'         },
]

// ── Page ──────────────────────────────────────────────────────────────────────

export function GovPage() {
  const [days, setDays] = useState(30)
  const [tab, setTab] = useState<Tab>('unowned')
  const [recCategory, setRecCategory] = useState('')

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

  const recSummaryQ = useQuery({
    queryKey: ['gov-rec-summary'],
    queryFn: () => govApi.getRecommendationsSummary(),
  })

  const recsQ = useQuery({
    queryKey: ['gov-recommendations', recCategory],
    queryFn: () => govApi.getRecommendations({ category: recCategory || undefined, limit: 100 }),
    enabled: tab === 'recommendations',
  })

  const invSummaryQ = useQuery({
    queryKey: ['gov-inventory-summary'],
    queryFn: () => govApi.getInventorySummary(),
  })

  const inventoryQ = useQuery({
    queryKey: ['gov-inventory'],
    queryFn: () => govApi.getInventory({ limit: 200 }),
    enabled: tab === 'inventory',
  })

  const s = summaryQ.data
  const rs = recSummaryQ.data
  const inv = invSummaryQ.data

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
            Resource governance — ownership coverage, label compliance, Advisor recommendations, and full inventory.
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
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {[
          { label: 'Billed Resources', value: s ? s.total_resources.toLocaleString() : '—',     color: 'border-gray-100' },
          { label: 'Unowned',          value: s ? s.unowned_resources.toLocaleString() : '—',   color: 'border-amber-100', sub: s ? `${s.unowned_pct}%` : undefined },
          { label: 'Avg Compliance',   value: s ? `${s.avg_compliance_pct}%` : '—',             color: s && s.avg_compliance_pct >= 90 ? 'border-emerald-100' : 'border-amber-100' },
          { label: 'Recommendations',  value: rs ? rs.total.toLocaleString() : '—',             color: 'border-blue-100',  sub: rs && rs.high_impact > 0 ? `${rs.high_impact} high` : undefined },
          { label: 'Est. Savings',     value: rs ? money.format(rs.total_estimated_savings_usd) : '—', color: 'border-emerald-100' },
          { label: 'Deployed Resources', value: inv ? inv.total_resources.toLocaleString() : '—', color: 'border-gray-100', sub: inv ? `${inv.resource_types} types` : undefined },
        ].map((k) => (
          <div key={k.label} className={`rounded-xl border ${k.color} bg-white p-4 shadow-sm`}>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">{k.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{k.value}</p>
            {k.sub && <p className="text-xs text-amber-600">{k.sub}</p>}
          </div>
        ))}
      </div>

      {/* Tab switcher */}
      <div className="flex flex-wrap rounded-lg border border-gray-200 bg-white p-1 shadow-sm w-fit gap-0.5">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.id
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Unowned tab ─────────────────────────────────────────────────────── */}
      {tab === 'unowned' && (
        <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          {unownedQ.isPending ? <SkeletonRows /> :
           unownedQ.isError ? (
            <div className="p-8 text-center text-sm text-red-500">Failed to load unowned costs data.</div>
           ) : (unownedQ.data ?? []).length === 0 ? (
            <EmptyState icon={Tag} message="All resources have an owner assigned." />
           ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {['Service', 'Resource ID', 'Region', 'Environment', 'Days Active', 'Cost (USD)'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(unownedQ.data as UnownedCostRow[]).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{row.service}</td>
                    <td className="max-w-[200px] truncate px-4 py-3 font-mono text-xs text-gray-500">{row.resource_id}</td>
                    <td className="px-4 py-3 text-gray-600">{row.region}</td>
                    <td className="px-4 py-3 text-gray-600">{row.environment}</td>
                    <td className="px-4 py-3 text-gray-600">{row.days_active}</td>
                    <td className="px-4 py-3 font-semibold text-gray-900">{money.format(row.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
           )}
        </div>
      )}

      {/* ── Compliance tab ──────────────────────────────────────────────────── */}
      {tab === 'compliance' && (
        <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          {complianceQ.isPending ? <SkeletonRows /> :
           complianceQ.isError ? (
            <div className="p-8 text-center text-sm text-red-500">Failed to load compliance data.</div>
           ) : (complianceQ.data ?? []).length === 0 ? (
            <EmptyState icon={AlertTriangle} message="No compliance data available." />
           ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {['Team', 'Total Cost', 'Untagged Cost', 'Compliance', ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(complianceQ.data as LabelComplianceRow[]).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{row.team}</td>
                    <td className="px-4 py-3 text-gray-700">{money.format(row.total_cost_usd)}</td>
                    <td className="px-4 py-3 text-gray-500">{money.format(row.untagged_cost_usd)}</td>
                    <td className="px-4 py-3"><ComplianceBadge pct={row.compliance_pct} /></td>
                    <td className="w-32 px-4 py-3"><ComplianceBar pct={row.compliance_pct} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
           )}
        </div>
      )}

      {/* ── Recommendations tab ─────────────────────────────────────────────── */}
      {tab === 'recommendations' && (
        <div className="space-y-4">
          {/* Category filter */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-600">Category:</span>
            {['', 'Cost', 'Security', 'Performance', 'HighAvailability', 'OperationalExcellence'].map((cat) => (
              <button
                key={cat}
                onClick={() => setRecCategory(cat)}
                className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                  recCategory === cat
                    ? 'bg-brand-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {cat || 'All'}
              </button>
            ))}
          </div>

          <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
            {recsQ.isPending ? <SkeletonRows /> :
             recsQ.isError ? (
              <div className="p-8 text-center text-sm text-red-500">Failed to load recommendations.</div>
             ) : (recsQ.data ?? []).length === 0 ? (
              <EmptyState icon={Lightbulb} message="No recommendations found. Your Azure environment looks healthy." />
             ) : (
              <table className="w-full text-sm">
                <thead className="border-b border-gray-100 bg-gray-50">
                  <tr>
                    {['Category', 'Impact', 'Resource', 'Description', 'Est. Savings / yr'].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {(recsQ.data as RecommendationRow[]).map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3"><CategoryBadge category={row.category} /></td>
                      <td className="px-4 py-3"><ImpactBadge impact={row.impact} /></td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-gray-800 truncate max-w-[160px]">{row.resource_name || '—'}</p>
                        <p className="text-xs text-gray-400 truncate max-w-[160px]">{row.resource_group}</p>
                      </td>
                      <td className="px-4 py-3 text-gray-700 max-w-[280px]">{row.short_description}</td>
                      <td className="px-4 py-3 font-semibold text-emerald-700">
                        {row.estimated_savings_usd != null ? money.format(row.estimated_savings_usd) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
             )}
          </div>
        </div>
      )}

      {/* ── Inventory tab ───────────────────────────────────────────────────── */}
      {tab === 'inventory' && (
        <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          {inventoryQ.isPending ? <SkeletonRows /> :
           inventoryQ.isError ? (
            <div className="p-8 text-center text-sm text-red-500">Failed to load inventory data.</div>
           ) : (inventoryQ.data ?? []).length === 0 ? (
            <EmptyState icon={Server} message="No inventory data yet. Trigger a sync to populate." />
           ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {['Name', 'Type', 'Resource Group', 'Location', 'Environment', 'Owner', 'SKU', 'State'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(inventoryQ.data as ResourceRow[]).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{row.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500 truncate max-w-[200px]">{row.resource_type.split('/').slice(-1)[0]}</td>
                    <td className="px-4 py-3 text-gray-600">{row.resource_group}</td>
                    <td className="px-4 py-3 text-gray-600">{row.location}</td>
                    <td className="px-4 py-3 text-gray-600 capitalize">{row.environment}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                        row.owner_team === 'untagged'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}>
                        {row.owner_team}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{row.sku_name || '—'}</td>
                    <td className="px-4 py-3"><StatesBadge state={row.provisioning_state} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
           )}
        </div>
      )}
    </div>
  )
}
