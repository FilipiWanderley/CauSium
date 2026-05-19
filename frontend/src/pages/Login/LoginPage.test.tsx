import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../contexts/I18nContext'

const loginMock = vi.fn()
const loginWithPasskeyMock = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    login: loginMock,
    loginWithPasskey: loginWithPasskeyMock,
    isAuthenticated: false,
  }),
}))

vi.mock('lucide-react', () => ({
  Cloud: () => null,
  ArrowLeft: () => null,
  Cpu: () => null,
  Eye: () => null,
  EyeOff: () => null,
}))

async function renderPage(search = '') {
  const { LoginPage } = await import('./LoginPage')
  return render(
    <MemoryRouter initialEntries={[`/login${search}`]}>
      <I18nProvider>
        <LoginPage />
      </I18nProvider>
    </MemoryRouter>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    loginMock.mockReset()
    loginWithPasskeyMock.mockReset()
    vi.unstubAllEnvs()
    vi.stubEnv('VITE_AUTH_PASSKEY_LOGIN_ENABLED', 'false')
    vi.stubEnv('VITE_AUTH_MICROSOFT_LOGIN_ENABLED', 'false')
  })

  it('renders sign-in form', async () => {
    await renderPage()
    expect(screen.getByPlaceholderText('customer@causium.io')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••••••')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in$/i })).toBeInTheDocument()
  })

  it('calls login with email and password on submit', async () => {
    loginMock.mockResolvedValue(undefined)
    await renderPage()

    fireEvent.change(screen.getByPlaceholderText('customer@causium.io'), {
      target: { value: 'user@company.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••••••'), {
      target: { value: 'secret123' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in$/i }))

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith('user@company.com', 'secret123')
    })
  })

  it('shows error message on login failure', async () => {
    loginMock.mockRejectedValue({ response: { status: 401 } })
    await renderPage()

    fireEvent.change(screen.getByPlaceholderText('customer@causium.io'), {
      target: { value: 'bad@company.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••••••'), {
      target: { value: 'wrongpass' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in$/i }))

    expect(await screen.findByText(/invalid email or password/i)).toBeInTheDocument()
  })

  it('disables submit button while loading', async () => {
    let resolve!: (value?: unknown) => void
    loginMock.mockImplementation(() => new Promise((r) => { resolve = r }))
    await renderPage()

    fireEvent.change(screen.getByPlaceholderText('customer@causium.io'), {
      target: { value: 'user@company.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••••••'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in$/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
    })

    resolve!()
  })

  it('calls loginWithPasskey with email when passkey button is clicked', async () => {
    vi.stubEnv('VITE_AUTH_PASSKEY_LOGIN_ENABLED', 'true')
    loginWithPasskeyMock.mockResolvedValue(undefined)
    await renderPage()

    fireEvent.change(screen.getByPlaceholderText('customer@causium.io'), {
      target: { value: 'passkey@company.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in with passkey/i }))

    await waitFor(() => {
      expect(loginWithPasskeyMock).toHaveBeenCalledWith('passkey@company.com')
    })
  })

  it('disables passkey button when email is empty', async () => {
    vi.stubEnv('VITE_AUTH_PASSKEY_LOGIN_ENABLED', 'true')
    await renderPage()
    const btn = screen.getByRole('button', { name: /sign in with passkey/i })
    expect(btn).toBeDisabled()
    expect(loginWithPasskeyMock).not.toHaveBeenCalled()
  })

  it('shows reset success banner when ?reset=success is in URL', async () => {
    window.history.pushState({}, '', '/login?reset=success')
    await renderPage()
    expect(screen.getByText(/password updated successfully/i)).toBeInTheDocument()
    window.history.pushState({}, '', '/login')
  })

  it('shows activation success banner when ?activated=success is in URL', async () => {
    window.history.pushState({}, '', '/login?activated=success')
    await renderPage()
    expect(screen.getByText(/invite accepted successfully/i)).toBeInTheDocument()
    window.history.pushState({}, '', '/login')
  })
})
