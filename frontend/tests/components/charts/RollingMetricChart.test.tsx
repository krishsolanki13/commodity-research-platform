import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RollingMetricChart } from '@/components/charts/RollingMetricChart'
import { mockChartInstance } from '../../setup'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

const N = 100
const mockPnl: ColumnarSeries = {
  index: Array.from({ length: N }, (_, i) => i),
  columns: { value: Array.from({ length: N }, (_, i) => (i % 3 === 0 ? 500 : -200)) },
}
const mockEquity: ColumnarSeries = {
  index: Array.from({ length: N }, (_, i) => i),
  columns: { value: Array.from({ length: N }, (_, i) => 1_000_000 + i * 100) },
}

describe('RollingMetricChart', () => {
  beforeEach(() => {
    mockChartInstance.setOption.mockClear()
  })

  it('renders with a title when valid data is provided', () => {
    render(<RollingMetricChart pnl={mockPnl} equity={mockEquity} title="Test Rolling" />)
    expect(screen.getByText('Test Rolling')).toBeInTheDocument()
  })

  it('renders without throwing when loading is true', () => {
    expect(() =>
      render(<RollingMetricChart pnl={mockPnl} equity={mockEquity} loading={true} />)
    ).not.toThrow()
  })

  it('does not throw when pnl and equity arrays are empty', () => {
    const empty: ColumnarSeries = { index: [], columns: { value: [] } }
    expect(() => render(<RollingMetricChart pnl={empty} equity={empty} />)).not.toThrow()
  })

  it('tooltip formatter includes marker HTML from CallbackDataParams', () => {
    render(<RollingMetricChart pnl={mockPnl} equity={mockEquity} title="Test Rolling" />)
    const calls = mockChartInstance.setOption.mock.calls
    expect(calls.length).toBeGreaterThan(0)
    const option = calls[calls.length - 1][0] as {
      tooltip?: { formatter?: (params: unknown) => string }
    }
    const formatter = option.tooltip?.formatter
    expect(formatter).toBeTypeOf('function')
    const marker = '<span>●</span>'
    const output = formatter!([
      {
        seriesName: 'Rolling Sharpe',
        axisValue: 1609459200000,
        value: 0.5,
        marker,
      },
    ])
    expect(output).toContain(marker)
  })
})
