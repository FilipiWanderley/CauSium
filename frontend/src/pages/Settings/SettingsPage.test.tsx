import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { SettingsPage } from './SettingsPage'
import { AuthContext } from '../../contexts/AuthContext'
import { I18nProvider } from '../../contexts/I18nContext'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('../../api/auth', () => ({
  authApi: {
    getTotpStatus: vi.fn().mockResolvedValue({ data: { enabled: false } }),
    getBackupCodesCount: vi.fn().mockResolvedValue({ data: { backup_codes_remaining: 5 } }),
    listPasskeys: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

const mockLogoutAll = vi.fn(() => Promise.resolve())

const user = {
  id: 'user-1',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'admin' as const,
  is_active: true,
  passkey_enabled: false,
  totp_enabled: false,
  must_change_password: false,
  created_at: '',
  org_id: 'org-1',
  org_name: 'Org',
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <MemoryRouter initialEntries={['/app/settings/security']}>
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          <AuthContext.Provider
            value={{
              user,
              isLoading: false,
              isAuthenticated: true,
              login: vi.fn(),
              loginWithPasskey: vi.fn(),
              registerCurrentPasskey: vi.fn(),
              logout: vi.fn(),
              logoutAll: mockLogoutAll,
              refreshUser: vi.fn(),
            }}
          >
            <SettingsPage />
          </AuthContext.Provider>
        </I18nProvider>
      </QueryClientProvider>
    </MemoryRouter>
  )
}

describe('SettingsPage', () => {
  it('renders global logout button and triggers action', async () => {
    renderPage()
    const btn = screen.getByText(/end all sessions/i)
    expect(btn).toBeInTheDocument()
    fireEvent.click(btn)
    await waitFor(() => expect(mockLogoutAll).toHaveBeenCalled())
  })
})
