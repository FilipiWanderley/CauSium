const DEFAULT_DISPLAY_CURRENCY = 'BRL'

function resolveLocale(currency: string) {
  return currency === 'BRL' ? 'pt-BR' : 'en-US'
}

export function getDisplayCurrency(currency?: string | null) {
  return currency?.trim().toUpperCase() || DEFAULT_DISPLAY_CURRENCY
}

export function formatCurrency(
  value: number,
  currency?: string | null,
  options?: Intl.NumberFormatOptions & { locale?: string }
) {
  const resolvedCurrency = getDisplayCurrency(currency)
  const { locale, ...intlOptions } = options ?? {}

  return new Intl.NumberFormat(locale ?? resolveLocale(resolvedCurrency), {
    style: 'currency',
    currency: resolvedCurrency,
    maximumFractionDigits: 0,
    ...intlOptions,
  }).format(value)
}

export { DEFAULT_DISPLAY_CURRENCY }
