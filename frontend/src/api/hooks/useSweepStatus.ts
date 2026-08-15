import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type SweepStatusResponse = components['schemas']['SweepStatusResponse']

export function useSweepStatus(sweepId: string | null) {
  return useQuery({
    queryKey: qk.sweep.status(sweepId!),
    queryFn: (): Promise<SweepStatusResponse> => client.get(`/api/sweeps/${sweepId}/status`),
    enabled: !!sweepId,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s !== 'complete' && s !== 'failed' ? 2000 : false
    },
    staleTime: 0,
  })
}
