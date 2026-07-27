import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/app/queryClient'
import { PriceChart } from '@/components/charts/PriceChart'
import { mockChartInstance } from '../../setup'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

// 5-bar Gold fixture
const goldOhlcv: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000, 1609718400000, 1609804800000],
  columns: {
    open: [1898.0, 1902.5, 1910.0, 1905.0, 1915.0],
    high: [1908.0, 1915.0, 1918.0, 1912.0, 1925.0],
    low: [1892.0, 1898.0, 1903.0, 1900.0, 1908.0],
    close: [1902.5, 1910.0, 1905.0, 1910.0, 1920.0],
    volume: [12000, 14500, 11000, 13200, 15800],
  },
}

// Fixture with a null bar to verify gap handling (no throw, no interpolation)
const ohlcvWithNull: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000],
  columns: {
    open: [1898.0, null, 1910.0],
    high: [1908.0, null, 1918.0],
    low: [1892.0, null, 1903.0],
    close: [1902.5, null, 1905.0],
    volume: [12000, null, 11000],
  },
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('PriceChart', () => {
  beforeEach(() => {
    mockChartInstance.setOption.mockClear()
  })

  it('renders without errors with Gold OHLCV fixture', () => {
    render(<PriceChart ohlcv={goldOhlcv} height={300} />, { wrapper: Wrapper })
    expect(document.body).not.toBeEmptyDOMElement()
  })

  it('does not throw when ohlcv contains null values', () => {
    expect(() =>
      render(<PriceChart ohlcv={ohlcvWithNull} height={300} />, { wrapper: Wrapper })
    ).not.toThrow()
  })

  it('passes loading state through to ChartFrame', () => {
    render(<PriceChart ohlcv={goldOhlcv} height={300} loading={true} />, { wrapper: Wrapper })
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })

  it('renders with overlay series without errors', () => {
    const overlay = {
      spec: {
        indicator_name: 'ema',
        params: { period: 50 },
        column_name: 'ema_50',
        asset: 'gold',
        computed_at: '2026-01-01T00:00:00Z',
      },
      values: [1900.0, 1905.0, 1908.0, 1910.0, 1915.0],
    }
    expect(() =>
      render(<PriceChart ohlcv={goldOhlcv} overlays={[overlay]} height={300} />, {
        wrapper: Wrapper,
      })
    ).not.toThrow()
  })

  it('volume series is named Volume', () => {
    render(<PriceChart ohlcv={goldOhlcv} height={300} volume={true} />, { wrapper: Wrapper })
    const calls = mockChartInstance.setOption.mock.calls
    expect(calls.length).toBeGreaterThan(0)
    const option = calls[calls.length - 1][0] as {
      series?: Array<{ name?: string }>
    }
    const volume = option.series?.find((s) => s.name === 'Volume')
    expect(volume).toBeDefined()
  })
})
