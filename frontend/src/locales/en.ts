export interface Translations {
  dashboard: {
    title: string
    subtitle: string
    currentMonthCost: string
    vsLastMonth: string
    potentialSavings: string
    openOpportunities: string
    activeAccounts: string
    totalConnected: string
    events7d: string
    cloudActivityEvents: string
    costTrend: string
    noCostData: string
    topServices: string
    noServiceData: string
    connectedAccounts: string
    colAccount: string
    colProvider: string
    colStatus: string
    colLastSync: string
    never: string
  }
  budget: {
    title: string
    notConfigured: string
    consumed: string
    projectedEom: string
    of: string
    configure: string
    save: string
    cancel: string
    period_monthly: string
    period_quarterly: string
    period_annual: string
    amount: string
    period: string
    thresholds: string
  }
  header: {
    logout: string
  }
}

export const en: Translations = {
  dashboard: {
    title: 'Dashboard',
    subtitle: 'Cloud cost overview — last 30 days',
    currentMonthCost: 'Current Month Cost',
    vsLastMonth: 'vs last month',
    potentialSavings: 'Potential Savings',
    openOpportunities: '{{count}} open opportunities',
    activeAccounts: 'Active Accounts',
    totalConnected: '{{count}} total connected',
    events7d: 'Events (7d)',
    cloudActivityEvents: 'Cloud activity events',
    costTrend: 'Cost Trend — 30 Days',
    noCostData: 'No cost data yet. Sync an account to populate.',
    topServices: 'Top Services',
    noServiceData: 'No service data yet.',
    connectedAccounts: 'Connected Accounts',
    colAccount: 'Account',
    colProvider: 'Provider',
    colStatus: 'Status',
    colLastSync: 'Last Sync',
    never: 'Never',
  },
  budget: {
    title: 'Workspace Budget',
    notConfigured: 'No budget configured for this workspace.',
    consumed: 'Consumed',
    projectedEom: 'Projected EOM',
    of: 'of',
    configure: 'Configure',
    save: 'Save',
    cancel: 'Cancel',
    period_monthly: 'Monthly',
    period_quarterly: 'Quarterly',
    period_annual: 'Annual',
    amount: 'Budget Amount (USD)',
    period: 'Period',
    thresholds: 'Alert Thresholds (%)',
  },
  header: {
    logout: 'Logout',
  },
}
