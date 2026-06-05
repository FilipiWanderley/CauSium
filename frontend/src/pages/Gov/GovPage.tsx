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
import { useI18n } from '../../contexts/I18nContext'
import { usePageTitle } from '../../hooks/usePageTitle'
import { SectionIntro } from '../../components/Layout/SectionIntro'
import { ExplainTooltip } from '../../components/UX/ExplainTooltip'
import { DEFAULT_DISPLAY_CURRENCY, formatCurrency } from '../../utils/currency'

// ── Formatters ────────────────────────────────────────────────────────────────

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

function ImpactBadge({ impact, label }: { impact: string; label: string }) {
  const color =
    impact === 'High'   ? 'bg-red-100 text-red-700' :
    impact === 'Medium' ? 'bg-amber-100 text-amber-700' :
                          'bg-gray-100 text-gray-600'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${color}`}>
      {label}
    </span>
  )
}

function CategoryBadge({ category, label }: { category: string; label: string }) {
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
      {label}
    </span>
  )
}

function StatesBadge({ state, labelSucceeded, labelFailed }: { state: string; labelSucceeded: string; labelFailed: string }) {
  const color =
    state === 'Succeeded' ? 'bg-emerald-100 text-emerald-700' :
    state === 'Failed'    ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-500'
  const display =
    state === 'Succeeded' ? labelSucceeded :
    state === 'Failed'    ? labelFailed :
    state || '—'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${color}`}>
      {display}
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

// ── Page ──────────────────────────────────────────────────────────────────────

export function GovPage() {
  const { t } = useI18n()
  const g = t.gov
  const ux = t.ux
  usePageTitle(g.title)
  const formatMoney = (value: number) => formatCurrency(value, DEFAULT_DISPLAY_CURRENCY)

  const TABS: { id: Tab; label: string }[] = [
    { id: 'unowned',         label: g.tabUnowned         },
    { id: 'compliance',      label: g.tabCompliance      },
    { id: 'recommendations', label: g.tabRecommendations },
    { id: 'inventory',       label: g.tabInventory       },
  ]

  const CATEGORY_LABELS: Record<string, string> = {
    Cost:                  g.catCost,
    Security:              g.catSecurity,
    Performance:           g.catPerformance,
    HighAvailability:      g.catHighAvailability,
    OperationalExcellence: g.catOperationalExcellence,
  }

  const IMPACT_LABELS: Record<string, string> = {
    High:   g.impactHigh,
    Medium: g.impactMedium,
    Low:    g.impactLow,
  }

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
            {g.title}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {g.subtitle}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-violet-50 px-2.5 py-1 font-medium text-violet-700">
              {g.governanceMetric}
            </span>
            <span className="rounded-full bg-gray-100 px-2.5 py-1 font-medium text-gray-700">
              {g.organizationWide}
            </span>
            <ExplainTooltip text={ux.tooltipGovernance} />
          </div>
        </div>

        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value={7}>{g.last7}</option>
          <option value={30}>{g.last30}</option>
          <option value={90}>{g.last90}</option>
        </select>
      </div>

      {/* KPI strip */}
      <div className="space-y-4">
        <SectionIntro
          title={g.sectionTitle}
          subtitle={g.sectionSubtitle}
          freshness={ux.freshnessRefreshes}
          badges={[
            { label: g.governanceMetric, tone: 'governance' },
            { label: g.organizationWide, tone: 'organization' },
          ]}
        />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {[
            { label: g.billedResources, value: s ? s.total_resources.toLocaleString() : '—', color: 'border-slate-900 bg-slate-900 text-white', sub: g.resourcesUnit, valueClass: 'text-white', labelClass: 'text-slate-300', subClass: 'text-slate-300' },
            { label: g.unowned, value: s ? s.unowned_resources.toLocaleString() : '—', color: 'border-amber-100', sub: s ? `${s.unowned_pct}%` : g.resourcesUnit },
            { label: g.avgCompliance, value: s ? `${s.avg_compliance_pct}%` : '—', color: s && s.avg_compliance_pct >= 90 ? 'border-emerald-100' : 'border-amber-100', sub: g.complianceUnit },
            { label: g.recommendations, value: rs ? rs.total.toLocaleString() : '—', color: 'border-blue-100', sub: rs && rs.high_impact > 0 ? `${rs.high_impact} ${g.impactHigh.toLowerCase()}` : undefined },
            { label: g.estSavings, value: rs ? formatMoney(rs.total_estimated_savings_usd) : '—', color: 'border-emerald-100', sub: g.organizationWide },
            { label: g.deployedResources, value: inv ? inv.total_resources.toLocaleString() : '—', color: 'border-gray-100', sub: inv ? `${inv.resource_types} ${g.types}` : g.resourcesUnit },
          ].map((k) => (
            <div key={k.label} className={`rounded-xl border ${k.color} p-4 shadow-sm ${k.color.includes('bg-slate-900') ? '' : 'bg-white'}`}>
              <p className={`text-xs font-medium uppercase tracking-wide ${k.labelClass ?? 'text-gray-400'}`}>{k.label}</p>
              <p className={`mt-1 text-2xl font-bold ${k.valueClass ?? 'text-gray-900'}`}>{k.value}</p>
              {k.sub && <p className={`text-xs ${k.subClass ?? 'text-amber-600'}`}>{k.sub}</p>}
            </div>
          ))}
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex flex-wrap rounded-lg border border-gray-200 bg-white p-1 shadow-sm w-fit gap-0.5">
        {TABS.map((tabItem) => (
          <button
            key={tabItem.id}
            onClick={() => setTab(tabItem.id)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === tabItem.id
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {tabItem.label}
          </button>
        ))}
      </div>

      {/* ── Unowned tab ─────────────────────────────────────────────────────── */}
      {tab === 'unowned' && (
        <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          {unownedQ.isPending ? <SkeletonRows /> :
           unownedQ.isError ? (
            <div className="p-8 text-center text-sm text-red-500">{g.errorUnowned}</div>
           ) : (unownedQ.data ?? []).length === 0 ? (
            <EmptyState icon={Tag} message={g.allOwned} />
           ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {[g.colService, g.colResourceId, g.colRegion, g.colEnvironment, g.colDaysActive, g.colCost].map((h) => (
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
                    <td className="px-4 py-3 font-semibold text-gray-900">{formatMoney(row.cost_usd)}</td>
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
            <div className="p-8 text-center text-sm text-red-500">{g.errorCompliance}</div>
           ) : (complianceQ.data ?? []).length === 0 ? (
            <EmptyState icon={AlertTriangle} message={g.noCompliance} />
           ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {[g.colTeam, g.colTotalCost, g.colUntaggedCost, g.colCompliance, ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(complianceQ.data as LabelComplianceRow[]).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{row.team}</td>
                    <td className="px-4 py-3 text-gray-700">{formatMoney(row.total_cost_usd)}</td>
                    <td className="px-4 py-3 text-gray-500">{formatMoney(row.untagged_cost_usd)}</td>
                    <td className="px-4 py-3"><ComplianceBadge pct={row.compliance_pct} /></td>
                    <td className="w-32 px-4 py-3"><ComplianceBar pct={row.compliance_pct} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Nota sobre custos sem equipe */}
            {(complianceQ.data as LabelComplianceRow[])?.some(r =>
              r.team === 'Sem equipe identificada' || r.team === 'No team mapped'
            ) && (
              <div className="px-4 py-3 bg-blue-50 border-t border-blue-100 text-xs text-blue-700">
                <strong>Nota:</strong> Custos sem tags de equipe no Azure foram agrupados como "Sem equipe identificada".
                Para classificar, configure tags <code>team</code>, <code>owner</code> ou <code>squad</code> nos recursos Azure.
              </div>
            )}
           )}
        </div>
      )}

      {/* ── Recommendations tab ─────────────────────────────────────────────── */}
      {tab === 'recommendations' && (
        <div className="space-y-4">
          {/* Category filter */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-600">{g.colCategory}:</span>
            {(['', 'Cost', 'Security', 'Performance', 'HighAvailability', 'OperationalExcellence'] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setRecCategory(cat)}
                className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                  recCategory === cat
                    ? 'bg-brand-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {cat ? (CATEGORY_LABELS[cat] ?? cat) : t.common.all}
              </button>
            ))}
          </div>

          <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
            {recsQ.isPending ? <SkeletonRows /> :
             recsQ.isError ? (
              <div className="p-8 text-center text-sm text-red-500">{g.errorRecommendations}</div>
             ) : (recsQ.data ?? []).length === 0 ? (
              <EmptyState icon={Lightbulb} message={g.noRecommendations} />
             ) : (
              <table className="w-full text-sm">
                <thead className="border-b border-gray-100 bg-gray-50">
                  <tr>
                    {[g.colCategory, g.colImpact, g.colResource, g.colDescription, g.colEstSavings].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {(recsQ.data as RecommendationRow[]).map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <CategoryBadge category={row.category} label={CATEGORY_LABELS[row.category] ?? row.category} />
                      </td>
                      <td className="px-4 py-3">
                        <ImpactBadge impact={row.impact} label={IMPACT_LABELS[row.impact] ?? row.impact} />
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-gray-800 truncate max-w-[160px]">{row.resource_name || '—'}</p>
                        <p className="text-xs text-gray-400 truncate max-w-[160px]">{row.resource_group}</p>
                      </td>
                      <td className="px-4 py-3 text-gray-700 max-w-[280px]">{row.short_description}</td>
                      <td className="px-4 py-3 font-semibold text-emerald-700">
                        {row.estimated_savings_usd != null ? formatMoney(row.estimated_savings_usd) : '—'}
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
            <div className="p-8 text-center text-sm text-red-500">{g.errorInventory}</div>
           ) : (inventoryQ.data ?? []).length === 0 ? (
            <EmptyState icon={Server} message={g.noInventory} />
           ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {[g.colName, g.colType, g.colResourceGroup, g.colLocation, g.colEnvironment, g.colOwner, g.colSku, g.colState].map((h) => (
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
                        {row.owner_team === 'untagged' ? g.untagged : row.owner_team}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{row.sku_name || '—'}</td>
                    <td className="px-4 py-3">
                      <StatesBadge
                        state={row.provisioning_state}
                        labelSucceeded={g.stateSucceeded}
                        labelFailed={g.stateFailed}
                      />
                    </td>
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
