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
  emphasis?: 'default' | 'primary' | 'secondary'
  action?: React.ReactNode
}

export function MetricCard({
  title,
  value,
  subtitle,
  change,
  changeLabel,
  icon,
  variant = 'default',
  emphasis = 'default',
  action,
}: MetricCardProps) {
  const isPositiveChange = change !== undefined && change > 0
  const isNegativeChange = change !== undefined && change < 0

  return (
    <div
      className={clsx(
        'rounded-xl border p-5 shadow-sm',
        variant === 'success' && 'border-green-200',
        variant === 'warning' && 'border-yellow-200',
        variant === 'danger' && 'border-red-200',
        variant === 'default' && 'border-gray-200',
        emphasis === 'default' && 'bg-white',
        emphasis === 'primary' && 'bg-slate-900 text-white shadow-md',
        emphasis === 'secondary' && 'bg-slate-50'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className={clsx(
            'text-sm font-medium',
            emphasis === 'primary' ? 'text-slate-200' : 'text-gray-500',
          )}>{title}</p>
          <p className={clsx(
            'mt-1 text-2xl font-bold',
            emphasis === 'primary' ? 'text-white' : 'text-gray-900',
          )}>{value}</p>
          {subtitle && (
            <p className={clsx(
              'mt-1 text-sm',
              emphasis === 'primary' ? 'text-slate-300' : 'text-gray-500',
            )}>{subtitle}</p>
          )}
          {change !== undefined && (
            <div className="mt-2 flex items-center gap-1">
              {isPositiveChange ? (
                <TrendingUp className={clsx('h-3.5 w-3.5', emphasis === 'primary' ? 'text-red-300' : 'text-red-500')} />
              ) : isNegativeChange ? (
                <TrendingDown className={clsx('h-3.5 w-3.5', emphasis === 'primary' ? 'text-green-300' : 'text-green-500')} />
              ) : null}
              <span
                className={clsx(
                  'text-xs font-medium',
                  isPositiveChange && (emphasis === 'primary' ? 'text-red-200' : 'text-red-600'),
                  isNegativeChange && (emphasis === 'primary' ? 'text-green-200' : 'text-green-600'),
                  !isPositiveChange && !isNegativeChange && (emphasis === 'primary' ? 'text-slate-300' : 'text-gray-500')
                )}
              >
                {change > 0 ? '+' : ''}{change?.toFixed(1)}%{' '}
                {changeLabel && (
                  <span className={clsx(emphasis === 'primary' ? 'text-slate-400' : 'text-gray-400')}>{changeLabel}</span>
                )}
              </span>
            </div>
          )}
          {action && <div className="mt-3">{action}</div>}
        </div>
        {icon && (
          <div className={clsx(
            'rounded-lg p-2.5',
            emphasis === 'primary' ? 'bg-white/10 text-slate-200' : 'bg-gray-50 text-gray-400',
          )}>{icon}</div>
        )}
      </div>
    </div>
  )
}
