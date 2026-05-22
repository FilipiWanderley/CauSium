/**
 * Reusable cell renderers for DataTable.
 * Standardize how status, risk, confidence, savings, and providers display across tables.
 */

import clsx from 'clsx'

export interface ResponsiveMetaItem {
  label: string
  value: React.ReactNode
  valueClassName?: string
}

// ─── Badge Cell ──────────────────────────────────────────────────────────────

interface BadgeCellProps {
  label: string
  variant?: 'default' | 'positive' | 'warning' | 'negative' | 'info' | 'muted'
}

const BADGE_STYLES: Record<NonNullable<BadgeCellProps['variant']>, string> = {
  default: 'bg-slate-100 text-slate-700',
  positive: 'bg-emerald-50 text-emerald-700',
  warning: 'bg-amber-50 text-amber-700',
  negative: 'bg-rose-50 text-rose-700',
  info: 'bg-blue-50 text-blue-700',
  muted: 'bg-slate-50 text-slate-400',
}

export function BadgeCell({ label, variant = 'default' }: BadgeCellProps) {
  return (
    <span className={clsx('inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium', BADGE_STYLES[variant])}>
      {label}
    </span>
  )
}

// ─── Savings Cell ────────────────────────────────────────────────────────────

interface SavingsCellProps {
  monthly: number
  annual?: number
  formatter: (n: number) => string
}

export function SavingsCell({ monthly, annual, formatter }: SavingsCellProps) {
  return (
    <div>
      <span className="font-semibold tabular-nums text-emerald-700">{formatter(monthly)}</span>
      {annual !== undefined && (
        <p className="mt-0.5 text-[10px] tabular-nums text-slate-400">{formatter(annual)}/yr</p>
      )}
    </div>
  )
}

// ─── Percent Cell ────────────────────────────────────────────────────────────

interface PercentCellProps {
  value: number | null
  label?: string
}

export function PercentCell({ value, label }: PercentCellProps) {
  if (value == null) return <span className="text-slate-300">—</span>
  return (
    <span className="tabular-nums text-slate-700">
      {Math.round(value * 100)}%{label && <span className="ml-1 text-slate-400">{label}</span>}
    </span>
  )
}

// ─── Delta Cell (change indicator) ──────────────────────────────────────────

interface DeltaCellProps {
  value: number
  formatter?: (n: number) => string
  /** If true, positive = bad (cost increase) */
  invertSemantic?: boolean
}

export function DeltaCell({ value, formatter, invertSemantic = false }: DeltaCellProps) {
  const isPositive = value > 0
  const isNegative = value < 0
  const goodColor = invertSemantic ? 'text-emerald-700' : 'text-rose-700'
  const badColor = invertSemantic ? 'text-rose-700' : 'text-emerald-700'

  return (
    <span className={clsx('font-medium tabular-nums', isPositive ? goodColor : isNegative ? badColor : 'text-slate-500')}>
      {value > 0 ? '+' : ''}{formatter ? formatter(value) : `${value.toFixed(1)}%`}
    </span>
  )
}

// ─── Truncated Text Cell ─────────────────────────────────────────────────────

interface TruncatedCellProps {
  primary: string
  secondary?: string | null
  maxLines?: 1 | 2
}

export function TruncatedCell({ primary, secondary, maxLines = 1 }: TruncatedCellProps) {
  return (
    <div className="min-w-0">
      <p className={clsx('font-medium text-slate-800', maxLines === 1 ? 'line-clamp-1' : 'line-clamp-2')}>{primary}</p>
      {secondary && <p className="mt-0.5 text-[10px] text-slate-400 line-clamp-1">{secondary}</p>}
    </div>
  )
}

// ─── Timestamp Cell ──────────────────────────────────────────────────────────

interface TimestampCellProps {
  value: string
  locale?: string
}

export function TimestampCell({ value, locale = 'en-US' }: TimestampCellProps) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return <span className="text-slate-400">{value}</span>
  return (
    <span className="text-slate-500 tabular-nums">
      {new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(date)}
    </span>
  )
}

// ─── Responsive Admin/Table Helpers ──────────────────────────────────────────

interface ResponsiveMetaListProps {
  items: ResponsiveMetaItem[]
  className?: string
}

export function ResponsiveMetaList({ items, className }: ResponsiveMetaListProps) {
  const visibleItems = items.filter((item) => item.value !== null && item.value !== undefined && item.value !== '')

  if (!visibleItems.length) return null

  return (
    <dl className={clsx('mt-2 grid grid-cols-1 gap-x-3 gap-y-1 text-[11px] text-slate-500 sm:hidden', className)}>
      {visibleItems.map((item) => (
        <div key={item.label} className="flex items-start justify-between gap-3">
          <dt className="shrink-0 text-slate-400">{item.label}</dt>
          <dd className={clsx('min-w-0 text-right text-slate-600', item.valueClassName)}>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

interface ResponsivePrimaryCellProps {
  title: React.ReactNode
  subtitle?: React.ReactNode
  meta?: ResponsiveMetaItem[]
  className?: string
}

export function ResponsivePrimaryCell({ title, subtitle, meta, className }: ResponsivePrimaryCellProps) {
  return (
    <div className={clsx('min-w-0', className)}>
      <div className="min-w-0">
        <p className="font-medium text-slate-800 break-words">{title}</p>
        {subtitle && <p className="mt-0.5 break-words text-[11px] text-slate-400">{subtitle}</p>}
      </div>
      {meta && <ResponsiveMetaList items={meta} />}
    </div>
  )
}

// ─── Score Cell (composite score with visual indicator) ─────────────────────

interface ScoreCellProps {
  score: number
  max?: number
}

export function ScoreCell({ score, max = 100 }: ScoreCellProps) {
  const pct = (score / max) * 100
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-10 rounded-full bg-slate-100">
        <div
          className={clsx('h-full rounded-full transition-all', pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-400' : 'bg-rose-400')}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
      <span className="text-[10px] font-semibold tabular-nums text-slate-700">{score.toFixed(0)}</span>
    </div>
  )
}
