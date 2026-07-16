import type { components } from '@/api/schema'
import { MOCK_RUN_ID } from './run-detail'
import { MOCK_RUN_ID_2 } from './run-list'

type CompareResponse = components['schemas']['CompareResponse']

const BASE_INDEX = [1609459200000, 1609545600000, 1609632000000, 1609718400000]

export const compareFixture: CompareResponse = {
  runs: [
    {
      run_id: MOCK_RUN_ID,
      asset: 'gold',
      strategy: 'ema_crossover',
      from_date: '2015-01-01',
      to_date: '2026-07-15',
      params: { fast_period: 50, slow_period: 200, signal_threshold: 0.0 },
      metrics: {
        sharpe: 0.301,
        max_drawdown: -0.0682,
        total_return: 0.182,
        cagr: 0.0153,
        win_rate: 0.211,
        profit_factor: 1.31,
        calmar: 0.187,
        sortino: 0.412,
      },
    },
    {
      run_id: MOCK_RUN_ID_2,
      asset: 'silver',
      strategy: 'ema_crossover',
      from_date: '2015-01-01',
      to_date: '2026-07-14',
      params: { fast_period: 50, slow_period: 200, signal_threshold: 0.0 },
      metrics: {
        sharpe: 0.412,
        max_drawdown: -0.0945,
        total_return: 0.231,
        cagr: 0.0194,
        win_rate: 0.263,
        profit_factor: 1.58,
        calmar: 0.205,
        sortino: 0.521,
      },
    },
  ],
  aligned_series: [
    {
      run_id: MOCK_RUN_ID,
      equity_normalized: {
        index: BASE_INDEX,
        columns: { value: [0, 0.012, 0.008, 0.019] },
      },
      rolling_sharpe_63: {
        index: BASE_INDEX,
        columns: { value: [null, null, 0.28, 0.31] },
      },
    },
    {
      run_id: MOCK_RUN_ID_2,
      equity_normalized: {
        index: BASE_INDEX,
        columns: { value: [0, 0.018, 0.015, 0.027] },
      },
      rolling_sharpe_63: {
        index: BASE_INDEX,
        columns: { value: [null, null, 0.38, 0.42] },
      },
    },
  ],
  intersection_from: '2016-01-04',
  intersection_to: '2026-07-14',
  intersection_bars: 2600,
  mixed_assets: true,
}
