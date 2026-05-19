import { useEffect } from 'react'

const APP_NAME = 'CauSium'

/**
 * Sets document.title for the current page.
 * Pattern: "CauSium — Section Name"
 */
export function usePageTitle(section: string) {
  useEffect(() => {
    document.title = section ? `${APP_NAME} — ${section}` : APP_NAME
    return () => {
      document.title = APP_NAME
    }
  }, [section])
}
