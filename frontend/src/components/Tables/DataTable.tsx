import { useState, useMemo, useCallback } from 'react'
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react'
import clsx from 'clsx'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface DataTableColumn<T> {
  key: string
  header: string
  /** Render cell content. Receives the row item. */
  render: (item: T) => React.ReactNode
  /** Sort comparator. If provided, column is sortable. */
  sortFn?: (a: T, b: T) => number
  /** Column alignment */
  align?: 'left' | 'center' | 'right'
  /** Responsive visibility */
  hideBelow?: 'sm' | 'md' | 'lg' | 'xl'
  /** Fixed width class (e.g. 'w-[280px]') */
  width?: string
  /** Whether this column should be sticky */
  sticky?: boolean
}

export type DataTableDensity = 'compact' | 'comfortable'

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  data: T[]
  /** Unique key extractor */
  getRowKey: (item: T) => string
  /** Row click handler */
  onRowClick?: (item: T) => void
  /** Density mode */
  density?: DataTableDensity
  /** Default sort column key */
  defaultSortKey?: string
  /** Default sort direction */
  defaultSortDir?: 'asc' | 'desc'
  /** Sticky header */
  stickyHeader?: boolean
  /** Loading state */
  loading?: boolean
  /** Loading row count for skeleton */
  loadingRows?: number
  /** Empty state content */
  emptyTitle?: string
  emptyDescription?: string
  /** Optional className for the wrapper */
  className?: string
  /** Optional row className */
  rowClassName?: string | ((item: T) => string)
}

// ─── Component ───────────────────────────────────────────────────────────────

export function DataTable<T>({
  columns,
  data,
  getRowKey,
  onRowClick,
  density = 'compact',
  defaultSortKey,
  defaultSortDir = 'desc',
  stickyHeader = false,
  loading = false,
  loadingRows = 8,
  emptyTitle = 'No data',
  emptyDescription,
  className,
  rowClassName,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(defaultSortKey ?? null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>(defaultSortDir)

  const handleSort = useCallback((key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }, [sortKey])

  const sortedData = useMemo(() => {
    if (!sortKey) return data
    const col = columns.find((c) => c.key === sortKey)
    if (!col?.sortFn) return data
    const sorted = [...data].sort(col.sortFn)
    return sortDir === 'asc' ? sorted.reverse() : sorted
  }, [data, sortKey, sortDir, columns])

  const cellPadding = density === 'compact' ? 'px-3 py-2' : 'px-4 py-3'
  const headerPadding = density === 'compact' ? 'px-3 py-2' : 'px-4 py-2.5'

  const hideClass = (col: DataTableColumn<T>) => {
    if (!col.hideBelow) return ''
    return `hidden ${col.hideBelow}:table-cell`
  }

  if (loading) {
    return (
      <div className={clsx('rounded-panel border border-slate-200 bg-white shadow-panel overflow-hidden', className)}>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/60">
                {columns.map((col) => (
                  <th key={col.key} className={clsx(headerPadding, hideClass(col))}>
                    <div className="h-3 w-16 rounded bg-slate-200 animate-pulse" />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {Array.from({ length: loadingRows }).map((_, i) => (
                <tr key={i}>
                  {columns.map((col) => (
                    <td key={col.key} className={clsx(cellPadding, hideClass(col))}>
                      <div className="h-3.5 rounded bg-slate-100 animate-pulse" style={{ width: `${50 + Math.random() * 40}%` }} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  if (!sortedData.length) {
    return (
      <div className={clsx('rounded-panel border border-dashed border-slate-200 bg-slate-50/50 px-6 py-12 text-center', className)}>
        <p className="text-sm font-medium text-slate-600">{emptyTitle}</p>
        {emptyDescription && <p className="mt-1 text-xs text-slate-400">{emptyDescription}</p>}
      </div>
    )
  }

  return (
    <div className={clsx('rounded-panel border border-slate-200 bg-white shadow-panel overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead className={stickyHeader ? 'sticky top-0 z-10' : ''}>
            <tr className="border-b border-slate-100 bg-slate-50/60 text-left">
              {columns.map((col) => {
                const isSortable = !!col.sortFn
                const isActive = sortKey === col.key
                return (
                  <th
                    key={col.key}
                    className={clsx(
                      headerPadding,
                      hideClass(col),
                      col.width,
                      col.align === 'right' && 'text-right',
                      col.align === 'center' && 'text-center',
                      isSortable && 'cursor-pointer select-none hover:bg-slate-100/60 transition-colors',
                    )}
                    onClick={isSortable ? () => handleSort(col.key) : undefined}
                  >
                    <div className={clsx('inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider', isActive ? 'text-slate-700' : 'text-slate-400')}>
                      {col.header}
                      {isSortable && (
                        isActive ? (
                          sortDir === 'desc' ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronsUpDown className="h-3 w-3 opacity-40" />
                        )
                      )}
                    </div>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {sortedData.map((item) => {
              const key = getRowKey(item)
              const rowCls = typeof rowClassName === 'function' ? rowClassName(item) : rowClassName
              return (
                <tr
                  key={key}
                  className={clsx(
                    'transition-colors',
                    onRowClick && 'cursor-pointer hover:bg-slate-50/80',
                    rowCls,
                  )}
                  onClick={onRowClick ? () => onRowClick(item) : undefined}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={clsx(
                        cellPadding,
                        'align-top',
                        hideClass(col),
                        col.align === 'right' && 'text-right',
                        col.align === 'center' && 'text-center',
                      )}
                    >
                      {col.render(item)}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
