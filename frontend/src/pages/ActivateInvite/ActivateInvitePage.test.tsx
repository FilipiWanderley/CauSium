import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ActivateInvitePage } from './ActivateInvitePage'

const previewMock = vi.fn()
const acceptMock = vi.fn()
const navigateMock = vi.fn()

vi.mock('../../api/invites', () => ({
  invitesApi: {
    preview: (...args: unknown[]) => previewMock(...args),
    accept: (...args: unknown[]) => acceptMock(...args),
  },
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

vi.mock('lucide-react', () => ({
  Cloud: () => null,
  ArrowLeft: () => null,
}))

const PENDING_PREVIEW = {
  org_name: 'Acme',
  invited_email: 'new@acme.com',
  role: 'viewer',
  status: 'pending',
}

function renderPage(token = 'tok-valid') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/activate?token=${token}`]}>
        <Routes>
          <Route path="/activate" element={<ActivateInvitePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ActivateInvitePage', () => {
  beforeEach(() => {
    previewMock.mockReset()
    acceptMock.mockReset()
    navigateMock.mockReset()
    previewMock.mockResolvedValue({ data: PENDING_PREVIEW })
  })

  it('renders invite preview after token resolves', async () => {
    renderPage()
    expect(await screen.findByText('Acme')).toBeInTheDocument()
    expect(screen.getByText('new@acme.com')).toBeInTheDocument()
    expect(screen.getByText('viewer')).toBeInTheDocument()
  })

  it('submit button is disabled until terms are accepted', async () => {
    renderPage()
    await screen.findByText('Acme')

    const submitBtn = screen.getByRole('button', { name: /ativar acesso/i })
    // Without terms checkbox, button is disabled
    expect(submitBtn).toBeDisabled()

    fireEvent.click(screen.getByRole('checkbox'))
    // Terms accepted + pending invite + valid token → enabled (name/password validated on submit)
    expect(submitBtn).not.toBeDisabled()
  })

  it('shows error when terms not accepted on submit attempt', async () => {
    renderPage()
    await screen.findByText('Acme')

    fireEvent.change(screen.getByPlaceholderText('Seu nome'), {
      target: { value: 'New User' },
    })
    fireEvent.change(screen.getByPlaceholderText('Min. 8 caracteres'), {
      target: { value: 'Password1!' },
    })
    fireEvent.change(screen.getByPlaceholderText('Repita a senha'), {
      target: { value: 'Password1!' },
    })
    // Don't check terms — submit via form
    const form = screen.getByRole('button', { name: /ativar acesso/i }).closest('form')!
    fireEvent.submit(form)

    expect(await screen.findByText(/você precisa aceitar os termos/i)).toBeInTheDocument()
    expect(acceptMock).not.toHaveBeenCalled()
  })

  it('calls invitesApi.accept with terms_accepted: true and navigates on success', async () => {
    acceptMock.mockResolvedValue({ data: {} })
    renderPage()
    await screen.findByText('Acme')

    fireEvent.change(screen.getByPlaceholderText('Seu nome'), {
      target: { value: 'New User' },
    })
    fireEvent.change(screen.getByPlaceholderText('Min. 8 caracteres'), {
      target: { value: 'Password1!' },
    })
    fireEvent.change(screen.getByPlaceholderText('Repita a senha'), {
      target: { value: 'Password1!' },
    })
    fireEvent.click(screen.getByRole('checkbox'))

    const submitBtn = screen.getByRole('button', { name: /ativar acesso/i })
    expect(submitBtn).not.toBeDisabled()
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(acceptMock).toHaveBeenCalledWith(
        'tok-valid',
        expect.objectContaining({ terms_accepted: true, full_name: 'New User' })
      )
    })
    expect(navigateMock).toHaveBeenCalledWith('/login?activated=success', { replace: true })
  })

  it('shows password mismatch error', async () => {
    renderPage()
    await screen.findByText('Acme')

    fireEvent.change(screen.getByPlaceholderText('Seu nome'), { target: { value: 'New User' } })
    fireEvent.change(screen.getByPlaceholderText('Min. 8 caracteres'), {
      target: { value: 'Password1!' },
    })
    fireEvent.change(screen.getByPlaceholderText('Repita a senha'), {
      target: { value: 'Different1!' },
    })
    fireEvent.click(screen.getByRole('checkbox'))

    const form = screen.getByRole('button', { name: /ativar acesso/i }).closest('form')!
    fireEvent.submit(form)

    expect(await screen.findByText(/senhas nao coincidem/i)).toBeInTheDocument()
    expect(acceptMock).not.toHaveBeenCalled()
  })

  it('shows API error message on accept failure', async () => {
    acceptMock.mockRejectedValue({
      response: { data: { detail: 'Token expired or invalid.' } },
    })
    renderPage()
    await screen.findByText('Acme')

    fireEvent.change(screen.getByPlaceholderText('Seu nome'), { target: { value: 'New User' } })
    fireEvent.change(screen.getByPlaceholderText('Min. 8 caracteres'), {
      target: { value: 'Password1!' },
    })
    fireEvent.change(screen.getByPlaceholderText('Repita a senha'), {
      target: { value: 'Password1!' },
    })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: /ativar acesso/i }))

    expect(await screen.findByText('Token expired or invalid.')).toBeInTheDocument()
  })

  it('disables submit for non-pending invite status', async () => {
    previewMock.mockResolvedValue({
      data: { ...PENDING_PREVIEW, status: 'expired' },
    })
    renderPage()
    await screen.findByText('Invite expired')

    expect(screen.getByRole('button', { name: /ativar acesso/i })).toBeDisabled()
  })
})
