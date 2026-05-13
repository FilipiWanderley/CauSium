function parseFlag(value: string | boolean | undefined) {
  if (typeof value === 'boolean') return value
  if (typeof value !== 'string') return false
  return ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export const featureFlags = {
  enterpriseShell: parseFlag(import.meta.env.VITE_FF_ENTERPRISE_SHELL),
  breadcrumbs: parseFlag(import.meta.env.VITE_FF_BREADCRUMBS),
  scopeSelector: parseFlag(import.meta.env.VITE_FF_SCOPE_SELECTOR),
} as const

export function isFeatureEnabled(flag: keyof typeof featureFlags) {
  return featureFlags[flag]
}
