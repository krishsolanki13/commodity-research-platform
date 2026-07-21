import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { queryClient } from '@/app/queryClient'
import { AssetRiskBarChart } from '@/components/charts/AssetRiskBarChart'

// Same Wrapper as PortfolioRollingCorrelationChart.test.tsx (Inc1).
function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

const mockVar99 = {
  gold: 11300,
  silver: 21000,
  copper: 12400,
  wti: 15100,
  brent: 14600,
  natural_gas: 60000,
}

describe('AssetRiskBarChart', () => {
  it('renders without errors with asset VaR fixture', () => {
    expect(() =>
      render(
        <AssetRiskBarChart
          assetVar99={mockVar99}
          assets={Object.keys(mockVar99)}
          height={220}
        />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
  })

  it('loading=true → loading skeleton', () => {
    render(
      <AssetRiskBarChart assetVar99={{}} assets={[]} loading={true} />,
      { wrapper: Wrapper }
    )
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })
})
