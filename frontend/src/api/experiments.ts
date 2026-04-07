import { apiClient } from './client'
import type { Experiment, ExperimentRun, ExperimentSummary, ExperimentStatus } from '../types'

export const experimentsApi = {
  list: (params?: { status?: ExperimentStatus; limit?: number; offset?: number }) =>
    apiClient.get<Experiment[]>('/experiments', { params }),

  summary: () => apiClient.get<ExperimentSummary>('/experiments/summary'),

  get: (id: string) => apiClient.get<Experiment>(`/experiments/${id}`),

  create: (data: {
    title: string
    hypothesis?: string
    description?: string
    opportunity_id?: string
  }) => apiClient.post<Experiment>('/experiments', data),

  update: (id: string, data: Partial<Experiment>) =>
    apiClient.patch<Experiment>(`/experiments/${id}`, data),

  transition: (id: string, to_status: ExperimentStatus) =>
    apiClient.post<Experiment>(`/experiments/${id}/transition`, { to_status }),

  listRuns: (experimentId: string) =>
    apiClient.get<ExperimentRun[]>(`/experiments/${experimentId}/runs`),

  createRun: (experimentId: string, data: { run_type: string }) =>
    apiClient.post<ExperimentRun>(`/experiments/${experimentId}/runs`, data),
}
