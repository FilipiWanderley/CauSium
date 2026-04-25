import { apiClient } from './client'
import type {
  ExecutionPlan,
  ExecutionPlanExecutionStatus,
  ExecutionPlanHandoffIn,
  ExecutionPlanListItem,
  ExecutionPlanScheduleIn,
  ExecutionPlanStatusUpdateIn,
  ExplainCostChangeRequest,
  ExplainCostChangeResponse,
  IntelCostAnomaly,
  IntelInsightsResponse,
  OptimizationPlan,
  PageResponse,
} from '../types'

export const intelApi = {
  explainCostChange: (req: ExplainCostChangeRequest) =>
    apiClient.post<ExplainCostChangeResponse>('/intel/explain-cost', req),
  insights: (language: 'pt' | 'en' = 'en') =>
    apiClient.get<IntelInsightsResponse>('/intel/insights', { params: { language } }),
  optimizationPlan: (params?: { language?: 'pt' | 'en'; include_ai_summary?: boolean }) =>
    apiClient.get<OptimizationPlan>('/intel/optimization-plan', { params }),
  listCostAnomalies: (params?: {
    provider?: string
    severity?: 'low' | 'medium' | 'high'
    page?: number
    page_size?: number
  }) => apiClient.get<PageResponse<IntelCostAnomaly>>('/intel/cost-anomalies', { params }),
  listExecutionPlans: (params?: {
    status?: string
    risk_level?: string
    page?: number
    page_size?: number
  }) => apiClient.get<PageResponse<ExecutionPlanListItem>>('/intel/execution-plan', { params }),
  updateExecutionPlanStatus: (executionPlanId: string, payload: ExecutionPlanStatusUpdateIn) =>
    apiClient.patch<ExecutionPlan>(`/intel/execution-plan/${executionPlanId}/status`, payload),
  scheduleExecutionPlan: (executionPlanId: string, payload: ExecutionPlanScheduleIn) =>
    apiClient.patch<ExecutionPlan>(`/intel/execution-plan/${executionPlanId}/schedule`, payload),
  createExecutionPlanHandoff: (executionPlanId: string, payload: ExecutionPlanHandoffIn) =>
    apiClient.post<ExecutionPlan>(`/intel/execution-plan/${executionPlanId}/handoff`, payload),
  getExecutionPlanExecutionStatus: (executionPlanId: string) =>
    apiClient.get<ExecutionPlanExecutionStatus>(`/intel/execution-plan/${executionPlanId}/execution-status`),
}
