import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type UniverseResponse = components['schemas']['UniverseResponse']

export function useAssets() {
  return useQuery({
    queryKey: qk.assets(),
    queryFn: () => client.get<UniverseResponse>('/api/assets'),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
  })
}
