import { apiClient } from './client'

export interface GovSummary {
  total_resources: number
  unowned_resources: number
  unowned_cost_usd: number
  unowned_pct: number
  teams_evaluated: number
  avg_compliance_pct: number
}

export interface UnownedCostRow {
  service: string
  resource_id: string
  region: string
  environment: string
  cost_usd: number
  days_active: number
}

export interface LabelComplianceRow {
  team: string
  total_cost_usd: number
  untagged_cost_usd: number
  compliance_pct: number
}

export const govApi = {
  getSummary: (days = 30): Promise<GovSummary> =>
    apiClient.get('/gov/summary', { params: { days } }).then((r) => r.data),

  getUnownedCosts: (days = 30, limit = 50): Promise<UnownedCostRow[]> =>
    apiClient.get('/gov/unowned-costs', { params: { days, limit } }).then((r) => r.data),

  getLabelCompliance: (days = 30): Promise<LabelComplianceRow[]> =>
    apiClient.get('/gov/label-compliance', { params: { days } }).then((r) => r.data),
}
