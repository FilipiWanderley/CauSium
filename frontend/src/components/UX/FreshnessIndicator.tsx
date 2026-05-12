import { Clock } from 'lucide-react'
import clsx from 'clsx'

interface FreshnessIndicatorProps {
  label: string
  variant?: 'muted' | 'subtle'
  className?: string
}

export function FreshnessIndicator({
  label,
  variant = 'muted',
  className,
}: FreshnessIndicatorProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 text-xs',
        variant === 'muted' && 'text-gray-400',
        variant === 'subtle' && 'text-gray-500',
        className,
      )}
    >
      <Clock className="h-3 w-3" />
      {label}
    </span>
  )
}
