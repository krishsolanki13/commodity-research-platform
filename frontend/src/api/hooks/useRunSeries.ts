import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type SeriesResponse = components['schemas']['SeriesResponse']

export function useRunSeries(runId: string, name: 'equity_curve' | 'pnl' | 'positions') {
  return useQuery({
    queryKey: qk.runSeries(runId, name),
    queryFn: () => client.get<SeriesResponse>(`/api/runs/${runId}/series/${name}`),
    enabled: !!runId,
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
  })
}
