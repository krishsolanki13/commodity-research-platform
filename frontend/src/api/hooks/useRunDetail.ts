import { useQuery } from '@tanstack/react-query'
import { client, ApiClientError } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type RunDetailResponse = components['schemas']['RunDetailResponse']

export function useRunDetail(runId: string) {
  return useQuery({
    queryKey: qk.run(runId),
    queryFn: () => client.get<RunDetailResponse>(`/api/runs/${runId}`),
    enabled: !!runId,
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    retry: (count, error) => {
      // Do not retry 404s — show ErrorState immediately
      if (error instanceof ApiClientError && error.apiError.status === 404) {
        return false
      }
      return count < 1
    },
  })
}
