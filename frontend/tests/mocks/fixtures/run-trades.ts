import type { components } from '@/api/schema'

type TradesPageResponse = components['schemas']['TradesPageResponse']
type TradeRecord = components['schemas']['TradeRecord']

const makeTrade = (i: number): TradeRecord => ({
  direction: i % 2 === 0 ? 'long' : 'short',
  entry_date: '2020-01-02',
  exit_date: '2020-06-15',
  entry_price: 1500.0 + i * 10,
  exit_price: 1600.0 + i * 10,
  duration_bars: 120 + i,
  gross_pnl: 10000 + i * 100,
  cost: 10.0,
  net_pnl: 9990 + i * 100,
  return_pct: 0.067,
  force_closed: i === 3,
})

export const goldTradesFixture: TradesPageResponse = {
  run_id: '20260715_120000_ema_crossover_gold',
  trades: Array.from({ length: 10 }, (_, i) => makeTrade(i)),
  page: 1,
  page_size: 100,
  total: 19,
  stats: {
    n_trades: 19,
    avg_duration_bars: 142,
    avg_win: 8234.5,
    avg_loss: -4123.2,
    largest_win: 31456.7,
    largest_loss: -18234.1,
  },
}
