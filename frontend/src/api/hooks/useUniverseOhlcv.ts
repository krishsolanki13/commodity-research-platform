import { useQueries } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'
import { rangeToDateParams } from '@/lib/date-range'
import type { RangePreset } from '@/lib/date-range'

type OhlcvResponse = components['schemas']['OhlcvResponse']

export const ASSET_NAMES = ['gold', 'silver', 'copper', 'wti', 'brent', 'natural_gas'] as const

export type AssetName = (typeof ASSET_NAMES)[number]

export function useUniverseOhlcv(range: RangePreset) {
  const { from_date, to_date } = rangeToDateParams(range)

  return useQueries({
    queries: ASSET_NAMES.map((asset) => ({
      queryKey: qk.assetOhlcv(asset, { from_date, to_date, downsample: 'view' as const }),
      queryFn: () => {
        const qs = new URLSearchParams({ from_date, to_date, downsample: 'view' })
        return client.get<OhlcvResponse>(`/api/assets/${asset}/ohlcv?${qs}`)
      },
      staleTime: 5 * 60 * 1000,
    })),
  })
}
