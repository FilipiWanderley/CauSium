import { apiClient } from './client'

export interface CostCoverage {
  total_cost_facts_30d: number
  first_cost_date: string | null
  last_cost_date: string | null
  providers: string[]
  subscriptions_count: number
  currencies: string[]
  total_cost_30d_usd: number
}

export interface UsageCoverage {
  total_usage_facts_30d: number
  metric_names: string[]
  has_cpu_metric: boolean
  has_memory_metric: boolean
  has_aks_agentpool_metrics: boolean
  agentpool_resource_count: number
  observation_days: number
}

export interface OpportunitiesStatus {
  total_opportunities: number
  opportunities_by_status: Record<string, number>
  opportunities_by_category: Record<string, number>
  open_opportunities: number
  generated_recently_count: number
  latest_opportunity_at: string | null
}

export interface RecommendationReadiness {
  vm_rightsizing_ready: boolean
  aks_rightsizing_ready: boolean
  autoscaler_ready: boolean
  blockers: string[]
  warnings: string[]
}

export interface ExportReadiness {
  csv_export_expected_rows: number
  csv_export_ready: boolean
}

export interface DataFreshness {
  cost_data_stale: boolean
  usage_data_stale: boolean
  latest_cost_seen_at: string | null
  latest_usage_seen_at: string | null
}

export interface FinOpsReadinessResponse {
  org_id: string
  assessed_at: string
  cost_coverage: CostCoverage
  usage_coverage: UsageCoverage
  opportunities: OpportunitiesStatus
  recommendation_readiness: RecommendationReadiness
  export_readiness: ExportReadiness
  data_freshness: DataFreshness
}

export const integrationHealthApi = {
  getReadiness: () =>
    apiClient.get<FinOpsReadinessResponse>('/admin/finops-readiness'),
}
