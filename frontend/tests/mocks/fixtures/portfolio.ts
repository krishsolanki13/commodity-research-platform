export const MOCK_PORTFOLIO_RUN_ID = '20260718_120000_portfolio_ema_crossover'

export const portfolioSummaryFixture = {
  run_id: MOCK_PORTFOLIO_RUN_ID,
  strategy: 'ema_crossover',
  assets: ['gold', 'silver', 'copper', 'wti', 'brent', 'natural_gas'],
  skipped_assets: [],
  initial_capital_per_asset: 1_000_000,
  initial_capital_total: 6_000_000,
  portfolio_date_range: ['2015-01-05', '2026-07-15'],
  portfolio_metrics: {
    total_return: 0.0125,
    cagr: 0.0008,
    sharpe: 0.0018,
    sortino: 0.0024,
    calmar: 0.011,
    max_drawdown: -0.0737,
    portfolio_vol: 0.0254,
    n_trading_days: 2860,
  },
  absolute_pnl_by_asset: {
    gold: 42500,
    silver: -8200,
    copper: 12100,
    wti: -3400,
    brent: 8900,
    natural_gas: -16900,
  },
  asset_contributions: {
    gold: 0.028,
    silver: -0.005,
    copper: 0.008,
    wti: -0.002,
    brent: 0.006,
    natural_gas: -0.011,
  },
}

export const portfolioAssetsFixture = {
  run_id: MOCK_PORTFOLIO_RUN_ID,
  assets: [
    {
      asset: 'gold',
      total_return: 0.0425,
      cagr: 0.0036,
      sharpe: 0.301,
      max_drawdown: -0.068,
      n_trades: 19,
      absolute_pnl: 42_500,
    },
    {
      asset: 'silver',
      total_return: -0.0082,
      cagr: -0.0007,
      sharpe: -0.082,
      max_drawdown: -0.094,
      n_trades: 22,
      absolute_pnl: -8_200,
    },
    {
      asset: 'copper',
      total_return: 0.0121,
      cagr: 0.001,
      sharpe: 0.142,
      max_drawdown: -0.071,
      n_trades: 18,
      absolute_pnl: 12_100,
    },
    {
      asset: 'wti',
      total_return: -0.0034,
      cagr: -0.0003,
      sharpe: -0.041,
      max_drawdown: -0.088,
      n_trades: 21,
      absolute_pnl: -3_400,
    },
    {
      asset: 'brent',
      total_return: 0.0089,
      cagr: 0.0007,
      sharpe: 0.098,
      max_drawdown: -0.079,
      n_trades: 20,
      absolute_pnl: 8_900,
    },
    {
      asset: 'natural_gas',
      total_return: -0.0169,
      cagr: -0.0014,
      sharpe: -0.178,
      max_drawdown: -0.154,
      n_trades: 27,
      absolute_pnl: -16_900,
    },
  ],
  skipped_assets: [],
}

export const portfolioStatusCompleteFixture = {
  run_id: MOCK_PORTFOLIO_RUN_ID,
  status: 'complete',
  error: null,
  executed_at: '2026-07-18T12:00:45Z',
}

const BASE_INDEX = [1609459200000, 1609545600000, 1609632000000, 1609718400000]

export const portfolioEquityFixture = {
  run_id: MOCK_PORTFOLIO_RUN_ID,
  portfolio_equity: {
    index: BASE_INDEX,
    columns: { value: [6_000_000, 6_012_000, 6_008_000, 6_025_000] },
  },
  portfolio_pnl: {
    index: BASE_INDEX,
    columns: { value: [0, 12_000, -4_000, 17_000] },
  },
}

export const portfolioRiskFixture = {
  run_id: MOCK_PORTFOLIO_RUN_ID,
  portfolio_var_95: 31948,
  portfolio_var_99: 44490,
  portfolio_var_95_pct: 0.0053,
  portfolio_var_99_pct: 0.0074,
  portfolio_es_95: 72400,
  portfolio_es_99: 99095,
  asset_var_95: {
    gold: 8200,
    silver: 15400,
    copper: 9100,
    wti: 11200,
    brent: 10800,
    natural_gas: 44200,
  },
  asset_var_99: {
    gold: 11300,
    silver: 21000,
    copper: 12400,
    wti: 15100,
    brent: 14600,
    natural_gas: 60000,
  },
  avg_gross_notional_by_asset: {
    gold: 100000,
    silver: 100000,
    copper: 100000,
    wti: 100000,
    brent: 100000,
    natural_gas: 100000,
  },
  avg_net_notional_by_asset: {
    gold: 42000,
    silver: -18000,
    copper: 55000,
    wti: -22000,
    brent: 31000,
    natural_gas: -88000,
  },
  total_avg_gross_notional: 600000,
  total_avg_net_notional: 0,
  portfolio_diversification_benefit: 2.23,
}

export const portfolioCorrelationFixture = {
  run_id: MOCK_PORTFOLIO_RUN_ID,
  correlation_matrix: {
    gold: {
      gold: 1.0,
      silver: 0.65,
      copper: 0.31,
      wti: 0.18,
      brent: 0.17,
      natural_gas: 0.04,
    },
    silver: {
      gold: 0.65,
      silver: 1.0,
      copper: 0.28,
      wti: 0.12,
      brent: 0.11,
      natural_gas: 0.02,
    },
    copper: {
      gold: 0.31,
      silver: 0.28,
      copper: 1.0,
      wti: 0.24,
      brent: 0.23,
      natural_gas: 0.08,
    },
    wti: {
      gold: 0.18,
      silver: 0.12,
      copper: 0.24,
      wti: 1.0,
      brent: 0.62,
      natural_gas: 0.09,
    },
    brent: {
      gold: 0.17,
      silver: 0.11,
      copper: 0.23,
      wti: 0.62,
      brent: 1.0,
      natural_gas: 0.08,
    },
    natural_gas: {
      gold: 0.04,
      silver: 0.02,
      copper: 0.08,
      wti: 0.09,
      brent: 0.08,
      natural_gas: 1.0,
    },
  },
  rolling_correlations_63: {
    brent: {
      wti: { index: BASE_INDEX, columns: { value: [null, null, 0.84, 0.91] } },
    },
    gold: {
      silver: {
        index: BASE_INDEX,
        columns: { value: [null, null, 0.61, 0.68] },
      },
    },
  },
  rolling_correlations_126: {
    brent: {
      wti: { index: BASE_INDEX, columns: { value: [null, null, null, 0.88] } },
    },
    gold: {
      silver: {
        index: BASE_INDEX,
        columns: { value: [null, null, null, 0.64] },
      },
    },
  },
  realized_vol_by_asset: {
    gold: 0.0235,
    silver: 0.0412,
    copper: 0.0318,
    wti: 0.0287,
    brent: 0.0271,
    natural_gas: 0.0641,
  },
  portfolio_realized_vol: 0.0254,
  avg_pairwise_correlation: 0.12,
  most_correlated_pair: ['brent', 'wti', 0.62],
  least_correlated_pair: ['gold', 'natural_gas', 0.04],
}
