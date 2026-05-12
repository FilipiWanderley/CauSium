import { CheckCircle, Clock, AlertTriangle, XCircle } from 'lucide-react'
import clsx from 'clsx'
import type { ReconciliationStatus } from '../../types'
import { useI18n } from '../../contexts/I18nContext'

const STATUS_CONFIG: Record<ReconciliationStatus, { icon: React.ElementType; className: string }> = {
  healthy: { icon: CheckCircle, className: 'bg-green-50 text-green-700' },
  delayed: { icon: Clock, className: 'bg-yellow-50 text-yellow-700' },
  partial: { icon: AlertTriangle, className: 'bg-orange-50 text-orange-700' },
  warning: { icon: XCircle, className: 'bg-red-50 text-red-700' },
}

interface ReconciliationBadgeProps {
  status: ReconciliationStatus
  className?: string
}

export function ReconciliationBadge({ status, className }: ReconciliationBadgeProps) {
  const { t } = useI18n()
  const config = STATUS_CONFIG[status]
  const Icon = config.icon
  const labelMap: Record<ReconciliationStatus, string> = {
    healthy: t.ux.integrityHealthy,
    delayed: t.ux.integrityDelayed,
    partial: t.ux.integrityPartial,
    warning: t.ux.integrityWarning,
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold',
        config.className,
        className,
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {labelMap[status]}
    </span>
  )
}
