import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'
import type { OhlcvParams } from '@/api/queryKeys'

type OhlcvResponse = components['schemas']['OhlcvResponse']

export function useAssetOhlcv(asset: string, params: OhlcvParams = {}) {
  const search = new URLSearchParams()
  if (params.from_date) search.set('from_date', params.from_date)
  if (params.to_date) search.set('to_date', params.to_date)
  if (params.downsample) search.set('downsample', params.downsample)
  const qs = search.toString()

  return useQuery({
    queryKey: qk.assetOhlcv(asset, params),
    queryFn: () => client.get<OhlcvResponse>(`/api/assets/${asset}/ohlcv${qs ? `?${qs}` : ''}`),
    staleTime: 5 * 60 * 1000,
    enabled: !!asset,
  })
}
