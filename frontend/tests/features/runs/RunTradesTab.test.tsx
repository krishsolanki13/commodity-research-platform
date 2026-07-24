import { describe, it, expect } from 'vitest'
import { computeFilteredStats } from '@/features/runs/RunTradesTab'
import type { components } from '@/api/schema'

type TradeRecord = components['schemas']['TradeRecord']

function makeTrade(
  overrides: Partial<TradeRecord> & Pick<TradeRecord, 'direction' | 'duration_bars' | 'net_pnl'>
): TradeRecord {
  return {
    entry_date: '2020-01-02',
    exit_date: '2020-06-15',
    entry_price: 1500,
    exit_price: 1600,
    gross_pnl: overrides.net_pnl,
    cost: 10,
    return_pct: 0.05,
    force_closed: false,
    ...overrides,
  }
}

describe('computeFilteredStats', () => {
  it('trade KPI stats update when direction filter changes', () => {
    const trades: TradeRecord[] = [
      makeTrade({ direction: 'long', duration_bars: 100, net_pnl: 500 }),
      makeTrade({ direction: 'long', duration_bars: 200, net_pnl: -100 }),
      makeTrade({ direction: 'short', duration_bars: 50, net_pnl: 200 }),
      makeTrade({ direction: 'short', duration_bars: 150, net_pnl: -50 }),
    ]

    const allStats = computeFilteredStats(trades, trades.length)
    expect(allStats.n_trades).toBe(4)
    expect(allStats.avg_duration_bars).toBe(125) // (100+200+50+150)/4

    const shortOnly = trades.filter((t) => t.direction === 'short')
    const shortStats = computeFilteredStats(shortOnly, shortOnly.length)
    expect(shortStats.n_trades).toBe(2)
    expect(shortStats.avg_duration_bars).toBe(100) // (50+150)/2
  })
})
