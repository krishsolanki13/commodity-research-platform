export const curveAvailableFixture = {
  assets: ['gold', 'silver', 'copper', 'wti', 'brent', 'natural_gas'],
}

export const goldCurveSnapshotFixture = {
  asset: 'gold',
  observation_date: '2026-07-15',
  regime: 'contango',
  front_price: 2400.5,
  back_price: 2450.2,
  n_contracts: 4,
  annualized_slope_pct: 0.0433,
  roll_yield_annualized: -0.0357,
  basis: -95.9,
  basis_pct: -0.0416,
  points: [
    { ticker: 'GCZ25', close: 2400.5, days_to_delivery: 165, data_date: '2026-07-15' },
    { ticker: 'GCG26', close: 2418.3, days_to_delivery: 226, data_date: '2026-07-15' },
    { ticker: 'GCJ26', close: 2434.1, days_to_delivery: 286, data_date: '2026-07-15' },
    { ticker: 'GCM26', close: 2450.2, days_to_delivery: 347, data_date: '2026-07-15' },
  ],
}

const BASE_DATE = new Date('2025-07-15')

export const goldCurveHistoryFixture = {
  asset: 'gold',
  from_date: '2025-07-15',
  to_date: '2026-07-15',
  snapshots: Array.from({ length: 10 }, (_, i) => {
    const d = new Date(BASE_DATE)
    d.setMonth(BASE_DATE.getMonth() + i)
    return {
      observation_date: d.toISOString().slice(0, 10),
      regime: i % 3 === 0 ? 'backwardation' : 'contango',
      annualized_slope_pct: i % 3 === 0 ? -0.025 : 0.043,
      roll_yield_annualized: i % 3 === 0 ? 0.035 : -0.036,
      basis: -95.9 + i * 2,
      front_price: 2350.0 + i * 10,
      n_contracts: 4,
    }
  }),
}
