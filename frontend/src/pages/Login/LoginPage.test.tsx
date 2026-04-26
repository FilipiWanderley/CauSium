import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

const loginMock = vi.fn()
const loginWithPasskeyMock = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    login: loginMock,
    loginWithPasskey: loginWithPasskeyMock,
    isAuthenticated: false,
  }),
}))

// lucide-react SVG icons fail in jsdom — stub them
vi.mock('lucide-react', () => ({
  Cloud: () => null,
}))

async function renderPage(search = '') {
  const { LoginPage } = await import('./LoginPage')
  return render(
    <MemoryRouter initialEntries={[`/login${search}`]}>
      <LoginPage />
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
    expect(screen.getByPlaceholderText('you@company.com')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in$/i })).toBeInTheDocument()
  })

  it('calls login with email and password on submit', async () => {
    loginMock.mockResolvedValue(undefined)
    await renderPage()

    fireEvent.change(screen.getByPlaceholderText('you@company.com'), {
      target: { value: 'user@company.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'secret123' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in$/i }))

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith('user@company.com', 'secret123')
    })
  })

  it('shows error message on login failure', async () => {
    loginMock.mockRejectedValue(new Error('401'))
    await renderPage()

    fireEvent.change(screen.getByPlaceholderText('you@company.com'), {
      target: { value: 'bad@company.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'wrongpass' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in$/i }))

    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument()
  })

  it('disables submit button while loading', async () => {
    let resolve!: (value?: unknown) => void
    loginMock.mockImplementation(() => new Promise((r) => { resolve = r }))
    await renderPage()

    fireEvent.change(screen.getByPlaceholderText('you@company.com'), {
      target: { value: 'user@company.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
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

    fireEvent.change(screen.getByPlaceholderText('you@company.com'), {
      target: { value: 'passkey@company.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in with passkey/i }))

    await waitFor(() => {
      expect(loginWithPasskeyMock).toHaveBeenCalledWith('passkey@company.com')
    })
  })

  it('shows error when passkey is clicked without email', async () => {
    vi.stubEnv('VITE_AUTH_PASSKEY_LOGIN_ENABLED', 'true')
    await renderPage()
    fireEvent.click(screen.getByRole('button', { name: /sign in with passkey/i }))
    expect(await screen.findByText(/informe seu e-mail/i)).toBeInTheDocument()
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
