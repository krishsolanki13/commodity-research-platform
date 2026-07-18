import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { AssetAttributionTable } from '@/components/data/AssetAttributionTable'
import { portfolioSummaryFixture } from '../../mocks/fixtures/portfolio'

const tableProps = {
  absolutePnlByAsset: portfolioSummaryFixture.absolute_pnl_by_asset,
  assets: portfolioSummaryFixture.assets,
  initialCapitalPerAsset: portfolioSummaryFixture.initial_capital_per_asset,
}

describe('AssetAttributionTable', () => {
  it('renders all six asset rows from the portfolio fixture', () => {
    render(<AssetAttributionTable {...tableProps} />)

    const table = screen.getByRole('grid', { name: 'Asset P&L attribution' })
    const body = table.querySelector('tbody')

    expect(body).not.toBeNull()
    expect(within(body as HTMLTableSectionElement).getAllByRole('row')).toHaveLength(6)
  })

  it('renders positive P&L in gain color and negative P&L in loss color', () => {
    render(<AssetAttributionTable {...tableProps} />)

    expect(screen.getByText('+$42.5k')).toHaveStyle('color: var(--text-gain)')
    expect(screen.getByText('−$8.2k')).toHaveStyle('color: var(--text-loss)')
  })
})
