import React, { createContext, useCallback, useEffect, useState } from 'react'
import { authApi } from '../api/auth'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  loginWithPasskey: (email: string) => Promise<void>
  registerCurrentPasskey: () => Promise<void>
  logout: () => Promise<void>
  logoutAll: () => Promise<void>
  /** Replace the in-memory user without a network round-trip. */
  refreshUser: (updated: User) => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(async () => {
    await authApi.logout()
    setUser(null)
  }, [])

  const logoutAll = useCallback(async () => {
    await authApi.logoutAll()
    setUser(null)
  }, [])

  /** Accept a freshly-returned User from the API and store it in context. */
  const refreshUser = useCallback(async (updated: User) => {
    setUser(updated)
  }, [])

  useEffect(() => {
    authApi
      .me()
      .then(({ data }) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await authApi.login(email, password)
    setUser(data.user)
  }, [])
  const base64urlToBuffer = useCallback((base64url: string) => {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
    const binary = atob(padded)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
    return bytes.buffer
  }, [])

  const textToBuffer = useCallback((value: string) => new TextEncoder().encode(value).buffer, [])

  const toBase64url = useCallback((buffer: ArrayBuffer) => {
    const bytes = new Uint8Array(buffer)
    let binary = ''
    bytes.forEach((b) => {
      binary += String.fromCharCode(b)
    })
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
  }, [])

  const assertPasskeyRuntime = useCallback(async () => {
    if (!window.isSecureContext) {
      throw new Error('Passkey requer contexto seguro (https ou localhost direto no navegador).')
    }
    if (!('PublicKeyCredential' in window) || !navigator.credentials) {
      throw new Error('Este navegador/ambiente não suporta passkey.')
    }
  }, [])

  const withTimeout = useCallback(async <T,>(promise: Promise<T>, ms: number, message: string): Promise<T> => {
    let timer: number | undefined
    const timeout = new Promise<never>((_, reject) => {
      timer = window.setTimeout(() => reject(new Error(message)), ms)
    })
    try {
      return (await Promise.race([promise, timeout])) as T
    } finally {
      if (timer) window.clearTimeout(timer)
    }
  }, [])

  const loginWithPasskey = useCallback(
    async (email: string) => {
      await assertPasskeyRuntime()
      const { data: options } = await authApi.passkeyLoginOptions(email)
      const assertion = (await withTimeout(
        navigator.credentials.get({
          publicKey: {
            challenge: base64urlToBuffer(options.challenge),
            timeout: options.timeout_ms,
            userVerification: 'preferred',
            rpId: options.rp_id,
            allowCredentials: options.allow_credentials.map((id) => ({
              id: base64urlToBuffer(id),
              type: 'public-key',
            })),
          },
        }),
        options.timeout_ms + 5000,
        'Tempo esgotado ao validar passkey.'
      )) as PublicKeyCredential | null
      if (!assertion) throw new Error('Passkey assertion failed')
      const response = assertion.response as AuthenticatorAssertionResponse
      const verify = await authApi.passkeyLoginVerify({
        email,
        challenge: options.challenge,
        credential_id: toBase64url(assertion.rawId),
        client_data_json: toBase64url(response.clientDataJSON),
        authenticator_data: toBase64url(response.authenticatorData),
        signature: toBase64url(response.signature),
        user_handle: response.userHandle ? toBase64url(response.userHandle) : null,
      })
      setUser(verify.data.user)
    },
    [assertPasskeyRuntime, base64urlToBuffer, toBase64url, withTimeout]
  )

  const registerCurrentPasskey = useCallback(async () => {
    if (!user) throw new Error('Not authenticated')
    await assertPasskeyRuntime()
    const { data: options } = await authApi.passkeyRegisterOptions(user.full_name)
    const credential = (await withTimeout(
      navigator.credentials.create({
        publicKey: {
          challenge: base64urlToBuffer(options.challenge),
          rp: { id: options.rp_id, name: options.rp_name },
          user: {
            id: textToBuffer(options.user_id),
            name: options.user_name,
            displayName: options.user_display_name,
          },
          pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
          timeout: options.timeout_ms,
          attestation: 'none',
          authenticatorSelection: {
            userVerification: 'preferred',
            residentKey: 'preferred',
          },
        },
      }),
      options.timeout_ms + 5000,
      'Tempo esgotado ao registrar passkey.'
    )) as PublicKeyCredential | null
    if (!credential) throw new Error('Passkey registration failed')
    const response = credential.response as AuthenticatorAttestationResponse
    const authData = response.getAuthenticatorData ? response.getAuthenticatorData() : null
    if (!authData) {
      throw new Error('Navegador não retornou authenticatorData da passkey')
    }
    const publicKeySpki = response.getPublicKey ? response.getPublicKey() : null
    if (!publicKeySpki) {
      throw new Error('Navegador não retornou chave pública da passkey')
    }
    const importedKey = await crypto.subtle.importKey(
      'spki',
      publicKeySpki,
      { name: 'ECDSA', namedCurve: 'P-256' },
      true,
      ['verify']
    )
    const publicKeyJwk = await crypto.subtle.exportKey('jwk', importedKey)
    if (!publicKeyJwk.x || !publicKeyJwk.y || publicKeyJwk.kty !== 'EC') {
      throw new Error('Falha ao extrair chave pública JWK da passkey')
    }
    await authApi.passkeyRegisterVerify({
      challenge: options.challenge,
      credential_id: toBase64url(credential.rawId),
      public_key_jwk: publicKeyJwk as Record<string, unknown>,
      client_data_json: toBase64url(response.clientDataJSON),
      authenticator_data: toBase64url(authData),
      attestation_object: toBase64url(response.attestationObject),
      transports: response.getTransports ? response.getTransports() : undefined,
      sign_count: 0,
    })
    const me = await authApi.me()
    setUser(me.data)
  }, [assertPasskeyRuntime, base64urlToBuffer, textToBuffer, toBase64url, user, withTimeout])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        loginWithPasskey,
        registerCurrentPasskey,
        logout,
        logoutAll,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
