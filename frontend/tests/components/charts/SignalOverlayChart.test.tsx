import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/app/queryClient'
import { SignalOverlayChart } from '@/components/charts/SignalOverlayChart'
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

describe('SignalOverlayChart', () => {
  it('renders ChartFrame wrapper without errors with fixture data', () => {
    render(
      <SignalOverlayChart
        ohlcv={ohlcvFixture}
        raw={rawFixture}
        position={positionFixture}
      />,
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
        <SignalOverlayChart
          ohlcv={ohlcvFixture}
          raw={rawFixture}
          position={positionFixture}
        />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
  })
})
