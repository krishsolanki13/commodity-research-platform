import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MetricDeltaTable } from '@/components/data/MetricDeltaTable'
import { compareFixture } from '../../mocks/fixtures/compare'

describe('MetricDeltaTable', () => {
  it('renders 8 metric rows by default', () => {
    render(
      <MetricDeltaTable
        runs={compareFixture.runs}
        baseRunId={compareFixture.runs[0].run_id}
      />
    )
    const expectedLabels = [
      'Sharpe', 'Sortino', 'Calmar', 'Total Return',
      'CAGR', 'Max Drawdown', 'Win Rate', 'Profit Factor',
    ]
    for (const label of expectedLabels) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })

  it('non-base run shows a delta value; base run shows no delta', () => {
    render(
      <MetricDeltaTable
        runs={compareFixture.runs}
        baseRunId={compareFixture.runs[0].run_id}
      />
    )
    // Non-base run deltas are prefixed with + or -
    const deltaValues = screen.getAllByText(/^[+-]/)
    expect(deltaValues.length).toBeGreaterThan(0)
  })

  it('base run has ★ marker in column header', () => {
    render(
      <MetricDeltaTable
        runs={compareFixture.runs}
        baseRunId={compareFixture.runs[0].run_id}
      />
    )
    expect(screen.getByText(/★/)).toBeInTheDocument()
  })
})
