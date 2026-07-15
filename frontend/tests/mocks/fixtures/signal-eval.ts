import type { components } from '@/api/schema'

type SignalEvaluateResponse = components['schemas']['SignalEvaluateResponse']

// Real Gold EMA 50/200 IC from platform gate data — IC 0.0123 < 0.02 → noise band
export const goldEmaEvalFixture: SignalEvaluateResponse = {
  asset: 'gold',
  strategy: 'ema_crossover',
  params: { fast_period: 50, slow_period: 200, signal_threshold: 0.0 },
  evaluation: {
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
