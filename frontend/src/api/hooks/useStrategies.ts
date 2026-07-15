import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type StrategyCatalogResponse = components['schemas']['StrategyCatalogResponse']

export function useStrategies() {
  return useQuery({
    queryKey: qk.strategies(),
    queryFn: () => client.get<StrategyCatalogResponse>('/api/strategies'),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
  })
}
