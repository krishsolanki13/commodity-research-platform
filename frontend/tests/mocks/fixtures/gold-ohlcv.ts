import type { components } from '@/api/schema'

type OhlcvResponse = components['schemas']['OhlcvResponse']

const BASE = 1580000000000
const DAY = 86400000

export const goldOhlcvFixture: OhlcvResponse = {
  asset: 'gold',
  from_date: '2026-06-13',
  to_date: '2026-07-06',
  bars: 20,
  bars_original: 20,
  downsampled: false,
  data: {
    index: Array.from({ length: 20 }, (_, i) => BASE + i * DAY),
    columns: {
      open: Array.from({ length: 20 }, (_, i) => 1900 + i * 1.5),
      high: Array.from({ length: 20 }, (_, i) => 1910 + i * 1.5),
      low: Array.from({ length: 20 }, (_, i) => 1890 + i * 1.5),
      close: Array.from({ length: 20 }, (_, i) => 1905 + i * 1.5),
      volume: Array.from({ length: 20 }, (_, i) => 12000 + ((i * 137) % 3000)),
    },
  },
}
