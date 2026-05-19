/**
 * Shared formatting utilities for dates, numbers, and percentages.
 * All user-facing screens should use these instead of ad-hoc formatting.
 */

// ─── Date formatting ────────────────────────────────────────────────────────

const DATE_SHORT_OPTS: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
}

const DATE_FULL_OPTS: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
}

const DATE_RELATIVE_UNITS: [number, Intl.RelativeTimeFormatUnit][] = [
  [60, 'second'],
  [3600, 'minute'],
  [86400, 'hour'],
  [604800, 'day'],
  [2592000, 'week'],
  [31536000, 'month'],
  [Infinity, 'year'],
]

/**
 * Format a date string or Date to a short display format.
 * Example: "Jan 15, 2025"
 */
export function formatDateShort(value: string | Date | null | undefined, locale = 'en-US'): string {
  if (!value) return '—'
  const date = typeof value === 'string' ? new Date(value) : value
  if (isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(locale, DATE_SHORT_OPTS)
}

/**
 * Format a date string or Date to a full display format with time.
 * Example: "Jan 15, 2025, 14:30"
 */
export function formatDateFull(value: string | Date | null | undefined, locale = 'en-US'): string {
  if (!value) return '—'
  const date = typeof value === 'string' ? new Date(value) : value
  if (isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(locale, DATE_FULL_OPTS)
}

/**
 * Format a date as relative time (e.g., "3 days ago", "in 2 hours").
 * Falls back to short date if older than 30 days.
 */
export function formatDateRelative(value: string | Date | null | undefined, locale = 'en-US'): string {
  if (!value) return '—'
  const date = typeof value === 'string' ? new Date(value) : value
  if (isNaN(date.getTime())) return '—'

  const diffSeconds = Math.round((date.getTime() - Date.now()) / 1000)
  const absDiff = Math.abs(diffSeconds)

  // If older than 30 days, use short date
  if (absDiff > 2592000) return formatDateShort(date, locale)

  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })

  for (const [threshold, unit] of DATE_RELATIVE_UNITS) {
    if (absDiff < threshold) {
      const prevThreshold = DATE_RELATIVE_UNITS[DATE_RELATIVE_UNITS.indexOf([threshold, unit]) - 1]?.[0] ?? 1
      const value = Math.round(diffSeconds / prevThreshold)
      return rtf.format(value, unit)
    }
  }

  return formatDateShort(date, locale)
}

// ─── Number formatting ──────────────────────────────────────────────────────

/**
 * Format a number with locale-aware thousands separators.
 * Example: 1234567 → "1,234,567"
 */
export function formatNumber(value: number | null | undefined, locale = 'en-US'): string {
  if (value == null) return '—'
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value)
}

/**
 * Format a number as compact (e.g., 1.2K, 3.4M).
 */
export function formatCompact(value: number | null | undefined, locale = 'en-US'): string {
  if (value == null) return '—'
  return new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

// ─── Percentage formatting ──────────────────────────────────────────────────

/**
 * Format a decimal (0–1) or percentage (0–100) as a display percentage.
 * Automatically detects if the value is already in percentage form (>1 or <-1).
 */
export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—'
  // If value is between -1 and 1, treat as decimal (multiply by 100)
  const pct = Math.abs(value) <= 1 ? value * 100 : value
  return `${pct >= 0 ? '' : ''}${pct.toFixed(decimals)}%`
}

/**
 * Format a percentage with sign (e.g., "+12.3%", "-5.0%").
 */
export function formatPercentSigned(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—'
  const pct = Math.abs(value) <= 1 ? value * 100 : value
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(decimals)}%`
}
