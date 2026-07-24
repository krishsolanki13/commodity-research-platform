import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { TermStructureHistoryChart } from '@/components/charts/TermStructureHistoryChart'
import { mockChartInstance } from '../../setup'
import { goldCurveHistoryFixture } from '../../mocks/fixtures/curve'

describe('TermStructureHistoryChart', () => {
  beforeEach(() => {
    mockChartInstance.setOption.mockClear()
  })

  it('uses axis tooltip trigger for dual-series hover', () => {
    render(
      <TermStructureHistoryChart snapshots={goldCurveHistoryFixture.snapshots} height={320} />
    )
    const calls = mockChartInstance.setOption.mock.calls
    expect(calls.length).toBeGreaterThan(0)
    const option = calls[calls.length - 1][0] as { tooltip?: { trigger?: string } }
    expect(option.tooltip?.trigger).toBe('axis')
  })

  it('renders ChartFrame wrapper without errors with 10-snapshot history fixture', () => {
    const { container } = render(
      <TermStructureHistoryChart snapshots={goldCurveHistoryFixture.snapshots} height={320} />
    )
    expect(container.firstChild).toBeTruthy()
  })

  it('shows loading state when loading=true without crashing', () => {
    const { container } = render(
      <TermStructureHistoryChart snapshots={[]} loading={true} height={320} />
    )
    expect(container.firstChild).toBeTruthy()
    expect(screen.queryByText(/no history data/i)).toBeNull()
  })

  it('does not throw when snapshots array is empty', () => {
    expect(() => render(<TermStructureHistoryChart snapshots={[]} height={320} />)).not.toThrow()
  })

  it('renders regime bands without throwing with mixed-regime history', () => {
    expect(() =>
      render(
        <TermStructureHistoryChart
          snapshots={goldCurveHistoryFixture.snapshots}
          height={300}
          showRegimeBands={true}
        />
      )
    ).not.toThrow()
  })
})
