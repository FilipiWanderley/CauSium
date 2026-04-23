import { apiClient } from './client'
import type { ExplainCostChangeRequest, ExplainCostChangeResponse } from '../types'

export const intelApi = {
  explainCostChange: (req: ExplainCostChangeRequest) =>
    apiClient.post<ExplainCostChangeResponse>('/intel/explain-cost', req),
}

