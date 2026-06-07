import { apiClient } from './client'

// ── Existing types ─────────────────────────────────────────────────────────────

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

// ── Tag Compliance ─────────────────────────────────────────────────────────────

export interface TopUntaggedRow {
  name: string
  cost_usd: number
  record_count: number
}

export interface TagComplianceMetrics {
  configured_tag_key: string
  total_cost: number
  tagged_cost: number
  untagged_cost: number
  coverage_pct: number
  total_records: number
  tagged_records: number
  untagged_records: number
  top_untagged_resource_groups: TopUntaggedRow[]
  top_untagged_services: TopUntaggedRow[]
}

export interface RecommendationRow {
  recommendation_id: string
  category: string
  impact: string
  resource_id: string
  resource_name: string
  resource_group: string
  service: string
  short_description: string
  estimated_savings_usd: number | null
}

export interface RecommendationsSummary {
  total: number
  high_impact: number
  total_estimated_savings_usd: number
  by_category: Record<string, number>
}

// ── Inventory ──────────────────────────────────────────────────────────────────

export interface ResourceRow {
  resource_id: string
  name: string
  resource_type: string
  resource_group: string
  location: string
  environment: string
  owner_team: string
  sku_name: string
  provisioning_state: string
}

export interface InventorySummary {
  total_resources: number
  resource_types: number
  resource_groups: number
  unowned_resources: number
}

// ── API client ─────────────────────────────────────────────────────────────────

export const govApi = {
  getSummary: (days = 30): Promise<GovSummary> =>
    apiClient.get('/gov/summary', { params: { days } }).then((r) => r.data),

  getUnownedCosts: (days = 30, limit = 50): Promise<UnownedCostRow[]> =>
    apiClient.get('/gov/unowned-costs', { params: { days, limit } }).then((r) => r.data),

  getLabelCompliance: (days = 30): Promise<LabelComplianceRow[]> =>
    apiClient.get('/gov/label-compliance', { params: { days } }).then((r) => r.data),

  getRecommendationsSummary: (): Promise<RecommendationsSummary> =>
    apiClient.get('/gov/recommendations/summary').then((r) => r.data),

  getRecommendations: (params?: {
    category?: string
    impact?: string
    limit?: number
  }): Promise<RecommendationRow[]> =>
    apiClient.get('/gov/recommendations', { params }).then((r) => r.data),

  getInventorySummary: (): Promise<InventorySummary> =>
    apiClient.get('/gov/inventory/summary').then((r) => r.data),

  getInventory: (params?: {
    resource_type?: string
    owner_team?: string
    environment?: string
    limit?: number
    offset?: number
  }): Promise<ResourceRow[]> =>
    apiClient.get('/gov/inventory', { params }).then((r) => r.data),

  getTagCompliance: (tagKey = 'team', days = 30): Promise<TagComplianceMetrics> =>
    apiClient.get('/gov/tag-compliance', { params: { tag_key: tagKey, days } }).then((r) => r.data),
}
