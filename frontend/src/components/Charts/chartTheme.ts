/**
 * CauSium Chart Theme — Enterprise-grade Recharts configuration.
 * Restrained, analytically strong, premium feel.
 */

import { chartColors } from '../../design-tokens'

// ─── Shared axis/grid/tooltip styling ────────────────────────────────────────

export const axisStyle = {
  fontSize: 10,
  fill: '#94a3b8', // slate-400
  fontFamily: 'Inter, system-ui, sans-serif',
} as const

export const gridStyle = {
  strokeDasharray: '3 3',
  stroke: '#f1f5f9', // slate-100
  strokeOpacity: 0.8,
} as const

export const tooltipStyle = {
  contentStyle: {
    fontSize: 12,
    fontFamily: 'Inter, system-ui, sans-serif',
    borderRadius: 8,
    border: '1px solid #e2e8f0', // slate-200
    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)',
    padding: '8px 12px',
    backgroundColor: '#ffffff',
  },
  labelStyle: {
    fontSize: 11,
    fontWeight: 600,
    color: '#1e293b', // slate-800
    marginBottom: 4,
  },
  itemStyle: {
    fontSize: 11,
    color: '#475569', // slate-600
    padding: '2px 0',
  },
  cursor: { stroke: '#cbd5e1', strokeWidth: 1, strokeDasharray: '4 4' },
} as const

// ─── Chart color sequences ───────────────────────────────────────────────────

export { chartColors }

/** Primary chart fill (area/bar) */
export const chartFill = {
  primary: '#2563eb',
  primaryLight: '#dbeafe', // blue-100
  positive: '#059669',
  positiveLight: '#d1fae5', // emerald-100
  warning: '#d97706',
  warningLight: '#fef3c7', // amber-100
  negative: '#dc2626',
  negativeLight: '#fee2e2', // rose-100
  neutral: '#64748b',
  neutralLight: '#f1f5f9', // slate-100
} as const

// ─── Bar chart defaults ──────────────────────────────────────────────────────

export const barDefaults = {
  radius: [4, 4, 0, 0] as [number, number, number, number],
  maxBarSize: 48,
} as const

// ─── Area chart defaults ─────────────────────────────────────────────────────

export const areaDefaults = {
  strokeWidth: 2,
  dot: false,
  activeDot: { r: 4, strokeWidth: 2, stroke: '#ffffff' },
} as const

// ─── Line chart defaults ─────────────────────────────────────────────────────

export const lineDefaults = {
  strokeWidth: 2,
  dot: false,
  activeDot: { r: 4, strokeWidth: 2, stroke: '#ffffff' },
} as const

// ─── Margin presets ──────────────────────────────────────────────────────────

export const chartMargin = {
  default: { top: 8, right: 8, left: 0, bottom: 0 },
  compact: { top: 4, right: 4, left: 0, bottom: 0 },
  withLabels: { top: 8, right: 8, left: 8, bottom: 8 },
} as const

// ─── Legend styling ──────────────────────────────────────────────────────────

export const legendStyle = {
  wrapperStyle: {
    fontSize: 11,
    fontFamily: 'Inter, system-ui, sans-serif',
    paddingTop: 12,
  },
  iconSize: 8,
  iconType: 'circle' as const,
} as const

// ─── Sparkline config (for inline mini charts) ──────────────────────────────

export const sparklineConfig = {
  width: 64,
  height: 24,
  strokeWidth: 1.5,
  colors: {
    positive: '#059669',
    negative: '#dc2626',
    warning: '#d97706',
    neutral: '#475569',
  },
} as const
