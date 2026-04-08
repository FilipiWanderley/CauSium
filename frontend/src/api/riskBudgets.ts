import { apiClient } from './client'
import type { RiskBudget, BudgetType, BudgetPeriod } from '../types'

interface ApiPage<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export const riskBudgetsApi = {
  list: (params?: { active_only?: boolean }) =>
    apiClient.get<ApiPage<RiskBudget>>('/risk-budgets', { params }),

  get: (id: string) => apiClient.get<RiskBudget>(`/risk-budgets/${id}`),

  create: (data: {
    name: string
    domain: string
    environment: string
    budget_type: BudgetType
    period: BudgetPeriod
    limit_value: number
  }) => apiClient.post<RiskBudget>('/risk-budgets', data),

  update: (id: string, data: { name?: string; limit_value?: number; period?: BudgetPeriod; is_active?: boolean }) =>
    apiClient.patch<RiskBudget>(`/risk-budgets/${id}`, data),

  delete: (id: string) => apiClient.delete(`/risk-budgets/${id}`),
}
