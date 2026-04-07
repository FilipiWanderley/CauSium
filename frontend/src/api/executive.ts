import { apiClient } from './client'
import type { ExecutiveSummary, ScorecardResponse } from '../types'

export const executiveApi = {
  summary: () => apiClient.get<ExecutiveSummary>('/executive/summary'),
  scorecard: () => apiClient.get<ScorecardResponse>('/executive/scorecard'),
}
