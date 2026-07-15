import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type DataStatusResponse = components['schemas']['DataStatusResponse']

export function useDataStatus(asset?: string) {
  const qs = asset ? `?asset=${asset}` : ''
  return useQuery({
    queryKey: qk.dataStatus(asset),
    queryFn: () => client.get<DataStatusResponse>(`/api/system/data-status${qs}`),
    staleTime: 5 * 60 * 1000,
  })
}
