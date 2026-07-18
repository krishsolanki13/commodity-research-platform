import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RegimeComparisonTable } from '@/components/data/RegimeComparisonTable'
import { goldCurveSnapshotFixture } from '../../mocks/fixtures/curve'
import type { AssetSnapshotWithLabel } from '@/api/hooks/useCurveSnapshots'

const twoAssets: AssetSnapshotWithLabel[] = [
  {
    asset: 'gold',
    label: 'Gold',
    // goldCurveSnapshotFixture: regime='contango', annualized_slope_pct positive
    snapshot: { ...goldCurveSnapshotFixture },
  },
  {
    asset: 'silver',
    label: 'Silver',
    snapshot: {
      ...goldCurveSnapshotFixture,
      asset: 'silver',
      regime: 'backwardation',
      annualized_slope_pct: -0.021,
      roll_yield_annualized: 0.018,
    },
  },
]

describe('RegimeComparisonTable', () => {
  it('renders 2 asset rows from fixture', () => {
    render(<RegimeComparisonTable snapshots={twoAssets} />)
    expect(screen.getByText('Gold')).toBeInTheDocument()
    expect(screen.getByText('Silver')).toBeInTheDocument()
  })

  it('positive slope renders in warn color; negative slope in gain color', () => {
    render(<RegimeComparisonTable snapshots={twoAssets} />)
    const rows = document.querySelectorAll('tbody tr')
    expect(rows).toHaveLength(2)
    // Slope column is index 3 (ASSET=0, REGIME=1, FRONT PRICE=2, SLOPE=3, ROLL YIELD=4)
    const goldSlopeCell = rows[0].querySelectorAll('td')[3]
    expect(goldSlopeCell.getAttribute('style')).toMatch(/text-warn|--text-warn/)
    const silverSlopeCell = rows[1].querySelectorAll('td')[3]
    expect(silverSlopeCell.getAttribute('style')).toMatch(/text-gain|--text-gain/)
  })
})
