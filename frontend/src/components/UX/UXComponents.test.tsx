import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { EmptyState } from '../../components/UX/EmptyState'
import { ErrorState } from '../../components/UX/ErrorState'
import { ErrorBoundary } from '../../components/UX/ErrorBoundary'
import { SessionExpired } from '../../components/UX/SessionExpired'
import { StatusBadge } from '../../components/UX/StatusBadge'
import { SkeletonLine, SkeletonCard, SkeletonTable, SkeletonMetricCards, SkeletonPrioritizedList } from '../../components/UX/Skeleton'

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No data" description="Nothing to show here" />)
    expect(screen.getByText('No data')).toBeInTheDocument()
    expect(screen.getByText('Nothing to show here')).toBeInTheDocument()
  })

  it('renders action button and calls onClick', () => {
    const onClick = vi.fn()
    render(<EmptyState title="Empty" action={{ label: 'Retry', onClick }} />)
    const button = screen.getByText('Retry')
    expect(button).toBeInTheDocument()
    fireEvent.click(button)
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('renders without action when not provided', () => {
    render(<EmptyState title="Empty" />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})

describe('ErrorState', () => {
  it('renders title and description', () => {
    render(<ErrorState title="Error occurred" description="Something broke" />)
    expect(screen.getByText('Error occurred')).toBeInTheDocument()
    expect(screen.getByText('Something broke')).toBeInTheDocument()
  })

  it('renders retry button and calls onRetry', () => {
    const onRetry = vi.fn()
    render(<ErrorState title="Error" onRetry={onRetry} retryLabel="Try again" />)
    const button = screen.getByText('Try again')
    fireEvent.click(button)
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders compact variant', () => {
    render(<ErrorState title="Error" compact />)
    expect(screen.getByText('Error')).toBeInTheDocument()
  })

  it('does not render retry button when onRetry is not provided', () => {
    render(<ErrorState title="Error" />)
    expect(screen.queryByText('Try again')).not.toBeInTheDocument()
  })
})

describe('StatusBadge', () => {
  it('renders with status variant', () => {
    render(<StatusBadge variant="status" value="open" label="Open" />)
    expect(screen.getByText('Open')).toBeInTheDocument()
  })

  it('renders with risk variant', () => {
    render(<StatusBadge variant="risk" value="high" label="High Risk" />)
    expect(screen.getByText('High Risk')).toBeInTheDocument()
  })

  it('renders with confidence variant', () => {
    render(<StatusBadge variant="confidence" value="medium" />)
    expect(screen.getByText('medium')).toBeInTheDocument()
  })

  it('renders with effort variant', () => {
    render(<StatusBadge variant="effort" value="low" label="Low Effort" />)
    expect(screen.getByText('Low Effort')).toBeInTheDocument()
  })

  it('uses value as display text when label is not provided', () => {
    render(<StatusBadge variant="risk" value="low" />)
    expect(screen.getByText('low')).toBeInTheDocument()
  })
})

describe('Skeleton components', () => {
  it('renders SkeletonLine', () => {
    const { container } = render(<SkeletonLine />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders SkeletonCard', () => {
    const { container } = render(<SkeletonCard />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders SkeletonTable with correct number of rows', () => {
    const { container } = render(<SkeletonTable rows={3} columns={4} />)
    const rows = container.querySelectorAll('tbody tr')
    expect(rows.length).toBe(3)
  })

  it('renders SkeletonMetricCards with correct count', () => {
    const { container } = render(<SkeletonMetricCards count={3} />)
    const cards = container.querySelectorAll('.animate-pulse')
    expect(cards.length).toBeGreaterThanOrEqual(3)
  })

  it('renders SkeletonPrioritizedList', () => {
    const { container } = render(<SkeletonPrioritizedList items={4} />)
    const items = container.querySelectorAll('.divide-y > div')
    expect(items.length).toBe(4)
  })
})

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <p>Hello world</p>
      </ErrorBoundary>
    )
    expect(screen.getByText('Hello world')).toBeInTheDocument()
  })

  it('renders fallback UI when child throws', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    function Bomb(): JSX.Element {
      throw new Error('Boom')
    }
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText(/your data is safe/i)).toBeInTheDocument()
    expect(screen.getByText('Reload page')).toBeInTheDocument()
    expect(screen.getByText(/decision support mode/i)).toBeInTheDocument()
    spy.mockRestore()
  })

  it('renders custom fallback title and description', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    function Bomb(): JSX.Element {
      throw new Error('Boom')
    }
    render(
      <ErrorBoundary fallbackTitle="Custom title" fallbackDescription="Custom desc">
        <Bomb />
      </ErrorBoundary>
    )
    expect(screen.getByText('Custom title')).toBeInTheDocument()
    expect(screen.getByText('Custom desc')).toBeInTheDocument()
    spy.mockRestore()
  })
})

describe('SessionExpired', () => {
  it('renders session expired message with sign-in button', () => {
    render(<SessionExpired />)
    expect(screen.getByText('Session expired')).toBeInTheDocument()
    expect(screen.getByText(/please sign in again/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByText(/decision support system/i)).toBeInTheDocument()
  })

  it('renders custom title and description', () => {
    render(<SessionExpired title="Custom expired" description="Custom message" />)
    expect(screen.getByText('Custom expired')).toBeInTheDocument()
    expect(screen.getByText('Custom message')).toBeInTheDocument()
  })
})
