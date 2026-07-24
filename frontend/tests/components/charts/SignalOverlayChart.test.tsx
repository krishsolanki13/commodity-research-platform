import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
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
  series?: Array<{ name?: string; tooltip?: { show?: boolean } }>
} {
  const calls = mockChartInstance.setOption.mock.calls
  expect(calls.length).toBeGreaterThan(0)
  return calls[calls.length - 1][0] as {
    series?: Array<{ name?: string; tooltip?: { show?: boolean } }>
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

  it('position series tooltip is suppressed', () => {
    render(
      <SignalOverlayChart ohlcv={ohlcvFixture} raw={rawFixture} position={positionFixture} />,
      { wrapper: Wrapper }
    )
    const option = lastChartOption()
    const position = option.series?.find((s) => s.name === 'Position')
    expect(position?.tooltip?.show).toBe(false)
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

  it('position pane has non-zero Long/Short values and yAxis padding beyond clipping range', () => {
    const mixedPosition: ColumnarSeries = {
      index: [1609459200000, 1609545600000, 1609632000000],
      columns: { position: [1, -1, 1] },
    }
    render(
      <SignalOverlayChart ohlcv={ohlcvFixture} raw={rawFixture} position={mixedPosition} />,
      { wrapper: Wrapper }
    )
    const option = lastChartOption() as {
      series?: Array<{ name?: string; data?: (number | null)[] }>
      yAxis?: Array<{ min?: number | null; max?: number | null }>
    }
    const position = option.series?.find((s) => s.name === 'Position')
    expect(position?.data).toBeDefined()
    const values = (position?.data ?? []).filter((v): v is number => typeof v === 'number')
    expect(values.some((v) => v !== 0)).toBe(true)
    expect(values).toContain(1)
    expect(values).toContain(-1)
    const posAxis = option.yAxis?.[2]
    expect(posAxis?.min).toBe(-1.5)
    expect(posAxis?.max).toBe(1.5)
  })
})
