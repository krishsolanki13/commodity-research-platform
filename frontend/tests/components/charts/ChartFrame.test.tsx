import { describe, it, expect, vi } from 'vitest'
import { useEffect } from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/app/queryClient'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { ApiClientError } from '@/api/client'
import { mockChartInstance } from '../../setup'

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ChartFrame', () => {
  it('renders LoadingSkeleton when loading=true — children not rendered', () => {
    render(
      <ChartFrame height={300} loading={true}>
        <div data-testid="chart-content">content</div>
      </ChartFrame>,
      { wrapper: Wrapper }
    )
    expect(screen.queryByTestId('chart-content')).not.toBeInTheDocument()
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })

  it('renders ErrorState when error prop provided', () => {
    const error = new ApiClientError({
      code: 'NOT_FOUND',
      message: 'Data unavailable.',
      status: 404,
    })
    render(
      <ChartFrame height={300} error={error} onRetry={vi.fn()}>
        <div>content</div>
      </ChartFrame>,
      { wrapper: Wrapper }
    )
    expect(screen.getByText('Data unavailable.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('renders EmptyState when empty prop provided', () => {
    render(
      <ChartFrame height={300} empty={{ message: 'No price data for this range.' }}>
        <div>content</div>
      </ChartFrame>,
      { wrapper: Wrapper }
    )
    expect(screen.getByText('No price data for this range.')).toBeInTheDocument()
  })

  it('renders children in data state (no loading/error/empty)', () => {
    render(
      <ChartFrame height={300}>
        <div data-testid="chart-content">ECharts goes here</div>
      </ChartFrame>,
      { wrapper: Wrapper }
    )
    expect(screen.getByTestId('chart-content')).toBeInTheDocument()
  })

  it('calls echarts.connect with syncGroup when a chart instance registers', async () => {
    const { echarts } = await import('@/lib/echarts-setup')
    vi.clearAllMocks()

    // Minimal child that registers itself via ChartFrameContext
    function MockChart() {
      const ctx = useChartFrame()
      useEffect(() => {
        ctx?.onChartReady(mockChartInstance as never)
      }, [ctx])
      return <div data-testid="mock-chart" />
    }

    render(
      <ChartFrame height={300} syncGroup="test-group">
        <MockChart />
      </ChartFrame>,
      { wrapper: Wrapper }
    )

    await screen.findByTestId('mock-chart')
    expect(echarts.connect).toHaveBeenCalledWith('test-group')
  })

  it('export button is present in toolbar (default toolbar=true)', () => {
    render(
      <ChartFrame height={300} title="Gold Price">
        <div />
      </ChartFrame>,
      { wrapper: Wrapper }
    )
    expect(screen.getByRole('button', { name: /export chart as png/i })).toBeInTheDocument()
  })
})
