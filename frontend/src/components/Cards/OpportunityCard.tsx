import clsx from 'clsx'
import type { Opportunity } from '../../types'
import { useI18n } from '../../contexts/I18nContext'
import { buildAzurePortalResourceUrl, parseAzureResourceId } from '../../utils/azureResource'

const RISK_COLORS = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-red-100 text-red-700',
}

const EFFORT_COLORS = {
  low: 'bg-blue-100 text-blue-700',
  medium: 'bg-purple-100 text-purple-700',
  high: 'bg-orange-100 text-orange-700',
}

const CATEGORY_LABELS: Record<string, string> = {
  rightsizing: 'Rightsizing',
  idle_resources: 'Idle Resources',
  reserved_instances: 'Reserved Instances',
  storage_optimization: 'Storage',
  network_optimization: 'Network',
  license_optimization: 'License',
  architecture_change: 'Architecture',
}

interface Props {
  opportunity: Opportunity
  onClick?: () => void
}

export function OpportunityCard({ opportunity: op, onClick }: Props) {
  const { t } = useI18n()
  const o = t.opportunities
  const parsedResource = parseAzureResourceId(op.resource_id)
  const azurePortalUrl = buildAzurePortalResourceUrl(op.resource_id)
  const machineName = parsedResource?.resourceName ?? o.unknownResource
  const resourceGroup = parsedResource?.resourceGroup ?? op.resource_name ?? o.unknownResource
  const machineSku = op.sku_name ?? o.unknownResource
  const machineFamily = op.machine_family ?? o.unknownResource

  return (
    <div
      className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
              {CATEGORY_LABELS[op.category] || op.category}
            </span>
            {op.environment && (
              <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">
                {op.environment}
              </span>
            )}
          </div>
          <h3 className="font-semibold text-gray-900 truncate">{op.title}</h3>
          <p className="mt-1 text-sm text-gray-500 line-clamp-2">{op.description}</p>
        </div>

        {/* Score badge */}
        <div className="flex-shrink-0 flex flex-col items-center">
          <div
            className={clsx(
              'flex h-12 w-12 items-center justify-center rounded-full text-white font-bold text-sm',
              op.composite_score >= 70 ? 'bg-green-500' :
              op.composite_score >= 40 ? 'bg-yellow-500' : 'bg-gray-400'
            )}
          >
            {op.composite_score.toFixed(0)}
          </div>
          <span className="mt-1 text-xs text-gray-400">score</span>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={clsx('rounded px-2 py-0.5 text-xs font-medium', RISK_COLORS[op.risk_level])}>
            {op.risk_level} risk
          </span>
          <span className={clsx('rounded px-2 py-0.5 text-xs font-medium', EFFORT_COLORS[op.effort_level])}>
            {op.effort_level} effort
          </span>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-green-600">
            ${op.estimated_monthly_savings_usd.toLocaleString()}/mo
          </p>
          <p className="text-xs text-gray-400">
            ${op.estimated_annual_savings_usd.toLocaleString()}/yr
          </p>
        </div>
      </div>

      {(op.resource_id || op.resource_name) && (
        <div className="mt-3 border-t border-gray-100 pt-3">
          <p className="text-xs text-gray-500">{o.targetResource}</p>
          <p className="mt-1 text-xs text-gray-700">
            {o.machineName}: <strong>{machineName}</strong>
          </p>
          <p className="mt-1 text-xs text-gray-700">
            {o.resourceGroup}: <strong>{resourceGroup}</strong>
          </p>
          <p className="mt-1 text-xs text-gray-700">
            {o.machineSku}: <strong>{machineSku}</strong>
          </p>
          <p className="mt-1 text-xs text-gray-700">
            {o.machineFamily}: <strong>{machineFamily}</strong>
          </p>
          {azurePortalUrl && (
            <a
              href={azurePortalUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex text-xs font-medium text-brand-600 hover:text-brand-700 hover:underline"
              onClick={(event) => event.stopPropagation()}
            >
              {o.openInAzure}
            </a>
          )}
        </div>
      )}

      {op.owner_team && (
        <div className="mt-3 border-t border-gray-100 pt-3">
          <span className="text-xs text-gray-500">Team: <strong>{op.owner_team}</strong></span>
          {op.service && (
            <span className="ml-3 text-xs text-gray-500">Service: <strong>{op.service}</strong></span>
          )}
        </div>
      )}
    </div>
  )
}
