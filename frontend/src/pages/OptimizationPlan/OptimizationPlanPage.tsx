import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { intelApi } from '../../api/intel'
import { useI18n } from '../../contexts/I18nContext'

export function OptimizationPlanPage() {
  const { t, language } = useI18n()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['optimization-plan', language],
    queryFn: async () => {
      const response = await intelApi.optimizationPlan({
        language: language === 'pt' ? 'pt' : 'en',
        include_ai_summary: true,
      })
      return response.data
    },
  })

  const currency = useMemo(
    () =>
      new Intl.NumberFormat(language === 'pt' ? 'pt-BR' : 'en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
      }),
    [language]
  )

  if (isLoading) {
    return <div className="p-6 text-sm text-gray-400">{t.common.loading}</div>
  }
  if (isError || !data) {
    return <div className="p-6 text-sm text-red-400">{t.optimizationPlan.error}</div>
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">{t.optimizationPlan.title}</h1>
        <p className="text-sm text-gray-400">{t.optimizationPlan.subtitle}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label={t.optimizationPlan.adjustedMonthly}
          value={currency.format(data.total_savings_monthly_adjusted_usd)}
        />
        <MetricCard
          label={t.optimizationPlan.adjustedAnnual}
          value={currency.format(data.total_savings_annual_adjusted_usd)}
        />
        <MetricCard
          label={t.optimizationPlan.quickWins}
          value={String(data.quick_wins.length)}
        />
        <MetricCard
          label={t.optimizationPlan.conflicts}
          value={String(data.conflict_hints.length)}
        />
      </div>

      <section className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <div className="text-sm font-medium text-gray-200">{t.optimizationPlan.summary}</div>
        <p className="mt-2 text-sm text-gray-300">{data.summary}</p>
      </section>

      {data.conflict_hints.length > 0 && (
        <section className="rounded-xl border border-amber-700/60 bg-amber-900/10 p-4">
          <div className="text-sm font-medium text-amber-300">{t.optimizationPlan.conflictHints}</div>
          <ul className="mt-2 space-y-1 text-sm text-amber-100">
            {data.conflict_hints.map((hint) => (
              <li key={hint}>- {hint}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-xl border border-gray-800 bg-gray-900">
        <div className="border-b border-gray-800 px-4 py-3 text-sm font-medium text-gray-200">
          {t.optimizationPlan.prioritized}
        </div>
        <div className="divide-y divide-gray-800">
          {data.prioritized.map((item) => (
            <article key={item.opportunity_id} className="space-y-1 px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-medium text-white">
                  #{item.rank} {item.title}
                </div>
                <div className="text-xs text-gray-300">
                  {t.optimizationPlan.score}: {item.priority_score.toFixed(3)}
                </div>
              </div>
              <div className="text-xs text-gray-400">
                {t.optimizationPlan.savings}: {currency.format(item.estimated_monthly_savings_usd)} / {t.common.monthly}
              </div>
              <div className="text-xs text-gray-500">{item.why_now}</div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      <div className="text-xs uppercase tracking-wide text-gray-400">{label}</div>
      <div className="mt-1 text-xl font-semibold text-white">{value}</div>
    </div>
  )
}
