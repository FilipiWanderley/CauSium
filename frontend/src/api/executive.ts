import { apiClient } from './client'
import type { ExecutiveSummary, ScorecardResponse } from '../types'

export const executiveApi = {
  summary: (subscriptionId?: string) =>
    apiClient.get<ExecutiveSummary>('/executive/summary', {
      params: subscriptionId ? { subscription_id: subscriptionId } : undefined,
    }),
  scorecard: () => apiClient.get<ScorecardResponse>('/executive/scorecard'),
}
