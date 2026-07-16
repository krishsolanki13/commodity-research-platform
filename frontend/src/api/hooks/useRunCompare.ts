import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type CompareResponse = components['schemas']['CompareResponse']

export function useRunCompare(ids: string[]) {
  const sortedIds = [...ids].sort()

  return useQuery({
    queryKey: qk.runCompare(sortedIds),
    queryFn: () => client.post<CompareResponse>('/api/runs/compare', { ids: sortedIds }),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    enabled: ids.length >= 2,
    retry: 1,
  })
}
