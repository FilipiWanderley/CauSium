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
  const width = 72
  const height = 32
  const padding = 3

  const points = values.map((v, i) => {
    const x = padding + (i / (values.length - 1)) * (width - padding * 2)
    const y = height - padding - ((v - min) / range) * (height - padding * 2)
    return `${x},${y}`
  })

  const areaPoints = [
    `${padding},${height - padding}`,
    ...points,
    `${width - padding},${height - padding}`,
  ]

  const strokeColor =
    tone === 'positive' ? '#0FA287' :
    tone === 'negative' ? '#dc2626' :
    tone === 'warning' ? '#d97706' :
    '#64748B'

  const areaColor =
    tone === 'positive' ? 'rgba(15, 162, 135, 0.1)' :
    tone === 'negative' ? 'rgba(220, 38, 38, 0.1)' :
    tone === 'warning' ? 'rgba(217, 119, 6, 0.1)' :
    'rgba(100, 116, 139, 0.1)'

  return (
    <svg width={width} height={height} className="shrink-0" aria-hidden="true">
      <defs>
        <linearGradient id={`sparkGrad-${tone}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.15" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={areaPoints.join(' ')}
        fill={`url(#sparkGrad-${tone})`}
      />
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={strokeColor}
        strokeWidth="2"
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
      <div className="h-8 w-36 rounded bg-slate-200" />
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
    positive: {
      border: 'border-l-teal-500',
      iconBg: 'bg-tealal-50',
      iconColor: 'text-teal-600',
      valueColor: 'text-navy',
      deltaPositive: 'text-teal-600',
      deltaNegative: 'text-emerald-600',
    },
    warning: {
      border: 'border-l-amber-500',
      iconBg: 'bg-amber-50',
      iconColor: 'text-amber-600',
      valueColor: 'text-navy',
      deltaPositive: 'text-teal-600',
      deltaNegative: 'text-emerald-600',
    },
    negative: {
      border: 'border-l-rose-500',
      iconBg: 'bg-rose-50',
      iconColor: 'text-rose-600',
      valueColor: 'text-navy',
      deltaPositive: 'text-teal-600',
      deltaNegative: 'text-emerald-600',
    },
    neutral: {
      border: 'border-l-slate-300',
      iconBg: 'bg-slate-100',
      iconColor: 'text-slate-500',
      valueColor: 'text-navy',
      deltaPositive: 'text-teal-600',
      deltaNegative: 'text-emerald-600',
    },
    info: {
      border: 'border-l-brand-500',
      iconBg: 'bg-brand-50',
      iconColor: 'text-brand-600',
      valueColor: 'text-navy',
      deltaPositive: 'text-teal-600',
      deltaNegative: 'text-emerald-600',
    },
  }

  const styles = toneStyles[tone]

  return (
    <div
      className={clsx(
        'group relative overflow-hidden rounded-xl border border-gray-light bg-white shadow-card-premium',
        'transition-all duration-200 hover:shadow-panel-hover hover:border-teal-200',
        'border-l-[4px]',
        styles.border,
        compact ? 'p-4' : 'p-5',
      )}
    >
      {/* Subtle gradient overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-transparent to-transparent opacity-0 transition-opacity duration-200 group-hover:opacity-100" />

      <div className="relative flex items-start justify-between gap-4">
        {/* Left: Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <p className={clsx(
            'text-xs font-medium uppercase tracking-wider',
            compact ? 'text-gray-cool' : 'text-slate-500'
          )}>
            {title}
          </p>

          {/* Value */}
          <p
            className={clsx(
              'mt-2 font-bold tracking-tight tabular-nums',
              styles.valueColor,
              compact ? 'text-xl' : 'text-2xl md:text-3xl',
            )}
          >
            {value}
          </p>

          {/* Delta */}
          {delta !== undefined && (
            <div className="mt-2 flex items-center gap-1.5">
              {isPositive ? (
                <TrendingUp className={clsx('h-4 w-4', styles.deltaPositive)} />
              ) : isNegative ? (
                <TrendingDown className={clsx('h-4 w-4', styles.deltaNegative)} />
              ) : (
                <Minus className="h-4 w-4 text-gray-cool" />
              )}
              <span
                className={clsx(
                  'text-sm font-semibold tabular-nums',
                  isPositive && styles.deltaPositive,
                  isNegative && styles.deltaNegative,
                  !isPositive && !isNegative && 'text-gray-cool',
                )}
              >
                {delta > 0 ? '+' : ''}{delta.toFixed(1)}%
              </span>
              {deltaLabel && (
                <span className="text-xs text-gray-cool ml-1">{deltaLabel}</span>
              )}
            </div>
          )}

          {/* Footer */}
          {footer && (
            <div className="mt-3 border-t border-gray-light/60 pt-3">
              <p className="text-xs text-gray-cool leading-relaxed">{footer}</p>
            </div>
          )}
        </div>

        {/* Right: Icon + Sparkline */}
        <div className="flex flex-col items-end gap-3">
          {icon && (
            <div className={clsx(
              'rounded-xl p-2.5 transition-transform duration-200 group-hover:scale-110',
              styles.iconBg,
              styles.iconColor
            )}>
              {icon}
            </div>
          )}
          {sparkline && sparkline.length > 1 && (
            <MiniSparkline data={sparkline} tone={tone} />
          )}
        </div>
      </div>
    </div>
  )
}
