import type { components } from '@/api/schema'

type RunDetailResponse = components['schemas']['RunDetailResponse']

export const goldEmaRunDetailFixture: RunDetailResponse = {
  run_id: '20260715_120000_ema_crossover_gold',
  asset: 'gold',
  strategy: 'ema_crossover',
  status: 'complete',
  from_date: '2015-01-01',
  to_date: '2026-07-15',
  params: { fast_period: 50, slow_period: 200, signal_threshold: 0.0 },
  metrics: {
    total_return: 0.182,
    cagr: 0.0153,
    sharpe: 0.301,
    sortino: 0.412,
    calmar: 0.187,
    max_drawdown: -0.0682,
    avg_drawdown: -0.0231,
    win_rate: 0.211,
    profit_factor: 1.31,
    avg_trade_duration_bars: 142,
    turnover: 0.041,
    avg_win: 8234.5,
    avg_loss: -4123.2,
    largest_win: 31456.7,
    largest_loss: -18234.1,
    initial_capital: 1000000,
  },
  provenance: {
    git_sha: '285f65ad',
    dirty_flag: false,
    package_versions: {
      pandas: '2.3.3',
      numpy: '2.5.0',
      yfinance: '1.4.1',
    },
  },
  signal_evaluation: {
    ic: 0.0123,
    icir: 0.12,
    turnover: 0.041,
    decay: [
      { horizon: 1, ic: 0.0123 },
      { horizon: 2, ic: 0.0098 },
      { horizon: 5, ic: 0.0071 },
      { horizon: 10, ic: 0.0043 },
      { horizon: 20, ic: 0.0021 },
    ],
    evaluation_window: 4148,
    computed_at: '2026-07-15T00:00:00Z',
    ic_band: 'noise',
  },
}

export const MOCK_RUN_ID = goldEmaRunDetailFixture.run_id
