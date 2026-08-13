import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type EIADataResponse = components['schemas']['EIADataResponse']

export function useEIAData(asset: string | null) {
  const qs = new URLSearchParams({ asset: asset ?? '' })
  return useQuery({
    queryKey: qk.eiaData(asset!),
    queryFn: (): Promise<EIADataResponse> => client.get(`/api/system/data/eia?${qs}`),
    enabled: !!asset,
    staleTime: 10 * 60 * 1000,
  })
}
