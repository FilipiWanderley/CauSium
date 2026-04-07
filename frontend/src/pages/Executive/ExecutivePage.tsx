import { useQuery } from '@tanstack/react-query'
import { executiveApi } from '../../api/executive'
import { MetricCard } from '../../components/Cards/MetricCard'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import clsx from 'clsx'

const fmt = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

export function ExecutivePage() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['executive', 'summary'],
    queryFn: () => executiveApi.summary().then((r) => r.data),
  })

  const { data: scorecard } = useQuery({
    queryKey: ['executive', 'scorecard'],
    queryFn: () => executiveApi.scorecard().then((r) => r.data),
  })

  if (summaryLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Executive View</h1>
        <p className="text-sm text-gray-500 mt-1">Financial performance, savings, and team efficiency</p>
      </div>

      {/* Top KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          title="Current Month Cost"
          value={fmt(summary?.current_month_cost_usd ?? 0)}
          change={summary?.mom_change_pct}
          changeLabel="MoM"
          variant={(summary?.mom_change_pct ?? 0) > 10 ? 'warning' : 'default'}
        />
        <MetricCard
          title="YTD Cloud Spend"
          value={fmt(summary?.ytd_cost_usd ?? 0)}
          subtitle="Year to date"
        />
        <MetricCard
          title="Realized Savings"
          value={fmt(summary?.total_realized_savings_usd ?? 0)}
          subtitle={`${fmt(summary?.savings_this_month_usd ?? 0)} this month`}
          variant="success"
        />
        <MetricCard
          title="Potential Savings"
          value={fmt(summary?.total_potential_savings_usd ?? 0)}
          subtitle={`${summary?.open_opportunities ?? 0} open opportunities`}
          variant="success"
        />
      </div>

      {/* Initiatives status */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCard title="In Progress" value={summary?.in_progress_initiatives ?? 0} subtitle="Initiatives" />
        <MetricCard title="Completed" value={summary?.completed_initiatives ?? 0} subtitle="Initiatives" variant="success" />
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-gray-500">Forecast Next Month</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {fmt(summary?.forecast_next_month_usd ?? 0)}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Confidence: {summary?.forecast_confidence ?? 'n/a'} · Linear projection
          </p>
        </div>
      </div>

      {/* Team scorecard */}
      {scorecard && scorecard.teams.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900">Team Efficiency Scorecard</h2>
            <span className="text-sm font-bold text-brand-600">
              Org Score: {scorecard.org_efficiency_score}/100
            </span>
          </div>

          <div className="mb-5 h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scorecard.teams.slice(0, 8)} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="team" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => [`${v}/100`, 'Score']} />
                <Bar dataKey="efficiency_score" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs font-medium text-gray-500">
                <th className="pb-2 pr-4">Team</th>
                <th className="pb-2 pr-4">Current Month</th>
                <th className="pb-2 pr-4">MoM</th>
                <th className="pb-2 pr-4">Open Opps</th>
                <th className="pb-2">Efficiency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {scorecard.teams.map((t) => (
                <tr key={t.team}>
                  <td className="py-2 pr-4 font-medium text-gray-900">{t.team}</td>
                  <td className="py-2 pr-4 text-gray-700">{fmt(t.current_month_cost_usd)}</td>
                  <td className={clsx('py-2 pr-4 text-xs font-medium', t.mom_change_pct > 0 ? 'text-red-600' : 'text-green-600')}>
                    {t.mom_change_pct > 0 ? '+' : ''}{t.mom_change_pct.toFixed(1)}%
                  </td>
                  <td className="py-2 pr-4 text-gray-600">{t.open_opportunities}</td>
                  <td className="py-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full bg-gray-100">
                        <div
                          className={clsx(
                            'h-full rounded-full',
                            t.efficiency_score >= 70 ? 'bg-green-500' :
                            t.efficiency_score >= 40 ? 'bg-yellow-500' : 'bg-red-400'
                          )}
                          style={{ width: `${t.efficiency_score}%` }}
                        />
                      </div>
                      <span className="text-xs font-semibold text-gray-700 w-8">
                        {t.efficiency_score}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Top savings */}
      {summary?.top_savings && summary.top_savings.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-900">Top Realized Savings</h2>
          <ul className="space-y-3">
            {summary.top_savings.map((s) => (
              <li key={s.initiative_id} className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">{s.title}</p>
                  {s.completed_at && (
                    <p className="text-xs text-gray-400">
                      Completed {new Date(s.completed_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <span className="text-sm font-bold text-green-600">
                  {fmt(s.realized_savings_usd)}/mo
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
