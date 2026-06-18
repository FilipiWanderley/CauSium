/**
 * CloudProviderIcon - Ícones oficiais de cloud providers
 *
 * Usa react-icons para logos de provedores de nuvem.
 * Mantém consistência visual com Lucide React para ícones genéricos.
 */

import { FaAws, FaMicrosoft } from 'react-icons/fa'
import { SiGooglecloud } from 'react-icons/si'
import type { CloudProvider } from '../../types'

export interface CloudProviderIconProps {
  /** Provedor de nuvem */
  provider: CloudProvider
  /** Tamanho do ícone (default: 20) */
  size?: number
  /** Classes CSS adicionais */
  className?: string
  /** Título para acessibilidade (aria-label) */
  title?: string
}

/**
 * Mapeamento de provedores para cores branding
 */
const PROVIDER_COLORS: Record<CloudProvider, string> = {
  aws: '#FF9900',
  azure: '#0078D4',
  gcp: '#4285F4',
}

/**
 * Mapeamento de provedores para títulos acessíveis
 */
const PROVIDER_TITLES: Record<CloudProvider, string> = {
  aws: 'Amazon Web Services',
  azure: 'Microsoft Azure',
  gcp: 'Google Cloud Platform',
}

/**
 * CloudProviderIcon - Componente para exibir logos de cloud providers
 *
 * @example
 * ```tsx
 * // Ícone básico
 * <CloudProviderIcon provider="aws" />
 *
 * // Com tamanho customizado
 * <CloudProviderIcon provider="azure" size={24} />
 *
 * // Com classes e título
 * <CloudProviderIcon
 *   provider="gcp"
 *   size={16}
 *   className="text-blue-500"
 *   title="Google Cloud"
 * />
 * ```
 */
export function CloudProviderIcon({
  provider,
  size = 20,
  className = '',
  title,
}: CloudProviderIconProps) {
  const computedTitle = title ?? PROVIDER_TITLES[provider]

  const IconComponent = {
    aws: FaAws,
    azure: FaMicrosoft,
    gcp: SiGooglecloud,
  }[provider]

  return (
    <IconComponent
      size={size}
      className={className}
      title={computedTitle}
      aria-label={computedTitle}
      aria-hidden={false}
    />
  )
}

/**
 * Versão inline do ícone para uso em contextos onde
 * precisa de cor customizada via CSS
 */
export function CloudProviderIconRaw({
  provider,
  size = 20,
  className = '',
}: Omit<CloudProviderIconProps, 'title'>) {
  const IconComponent = {
    aws: FaAws,
    azure: FaMicrosoft,
    gcp: SiGooglecloud,
  }[provider]

  return (
    <IconComponent
      size={size}
      className={className}
      aria-hidden="true"
    />
  )
}

/**
 * Versão com cor branding do provider
 */
export function CloudProviderIconBranded({
  provider,
  size = 20,
  className = '',
  title,
}: CloudProviderIconProps) {
  const color = PROVIDER_COLORS[provider]
  const computedTitle = title ?? PROVIDER_TITLES[provider]

  const IconComponent = {
    aws: FaAws,
    azure: FaMicrosoft,
    gcp: SiGooglecloud,
  }[provider]

  return (
    <span
      className={`inline-flex items-center justify-center ${className}`}
      style={{ color }}
      title={computedTitle}
    >
      <IconComponent size={size} aria-hidden="true" />
    </span>
  )
}

/**
 * Componente de badge com ícone e label
 */
export interface CloudProviderBadgeProps {
  provider: CloudProvider
  label?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const BADGE_SIZES = {
  sm: {
    container: 'text-[10px] px-1.5 py-0.5 gap-1',
    icon: 12,
  },
  md: {
    container: 'text-xs px-2 py-1 gap-1.5',
    icon: 14,
  },
  lg: {
    container: 'text-sm px-2.5 py-1.5 gap-2',
    icon: 16,
  },
}

const BADGE_STYLES: Record<CloudProvider, string> = {
  aws: 'bg-orange-50 text-orange-700 border-orange-200',
  azure: 'bg-blue-50 text-blue-700 border-blue-200',
  gcp: 'bg-slate-100 text-slate-700 border-slate-200',
}

export function CloudProviderBadge({
  provider,
  label,
  size = 'md',
  className = '',
}: CloudProviderBadgeProps) {
  const sizes = BADGE_SIZES[size]
  const computedLabel = label ?? PROVIDER_TITLES[provider]

  return (
    <span
      className={`
        inline-flex items-center rounded-full border font-medium
        ${BADGE_STYLES[provider]}
        ${sizes.container}
        ${className}
      `}
    >
      <CloudProviderIconRaw provider={provider} size={sizes.icon} />
      <span className="whitespace-nowrap">{computedLabel}</span>
    </span>
  )
}

export default CloudProviderIcon