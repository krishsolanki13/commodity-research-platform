import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { queryClient } from '@/app/queryClient'
import { WalkForwardChart } from '@/components/charts/WalkForwardChart'
import { ValidationSummaryTable } from '@/features/runs/ValidationSummaryTable'
import type { components } from '@/api/schema'

type ValidationReportResponse = components['schemas']['ValidationReportResponse']

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

const mockFolds = [
  { fold: 0, is_sharpe: 0.45, oos_sharpe: 0.38 },
  { fold: 1, is_sharpe: 0.52, oos_sharpe: null },
  { fold: 2, is_sharpe: -0.1, oos_sharpe: 0.05 },
]

function baseReport(
  overrides: Partial<ValidationReportResponse> = {},
): ValidationReportResponse {
  return {
    validation_run_id: 'val-1',
    asset: 'gold',
    strategy_name: 'ema_crossover',
    parameters: { fast_period: 50 },
    n_splits: 3,
    embargo_bars: 10,
    computation_date: '2026-08-06T00:00:00Z',
    folds: [
      {
        split: {
          fold_idx: 0,
          train_start: '2015-01-01',
          train_end: '2018-01-01',
          test_start: '2018-01-15',
          test_end: '2019-01-01',
          n_train_bars: 750,
          n_test_bars: 250,
          embargo_bars: 10,
        },
        train_sharpe: 0.45,
        test_sharpe: 0.38,
        train_return: 0.12,
        test_return: 0.1,
        train_max_dd: -0.08,
        test_max_dd: -0.09,
        train_n_trades: 40,
        test_n_trades: 12,
        overfitting_ratio: 0.84,
      },
    ],
    insample_sharpe: 0.5,
    outsample_sharpe: 0.45,
    insample_return: 0.1,
    outsample_return: 0.09,
    overfitting_ratio: 0.9,
    sharpe_se: 0.1,
    psr: 0.8,
    n_trials: 1,
    sr_benchmark: 0,
    dsr: 0.7,
    is_significant: true,
    dsr_threshold: 0.95,
    ...overrides,
  }
}

describe('WalkForwardChart', () => {
  it('renders without crashing with 3 folds of mock data', () => {
    expect(() =>
      render(<WalkForwardChart folds={mockFolds} />, { wrapper: Wrapper }),
    ).not.toThrow()
    expect(screen.getByText('Walk-Forward Folds')).toBeInTheDocument()
  })

  it('renders loading state', () => {
    render(<WalkForwardChart folds={[]} loading={true} />, { wrapper: Wrapper })
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })

  it('handles null is_sharpe / oos_sharpe without crashing', () => {
    expect(() =>
      render(
        <WalkForwardChart
          folds={[
            { fold: 0, is_sharpe: null, oos_sharpe: null },
            { fold: 1, is_sharpe: 0.2, oos_sharpe: null },
          ]}
        />,
        { wrapper: Wrapper },
      ),
    ).not.toThrow()
  })
})

describe('ValidationSummaryTable', () => {
  it('renders all 7 metric rows', () => {
    render(<ValidationSummaryTable report={baseReport()} />, { wrapper: Wrapper })
    expect(screen.getByText('Sharpe')).toBeInTheDocument()
    expect(screen.getByText('Total Return')).toBeInTheDocument()
    expect(screen.getByText('Max Drawdown')).toBeInTheDocument()
    expect(screen.getByText('N Trades')).toBeInTheDocument()
    expect(screen.getByText('Overfitting Ratio')).toBeInTheDocument()
    expect(screen.getByText('PSR')).toBeInTheDocument()
    expect(screen.getByText('DSR')).toBeInTheDocument()
  })

  it('applies text-gain when OOS/IS ratio >= 0.8', () => {
    const { container } = render(
      <ValidationSummaryTable
        report={baseReport({
          insample_sharpe: 1.0,
          outsample_sharpe: 0.85,
        })}
      />,
      { wrapper: Wrapper },
    )
    expect(container.querySelector('.text-gain')).toBeTruthy()
  })

  it('applies text-warn when OOS/IS ratio 0.5–0.8', () => {
    const { container } = render(
      <ValidationSummaryTable
        report={baseReport({
          insample_sharpe: 1.0,
          outsample_sharpe: 0.6,
          insample_return: null,
          outsample_return: null,
          folds: [],
        })}
      />,
      { wrapper: Wrapper },
    )
    expect(container.querySelector('.text-warn')).toBeTruthy()
  })

  it('applies text-loss when OOS/IS ratio < 0.5', () => {
    const { container } = render(
      <ValidationSummaryTable
        report={baseReport({
          insample_sharpe: 1.0,
          outsample_sharpe: 0.3,
          insample_return: null,
          outsample_return: null,
          folds: [],
        })}
      />,
      { wrapper: Wrapper },
    )
    expect(container.querySelector('.text-loss')).toBeTruthy()
  })
})
