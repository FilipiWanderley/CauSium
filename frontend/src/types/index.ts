// Auth
export type UserRole = 'platform_admin' | 'admin' | 'engineer' | 'finops' | 'executive' | 'viewer'

export interface User {
  id: string
  org_id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  passkey_enabled: boolean
  must_change_password: boolean
  created_at: string
  org_name: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

// Cloud Accounts
export type CloudProvider = 'azure' | 'aws' | 'gcp'
export type ConnectorStatus = 'active' | 'inactive' | 'error' | 'pending'

export interface CloudAccount {
  id: string
  org_id: string
  provider: CloudProvider
  external_id: string
  display_name: string
  tenant_id: string | null
  status: ConnectorStatus
  last_sync_at: string | null
  created_at: string
}

export interface ConnectorHealth {
  id: number
  account_id: string
  checked_at: string
  status: ConnectorStatus
  latency_ms: number | null
  message: string | null
}

export interface ConnectorSyncStatus {
  account_id: string
  provider: CloudProvider
  display_name: string
  connector_status: ConnectorStatus
  last_sync_at: string | null
  last_health_check_at: string | null
  open_dlq_count: number
  needs_attention: boolean
}

export interface ScopeValidation {
  account_id: string
  provider: CloudProvider
  ok: boolean
  message: string
  validated_scopes: string[]
  scopes_validated_at: string | null
}

// Cloud Ledger
export interface CostTrend {
  date: string
  cost_usd: number
  provider?: string
}

export interface ServiceBreakdown {
  service: string
  cost_usd: number
  percentage: number
}

export interface SubscriptionCostBreakdown {
  subscription_id: string
  subscription_name?: string | null
  total_cost_usd: number
  row_count: number
  max_date: string
  percentage_of_total: number
}

export interface SubscriptionCostSummary {
  days: number
  total_cost_usd: number
  subscription_count: number
  items: SubscriptionCostBreakdown[]
}

export interface DashboardMetrics {
  current_month_cost: number
  previous_month_cost: number
  mom_change_pct: number
  daily_trend: CostTrend[]
  top_services: ServiceBreakdown[]
  top_teams: ServiceBreakdown[]
  event_count_7d: number
  active_accounts: number
  currency?: string
  data_min_date?: string | null
  data_max_date?: string | null
  subscriptions_included?: number
  cost_basis?: string
  billing_currency?: string
}

export interface ReconciliationSubscriptionRow {
  subscription_id: string
  account_id: string | null
  display_name: string | null
  provider: string | null
  total_cost: number
  records_count: number
  min_date: string | null
  max_date: string | null
  currency: string | null
  external_id_match: boolean
}

export interface ReconciliationWarnings {
  no_data: boolean
  mixed_currency: boolean
  partial_range: boolean
  missing_subscription_id: boolean
  account_mismatch: boolean
  orphan_records: number
}

export type ReconciliationStatus = 'healthy' | 'delayed' | 'partial' | 'warning'

export interface IntegrityMetadata {
  ingestion_gap_days: number
  sync_age_minutes: number | null
  reconciliation_status: ReconciliationStatus
  last_sync_at: string | null
  data_through_date: string | null
  billing_period: string
  subscriptions_active: number
  // FINOPS-4.1: export capability detection
  detected_cost_type: 'actual' | 'amortized' | 'mixed' | 'unknown'
  export_format_hint: 'legacy' | 'modern' | 'focus' | 'unknown'
  reservation_metadata_available: boolean
  pricing_model_available: boolean
  charge_type_available: boolean
  benefit_metadata_available: boolean
  cost_basis_explanation: string
  portal_comparison_hint: string
}

export interface ReconciliationReport {
  org_id: string
  account_id: string | null
  subscription_id: string | null
  provider: string | null
  start_date: string
  end_date: string
  total_cost: number
  dashboard_equivalent_total: number
  difference: number
  difference_pct: number
  records_count: number
  min_date: string | null
  max_date: string | null
  distinct_services: number
  distinct_resources: number
  subscription_count: number
  currencies: string[]
  dominant_currency: string
  mixed_currency: boolean
  by_subscription: ReconciliationSubscriptionRow[]
  warnings: ReconciliationWarnings
  note: string
}

export interface ReservationCoverageByService {
  service: string
  compute_cost_usd: number
  reserved_cost_usd: number
  uncovered_cost_usd: number
  coverage_pct: number
}

export interface ReservationCoverageSummary {
  period_start: string
  period_end: string
  total_compute_cost_usd: number
  total_reserved_cost_usd: number
  uncovered_compute_cost_usd: number
  coverage_pct: number
  has_active_reservations: boolean
  services: ReservationCoverageByService[]
  recommendation: string
}

export type ReservationEfficiencyAction =
  | 'keep'
  | 'resize_resource'
  | 'schedule_stop'
  | 'exchange_reservation'
  | 'do_not_renew'

export interface ReservationEfficiencyByFamily {
  family: string
  reserved_capacity_units: number
  effective_used_units: number
  idle_reserved_units: number
  utilization_pct: number
  waste_cost_usd: number
  payg_equivalent_cost_usd: number
  exchange_candidate: boolean
  recommended_action: ReservationEfficiencyAction
  reason: string
  confidence: number
  action_priority: number
  exchange_eligible: boolean
  renewal_window_days: number | null
  advisory_signals: string[]
}

export interface ReservationEfficiencySummary {
  period_start: string
  period_end: string
  total_families: number
  total_reserved_capacity_units: number
  total_effective_used_units: number
  total_idle_reserved_units: number
  avg_utilization_pct: number
  total_waste_cost_usd: number
  total_payg_equivalent_cost_usd: number
  families: ReservationEfficiencyByFamily[]
  recommendation: string
}

export interface DetailedCostRow {
  date: string
  account_id: string
  provider: string
  subscription_id: string | null
  service: string | null
  resource_id: string | null
  resource_name: string | null
  region: string | null
  environment: string | null
  owner_team: string | null
  cost_usd: number
  usage_quantity: number | null
  usage_unit: string | null
  currency: string | null
}

export interface PageResponse<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  has_next: boolean
}

// Opportunities
export type OpportunityCategory =
  | 'rightsizing'
  | 'aks_nodepool_rightsizing'
  | 'aks_autoscaler_recommendation'
  | 'idle_resources'
  | 'reserved_instances'
  | 'storage_optimization'
  | 'network_optimization'
  | 'license_optimization'
  | 'architecture_change'

export type RiskLevel = 'low' | 'medium' | 'high'
export type EffortLevel = 'low' | 'medium' | 'high'
export type OpportunityStatus = 'open' | 'in_progress' | 'resolved' | 'dismissed' | 'validated'

export type SavingsMethodology =
  | 'deterministic_sku_ratio'
  | 'deterministic_node_reduction'
  | 'deterministic_autoscaler'
  | 'heuristic_category_rate'

export type ConfidenceTier = 'high' | 'medium' | 'low' | 'insufficient'

export interface SavingsEvidence {
  current_monthly_cost_estimate: number
  projected_monthly_cost_estimate: number | null
  estimated_monthly_savings: number
  estimated_annual_savings: number
  savings_confidence: number
  confidence_tier: ConfidenceTier
  calculation_basis: string
  evidence_summary: string
  evidence_window_days: number | null
  risk_level: RiskLevel
  safety_margin_applied: boolean
  methodology: SavingsMethodology
  limitations: string[]
}

export interface Opportunity {
  id: string
  org_id: string
  account_id: string | null
  title: string
  description: string
  category: OpportunityCategory
  composite_score: number
  financial_impact_score: number
  risk_score: number
  effort_score: number
  criticality_score: number
  estimated_monthly_savings_usd: number
  estimated_annual_savings_usd: number
  current_monthly_cost_usd: number
  risk_level: RiskLevel
  effort_level: EffortLevel
  status: OpportunityStatus
  resource_id: string | null
  resource_name: string | null
  sku_name: string | null
  machine_family: string | null
  service: string | null
  region: string | null
  environment: string | null
  owner_team: string | null
  score_rationale: string | null
  playbook: string | null
  decision_evidence: OpportunityDecisionEvidence | null
  savings_evidence: SavingsEvidence | null
  created_at: string
}

export interface OpportunityDecisionEvidence {
  resource_type?: string | null
  cluster_name?: string | null
  node_pool?: string | null
  current_node_count?: number | null
  recommended_node_count?: number | null
  node_sku?: string | null
  cpu_p95?: number | null
  memory_p95?: number | null
  window_days?: number | null
  history_days?: number | null
  allocated_cpu?: number | null
  allocated_memory?: number | null
  requested_cpu?: number | null
  requested_memory?: number | null
  is_system_pool?: boolean | null
  autoscaler_enabled?: boolean | null
  autoscaler_min_count?: number | null
  autoscaler_max_count?: number | null
  autoscaler_action?: string | null
  recommended_min_count?: number | null
  recommended_max_count?: number | null
  has_kube_system_workloads?: boolean | null
  has_critical_workloads?: boolean | null
  variability_score?: number | null
  blocked_by?: string[] | null
  requested_pressure?: boolean | null
  cpu_p95_stddev?: number | null
  memory_p95_stddev?: number | null
  current_sku?: string | null
  recommended_sku?: string | null
  current_monthly_cost?: number | null
  estimated_monthly_cost?: number | null
  estimated_savings?: number | null
  estimated_savings_pct?: number | null
  confidence?: number | null
  risk_level?: RiskLevel | null
  reason?: string | null
}

export interface OpportunityExplainResponse {
  summary: string
  why_now: string
  expected_impact: string
  risks: string[]
  recommended_steps: string[]
  confidence: number
  model: string | null
  debug: Record<string, unknown> | null
}

export interface OpportunitySummary {
  total: number
  open: number
  in_progress: number
  resolved: number
  total_potential_savings_usd: number
  top_category: string | null
}

export interface OptimizationPlanRecommendation {
  opportunity_id: string
  category: OpportunityCategory
  title: string
  resource_id: string | null
  resource_name: string | null
  service: string | null
  environment: string | null
  owner_team: string | null
  estimated_monthly_savings_usd: number
  confidence: number
  risk_level: RiskLevel
  effort_level: EffortLevel
  priority_score: number
  rank: number
  why_now: string
  next_step: string
  conflict_hints: string[]
  conflicting_with_opportunity_ids: string[]
}

export interface OptimizationPlanGroup {
  key: string
  label: string
  total_items: number
  total_estimated_monthly_savings_usd: number
  opportunity_ids: string[]
}

export interface OptimizationPlan {
  total_recommendations: number
  total_savings_monthly_raw_usd: number
  total_savings_monthly_adjusted_usd: number
  total_savings_annual_adjusted_usd: number
  confidence_global: number
  summary: string
  summary_source: 'deterministic' | 'ai'
  ai_summary: string | null
  ai_model: string | null
  quick_wins: OptimizationPlanRecommendation[]
  prioritized: OptimizationPlanRecommendation[]
  groups: OptimizationPlanGroup[]
  conflict_hints: string[]
}

export type ExecutionPlanStatus =
  | 'review_required'
  | 'blocked'
  | 'approved'
  | 'rejected'
  | 'scheduled'
  | 'in_execution'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface ExecutionPlanListItem {
  execution_plan_id: string
  status: ExecutionPlanStatus
  risk_level: RiskLevel
  total_savings_monthly: number
  gates_triggered: string[]
  selected_opportunity_ids: string[]
  pulselab_experiment_id?: string | null
  experiment_status?: 'running' | 'completed' | 'failed' | null
  execution_outcome?: 'success' | 'partial' | 'failed' | null
  actual_savings?: number | null
  created_at: string
}

export interface ExecutionPlan {
  execution_plan_id: string
  status: ExecutionPlanStatus
  mode: 'manual_review' | 'pulselab_handoff'
  total_savings_monthly: number
  risk_level: RiskLevel
  conflicts: string[]
  checklist: string[]
  steps: string[]
  gates_triggered: string[]
  selected_opportunity_ids: string[]
  scheduled_for?: string | null
  maintenance_window?: string | null
  pulselab_experiment_id?: string | null
  handoff_checklist?: string[]
  experiment_status?: 'running' | 'completed' | 'failed' | null
  experiment_result?: Record<string, unknown> | null
  actual_savings?: number | null
  execution_outcome?: 'success' | 'partial' | 'failed' | null
}

export interface ExecutionPlanStatusUpdateIn {
  status: 'approved' | 'rejected'
  comment?: string
}

export interface ExecutionPlanScheduleIn {
  scheduled_for: string
  maintenance_window: string
  comment?: string
}

export interface ExecutionPlanHandoffIn {
  comment?: string
  target_environment?: string
  target_criticality?: string
}

export interface ExecutionPlanExecutionStatus {
  execution_plan_id: string
  experiment_id: string
  status: 'running' | 'completed' | 'failed'
  actual_savings: number
  expected_savings: number
  delta: number
  outcome: 'success' | 'partial' | 'failed'
}

// Workflow
export type InitiativeStatus = 'backlog' | 'planned' | 'in_progress' | 'review' | 'done' | 'cancelled'

export interface Initiative {
  id: string
  org_id: string
  opportunity_id: string | null
  owner_id: string | null
  title: string
  description: string | null
  status: InitiativeStatus
  sla_date: string | null
  completed_at: string | null
  external_ref: string | null
  external_url: string | null
  realized_savings_usd: number | null
  is_overdue: boolean
  created_at: string
  updated_at: string
}

export interface InitiativeBoard {
  backlog: Initiative[]
  planned: Initiative[]
  in_progress: Initiative[]
  review: Initiative[]
  done: Initiative[]
  cancelled: Initiative[]
}

export interface Comment {
  id: string
  initiative_id: string
  user_id: string
  body: string
  created_at: string
}

// Executive
export interface SavingsRecord {
  initiative_id: string
  title: string
  realized_savings_usd: number
  completed_at: string | null
}

export interface ExecutiveSummary {
  current_month_cost_usd: number
  previous_month_cost_usd: number
  mom_change_pct: number
  ytd_cost_usd: number
  total_realized_savings_usd: number
  total_potential_savings_usd: number
  savings_this_month_usd: number
  open_opportunities: number
  in_progress_initiatives: number
  completed_initiatives: number
  forecast_next_month_usd: number
  forecast_confidence: string
  top_savings: SavingsRecord[]
}

export interface TeamScorecard {
  team: string
  current_month_cost_usd: number
  previous_month_cost_usd: number
  mom_change_pct: number
  open_opportunities: number
  realized_savings_usd: number
  efficiency_score: number
}

export interface ScorecardResponse {
  teams: TeamScorecard[]
  org_efficiency_score: number
}

// Economics — SP-EC01
export type FinancialBudgetPeriod = 'monthly' | 'quarterly' | 'annual'

export interface WorkspaceBudget {
  id: string
  org_id: string
  amount_usd: number
  period: FinancialBudgetPeriod
  currency: string
  alert_thresholds: number[]
  created_at: string
  updated_at: string
  // Live consumption (computed server-side from ClickHouse)
  consumed_usd: number
  consumed_pct: number
  projected_eom_usd: number | null
}

export interface WorkspaceBudgetUpsert {
  amount_usd: number
  period: FinancialBudgetPeriod
  currency?: string
  alert_thresholds?: number[]
}

export type EconomicsReportType = 'summary'
export type ReportExportFormat = 'csv' | 'xlsx'
export type ReportExportStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface ReportExportCreate {
  report_type?: EconomicsReportType
  file_format: ReportExportFormat
  window_days?: number
  filters?: Record<string, unknown> | null
}

export interface ReportExportJob {
  id: string
  org_id: string
  requested_by_user_id: string
  report_type: EconomicsReportType
  file_format: ReportExportFormat
  status: ReportExportStatus
  window_days: number
  filters: Record<string, unknown> | null
  file_name: string | null
  content_type: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  expires_at: string | null
  download_ready: boolean
  created_at: string
  updated_at: string
}

// Risk Budgets
export type BudgetType = 'blast_radius' | 'cost_variance' | 'error_rate' | 'change_frequency'
export type BudgetPeriod = 'daily' | 'weekly' | 'monthly'

export interface RiskBudget {
  id: string
  org_id: string
  name: string
  domain: string
  environment: string
  budget_type: BudgetType
  period: BudgetPeriod
  limit_value: number
  current_value: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

// Experiments
export type ExperimentStatus =
  | 'draft'
  | 'hypothesis'
  | 'simulating'
  | 'approved'
  | 'running'
  | 'measuring'
  | 'concluded'
  | 'cancelled'

export type ExperimentOutcome = 'improved' | 'regressed' | 'inconclusive' | 'cancelled'

export interface Experiment {
  id: string
  org_id: string
  opportunity_id: string | null
  title: string
  hypothesis: string | null
  description: string | null
  status: ExperimentStatus
  outcome: ExperimentOutcome | null
  simulated_savings_usd: number | null
  simulated_confidence: number | null
  simulation_notes: string | null
  guardrails: Record<string, unknown> | null
  causal_summary: string | null
  owner_id: string | null
  approved_by_id: string | null
  risk_budget_id: string | null
  estimated_risk_score: number | null
  actual_savings_usd: number | null
  actual_confidence: number | null
  started_at: string | null
  concluded_at: string | null
  created_at: string
  updated_at: string
}

export interface ExperimentSummary {
  total: number
  by_status: Record<ExperimentStatus, number>
  total_simulated_savings_usd: number
  total_actual_savings_usd: number
}

export type RunType = 'dry_run' | 'canary' | 'full'
export type RunStatus = 'pending' | 'running' | 'completed' | 'rolled_back'

export interface ExperimentRun {
  id: string
  experiment_id: string
  org_id: string
  run_type: RunType
  status: RunStatus
  metrics_before: Record<string, unknown> | null
  metrics_after: Record<string, unknown> | null
  impact_usd: number | null
  error_rate_before: number | null
  error_rate_after: number | null
  rollback_triggered: boolean
  rollback_reason: string | null
  notes: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

// Change Events
export type ChangeEventType =
  | 'deploy'
  | 'config_change'
  | 'scaling'
  | 'incident'
  | 'cost_anomaly'
  | 'policy_change'

export interface ChangeEvent {
  id: string
  org_id: string
  account_id: string | null
  event_type: ChangeEventType
  service: string | null
  resource_id: string | null
  environment: string
  owner_team: string | null
  region: string | null
  title: string
  description: string | null
  cost_impact_usd: number | null
  causal_confidence: number | null
  external_ref: string | null
  extra_metadata: Record<string, unknown> | null
  occurred_at: string
  created_at: string
}

// PulseIntel
export interface ExplainCostChangeRequest {
  start_date: string
  end_date: string
  provider?: CloudProvider
  language?: 'pt' | 'en'
}

export interface ExplainCostCause {
  cause: string
  evidence: string[]
  estimated_impact_usd: number | null
}

export interface ExplainCostChangeResponse {
  summary: string
  causes: ExplainCostCause[]
  impact: string
  recommendation: string
  confidence: number
  model?: string | null
}

export type IntelAnomalySeverity = 'low' | 'medium' | 'high'

export interface IntelCostAnomaly {
  id: string
  provider: string
  service: string
  observed_date: string
  current_cost_usd: number
  historical_mean_usd: number
  historical_stddev_usd: number
  z_score: number
  deviation_pct: number | null
  severity: IntelAnomalySeverity
  window_days: number
  z_threshold: number
  created_at: string
}

export interface IntelInsightsResponse {
  top_saving_opportunity: string
  main_risk: string
  cost_trend_summary: string
  recommended_action: string
  confidence: number
  model?: string | null
  debug?: Record<string, unknown> | null
}
