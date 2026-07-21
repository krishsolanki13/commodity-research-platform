import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { queryClient } from '@/app/queryClient'
import { PortfolioRollingCorrelationChart } from '@/components/charts/PortfolioRollingCorrelationChart'
import { portfolioCorrelationFixture } from '../../mocks/fixtures/portfolio'

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('PortfolioRollingCorrelationChart', () => {
  it('renders without errors with correlation fixture', () => {
    expect(() =>
      render(
        <PortfolioRollingCorrelationChart
          rollingCorrelations={portfolioCorrelationFixture.rolling_correlations_63}
          correlationMatrix={portfolioCorrelationFixture.correlation_matrix}
          windowDays={63}
          height={280}
        />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
  })

  it('loading=true → loading skeleton rendered', () => {
    render(
      <PortfolioRollingCorrelationChart
        rollingCorrelations={{}}
        correlationMatrix={{}}
        windowDays={63}
        loading={true}
      />,
      { wrapper: Wrapper }
    )
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })

  it('empty correlationMatrix → ChartFrame empty state', () => {
    render(
      <PortfolioRollingCorrelationChart
        rollingCorrelations={{}}
        correlationMatrix={{}}
        windowDays={63}
        empty={{ message: 'No data.' }}
      />,
      { wrapper: Wrapper }
    )
    expect(screen.getByText('No data.')).toBeInTheDocument()
  })
})
