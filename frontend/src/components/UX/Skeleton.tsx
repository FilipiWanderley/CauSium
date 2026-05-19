import clsx from 'clsx'

interface SkeletonProps {
  className?: string
}

export function SkeletonLine({ className }: SkeletonProps) {
  return (
    <div className={clsx('animate-pulse rounded bg-gray-200', className ?? 'h-4 w-full')} />
  )
}

export function SkeletonCard({ className }: SkeletonProps) {
  return (
    <div className={clsx('animate-pulse rounded-xl border border-gray-100 bg-gray-50 p-5', className)}>
      <div className="h-3 w-24 rounded bg-gray-200" />
      <div className="mt-3 h-6 w-32 rounded bg-gray-200" />
    </div>
  )
}

export function SkeletonTableRow({ columns = 6 }: { columns?: number }) {
  const widths = ['w-40', 'w-24', 'w-20', 'w-28', 'w-16', 'w-20', 'w-24', 'w-16']
  return (
    <tr className="border-b border-gray-50">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className={clsx('animate-pulse rounded bg-gray-200 h-4', widths[i % widths.length])} />
        </td>
      ))}
    </tr>
  )
}

export function SkeletonMetricCards({ count = 4 }: { count?: number }) {
  return (
    <div className={clsx('grid gap-4', count === 4 ? 'grid-cols-2 lg:grid-cols-4' : 'grid-cols-2 md:grid-cols-3')}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

export function SkeletonTable({ rows = 8, columns = 6 }: { rows?: number; columns?: number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              {Array.from({ length: columns }).map((_, i) => (
                <th key={i} className="px-4 py-3">
                  <div className="animate-pulse rounded bg-gray-200 h-3 w-16" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rows }).map((_, i) => (
              <SkeletonTableRow key={i} columns={columns} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function SkeletonSection({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <div className="animate-pulse rounded bg-gray-200 h-4 w-40" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={clsx('animate-pulse rounded bg-gray-100 h-3', i === lines - 1 ? 'w-3/4' : 'w-full')} />
      ))}
    </div>
  )
}

export function SkeletonPrioritizedList({ items = 5 }: { items?: number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <div className="animate-pulse rounded bg-gray-200 h-4 w-32" />
      </div>
      <div className="divide-y divide-gray-100">
        {Array.from({ length: items }).map((_, i) => (
          <div key={i} className="px-4 py-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="animate-pulse rounded bg-gray-200 h-4 w-48" />
              <div className="animate-pulse rounded bg-gray-200 h-4 w-16" />
            </div>
            <div className="animate-pulse rounded bg-gray-100 h-3 w-32" />
            <div className="animate-pulse rounded bg-gray-100 h-3 w-64" />
          </div>
        ))}
      </div>
    </div>
  )
}
