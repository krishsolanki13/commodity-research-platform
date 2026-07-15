import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type AssetSummaryResponse = components['schemas']['AssetSummaryResponse']

export function useAssetSummary(asset: string, from?: string, to?: string) {
  return useQuery({
    queryKey: qk.assetSummary(asset, from, to),
    queryFn: () => {
      const qs = new URLSearchParams()
      if (from) qs.set('from_date', from)
      if (to) qs.set('to_date', to)
      const qsStr = qs.toString()
      return client.get<AssetSummaryResponse>(
        `/api/assets/${asset}/summary${qsStr ? `?${qsStr}` : ''}`
      )
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!asset,
  })
}
