import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

// List endpoint returns SweepListResponse (not SweepRunSummaryResponse[])
type SweepListResponse = components['schemas']['SweepListResponse']

export function useSweeps() {
  return useQuery({
    queryKey: qk.sweep.list(),
    queryFn: (): Promise<SweepListResponse> => client.get('/api/sweeps'),
    staleTime: 30_000,
  })
}
