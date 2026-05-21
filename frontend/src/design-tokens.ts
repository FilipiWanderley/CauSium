/**
 * CauSium Design Tokens — Semantic color system and data visualization palette.
 * Enterprise-grade, restrained, analytically strong.
 */

export const colors = {
  // Surface hierarchy
  surface: {
    page: 'bg-slate-50',
    panel: 'bg-white',
    panelHover: 'hover:bg-slate-50/50',
    sunken: 'bg-slate-100/60',
    elevated: 'bg-white shadow-sm',
  },

  // Border system
  border: {
    subtle: 'border-slate-150',
    default: 'border-slate-200',
    strong: 'border-slate-300',
    focus: 'border-brand-500',
  },

  // Text hierarchy
  text: {
    primary: 'text-slate-900',
    secondary: 'text-slate-600',
    tertiary: 'text-slate-400',
    inverse: 'text-white',
    muted: 'text-slate-500',
  },

  // Semantic status tones
  status: {
    positive: {
      text: 'text-emerald-700',
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    },
    warning: {
      text: 'text-amber-700',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      badge: 'bg-amber-50 text-amber-700 border-amber-200',
    },
    negative: {
      text: 'text-rose-700',
      bg: 'bg-rose-50',
      border: 'border-rose-200',
      badge: 'bg-rose-50 text-rose-700 border-rose-200',
    },
    neutral: {
      text: 'text-slate-600',
      bg: 'bg-slate-50',
      border: 'border-slate-200',
      badge: 'bg-slate-50 text-slate-600 border-slate-200',
    },
    info: {
      text: 'text-blue-700',
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      badge: 'bg-blue-50 text-blue-700 border-blue-200',
    },
  },

  // Data visualization palette (8 colors, colorblind-safe)
  chart: {
    primary: '#2563eb',
    secondary: '#0891b2',
    tertiary: '#7c3aed',
    quaternary: '#059669',
    quinary: '#d97706',
    senary: '#dc2626',
    septenary: '#4f46e5',
    octonary: '#0d9488',
  },
} as const

export const chartColors = [
  colors.chart.primary,
  colors.chart.secondary,
  colors.chart.tertiary,
  colors.chart.quaternary,
  colors.chart.quinary,
  colors.chart.senary,
  colors.chart.septenary,
  colors.chart.octonary,
]

// Spacing rhythm for page sections
export const spacing = {
  page: {
    x: 'px-4 lg:px-6',
    y: 'py-5 lg:py-6',
    gap: 'gap-6',
  },
  section: {
    gap: 'gap-5',
    inner: 'p-5',
  },
  panel: {
    padding: 'p-5',
    paddingCompact: 'p-4',
    gap: 'gap-4',
  },
} as const

// Typography presets for KPI/metric display
export const typography = {
  kpiLarge: 'text-3xl font-bold tracking-tight tabular-nums',
  kpiMedium: 'text-2xl font-bold tracking-tight tabular-nums',
  kpiSmall: 'text-xl font-semibold tabular-nums',
  kpiDelta: 'text-sm font-medium tabular-nums',
  sectionTitle: 'text-base font-semibold text-slate-900',
  sectionSubtitle: 'text-sm text-slate-500',
  panelTitle: 'text-sm font-semibold text-slate-800',
  panelSubtitle: 'text-xs text-slate-500',
  label: 'text-xs font-medium uppercase tracking-wide text-slate-500',
  caption: 'text-[11px] text-slate-400',
} as const

export type StatusTone = keyof typeof colors.status
