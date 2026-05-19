import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../contexts/I18nContext'
import { MembersPage } from './MembersPage'

const listMembersMock = vi.fn()
const createMemberMock = vi.fn()
const listInvitesMock = vi.fn()
const createInviteMock = vi.fn()
const revokeInviteMock = vi.fn()
const resetUserMfaMock = vi.fn()
const resetUserPasswordMock = vi.fn()
const deactivateUserMock = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: 'admin-1',
      org_id: 'org-1',
      email: 'admin@company.com',
      full_name: 'Admin',
      role: 'admin',
      is_active: true,
      passkey_enabled: false,
      must_change_password: false,
      must_accept_terms: false,
      created_at: '2026-01-01T00:00:00Z',
      org_name: 'Acme',
    },
  }),
}))

vi.mock('../../api/members', () => ({
  membersApi: {
    list: (...args: unknown[]) => listMembersMock(...args),
    create: (...args: unknown[]) => createMemberMock(...args),
  },
}))

vi.mock('../../api/invites', () => ({
  invitesApi: {
    list: (...args: unknown[]) => listInvitesMock(...args),
    create: (...args: unknown[]) => createInviteMock(...args),
    revoke: (...args: unknown[]) => revokeInviteMock(...args),
  },
}))

vi.mock('../../api/admin', () => ({
  adminApi: {
    resetUserMfa: (...args: unknown[]) => resetUserMfaMock(...args),
    resetUserPassword: (...args: unknown[]) => resetUserPasswordMock(...args),
    deactivateUser: (...args: unknown[]) => deactivateUserMock(...args),
  },
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          <MembersPage />
        </I18nProvider>
      </QueryClientProvider>
    </MemoryRouter>
  )
}

describe('MembersPage UX state safety', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    listMembersMock.mockResolvedValue({
      data: {
        items: [
          {
            id: 'user-1',
            org_id: 'org-1',
            email: 'user@company.com',
            full_name: 'User One',
            role: 'viewer',
            is_active: true,
            passkey_enabled: false,
            must_change_password: false,
            created_at: '2026-01-01T00:00:00Z',
            org_name: 'Acme',
          },
        ],
      },
    })

    listInvitesMock.mockResolvedValue({
      data: {
        items: [
          {
            id: 'invite-1',
            org_id: 'org-1',
            invited_email: 'invite@company.com',
            invited_by_user_id: 'admin-1',
            role: 'viewer',
            token: 'tok-1',
            expires_at: '2026-12-31T00:00:00Z',
            accepted_at: null,
            status: 'pending',
            created_at: '2026-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 10,
        has_next: false,
      },
    })

    createMemberMock.mockResolvedValue({ data: {} })
    createInviteMock.mockResolvedValue({ data: {} })
    revokeInviteMock.mockResolvedValue({ data: {} })
    resetUserPasswordMock.mockResolvedValue({
      data: { temporary_password: 'TempPass123!', user: {} },
    })
    deactivateUserMock.mockResolvedValue({ data: {} })
  })

  it('disables member actions while reset MFA is pending', async () => {
    let resolveMfa: (() => void) | undefined
    resetUserMfaMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveMfa = () => resolve({ data: { revoked_passkeys: 2 } })
        })
    )

    renderPage()

    await screen.findByText('User One')

    fireEvent.click(screen.getByRole('button', { name: 'Reset MFA' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Resetting MFA...' })).toBeDisabled()
    })

    expect(screen.getByRole('button', { name: 'Reset Password' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Deactivate' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Invites' })).toBeDisabled()

    resolveMfa?.()
    await waitFor(() => {
      expect(screen.getByText('MFA reset completed for user@company.com. Revoked passkeys: 2.')).toBeInTheDocument()
    })
  })

  it('shows revoking state and disables invite actions while revoke is pending', async () => {
    let resolveRevoke: (() => void) | undefined
    revokeInviteMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRevoke = () => resolve({ data: {} })
        })
    )

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Invites' }))

    await screen.findByText('invite@company.com')

    fireEvent.click(screen.getByRole('button', { name: 'Revoke' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Revoking...' })).toBeDisabled()
    })

    expect(screen.getByRole('button', { name: 'Copy Link' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Members' })).toBeDisabled()

    resolveRevoke?.()
    await waitFor(() => {
      expect(screen.getByText('Invite revoked for invite@company.com.')).toBeInTheDocument()
    })
  })

  it('shows error feedback with red tone when invite creation fails', async () => {
    createInviteMock.mockRejectedValue(new Error('Invite service unavailable'))

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Invites' }))

    fireEvent.change(screen.getByPlaceholderText('member@company.com'), {
      target: { value: 'new@company.com' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Create Invite' }))

    const errorMessage = await screen.findByText('Invite service unavailable')
    expect(errorMessage).toBeInTheDocument()
    expect(errorMessage.closest('div')).toHaveClass('text-red-700')
    expect(errorMessage.closest('div')).toHaveClass('bg-red-50')
  })

  it('disables tab switch while create member is pending', async () => {
    let resolveCreateMember: (() => void) | undefined
    createMemberMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreateMember = () => resolve({ data: {} })
        })
    )

    renderPage()

    fireEvent.change(screen.getByPlaceholderText('member@company.com'), {
      target: { value: 'person@company.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('Full name'), {
      target: { value: 'Person Test' },
    })
    fireEvent.change(screen.getByPlaceholderText('Temporary password'), {
      target: { value: 'StrongPass123!' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Create Member' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Creating...' })).toBeDisabled()
    })

    expect(screen.getByRole('button', { name: 'Invites' })).toBeDisabled()

    resolveCreateMember?.()
    await waitFor(() => {
      expect(screen.getByText('Member created successfully.')).toBeInTheDocument()
    })
  })

  it('disables invite filters and pagination while create invite is pending', async () => {
    let resolveCreateInvite: (() => void) | undefined
    createInviteMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreateInvite = () =>
            resolve({
              data: {
                invited_email: 'new@company.com',
                token: 'tok-new',
              },
            })
        })
    )

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Invites' }))

    fireEvent.change(screen.getByPlaceholderText('member@company.com'), {
      target: { value: 'new@company.com' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Create Invite' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Creating...' })).toBeDisabled()
    })

    expect(screen.getByPlaceholderText('Search by invited email')).toBeDisabled()
    expect(screen.getByDisplayValue('All')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Prev' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()

    resolveCreateInvite?.()
    await waitFor(() => {
      expect(screen.getByText(/Invite created for new@company.com./)).toBeInTheDocument()
    })
  })
})
