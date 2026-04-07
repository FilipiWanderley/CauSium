import clsx from 'clsx'
import { TrendingDown, TrendingUp } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  change?: number
  changeLabel?: string
  icon?: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger'
}

export function MetricCard({
  title,
  value,
  subtitle,
  change,
  changeLabel,
  icon,
  variant = 'default',
}: MetricCardProps) {
  const isPositiveChange = change !== undefined && change > 0
  const isNegativeChange = change !== undefined && change < 0

  return (
    <div
      className={clsx(
        'rounded-xl border bg-white p-5 shadow-sm',
        variant === 'success' && 'border-green-200',
        variant === 'warning' && 'border-yellow-200',
        variant === 'danger' && 'border-red-200',
        variant === 'default' && 'border-gray-200'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
          )}
          {change !== undefined && (
            <div className="mt-2 flex items-center gap-1">
              {isPositiveChange ? (
                <TrendingUp className="h-3.5 w-3.5 text-red-500" />
              ) : isNegativeChange ? (
                <TrendingDown className="h-3.5 w-3.5 text-green-500" />
              ) : null}
              <span
                className={clsx(
                  'text-xs font-medium',
                  isPositiveChange && 'text-red-600',
                  isNegativeChange && 'text-green-600',
                  !isPositiveChange && !isNegativeChange && 'text-gray-500'
                )}
              >
                {change > 0 ? '+' : ''}{change?.toFixed(1)}%{' '}
                {changeLabel && (
                  <span className="text-gray-400">{changeLabel}</span>
                )}
              </span>
            </div>
          )}
        </div>
        {icon && (
          <div className="rounded-lg bg-gray-50 p-2.5 text-gray-400">{icon}</div>
        )}
      </div>
    </div>
  )
}
