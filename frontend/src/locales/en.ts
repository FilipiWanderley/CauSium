export interface Translations {
  nav: {
    economics: string
    sectionEconomics: string
    sectionFinancial: string
    economicsCosts: string
    economicsUsage: string
    economicsSkus: string
    economicsReports: string
    sectionOptimization: string
    opportunities: string
    optimizationPlan: string
    experiments: string
    notifications: string
    sectionGovernance: string
    sectionSustainability: string
    sectionOperations: string
    sectionAdministration: string
    gov: string
    green: string
    initiatives: string
    riskBudgets: string
    changeEvents: string
    executive: string
    sectionPlatform: string
    members: string
    settings: string
    settingsTeam: string
    settingsCloud: string
    settingsSecurity: string
    platformWorkspaces: string
    platformSync: string
    platformSlo: string
    adminReconciliation: string
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
    subscriptionLabel: string
    allSubscriptionsConsolidated: string
    subscriptionScopedView: string
    consolidatedViewAcross: string
    syncHint: string
    filteredScope: string
    consolidatedScope: string
    currentMonthCost: string
    vsLastMonth: string
    financialOverview: string
    financialOverviewSubtitle: string
    optimizationSection: string
    optimizationSectionSubtitle: string
    operationsSection: string
    operationsSectionSubtitle: string
    financialMetric: string
    operationalMetric: string
    organizationWide: string
    subscriptionScoped: string
    billingContext: string
    explainCostCta: string
    explainCostTitle: string
    explainCostLoading: string
    explainCostError: string
    explainCostSummary: string
    explainCostCauses: string
    explainCostRecommendation: string
    explainCostConfidence: string
    explainCostModelRuleBased: string
    explainCostFallbackSummaryWithChange: string
    explainCostFallbackSummaryWithoutChange: string
    explainCostFallbackRecommendation: string
    insightsTitle: string
    insightsSubtitle: string
    insightsTopSaving: string
    insightsMainRisk: string
    insightsTrend: string
    insightsAction: string
    insightsConfidence: string
    insightsModelRuleBased: string
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
    monitoringVsBaseline: string
    todayCost: string
    avgPrevious30d: string
    todayVsAvgDelta: string
    partialUntilLastSync: string
    billingProcessingPending: string
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
    connectFirstAccountCta: string
    connectFirstAccountMessage: string
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
    alertCostSpike: string
    alertCostDrop: string
    alertCostDetail: string
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
    searchPlaceholder: string
    searchAriaLabel: string
    breadcrumbsHome: string
    operationalConsole: string
    scopeProvider: string
    scopeSubscription: string
    scopePeriod: string
    allProviders: string
    allSubscriptions: string
    period30d: string
    periodCurrentMonth: string
    period90d: string
    compactDensity: string
    comfortDensity: string
    enterpriseShellVersion: string
  }
  opportunities: {
    title: string
    subtitle: string
    viewTable: string
    viewCards: string
    open: string
    inProgress: string
    resolved: string
    totalSavings: string
    allCategories: string
    rightsizing: string
    aksAutoscalerRecommendation: string
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
    summaryOpportunities: string
    summaryPerMonth: string
    summaryHighRisk: string
    currentStatus: string
    colOpportunity: string
    colCategory: string
    colProvider: string
    colResourceScope: string
    colEstimatedMonthlySavings: string
    colConfidence: string
    colRisk: string
    colStatus: string
    colDetectedAt: string
    colAction: string
    readOnlyNoticeTitle: string
    readOnlyNoticeDesc: string
    openDetail: string
    providerAzure: string
    providerAws: string
    providerGcp: string
    providerUnknown: string
    riskLow: string
    riskMedium: string
    riskHigh: string
    executionOwnershipHint: string
    markInReview: string
    markApproved: string
    markValidated: string
    markDismissed: string
    rightsizingEvidenceTitle: string
    currentLabel: string
    recommendedLabel: string
    memoryP95Label: string
    monthlySavingsLabel: string
    savingsPctLabel: string
    confidenceLabel: string
    riskLabel: string
    reasonLabel: string
    aksEvidenceTitle: string
    clusterLabel: string
    nodePoolLabel: string
    nodesLabel: string
    skuLabel: string
    explainWithAI: string
    explainLoading: string
    explainError: string
    explainSummary: string
    explainWhyNow: string
    explainImpact: string
    explainRisks: string
    explainSteps: string
  }
  optimizationPlan: {
    title: string
    subtitle: string
    error: string
    adjustedMonthly: string
    adjustedAnnual: string
    quickWins: string
    conflicts: string
    summary: string
    conflictHints: string
    prioritized: string
    score: string
    savings: string
    governanceTitle: string
    governanceSubtitle: string
    noExecutionPlan: string
    generateExecutionPlan: string
    generateExecutionPlanSoon: string
    latestPlanId: string
    reviewComment: string
    reviewCommentPlaceholder: string
    approvePlan: string
    rejectPlan: string
    schedulePlan: string
    scheduledFor: string
    maintenanceWindow: string
    maintenanceWindowPlaceholder: string
    targetEnvironment: string
    targetCriticality: string
    sendToPulseLab: string
    handoffSuccess: string
    handoffError: string
    handoffExperimentId: string
    executionTrackingTitle: string
    executionTrackingSubtitle: string
    experimentStatusLabel: string
    executionOutcomeLabel: string
    expectedSavingsLabel: string
    actualSavingsLabel: string
    deltaSavingsLabel: string
    executionStatusRunning: string
    executionStatusCompleted: string
    executionStatusFailed: string
    executionOutcomeSuccess: string
    executionOutcomePartial: string
    executionOutcomeFailed: string
    updatingStatus: string
    statusUpdateError: string
    statusUpdateSuccessApproved: string
    statusUpdateSuccessRejected: string
    scheduleUpdateSuccess: string
    scheduleUpdateError: string
    timeline: string
    timelineReviewRequired: string
    timelineBlocked: string
    timelineApproved: string
    timelineScheduled: string
    timelineRejected: string
    statusReviewRequired: string
    statusBlocked: string
    statusApproved: string
    statusScheduled: string
    statusRejected: string
    statusUnknown: string
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
    summaryWithData: string
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
    subscriptionLabel: string
    allSubscriptionsConsolidated: string
    subscriptionViewing: string
    consolidatedAcross: string
    filteredScope: string
    consolidatedScope: string
    azureLabel: string
    scoreLabel: string
    topSavings: string
    completedDate: string
    perMonth: string
    azureSubscriptionsConnected: string
    monitoredHistoricalDays: string
    financialValuesBrl: string
    consolidated: string
    filtered: string
    organizationWide: string
    financialMetric: string
    operationalMetric: string
    subscriptionScoped: string
    billingContext: string
    overviewTitle: string
    overviewSubtitle: string
    optimizationTitle: string
    optimizationSubtitle: string
    operationsTitle: string
    operationsSubtitle: string
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
    governanceMetric: string
    organizationWide: string
    resourcesUnit: string
    complianceUnit: string
    sectionTitle: string
    sectionSubtitle: string
    noGovernanceIssues: string
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
    sustainabilityEstimate: string
    organizationWide: string
    overviewTitle: string
    overviewSubtitle: string
    breakdownTitle: string
    breakdownSubtitle: string
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
    subscriptionLabel: string
    allSubscriptionsCount: string
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
    colSubscription: string
    colService: string
    colResource: string
    colTeam: string
    colEnvironment: string
    colRegion: string
    colCost: string
    colShare: string
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
    financialValuesBrl: string
    filtered: string
    financialMetric: string
    billingContext: string
    overviewTitle: string
    overviewSubtitle: string
    optimizationTitle: string
    optimizationSubtitle: string
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
    operationalMetric: string
    organizationWide: string
    financialValuesBrl: string
    reservationCoverage: string
    computeSpendBasis: string
    reservedSpendBasis: string
    uncoveredSpendBasis: string
    coveragePct: string
    reservationCoverageLoading: string
    reservationCoverageEmpty: string
    reservationsDetected: string
    noReservationsDetected: string
    operationsTitle: string
    operationsSubtitle: string
    financialTitle: string
    financialSubtitle: string
    serviceColumn: string
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
    financialValuesBrl: string
    consolidated: string
    overviewTitle: string
    overviewSubtitle: string
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
    financialValuesBrl: string
    consolidated: string
    overviewTitle: string
    overviewSubtitle: string
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
    firstAccessHint: string
    noAccount: string
    contactAdmin: string
  }
  forgotPassword: {
    backToSignIn: string
    title: string
    subtitle: string
    emailLabel: string
    emailPlaceholder: string
    submit: string
    submitting: string
    genericError: string
    successTitle: string
    successMessage: string
  }
  resetPassword: {
    title: string
    subtitle: string
    tokenLabel: string
    tokenPlaceholder: string
    newPasswordLabel: string
    newPasswordPlaceholder: string
    confirmPasswordLabel: string
    confirmPasswordPlaceholder: string
    submit: string
    submitting: string
    errorPasswordsMismatch: string
    errorPasswordTooShort: string
    errorInvalidOrExpiredLink: string
    backToSignIn: string
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
  ux: {
    freshnessRecent: string
    freshnessSyncing: string
    freshnessSnapshot: string
    freshnessRefreshes: string
    tooltipForecast: string
    tooltipPotentialSavings: string
    tooltipGovernance: string
    tooltipCO2: string
    tooltipReservationCoverage: string
    tooltipEfficiencyScore: string
    tooltipVolatility: string
    tooltipConcentrationRisk: string
    emptyNoAnomalies: string
    emptyNoOptimizations: string
    emptyNoGovernanceIssues: string
    emptyNoRecentEvents: string
    emptyNoEmissions: string
    billingDataRange: string
    billingSubscriptions: string
    billingCostBasis: string
    billingCurrency: string
    costBasisActualPreTax: string
    integrityHealthy: string
    integrityDelayed: string
    integrityPartial: string
    integrityWarning: string
    integrityLastSync: string
    integrityDataThrough: string
    integrityBillingPeriod: string
    integrityGapDays: string
    integritySyncAge: string
    integritySubscriptions: string
    integrityDiagnosticsTitle: string
    integrityDiagnosticsSubtitle: string
    integrityProviderScope: string
    integrityDataCoverage: string
    integrityStatusLabel: string
    integrityDelayedMessage: string
    integrityNoDataMessage: string
    integrityPartialMessage: string
    exportBasisLabel: string
    exportFormatLabel: string
    exportReservationMeta: string
    exportReservationAvailable: string
    exportReservationNotAvailable: string
    exportPortalHint: string
  }
}

export const en: Translations = {
  nav: {
    economics: 'Dashboard',
    sectionEconomics: 'Economics',
    sectionFinancial: 'Financial',
    economicsCosts: 'Costs',
    economicsUsage: 'Usage',
    economicsSkus: 'SKUs',
    economicsReports: 'Reports',
    sectionOptimization: 'Optimization',
    opportunities: 'Opportunities',
    optimizationPlan: 'Optimization Plan',
    experiments: 'Experiments',
    notifications: 'Notifications',
    sectionGovernance: 'Governance',
    sectionSustainability: 'Sustainability',
    sectionOperations: 'Operations',
    sectionAdministration: 'Administration',
    gov: 'PulseGov',
    green: 'PulseGreen',
    initiatives: 'Initiatives',
    riskBudgets: 'Risk Budgets',
    changeEvents: 'Change Events',
    executive: 'Executive',
    sectionPlatform: 'Platform',
    members: 'Members',
    settings: 'Settings',
    settingsTeam: 'Team',
    settingsCloud: 'Cloud Accounts',
    settingsSecurity: 'Security',
    platformWorkspaces: 'Workspaces',
    platformSync: 'Sync',
    platformSlo: 'SLO',
    adminReconciliation: 'Reconciliation',
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
    refreshData: 'Refresh View',
    refreshingData: 'Refreshing...',
    adjustBudget: 'Budget Settings',
    queueIngestion: 'Sync Cloud Data',
    queueingIngestion: 'Syncing...',
    refreshSuccess: 'Dashboard data refreshed.',
    ingestQueuedSuccess: 'Ingestion queued for {{count}} account(s).',
    ingestNoAccounts: 'No active account available for ingestion.',
    actionError: 'Action failed. Please try again.',
    providerAll: 'All providers',
    providerAzure: 'Azure',
    providerAws: 'AWS',
    providerGcp: 'GCP',
    subscriptionLabel: 'Subscription',
    allSubscriptionsConsolidated: 'All subscriptions (consolidated)',
    subscriptionScopedView: 'Subscription-scoped view: {{name}}. Applies to cost metrics only.',
    consolidatedViewAcross: 'Consolidated view across {{count}} subscriptions.',
    syncHint: 'When syncing cloud data, new provider usage and costs may take a few minutes to appear.',
    filteredScope: 'Filtered: {{scope}}',
    consolidatedScope: 'Consolidated · {{count}} subscriptions',
    currentMonthCost: 'Current Month Cost',
    vsLastMonth: 'vs last month',
    financialOverview: 'Financial Overview',
    financialOverviewSubtitle: 'Spend, forecast and trend for the selected scope.',
    optimizationSection: 'Optimization',
    optimizationSectionSubtitle: 'Recommendations, anomaly signals and efficiency priorities for the current scope.',
    operationsSection: 'Operational Metrics',
    operationsSectionSubtitle: 'Monitoring, activity and connected cloud estate signals.',
    financialMetric: 'Financial metric',
    operationalMetric: 'Operational metric',
    organizationWide: 'Organization-wide',
    subscriptionScoped: 'Subscription scoped',
    billingContext: 'Billing context',
    explainCostCta: 'Explain change',
    explainCostTitle: 'Explain Cost Change',
    explainCostLoading: 'Analyzing cost drivers…',
    explainCostError: 'Could not generate an explanation right now.',
    explainCostSummary: 'Summary',
    explainCostCauses: 'Top causes',
    explainCostRecommendation: 'Recommendation',
    explainCostConfidence: 'Confidence',
    explainCostModelRuleBased: 'Based on billing history',
    explainCostFallbackSummaryWithChange:
      'From {{start}} to {{end}}, current month cost is {{cost}} with a {{change}} change vs last month.',
    explainCostFallbackSummaryWithoutChange:
      'From {{start}} to {{end}}, current month cost is {{cost}}. Month-over-month comparison is not available yet.',
    explainCostFallbackRecommendation:
      'Review recent cost drivers for this period, validate the billing context in {{currency}}, and compare top services before taking action.',
    insightsTitle: 'Historical Insights (baseline)',
    insightsSubtitle: 'Prioritized recommendations from cost, opportunities, and anomaly signals',
    insightsTopSaving: 'Savings summary',
    insightsMainRisk: 'Main risk',
    insightsTrend: 'Cost trend',
    insightsAction: 'Recommended action (based on historical baseline)',
    insightsConfidence: 'Insight confidence',
    insightsModelRuleBased: 'Based on billing history',
    insightsUnavailable: 'No optimization insights available for this scope yet.',
    anomaliesTitle: 'Cost Anomalies',
    anomaliesSubtitle: 'Outliers detected against recent baseline',
    anomaliesNone: 'No anomalies detected for the selected scope.',
    anomalyCriticalOnly: 'High only',
    anomalyShowAll: 'Show all',
    anomalySeverityLow: 'Low',
    anomalySeverityMedium: 'Medium',
    anomalySeverityHigh: 'High',
    potentialSavings: 'Potential Savings',
    openOpportunities: '{{count}} open opportunities',
    activeAccounts: 'Active Accounts',
    totalConnected: '{{count}} total connected',
    events7d: 'Recent events — last 7 days',
    cloudActivityEvents: 'Cloud activity & change events',
    monitoringVsBaseline: 'Current monitoring vs historical baseline',
    todayCost: "Today's cost",
    avgPrevious30d: 'Daily average (previous 30 days)',
    todayVsAvgDelta: 'Today vs average delta',
    partialUntilLastSync: 'Partial up to last sync',
    billingProcessingPending: 'Waiting for billing processing',
    costTrend: 'Cost baseline — last 30 days',
    noCostData: 'No cost data yet. Sync an account to populate.',
    topServices: 'Top services — historical window',
    noServiceData: 'No service data yet.',
    connectedAccounts: 'Connected Accounts',
    colAccount: 'Account',
    colProvider: 'Provider',
    colStatus: 'Status',
    colLastSync: 'Last Sync',
    never: 'Never',
    recentChanges: 'Recent Changes',
    viewAll: 'View all →',
    noChangeEvents: 'No recent change events found for this scope yet.',
    noAccounts: 'No accounts connected yet.',
    connectFirstAccountCta: 'Connect Account',
    connectFirstAccountMessage: 'Connect your first cloud account to start seeing your costs.',
    changeEventsOverlaid: '{{count}} change event{{s}} overlaid',
    reservationsTitle: 'Reservation Priorities',
    reservationsViewAll: 'Open costs →',
    reservationsPriority: 'Priority P{{priority}}',
    reservationsWaste: 'Waste {{waste}}',
    reservationsEmpty: 'No reservation opportunities detected for this scope yet.',
    resActionKeep: 'Keep',
    resActionResize: 'Resize',
    resActionScheduleStop: 'Schedule stop',
    resActionExchange: 'Exchange',
    resActionDoNotRenew: 'Do not renew',
    reservationsHighBadge: '{{count}} high',
    reservationsCriticalOnly: 'High priority only',
    reservationsShowAll: 'Show all',
    alertCostSpike: "Today's cost is {{delta}}% above the 30-day average",
    alertCostDrop: "Today's cost is {{delta}}% below the 30-day average",
    alertCostDetail: 'Today: {{today}} · 30d avg: {{avg}} · Delta: {{diff}}',
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
    searchPlaceholder: 'Search resources, opportunities, subscriptions or initiatives',
    searchAriaLabel: 'Global search',
    breadcrumbsHome: 'Console',
    operationalConsole: 'Operational Console',
    scopeProvider: 'Provider scope',
    scopeSubscription: 'Subscription scope',
    scopePeriod: 'Period',
    allProviders: 'All providers',
    allSubscriptions: 'All subscriptions',
    period30d: 'Last 30 days',
    periodCurrentMonth: 'Current month',
    period90d: 'Last 90 days',
    compactDensity: 'Compact density',
    comfortDensity: 'Comfort density',
    enterpriseShellVersion: 'Enterprise Shell Preview',
  },
  opportunities: {
    title: 'Opportunities',
    subtitle: 'Prioritized by composite score — financial impact × risk × effort',
    viewTable: 'Table',
    viewCards: 'Cards',
    open: 'Open',
    inProgress: 'In Progress',
    resolved: 'Resolved',
    totalSavings: 'Total Potential Savings',
    allCategories: 'All categories',
    rightsizing: 'Rightsizing',
    aksAutoscalerRecommendation: 'AKS Autoscaler',
    idleResources: 'Idle Resources',
    reservedInstances: 'Reserved Instances',
    storage: 'Storage',
    network: 'Network',
    noOpportunities: 'No opportunities in the operational queue.',
    noOpportunitiesHint: 'Sync cloud accounts and generate recommendations to populate this FinOps work queue.',
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
    summaryOpportunities: '{{count}} opportunities',
    summaryPerMonth: '{{amount}}/mo',
    summaryHighRisk: '{{count}} high risk',
    currentStatus: 'Current status',
    colOpportunity: 'Opportunity',
    colCategory: 'Category',
    colProvider: 'Provider',
    colResourceScope: 'Resource / scope',
    colEstimatedMonthlySavings: 'Estimated monthly savings',
    colConfidence: 'Confidence',
    colRisk: 'Risk',
    colStatus: 'Status',
    colDetectedAt: 'Detected',
    colAction: 'Action',
    readOnlyNoticeTitle: 'Read-only analysis mode',
    readOnlyNoticeDesc: 'The platform only reads tenant data and generates recommendations. Execution always happens after explicit client decision.',
    openDetail: 'Open detail',
    providerAzure: 'Azure',
    providerAws: 'AWS',
    providerGcp: 'GCP',
    providerUnknown: 'Unmapped',
    riskLow: 'Low',
    riskMedium: 'Medium',
    riskHigh: 'High',
    executionOwnershipHint: 'Execution is external to the platform and owned by the client team.',
    markInReview: 'Mark as under review',
    markApproved: 'Mark as approved/executed',
    markValidated: 'Mark as validated',
    markDismissed: 'Mark as dismissed',
    rightsizingEvidenceTitle: 'Rightsizing Evidence',
    currentLabel: 'Current',
    recommendedLabel: 'Recommended',
    memoryP95Label: 'Memory p95',
    monthlySavingsLabel: 'Monthly Savings',
    savingsPctLabel: 'Savings %',
    confidenceLabel: 'Confidence',
    riskLabel: 'Risk',
    reasonLabel: 'Reason',
    aksEvidenceTitle: 'AKS Node Pool Evidence',
    clusterLabel: 'Cluster',
    nodePoolLabel: 'Node Pool',
    nodesLabel: 'Nodes',
    skuLabel: 'SKU',
    explainWithAI: 'Explain with AI',
    explainLoading: 'Generating explanation...',
    explainError: 'Could not generate explanation right now.',
    explainSummary: 'Summary',
    explainWhyNow: 'Why now',
    explainImpact: 'Expected impact',
    explainRisks: 'Risks',
    explainSteps: 'Recommended steps',
  },
  optimizationPlan: {
    title: 'Optimization Plan',
    subtitle: 'Deterministic ranking with quick wins and conflict-aware savings',
    error: 'Could not load optimization plan.',
    adjustedMonthly: 'Adjusted Monthly Savings',
    adjustedAnnual: 'Adjusted Annual Savings',
    quickWins: 'Quick Wins',
    conflicts: 'Conflicts',
    summary: 'Execution Summary',
    conflictHints: 'Conflict Hints',
    prioritized: 'Prioritized Recommendations',
    score: 'Priority score',
    savings: 'Savings',
    governanceTitle: 'Execution Governance',
    governanceSubtitle: 'Approval workflow for execution plans with audit trail',
    noExecutionPlan: 'No execution plan available yet. Create one to enable approval workflow.',
    generateExecutionPlan: 'Generate Execution Plan',
    generateExecutionPlanSoon: 'Coming soon',
    latestPlanId: 'Execution plan',
    reviewComment: 'Review comment',
    reviewCommentPlaceholder: 'Add a context comment for approval or rejection.',
    approvePlan: 'Approve Plan',
    rejectPlan: 'Reject Plan',
    schedulePlan: 'Schedule Plan',
    scheduledFor: 'Scheduled For',
    maintenanceWindow: 'Maintenance Window',
    maintenanceWindowPlaceholder: 'e.g. night_window_02_04_utc',
    targetEnvironment: 'Target Environment',
    targetCriticality: 'Target Criticality',
    sendToPulseLab: 'Send to PulseLab',
    handoffSuccess: 'PulseLab handoff created. Experiment ID:',
    handoffError: 'Could not create PulseLab handoff.',
    handoffExperimentId: 'PulseLab Experiment',
    executionTrackingTitle: 'Execution Tracking',
    executionTrackingSubtitle: 'Synchronized with PulseLab status and real savings results.',
    experimentStatusLabel: 'Experiment Status',
    executionOutcomeLabel: 'Execution Outcome',
    expectedSavingsLabel: 'Expected Savings',
    actualSavingsLabel: 'Actual Savings',
    deltaSavingsLabel: 'Delta',
    executionStatusRunning: 'Running',
    executionStatusCompleted: 'Completed',
    executionStatusFailed: 'Failed',
    executionOutcomeSuccess: 'Success',
    executionOutcomePartial: 'Partial',
    executionOutcomeFailed: 'Failed',
    updatingStatus: 'Updating...',
    statusUpdateError: 'Could not update execution plan status.',
    statusUpdateSuccessApproved: 'Execution plan approved successfully.',
    statusUpdateSuccessRejected: 'Execution plan rejected successfully.',
    scheduleUpdateSuccess: 'Execution plan scheduled successfully.',
    scheduleUpdateError: 'Could not schedule execution plan.',
    timeline: 'Timeline',
    timelineReviewRequired: 'Review Required',
    timelineBlocked: 'Blocked',
    timelineApproved: 'Approved',
    timelineScheduled: 'Scheduled',
    timelineRejected: 'Rejected',
    statusReviewRequired: 'Review Required',
    statusBlocked: 'Blocked',
    statusApproved: 'Approved',
    statusScheduled: 'Scheduled',
    statusRejected: 'Rejected',
    statusUnknown: 'Unknown',
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
    summaryWithData: '{{count}} experiments · ${{savings}} realized',
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
    noData: 'No violations detected. Configure a budget and trigger a deployment to visualize risk data.',
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
    subtitle: 'Consolidated financial performance, savings, and team efficiency.',
    currentMonthCost: 'Current Month Spend',
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
    subscriptionLabel: 'Subscription',
    allSubscriptionsConsolidated: 'All subscriptions (consolidated)',
    subscriptionViewing: 'Viewing: {{scope}}. Financial metrics only.',
    consolidatedAcross: 'Consolidated across {{count}} subscriptions.',
    filteredScope: 'Filtered: {{scope}}',
    consolidatedScope: 'Consolidated · {{count}} subscriptions',
    azureLabel: 'Azure',
    scoreLabel: 'Score',
    topSavings: 'Top Realized Savings',
    completedDate: 'Completed {{date}}',
    perMonth: '/mo',
    azureSubscriptionsConnected: 'Azure real data — {{count}} connected subscription(s)',
    monitoredHistoricalDays: 'monitored over the last {{days}} days (historical baseline)',
    financialValuesBrl: 'Displayed using tenant billing context',
    consolidated: 'Consolidated',
    filtered: 'Filtered',
    organizationWide: 'Organization-wide',
    financialMetric: 'Billing-context financial metric',
    operationalMetric: 'Operational metric',
    subscriptionScoped: 'Subscription scoped',
    billingContext: 'Billing context',
    overviewTitle: 'Financial Overview',
    overviewSubtitle: 'Spend, forecast and savings performance for the selected scope.',
    optimizationTitle: 'Optimization',
    optimizationSubtitle: 'Savings execution progress, forecast and prioritized initiatives.',
    operationsTitle: 'Operational Metrics',
    operationsSubtitle: 'Team efficiency signals and current operating performance by team.',
  },
  gov: {
    title: 'PulseGov',
    subtitle: 'Resource governance metrics for ownership coverage, label compliance, Advisor recommendations, and full inventory.',
    last7: 'Last 7 days',
    last30: 'Last 30 days',
    last90: 'Last 90 days',
    billedResources: 'Billed Resources',
    unowned: 'Unowned',
    avgCompliance: 'Avg Compliance',
    recommendations: 'Recommendations',
    estSavings: 'Est. Savings',
    deployedResources: 'Governed Resources',
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
    colCost: 'Spend',
    colTeam: 'Team',
    colTotalCost: 'Total Spend',
    colUntaggedCost: 'Untagged Spend',
    colCompliance: 'Compliance',
    errorUnowned: 'Failed to load unowned costs data.',
    errorCompliance: 'Failed to load compliance data.',
    noCompliance: 'Waiting for compliance data. Trigger an inventory sync to populate this view.',
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
    governanceMetric: 'Governance metric',
    organizationWide: 'Organization-wide',
    resourcesUnit: 'resources',
    complianceUnit: 'compliance %',
    sectionTitle: 'Governance',
    sectionSubtitle: 'Policy, tagging and operational compliance signals across the organization.',
    noGovernanceIssues: 'No governance issues found.',
  },
  green: {
    title: 'PulseGreen',
    subtitle: 'Sustainability estimate derived from cloud spend and regional grid intensity.',
    last3m: 'Last 3 months',
    last6m: 'Last 6 months',
    last12m: 'Last 12 months',
    totalCO2: 'Total CO₂e',
    kg: 'kg',
    tCO2: 'tCO₂e',
    cloudSpend: 'Cloud Spend Basis',
    intensity: 'Intensity (gCO₂e/$)',
    momDelta: 'MoM Delta',
    monthlyTrend: 'Monthly Emissions Trend',
    noEmissions: 'No emission records for this period. Try expanding the date range or syncing a data source with carbon metrics.',
    colMonth: 'Month',
    colKg: 'kgCO₂e',
    colTCO2: 'tCO₂e',
    colCost: 'Cloud Spend Basis',
    colMom: 'MoM',
    breakdown: 'Emissions Breakdown',
    window7: '7 days',
    window30: '30 days',
    window90: '90 days',
    byService: 'By Service',
    byRegion: 'By Region',
    byEnvironment: 'By Environment',
    byTeam: 'By Team',
    noBreakdown: 'No team-level data available. Assign team tags to resources to view emissions distribution.',
    dataOfficial: 'Data source: official provider carbon API',
    dataEstimated: 'Data source: calibrated cost-based estimate',
    dataMixed: 'Data source: mixed (official + estimated)',
    sustainabilityEstimate: 'Sustainability estimate',
    organizationWide: 'Organization-wide',
    overviewTitle: 'Sustainability',
    overviewSubtitle: 'Carbon and efficiency estimates based on cloud usage and billing signals.',
    breakdownTitle: 'Sustainability Breakdown',
    breakdownSubtitle: 'Emission distribution across cloud dimensions for the selected time window.',
  },
  economicsCosts: {
    title: 'Economics Costs',
    subtitle: 'Historical baseline analysis of spend distribution by service and team with interactive filters.',
    timeWindow: 'Historical window',
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
    subscriptionLabel: 'Subscription',
    allSubscriptionsCount: 'All ({{count}})',
    visibleCost: 'Visible Spend',
    exportReport: 'Export Report',
    format: 'Format',
    csv: 'CSV',
    excel: 'Excel (.xlsx)',
    requesting: 'Requesting…',
    generating: 'Generating…',
    buildingFormat: 'Building {{format}} — please wait…',
    downloadFile: 'Download {{filename}}',
    reset: 'Reset',
    detailedCosts: 'Detailed Spend Rows',
    detailedCostsDesc: 'Detailed ledger rows with combined filters and pagination.',
    totalRows: 'Total rows: {{count}}',
    loadingRows: 'Loading detailed costs...',
    noRows: 'No cost rows for current filters.',
    pageOf: 'Page {{page}} of {{total}}',
    previous: 'Previous',
    next: 'Next',
    costByService: 'Spend by Service',
    loadingServices: 'Loading services...',
    noServiceData: 'No results for the selected filters. Try clearing filters or expanding the time range.',
    costByTeam: 'Spend by Team',
    loadingTeams: 'Loading teams...',
    noTeamData: 'No team data available.',
    colDate: 'Date',
    colProvider: 'Provider',
    colSubscription: 'Subscription',
    colService: 'Service',
    colResource: 'Resource',
    colTeam: 'Team',
    colEnvironment: 'Environment',
    colRegion: 'Region',
    colCost: 'Spend',
    colShare: 'Share',
    reservationEfficiency: 'Reservation Efficiency',
    familiesCount: 'Families analyzed: {{count}}',
    loadingReservationEfficiency: 'Loading reservation efficiency...',
    noReservationEfficiency: 'No active reservations or savings plans detected. Purchase reservations to reduce cost and unlock this analysis.',
    avgUtilization: 'Average utilization',
    totalWaste: 'Potential Waste',
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
    financialValuesBrl: 'Financial values follow tenant billing context',
    filtered: 'Filtered',
    financialMetric: 'Financial metric',
    billingContext: 'Billing context',
    overviewTitle: 'Financial Overview',
    overviewSubtitle: 'Spend visibility and detailed billing rows for the current filter set.',
    optimizationTitle: 'Optimization',
    optimizationSubtitle: 'Reservation efficiency and waste signals to prioritize optimization work.',
  },
  economicsUsage: {
    title: 'Economics Usage',
    subtitle: 'Monitor operational usage behavior, identify volatility, and track efficiency stability over time.',
    timeWindow: 'Time window',
    last30: 'Last 30 days',
    last60: 'Last 60 days',
    last90: 'Last 90 days',
    last180: 'Last 180 days',
    dailyAvg: 'Daily Average',
    dailyAvgDesc: 'Usage units / day',
    peakDay: 'Peak Day',
    peakDayDesc: 'Highest usage day',
    volatility: 'Volatility',
    volatilityDesc: 'Operational variance',
    efficiencyScore: 'Efficiency Score',
    efficiencyScoreDesc: 'Operational metric',
    timeline: 'Usage Timeline ({{days}} days)',
    loadingTimeline: 'Loading usage timeline...',
    noData: 'No usage data available for this period.',
    colDate: 'Date',
    colValue: 'Usage units / day',
    operationalMetric: 'Operational metric',
    organizationWide: 'Organization-wide',
    financialValuesBrl: 'Displayed using tenant billing context',
    reservationCoverage: 'Reservation Coverage',
    computeSpendBasis: 'Compute Spend Basis',
    reservedSpendBasis: 'Reserved Commitment Spend',
    uncoveredSpendBasis: 'Uncovered Spend Basis',
    coveragePct: 'Coverage (%)',
    reservationCoverageLoading: 'Calculating reservation coverage...',
    reservationCoverageEmpty: 'No reservation data for this period.',
    reservationsDetected: 'Reservations detected',
    noReservationsDetected: 'No active reservation detected',
    operationsTitle: 'Operational Metrics',
    operationsSubtitle: 'Usage intensity, peaks and stability indicators for the selected time window.',
    financialTitle: 'Financial Overview',
    financialSubtitle: 'Reservation coverage and billing-aligned spend basis for compute usage.',
    serviceColumn: 'Service',
  },
  economicsSkus: {
    title: 'Economics SKUs',
    subtitle: 'Track spend concentration by SKU dimension to prioritize optimization efforts.',
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
    totalCost: 'Total Spend',
    top3Share: 'Top 3 Share',
    breakdown: 'SKU Spend Breakdown',
    loading: 'Loading SKU breakdown...',
    noData: 'No SKU data available for the selected window.',
    colRank: '#',
    colSku: 'SKU',
    colCost: 'Spend',
    colShare: 'Share',
    financialValuesBrl: 'Financial values follow tenant billing context',
    consolidated: 'Billing-aligned view',
    overviewTitle: 'Financial Overview',
    overviewSubtitle: 'Billing concentration by SKU dimension to highlight where spend is most concentrated.',
  },
  economicsReports: {
    title: 'Economics Reports',
    subtitle: 'Generate consolidated snapshots from key financial indicators and export them as CSV or Excel.',
    reportWindow: 'Report window',
    last30: 'Last 30 days',
    last60: 'Last 60 days',
    last90: 'Last 90 days',
    processing: 'Processing...',
    exportCsv: 'Export CSV',
    exportExcel: 'Export Excel',
    currentMonth: 'Current Month Spend',
    previousMonth: 'Previous Month Spend',
    momChange: 'MoM Change',
    topServices: 'Top Services by Spend',
    topTeams: 'Top Teams by Spend',
    loading: 'Loading...',
    noData: 'Select a time range and click Generate Report to view financial indicators.',
    errorEnqueue: 'Failed to enqueue the export job.',
    asyncNote: 'Exports are generated asynchronously on the backend and downloaded when ready.',
    queued: 'Export queued. Waiting for worker pickup.',
    running: 'Export running. The download will start automatically.',
    completed: 'Export completed and downloaded.',
    completedDownload: 'Export completed. Starting download.',
    financialValuesBrl: 'Uses dashboard billing currency when available',
    consolidated: 'Billing-aligned view',
    overviewTitle: 'Financial Overview',
    overviewSubtitle: 'Export-ready financial summary with billing-aligned monthly trend context.',
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
    emailPlaceholder: 'customer@causium.io',
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
    firstAccessHint: 'First access? Use the invite link sent to your email.',
    noAccount: 'No account?',
    contactAdmin: 'Contact your workspace administrator.',
  },
  forgotPassword: {
    backToSignIn: 'Back to sign in',
    title: 'Reset your password',
    subtitle: "Enter your email and we'll send you reset instructions.",
    emailLabel: 'Email',
    emailPlaceholder: 'you@company.com',
    submit: 'Send reset instructions',
    submitting: 'Sending…',
    genericError: 'Something went wrong. Please try again.',
    successTitle: 'Check your instructions',
    successMessage: 'If {{email}} is registered, you will receive password reset instructions.',
  },
  resetPassword: {
    title: 'Set new password',
    subtitle: 'Choose a strong password for your account.',
    tokenLabel: 'Reset token',
    tokenPlaceholder: 'Paste your reset token here',
    newPasswordLabel: 'New password',
    newPasswordPlaceholder: 'Min. 8 characters',
    confirmPasswordLabel: 'Confirm password',
    confirmPasswordPlaceholder: 'Repeat your new password',
    submit: 'Update password',
    submitting: 'Updating password…',
    errorPasswordsMismatch: 'Passwords do not match.',
    errorPasswordTooShort: 'Password must be at least 8 characters.',
    errorInvalidOrExpiredLink: 'Failed to reset password. The link may be expired or invalid.',
    backToSignIn: 'Back to sign in',
  },
  ux: {
    freshnessRecent: 'Last updated recently',
    freshnessSyncing: 'Cloud sync in progress',
    freshnessSnapshot: 'Based on latest available billing snapshot',
    freshnessRefreshes: 'Data refreshes periodically',
    tooltipForecast: 'Projected using historical spend trends.',
    tooltipPotentialSavings: 'Estimated optimization opportunities based on detected inefficiencies.',
    tooltipGovernance: 'Derived from tagging, policy and operational governance signals.',
    tooltipCO2: 'Estimated using cloud usage and sustainability factors.',
    tooltipReservationCoverage: 'Percentage of compute spend covered by reservations or savings plans.',
    tooltipEfficiencyScore: 'Composite score based on cost volatility and month-over-month variation.',
    tooltipVolatility: 'Standard deviation of daily spend over the selected window.',
    tooltipConcentrationRisk: 'Share of total cost concentrated in the top 3 SKUs.',
    emptyNoAnomalies: 'No anomalies detected for this scope.',
    emptyNoOptimizations: 'No optimization opportunities detected yet.',
    emptyNoGovernanceIssues: 'No governance issues found.',
    emptyNoRecentEvents: 'No recent operational events.',
    emptyNoEmissions: 'No emissions data available for this period.',
    billingDataRange: '{{start}} – {{end}}',
    billingSubscriptions: '{{count}} subscriptions consolidated',
    billingCostBasis: 'Actual Cost · Pre-tax',
    billingCurrency: 'Billing: {{currency}}',
    costBasisActualPreTax: 'Actual Cost · Pre-tax',
    integrityHealthy: 'Healthy',
    integrityDelayed: 'Delayed',
    integrityPartial: 'Partial',
    integrityWarning: 'Warning',
    integrityLastSync: 'Last sync: {{time}}',
    integrityDataThrough: 'Data available through {{date}}',
    integrityBillingPeriod: 'Billing period: calendar month',
    integrityGapDays: 'Ingestion gap: {{days}} day(s)',
    integritySyncAge: 'Sync age: {{minutes}} min',
    integritySubscriptions: '{{count}} active subscriptions',
    integrityDiagnosticsTitle: 'Data Diagnostics',
    integrityDiagnosticsSubtitle: 'Detailed metadata about data freshness and coverage',
    integrityProviderScope: 'Provider scope: {{scope}}',
    integrityDataCoverage: 'Coverage: {{start}} to {{end}}',
    integrityStatusLabel: 'Reconciliation status',
    integrityDelayedMessage: 'Billing data is 3–5 days behind. This is common during provider processing windows.',
    integrityNoDataMessage: 'No billing data available. Verify cloud account connectivity.',
    integrityPartialMessage: 'Data coverage is incomplete. Some subscriptions may not be reporting.',
    exportBasisLabel: 'Export basis: {{basis}}',
    exportFormatLabel: 'Export format: {{format}}',
    exportReservationMeta: 'Reservation metadata',
    exportReservationAvailable: 'Available',
    exportReservationNotAvailable: 'Not available in current export',
    exportPortalHint: '{{hint}}',
  },
}
