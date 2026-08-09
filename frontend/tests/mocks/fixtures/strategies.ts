import type { components } from '@/api/schema'

type StrategyCatalogResponse = components['schemas']['StrategyCatalogResponse']

export const strategyCatalogFixture: StrategyCatalogResponse = {
  strategies: [
    {
      name: 'ema_crossover',
      display_name: 'EMA Crossover',
      description:
        'Long when fast EMA > slow EMA, short when fast EMA < slow EMA. Classic trend-following signal.',
      params_schema: [
        {
          name: 'fast_period',
          kind: 'int',
          default: 50,
          min: 2,
          max: 200,
          description: 'Fast EMA period',
          unit: 'bars',
        },
        {
          name: 'slow_period',
          kind: 'int',
          default: 200,
          min: 10,
          max: 500,
          description: 'Slow EMA period',
          unit: 'bars',
        },
        {
          name: 'signal_threshold',
          kind: 'float',
          default: 0.0,
          min: 0.0,
          max: 1.0,
          description: 'Threshold for position entry',
        },
      ],
      default_params: {
        fast_period: 50,
        slow_period: 200,
        signal_threshold: 0.0,
      },
    },
    {
      name: 'momentum',
      display_name: 'Momentum',
      description:
        'Long when z-scored momentum is positive, short when negative. Cross-sectional momentum adapted for single-asset use.',
      params_schema: [
        {
          name: 'lookback_period',
          kind: 'int',
          default: 20,
          min: 5,
          max: 252,
          description: 'Momentum lookback',
          unit: 'bars',
        },
        {
          name: 'z_score_window',
          kind: 'int',
          default: 63,
          min: 10,
          max: 252,
          description: 'Z-score window',
          unit: 'bars',
        },
        {
          name: 'signal_threshold',
          kind: 'float',
          default: 0.5,
          min: 0.0,
          max: 3.0,
          description: 'Z-score threshold',
        },
      ],
      default_params: {
        lookback_period: 20,
        z_score_window: 63,
        signal_threshold: 0.5,
      },
    },
    {
      name: 'rsi_reversion',
      display_name: 'RSI Reversion',
      description:
        'Long when RSI is oversold, short when overbought. Mean-reversion signal using RSI oscillator.',
      params_schema: [
        {
          name: 'period',
          kind: 'int',
          default: 14,
          min: 2,
          max: 50,
          description: 'RSI period',
          unit: 'bars',
        },
        {
          name: 'oversold_threshold',
          kind: 'float',
          default: 30.0,
          min: 10.0,
          max: 45.0,
          description: 'Oversold level',
        },
        {
          name: 'overbought_threshold',
          kind: 'float',
          default: 70.0,
          min: 55.0,
          max: 90.0,
          description: 'Overbought level',
        },
      ],
      default_params: {
        period: 14,
        oversold_threshold: 30,
        overbought_threshold: 70,
      },
    },
    {
      name: 'donchian_breakout',
      display_name: 'Donchian Breakout',
      description:
        'Long on upward channel breakout, short on downward breakout. Classic trend-following channel system.',
      params_schema: [
        {
          name: 'channel_period',
          kind: 'int',
          default: 20,
          min: 5,
          max: 252,
          description: 'Channel lookback',
          unit: 'bars',
        },
      ],
      default_params: {
        channel_period: 20,
      },
    },
    {
      name: 'carry',
      display_name: 'Carry',
      description:
        'Long in backwardation (positive roll yield), short in contango. Commodity risk premium from the futures curve.',
      params_schema: [
        {
          name: 'threshold',
          kind: 'float',
          default: 0.0,
          min: 0.0,
          max: 0.5,
          description: 'Minimum annualized roll yield magnitude to generate signal',
        },
        {
          name: 'n_contracts',
          kind: 'int',
          default: 4,
          min: 2,
          max: 12,
          description: 'Number of contracts used in forward curve construction',
        },
      ],
      default_params: {
        threshold: 0.0,
        n_contracts: 4,
      },
    },
    {
      name: 'wti_brent_spread',
      display_name: 'WTI-Brent Spread',
      description:
        "Mean-reversion signal based on the WTI-Brent crude oil spread z-score. Long WTI when spread is narrow (WTI cheap); short WTI when wide. Requires asset='wti'. Single-asset approximation of a spread trade.",
      params_schema: [
        {
          name: 'lookback',
          kind: 'int',
          default: 63,
          min: 20,
          max: 252,
          description: 'Rolling window for spread mean and std (trading days)',
        },
        {
          name: 'threshold',
          kind: 'float',
          default: 1.0,
          min: 0.5,
          max: 3.0,
          description: 'Entry threshold (|z| > threshold to enter position)',
        },
      ],
      default_params: {
        lookback: 63,
        threshold: 1.0,
      },
    },
    {
      name: 'cot_positioning',
      display_name: 'COT Positioning',
      description:
        'Contrarian signal from CFTC net speculative positioning. Percentile rank > 80 → short (overcrowded long). < 20 → long.',
      params_schema: [
        {
          name: 'upper_pct',
          kind: 'float',
          default: 80.0,
          min: 50.0,
          max: 99.0,
          description: 'Percentile rank above which to go short (overcrowded long)',
        },
        {
          name: 'lower_pct',
          kind: 'float',
          default: 20.0,
          min: 1.0,
          max: 50.0,
          description: 'Percentile rank below which to go long (overcrowded short)',
        },
      ],
      default_params: {
        upper_pct: 80.0,
        lower_pct: 20.0,
      },
    },
    {
      name: 'eia_inventory',
      display_name: 'EIA Inventory',
      description:
        'Fundamental signal from EIA weekly petroleum inventory surprise. WTI and Brent only. Drawdown (negative surprise) -> long. Build (positive) -> short. Flat for all non-crude assets.',
      params_schema: [
        {
          name: 'threshold',
          kind: 'float',
          default: 1.0,
          min: 0.5,
          max: 3.0,
          description: 'Z-score threshold for inventory surprise entry',
        },
      ],
      default_params: {
        threshold: 1.0,
      },
    },
  ],
}
