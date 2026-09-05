import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/app/queryClient'
import { SignalOverlayChart } from '@/components/charts/SignalOverlayChart'
import { mockChartInstance } from '../../setup'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

const ohlcvFixture: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000],
  columns: {
    open: [1800, 1810, 1805],
    high: [1820, 1825, 1815],
    low: [1795, 1800, 1798],
    close: [1810, 1805, 1812],
  },
}

const rawFixture: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000],
  columns: { raw: [0.5, null, 0.8] },
}

const positionFixture: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000],
  columns: { position: [1, 0, 1] },
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

function lastChartOption(): {
  series?: Array<{ name?: string; tooltip?: { show?: boolean }; markArea?: { data?: unknown[] } }>
  yAxis?: Array<{ min?: number | null; max?: number | null; gridIndex?: number }>
} {
  const calls = mockChartInstance.setOption.mock.calls
  expect(calls.length).toBeGreaterThan(0)
  return calls[calls.length - 1][0] as {
    series?: Array<{ name?: string; tooltip?: { show?: boolean }; markArea?: { data?: unknown[] } }>
    yAxis?: Array<{ min?: number | null; max?: number | null; gridIndex?: number }>
  }
}

describe('SignalOverlayChart', () => {
  beforeEach(() => {
    mockChartInstance.setOption.mockClear()
  })

  it('signal series is named Signal', () => {
    render(
      <SignalOverlayChart ohlcv={ohlcvFixture} raw={rawFixture} position={positionFixture} />,
      { wrapper: Wrapper }
    )
    const option = lastChartOption()
    const signal = option.series?.find((s) => s.name === 'Signal')
    expect(signal).toBeDefined()
  })

  it('position series is removed — markArea used instead of dedicated pane', () => {
    render(
      <SignalOverlayChart ohlcv={ohlcvFixture} raw={rawFixture} position={positionFixture} />,
      { wrapper: Wrapper }
    )
    const option = lastChartOption()
    const position = option.series?.find((s) => s.name === 'Position')
    expect(position).toBeUndefined()
  })

  it('renders ChartFrame wrapper without errors with fixture data', () => {
    render(
      <SignalOverlayChart ohlcv={ohlcvFixture} raw={rawFixture} position={positionFixture} />,
      { wrapper: Wrapper }
    )
    expect(document.body).not.toBeEmptyDOMElement()
  })

  it('passes loading state through to ChartFrame', () => {
    render(
      <SignalOverlayChart
        ohlcv={ohlcvFixture}
        raw={rawFixture}
        position={positionFixture}
        loading={true}
      />,
      { wrapper: Wrapper }
    )
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })

  it('does not throw when raw signal contains null values', () => {
    expect(() =>
      render(
        <SignalOverlayChart ohlcv={ohlcvFixture} raw={rawFixture} position={positionFixture} />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
  })

  it('markArea bands are on signal series only — candlestick has no markArea', () => {
    const mixedPosition: ColumnarSeries = {
      index: [1609459200000, 1609545600000, 1609632000000],
      columns: { position: [1, -1, 1] },
    }
    render(
      <SignalOverlayChart ohlcv={ohlcvFixture} raw={rawFixture} position={mixedPosition} />,
      { wrapper: Wrapper }
    )
    const option = lastChartOption()
    const candlestick = option.series?.find((s) => s.name !== 'Signal')
    const signal = option.series?.find((s) => s.name === 'Signal')
    // Price pane: candlestick must have NO markArea (no background tints)
    expect(candlestick?.markArea).toBeUndefined()
    // Signal pane: signal series must have markArea with Long/Short band data
    expect(signal?.markArea).toBeDefined()
    expect(Array.isArray(signal?.markArea?.data)).toBe(true)
    expect((signal?.markArea?.data ?? []).length).toBeGreaterThan(0)
  })

  it('chart uses two-pane layout — only two yAxis entries', () => {
    render(
      <SignalOverlayChart ohlcv={ohlcvFixture} raw={rawFixture} position={positionFixture} />,
      { wrapper: Wrapper }
    )
    const option = lastChartOption()
    expect(option.yAxis?.length).toBe(2)
  })

  it('does not call setOption when ohlcv lacks OHLC columns (raw_signal fallback)', () => {
    const signalOnlyOhlcv: ColumnarSeries = {
      index: [1609459200000, 1609545600000],
      columns: { raw: [0.5, -0.3] },
    }
    expect(() =>
      render(
        <SignalOverlayChart
          ohlcv={signalOnlyOhlcv}
          raw={rawFixture}
          position={positionFixture}
        />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
    expect(mockChartInstance.setOption).not.toHaveBeenCalled()
    expect(screen.getByText(/No chart data for this window/i)).toBeInTheDocument()
  })
})
