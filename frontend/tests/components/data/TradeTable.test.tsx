import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { TradeTable } from '@/components/data/TradeTable'
import { goldTradesFixture } from '../../mocks/fixtures/run-trades'
import { MOCK_RUN_ID } from '../../mocks/fixtures/run-detail'

const DEFAULT_PROPS = {
  runId: MOCK_RUN_ID,
  trades: goldTradesFixture.trades,
  page: 1,
  pageSize: 100,
  total: goldTradesFixture.total,
  stats: goldTradesFixture.stats,
  onPage: vi.fn(),
  direction: 'all' as const,
  onDirectionChange: vi.fn(),
  forceClosed: null,
  onForceClosedChange: vi.fn(),
}

describe('TradeTable', () => {
  it('renders trade direction values', () => {
    render(<TradeTable {...DEFAULT_PROPS} />)
    expect(screen.getAllByText('long').length).toBeGreaterThan(0)
  })

  it('force-closed trade shows the AlertTriangle icon', () => {
    render(<TradeTable {...DEFAULT_PROPS} />)
    expect(screen.getByTestId('force-closed-icon')).toBeInTheDocument()
  })

  it('stats header displays the total trade count', () => {
    render(<TradeTable {...DEFAULT_PROPS} />)
    expect(screen.getByText('19')).toBeInTheDocument()
  })

  it('loading prop renders a loading state without throwing', () => {
    expect(() => render(<TradeTable {...DEFAULT_PROPS} loading={true} />)).not.toThrow()
  })
})
