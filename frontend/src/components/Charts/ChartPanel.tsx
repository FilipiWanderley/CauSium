import clsx from 'clsx'

interface ChartPanelProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  children: React.ReactNode
  loading?: boolean
  empty?: boolean
  emptyMessage?: string
  className?: string
  height?: number | string
}

function ChartSkeleton({ height }: { height: number | string }) {
  return (
    <div
      className="animate-pulse rounded-lg bg-slate-100/80"
      style={{ height: typeof height === 'number' ? `${height}px` : height }}
    >
      <div className="flex h-full items-end justify-between gap-1 px-6 pb-4 pt-8">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 rounded-t bg-slate-200/80"
            style={{ height: `${20 + Math.random() * 60}%` }}
          />
        ))}
      </div>
    </div>
  )
}

function EmptyChart({ message, height }: { message: string; height: number | string }) {
  return (
    <div
      className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/50"
      style={{ height: typeof height === 'number' ? `${height}px` : height }}
    >
      <div className="text-center">
        <div className="mx-auto mb-2 h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center">
          <svg className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </svg>
        </div>
        <p className="text-xs text-slate-400">{message}</p>
      </div>
    </div>
  )
}

export function ChartPanel({
  title,
  subtitle,
  actions,
  children,
  loading = false,
  empty = false,
  emptyMessage = 'No data available',
  className,
  height = 280,
}: ChartPanelProps) {
  return (
    <div
      className={clsx(
        'rounded-panel border border-slate-200 bg-white shadow-panel',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      <div className="px-5 pb-5">
        {loading ? (
          <ChartSkeleton height={height} />
        ) : empty ? (
          <EmptyChart message={emptyMessage} height={height} />
        ) : (
          children
        )}
      </div>
    </div>
  )
}
