import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { SweepResultsTable } from '@/features/sweeps/SweepResultsTable'
import type { components } from '@/api/schema'

type SweepRunSummaryResponse = components['schemas']['SweepRunSummaryResponse']

const mockRuns: SweepRunSummaryResponse[] = [
  {
    sweep_id: 'sw-1',
    run_id: 'run-1',
    parameters: { fast_period: 10, slow_period: 50 },
    sharpe: 0.85,
    total_return: 0.12,
    max_drawdown: -0.08,
    n_trades: 24,
    status: 'complete',
  },
  {
    sweep_id: 'sw-1',
    run_id: 'run-2',
    parameters: { fast_period: 20, slow_period: 100 },
    sharpe: 1.42,
    total_return: 0.18,
    max_drawdown: -0.05,
    n_trades: 19,
    status: 'complete',
  },
  {
    sweep_id: 'sw-1',
    run_id: 'run-3',
    parameters: { fast_period: 30, slow_period: 150 },
    sharpe: 0.62,
    total_return: 0.06,
    max_drawdown: -0.11,
    n_trades: 15,
    status: 'complete',
  },
]

describe('SweepResultsTable', () => {
  it('renders with mock runs data', () => {
    render(
      <SweepResultsTable
        runs={mockRuns}
        sortBy="sharpe"
        sortDir="desc"
        onSort={() => {}}
      />,
    )
    expect(screen.getByText(/fast_period=10/)).toBeInTheDocument()
    expect(screen.getByText(/slow_period=150/)).toBeInTheDocument()
  })

  it('highlights row with highest Sharpe using bg-bg-selected', () => {
    const { container } = render(
      <SweepResultsTable
        runs={mockRuns}
        sortBy="sharpe"
        sortDir="desc"
        onSort={() => {}}
      />,
    )
    const bestRow = container.querySelector('tr.bg-bg-selected')
    expect(bestRow).toBeTruthy()
    expect(bestRow?.textContent).toContain('fast_period=20')
  })

  it('calls onSort when column header clicked', async () => {
    const user = userEvent.setup()
    const onSort = vi.fn()
    render(
      <SweepResultsTable
        runs={mockRuns}
        sortBy="sharpe"
        sortDir="desc"
        onSort={onSort}
      />,
    )
    await user.click(screen.getByRole('columnheader', { name: /max dd/i }))
    expect(onSort).toHaveBeenCalledWith('max_drawdown')
  })
})
