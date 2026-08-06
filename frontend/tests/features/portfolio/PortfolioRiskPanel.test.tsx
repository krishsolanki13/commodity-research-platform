import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { queryClient } from '@/app/queryClient'
import { ContributionToRiskChart } from '@/components/charts/ContributionToRiskChart'
import { PortfolioRiskPanel } from '@/features/portfolio/PortfolioRiskPanel'
import type { components } from '@/api/schema'

type RiskReportResponse = components['schemas']['RiskReportResponse']

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

const mockContribution = {
  gold: 0.22,
  silver: 0.18,
  copper: 0.15,
  wti: 0.2,
  brent: 0.15,
  natural_gas: 0.1,
}

function baseRisk(overrides: Partial<RiskReportResponse> = {}): RiskReportResponse {
  return {
    run_id: 'test-run',
    portfolio_var_95: 31948,
    portfolio_var_99: 44490,
    portfolio_var_95_pct: 0.0053,
    portfolio_var_99_pct: 0.0074,
    portfolio_es_95: 38000,
    portfolio_es_99: 52000,
    asset_var_95: { gold: 8200, silver: 15400 },
    asset_var_99: { gold: 11300, silver: 21000 },
    avg_gross_notional_by_asset: { gold: 1_000_000 },
    avg_net_notional_by_asset: { gold: 500_000 },
    total_avg_gross_notional: 6_000_000,
    total_avg_net_notional: 1_200_000,
    portfolio_diversification_benefit: 1.42,
    lookback_days: 252,
    methodology: 'historical_simulation',
    n_backtesting_days: 250,
    exceptions_95: 12,
    exceptions_99: 2,
    exception_rate_95: 0.048,
    exception_rate_99: 0.008,
    kupiec_lr_99: 0.5,
    kupiec_pvalue_99: 0.1,
    asset_contribution_to_vol: { gold: 0.01 },
    asset_contribution_to_vol_pct: mockContribution,
    ...overrides,
  }
}

describe('ContributionToRiskChart', () => {
  it('renders without crashing given mock data', () => {
    expect(() =>
      render(<ContributionToRiskChart data={mockContribution} />, { wrapper: Wrapper })
    ).not.toThrow()
    expect(screen.getByText('Vol Contribution by Asset')).toBeInTheDocument()
  })

  it('renders loading state via ChartFrame', () => {
    render(<ContributionToRiskChart data={{}} loading={true} />, { wrapper: Wrapper })
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })
})

describe('PortfolioRiskPanel Kupiec row', () => {
  it('shows "✓ Calibrated" when kupiec_pvalue_99 = 0.10', () => {
    render(<PortfolioRiskPanel risk={baseRisk({ kupiec_pvalue_99: 0.1 })} />, {
      wrapper: Wrapper,
    })
    expect(screen.getByText('✓ Calibrated')).toBeInTheDocument()
  })

  it('shows "✗ Miscalibrated" when kupiec_pvalue_99 = 0.02', () => {
    render(<PortfolioRiskPanel risk={baseRisk({ kupiec_pvalue_99: 0.02 })} />, {
      wrapper: Wrapper,
    })
    expect(screen.getByText('✗ Miscalibrated')).toBeInTheDocument()
  })

  it('shows em-dash when kupiec_pvalue_99 = null', () => {
    render(<PortfolioRiskPanel risk={baseRisk({ kupiec_pvalue_99: null })} />, {
      wrapper: Wrapper,
    })
    const calibration = screen.getByText('CALIBRATION').closest('div')
    expect(calibration).toBeTruthy()
    expect(calibration!.querySelector('.cursor-help')).toHaveTextContent('—')
  })
})
