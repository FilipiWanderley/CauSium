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

export interface DashboardMetrics {
  current_month_cost: number
  previous_month_cost: number
  mom_change_pct: number
  daily_trend: CostTrend[]
  top_services: ServiceBreakdown[]
  top_teams: ServiceBreakdown[]
  event_count_7d: number
  active_accounts: number
}

// Opportunities
export type OpportunityCategory =
  | 'rightsizing'
  | 'idle_resources'
  | 'reserved_instances'
  | 'storage_optimization'
  | 'network_optimization'
  | 'license_optimization'
  | 'architecture_change'

export type RiskLevel = 'low' | 'medium' | 'high'
export type EffortLevel = 'low' | 'medium' | 'high'
export type OpportunityStatus = 'open' | 'in_progress' | 'resolved' | 'dismissed' | 'validated'

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
  service: string | null
  region: string | null
  environment: string | null
  owner_team: string | null
  score_rationale: string | null
  playbook: string | null
  created_at: string
}

export interface OpportunitySummary {
  total: number
  open: number
  in_progress: number
  resolved: number
  total_potential_savings_usd: number
  top_category: string | null
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
