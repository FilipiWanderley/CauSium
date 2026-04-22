import { useEffect, useState } from 'react'

export function usePersistentBoolean(storageKey: string, defaultValue = false) {
  const [value, setValue] = useState<boolean>(() => {
    if (typeof window === 'undefined') return defaultValue
    try {
      const raw = window.localStorage.getItem(storageKey)
      if (raw == null) return defaultValue
      return raw === 'true'
    } catch {
      return defaultValue
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, String(value))
    } catch {
      // Ignore storage write failures (privacy mode or quota).
    }
  }, [storageKey, value])

  return [value, setValue] as const
}
