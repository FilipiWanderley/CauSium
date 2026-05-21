import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { I18nProvider } from '../../contexts/I18nContext'

vi.mock('../../api/auth', async () => {
  const getTotpStatus = vi.fn()
  const setupTotp = vi.fn()
  const enableTotp = vi.fn()
  const disableTotp = vi.fn()
  const getBackupCodesCount = vi.fn()
  const regenerateBackupCodes = vi.fn()
  return {
    authApi: {
      getTotpStatus,
      setupTotp,
      enableTotp,
      disableTotp,
      getBackupCodesCount,
      regenerateBackupCodes,
    },
    __mocks: {
      getTotpStatus,
      setupTotp,
      enableTotp,
      disableTotp,
      getBackupCodesCount,
      regenerateBackupCodes,
    },
  }
})

// qrcode.react needs canvas — stub it in jsdom
vi.mock('qrcode.react', () => ({
  QRCodeSVG: () => null,
}))

describe('MfaTotpSettings', () => {
  let mocks: Record<string, ReturnType<typeof vi.fn>>
  let MfaTotpSettings: React.ComponentType
  let QueryClient: any
  let QueryClientProvider: any

  function setup() {
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false, staleTime: 0 },
      },
    })
    render(
      <I18nProvider>
        <QueryClientProvider client={client}>
          <MfaTotpSettings />
        </QueryClientProvider>
      </I18nProvider>
    )
  }

  beforeAll(async () => {
    const mod = await import('../../api/auth')
    mocks = (mod as any).__mocks
    const comp = await import('./MfaTotpSettings')
    MfaTotpSettings = comp.MfaTotpSettings
    const rq = await import('@tanstack/react-query')
    QueryClient = rq.QueryClient
    QueryClientProvider = rq.QueryClientProvider
  })

  beforeEach(() => {
    Object.values(mocks).forEach((fn) => fn.mockReset())
    mocks.getTotpStatus.mockResolvedValue({ data: { enabled: false } })
    mocks.getBackupCodesCount.mockResolvedValue({ data: { backup_codes_remaining: 8 } })
  })

  it('shows disabled status and Enable 2FA button', async () => {
    setup()
    expect(await screen.findByText(/not enabled/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /enable 2fa/i })).toBeInTheDocument()
  })

  it('activates MFA: goes through setup → enable → backup codes → enabled', async () => {
    const BACKUP_CODES = ['AAAAA-11111', 'BBBBB-22222']
    mocks.setupTotp.mockResolvedValue({
      data: { secret: 'TESTSECRET', otpauth_url: 'otpauth://totp/test?secret=TESTSECRET' },
    })
    mocks.enableTotp.mockResolvedValue({
      data: { enabled: true, backup_codes: BACKUP_CODES },
    })
    // After enable, status becomes enabled
    mocks.getTotpStatus
      .mockResolvedValueOnce({ data: { enabled: false } })
      .mockResolvedValue({ data: { enabled: true } })

    setup()

    // Step: status
    fireEvent.click(await screen.findByRole('button', { name: /enable 2fa/i }))

    // Step: enable — wait for QR / secret / code input
    const codeInput = await screen.findByPlaceholderText(/authenticator code/i)
    expect(screen.getByText(/scan this qr code/i)).toBeInTheDocument()

    fireEvent.change(codeInput, { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: /^enable$/i }))

    // Step: backup_codes — should show codes
    for (const code of BACKUP_CODES) {
      expect(await screen.findByText(code)).toBeInTheDocument()
    }
    expect(screen.getByText(/save your recovery codes/i)).toBeInTheDocument()

    // Confirm backup codes saved
    fireEvent.click(screen.getByRole('button', { name: /i saved these codes/i }))

    // Step: enabled
    expect(await screen.findByText(/two-factor authentication is enabled/i)).toBeInTheDocument()
  })

  it('disables MFA with a TOTP code', async () => {
    mocks.getTotpStatus.mockResolvedValue({ data: { enabled: true } })
    mocks.disableTotp.mockResolvedValue({ data: { enabled: false } })
    mocks.getBackupCodesCount.mockResolvedValue({ data: { backup_codes_remaining: 3 } })

    setup()

    // Wait for enabled state
    expect(await screen.findByText(/two-factor authentication is enabled/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /disable 2fa/i }))

    // Step: disable — code input
    const codeInput = await screen.findByPlaceholderText(/authenticator code/i)
    fireEvent.change(codeInput, { target: { value: '654321' } })
    fireEvent.click(screen.getByRole('button', { name: /^disable$/i }))

    await waitFor(() => {
      expect(mocks.disableTotp).toHaveBeenCalledWith({ code: '654321' })
    })

    expect(await screen.findByText(/disabled/i)).toBeInTheDocument()
  })

  it('shows error when enable fails', async () => {
    mocks.setupTotp.mockResolvedValue({
      data: { secret: 'SECRET', otpauth_url: 'otpauth://totp/test?secret=SECRET' },
    })
    mocks.enableTotp.mockRejectedValue(new Error('Invalid code.'))

    setup()

    fireEvent.click(await screen.findByRole('button', { name: /enable 2fa/i }))
    const codeInput = await screen.findByPlaceholderText(/authenticator code/i)
    fireEvent.change(codeInput, { target: { value: '000000' } })
    fireEvent.click(screen.getByRole('button', { name: /^enable$/i }))

    expect(await screen.findByText(/invalid code/i)).toBeInTheDocument()
  })

  it('regenerates backup codes', async () => {
    mocks.getTotpStatus.mockResolvedValue({ data: { enabled: true } })
    mocks.getBackupCodesCount.mockResolvedValue({ data: { backup_codes_remaining: 1 } })
    const NEW_CODES = ['CCCCC-33333', 'DDDDD-44444']
    mocks.regenerateBackupCodes.mockResolvedValue({
      data: { enabled: true, backup_codes: NEW_CODES },
    })

    setup()

    expect(await screen.findByText(/two-factor authentication is enabled/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /regenerate recovery codes/i }))

    const codeInput = await screen.findByPlaceholderText(/authenticator code/i)
    fireEvent.change(codeInput, { target: { value: '111111' } })
    fireEvent.click(screen.getByRole('button', { name: /^regenerate$/i }))

    for (const code of NEW_CODES) {
      expect(await screen.findByText(code)).toBeInTheDocument()
    }
  })
})
