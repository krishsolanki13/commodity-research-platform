import { http, HttpResponse } from 'msw'
import { dataStatusFixture } from '../fixtures/data-status'

export const systemHandlers = [
  http.get('http://localhost:8000/api/system/data-status', () =>
    HttpResponse.json(dataStatusFixture)
  ),

  http.post('http://localhost:8000/api/system/ingest', () =>
    HttpResponse.json({
      status: 'ok',
      assets_ingested: ['gold', 'silver', 'copper', 'wti', 'brent', 'natural_gas'],
      assets_failed: [],
      detail: null,
    })
  ),

  http.get('http://localhost:8000/api/system/curve-coverage/:asset', ({ params }) =>
    HttpResponse.json({
      asset: params.asset,
      curve_coverage_start: '2024-09-27',
      n_contracts: 4,
      message: `Curve-dependent signals (Carry) are only evaluable from 2024-09-27 onward for ${String(params.asset)}`,
    })
  ),

  http.get('http://localhost:8000/api/system/data/qc', ({ request }) => {
    const asset = new URL(request.url).searchParams.get('asset') ?? 'gold'
    return HttpResponse.json({
      asset,
      generated_at: '2026-08-12T00:00:00Z',
      bar_count: 4120,
      from_date: '2010-01-04',
      to_date: '2026-08-11',
      zero_volume_days: 2,
      ohlc_violations: 0,
      large_gap_flags: 1,
      data_health: 'ok',
      anomalies: [],
    })
  }),

  http.get('http://localhost:8000/api/system/data/cot', ({ request }) => {
    const asset = new URL(request.url).searchParams.get('asset') ?? 'gold'
    if (asset === 'brent') {
      return HttpResponse.json({
        asset,
        available: false,
        records: [],
        message: 'COT data is not available for this asset.',
      })
    }
    return HttpResponse.json({
      asset,
      available: true,
      message: '',
      records: [
        { date: '2024-01-02', net_speculative: 120000, percentile_rank: 0.72 },
        { date: '2024-01-09', net_speculative: 135000, percentile_rank: 0.81 },
        { date: '2024-01-16', net_speculative: 128000, percentile_rank: 0.76 },
      ],
    })
  }),

  http.get('http://localhost:8000/api/system/data/eia', ({ request }) => {
    const asset = new URL(request.url).searchParams.get('asset') ?? 'wti'
    if (asset === 'gold' || asset === 'silver' || asset === 'copper') {
      return HttpResponse.json({
        asset,
        available: false,
        records: [],
        message: 'EIA inventory data is not available for this asset.',
      })
    }
    return HttpResponse.json({
      asset,
      available: true,
      message: '',
      records: [
        { date: '2024-01-05', inventory: 420.1, surprise: -1.2, surprise_zscore: -0.8 },
        { date: '2024-01-12', inventory: 418.4, surprise: 2.1, surprise_zscore: 1.1 },
        { date: '2024-01-19', inventory: 419.0, surprise: 0.3, surprise_zscore: 0.2 },
      ],
    })
  }),
]
