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
  ],
}
