import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type FeatureComputeRequest = components['schemas']['FeatureComputeRequest']
type FeatureComputeResponse = components['schemas']['FeatureComputeResponse']

export function useFeatureCompute(request: FeatureComputeRequest | null) {
  return useQuery({
    queryKey: qk.features(
      request?.asset ?? '',
      request?.from_date ?? undefined,
      request?.to_date ?? undefined,
      request?.specs
    ),
    queryFn: () => client.post<FeatureComputeResponse>('/api/features/compute', request!),
    staleTime: Infinity,
    enabled: request !== null,
  })
}
