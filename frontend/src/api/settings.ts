import { apiClient } from './client'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface FinOpsSettings {
  monitored_tag_key: string
}

export interface FinOpsSettingsUpdate {
  monitored_tag_key: string
}

// Predefined tag options for the dropdown
export const TAG_OPTIONS = [
  { value: 'team', label: 'team' },
  { value: 'owner', label: 'owner' },
  { value: 'squad', label: 'squad' },
  { value: 'application', label: 'application' },
  { value: 'business_unit', label: 'business_unit' },
  { value: 'costcenter', label: 'costcenter' },
  { value: 'product', label: 'product' },
  { value: 'project', label: 'project' },
  { value: 'department', label: 'department' },
] as const

export type TagOption = (typeof TAG_OPTIONS)[number]['value']

// ── API client ─────────────────────────────────────────────────────────────────

export const settingsApi = {
  getFinOpsSettings: (): Promise<FinOpsSettings> =>
    apiClient.get('/settings/finops').then((r) => r.data),

  updateFinOpsSettings: (settings: FinOpsSettingsUpdate): Promise<FinOpsSettings> =>
    apiClient.put('/settings/finops', settings).then((r) => r.data),
}