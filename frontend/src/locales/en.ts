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
  header: {
    logout: 'Logout',
  },
}
