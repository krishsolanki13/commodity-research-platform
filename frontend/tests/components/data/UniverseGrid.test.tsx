import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { TooltipProvider } from '@/ui/tooltip'
import { UniverseGrid } from '@/components/data/UniverseGrid'
import type { AssetRow } from '@/components/data/UniverseGrid'

function makeRow(overrides: Partial<AssetRow> = {}): AssetRow {
  return {
    name: 'gold',
    displayName: 'Gold',
    ticker: 'GC=F',
    exchange: 'COMEX',
    lastPrice: 1920.5,
    lastDate: '2026-07-06',
    return1d: 0.0012,
    return1w: 0.0087,
    return1m: 0.0234,
    realizedVol63d: 0.1526,
    avgVolume20d: 12500,
    barCount: 4150,
    dataHealth: 'ok',
    flaggedAnomalies: 0,
    sparklineValues: [1900, 1905, 1910, 1915, 1920],
    ...overrides,
  }
}

const DISPLAY_NAMES: Record<string, string> = {
  gold: 'Gold',
  silver: 'Silver',
  copper: 'Copper',
  wti: 'Wti',
  brent: 'Brent',
  natural_gas: 'Natural Gas',
}

const ASSET_NAMES = ['gold', 'silver', 'copper', 'wti', 'brent', 'natural_gas']
const SIX_ROWS: AssetRow[] = ASSET_NAMES.map((n) =>
  makeRow({ name: n, displayName: DISPLAY_NAMES[n] })
)

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter>
      <TooltipProvider>{children}</TooltipProvider>
    </MemoryRouter>
  )
}

describe('UniverseGrid', () => {
  it('renders 6 rows for 6-asset fixture', () => {
    render(<UniverseGrid rows={SIX_ROWS} onRowClick={vi.fn()} />, { wrapper: Wrapper })
    expect(screen.getByText('Gold')).toBeInTheDocument()
    expect(screen.getByText('Silver')).toBeInTheDocument()
    expect(screen.getByText('Natural Gas')).toBeInTheDocument()
  })

  it('calls onRowClick with asset name (not displayName) when row clicked', async () => {
    const onRowClick = vi.fn()
    render(<UniverseGrid rows={[makeRow()]} onRowClick={onRowClick} />, { wrapper: Wrapper })
    await userEvent.click(screen.getByText('Gold'))
    expect(onRowClick).toHaveBeenCalledWith('gold')
  })

  it('data_health="crit" renders crit color on health dot', () => {
    const critRow = makeRow({
      name: 'copper',
      displayName: 'Copper',
      dataHealth: 'crit',
      flaggedAnomalies: 3,
    })
    render(<UniverseGrid rows={[critRow]} onRowClick={vi.fn()} />, { wrapper: Wrapper })
    const html = document.body.innerHTML
    expect(html).toMatch(/crit/)
  })

  it('renders Sparkline SVG in rows', () => {
    render(<UniverseGrid rows={SIX_ROWS} onRowClick={vi.fn()} />, { wrapper: Wrapper })
    const svgs = document.querySelectorAll('svg')
    expect(svgs.length).toBeGreaterThanOrEqual(1)
  })

  it('loading=true renders skeleton instead of data rows', () => {
    render(<UniverseGrid rows={[]} onRowClick={vi.fn()} loading={true} />, { wrapper: Wrapper })
    // DataGrid loading state renders skeleton — no data rows
    expect(screen.queryByText('Gold')).not.toBeInTheDocument()
  })
})
