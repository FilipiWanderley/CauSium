export interface ParsedAzureResourceId {
  subscriptionId: string
  resourceGroup: string
  providerNamespace: string
  resourceTypePath: string
  resourceName: string
}

export function parseAzureResourceId(resourceId: string | null | undefined): ParsedAzureResourceId | null {
  if (!resourceId) return null
  const trimmed = resourceId.trim()
  if (!trimmed.startsWith('/')) return null

  const parts = trimmed.split('/').filter(Boolean)
  const subscriptionsIdx = parts.findIndex((p) => p.toLowerCase() === 'subscriptions')
  const resourceGroupsIdx = parts.findIndex((p) => p.toLowerCase() === 'resourcegroups')
  const providersIdx = parts.findIndex((p) => p.toLowerCase() === 'providers')

  if (subscriptionsIdx < 0 || resourceGroupsIdx < 0 || providersIdx < 0) return null
  if (subscriptionsIdx + 1 >= parts.length) return null
  if (resourceGroupsIdx + 1 >= parts.length) return null
  if (providersIdx + 2 >= parts.length) return null

  const subscriptionId = parts[subscriptionsIdx + 1]
  const resourceGroup = parts[resourceGroupsIdx + 1]
  const providerNamespace = parts[providersIdx + 1]
  const resourceTypeSegments = parts.slice(providersIdx + 2, parts.length - 1)
  const resourceTypePath = resourceTypeSegments.join('/')
  const resourceName = parts[parts.length - 1]

  return {
    subscriptionId,
    resourceGroup,
    providerNamespace,
    resourceTypePath,
    resourceName,
  }
}

export function buildAzurePortalResourceUrl(resourceId: string | null | undefined): string | null {
  if (!resourceId) return null
  const trimmed = resourceId.trim()
  if (!trimmed.startsWith('/')) return null
  return `https://portal.azure.com/#@/resource${trimmed}/overview`
}
