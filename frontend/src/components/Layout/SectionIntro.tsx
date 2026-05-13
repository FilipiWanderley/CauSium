import clsx from 'clsx'
import { FreshnessIndicator } from '../UX/FreshnessIndicator'

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
  freshness?: string
}

const BADGE_DOT_STYLES: Record<BadgeTone, string> = {
  financial: 'bg-emerald-500',
  operational: 'bg-blue-500',
  governance: 'bg-violet-500',
  organization: 'bg-gray-400',
  subscription: 'bg-sky-500',
  billing: 'bg-amber-500',
  sustainability: 'bg-teal-500',
  secondary: 'bg-slate-400',
}

export function SectionIntro({
  title,
  subtitle,
  badges = [],
  compact = false,
  freshness,
}: SectionIntroProps) {
  return (
    <div className={clsx('flex flex-col gap-3', compact && 'gap-2')}>
      <div>
        <div className="flex items-center gap-3">
          <h2 className={clsx('font-semibold text-gray-900', compact ? 'text-sm' : 'text-base sm:text-lg')}>
            {title}
          </h2>
          {freshness && <FreshnessIndicator label={freshness} />}
        </div>
        <p className={clsx('mt-1 text-gray-500', compact ? 'text-xs' : 'text-sm')}>
          {subtitle}
        </p>
      </div>
      {badges.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-500">
          {badges.map((badge) => (
            <span
              key={`${badge.tone ?? 'secondary'}-${badge.label}`}
              className="inline-flex items-center gap-1.5 font-medium"
            >
              <span className={clsx('h-1.5 w-1.5 rounded-full', BADGE_DOT_STYLES[badge.tone ?? 'secondary'])} />
              {badge.label}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
