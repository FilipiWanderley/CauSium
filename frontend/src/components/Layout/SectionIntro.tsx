import clsx from 'clsx'

type BadgeTone =
  | 'financial'
  | 'operational'
  | 'governance'
  | 'organization'
  | 'subscription'
  | 'billing'
  | 'sustainability'
  | 'secondary'

interface SectionBadge {
  label: string
  tone?: BadgeTone
}

interface SectionIntroProps {
  title: string
  subtitle: string
  badges?: SectionBadge[]
  compact?: boolean
}

const BADGE_STYLES: Record<BadgeTone, string> = {
  financial: 'bg-emerald-50 text-emerald-700',
  operational: 'bg-blue-50 text-blue-700',
  governance: 'bg-violet-50 text-violet-700',
  organization: 'bg-gray-100 text-gray-700',
  subscription: 'bg-sky-50 text-sky-700',
  billing: 'bg-amber-50 text-amber-700',
  sustainability: 'bg-teal-50 text-teal-700',
  secondary: 'bg-slate-100 text-slate-700',
}

export function SectionIntro({
  title,
  subtitle,
  badges = [],
  compact = false,
}: SectionIntroProps) {
  return (
    <div className={clsx('flex flex-col gap-3', compact && 'gap-2')}>
      <div>
        <h2 className={clsx('font-semibold text-gray-900', compact ? 'text-sm' : 'text-base sm:text-lg')}>
          {title}
        </h2>
        <p className={clsx('mt-1 text-gray-500', compact ? 'text-xs' : 'text-sm')}>
          {subtitle}
        </p>
      </div>
      {badges.length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs">
          {badges.map((badge) => (
            <span
              key={`${badge.tone ?? 'secondary'}-${badge.label}`}
              className={clsx(
                'rounded-full px-2.5 py-1 font-medium',
                BADGE_STYLES[badge.tone ?? 'secondary'],
              )}
            >
              {badge.label}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
