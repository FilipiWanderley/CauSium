import { apiClient } from './client'

export interface GreenSummary {
  total_kg_co2e: number
  total_cost_usd: number
  intensity_avg: number
  mom_delta_pct: number | null
  months_available: number
  data_source: 'official' | 'estimated' | 'mixed'
  note: string
}

export interface EmissionsMonthRow {
  month: string
  kg_co2e: number
  cost_usd: number
  delta_pct: number | null
}

export interface EmissionsBreakdownRow {
  dimension: string
  kg_co2e: number
  cost_usd: number
  share_pct: number
}

export type BreakdownDimension = 'service' | 'region' | 'environment' | 'owner_team'

export const greenApi = {
  getSummary: (months = 6): Promise<GreenSummary> =>
    apiClient.get('/green/summary', { params: { months } }).then((r) => r.data),

  getEmissions: (months = 12): Promise<EmissionsMonthRow[]> =>
    apiClient.get('/green/emissions', { params: { months } }).then((r) => r.data),

  getBreakdown: (by: BreakdownDimension = 'service', days = 30): Promise<EmissionsBreakdownRow[]> =>
    apiClient.get('/green/breakdown', { params: { by, days } }).then((r) => r.data),
}
