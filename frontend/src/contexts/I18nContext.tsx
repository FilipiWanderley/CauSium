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
  const [lang, setLangState] = useState<Language>(
    () => (localStorage.getItem(STORAGE_KEY) as Language) ?? 'en'
  )

  const setLang = useCallback((l: Language) => {
    localStorage.setItem(STORAGE_KEY, l)
    setLangState(l)
  }, [])

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
