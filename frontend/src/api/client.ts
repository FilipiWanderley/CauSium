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

let _isRefreshing = false

apiClient.interceptors.response.use(
  (r) => r,
  async (error) => {
    const originalRequest = error.config
    // Only attempt refresh once, and not for auth endpoints themselves
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh') &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/me')
    ) {
      if (_isRefreshing) return Promise.reject(error)
      originalRequest._retry = true
      _isRefreshing = true
      try {
        await axios.post(
          `${BASE_URL}/api/v1/auth/refresh`,
          {},
          {
            withCredentials: true,
            headers: { 'Content-Type': 'application/json' },
          }
        )
        _isRefreshing = false
        return apiClient.request(originalRequest)
      } catch {
        _isRefreshing = false
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
