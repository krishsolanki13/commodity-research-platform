import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type COTDataResponse = components['schemas']['COTDataResponse']

export function useCOTData(asset: string | null) {
  const qs = new URLSearchParams({ asset: asset ?? '' })
  return useQuery({
    queryKey: qk.cotData(asset!),
    queryFn: (): Promise<COTDataResponse> => client.get(`/api/system/data/cot?${qs}`),
    enabled: !!asset,
    staleTime: 10 * 60 * 1000,
  })
}
