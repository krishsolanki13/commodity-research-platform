import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/app/queryClient'
import { EquityCurveChart } from '@/components/charts/EquityCurveChart'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

const equityFixture: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000, 1609718400000],
  columns: { value: [1000000, 1005000, 1003000, 1010000] },
}

const drawdownFixture: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000, 1609718400000],
  columns: { value: [0, -0.002, -0.003, 0] },
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('EquityCurveChart', () => {
  it('renders without errors with equity series', () => {
    expect(() =>
      render(
        <EquityCurveChart equity={equityFixture} baseline={1000000} height={300} />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
  })

  it('renders with drawdown pane without errors', () => {
    expect(() =>
      render(
        <EquityCurveChart
          equity={equityFixture}
          drawdown={drawdownFixture}
          baseline={1000000}
          height={400}
        />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
  })

  it('renders compare mode with two series without errors', () => {
    const compareFixture = {
      name: 'EMA 20/100 Gold',
      equity: {
        index: equityFixture.index,
        columns: { value: [1000000, 1002000, 1001000, 1008000] },
      },
    }
    expect(() =>
      render(
        <EquityCurveChart
          equity={equityFixture}
          compare={[compareFixture]}
          height={300}
        />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
  })
})
