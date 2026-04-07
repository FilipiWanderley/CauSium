import { apiClient } from './client'
import type { TokenResponse, User } from '../types'

export interface PasskeyRegistrationOptions {
  challenge: string
  rp_id: string
  rp_name: string
  user_id: string
  user_name: string
  user_display_name: string
  timeout_ms: number
}

export interface PasskeyLoginOptions {
  challenge: string
  rp_id: string
  allow_credentials: string[]
  timeout_ms: number
}

export interface PasskeyCredential {
  id: string
  credential_id: string
  transports: string[]
  sign_count: number
  created_at: string
  last_used_at: string | null
}

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<TokenResponse>('/auth/login', { email, password }),

  register: (data: {
    org_name: string
    org_slug: string
    email: string
    full_name: string
    password: string
  }) => apiClient.post<TokenResponse>('/auth/register', data),

  me: () => apiClient.get<User>('/auth/me'),

  refresh: () => apiClient.post<TokenResponse>('/auth/refresh', {}),

  logout: () => apiClient.post<void>('/auth/logout', {}),

  passkeyRegisterOptions: (display_name?: string) =>
    apiClient.post<PasskeyRegistrationOptions>('/auth/passkey/register/options', { display_name }),

  passkeyRegisterVerify: (payload: {
    challenge: string
    credential_id: string
    public_key_jwk: Record<string, unknown>
    client_data_json: string
    authenticator_data: string
    attestation_object?: string
    transports?: string[]
    sign_count?: number
  }) => apiClient.post<void>('/auth/passkey/register/verify', payload),

  passkeyLoginOptions: (email: string) =>
    apiClient.post<PasskeyLoginOptions>('/auth/passkey/login/options', { email }),

  passkeyLoginVerify: (payload: {
    email: string
    challenge: string
    credential_id: string
    client_data_json: string
    authenticator_data: string
    signature: string
    user_handle?: string | null
    sign_count?: number
  }) => apiClient.post<TokenResponse>('/auth/passkey/login/verify', payload),

  listPasskeys: () => apiClient.get<PasskeyCredential[]>('/auth/passkeys'),

  revokePasskey: (passkeyId: string) => apiClient.delete(`/auth/passkeys/${passkeyId}`),
}
