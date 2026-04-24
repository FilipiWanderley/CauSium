import { apiClient } from './client'
import type {
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
}
