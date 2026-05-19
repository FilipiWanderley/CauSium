import clsx from 'clsx'
import type { ConfidenceTier, EffortLevel, OpportunityStatus, RiskLevel } from '../../types'

type BadgeVariant = 'status' | 'risk' | 'confidence' | 'effort' | 'custom'
type BadgeSize = 'sm' | 'md'

interface StatusBadgeProps {
  variant: BadgeVariant
  value: string
  label?: string
  size?: BadgeSize
  className?: string
}

const STATUS_STYLES: Record<OpportunityStatus, string> = {
  open: 'bg-sky-100 text-sky-700',
  in_progress: 'bg-amber-100 text-amber-700',
  resolved: 'bg-emerald-100 text-emerald-700',
  dismissed: 'bg-gray-100 text-gray-700',
  validated: 'bg-blue-100 text-blue-700',
}

const RISK_STYLES: Record<RiskLevel, string> = {
  low: 'bg-emerald-50 text-emerald-700',
  medium: 'bg-amber-50 text-amber-700',
  high: 'bg-red-50 text-red-700',
}

const CONFIDENCE_STYLES: Record<ConfidenceTier, string> = {
  high: 'bg-slate-100 text-slate-700',
  medium: 'bg-slate-50 text-slate-600',
  low: 'bg-amber-50 text-amber-700',
  insufficient: 'bg-gray-100 text-gray-500',
}

const EFFORT_STYLES: Record<EffortLevel, string> = {
  low: 'bg-blue-50 text-blue-700',
  medium: 'bg-purple-50 text-purple-700',
  high: 'bg-orange-50 text-orange-700',
}

function getStyle(variant: BadgeVariant, value: string): string {
  switch (variant) {
    case 'status':
      return STATUS_STYLES[value as OpportunityStatus] ?? 'bg-gray-100 text-gray-600'
    case 'risk':
      return RISK_STYLES[value as RiskLevel] ?? 'bg-gray-100 text-gray-600'
    case 'confidence':
      return CONFIDENCE_STYLES[value as ConfidenceTier] ?? 'bg-gray-100 text-gray-600'
    case 'effort':
      return EFFORT_STYLES[value as EffortLevel] ?? 'bg-gray-100 text-gray-600'
    default:
      return 'bg-gray-100 text-gray-600'
  }
}

export function StatusBadge({ variant, value, label, size = 'sm', className }: StatusBadgeProps) {
  const displayText = label ?? value

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full font-medium',
        getStyle(variant, value),
        size === 'sm' && 'px-2 py-0.5 text-xs',
        size === 'md' && 'px-2.5 py-1 text-xs',
        className,
      )}
    >
      {displayText}
    </span>
  )
}
