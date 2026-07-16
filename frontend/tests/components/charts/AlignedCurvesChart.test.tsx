import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AlignedCurvesChart } from '@/components/charts/AlignedCurvesChart'
import { compareFixture } from '../../mocks/fixtures/compare'

const twoSeriesFixture = compareFixture.aligned_series.map((s, i) => ({
  runId: s.run_id,
  label: `Run ${i + 1}`,
  equityNormalized: s.equity_normalized,
}))

describe('AlignedCurvesChart', () => {
  it('renders without errors with 2-series fixture', () => {
    render(
      <AlignedCurvesChart series={twoSeriesFixture} title="Normalized Returns" />
    )
    expect(screen.getByText('Normalized Returns')).toBeInTheDocument()
  })

  it('loading=true passes loading state to ChartFrame', () => {
    const { container } = render(
      <AlignedCurvesChart
        series={twoSeriesFixture}
        title="Normalized Returns"
        loading
      />
    )
    const loadingEl = container.querySelector(
      '[aria-busy="true"], .animate-pulse, [data-testid="loading-skeleton"]'
    )
    expect(loadingEl).not.toBeNull()
  })

  it('empty series array does not throw', () => {
    expect(() =>
      render(<AlignedCurvesChart series={[]} title="Empty" />)
    ).not.toThrow()
  })
})
