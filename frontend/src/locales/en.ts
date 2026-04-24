export interface Translations {
  nav: {
    economics: string
    economicsCosts: string
    economicsUsage: string
    economicsSkus: string
    economicsReports: string
    opportunities: string
    experiments: string
    notifications: string
    gov: string
    green: string
    initiatives: string
    riskBudgets: string
    changeEvents: string
    executive: string
    members: string
    settings: string
    settingsTeam: string
    settingsCloud: string
    settingsSecurity: string
    platformWorkspaces: string
    platformSync: string
    platformSlo: string
    soon: string
  }
  common: {
    cancel: string
    save: string
    loading: string
    previous: string
    next: string
    all: string
    create: string
    delete: string
    edit: string
    close: string
    copy: string
    export: string
    download: string
    reset: string
    activate: string
    deactivate: string
    remove: string
    confirm: string
    reason: string
    name: string
    role: string
    environment: string
    daily: string
    weekly: string
    monthly: string
    quarterly: string
    annual: string
    production: string
    staging: string
    development: string
    unknown: string
    high: string
    medium: string
    low: string
  }
  dashboard: {
    title: string
    subtitle: string
    providerScope: string
    refreshData: string
    refreshingData: string
    adjustBudget: string
    queueIngestion: string
    queueingIngestion: string
    refreshSuccess: string
    ingestQueuedSuccess: string
    ingestNoAccounts: string
    actionError: string
    providerAll: string
    providerAzure: string
    providerAws: string
    providerGcp: string
    currentMonthCost: string
    vsLastMonth: string
    explainCostCta: string
    explainCostTitle: string
    explainCostLoading: string
    explainCostError: string
    explainCostSummary: string
    explainCostCauses: string
    explainCostRecommendation: string
    explainCostConfidence: string
    insightsTitle: string
    insightsSubtitle: string
    insightsTopSaving: string
    insightsMainRisk: string
    insightsTrend: string
    insightsAction: string
    insightsConfidence: string
    insightsUnavailable: string
    anomaliesTitle: string
    anomaliesSubtitle: string
    anomaliesNone: string
    anomalyCriticalOnly: string
    anomalyShowAll: string
    anomalySeverityLow: string
    anomalySeverityMedium: string
    anomalySeverityHigh: string
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
    recentChanges: string
    viewAll: string
    noChangeEvents: string
    noAccounts: string
    changeEventsOverlaid: string
    reservationsTitle: string
    reservationsViewAll: string
    reservationsPriority: string
    reservationsWaste: string
    reservationsEmpty: string
    resActionKeep: string
    resActionResize: string
    resActionScheduleStop: string
    resActionExchange: string
    resActionDoNotRenew: string
    reservationsHighBadge: string
    reservationsCriticalOnly: string
    reservationsShowAll: string
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
  opportunities: {
    title: string
    subtitle: string
    open: string
    inProgress: string
    resolved: string
    totalSavings: string
    allCategories: string
    rightsizing: string
    idleResources: string
    reservedInstances: string
    storage: string
    network: string
    noOpportunities: string
    noOpportunitiesHint: string
    detailTitle: string
    targetResource: string
    machineName: string
    machineSku: string
    machineFamily: string
    resourceGroup: string
    resourceId: string
    openInAzure: string
    unknownResource: string
    monthlySavings: string
    compositeScore: string
    scoreRationale: string
    playbook: string
    createInitiative: string
    dismiss: string
    statusAll: string
    statusOpenSuggestion: string
    statusInProgressReview: string
    statusResolvedApproved: string
    statusDismissed: string
    statusValidated: string
    currentStatus: string
    readOnlyNoticeTitle: string
    readOnlyNoticeDesc: string
    executionOwnershipHint: string
    markInReview: string
    markApproved: string
    markValidated: string
    markDismissed: string
  }
  initiatives: {
    title: string
    subtitle: string
    newInitiative: string
    createInitiative: string
    titlePlaceholder: string
    create: string
    cancel: string
    backlog: string
    planned: string
    inProgress: string
    review: string
    done: string
    empty: string
    moveTo: string
    sla: string
    overdue: string
  }
  experiments: {
    title: string
    subtitle: string
    newExperiment: string
    titleLabel: string
    hypothesis: string
    create: string
    cancel: string
    draft: string
    simulating: string
    approved: string
    running: string
    measuring: string
    concluded: string
    simSavings: string
    actualSavings: string
    noExperiments: string
    loading: string
    improved: string
    regressed: string
    inconclusive: string
    cancelled: string
  }
  riskBudgets: {
    title: string
    blastRadius: string
    blastRadiusDesc: string
    costVariance: string
    costVarianceDesc: string
    errorRate: string
    errorRateDesc: string
    changeFrequency: string
    changeFrequencyDesc: string
    noData: string
    exceeded: string
    deactivate: string
    activate: string
    delete: string
    newBudget: string
    newBudgetTitle: string
    namePlaceholder: string
    domainLabel: string
    domainPlaceholder: string
    limitPlaceholderPct: string
    limitPlaceholderNum: string
    createBudget: string
    activeOnly: string
    noBudgets: string
    noBudgetsHint: string
    createFirst: string
    nameLabel: string
    budgetType: string
    period: string
    limitUnit: string
  }
  changeEvents: {
    title: string
    subtitle: string
    logEvent: string
    logEventTitle: string
    type: string
    environment: string
    titleLabel: string
    titleDesc: string
    service: string
    servicePlaceholder: string
    costImpact: string
    costImpactPlaceholder: string
    occurredAt: string
    description: string
    descriptionPlaceholder: string
    saveEvent: string
    all: string
    colType: string
    colTitle: string
    colService: string
    colEnv: string
    colCostImpact: string
    colCausalConf: string
    colOccurred: string
    noEvents: string
    deploy: string
    configChange: string
    scaling: string
    incident: string
    costAnomaly: string
    policyChange: string
  }
  executive: {
    title: string
    subtitle: string
    currentMonthCost: string
    mom: string
    ytdSpend: string
    ytdDesc: string
    realizedSavings: string
    realizedDesc: string
    potentialSavings: string
    openOpportunities: string
    inProgress: string
    completed: string
    initiatives: string
    forecastNextMonth: string
    confidence: string
    na: string
    linearProjection: string
    teamScorecard: string
    orgScore: string
    team: string
    currentMonth: string
    openOpps: string
    efficiency: string
    topSavings: string
    completedDate: string
    perMonth: string
  }
  gov: {
    title: string
    subtitle: string
    last7: string
    last30: string
    last90: string
    billedResources: string
    unowned: string
    avgCompliance: string
    recommendations: string
    estSavings: string
    deployedResources: string
    types: string
    tabUnowned: string
    tabCompliance: string
    tabRecommendations: string
    tabInventory: string
    allOwned: string
    colService: string
    colResourceId: string
    colRegion: string
    colEnvironment: string
    colDaysActive: string
    colCost: string
    colTeam: string
    colTotalCost: string
    colUntaggedCost: string
    colCompliance: string
    errorUnowned: string
    errorCompliance: string
    noCompliance: string
    colCategory: string
    colImpact: string
    colResource: string
    colDescription: string
    colEstSavings: string
    errorRecommendations: string
    noRecommendations: string
    catCost: string
    catSecurity: string
    catPerformance: string
    catHighAvailability: string
    catOperationalExcellence: string
    impactHigh: string
    impactMedium: string
    impactLow: string
    colName: string
    colType: string
    colResourceGroup: string
    colLocation: string
    colOwner: string
    colSku: string
    colState: string
    stateSucceeded: string
    stateFailed: string
    untagged: string
    errorInventory: string
    noInventory: string
  }
  green: {
    title: string
    subtitle: string
    last3m: string
    last6m: string
    last12m: string
    totalCO2: string
    kg: string
    tCO2: string
    cloudSpend: string
    intensity: string
    momDelta: string
    monthlyTrend: string
    noEmissions: string
    colMonth: string
    colKg: string
    colTCO2: string
    colCost: string
    colMom: string
    breakdown: string
    window7: string
    window30: string
    window90: string
    byService: string
    byRegion: string
    byEnvironment: string
    byTeam: string
    noBreakdown: string
    dataOfficial: string
    dataEstimated: string
    dataMixed: string
  }
  economicsCosts: {
    title: string
    subtitle: string
    timeWindow: string
    last30: string
    last60: string
    last90: string
    last180: string
    serviceFilter: string
    serviceFilterPlaceholder: string
    providerFilter: string
    providerFilterPlaceholder: string
    teamFilter: string
    teamFilterPlaceholder: string
    visibleCost: string
    exportReport: string
    format: string
    csv: string
    excel: string
    requesting: string
    generating: string
    buildingFormat: string
    downloadFile: string
    reset: string
    detailedCosts: string
    detailedCostsDesc: string
    totalRows: string
    loadingRows: string
    noRows: string
    pageOf: string
    previous: string
    next: string
    costByService: string
    loadingServices: string
    noServiceData: string
    costByTeam: string
    loadingTeams: string
    noTeamData: string
    colDate: string
    colProvider: string
    colService: string
    colResource: string
    colTeam: string
    colEnvironment: string
    colRegion: string
    colCost: string
    reservationEfficiency: string
    familiesCount: string
    loadingReservationEfficiency: string
    noReservationEfficiency: string
    avgUtilization: string
    totalWaste: string
    totalReserved: string
    colFamily: string
    colPriority: string
    colUtilization: string
    colAction: string
    colWaste: string
    colRenewal: string
    colAdvisor: string
    noRenewalWindow: string
    noAdvisorSignals: string
    actionKeep: string
    actionResize: string
    actionScheduleStop: string
    actionExchange: string
    actionDoNotRenew: string
    reservationHighBadge: string
    reservationCriticalOnly: string
    reservationShowAll: string
  }
  economicsUsage: {
    title: string
    subtitle: string
    timeWindow: string
    last30: string
    last60: string
    last90: string
    last180: string
    dailyAvg: string
    dailyAvgDesc: string
    peakDay: string
    peakDayDesc: string
    volatility: string
    volatilityDesc: string
    efficiencyScore: string
    efficiencyScoreDesc: string
    timeline: string
    loadingTimeline: string
    noData: string
    colDate: string
    colValue: string
  }
  economicsSkus: {
    title: string
    subtitle: string
    note: string
    window: string
    last30: string
    last60: string
    last90: string
    last180: string
    topRows: string
    top10: string
    top20: string
    top30: string
    top50: string
    totalCost: string
    top3Share: string
    breakdown: string
    loading: string
    noData: string
    colRank: string
    colSku: string
    colCost: string
    colShare: string
  }
  economicsReports: {
    title: string
    subtitle: string
    reportWindow: string
    last30: string
    last60: string
    last90: string
    processing: string
    exportCsv: string
    exportExcel: string
    currentMonth: string
    previousMonth: string
    momChange: string
    topServices: string
    topTeams: string
    loading: string
    noData: string
    errorEnqueue: string
    asyncNote: string
    queued: string
    running: string
    completed: string
    completedDownload: string
  }
  notifications: {
    title: string
    subtitle: string
    markAllRead: string
    unread: string
    critical: string
    totalVisible: string
    allCategories: string
    financial: string
    optimization: string
    governance: string
    activity: string
    security: string
    allTypes: string
    typeActivity: string
    typeCreated: string
    typeUpdated: string
    typeDeleted: string
    typeSync: string
    typeSecurity: string
    immediateActionTitle: string
    immediateActionDesc: string
    focusCritical: string
    soundOn: string
    soundOff: string
    soundEnable: string
    soundDisable: string
    allStatuses: string
    statusUnread: string
    statusRead: string
    statusArchived: string
    error: string
    noNotifications: string
    emptyHint: string
    viewDetails: string
    markRead: string
    archive: string
  }
  settings: {
    passkeys: string
    registeredAt: string
    revoke: string
    noPasskeys: string
    registerPasskey: string
    registering: string
    passkeySuccess: string
    passkeyError: string
    sessions: string
    logoutAll: string
    loggingOut: string
    logoutSuccess: string
    logoutError: string
  }
  members: {
    title: string
    subtitle: string
    tabMembers: string
    tabInvites: string
    createMember: string
    emailPlaceholder: string
    fullNamePlaceholder: string
    tempPasswordPlaceholder: string
    creating: string
    workspaceMembers: string
    prev: string
    pageOf: string
    next: string
    loadingMembers: string
    noMembers: string
    resetMfa: string
    resettingMfa: string
    resetPassword: string
    resettingPassword: string
    deactivate: string
    deactivating: string
    edit: string
    saving: string
    remove: string
    removing: string
    createInvite: string
    days3: string
    days7: string
    days14: string
    days30: string
    searchInvite: string
    statusPending: string
    statusAccepted: string
    statusExpired: string
    statusRevoked: string
    copyLink: string
    revoke: string
    revoking: string
    noInvites: string
    tempPasswordTitle: string
    tempPasswordUser: string
    tempPasswordNote: string
    copy: string
    close: string
    deactivateTitle: string
    deactivateDesc: string
    reason: string
    cancel: string
    confirmDeactivate: string
    editMember: string
    fullName: string
    role: string
    save: string
    removeTitle: string
    removeDesc: string
    confirmRemove: string
    toastCreated: string
    toastCreateError: string
    toastPasswordReset: string
    toastPasswordError: string
    toastMfaReset: string
    toastMfaError: string
    toastDeactivated: string
    toastDeactivateError: string
    toastUpdated: string
    toastUpdateError: string
    toastRemoved: string
    toastRemoveError: string
    toastInviteCreated: string
    toastInviteError: string
    toastInviteRevoked: string
    toastInviteRevokeError: string
  }
  login: {
    back: string
    oidcFailed: string
    invalidCredentials: string
    serverError: string
    networkError: string
    passkeyFailed: string
    welcomeBack: string
    subtitle: string
    badgeMultiCloud: string
    badgeRiskAware: string
    badgeEnterprise: string
    signInContinue: string
    emailLabel: string
    emailPlaceholder: string
    passwordLabel: string
    forgotPassword: string
    passwordPlaceholder: string
    showPassword: string
    hidePassword: string
    signIn: string
    signingIn: string
    orContinueWith: string
    enterEmailFirst: string
    passkeySignIn: string
    passkeyValidating: string
    microsoftSignIn: string
    microsoftRedirecting: string
    noAccount: string
    contactAdmin: string
  }
  platform: {
    syncTitle: string
    syncSubtitle: string
    syncAccounts: string
    syncNeedsAttention: string
    syncHealthy: string
    syncOpenDlq: string
    syncConnectorOps: string
    syncAllProviders: string
    syncAllStatus: string
    syncStatusActive: string
    syncStatusPending: string
    syncStatusInactive: string
    syncStatusError: string
    syncAllAttention: string
    syncNeedsAttentionFilter: string
    syncHealthyOnly: string
    syncSortAttentionFirst: string
    syncSortDlqDesc: string
    syncSortLatestSync: string
    syncSortNameAsc: string
    syncPerPage: string
    syncColAccount: string
    syncColProvider: string
    syncColStatus: string
    syncColLastSync: string
    syncColLastHealth: string
    syncColOpenDlq: string
    syncColAttention: string
    syncColAction: string
    syncAttentionYes: string
    syncAttentionOk: string
    syncQueueing: string
    syncTrigger: string
    syncShowing: string
    syncPage: string
    workspacesTitle: string
    workspacesSubtitle: string
    workspacesAllOrgs: string
    workspacesSearch: string
    workspacesAllStates: string
    workspacesStateActive: string
    workspacesStateSuspended: string
    workspacesStateArchived: string
    workspacesLoading: string
    workspacesNoOrgs: string
    workspacesColOrg: string
    workspacesColPlan: string
    workspacesColMembers: string
    workspacesColState: string
    workspacesColCreated: string
    workspacesColActions: string
    workspacesLoadingUsers: string
    workspacesNoUsers: string
    workspacesUsers: string
    workspacesAuditWindow: string
    workspacesLast24h: string
    workspacesLast7d: string
    workspacesLast30d: string
    workspacesAllTime: string
    workspacesPwdResetBadge: string
    workspacesMfaResetBadge: string
    workspacesDeactivatedBadge: string
    workspacesInactive: string
    workspacesResetMfa: string
    workspacesResetting: string
    workspacesResetPassword: string
    workspacesDeactivateUser: string
    workspacesDeactivating: string
    workspacesSuspendTitle: string
    workspacesRestoreTitle: string
    workspacesArchiveTitle: string
    workspacesArchiveWarning: string
    workspacesReasonRequired: string
    workspacesReasonOptional: string
    workspacesReasonPlaceholder: string
    workspacesRestorePlaceholder: string
    workspacesActionFailed: string
    workspacesProcessing: string
    workspacesSuspend: string
    workspacesRestore: string
    workspacesArchive: string
    workspacesTempPwdTitle: string
    workspacesTempPwdNote: string
    workspacesConfirmResetMfa: string
    workspacesConfirmResetPassword: string
    workspacesConfirmDeactivate: string
    workspacesDeactivatePrompt: string
    workspacesDeactivateDefault: string
    workspacesViewUsers: string
    workspacesSuspendHint: string
    workspacesRestoreHint: string
    workspacesArchiveHint: string
    sloTitle: string
    sloSubtitle: string
    sloLoading: string
    sloRequests: string
    sloErrorRate: string
    sloTarget: string
    sloBurnRate: string
    sloBurnDesc: string
    sloAlerts: string
    sloCriticalWarning: string
    sloApiPathsTitle: string
    sloColPath: string
    sloColReq: string
    sloColErrorPct: string
    sloColP95: string
    sloColAvg: string
    sloColMax: string
    sloWorkerTitle: string
    sloColWorker: string
    sloColTotal: string
    sloColSuccess: string
    sloColRetry: string
    sloColFailed: string
    sloAlertsTitle: string
    sloNoAlerts: string
    sloAlertAction: string
    syncSuccessMsg: string
    syncErrorMsg: string
    syncNoAccounts: string
    refresh: string
    readOnlyBannerTitle: string
    readOnlyBannerBody: string
  }
}

export const en: Translations = {
  nav: {
    economics: 'Economics',
    economicsCosts: 'Costs',
    economicsUsage: 'Usage',
    economicsSkus: 'SKUs',
    economicsReports: 'Reports',
    opportunities: 'PulseIntel',
    experiments: 'PulseLab',
    notifications: 'Notifications',
    gov: 'PulseGov',
    green: 'PulseGreen',
    initiatives: 'Initiatives',
    riskBudgets: 'Risk Budgets',
    changeEvents: 'Change Events',
    executive: 'Executive',
    members: 'Members',
    settings: 'Settings',
    settingsTeam: 'Team',
    settingsCloud: 'Cloud',
    settingsSecurity: 'Security',
    platformWorkspaces: 'Workspaces',
    platformSync: 'Sync',
    platformSlo: 'SLO',
    soon: 'Soon',
  },
  common: {
    cancel: 'Cancel',
    save: 'Save',
    loading: 'Loading...',
    previous: 'Previous',
    next: 'Next',
    all: 'All',
    create: 'Create',
    delete: 'Delete',
    edit: 'Edit',
    close: 'Close',
    copy: 'Copy',
    export: 'Export',
    download: 'Download',
    reset: 'Reset',
    activate: 'Activate',
    deactivate: 'Deactivate',
    remove: 'Remove',
    confirm: 'Confirm',
    reason: 'Reason',
    name: 'Name',
    role: 'Role',
    environment: 'Environment',
    daily: 'Daily',
    weekly: 'Weekly',
    monthly: 'Monthly',
    quarterly: 'Quarterly',
    annual: 'Annual',
    production: 'Production',
    staging: 'Staging',
    development: 'Development',
    unknown: 'Unknown',
    high: 'High',
    medium: 'Medium',
    low: 'Low',
  },
  dashboard: {
    title: 'Dashboard',
    subtitle: 'Cloud spending overview and optimization scorecard',
    providerScope: 'Provider scope',
    refreshData: 'Refresh data',
    refreshingData: 'Refreshing...',
    adjustBudget: 'Adjust budget',
    queueIngestion: 'Queue ingestion',
    queueingIngestion: 'Queueing...',
    refreshSuccess: 'Dashboard data refreshed.',
    ingestQueuedSuccess: 'Ingestion queued for {{count}} account(s).',
    ingestNoAccounts: 'No active account available for ingestion.',
    actionError: 'Action failed. Please try again.',
    providerAll: 'All providers',
    providerAzure: 'Azure',
    providerAws: 'AWS',
    providerGcp: 'GCP',
    currentMonthCost: 'Current Month Cost',
    vsLastMonth: 'vs last month',
    explainCostCta: 'Explain change',
    explainCostTitle: 'Explain Cost Change',
    explainCostLoading: 'Analyzing cost drivers…',
    explainCostError: 'Could not generate an explanation right now.',
    explainCostSummary: 'Summary',
    explainCostCauses: 'Top causes',
    explainCostRecommendation: 'Recommendation',
    explainCostConfidence: 'Confidence',
    insightsTitle: 'AI Insights Engine',
    insightsSubtitle: 'Prioritized recommendations from cost, opportunities, and anomaly signals',
    insightsTopSaving: 'Top saving opportunity',
    insightsMainRisk: 'Main risk',
    insightsTrend: 'Cost trend',
    insightsAction: 'Recommended action',
    insightsConfidence: 'Insight confidence',
    insightsUnavailable: 'No insights available right now.',
    anomaliesTitle: 'Cost Anomalies',
    anomaliesSubtitle: 'Outliers detected against recent baseline',
    anomaliesNone: 'No anomalies detected in the recent window.',
    anomalyCriticalOnly: 'High only',
    anomalyShowAll: 'Show all',
    anomalySeverityLow: 'Low',
    anomalySeverityMedium: 'Medium',
    anomalySeverityHigh: 'High',
    potentialSavings: 'Potential Savings',
    openOpportunities: '{{count}} open opportunities',
    activeAccounts: 'Active Accounts',
    totalConnected: '{{count}} total connected',
    events7d: 'Events (7d)',
    cloudActivityEvents: 'Cloud activity & change events',
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
    recentChanges: 'Recent Changes',
    viewAll: 'View all →',
    noChangeEvents: 'No change events logged yet.',
    noAccounts: 'No accounts connected yet.',
    changeEventsOverlaid: '{{count}} change event{{s}} overlaid',
    reservationsTitle: 'Reservation Priorities',
    reservationsViewAll: 'Open costs →',
    reservationsPriority: 'Priority P{{priority}}',
    reservationsWaste: 'Waste {{waste}}',
    reservationsEmpty: 'No reservation action items for now.',
    resActionKeep: 'Keep',
    resActionResize: 'Resize',
    resActionScheduleStop: 'Schedule stop',
    resActionExchange: 'Exchange',
    resActionDoNotRenew: 'Do not renew',
    reservationsHighBadge: '{{count}} high',
    reservationsCriticalOnly: 'Critical only',
    reservationsShowAll: 'Show all',
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
  opportunities: {
    title: 'Opportunities',
    subtitle: 'Prioritized by composite score — financial impact × risk × effort',
    open: 'Open',
    inProgress: 'In Progress',
    resolved: 'Resolved',
    totalSavings: 'Total Potential Savings',
    allCategories: 'All categories',
    rightsizing: 'Rightsizing',
    idleResources: 'Idle Resources',
    reservedInstances: 'Reserved Instances',
    storage: 'Storage',
    network: 'Network',
    noOpportunities: 'No opportunities found.',
    noOpportunitiesHint: 'Sync a cloud account and generate opportunities to see results here.',
    detailTitle: 'Opportunity Detail',
    targetResource: 'Target Resource',
    machineName: 'Machine',
    machineSku: 'SKU',
    machineFamily: 'Family',
    resourceGroup: 'Resource Group',
    resourceId: 'Resource ID',
    openInAzure: 'Open in Azure Portal',
    unknownResource: 'Unknown',
    monthlySavings: 'Monthly Savings',
    compositeScore: 'Composite Score',
    scoreRationale: 'Score Rationale',
    playbook: 'Playbook',
    createInitiative: 'Create Initiative',
    dismiss: 'Dismiss',
    statusAll: 'All status',
    statusOpenSuggestion: 'AI suggestion',
    statusInProgressReview: 'Under client review',
    statusResolvedApproved: 'Approved and executed by client',
    statusDismissed: 'Dismissed by client',
    statusValidated: 'Validated by client',
    currentStatus: 'Current status',
    readOnlyNoticeTitle: 'Read-only analysis mode',
    readOnlyNoticeDesc: 'The platform only reads tenant data and generates recommendations. Execution always happens after explicit client decision.',
    executionOwnershipHint: 'Execution is external to the platform and owned by the client team.',
    markInReview: 'Mark as under review',
    markApproved: 'Mark as approved/executed',
    markValidated: 'Mark as validated',
    markDismissed: 'Mark as dismissed',
  },
  initiatives: {
    title: 'Initiatives',
    subtitle: 'Execution board — track optimization initiatives',
    newInitiative: 'New Initiative',
    createInitiative: 'Create Initiative',
    titlePlaceholder: 'Initiative title...',
    create: 'Create',
    cancel: 'Cancel',
    backlog: 'Backlog',
    planned: 'Planned',
    inProgress: 'In Progress',
    review: 'Review',
    done: 'Done',
    empty: 'Empty',
    moveTo: 'Move to {{status}} →',
    sla: 'SLA: {{date}}',
    overdue: 'OVERDUE',
  },
  experiments: {
    title: 'Experiments',
    subtitle: 'Optimization experiments pipeline',
    newExperiment: 'New Experiment',
    titleLabel: 'Experiment title *',
    hypothesis: 'Hypothesis (optional)',
    create: 'Create',
    cancel: 'Cancel',
    draft: 'Draft',
    simulating: 'Simulating',
    approved: 'Approved',
    running: 'Running',
    measuring: 'Measuring',
    concluded: 'Concluded',
    simSavings: 'Sim. savings:',
    actualSavings: 'Actual savings:',
    noExperiments: 'No experiments',
    loading: 'Loading…',
    improved: 'improved',
    regressed: 'regressed',
    inconclusive: 'inconclusive',
    cancelled: 'cancelled',
  },
  riskBudgets: {
    title: 'Risk Budgets',
    blastRadius: 'Blast Radius',
    blastRadiusDesc: '% max of services affected by a change',
    costVariance: 'Cost Variance',
    costVarianceDesc: 'Max allowed cost increase per period',
    errorRate: 'Error Rate',
    errorRateDesc: 'Max allowed error rate after a deploy',
    changeFrequency: 'Change Frequency',
    changeFrequencyDesc: 'Max number of changes per period',
    noData: 'No data yet',
    exceeded: 'Budget exceeded',
    deactivate: 'Deactivate',
    activate: 'Activate',
    delete: 'Delete',
    newBudget: 'New Budget',
    newBudgetTitle: 'New Risk Budget',
    namePlaceholder: 'e.g. Payments squad cost variance',
    domainLabel: 'Domain / Team *',
    domainPlaceholder: 'e.g. payments, api-gateway',
    limitPlaceholderPct: 'e.g. 10',
    limitPlaceholderNum: 'e.g. 20',
    createBudget: 'Create Budget',
    activeOnly: 'Active only',
    noBudgets: 'No risk budgets yet.',
    noBudgetsHint: 'Create a budget to define safe thresholds for deployments, cost variance, and error rates per domain and environment.',
    createFirst: 'Create first budget',
    nameLabel: 'Name *',
    budgetType: 'Budget Type',
    period: 'Period',
    limitUnit: 'Limit ({{unit}}) *',
  },
  changeEvents: {
    title: 'Change Events',
    subtitle: 'deploy, config, incidents, cost anomalies',
    logEvent: 'Log Event',
    logEventTitle: 'Log Change Event',
    type: 'Type *',
    environment: 'Environment',
    titleLabel: 'Title *',
    titleDesc: 'Describe what changed',
    service: 'Service',
    servicePlaceholder: 'e.g. api-gateway',
    costImpact: 'Cost Impact (USD)',
    costImpactPlaceholder: 'e.g. 1500 or -500',
    occurredAt: 'Occurred At *',
    description: 'Description',
    descriptionPlaceholder: 'Optional notes',
    saveEvent: 'Save Event',
    all: 'All',
    colType: 'Type',
    colTitle: 'Title',
    colService: 'Service',
    colEnv: 'Env',
    colCostImpact: 'Cost Impact',
    colCausalConf: 'Causal Conf.',
    colOccurred: 'Occurred',
    noEvents: 'No change events yet. Log the first one.',
    deploy: 'Deploy',
    configChange: 'Config Change',
    scaling: 'Scaling',
    incident: 'Incident',
    costAnomaly: 'Cost Anomaly',
    policyChange: 'Policy Change',
  },
  executive: {
    title: 'Executive View',
    subtitle: 'Financial performance, savings, and team efficiency',
    currentMonthCost: 'Current Month Cost',
    mom: 'MoM',
    ytdSpend: 'YTD Cloud Spend',
    ytdDesc: 'Year to date',
    realizedSavings: 'Realized Savings',
    realizedDesc: 'this month',
    potentialSavings: 'Potential Savings',
    openOpportunities: 'open opportunities',
    inProgress: 'In Progress',
    completed: 'Completed',
    initiatives: 'Initiatives',
    forecastNextMonth: 'Forecast Next Month',
    confidence: 'Confidence:',
    na: 'n/a',
    linearProjection: 'Linear projection',
    teamScorecard: 'Team Efficiency Scorecard',
    orgScore: 'Org Score: {{score}}/100',
    team: 'Team',
    currentMonth: 'Current Month',
    openOpps: 'Open Opps',
    efficiency: 'Efficiency',
    topSavings: 'Top Realized Savings',
    completedDate: 'Completed {{date}}',
    perMonth: '/mo',
  },
  gov: {
    title: 'PulseGov',
    subtitle: 'Resource governance — ownership coverage, label compliance, Advisor recommendations, and full inventory.',
    last7: 'Last 7 days',
    last30: 'Last 30 days',
    last90: 'Last 90 days',
    billedResources: 'Billed Resources',
    unowned: 'Unowned',
    avgCompliance: 'Avg Compliance',
    recommendations: 'Recommendations',
    estSavings: 'Est. Savings',
    deployedResources: 'Deployed Resources',
    types: 'types',
    tabUnowned: 'Unowned Resources',
    tabCompliance: 'Label Compliance',
    tabRecommendations: 'Recommendations',
    tabInventory: 'Inventory',
    allOwned: 'All resources have an owner assigned.',
    colService: 'Service',
    colResourceId: 'Resource ID',
    colRegion: 'Region',
    colEnvironment: 'Environment',
    colDaysActive: 'Days Active',
    colCost: 'Cost (USD)',
    colTeam: 'Team',
    colTotalCost: 'Total Cost',
    colUntaggedCost: 'Untagged Cost',
    colCompliance: 'Compliance',
    errorUnowned: 'Failed to load unowned costs data.',
    errorCompliance: 'Failed to load compliance data.',
    noCompliance: 'No compliance data available.',
    colCategory: 'Category',
    colImpact: 'Impact',
    colResource: 'Resource',
    colDescription: 'Description',
    colEstSavings: 'Est. Savings / yr',
    errorRecommendations: 'Failed to load recommendations.',
    noRecommendations: 'No recommendations found. Your Azure environment looks healthy.',
    catCost: 'Cost',
    catSecurity: 'Security',
    catPerformance: 'Performance',
    catHighAvailability: 'High Availability',
    catOperationalExcellence: 'Operational Excellence',
    impactHigh: 'High',
    impactMedium: 'Medium',
    impactLow: 'Low',
    colName: 'Name',
    colType: 'Type',
    colResourceGroup: 'Resource Group',
    colLocation: 'Location',
    colOwner: 'Owner',
    colSku: 'SKU',
    colState: 'State',
    stateSucceeded: 'Succeeded',
    stateFailed: 'Failed',
    untagged: 'untagged',
    errorInventory: 'Failed to load inventory data.',
    noInventory: 'No inventory data yet. Trigger a sync to populate.',
  },
  green: {
    title: 'PulseGreen',
    subtitle: 'Estimated carbon footprint derived from cloud spend and regional grid intensity.',
    last3m: 'Last 3 months',
    last6m: 'Last 6 months',
    last12m: 'Last 12 months',
    totalCO2: 'Total CO₂e',
    kg: 'kg',
    tCO2: 'tCO₂e',
    cloudSpend: 'Cloud Spend',
    intensity: 'Intensity (gCO₂e/$)',
    momDelta: 'MoM Delta',
    monthlyTrend: 'Monthly Emissions Trend',
    noEmissions: 'No emissions data available for this period.',
    colMonth: 'Month',
    colKg: 'kgCO₂e',
    colTCO2: 'tCO₂e',
    colCost: 'Cloud Cost',
    colMom: 'MoM',
    breakdown: 'Emissions Breakdown',
    window7: '7 days',
    window30: '30 days',
    window90: '90 days',
    byService: 'By Service',
    byRegion: 'By Region',
    byEnvironment: 'By Environment',
    byTeam: 'By Team',
    noBreakdown: 'No breakdown data available.',
    dataOfficial: 'Data source: official provider carbon API',
    dataEstimated: 'Data source: calibrated cost-based estimate',
    dataMixed: 'Data source: mixed (official + estimated)',
  },
  economicsCosts: {
    title: 'Economics Costs',
    subtitle: 'Explore detailed cost distribution by service and team using interactive filters.',
    timeWindow: 'Time window',
    last30: 'Last 30 days',
    last60: 'Last 60 days',
    last90: 'Last 90 days',
    last180: 'Last 180 days',
    serviceFilter: 'Service filter',
    serviceFilterPlaceholder: 'Filter service name',
    providerFilter: 'Provider filter',
    providerFilterPlaceholder: 'azure, aws, gcp',
    teamFilter: 'Team filter',
    teamFilterPlaceholder: 'owner team',
    visibleCost: 'Visible Cost',
    exportReport: 'Export Report',
    format: 'Format',
    csv: 'CSV',
    excel: 'Excel (.xlsx)',
    requesting: 'Requesting…',
    generating: 'Generating…',
    buildingFormat: 'Building {{format}} — please wait…',
    downloadFile: 'Download {{filename}}',
    reset: 'Reset',
    detailedCosts: 'Detailed Costs',
    detailedCostsDesc: 'Detailed rows from the ledger with combined filters and pagination.',
    totalRows: 'Total rows: {{count}}',
    loadingRows: 'Loading detailed costs...',
    noRows: 'No cost rows for current filters.',
    pageOf: 'Page {{page}} of {{total}}',
    previous: 'Previous',
    next: 'Next',
    costByService: 'Cost by Service',
    loadingServices: 'Loading services...',
    noServiceData: 'No service data for current filter.',
    costByTeam: 'Cost by Team',
    loadingTeams: 'Loading teams...',
    noTeamData: 'No team data available.',
    colDate: 'Date',
    colProvider: 'Provider',
    colService: 'Service',
    colResource: 'Resource',
    colTeam: 'Team',
    colEnvironment: 'Environment',
    colRegion: 'Region',
    colCost: 'Cost',
    reservationEfficiency: 'Reservation Efficiency',
    familiesCount: 'Families analyzed: {{count}}',
    loadingReservationEfficiency: 'Loading reservation efficiency...',
    noReservationEfficiency: 'No active reservations detected for this window.',
    avgUtilization: 'Average utilization',
    totalWaste: 'Total waste',
    totalReserved: 'Reserved commitment',
    colFamily: 'Family',
    colPriority: 'Priority',
    colUtilization: 'Utilization',
    colAction: 'Action',
    colWaste: 'Waste',
    colRenewal: 'Renewal',
    colAdvisor: 'Advisor signal',
    noRenewalWindow: 'No window',
    noAdvisorSignals: 'No signal',
    actionKeep: 'Keep',
    actionResize: 'Resize resource',
    actionScheduleStop: 'Schedule stop',
    actionExchange: 'Exchange reservation',
    actionDoNotRenew: 'Do not renew',
    reservationHighBadge: '{{count}} high',
    reservationCriticalOnly: 'Critical only',
    reservationShowAll: 'Show all',
  },
  economicsUsage: {
    title: 'Economics Usage',
    subtitle: 'Monitor usage behavior, identify volatility and track efficiency stability over time.',
    timeWindow: 'Time window',
    last30: 'Last 30 days',
    last60: 'Last 60 days',
    last90: 'Last 90 days',
    last180: 'Last 180 days',
    dailyAvg: 'Daily Average',
    dailyAvgDesc: 'Cost units / day',
    peakDay: 'Peak Day',
    peakDayDesc: 'Highest observed day',
    volatility: 'Volatility',
    volatilityDesc: 'Standard deviation',
    efficiencyScore: 'Efficiency Score',
    efficiencyScoreDesc: 'Stability and MoM impact',
    timeline: 'Usage Timeline ({{days}} days)',
    loadingTimeline: 'Loading usage timeline...',
    noData: 'No usage data available for this period.',
    colDate: 'Date',
    colValue: 'Usage Value',
  },
  economicsSkus: {
    title: 'Economics SKUs',
    subtitle: 'Track spending concentration by SKU dimension to prioritize optimization efforts.',
    note: 'SKU view is currently mapped from service-level billing dimension. Provider-native SKU ingestion will be connected in a follow-up increment.',
    window: 'Window',
    last30: 'Last 30 days',
    last60: 'Last 60 days',
    last90: 'Last 90 days',
    last180: 'Last 180 days',
    topRows: 'Top rows',
    top10: 'Top 10',
    top20: 'Top 20',
    top30: 'Top 30',
    top50: 'Top 50',
    totalCost: 'Total Cost',
    top3Share: 'Top 3 Share',
    breakdown: 'SKU Breakdown',
    loading: 'Loading SKU breakdown...',
    noData: 'No SKU data available for the selected window.',
    colRank: '#',
    colSku: 'SKU',
    colCost: 'Cost',
    colShare: 'Share',
  },
  economicsReports: {
    title: 'Economics Reports',
    subtitle: 'Generate operational snapshots from key financial indicators and export them as CSV.',
    reportWindow: 'Report window',
    last30: 'Last 30 days',
    last60: 'Last 60 days',
    last90: 'Last 90 days',
    processing: 'Processing...',
    exportCsv: 'Export CSV',
    exportExcel: 'Export Excel',
    currentMonth: 'Current Month',
    previousMonth: 'Previous Month',
    momChange: 'MoM Change',
    topServices: 'Top Services',
    topTeams: 'Top Teams',
    loading: 'Loading...',
    noData: 'No data available.',
    errorEnqueue: 'Failed to enqueue the export job.',
    asyncNote: 'Exports are generated asynchronously on the backend and downloaded when ready.',
    queued: 'Export queued. Waiting for worker pickup.',
    running: 'Export running. The download will start automatically.',
    completed: 'Export completed and downloaded.',
    completedDownload: 'Export completed. Starting download.',
  },
  notifications: {
    title: 'Notifications',
    subtitle: 'Workspace-wide alerts, budget breaches, and optimization signals.',
    markAllRead: 'Mark all read',
    unread: 'Unread',
    critical: 'Critical',
    totalVisible: 'Total Visible',
    allCategories: 'All categories',
    financial: 'Financial',
    optimization: 'Optimization',
    governance: 'Governance',
    activity: 'Activity',
    security: 'Security',
    allTypes: 'All types',
    typeActivity: 'Activity',
    typeCreated: 'Created',
    typeUpdated: 'Updated',
    typeDeleted: 'Deleted',
    typeSync: 'Sync',
    typeSecurity: 'Security',
    immediateActionTitle: 'Immediate action required',
    immediateActionDesc: '{{count}} critical unread alerts need attention now.',
    focusCritical: 'Focus critical',
    soundOn: 'Sound on',
    soundOff: 'Sound off',
    soundEnable: 'Enable alert sound',
    soundDisable: 'Disable alert sound',
    allStatuses: 'All statuses',
    statusUnread: 'Unread',
    statusRead: 'Read',
    statusArchived: 'Archived',
    error: 'Failed to load notifications. The backend service may still be initializing.',
    noNotifications: 'No notifications match your filters.',
    emptyHint: 'Alerts are generated from risk budget breaches, optimization signals, and workspace events.',
    viewDetails: 'View details →',
    markRead: 'Mark as read',
    archive: 'Archive',
  },
  settings: {
    passkeys: 'Passkeys',
    registeredAt: 'Registered at {{date}}',
    revoke: 'Revoke',
    noPasskeys: 'No passkeys registered.',
    registerPasskey: 'Register new passkey',
    registering: 'Registering...',
    passkeySuccess: 'Passkey registered successfully',
    passkeyError: 'Failed to register passkey',
    sessions: 'Sessions',
    logoutAll: 'End all sessions (global logout)',
    loggingOut: 'Ending sessions...',
    logoutSuccess: 'All sessions ended. Please log in again.',
    logoutError: 'Failed to end sessions. Please try again.',
  },
  members: {
    title: 'Members',
    subtitle: 'Manage workspace members and invite lifecycle from a single operational panel.',
    tabMembers: 'Members',
    tabInvites: 'Invites',
    createMember: 'Create Member',
    emailPlaceholder: 'member@company.com',
    fullNamePlaceholder: 'Full name',
    tempPasswordPlaceholder: 'Temporary password',
    creating: 'Creating...',
    workspaceMembers: 'Workspace Members ({{count}})',
    prev: 'Prev',
    pageOf: 'Page {{page}} / {{total}}',
    next: 'Next',
    loadingMembers: 'Loading members...',
    noMembers: 'No members found.',
    resetMfa: 'Reset MFA',
    resettingMfa: 'Resetting MFA...',
    resetPassword: 'Reset Password',
    resettingPassword: 'Resetting...',
    deactivate: 'Deactivate',
    deactivating: 'Deactivating...',
    edit: 'Edit',
    saving: 'Saving...',
    remove: 'Remove',
    removing: 'Removing...',
    createInvite: 'Create Invite',
    days3: '3 days',
    days7: '7 days',
    days14: '14 days',
    days30: '30 days',
    searchInvite: 'Search by invited email',
    statusPending: 'pending',
    statusAccepted: 'accepted',
    statusExpired: 'expired',
    statusRevoked: 'revoked',
    copyLink: 'Copy Link',
    revoke: 'Revoke',
    revoking: 'Revoking...',
    noInvites: 'No invites found.',
    tempPasswordTitle: 'Temporary Password Generated',
    tempPasswordUser: 'User: {{email}}',
    tempPasswordNote: 'Share this password securely. It is shown only once and the user must change password on next login.',
    copy: 'Copy',
    close: 'Close',
    deactivateTitle: 'Deactivate Member',
    deactivateDesc: 'Deactivating {{email}} blocks login immediately. This action is audited.',
    reason: 'Reason (required)',
    cancel: 'Cancel',
    confirmDeactivate: 'Confirm Deactivate',
    editMember: 'Edit Member',
    fullName: 'Full name',
    role: 'Role',
    save: 'Save',
    removeTitle: 'Remove Member',
    removeDesc: 'Removing {{email}} is audited and blocks login immediately.',
    confirmRemove: 'Confirm Remove',
    toastCreated: 'Member created successfully.',
    toastCreateError: 'Could not create member.',
    toastPasswordReset: 'Password reset completed for {{email}}.',
    toastPasswordError: 'Could not reset password.',
    toastMfaReset: 'MFA reset completed for {{email}}. Revoked passkeys: {{count}}.',
    toastMfaError: 'Could not reset MFA.',
    toastDeactivated: 'User {{email}} was deactivated.',
    toastDeactivateError: 'Could not deactivate user.',
    toastUpdated: 'User {{email}} updated.',
    toastUpdateError: 'Could not update user.',
    toastRemoved: 'User {{email}} was removed.',
    toastRemoveError: 'Could not remove user.',
    toastInviteCreated: 'Invite created for {{email}}. Link: {{link}}',
    toastInviteError: 'Could not create invite.',
    toastInviteRevoked: 'Invite revoked for {{email}}.',
    toastInviteRevokeError: 'Could not revoke invite.',
  },
  platform: {
    syncTitle: 'Platform Sync Status',
    syncSubtitle: 'Operational visibility for connector health and ingestion backlog.',
    syncAccounts: 'Accounts',
    syncNeedsAttention: 'Needs Attention',
    syncHealthy: 'Healthy',
    syncOpenDlq: 'Open DLQ',
    syncConnectorOps: 'Connector Operations',
    syncAllProviders: 'All providers',
    syncAllStatus: 'All status',
    syncStatusActive: 'Active',
    syncStatusPending: 'Pending',
    syncStatusInactive: 'Inactive',
    syncStatusError: 'Error',
    syncAllAttention: 'All attention',
    syncNeedsAttentionFilter: 'Needs attention',
    syncHealthyOnly: 'Healthy only',
    syncSortAttentionFirst: 'Sort: Attention first',
    syncSortDlqDesc: 'Sort: DLQ high to low',
    syncSortLatestSync: 'Sort: Latest sync',
    syncSortNameAsc: 'Sort: Name A-Z',
    syncPerPage: '{{n}} / page',
    syncColAccount: 'Account',
    syncColProvider: 'Provider',
    syncColStatus: 'Status',
    syncColLastSync: 'Last Sync',
    syncColLastHealth: 'Last Health Check',
    syncColOpenDlq: 'Open DLQ',
    syncColAttention: 'Attention',
    syncColAction: 'Action',
    syncAttentionYes: 'Yes',
    syncAttentionOk: 'OK',
    syncQueueing: 'Queueing...',
    syncTrigger: 'Trigger Sync',
    syncShowing: 'Showing {{from}}-{{to}} of {{total}}',
    syncPage: 'Page {{current}} / {{total}}',
    workspacesTitle: 'Platform Workspaces',
    workspacesSubtitle: 'Manage all organizations — suspend, restore, or archive workspaces.',
    workspacesAllOrgs: 'All Organizations',
    workspacesSearch: 'Search by name or slug',
    workspacesAllStates: 'All states',
    workspacesStateActive: 'Active',
    workspacesStateSuspended: 'Suspended',
    workspacesStateArchived: 'Archived',
    workspacesLoading: 'Loading workspaces…',
    workspacesNoOrgs: 'No organizations found.',
    workspacesColOrg: 'Organization',
    workspacesColPlan: 'Plan',
    workspacesColMembers: 'Members',
    workspacesColState: 'State',
    workspacesColCreated: 'Created',
    workspacesColActions: 'Actions',
    workspacesLoadingUsers: 'Loading users…',
    workspacesNoUsers: 'No users in this workspace.',
    workspacesUsers: 'Users ({{total}})',
    workspacesAuditWindow: 'Audit timeline window',
    workspacesLast24h: 'Last 24h',
    workspacesLast7d: 'Last 7 days',
    workspacesLast30d: 'Last 30 days',
    workspacesAllTime: 'All time',
    workspacesPwdResetBadge: 'pwd reset:',
    workspacesMfaResetBadge: 'mfa reset:',
    workspacesDeactivatedBadge: 'deactivated:',
    workspacesInactive: 'inactive',
    workspacesResetMfa: 'Reset MFA',
    workspacesResetting: 'Resetting...',
    workspacesResetPassword: 'Reset Password',
    workspacesDeactivateUser: 'Deactivate',
    workspacesDeactivating: 'Deactivating...',
    workspacesSuspendTitle: 'Suspend Workspace',
    workspacesRestoreTitle: 'Restore Workspace',
    workspacesArchiveTitle: 'Archive Workspace',
    workspacesArchiveWarning: '— this action is irreversible.',
    workspacesReasonRequired: 'Reason',
    workspacesReasonOptional: 'Reason (optional)',
    workspacesReasonPlaceholder: 'Describe the reason for this action…',
    workspacesRestorePlaceholder: 'Describe the reason for restoring…',
    workspacesActionFailed: 'Action failed. Please try again.',
    workspacesProcessing: 'Processing…',
    workspacesSuspend: 'Suspend',
    workspacesRestore: 'Restore',
    workspacesArchive: 'Archive',
    workspacesTempPwdTitle: 'Temporary Password Generated',
    workspacesTempPwdNote: 'Share this password securely. It is shown only once and the user must change it on next login.',
    workspacesConfirmResetMfa: 'Reset MFA for {{email}}? This will revoke all registered passkeys.',
    workspacesConfirmResetPassword: 'Reset password for {{email}}? A temporary password will be generated.',
    workspacesConfirmDeactivate: 'Deactivate {{email}}? This blocks login immediately while keeping audit history.',
    workspacesDeactivatePrompt: 'Reason for deactivation (required):',
    workspacesDeactivateDefault: 'Member offboarding',
    workspacesViewUsers: 'View users',
    workspacesSuspendHint: 'Suspend workspace',
    workspacesRestoreHint: 'Restore workspace',
    workspacesArchiveHint: 'Archive workspace (irreversible)',
    sloTitle: 'Platform SLI/SLO',
    sloSubtitle: 'Operational reliability view with error budget, latency targets and actionable alerts.',
    sloLoading: 'Loading SLI/SLO snapshot...',
    sloRequests: 'Requests',
    sloErrorRate: 'Error Rate',
    sloTarget: 'target: {{value}}%',
    sloBurnRate: 'Burn Rate',
    sloBurnDesc: 'error budget consumption speed',
    sloAlerts: 'Alerts',
    sloCriticalWarning: 'critical {{c}} · warning {{w}}',
    sloApiPathsTitle: 'API Path SLOs (Top 10)',
    sloColPath: 'Path',
    sloColReq: 'Req',
    sloColErrorPct: 'Error %',
    sloColP95: 'P95 (ms)',
    sloColAvg: 'Avg (ms)',
    sloColMax: 'Max (ms)',
    sloWorkerTitle: 'Worker Reliability',
    sloColWorker: 'Worker',
    sloColTotal: 'Total',
    sloColSuccess: 'Success',
    sloColRetry: 'Retry',
    sloColFailed: 'Failed',
    sloAlertsTitle: 'Actionable Alerts',
    sloNoAlerts: 'No active SLO alerts.',
    sloAlertAction: 'Action:',
    syncSuccessMsg: 'Sync job queued successfully.',
    syncErrorMsg: 'Could not trigger sync for this account. Please try again.',
    syncNoAccounts: 'No cloud accounts found.',
    refresh: 'Refresh',
    readOnlyBannerTitle: 'Read-only platform mode',
    readOnlyBannerBody: 'CauSium only reads tenant data and suggests actions. Nothing is executed automatically.',
  },
  login: {
    back: 'Back',
    oidcFailed: 'SSO sign in failed: {{error}}',
    invalidCredentials: 'Invalid email or password.',
    serverError: 'Server error. Please try again in a moment.',
    networkError: 'Could not connect. Check your network and try again.',
    passkeyFailed: 'Passkey sign in failed. Make sure you have registered a passkey for this account.',
    welcomeBack: 'Welcome back',
    subtitle: 'Cloud cost intelligence platform for safer decisions and faster execution.',
    badgeMultiCloud: 'Multi-Cloud',
    badgeRiskAware: 'Risk-Aware',
    badgeEnterprise: 'Enterprise Ready',
    signInContinue: 'Sign in to continue to your workspace.',
    emailLabel: 'Email',
    emailPlaceholder: 'customer.demo@causium.io',
    passwordLabel: 'Password',
    forgotPassword: 'Forgot password?',
    passwordPlaceholder: '••••••••••••',
    showPassword: 'Show password',
    hidePassword: 'Hide password',
    signIn: 'Sign in',
    signingIn: 'Signing in...',
    orContinueWith: 'or continue with',
    enterEmailFirst: 'Enter your email first',
    passkeySignIn: 'Sign in with Passkey',
    passkeyValidating: 'Validating passkey...',
    microsoftSignIn: 'Sign in with Microsoft',
    microsoftRedirecting: 'Redirecting to Microsoft...',
    noAccount: 'No account?',
    contactAdmin: 'Contact your workspace administrator.',
  },
}
