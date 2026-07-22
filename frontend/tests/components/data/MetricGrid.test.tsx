import { render, screen } from '@testing-library/react'
import { describe, test, expect } from 'vitest'
import { MetricGrid } from '@/components/data/MetricGrid'

const metrics = [
  { label: 'SHARPE', value: 0.3, format: 'ratio' as const },
  { label: 'MAX DD', value: -0.068, format: 'drawdown' as const },
  { label: 'TOTAL RETURN', value: 0.18, format: 'percent' as const },
]

describe('MetricGrid', () => {
  test('renders correct number of metric labels', () => {
    render(<MetricGrid metrics={metrics} columns={3} />)
    expect(screen.getByText('SHARPE')).toBeInTheDocument()
    expect(screen.getByText('MAX DD')).toBeInTheDocument()
    expect(screen.getByText('TOTAL RETURN')).toBeInTheDocument()
  })

  test('renders LoadingSkeleton when loading=true', () => {
    const { container } = render(<MetricGrid metrics={[]} loading={true} />)
    expect(container.querySelector('[data-variant="metric-grid"]')).toBeInTheDocument()
  })

  test('6-column grid renders all metrics', () => {
    const sixMetrics = Array.from({ length: 6 }, (_, i) => ({
      label: `METRIC ${i}`,
      value: i * 0.1,
      format: 'ratio' as const,
    }))
    render(<MetricGrid metrics={sixMetrics} columns={6} />)
    expect(screen.getAllByText(/METRIC/)).toHaveLength(6)
  })
})
