export const UNMAPPED_TEAM_LABEL = 'Sem equipe identificada'

/**
 * Known team prefixes inferred from Resource Group patterns.
 * These are displayed when Azure Cost Management API does not return team tags.
 */
export const KNOWN_TEAM_PREFIXES = [
  'CSC',
  'CQG',
  'Engetec',
  'Vital',
  'QGI',
  'QGGN',
  'QGSA',
  'Frontis',
  'Datalake',
] as const

export function isKnownTeamLabel(label: string): boolean {
  return KNOWN_TEAM_PREFIXES.includes(label as typeof KNOWN_TEAM_PREFIXES[number])
}

export function formatTeamGroupingLabel(value: string | null | undefined) {
  if (value == null) return value
  const trimmed = value.trim().toLowerCase()
  if (trimmed === 'untagged') return UNMAPPED_TEAM_LABEL
  return value
}

/**
 * Get display label for team with inference awareness.
 * Teams from Resource Group inference are: CSC, CQG, Engetec, Vital, QGI, QGGN, QGSA, Frontis, Datalake
 */
export function getTeamDisplayLabel(ownerTeam: string | null | undefined, resourceGroup?: string): string {
  if (!ownerTeam) return UNMAPPED_TEAM_LABEL
  const trimmed = ownerTeam.trim().toLowerCase()
  if (trimmed === 'untagged') return UNMAPPED_TEAM_LABEL
  return ownerTeam
}
