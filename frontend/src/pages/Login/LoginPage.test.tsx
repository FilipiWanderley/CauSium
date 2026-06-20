import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../contexts/I18nContext'

// Mock do useAuth - definido antes de qualquer import
const mockLogin = vi.fn()
const mockIsAuthenticated = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    isAuthenticated: mockIsAuthenticated(),
  }),
}))

vi.mock('lucide-react', () => ({
  Eye: () => 'EyeIcon',
  EyeOff: () => 'EyeOffIcon',
}))

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockIsAuthenticated.mockReturnValue(false)
  })

  it('renders login form elements', async () => {
    const { LoginPage } = await import('./LoginPage')
    render(
      <MemoryRouter>
        <I18nProvider>
          <LoginPage />
        </I18nProvider>
      </MemoryRouter>
    )

    // Verifica se os campos estão presentes
    expect(screen.getByPlaceholderText('customer@causium.io')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••••••')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in$/i })).toBeInTheDocument()
  })

  it('renders brand logo and tagline', async () => {
    const { LoginPage } = await import('./LoginPage')
    render(
      <MemoryRouter>
        <I18nProvider>
          <LoginPage />
        </I18nProvider>
      </MemoryRouter>
    )

    // Logo aparece duas vezes (desktop e mobile), usamos getAllByText
    expect(screen.getAllByText(/CauSium/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/govern cloud with confidence/i)).toBeInTheDocument()
  })

  it('calls login with email and password on submit', async () => {
    mockLogin.mockResolvedValue(undefined)
    const { LoginPage } = await import('./LoginPage')
    render(
      <MemoryRouter>
        <I18nProvider>
          <LoginPage />
        </I18nProvider>
      </MemoryRouter>
    )

    const emailInput = screen.getByPlaceholderText('customer@causium.io')
    const passwordInput = screen.getByPlaceholderText('••••••••••••')
    const submitButton = screen.getByRole('button', { name: /sign in$/i })

    fireEvent.change(emailInput, { target: { value: 'user@company.com' } })
    fireEvent.change(passwordInput, { target: { value: 'secret123' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('user@company.com', 'secret123')
    })
  })

  it('shows error message on login failure', async () => {
    mockLogin.mockRejectedValue({ response: { status: 401 } })
    const { LoginPage } = await import('./LoginPage')
    render(
      <MemoryRouter>
        <I18nProvider>
          <LoginPage />
        </I18nProvider>
      </MemoryRouter>
    )

    const emailInput = screen.getByPlaceholderText('customer@causium.io')
    const passwordInput = screen.getByPlaceholderText('••••••••••••')
    const submitButton = screen.getByRole('button', { name: /sign in$/i })

    fireEvent.change(emailInput, { target: { value: 'bad@company.com' } })
    fireEvent.change(passwordInput, { target: { value: 'wrongpass' } })
    fireEvent.click(submitButton)

    expect(await screen.findByText(/invalid email or password/i)).toBeInTheDocument()
  })

  it('disables submit button while loading', async () => {
    let resolve!: () => void
    mockLogin.mockImplementation(() => new Promise((r) => { resolve = r as () => void }))
    const { LoginPage } = await import('./LoginPage')
    render(
      <MemoryRouter>
        <I18nProvider>
          <LoginPage />
        </I18nProvider>
      </MemoryRouter>
    )

    const emailInput = screen.getByPlaceholderText('customer@causium.io')
    const passwordInput = screen.getByPlaceholderText('••••••••••••')
    const submitButton = screen.getByRole('button', { name: /sign in$/i })

    fireEvent.change(emailInput, { target: { value: 'user@company.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
    })

    resolve()
  })

  it('shows Forgot password link', async () => {
    const { LoginPage } = await import('./LoginPage')
    render(
      <MemoryRouter>
        <I18nProvider>
          <LoginPage />
        </I18nProvider>
      </MemoryRouter>
    )

    const link = screen.getByRole('link', { name: /forgot password/i })
    expect(link).toHaveAttribute('href', '/forgot-password')
  })

  it('does NOT render Passkey button', async () => {
    const { LoginPage } = await import('./LoginPage')
    render(
      <MemoryRouter>
        <I18nProvider>
          <LoginPage />
        </I18nProvider>
      </MemoryRouter>
    )

    expect(screen.queryByRole('button', { name: /passkey/i })).not.toBeInTheDocument()
  })

  it('does NOT render Microsoft login button', async () => {
    const { LoginPage } = await import('./LoginPage')
    render(
      <MemoryRouter>
        <I18nProvider>
          <LoginPage />
        </I18nProvider>
      </MemoryRouter>
    )

    expect(screen.queryByRole('button', { name: /microsoft/i })).not.toBeInTheDocument()
  })
})
