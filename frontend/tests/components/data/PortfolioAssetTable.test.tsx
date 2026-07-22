import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { PortfolioAssetTable } from '@/components/data/PortfolioAssetTable'

const mockAssets = ['gold', 'silver', 'copper']

const mockMetrics: Record<string, Record<string, number | null>> = {
  gold: {
    sharpe: 0.301,
    max_drawdown: -0.068,
    total_return: 0.0425,
    win_rate: 0.211,
    avg_trade_duration_bars: 142,
  },
  silver: {
    sharpe: -0.082,
    max_drawdown: -0.094,
    total_return: -0.0082,
    win_rate: 0.19,
    avg_trade_duration_bars: 138,
  },
  copper: {
    sharpe: 0.142,
    max_drawdown: -0.071,
    total_return: 0.0121,
    win_rate: 0.205,
    avg_trade_duration_bars: 155,
  },
}

describe('PortfolioAssetTable', () => {
  it('renders three asset rows excluding the header', () => {
    render(<PortfolioAssetTable assetMetrics={mockMetrics} assets={mockAssets} />)

    const rows = screen.getAllByRole('row')
    expect(rows.length - 1).toBe(3)
  })

  it('colors positive and negative returns with gain and loss variables', () => {
    render(<PortfolioAssetTable assetMetrics={mockMetrics} assets={mockAssets} />)

    const rows = document.querySelectorAll('tbody tr')
    const goldReturn = rows[0]?.querySelectorAll('td')[3]
    const silverReturn = rows[1]?.querySelectorAll('td')[3]

    expect(goldReturn?.getAttribute('style')).toContain('--text-gain')
    expect(silverReturn?.getAttribute('style')).toContain('--text-loss')
  })

  it('renders an em dash for a null max drawdown', () => {
    const metricsWithNull = {
      gold: { ...mockMetrics.gold, max_drawdown: null },
    }
    render(<PortfolioAssetTable assetMetrics={metricsWithNull} assets={['gold']} />)

    const maxDrawdownCell = document.querySelector('tbody tr td:nth-child(3)')
    expect(maxDrawdownCell?.textContent).toBe('\u2014')
  })

  it('renders View links for assets with run IDs', () => {
    const assetRunIds: Record<string, string | null> = {
      gold: '20260722_142301_ema_crossover_gold',
      silver: null,
      copper: '20260722_142310_ema_crossover_copper',
    }
    render(
      <MemoryRouter>
        <PortfolioAssetTable
          assetMetrics={mockMetrics}
          assets={mockAssets}
          assetRunIds={assetRunIds}
        />
      </MemoryRouter>
    )
    const links = screen.getAllByRole('link', { name: /view.*run detail/i })
    // gold and copper have run IDs; silver is null
    expect(links).toHaveLength(2)
    expect(links[0]).toHaveAttribute('href', '/runs/20260722_142301_ema_crossover_gold')
  })

  it('renders no View column when assetRunIds prop is absent', () => {
    render(
      <PortfolioAssetTable
        assetMetrics={mockMetrics}
        assets={mockAssets}
        // no assetRunIds prop
      />
    )
    expect(screen.queryByRole('link', { name: /view/i })).not.toBeInTheDocument()
    expect(screen.queryByText('VIEW')).not.toBeInTheDocument()
  })
})
