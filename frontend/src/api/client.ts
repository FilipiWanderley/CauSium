import axios from 'axios'

const ENV_BASE_URL = (import.meta.env.VITE_API_URL || '').trim()
const IS_LOCALHOST_RUNTIME =
  typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname === '::1')

// In local runtime, force same-origin `/api` (Vite proxy) to avoid
// cross-origin auth/cookie issues when VITE_API_URL points to a different port.
const BASE_URL = IS_LOCALHOST_RUNTIME ? '' : ENV_BASE_URL

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

apiClient.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        await axios.post(
          `${BASE_URL}/api/v1/auth/refresh`,
          {},
          {
            withCredentials: true,
            headers: { 'Content-Type': 'application/json' },
          }
        )
        return apiClient.request(error.config)
      } catch {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
