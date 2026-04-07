import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

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
