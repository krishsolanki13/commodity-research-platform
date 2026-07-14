import { render } from '@testing-library/react'
import { describe, test, expect } from 'vitest'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'

describe('LoadingSkeleton', () => {
  test('metric-grid variant renders', () => {
    const { container } = render(<LoadingSkeleton variant="metric-grid" columns={4} />)
    expect(container.querySelector('[data-variant="metric-grid"]')).toBeInTheDocument()
  })

  test('chart variant renders', () => {
    const { container } = render(<LoadingSkeleton variant="chart" />)
    expect(container.querySelector('[data-variant="chart"]')).toBeInTheDocument()
  })
})
