import clsx from 'clsx'
import { TrendingDown, TrendingUp, Minus } from 'lucide-react'
import type { StatusTone } from '../../design-tokens'

interface SparklinePoint {
  value: number
}

interface KpiCardProps {
  title: string
  value: string | number
  delta?: number
  deltaLabel?: string
  tone?: StatusTone
  sparkline?: SparklinePoint[]
  footer?: React.ReactNode
  icon?: React.ReactNode
  loading?: boolean
  compact?: boolean
}

function MiniSparkline({ data, tone }: { data: SparklinePoint[]; tone: StatusTone }) {
  if (data.length < 2) return null
  const values = data.map((d) => d.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const width = 64
  const height = 24
  const padding = 2

  const points = values.map((v, i) => {
    const x = padding + (i / (values.length - 1)) * (width - padding * 2)
    const y = height - padding - ((v - min) / range) * (height - padding * 2)
    return `${x},${y}`
  })

  const strokeColor =
    tone === 'positive' ? '#0FA287' :
    tone === 'negative' ? '#dc2626' :
    tone === 'warning' ? '#d97706' :
    '#64748B'

  return (
    <svg width={width} height={height} className="shrink-0" aria-hidden="true">
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function SkeletonKpi() {
  return (
    <div className="animate-pulse space-y-3 p-5">
      <div className="h-3 w-24 rounded bg-slate-200" />
      <div className="h-7 w-32 rounded bg-slate-200" />
      <div className="h-3 w-20 rounded bg-slate-100" />
    </div>
  )
}

export function KpiCard({
  title,
  value,
  delta,
  deltaLabel,
  tone = 'neutral',
  sparkline,
  footer,
  icon,
  loading = false,
  compact = false,
}: KpiCardProps) {
  if (loading) {
    return (
      <div className="rounded-panel border border-slate-200 bg-white shadow-panel">
        <SkeletonKpi />
      </div>
    )
  }

  const isPositive = delta !== undefined && delta > 0
  const isNegative = delta !== undefined && delta < 0

  const toneStyles = {
    positive: 'border-l-teal-500',
    warning: 'border-l-amber-500',
    negative: 'border-l-rose-500',
    neutral: 'border-l-gray-cool',
    info: 'border-l-brand-500',
  }

  return (
    <div
      className={clsx(
        'rounded-panel border border-gray-light bg-white shadow-card-premium transition-shadow hover:shadow-panel-hover',
        'border-l-[3px]',
        toneStyles[tone],
        compact ? 'p-4' : 'p-5',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-cool truncate">
            {title}
          </p>
          <p
            className={clsx(
              'mt-1.5 font-bold tracking-tight tabular-nums text-navy',
              compact ? 'text-kpi-sm' : 'text-kpi-md',
            )}
          >
            {value}
          </p>
          {delta !== undefined && (
            <div className="mt-2 flex items-center gap-1.5">
              {isPositive ? (
                <TrendingUp className="h-3.5 w-3.5 text-teal-600" />
              ) : isNegative ? (
                <TrendingDown className="h-3.5 w-3.5 text-emerald-600" />
              ) : (
                <Minus className="h-3.5 w-3.5 text-gray-cool" />
              )}
              <span
                className={clsx(
                  'text-sm font-medium tabular-nums',
                  isPositive && 'text-teal-600',
                  isNegative && 'text-emerald-600',
                  !isPositive && !isNegative && 'text-gray-cool',
                )}
              >
                {delta > 0 ? '+' : ''}{delta.toFixed(1)}%
              </span>
              {deltaLabel && (
                <span className="text-xs text-gray-cool ml-0.5">{deltaLabel}</span>
              )}
            </div>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          {icon && (
            <div className="rounded-lg bg-gray-light p-2 text-gray-cool">
              {icon}
            </div>
          )}
          {sparkline && sparkline.length > 1 && (
            <MiniSparkline data={sparkline} tone={tone} />
          )}
        </div>
      </div>
      {footer && (
        <div className="mt-3 border-t border-gray-light pt-3 text-xs text-gray-cool">
          {footer}
        </div>
      )}
    </div>
  )
}
