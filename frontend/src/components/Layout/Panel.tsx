import clsx from 'clsx'

interface PanelProps {
  children: React.ReactNode
  className?: string
  compact?: boolean
  flush?: boolean
}

export function Panel({ children, className, compact = false, flush = false }: PanelProps) {
  return (
    <div
      className={clsx(
        'rounded-panel border border-gray-light bg-white shadow-card-premium',
        !flush && (compact ? 'p-4' : 'p-5'),
        className,
      )}
    >
      {children}
    </div>
  )
}

interface PanelHeaderProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  badge?: React.ReactNode
}

export function PanelHeader({ title, subtitle, actions, badge }: PanelHeaderProps) {
  return (
    <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 w-full flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-navy">{title}</h3>
          {badge}
        </div>
        {subtitle && (
          <p className="mt-0.5 text-xs text-gray-cool">{subtitle}</p>
        )}
      </div>
      {actions && (
        <div className="flex max-w-full flex-wrap items-center gap-2 sm:shrink-0 sm:justify-end">
          {actions}
        </div>
      )}
    </div>
  )
}

interface PanelSectionProps {
  children: React.ReactNode
  title?: string
  className?: string
}

export function PanelSection({ children, title, className }: PanelSectionProps) {
  return (
    <div className={clsx('border-t border-gray-light pt-4 mt-4', className)}>
      {title && (
        <p className="text-xs font-medium uppercase tracking-wide text-gray-cool mb-3">{title}</p>
      )}
      {children}
    </div>
  )
}
