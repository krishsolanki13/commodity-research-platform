import { http, HttpResponse } from 'msw'

export const featureHandlers = [
  http.post('http://localhost:8000/api/features/compute', () =>
    HttpResponse.json({
      asset: 'gold',
      from_date: '2015-01-01',
      to_date: '2026-07-06',
      bars: 2890,
      specs: [
        {
          indicator_name: 'ema',
          params: { period: 50 },
          column_name: 'ema_50',
          asset: 'gold',
          computed_at: '2026-07-06T00:00:00Z',
        },
      ],
      columns: {
        index: [1609459200000],
        columns: { ema_50: [1902.5] },
      },
    })
  ),
]
