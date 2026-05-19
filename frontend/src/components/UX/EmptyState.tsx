import clsx from 'clsx'
import { Search, Lightbulb, FileText } from 'lucide-react'

type EmptyIcon = 'search' | 'lightbulb' | 'document'

interface EmptyStateProps {
  icon?: EmptyIcon
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

const ICONS: Record<EmptyIcon, React.ElementType> = {
  search: Search,
  lightbulb: Lightbulb,
  document: FileText,
}

export function EmptyState({ icon = 'lightbulb', title, description, action, className }: EmptyStateProps) {
  const Icon = ICONS[icon]

  return (
    <div className={clsx(
      'rounded-xl border-2 border-dashed border-gray-200 bg-white px-6 py-12 text-center',
      className,
    )}>
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
        <Icon className="h-6 w-6 text-gray-400" />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-gray-900">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto">{description}</p>
      )}
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-4 inline-flex items-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
