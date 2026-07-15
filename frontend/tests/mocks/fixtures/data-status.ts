import type { components } from '@/api/schema'

type DataStatusResponse = components['schemas']['DataStatusResponse']

export const dataStatusFixture: DataStatusResponse = {
  assets: [
    {
      name: 'gold',
      bar_count: 4150,
      from_date: '2010-01-04',
      to_date: '2026-07-06',
      last_ingested: '2026-07-06T08:00:00Z',
      flagged_anomalies: 0,
      data_health: 'ok',
      flags: [],
    },
    {
      name: 'silver',
      bar_count: 4148,
      from_date: '2010-01-04',
      to_date: '2026-07-06',
      last_ingested: '2026-07-06T08:00:00Z',
      flagged_anomalies: 0,
      data_health: 'ok',
      flags: [],
    },
    {
      name: 'copper',
      bar_count: 4147,
      from_date: '2010-01-04',
      to_date: '2026-07-06',
      last_ingested: '2026-07-06T08:00:00Z',
      flagged_anomalies: 2,
      data_health: 'warn',
      flags: [
        {
          date: '2020-03-18',
          violation_type: 'ohlc_consistency',
          detail: 'Close outside High-Low range',
        },
        {
          date: '2021-02-24',
          violation_type: 'ohlc_consistency',
          detail: 'Close outside High-Low range',
        },
      ],
    },
    {
      name: 'wti',
      bar_count: 4150,
      from_date: '2010-01-04',
      to_date: '2026-07-06',
      last_ingested: '2026-07-06T08:00:00Z',
      flagged_anomalies: 0,
      data_health: 'ok',
      flags: [],
    },
    {
      name: 'brent',
      bar_count: 4102,
      from_date: '2010-01-04',
      to_date: '2026-07-06',
      last_ingested: '2026-07-06T08:00:00Z',
      flagged_anomalies: 0,
      data_health: 'ok',
      flags: [],
    },
    {
      name: 'natural_gas',
      bar_count: 4145,
      from_date: '2010-01-04',
      to_date: '2026-07-06',
      last_ingested: '2026-07-06T08:00:00Z',
      flagged_anomalies: 0,
      data_health: 'ok',
      flags: [],
    },
  ],
  total_flags: 2,
}
