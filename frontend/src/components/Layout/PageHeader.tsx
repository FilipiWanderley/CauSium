import clsx from 'clsx'

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  meta?: React.ReactNode
  className?: string
}

export function PageHeader({ title, subtitle, actions, meta, className }: PageHeaderProps) {
  return (
    <div className={clsx('flex flex-col gap-1', className)}>
      <div className="flex flex-col items-start gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 w-full flex-1">
          <h1 className="text-xl font-bold tracking-tight text-slate-900">{title}</h1>
          {subtitle && (
            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          )}
        </div>
        {actions && (
          <div className="flex max-w-full flex-wrap items-center gap-2 md:shrink-0 md:justify-end">
            {actions}
          </div>
        )}
      </div>
      {meta && (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
          {meta}
        </div>
      )}
    </div>
  )
}
