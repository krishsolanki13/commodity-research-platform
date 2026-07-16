import type { components } from '@/api/schema'

type RunListResponse = components['schemas']['RunListResponse']

export const MOCK_RUN_ID_2 = '20260714_100000_ema_crossover_silver'

export const runListFixture: RunListResponse = {
  runs: [
    {
      run_id: '20260715_120000_ema_crossover_gold',
      asset: 'gold',
      strategy: 'ema_crossover',
      status: 'complete',
      from_date: '2015-01-01',
      to_date: '2026-07-15',
      sharpe: 0.301,
      max_drawdown: -0.0682,
      total_return: 0.182,
      cagr: 0.0153,
      win_rate: 0.211,
      n_trades: 19,
      ic: 0.0123,
      ic_band: 'noise',
      executed_at: '2026-07-15T12:00:03Z',
    },
    {
      run_id: MOCK_RUN_ID_2,
      asset: 'silver',
      strategy: 'ema_crossover',
      status: 'complete',
      from_date: '2015-01-01',
      to_date: '2026-07-14',
      sharpe: 0.412,
      max_drawdown: -0.0945,
      total_return: 0.231,
      cagr: 0.0194,
      win_rate: 0.263,
      n_trades: 22,
      ic: 0.0189,
      ic_band: 'noise',
      executed_at: '2026-07-14T10:00:05Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
}
