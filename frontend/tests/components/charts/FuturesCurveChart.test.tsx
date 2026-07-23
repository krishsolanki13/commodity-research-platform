import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { FuturesCurveChart } from '@/components/charts/FuturesCurveChart'
import { goldCurveSnapshotFixture } from '../../mocks/fixtures/curve'

describe('FuturesCurveChart', () => {
  it('renders ChartFrame wrapper without errors with 4-point Gold fixture', () => {
    const { container } = render(
      <FuturesCurveChart
        points={goldCurveSnapshotFixture.points}
        regime={goldCurveSnapshotFixture.regime as 'contango'}
        asset="gold"
        height={300}
      />
    )
    expect(container.firstChild).toBeTruthy()
  })

  it('shows loading state when loading=true without crashing', () => {
    const { container } = render(
      <FuturesCurveChart points={[]} regime={null} asset="gold" loading={true} height={300} />
    )
    // ChartFrame renders loading skeleton — no empty message should appear
    expect(container.firstChild).toBeTruthy()
    expect(screen.queryByText(/no contract data/i)).toBeNull()
  })

  it('shows empty state message when points array is empty', () => {
    const emptyMsg = 'No contract data for this asset.'
    render(
      <FuturesCurveChart
        points={[]}
        regime={null}
        asset="gold"
        empty={{ message: emptyMsg }}
        height={300}
      />
    )
    expect(screen.getByText(emptyMsg)).toBeTruthy()
  })
})
