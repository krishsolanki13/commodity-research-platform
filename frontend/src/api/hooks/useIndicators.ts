import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type IndicatorCatalogResponse = components['schemas']['IndicatorCatalogResponse']

export function useIndicators() {
  return useQuery({
    queryKey: qk.indicators(),
    queryFn: () => client.get<IndicatorCatalogResponse>('/api/indicators'),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
  })
}
