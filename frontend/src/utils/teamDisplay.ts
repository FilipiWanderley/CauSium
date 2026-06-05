export const UNMAPPED_TEAM_LABEL = 'Sem equipe identificada'

export function formatTeamGroupingLabel(value: string | null | undefined) {
  if (value == null) return value
  return value.trim().toLowerCase() === 'untagged' ? UNMAPPED_TEAM_LABEL : value
}
