import type { components } from '@/api/schema'

type IndicatorCatalogResponse = components['schemas']['IndicatorCatalogResponse']

export const indicatorCatalogFixture: IndicatorCatalogResponse = {
  indicators: [
    {
      name: 'ema',
      display_name: 'Exponential Moving Average',
      category: 'trend',
      params_schema: [
        {
          name: 'period',
          kind: 'int',
          default: 20,
          min: 2,
          max: 500,
          description: 'Lookback period in bars',
          unit: 'bars',
        },
      ],
      column_name_template: 'ema_{period}',
    },
    {
      name: 'sma',
      display_name: 'Simple Moving Average',
      category: 'trend',
      params_schema: [
        {
          name: 'period',
          kind: 'int',
          default: 20,
          min: 2,
          max: 500,
          description: 'Lookback period in bars',
          unit: 'bars',
        },
      ],
      column_name_template: 'sma_{period}',
    },
    {
      name: 'rsi',
      display_name: 'Relative Strength Index',
      category: 'oscillator',
      params_schema: [
        {
          name: 'period',
          kind: 'int',
          default: 14,
          min: 2,
          max: 100,
          description: 'RSI period',
          unit: 'bars',
        },
      ],
      column_name_template: 'rsi_{period}',
    },
    {
      name: 'rvgi',
      display_name: 'Relative Vigor Index',
      category: 'oscillator',
      params_schema: [
        {
          name: 'period',
          kind: 'int',
          default: 10,
          min: 2,
          max: 100,
          description: 'RVGI period',
          unit: 'bars',
        },
      ],
      column_name_template: 'rvgi_{period}',
    },
    {
      name: 'momentum',
      display_name: 'Momentum',
      category: 'momentum',
      params_schema: [
        {
          name: 'lookback',
          kind: 'int',
          default: 20,
          min: 5,
          max: 126,
          description: 'Lookback bars',
          unit: 'bars',
        },
        {
          name: 'z_score_window',
          kind: 'int',
          default: 63,
          min: 20,
          max: 252,
          description: 'Z-score window',
          unit: 'bars',
        },
      ],
      column_name_template: 'momentum_{lookback}',
    },
  ],
}
