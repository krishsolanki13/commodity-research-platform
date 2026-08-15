import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { queryClient } from '@/app/queryClient'
import { RegimeBreakdownChart } from '@/components/charts/RegimeBreakdownChart'
import { PortfolioRegimePanel } from '@/features/portfolio/PortfolioRegimePanel'
import type { components } from '@/api/schema'

type RegimeAttributionResponse = components['schemas']['RegimeAttributionResponse']

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

function mockRegimeData(
  overrides: Partial<RegimeAttributionResponse> = {},
): RegimeAttributionResponse {
  return {
    run_id: '20260808_test_gold',
    asset: 'gold',
    strategy_name: 'ema_crossover',
    n_contracts: 4,
    computation_date: '2026-08-08',
    regime_metrics: {
      contango: {
        regime: 'contango',
        n_days: 100,
        coverage: 0.4,
        sharpe: 0.3,
        total_return: 0.12,
        max_drawdown: -0.05,
        n_trades: 10,
        win_rate: 0.5,
      },
      backwardation: {
        regime: 'backwardation',
        n_days: 80,
        coverage: 0.35,
        sharpe: 0.5,
        total_return: 0.18,
        max_drawdown: -0.04,
        n_trades: 8,
        win_rate: 0.55,
      },
      flat: {
        regime: 'flat',
        n_days: 50,
        coverage: 0.25,
        sharpe: 0.1,
        total_return: 0.04,
        max_drawdown: -0.02,
        n_trades: 5,
        win_rate: 0.4,
      },
    },
    regime_coverage: { contango: 0.4, backwardation: 0.35, flat: 0.25 },
    dominant_regime: 'contango',
    total_days_with_regime: 230,
    total_days_in_run: 250,
    ...overrides,
  }
}

describe('RegimeBreakdownChart', () => {
  it('renders without crashing with mock regime metrics', () => {
    expect(() =>
      render(<RegimeBreakdownChart data={mockRegimeData()} />, { wrapper: Wrapper }),
    ).not.toThrow()
    expect(screen.getByText('Performance by Term Structure Regime')).toBeInTheDocument()
  })

  it('shows loading state when loading=true', () => {
    render(<RegimeBreakdownChart data={mockRegimeData()} loading={true} />, {
      wrapper: Wrapper,
    })
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })
})

describe('PortfolioRegimePanel', () => {
  it('shows empty state when assetRunIds is null', () => {
    render(<PortfolioRegimePanel runId="port-1" assetRunIds={null} />, {
      wrapper: Wrapper,
    })
    expect(screen.getByText('Regime attribution unavailable')).toBeInTheDocument()
  })

  it('shows empty state when assetRunIds is {}', () => {
    render(<PortfolioRegimePanel runId="port-1" assetRunIds={{}} />, {
      wrapper: Wrapper,
    })
    expect(screen.getByText('Regime attribution unavailable')).toBeInTheDocument()
  })
})
