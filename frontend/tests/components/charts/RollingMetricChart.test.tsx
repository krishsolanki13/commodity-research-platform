import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RollingMetricChart } from '@/components/charts/RollingMetricChart'
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
})
