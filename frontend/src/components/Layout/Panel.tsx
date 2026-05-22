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
        'rounded-panel border border-slate-200 bg-white shadow-panel',
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
          <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
          {badge}
        </div>
        {subtitle && (
          <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
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
    <div className={clsx('border-t border-slate-100 pt-4 mt-4', className)}>
      {title && (
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400 mb-3">{title}</p>
      )}
      {children}
    </div>
  )
}
