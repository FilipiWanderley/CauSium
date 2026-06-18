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
  open: 'bg-teal-50 text-teal-700',
  in_progress: 'bg-amber-50 text-amber-700',
  resolved: 'bg-teal-50 text-teal-800',
  dismissed: 'bg-gray-light text-gray-cool',
  validated: 'bg-teal-50 text-teal-700',
}

const RISK_STYLES: Record<RiskLevel, string> = {
  low: 'bg-teal-50 text-teal-700',
  medium: 'bg-amber-50 text-amber-700',
  high: 'bg-rose-50 text-rose-700',
}

const CONFIDENCE_STYLES: Record<ConfidenceTier, string> = {
  high: 'bg-teal-50 text-teal-700',
  medium: 'bg-gray-light text-gray-cool',
  low: 'bg-amber-50 text-amber-700',
  insufficient: 'bg-gray-light text-gray-cool',
}

const EFFORT_STYLES: Record<EffortLevel, string> = {
  low: 'bg-blue-50 text-blue-700',
  medium: 'bg-purple-50 text-purple-700',
  high: 'bg-orange-50 text-orange-700',
}

function getStyle(variant: BadgeVariant, value: string): string {
  switch (variant) {
    case 'status':
      return STATUS_STYLES[value as OpportunityStatus] ?? 'bg-gray-light text-gray-cool'
    case 'risk':
      return RISK_STYLES[value as RiskLevel] ?? 'bg-gray-light text-gray-cool'
    case 'confidence':
      return CONFIDENCE_STYLES[value as ConfidenceTier] ?? 'bg-gray-light text-gray-cool'
    case 'effort':
      return EFFORT_STYLES[value as EffortLevel] ?? 'bg-gray-light text-gray-cool'
    default:
      return 'bg-gray-light text-gray-cool'
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
