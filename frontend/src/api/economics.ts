import { apiClient } from './client'
import type { WorkspaceBudget, WorkspaceBudgetUpsert } from '../types'

export const economicsApi = {
  /**
   * Fetch the workspace budget enriched with live consumption metrics.
   * Returns 404 when no budget has been configured yet.
   */
  getBudget() {
    return apiClient.get<WorkspaceBudget>('/economics/budget')
  },

  /**
   * Create or update the workspace budget configuration.
   * Requires admin / finops role.
   */
  upsertBudget(payload: WorkspaceBudgetUpsert) {
    return apiClient.put<WorkspaceBudget>('/economics/budget', payload)
  },
}
