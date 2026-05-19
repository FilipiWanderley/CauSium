import { AlertTriangle, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

interface ErrorStateProps {
  title?: string
  description?: string
  onRetry?: () => void
  retryLabel?: string
  compact?: boolean
  className?: string
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'We could not load this data. Please try again.',
  onRetry,
  retryLabel = 'Try again',
  compact = false,
  className,
}: ErrorStateProps) {
  if (compact) {
    return (
      <div className={clsx('flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3', className)}>
        <AlertTriangle className="h-4 w-4 flex-shrink-0 text-red-500" />
        <p className="flex-1 text-sm text-red-700">{title}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 rounded-md border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 transition hover:bg-red-50"
          >
            <RefreshCw className="h-3 w-3" />
            {retryLabel}
          </button>
        )}
      </div>
    )
  }

  return (
    <div className={clsx(
      'rounded-xl border border-red-200 bg-red-50 px-6 py-10 text-center',
      className,
    )}>
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
        <AlertTriangle className="h-6 w-6 text-red-500" />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-red-900">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-red-700 max-w-md mx-auto">{description}</p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-700 shadow-sm transition hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
        >
          <RefreshCw className="h-4 w-4" />
          {retryLabel}
        </button>
      )}
    </div>
  )
}
