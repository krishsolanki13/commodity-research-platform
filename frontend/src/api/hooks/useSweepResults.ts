import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type SweepResultResponse = components['schemas']['SweepResultResponse']

export function useSweepResults(
  sweepId: string | null,
  sortBy: string = 'sharpe',
  sortDir: string = 'desc'
) {
  const qs = new URLSearchParams({ sort_by: sortBy, sort_dir: sortDir })
  return useQuery({
    queryKey: qk.sweep.results(sweepId!, sortBy, sortDir),
    queryFn: (): Promise<SweepResultResponse> => client.get(`/api/sweeps/${sweepId}/results?${qs}`),
    enabled: !!sweepId,
    staleTime: Infinity,
  })
}
