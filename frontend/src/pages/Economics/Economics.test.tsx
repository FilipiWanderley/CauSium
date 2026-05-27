import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { I18nProvider } from '../../contexts/I18nContext'
import { EconomicsSkusPage } from '../EconomicsSkus/EconomicsSkusPage'
import { EconomicsReportsPage } from '../EconomicsReports/EconomicsReportsPage'

const mockTopServicesPaginated = vi.fn()
const mockCostTrend = vi.fn()
const mockDashboard = vi.fn()
const mockReservationCoverage = vi.fn()
const mockTopTeamsPaginated = vi.fn()
const mockSubscriptionCostSummary = vi.fn()
const mockDetailedCosts = vi.fn()
const mockReservationEfficiency = vi.fn()

vi.mock('../../api/ledger', () => ({
  ledgerApi: {
    topServicesPaginated: (...args: unknown[]) => mockTopServicesPaginated(...args),
    costTrend: (...args: unknown[]) => mockCostTrend(...args),
    dashboard: (...args: unknown[]) => mockDashboard(...args),
    reservationCoverage: (...args: unknown[]) => mockReservationCoverage(...args),
    subscriptionCostSummary: (...args: unknown[]) => mockSubscriptionCostSummary(...args),
    detailedCosts: (...args: unknown[]) => mockDetailedCosts(...args),
    reservationEfficiency: (...args: unknown[]) => mockReservationEfficiency(...args),
    topTeamsPaginated: (...args: unknown[]) => mockTopTeamsPaginated(...args),
    createExportJob: vi.fn(),
    getExportJob: vi.fn(),
    downloadExportUrl: vi.fn(() => '#'),
  },
}))

vi.mock('../../api/economics', () => ({
  economicsApi: {
    createReportExport: vi.fn(),
    getReportExport: vi.fn(() => Promise.resolve({ data: null })),
    downloadReportExport: vi.fn(),
  },
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
    },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          {children}
        </I18nProvider>
      </QueryClientProvider>
    )
  }
}

describe('EconomicsSkusPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows skeleton loading state initially', () => {
    mockTopServicesPaginated.mockReturnValue(new Promise(() => {}))

    const { container } = render(<EconomicsSkusPage />, { wrapper: createWrapper() })
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('shows error state when query fails', async () => {
    mockTopServicesPaginated.mockRejectedValue(new Error('Network error'))

    render(<EconomicsSkusPage />, { wrapper: createWrapper() })

    // Component has retry: 2, so wait for retries to exhaust
    await waitFor(
      () => {
        expect(screen.getByText('Reset')).toBeInTheDocument()
      },
      { timeout: 5000 },
    )
  })

  it('shows empty state when no data', async () => {
    mockTopServicesPaginated.mockResolvedValue({ data: { items: [] } })

    render(<EconomicsSkusPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('No SKU data available for the selected window.')).toBeInTheDocument()
    })
  })

  it('renders table when data is available', async () => {
    mockTopServicesPaginated.mockResolvedValue({
      data: {
        items: [
          { service: 'Virtual Machines', cost_usd: 5000, percentage: 45.2 },
          { service: 'Storage', cost_usd: 2000, percentage: 18.1 },
        ],
      },
    })

    render(<EconomicsSkusPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Virtual Machines')).toBeInTheDocument()
      expect(screen.getByText('Storage')).toBeInTheDocument()
    })
  })
})

describe('EconomicsReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    mockDashboard.mockReturnValue(new Promise(() => {}))
    mockTopServicesPaginated.mockReturnValue(new Promise(() => {}))
    mockTopTeamsPaginated.mockReturnValue(new Promise(() => {}))

    render(<EconomicsReportsPage />, { wrapper: createWrapper() })
    expect(screen.getAllByText('Loading...').length).toBeGreaterThan(0)
  })

  it('shows fallback values when queries fail', async () => {
    mockDashboard.mockRejectedValue(new Error('fail'))
    mockTopServicesPaginated.mockRejectedValue(new Error('fail'))
    mockTopTeamsPaginated.mockRejectedValue(new Error('fail'))

    render(<EconomicsReportsPage />, { wrapper: createWrapper() })

    await waitFor(
      () => {
        expect(screen.getAllByText('R$ 0').length).toBeGreaterThan(0)
      },
      { timeout: 5000 },
    )
  })

  it('renders metric cards when data loads', async () => {
    mockDashboard.mockResolvedValue({
      data: { current_month_cost: 10000, previous_month_cost: 9000, mom_change_pct: 11.1, currency: 'USD' },
    })
    mockTopServicesPaginated.mockResolvedValue({ data: { items: [] } })
    mockTopTeamsPaginated.mockResolvedValue({ data: { items: [] } })

    render(<EconomicsReportsPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('R$ 10.000')).toBeInTheDocument()
    })
  })
})
