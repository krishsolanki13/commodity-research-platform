import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/app/queryClient'
import { ICRollingChart } from '@/components/charts/ICRollingChart'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

const icSeriesFixture: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000],
  columns: { value: [0.012, 0.032, -0.001] },
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ICRollingChart', () => {
  it('renders ChartFrame wrapper without errors with IC series fixture', () => {
    render(<ICRollingChart ic={icSeriesFixture} window={63} />, { wrapper: Wrapper })
    expect(document.body).not.toBeEmptyDOMElement()
  })

  it('passes loading state through to ChartFrame', () => {
    render(<ICRollingChart ic={icSeriesFixture} window={63} loading={true} />, {
      wrapper: Wrapper,
    })
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })

  it('does not throw with empty ic series', () => {
    const emptyIc: ColumnarSeries = {
      index: [],
      columns: { value: [] },
    }
    expect(() =>
      render(<ICRollingChart ic={emptyIc} window={63} />, { wrapper: Wrapper })
    ).not.toThrow()
  })
})
