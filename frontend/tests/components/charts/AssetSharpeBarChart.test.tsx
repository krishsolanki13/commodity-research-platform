import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { queryClient } from '@/app/queryClient'
import { AssetSharpeBarChart } from '@/components/charts/AssetSharpeBarChart'

// Same Wrapper as PortfolioRollingCorrelationChart.test.tsx (Inc1).
function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

const mockMetrics = {
  gold: {
    sharpe: 0.301,
    total_return: 0.0425,
    max_drawdown: -0.068,
    win_rate: 0.211,
    n_trades: 19,
  },
  silver: {
    sharpe: -0.082,
    total_return: -0.0082,
    max_drawdown: -0.094,
    win_rate: 0.19,
    n_trades: 22,
  },
  natural_gas: {
    sharpe: -0.178,
    total_return: -0.0169,
    max_drawdown: -0.154,
    win_rate: 0.183,
    n_trades: 27,
  },
}
const mockAssets = ['gold', 'silver', 'natural_gas']

describe('AssetSharpeBarChart', () => {
  it('renders without errors with populated assetMetrics fixture', () => {
    expect(() =>
      render(<AssetSharpeBarChart assetMetrics={mockMetrics} assets={mockAssets} />, {
        wrapper: Wrapper,
      })
    ).not.toThrow()
  })

  it('loading=true → loading skeleton', () => {
    render(<AssetSharpeBarChart assetMetrics={{}} assets={[]} loading={true} />, {
      wrapper: Wrapper,
    })
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })

  it('empty assetMetrics {} → empty state without throw', () => {
    render(
      <AssetSharpeBarChart
        assetMetrics={{}}
        assets={[]}
        empty={{ message: 'Re-run to generate.' }}
      />,
      { wrapper: Wrapper }
    )
    expect(screen.getByText(/re-run to generate/i)).toBeInTheDocument()
  })
})
