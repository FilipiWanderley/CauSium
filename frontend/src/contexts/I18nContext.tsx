import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { en } from '../locales/en'
import { pt } from '../locales/pt'
import type { Translations } from '../locales/en'

export type Language = 'en' | 'pt'

const LOCALES: Record<Language, Translations> = { en, pt }
const STORAGE_KEY = 'causium:lang'

interface I18nContextValue {
  lang: Language
  setLang: (l: Language) => void
  t: Translations
}

const I18nContext = createContext<I18nContextValue | null>(null)

export function I18nProvider({ children }: { children: React.ReactNode }) {
  // Language is fixed to English. Clear any previously stored locale preference.
  localStorage.removeItem(STORAGE_KEY)
  const [lang] = useState<Language>('en')
  const setLang = useCallback((_l: Language) => {}, [])

  const value = useMemo(
    () => ({ lang, setLang, t: LOCALES[lang] }),
    [lang, setLang]
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used inside I18nProvider')
  return ctx
}
